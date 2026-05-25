import os
import sys
import re
import argparse
import subprocess
from datetime import datetime

# Path references
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
VERSION_FILE = os.path.join(PROJECT_DIR, "src", "version.py")
FRONTEND_DIR = os.path.join(PROJECT_DIR, "frontend")

# Conventional commit patterns
CONVENTIONAL_COMMIT_PREFIXES = ["feat", "fix", "docs", "style", "refactor", "test", "chore", "perf", "ci", "build"]

def run_cmd(cmd, cwd=PROJECT_DIR, capture_output=False, check=True):
    """Utility to run a shell command."""
    print(f"Executing: {cmd}")
    res = subprocess.run(cmd, cwd=cwd, shell=True, text=True, capture_output=capture_output)
    if check and res.returncode != 0:
        print(f"Error executing command: {cmd}")
        if capture_output:
            print(f"Stdout:\n{res.stdout}")
            print(f"Stderr:\n{res.stderr}")
        sys.exit(res.returncode)
    return res

def get_active_branch():
    """Get the name of the currently checked out Git branch."""
    res = run_cmd("git rev-parse --abbrev-ref HEAD", capture_output=True)
    return res.stdout.strip()

def create_branch(task_name):
    """Phase 3: Automated Branch Creation."""
    # Normalize task name
    clean_name = re.sub(r'[^a-zA-Z0-9_-]', '-', task_name.lower())
    clean_name = re.sub(r'-+', '-', clean_name).strip('-')
    
    date_str = datetime.now().strftime("%Y%m%d")
    branch_name = f"task/{date_str}-{clean_name}"
    
    print(f"Creating topic branch: {branch_name}...")
    run_cmd(f"git checkout -b {branch_name}")
    print(f"Successfully switched to branch {branch_name}")

def validate_commit_message(msg):
    """Checks if message complies with Conventional Commit format."""
    pattern = r'^(' + '|'.join(CONVENTIONAL_COMMIT_PREFIXES) + r')(\([a-zA-Z0-9_-]+\))?!?: .+'
    if not re.match(pattern, msg):
        print(f"Error: Commit message '{msg}' does not match Conventional Commit specifications.")
        print("Example format: 'feat(api): add new endpoints' or 'fix(ui): resolve alignment issue'")
        sys.exit(1)

def run_tests():
    """Run Python unit tests using unittest."""
    print("Running automated Python unit tests...")
    res = subprocess.run("python -m unittest discover -s src -p \"test_*.py\"", cwd=PROJECT_DIR, shell=True)
    return res.returncode == 0

def commit_changes(msg):
    """Phase 3: Automated Pre-commit Tests & Commit."""
    # 1. Validate Commit Message
    validate_commit_message(msg)
    
    # 2. Run Tests
    if not run_tests():
        print("Error: Unit tests failed. Commit aborted.")
        sys.exit(1)
        
    print("All unit tests passed! Proceeding to stage and commit...")
    # 3. Stage and commit
    run_cmd("git add .")
    run_cmd(f'git commit -m "{msg}"')
    print("Changes committed successfully.")

def merge_main():
    """Phase 3: Merge back to main and clean up."""
    active_branch = get_active_branch()
    if active_branch == "main":
        print("Already on main branch.")
        sys.exit(1)
        
    print(f"Switching to main branch to merge: {active_branch}...")
    
    # Run tests on current branch first
    if not run_tests():
        print("Error: Tests failed on the active branch. Aborting merge.")
        sys.exit(1)
        
    # Check out main
    run_cmd("git checkout main")
    
    # Pull latest main changes if remote is configured
    remote_check = run_cmd("git remote", capture_output=True)
    if remote_check.stdout.strip():
        print("Pulling latest updates from remote...")
        subprocess.run("git pull origin main", cwd=PROJECT_DIR, shell=True)
        
    # Merge task branch
    print(f"Merging branch {active_branch} into main...")
    run_cmd(f"git merge {active_branch} --no-edit")
    
    # Run tests on main to verify integration
    if not run_tests():
        print("Error: Integration tests failed on main after merge. Please resolve conflicts or bugs.")
        sys.exit(1)
        
    # Delete local task branch
    print(f"Deleting local task branch {active_branch}...")
    run_cmd(f"git branch -d {active_branch}")
    print("Merge complete and task branch cleaned up.")

def read_version():
    """Reads semantic version from src/version.py."""
    if not os.path.exists(VERSION_FILE):
        return "1.0.0"
    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
    return match.group(1) if match else "1.0.0"

def write_version(ver_str):
    """Writes semantic version to src/version.py."""
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(f'__version__ = "{ver_str}"\n')

def bump_version(bump_type):
    """Phase 3: Bumps version, runs builds, and tags release."""
    active_branch = get_active_branch()
    if active_branch != "main":
        print("Releases and version bumps can only be triggered from the 'main' branch.")
        sys.exit(1)
        
    current_ver = read_version()
    parts = list(map(int, current_ver.split('.')))
    
    if bump_type == "major":
        parts[0] += 1
        parts[1] = 0
        parts[2] = 0
    elif bump_type == "minor":
        parts[1] += 1
        parts[2] = 0
    else:  # patch
        parts[2] += 1
        
    new_ver = ".".join(map(str, parts))
    print(f"Bumping version from v{current_ver} to v{new_ver}...")
    
    # 1. Update version.py
    write_version(new_ver)
    
    # 2. Build Frontend assets so the compiled bundle version matches
    print("Compiling frontend assets for release...")
    run_cmd("npm run build", cwd=FRONTEND_DIR)
    
    # 3. Commit version change and dist assets
    run_cmd("git add -f src/version.py frontend/dist")
    run_cmd(f'git commit -m "chore(release): bump version to v{new_ver}"')
    
    # 4. Tag Git release
    print(f"Creating Git release tag v{new_ver}...")
    run_cmd(f'git tag -a v{new_ver} -m "Release version {new_ver}"')
    print(f"Release v{new_ver} completed successfully! Remember to run 'git push origin main --tags' to sync.")

def sync_codebase():
    """Phase 6: Sync codebase, pull latest changes and restore stashed local edits."""
    active_branch = get_active_branch()
    
    # Check if there are unstaged changes
    status_check = run_cmd("git status --porcelain", capture_output=True)
    has_unstaged = bool(status_check.stdout.strip())
    
    if has_unstaged:
        print("Unstaged changes detected. Stashing them temporarily to prevent conflict...")
        run_cmd("git stash")
        
    try:
        # Check if remote is configured
        remote_check = run_cmd("git remote", capture_output=True)
        has_remote = bool(remote_check.stdout.strip())
        
        if has_remote:
            print("Fetching latest changes from remote...")
            subprocess.run("git fetch origin", cwd=PROJECT_DIR, shell=True)
            
        if active_branch != "main":
            print(f"Syncing main branch changes into topic branch {active_branch}...")
            # Check out main and update it
            run_cmd("git checkout main")
            if has_remote:
                subprocess.run("git pull origin main", cwd=PROJECT_DIR, shell=True)
            # Return to topic branch
            run_cmd(f"git checkout {active_branch}")
            
            # Merge main into topic branch
            print("Merging main into topic branch...")
            res = subprocess.run("git merge main --no-edit", cwd=PROJECT_DIR, shell=True)
            if res.returncode != 0:
                print("Warning: Merge conflict detected between main and your topic branch.")
                print("Aborting merge. Please resolve conflicts manually.")
                subprocess.run("git merge --abort", cwd=PROJECT_DIR, shell=True)
                sys.exit(1)
        else:
            # If we are on main, just pull main
            if has_remote:
                print("Pulling latest main branch...")
                subprocess.run("git pull origin main", cwd=PROJECT_DIR, shell=True)
                
        # Run tests to confirm sanity
        if not run_tests():
            print("Warning: Unit tests failed after sync. Codebase might be in an unhealthy state.")
        else:
            print("Codebase synced and verified successfully.")
    finally:
        if has_unstaged:
            print("Restoring stashed changes...")
            run_cmd("git stash pop")

def main():
    parser = argparse.ArgumentParser(description="Git Automation & Versioning Helper for Agents")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # create-branch
    p_branch = subparsers.add_parser("create-branch", help="Create topic branch for a task")
    p_branch.add_argument("task_name", help="Name of the task (e.g. 'pdf-upload-support')")
    
    # commit
    p_commit = subparsers.add_parser("commit", help="Run tests and commit modifications")
    p_commit.add_argument("message", help="Conventional Commit message")
    
    # merge-main
    subparsers.add_parser("merge-main", help="Switch to main, merge active task branch, run tests, and delete task branch")
    
    # bump
    p_bump = subparsers.add_parser("bump", help="Bump version, compile assets, commit, and tag release")
    p_bump.add_argument("type", choices=["patch", "minor", "major"], help="Type of version increment")
    
    # sync
    subparsers.add_parser("sync", help="Sync latest commits and resolve unstaged file conflicts")
    
    args = parser.parse_args()
    
    if args.command == "create-branch":
        create_branch(args.task_name)
    elif args.command == "commit":
        commit_changes(args.message)
    elif args.command == "merge-main":
        merge_main()
    elif args.command == "bump":
        bump_version(args.type)
    elif args.command == "sync":
        sync_codebase()

if __name__ == "__main__":
    main()

import os
import subprocess
import sys

def run_git(args):
    try:
        result = subprocess.run(["git"] + args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Git error running '{' '.join(args)}': {e.stderr}")
        return None

def main():
    print("==================================================")
    # CP1252 compatible header (no emojis)
    print("   Hugging Face Spaces Deployer Helper")
    print("==================================================")
    
    # 1. Check if git repository is set up
    if not os.path.exists(".git"):
        print("[ERROR] Git repository not initialized. Please run inside a git repo.")
        sys.exit(1)

    print("Before running this script, make sure you have:")
    print("1. Created a free account on https://huggingface.co")
    print("2. Created a new Space with 'Docker' SDK (select Blank template).")
    print("3. Generated a Write Access Token at: https://huggingface.co/settings/tokens")
    print("-" * 50)
    
    username = input("Enter your Hugging Face username: ").strip()
    space_name = input("Enter your Hugging Face Space name: ").strip()
    token = input("Enter your Hugging Face Write Access Token: ").strip()
    
    if not username or not space_name or not token:
        print("[ERROR] Username, Space name, and Token are all required.")
        sys.exit(1)
        
    # Get current branch name
    current_branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    if not current_branch:
        print("[ERROR] Could not determine current git branch.")
        sys.exit(1)
        
    print(f"Deploying current branch '{current_branch}' to Hugging Face Space '{username}/{space_name}'...")
    
    # Configure remote URL with token authentication
    remote_url = f"https://{username}:{token}@huggingface.co/spaces/{username}/{space_name}"
    
    # Check if remote 'hf' already exists
    remotes = run_git(["remote"])
    if remotes and "hf" in remotes.split():
        print("Updating existing git remote 'hf'...")
        run_git(["remote", "set-url", "hf", remote_url])
    else:
        print("Adding new git remote 'hf'...")
        run_git(["remote", "add", "hf", remote_url])
        
    # Push branch to Hugging Face
    print("Pushing repository to Hugging Face (this may take a moment)...")
    # Pushing current branch to HF spaces 'main' branch
    success = run_git(["push", "-f", "hf", f"{current_branch}:main"])
    
    if success is not None:
        print("\n==================================================")
        print("🎉 SUCCESS! Pushed to Hugging Face Spaces successfully.")
        print(f"Deployment link: https://huggingface.co/spaces/{username}/{space_name}")
        print("==================================================")
        print("\nNext steps:")
        print("1. Open settings in your HF Space.")
        print("2. Scroll to 'Repository secrets' and add a Secret:")
        print("   - Name: GEMINI_API_KEY")
        print("   - Value: (Your Gemini API Key)")
        print("3. Your Space will build and start automatically!")
    else:
        print("\n[ERROR] Deployment failed. Verify your token permissions and Space name.")

if __name__ == "__main__":
    main()

# 🤖 AI Agent Git & Versioning Rules

This document establishes the repository Git guidelines. All AI coding agents operating on this codebase **MUST** follow these rules to maintain perfect branch hygiene, automated release versioning, and continuous verification.

---

## 📋 Git Workflow Rules

### 0. Codebase Sync & Conflict Prevention
* **ALWAYS** run the sync utility immediately at the start of your agent execution before making any edits or starting a task:
  ```bash
  python scripts/git_helper.py sync
  ```
  This command automatically:
  1. Stashes any local unstaged changes.
  2. Fetches and pulls the latest commits from the remote `main` branch.
  3. Merges the updated `main` branch into your topic branch (if on a topic branch).
  4. Restores your local unstaged changes, automatically resolving concurrent workspace conflicts between different agent sessions.

### 1. Topic Branch Isolation
* **NEVER** edit files or commit directly to the `main` branch.
* For every task or user request, check out a dedicated topic branch before coding.
* Use the automation script to create and name the branch:
  ```bash
  python scripts/git_helper.py create-branch <task-name>
  ```
  This creates a branch named `task/YYYYMMDD-<task-name>` and switches to it automatically.

### 2. Conventional Commit Format
* All commits must strictly use the **Conventional Commits** format. Supported prefixes:
  * `feat`: A new feature (e.g. `feat(tracker): add kanban filter`)
  * `fix`: A bug fix (e.g. `fix(wizard): resolve button lock`)
  * `docs`: Documentation changes (e.g. `docs: update setup steps`)
  * `style`: Styling and asset modifications (e.g. `style(ui): transition colors`)
  * `refactor`: Code reorganization with no feature changes (e.g. `refactor(db): close connections`)
  * `test`: Adding or updating test suites (e.g. `test(api): check monitors trigger`)
  * `chore`: Minor tasks, version releases, build updates (e.g. `chore(release): bump version`)
  * `perf`: Performance optimizations (e.g. `perf(pdf): accelerate rendering`)

### 3. Automated Pre-Commit Verification
* **NEVER** commit using raw `git commit` commands.
* Always execute the automated commit command:
  ```bash
  python scripts/git_helper.py commit "<commit-message>"
  ```
  This script will:
  1. Validate that the commit message complies with Conventional Commit rules.
  2. Run the full Python test suite (`python -m unittest discover`).
  3. Stage all modified and untracked files (`git add .`) and commit **only if all tests pass**.
  4. Abort the commit immediately if any test fails.

### 4. Continuous Integration Merges
* When the task is complete and verified, merge back to main using the helper tool:
  ```bash
  python scripts/git_helper.py merge-main
  ```
  This script will check out `main`, pull latest changes, merge the task branch, run verification tests, and clean up the local task branch.

### 5. Semantic Release Versioning
* Bumping versions and releasing tags must only happen from the `main` branch.
* Choose the appropriate bump type:
  * **patch** (bugfixes, documentation, refactors): `python scripts/git_helper.py bump patch`
  * **minor** (new features, endpoints, components): `python scripts/git_helper.py bump minor`
  * **major** (breaking changes, database schema redesigns): `python scripts/git_helper.py bump major`
* The bump command automatically updates `src/version.py`, rebuilds the frontend bundles to sync assets, commits the changes, and tags a release (e.g., `v1.1.1`).

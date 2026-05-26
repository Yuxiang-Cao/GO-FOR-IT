# 🤖 GO FOR IT — Job Monitor & CV Tailor Agent System

An automated full-stack agentic system designed to monitor job boards, evaluate job descriptions (JDs), conduct clarifying interviews (`/grill-me`), customize LaTeX CVs to fit a strict 1-page budget without inventing facts, and track your recruitment pipeline.

---

## 🌟 Key Features

1. **Multi-Monitor Job Scraping:** Configures and runs multiple concurrent, independent job monitors to scrape RSS feeds based on distinct keywords, locations, languages, and remote options.
2. **Dynamic In-App Preferences**: Modify system-wide search keywords and target countries directly within the web app settings. This updates the config file on the fly and hot-reloads the active agents.
3. **Match Score Assessment:** Evaluates JDs against your baseline resume, calculating a weighted match percentage, identifying transferable skills, and proposing bridges for missing gaps.
4. **PDF Baseline Ingestion:** Ingests baseline resumes in either LaTeX (`.tex`) or PDF (`.pdf`) format. If PDF is uploaded, it uses `pypdf` extraction and Gemini to structure the profile.
5. **Robust Playwright PDF Generation:** Personalizes and compiles tailored resumes to LaTeX or PDF. If local LaTeX compilers (like `tectonic` or `pdflatex`) are not detected on the host system, the backend automatically uses Playwright headless Chromium to render and print a single-page PDF.
6. **Unified "Tailor & Apply" Wizard:** Guides you through match scores, targeted gap-bridging interview questions, resume tailoring, and pipeline dashboard confirmation in a single wizard.
7. **Unified Developer Plan:** Consolidates all registered skill gaps across jobs into a learning action plan and roadmap.
8. **Tracker Kanban Dashboard:** Visual tracker dashboard to track status (Applied, Interviewing, Offer, Rejected) synchronized directly with your database and an exportable [applications.md](file:///c:/Users/a518028/OneDrive%20-%20Volvo%20Group/repos/learner/applications.md) log.

---

## 🚀 How to Run Locally

Anyone can run this project locally on their machine.

### Path A: Run with Docker Compose (Recommended - Zero Setup)
Docker packages everything (including the compilers and dependencies) so you don't have to install anything on your host machine.

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/).
2. Set your API Key in your terminal:
   * **Windows (PowerShell):** `$env:GEMINI_API_KEY="your-key"`
   * **Mac/Linux:** `export GEMINI_API_KEY="your-key"`
3. Start the application:
   ```bash
   docker compose up --build
   ```
4. Open `http://localhost:8000` in your web browser.

### Path B: One-Click Local Run (Windows / macOS / Linux)
If you already have Python 3 and Node.js installed on your host machine:

* **Windows:** Double-click the **`run.bat`** file at the root.
* **Mac/Linux:** Open your terminal and run:
  ```bash
  python run.py
  ```

This launcher will automatically set up Python dependencies, compile the frontend assets, launch the FastAPI server, and open your default web browser pointing to the app.

---

## 🛠️ Developer & Agent Git Automation

To maintain a clean repository and release structure, all developers and AI agents **MUST** follow our Git branch workflow using the automated CLI helper:

* **Sync Codebase** (run at startup to pop local changes, fetch main changes, merge them, and pop local changes back):
  ```bash
  python scripts/git_helper.py sync
  ```
* **Create Task Branch** (isolates coding to topic branches):
  ```bash
  python scripts/git_helper.py create-branch <task-name>
  ```
* **Verify & Commit** (validates conventional commit formatting, runs the 14-test backend integration suite, stages changes, and commits):
  ```bash
  python scripts/git_helper.py commit "feat: your conventional message"
  ```
* **Merge to Main**:
  ```bash
  python scripts/git_helper.py merge-main
  ```
* **Bump Version Release** (bumps version in source, builds frontend production assets, commits build artifacts, and tags release):
  ```bash
  python scripts/git_helper.py bump [patch|minor|major]
  ```

For full details, please refer to the [AI Agent Git & Versioning Rules](file:///c:/Users/a518028/OneDrive%20-%20Volvo%20Group/repos/learner/AGENT_GIT_RULES.md) document.

---

## ☁️ Deploying Online for Free (Hugging Face Spaces)

You can host this project 24/7 in the cloud for free using Hugging Face Spaces:

1. Create a free account on [Hugging Face](https://huggingface.co/).
2. Create a new **Space**, select **Docker** as the SDK, and choose the **Blank** template (set visibility to **Private** to protect your resume details).
3. Run the automated deployment helper:
   ```bash
   python deploy_hf.py
   ```
4. Input your username, Space name, and Hugging Face Write Token. It will configure Git and push the code.
5. In your Space **Settings**, add a Secret variable named `GEMINI_API_KEY` containing your API key. The Space will build and deploy!

---

## ⚙️ Configuration

You can customize your global search keywords, target locations, languages, and working culture context in the **`config.yaml`** file. 

*Alternatively, you can edit and save all of these preferences directly from the web application by navigating to the **System Settings** tab and updating the **Global System Preferences** section.*

Example `config.yaml` layout:

```yaml
search:
  keywords:
    - "Python Engineer"
    - "AI Engineer"
  countries:
    - "Sweden"
  remote: true
  languages:
    - "English"
  citizenship_restrictions:
    - "EU Citizen"
```

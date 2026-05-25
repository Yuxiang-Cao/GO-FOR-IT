# 🤖 Job Monitor & CV Tailor Agent System

An automated multi-agent system designed to monitor job boards, evaluate job descriptions (JDs), conduct clarifying interviews (`/grill-me`), customize LaTeX CVs to fit a strict 1-page budget without inventing facts, and track your recruitment pipeline.

---

## 🌟 Key Features

1. **Job Monitoring:** Scrapes RSS and job feeds (like WeWorkRemotely and RemoteOK) based on your custom configuration (keywords, location, citizenship, and language filters).
2. **Match Score Assessment:** Evaluates JDs against your baseline resume, calculating a weighted match percentage and identifying transferable skills.
3. **Interactive Grilling (/grill-me):** Conducts a conversational interview to extract relevant accomplishments, technical details, or soft skills not yet listed on your CV.
4. **1-Page LaTeX Tailoring:** Modifies your LaTeX source code to highlight target qualifications, automatically compressing lists and shrinking margins to fit a strict 1-page layout.
5. **Unified Dashboard:** Direct kanban tracker to follow your application statuses (Applied, Interviewing, Offer, Rejected).
6. **Unified Developer Plan:** Consolidates all skill gaps into a structured learning roadmap.

---

## 🚀 How to Run Locally

Anyone can access and run this project locally on their machine.

### Path A: Run with Docker Compose (Recommended - No Installation Needed)
If you want to compile resumes to PDF, you need a LaTeX compiler. Docker packages everything (including the compiler) so you don't have to install anything on your host machine.

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/).
2. Set your API Key in your terminal:
   - **Windows (PowerShell):** `$env:GEMINI_API_KEY="your-key"`
   - **Mac/Linux:** `export GEMINI_API_KEY="your-key"`
3. Start the application:
   ```bash
   docker compose up --build
   ```
4. Open `http://localhost:8000` in your web browser.

### Path B: One-Click Local Run (Windows / macOS / Linux)
If you already have Python 3 and Node.js installed, you can run the app directly:

* **Windows:** Double-click the **`run.bat`** file at the root.
* **Mac/Linux:** Open your terminal and run:
  ```bash
  python run.py
  ```

This script will set up python dependencies, compile the frontend assets, start the FastAPI server, and open your browser automatically.

---

## ☁️ Deploying Online for Free (Hugging Face Spaces)

You can host this project 24/7 in the cloud for free using Hugging Face Spaces:

1. Create a free account on [Hugging Face](https://huggingface.co/).
2. Create a new **Space**, select **Docker** as the SDK, and choose the **Blank** template (make it Private so your CV details are secure).
3. Run the automated deployment script:
   ```bash
   python deploy_hf.py
   ```
4. Input your username, Space name, and Hugging Face Write Token. It will configure Git and push the code.
5. In your Space **Settings**, add a Secret variable named `GEMINI_API_KEY` containing your API key. The Space will build and deploy!

---

## 🛠️ Configuration

You can customize your global search keywords, target locations, languages, and working culture context in the **`config.yaml`** file.

*Alternatively, you can edit and save all of these preferences directly from the web application by navigating to the **System Settings** tab and updating the **Global System Preferences** section. This dynamically updates `config.yaml` and reloads configurations for active agents.*

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

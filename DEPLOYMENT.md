# Deployment and Runner Guide - Job Monitor & CV Tailor

This guide covers running the application locally (with or without Docker) and deploying it 100% for free to **Hugging Face Spaces**.

---

## 1. Quick Start: Local Run (No Docker)
You can run the entire application using Python. If you have Node.js/NPM installed, the script will compile the Vite frontend for you.

### Prerequisites:
- Python 3.10+ installed
- Node.js (v18+) and NPM installed (only required to build the frontend once; otherwise, the pre-built `frontend/dist` is served)

### Instructions:
1. Set your Gemini API Key in your terminal environment:
   ```powershell
   # On Windows (PowerShell)
   $env:GEMINI_API_KEY="your-api-key-here"

   # On Linux/macOS
   export GEMINI_API_KEY="your-api-key-here"
   ```
2. Start the local server:
   ```bash
   python run.py
   ```
3. The script will prepare dependencies, build the frontend if missing, start FastAPI on port 8000, and automatically open `http://localhost:8000` in your web browser.

---

## 2. Local Run: Containerized (Docker Compose)
Running via Docker is the **recommended** way if you do not want to install LaTeX compilers (like `pdflatex` or `tectonic`) on your local host machine. Docker will package the entire LaTeX compile chain inside the container.

### Prerequisites:
- Docker Desktop installed and running

### Instructions:
1. Set your Gemini API Key in your shell.
2. Build and start the container:
   ```bash
   docker compose up --build
   ```
3. Navigate to `http://localhost:8000` in your browser.
4. Your SQLite database (`data/database.db`) and compiled resumes (`data/output/`) will be saved in your local directory via Docker volumes, so your data will persist across restarts.

---

## 3. Deploying 100% For Free on Hugging Face Spaces
Hugging Face Spaces is a cloud hosting provider that allows running custom Dockerfiles 24/7 for free.

### Setup Instructions:
1. Create a free account at [Hugging Face](https://huggingface.co/).
2. Create a new **Space**:
   - Go to your profile -> **New Space**.
   - Enter a **Space Name** (e.g. `my-job-agent`).
   - Select **Docker** as the SDK.
   - Choose the **Blank** template.
   - Set Space visibility to **Public** or **Private** (recommended Private so your CV details are not publicly visible).
   - Click **Create Space**.
3. Set your API Key secret:
   - In your Space, navigate to the **Settings** tab.
   - Scroll down to **Variables and secrets**.
   - Click **New secret**.
   - Key: `GEMINI_API_KEY`
   - Value: `your-api-key-here`
4. Deploy the repository:
   - Clone the Space repository locally using git or copy the files directly using the Hugging Face Web interface.
   - Copy all files from this directory (`src/`, `frontend/`, `Dockerfile`, `config.yaml`, `requirements.txt`) into the Space repository.
   - Commit and push to Hugging Face:
     ```bash
     git add .
     git commit -m "Deploy Job Monitor & CV Tailor application"
     git push
     ```
5. Hugging Face will automatically detect the `Dockerfile`, build the React frontend, set up the LaTeX compiler, and deploy your application online for free! You and your friends can access it via the Space URL.

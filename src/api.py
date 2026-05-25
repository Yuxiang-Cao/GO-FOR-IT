import os
import json
import shutil
import yaml
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.database import JobDatabase
from src.utils.latex_parser import LatexCVParser
from src.utils.latex_compiler import LatexCompiler
from src.agents.job_monitor import JobMonitor
from src.agents.analyzer import JDAnalyzer
from src.agents.cv_tailor import CVTailor
from src.agents.tracker import AppTracker
from src.version import __version__

# FastAPI app setup moved below backend references instantiation to support lifespan database references

# Define paths relative to this file's folder to prevent directory mismatch errors
src_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(src_dir)

db_path = os.path.join(project_dir, "data", "database.db")
resume_json_path = os.path.join(project_dir, "data", "resume_base.json")
base_cv_path = os.path.join(project_dir, "data", "cv.tex")
output_dir = os.path.join(project_dir, "data", "output")
config_path = os.path.join(project_dir, "config.yaml")

# Ensure folders exist
os.makedirs(os.path.dirname(db_path), exist_ok=True)
os.makedirs(output_dir, exist_ok=True)

# Setup backend references
db = JobDatabase(db_path)
parser = LatexCVParser()
compiler = LatexCompiler()
monitor = JobMonitor(config_path=config_path, db_path=db_path)
analyzer = JDAnalyzer(config_path=config_path, db_path=db_path)
tailor = CVTailor(config_path=config_path)
tracker = AppTracker(db_path=db_path, dashboard_path=os.path.join(project_dir, "applications.md"))

from contextlib import asynccontextmanager
import asyncio

# Background loop task handle
background_monitor_task = None

async def run_monitors_background_loop():
    # Wait 10 seconds for DB initialization
    await asyncio.sleep(10)
    while True:
        try:
            active_monitors = db.get_active_monitors()
            print(f"Background Job Monitor: Running {len(active_monitors)} active monitors...")
            for mon in active_monitors:
                try:
                    keywords_list = json.loads(mon["keywords"])
                    locations_list = json.loads(mon["locations"])
                    search_cfg = {
                        "keywords": keywords_list,
                        "countries": locations_list,
                        "cities": [],
                        "remote": bool(mon["remote"]),
                        "languages": ["English", "Swedish"],
                        "citizenship_restrictions": []
                    }
                    print(f"Running background scraper for monitor '{mon['name']}'...")
                    monitor.monitor_and_store(search_cfg=search_cfg)
                except Exception as mon_err:
                    print(f"Error executing background monitor '{mon['name']}': {mon_err}")
        except Exception as e:
            print(f"Error in background monitors loop: {e}")
        await asyncio.sleep(300)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global background_monitor_task
    background_monitor_task = asyncio.create_task(run_monitors_background_loop())
    yield
    if background_monitor_task:
        background_monitor_task.cancel()
        try:
            await background_monitor_task
        except asyncio.CancelledError:
            pass

app = FastAPI(title="Job Monitor & CV Tailor API", lifespan=lifespan)

# Configure CORS for Vite dev server (usually localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for local dev simplicity
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount outputs as static files so PDF can be displayed/downloaded
app.mount("/output", StaticFiles(directory=output_dir), name="output")

# Models
class AnswersModel(BaseModel):
    answers: List[dict] # List of {"question": str, "answer": str, "category": Optional[str]}

class ManualJobModel(BaseModel):
    company: str
    title: str
    jd_text: str
    location: Optional[str] = "Remote"

class JobStatusModel(BaseModel):
    status: str
    notes: Optional[str] = ""

class ConfigModel(BaseModel):
    search: Optional[dict] = None
    culture: Optional[dict] = None

class MonitorModel(BaseModel):
    name: str
    keywords: List[str]
    locations: List[str]
    remote: bool
    active: Optional[bool] = True

class ExtractModel(BaseModel):
    text: str

# API Endpoints
@app.get("/api/config")
def get_config():
    """Returns the current search and system configuration."""
    if not os.path.exists(config_path):
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

@app.post("/api/config")
def update_config(payload: ConfigModel):
    """Updates the config.yaml file and reloads configurations in active agents."""
    existing = {}
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            existing = yaml.safe_load(f) or {}

    if payload.search:
        existing["search"] = payload.search
    if payload.culture:
        existing["culture"] = payload.culture

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(existing, f, default_flow_style=False)

    # Reload configs in active agents
    monitor.config = monitor._load_config()
    analyzer.config = analyzer._load_config()
    tailor.config = tailor._load_config()

    return {"detail": "Configuration updated successfully.", "config": existing}

@app.get("/api/status")
def get_status():
    """Checks if the baseline resume has been uploaded and set up."""
    cv_exists = os.path.exists(resume_json_path)
    cv_details = None
    if cv_exists:
        try:
            cv_details = parser.load_json(resume_json_path)
        except Exception:
            pass
            
    return {
        "onboarded": cv_exists,
        "cv_details": cv_details,
        "has_compiler": compiler.compiler is not None,
        "compiler_detected": compiler.compiler,
        "version": __version__
    }

@app.post("/api/upload-cv")
async def upload_cv(file: UploadFile = File(...)):
    """Receives baseline LaTeX (.tex) or PDF (.pdf) CV, parses it, and returns onboarding profile questions."""
    filename = file.filename.lower()
    if not (filename.endswith(".tex") or filename.endswith(".pdf")):
        raise HTTPException(status_code=400, detail="Only LaTeX (.tex) and PDF (.pdf) files are supported.")
        
    if filename.endswith(".tex"):
        # Save base file
        with open(base_cv_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Parse LaTeX
        try:
            with open(base_cv_path, "r", encoding="utf-8") as f:
                latex_content = f.read()
            cv_json = parser.parse(latex_content)
            parser.save_json(cv_json, resume_json_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to parse LaTeX file: {e}")
    else:
        # Save baseline PDF
        pdf_path = os.path.join(project_dir, "data", "cv.pdf")
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Parse PDF using pypdf
        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            raw_text = ""
            for page in reader.pages:
                text_page = page.extract_text()
                if text_page:
                    raw_text += text_page + "\n"
            
            if not raw_text.strip():
                raise ValueError("PDF contains no readable text extract. Make sure it is not scanned/image-only.")
                
            # Structure text using Gemini
            cv_json = analyzer.structure_raw_cv_text(raw_text)
            parser.save_json(cv_json, resume_json_path)
            
            # Rebuild a baseline LaTeX CV for future tailoring outputs
            rebuilt_latex = parser.rebuild(cv_json)
            with open(base_cv_path, "w", encoding="utf-8") as f:
                f.write(rebuilt_latex)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to parse and structure PDF CV: {e}")
            
    # Generate general profile questions
    questions = analyzer.generate_general_profiling_questions(cv_json)
    return {
        "detail": "CV parsed successfully",
        "questions": questions
    }

@app.post("/api/onboard/answers")
def submit_onboard_answers(payload: AnswersModel):
    """Saves first-time general profiling answers to database."""
    for item in payload.answers:
        q = item.get("question")
        a = item.get("answer")
        category = item.get("category", "general")
        if q and a and a.lower() != "skip":
            db.add_qa(q, a, category)
    return {"status": "Onboarding answers saved successfully."}

@app.post("/api/onboard/skip")
def skip_onboarding():
    """Skips onboarding by creating a default empty CV profile."""
    empty_cv = {
        "preamble": "\\documentclass{article}\n\\begin{document}\n\\end{document}",
        "sections": []
    }
    with open(resume_json_path, "w", encoding="utf-8") as f:
        json.dump(empty_cv, f)
    with open(base_cv_path, "w", encoding="utf-8") as f:
        f.write("\\documentclass{article}\n\\begin{document}\n\\end{document}\n")
    return {"detail": "Onboarding skipped. Clean dashboard activated."}


@app.get("/api/jobs")
def get_jobs():
    """Lists all stored jobs."""
    cursor = db.conn.cursor()
    cursor.execute("SELECT * FROM jobs ORDER BY created_at DESC")
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

@app.post("/api/jobs/monitor")
def run_job_monitor():
    """Triggers job monitoring feed scrape using active database monitors."""
    active_monitors = db.get_active_monitors()
    new_jobs = []
    
    if not active_monitors:
        # Fall back to default config settings
        new_jobs = monitor.monitor_and_store()
    else:
        seen_job_ids = set()
        for mon in active_monitors:
            try:
                keywords_list = json.loads(mon["keywords"])
                locations_list = json.loads(mon["locations"])
                search_cfg = {
                    "keywords": keywords_list,
                    "countries": locations_list,
                    "cities": [],
                    "remote": bool(mon["remote"]),
                    "languages": ["English", "Swedish"],
                    "citizenship_restrictions": []
                }
                jobs = monitor.monitor_and_store(search_cfg=search_cfg)
                for j in jobs:
                    if j["id"] not in seen_job_ids:
                        seen_job_ids.add(j["id"])
                        new_jobs.append(j)
            except Exception as mon_err:
                print(f"Error executing monitor '{mon['name']}': {mon_err}")
                
    return {"detail": f"Scrape complete. Discovered {len(new_jobs)} jobs.", "new_jobs": new_jobs}

@app.post("/api/jobs/manual")
def add_job_manually(payload: ManualJobModel):
    """Manually adds a job description."""
    job_id = db.add_job(payload.company, payload.title, payload.jd_text, location=payload.location)
    return {"job_id": job_id, "detail": "Job added successfully."}

@app.post("/api/jobs/{job_id}/analyze")
def analyze_job(job_id: str):
    """Runs match score and skill gap analysis on target job description."""
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
        
    if not os.path.exists(resume_json_path):
        raise HTTPException(status_code=400, detail="Onboard baseline CV first.")
        
    cv_json = parser.load_json(resume_json_path)
    analysis = analyzer.analyze_jd(job["jd_text"], cv_json)
    
    score = analysis.get("confidence_score", 0.0)
    db.update_job_analysis(job_id, score, json.dumps(analysis))
    
    return {
        "job_id": job_id,
        "score": score,
        "analysis": analysis
    }

@app.get("/api/jobs/{job_id}/questions")
def get_job_questions(job_id: str):
    """Fetches Dynamic /grill-me questions to bridge skill gaps."""
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
        
    cv_json = parser.load_json(resume_json_path)
    
    # Load analysis or generate it if missing
    analysis = None
    if job["match_report"]:
        analysis = json.loads(job["match_report"])
    else:
        analysis = analyzer.analyze_jd(job["jd_text"], cv_json)
        db.update_job_analysis(job_id, analysis.get("confidence_score", 0.0), json.dumps(analysis))
        
    questions = analyzer.generate_interview_questions(job["jd_text"], cv_json, analysis)
    return {"questions": questions}

@app.post("/api/jobs/{job_id}/answers")
def submit_job_answers(job_id: str, payload: AnswersModel):
    """Registers answers to targeted questions for specific job."""
    for item in payload.answers:
        q = item.get("question")
        a = item.get("answer")
        category = item.get("category", "target")
        if q and a and a.lower() != "skip":
            db.add_qa(q, a, category)
            
    # Mark job status to grilled
    db.update_job_status(job_id, "grilled")
    return {"detail": "Answers submitted. Ready for tailoring."}

@app.post("/api/jobs/{job_id}/tailor")
def tailor_cv(job_id: str):
    """Tailors CV JSON, rebuilds LaTeX, compiles to PDF, handles page limits."""
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
        
    if not os.path.exists(resume_json_path):
        raise HTTPException(status_code=400, detail="Onboard baseline CV first.")
        
    cv_json = parser.load_json(resume_json_path)
    
    # Gather Q&A history context from database to guide personalization
    qa_history = db.get_all_qa()
    
    print("Running tailor LLM service...")
    tailored_cv_json = tailor.tailor_cv_json(cv_json, job["jd_text"], qa_history)
    tailored_latex = parser.rebuild(tailored_cv_json)
    
    print("Checking page budget layout constraints...")
    optimized_latex = tailor.optimize_page_budget(tailored_latex)
    
    # Save the output files
    sanitized_company = job["company"].lower().replace(" ", "_")
    sanitized_title = job["title"].lower().replace(" ", "_")
    file_prefix = f"cv_{sanitized_company}_{sanitized_title}"
    
    tex_out_path = f"data/output/{file_prefix}.tex"
    pdf_out_path = f"data/output/{file_prefix}.pdf"
    
    with open(tex_out_path, "w", encoding="utf-8") as f:
        f.write(optimized_latex)
        
    # Compile
    try:
        compiled_pdf = compiler.compile(tex_out_path, output_dir="data/output")
        pdf_download_url = f"/output/{file_prefix}.pdf"
        tex_download_url = f"/output/{file_prefix}.tex"
    except Exception as e:
        print(f"LaTeX compilation failed: {e}. Falling back to Playwright HTML-to-PDF...")
        try:
            pdf_path = os.path.join(project_dir, "data", "output", f"{file_prefix}.pdf")
            compiler.compile_html_to_pdf(tailored_cv_json, pdf_path)
            pdf_download_url = f"/output/{file_prefix}.pdf"
            tex_download_url = f"/output/{file_prefix}.tex"
        except Exception as playwright_err:
            print(f"Playwright compilation also failed: {playwright_err}")
            pdf_download_url = None
            tex_download_url = f"/output/{file_prefix}.tex"
        
    # Update job state
    db.update_job_status(job_id, "tailored")
    
    return {
        "status": "tailored",
        "tex_file": tex_download_url,
        "pdf_file": pdf_download_url,
        "has_pdf": pdf_download_url is not None
    }

@app.post("/api/jobs/{job_id}/apply")
def apply_job(job_id: str, payload: JobStatusModel):
    """Logs applied job in database, updating applications.md."""
    # Build file paths
    job = db.get_job(job_id)
    sanitized_company = job["company"].lower().replace(" ", "_")
    sanitized_title = job["title"].lower().replace(" ", "_")
    pdf_path = f"data/output/cv_{sanitized_company}_{sanitized_title}.pdf"
    
    if not os.path.exists(pdf_path):
        pdf_path = None
        
    tracker.log_application(job_id, pdf_path, payload.notes)
    return {"detail": "Logged application successfully."}

@app.get("/api/tracker")
def get_tracker():
    """Returns active applications dashboard records."""
    return db.get_applications()

@app.put("/api/tracker/{job_id}")
def update_tracker_status(job_id: str, payload: JobStatusModel):
    """Updates application pipeline state."""
    db.update_application_status(job_id, payload.status)
    tracker.generate_markdown_dashboard()
    return {"detail": "Status updated successfully."}

@app.get("/api/devplan")
def get_development_plan():
    """Aggregates skill gaps from database and generates unified training roadmap."""
    cursor = db.conn.cursor()
    cursor.execute("SELECT match_report FROM jobs WHERE match_report IS NOT NULL")
    rows = cursor.fetchall()
    
    all_missing = set()
    for row in rows:
        try:
            report = json.loads(row["match_report"])
            all_missing.update(report.get("skills_missing", []))
        except Exception:
            pass
            
    if not all_missing:
        return {"missing_skills": [], "plan": []}
        
    plan = analyzer.generate_development_plan(list(all_missing))
    return {
        "missing_skills": list(all_missing),
        "plan": plan
    }

@app.get("/api/monitors")
def get_monitors():
    monitors = db.get_monitors()
    deserialized = []
    for m in monitors:
        row = dict(m)
        try:
            row["keywords"] = json.loads(row["keywords"])
        except Exception:
            row["keywords"] = []
        try:
            row["locations"] = json.loads(row["locations"])
        except Exception:
            row["locations"] = []
        row["remote"] = bool(row["remote"])
        row["active"] = bool(row["active"])
        deserialized.append(row)
    return deserialized

@app.post("/api/monitors")
def add_monitor(payload: MonitorModel):
    monitor_id = db.add_monitor(
        name=payload.name,
        keywords=payload.keywords,
        locations=payload.locations,
        remote=payload.remote,
        active=payload.active
    )
    return {"monitor_id": monitor_id, "detail": "Monitor created successfully."}

@app.put("/api/monitors/{monitor_id}")
def update_monitor(monitor_id: str, payload: MonitorModel):
    db.update_monitor(
        monitor_id=monitor_id,
        name=payload.name,
        keywords=payload.keywords,
        locations=payload.locations,
        remote=payload.remote,
        active=payload.active
    )
    return {"detail": "Monitor updated successfully."}

@app.delete("/api/monitors/{monitor_id}")
def delete_monitor(monitor_id: str):
    db.delete_monitor(monitor_id)
    return {"detail": "Monitor deleted successfully."}

@app.post("/api/monitors/extract")
def extract_preferences(payload: ExtractModel):
    extracted = analyzer.extract_monitor_preferences(payload.text)
    return extracted
# Serve compiled frontend static files if they exist
frontend_dist_path = os.path.join(project_dir, "frontend", "dist")
if os.path.exists(frontend_dist_path):
    app.mount("/", StaticFiles(directory=frontend_dist_path, html=True), name="frontend")


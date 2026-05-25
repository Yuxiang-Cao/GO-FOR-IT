import os
import json
import yaml
from src.database import JobDatabase
from src.utils.latex_parser import LatexCVParser
from src.utils.latex_compiler import LatexCompiler
from src.agents.job_monitor import JobMonitor
from src.agents.analyzer import JDAnalyzer
from src.agents.cv_tailor import CVTailor
from src.agents.tracker import AppTracker

class JobAgentCLI:
    def __init__(self):
        self.db_path = "data/database.db"
        self.db = JobDatabase(self.db_path)
        self.parser = LatexCVParser()
        self.compiler = LatexCompiler()
        self.monitor = JobMonitor(db_path=self.db_path)
        self.analyzer = JDAnalyzer(db_path=self.db_path)
        self.tailor = CVTailor()
        self.tracker = AppTracker(db_path=self.db_path)
        
        # Load config to get template location
        with open("config.yaml", "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
            
        self.base_cv_path = self.config.get("latex", {}).get("base_cv_path", "cv.tex")
        self.resume_json_path = "data/resume_base.json"

    def run(self):
        print("====================================================")
        print("   🤖 JOB MONITOR & CV TAILOR AGENT SYSTEM 🤖       ")
        print("====================================================")
        
        # Self-aligning check: ensure baseline CV exists and is parsed
        if not os.path.exists(self.resume_json_path):
            print("\n[Onboarding] Baseline CV JSON not found. Initializing setup...")
            self._onboard_user()

        while True:
            print("\n--- Main Menu ---")
            print("1. Process a New Job Description (JD)")
            print("2. Run Job Monitor (Fetch & Filter Jobs)")
            print("3. View Applications & Update Status")
            print("4. View Consolidated Career Development Plan")
            print("5. Re-run Onboarding (/grill-me Profile Setup)")
            print("6. Exit")
            
            choice = input("\nEnter choice (1-6): ").strip()
            
            if choice == "1":
                self._process_new_jd()
            elif choice == "2":
                self._run_job_monitor()
            elif choice == "3":
                self._view_applications()
            elif choice == "4":
                self._view_development_plan()
            elif choice == "5":
                self._onboard_user()
            elif choice == "6":
                print("Goodbye!")
                break
            else:
                print("Invalid choice, please select 1-6.")

    def _onboard_user(self):
        """Initial onboarding: parses the base CV and runs general /grill-me."""
        print(f"\nLooking for base CV at: {self.base_cv_path}")
        if not os.path.exists(self.base_cv_path):
            print(f"ERROR: Base LaTeX CV not found at {self.base_cv_path}")
            # Create a basic sample cv.tex so the user has something to start with
            self._create_sample_cv()
            
        with open(self.base_cv_path, "r", encoding="utf-8") as f:
            latex_content = f.read()
            
        print("Parsing LaTeX CV into intermediate JSON format...")
        cv_json = self.parser.parse(latex_content)
        self.parser.save_json(cv_json, self.resume_json_path)
        print(f"Saved parsed CV to {self.resume_json_path}")
        
        # General /grill-me profile questions
        print("\nStarting general profiling (/grill-me onboarding)...")
        questions = self.analyzer.generate_general_profiling_questions(cv_json)
        
        print("\nI will ask you a few questions to understand experience not in your CV.")
        print("Type 'skip' or press Enter on an empty line to bypass any question.")
        
        for idx, q in enumerate(questions):
            q_text = q["question"]
            print(f"\n[{idx+1}/{len(questions)}] {q_text}")
            answer = input("Your answer: ").strip()
            if answer and answer.lower() != "skip":
                self.db.add_qa(q_text, answer, category=q.get("category", "general"))
                print("Recorded.")
            else:
                print("Skipped.")
                
        print("\nOnboarding completed!")

    def _create_sample_cv(self):
        """Generates a sample LaTeX resume if none exists, to facilitate instant testability."""
        print("Creating a sample cv.tex template for testing...")
        sample = r"""\documentclass[10pt]{article}
\usepackage[margin=0.75in]{geometry}
\usepackage{titlesec}
\usepackage{hyperref}

\titleformat{\section}{\large\bfseries}{}{0em}{}[\titlerule]
\titlespacing{\section}{0pt}{10pt}{5pt}

\begin{document}
\pagestyle{empty}

\begin{center}
    {\LARGE \textbf{Alex Dev}} \\
    alex@example.com | +46 70 123 45 67 | Gothenburg, Sweden
\end{center}

\section{Summary}
Experienced Python developer specializing in building REST APIs and automation scripts. Passionate about software architecture.

\section{Experience}
\textbf{Software Engineer} at Tech Solutions (2023 - Present)
\begin{itemize}
    \item Developed Python services using Flask and PostgreSQL.
    \item Maintained unit tests and automated test runners.
    \item Collaborated in Agile Scrum teams to deliver sprints.
\end{itemize}

\textbf{Junior Developer} at CodeCorp (2021 - 2023)
\begin{itemize}
    \item Fixed bugs in JavaScript/Node.js web applications.
    \item Set up Git workflows and deployment steps.
\end{itemize}

\section{Skills}
\begin{itemize}
    \item Languages: Python, JavaScript, SQL, HTML/CSS
    \item Tools: Git, VS Code, Linux, PostgreSQL
\end{itemize}

\end{document}
"""
        with open(self.base_cv_path, "w", encoding="utf-8") as f:
            f.write(sample)
        print("Sample cv.tex created successfully!")

    def _process_new_jd(self):
        print("\n--- Process New Job Description ---")
        company = input("Company Name: ").strip()
        title = input("Job Title: ").strip()
        location = input("Location (e.g. Gothenburg / Remote): ").strip()
        print("Enter/Paste the Job Description text (Ctrl+Z or Ctrl+D on empty line to finish):")
        
        jd_lines = []
        while True:
            try:
                line = input()
                jd_lines.append(line)
            except EOFError:
                break
        
        jd_text = "\n".join(jd_lines).strip()
        if not jd_text:
            print("Job description cannot be empty.")
            return
            
        # Add job to DB
        job_id = self.db.add_job(company, title, jd_text, location=location)
        
        # Load CV
        cv_json = self.parser.load_json(self.resume_json_path)
        
        # Analyze JD
        print("\nAnalyzing JD and comparing to your CV...")
        analysis = self.analyzer.analyze_jd(jd_text, cv_json)
        score = analysis.get("confidence_score", 0.0)
        
        print(f"\nInitial Match Confidence: {score:.1f}/100")
        print("\nSkills Matched:", ", ".join(analysis.get("skills_matched", [])))
        print("Skills Missing:", ", ".join(analysis.get("skills_missing", [])))
        
        # Dynamic /grill-me loop
        print("\nStarting target interview session to bridge skill gaps...")
        questions = self.analyzer.generate_interview_questions(jd_text, cv_json, analysis)
        
        qa_context = []
        if questions:
            for idx, q in enumerate(questions):
                q_text = q["question"]
                print(f"\n[{idx+1}/{len(questions)}] {q_text}")
                ans = input("Your answer (or press enter/type 'skip'): ").strip()
                if ans and ans.lower() != "skip":
                    self.db.add_qa(q_text, ans, category=q.get("skill_target"))
                    qa_context.append({"question": q_text, "answer": ans})
                    print("Saved.")
                else:
                    print("Skipped.")
        else:
            print("No new questions needed! Your profile context is complete.")

        # Tailor CV
        print("\nGenerating tailored CV content...")
        tailored_cv_json = self.tailor.tailor_cv_json(cv_json, jd_text, qa_context)
        
        # Rebuild LaTeX
        print("Reassembling LaTeX layout...")
        tailored_latex = self.parser.rebuild(tailored_cv_json)
        
        # Compile and check page count
        print("Validating layout & page count...")
        optimized_latex = self.tailor.optimize_page_budget(tailored_latex)
        
        # Save tailored LaTeX file
        tailored_filename = f"cv_{company.lower().replace(' ', '_')}_{title.lower().replace(' ', '_')}.tex"
        with open(tailored_filename, "w", encoding="utf-8") as f:
            f.write(optimized_latex)
        print(f"\nTailored LaTeX saved to: {tailored_filename}")
        
        # Compile final PDF
        try:
            pdf_path = self.compiler.compile(tailored_filename)
            print(f"Tailored PDF compiled successfully at: {pdf_path}")
        except Exception as e:
            pdf_path = None
            print(f"Could not compile PDF automatically: {e}")
            
        # Update job database analysis
        self.db.update_job_analysis(job_id, score, json.dumps(analysis))
        
        # Confirm Apply Loop
        confirm = input("\nHave you applied to this job? (yes/no): ").strip().lower()
        if confirm == "yes" or confirm == "y":
            notes = input("Any notes? (e.g. 'Sent via LinkedIn'): ").strip()
            self.tracker.log_application(job_id, pdf_path, notes)
            print("Application logged.")
        else:
            self.db.update_job_status(job_id, "tailored")
            print("Job saved to DB with status 'tailored'.")

    def _run_job_monitor(self):
        print("\nFetching latest remote software engineering jobs...")
        # StackOverflow or custom WWR feed
        new_jobs = self.monitor.monitor_and_store()
        if not new_jobs:
            print("No new matching jobs found matching your filters.")
        else:
            print(f"\nFound {len(new_jobs)} new jobs:")
            for j in new_jobs:
                print(f"- **{j['company']}**: {j['title']} ({j['location']})")

    def _view_applications(self):
        print("\n--- Current Applications Tracker ---")
        apps = self.db.get_applications()
        if not apps:
            print("No applications tracked yet.")
            return
            
        for idx, app in enumerate(apps):
            print(f"\n[{idx+1}] {app['company']} - {app['title']}")
            print(f"    Applied Date: {app['applied_date']}")
            print(f"    Status: {app['status']}")
            print(f"    CV: {app['tailored_cv_path']}")
            print(f"    Notes: {app['notes']}")
            
        manage = input("\nWould you like to update a status? (yes/no): ").strip().lower()
        if manage in ["yes", "y"]:
            try:
                num = int(input("Enter application index number: ").strip()) - 1
                if 0 <= num < len(apps):
                    target_app = apps[num]
                    new_status = input("Enter new status (applied, interviewing, offer, rejected): ").strip().lower()
                    if new_status in ["applied", "interviewing", "offer", "rejected"]:
                        self.tracker.update_status(target_app["job_id"], new_status)
                    else:
                        print("Invalid status.")
                else:
                    print("Invalid index.")
            except ValueError:
                print("Please enter a valid number.")

    def _view_development_plan(self):
        print("\nConsolidating missing skills across all jobs...")
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT match_report FROM jobs WHERE match_report IS NOT NULL")
        rows = cursor.fetchall()
        
        all_missing = set()
        for row in rows:
            report = json.loads(row["match_report"])
            all_missing.update(report.get("skills_missing", []))
            
        if not all_missing:
            print("No missing skills registered in database. Keep applying!")
            return
            
        print("\nAggregated Skill Gaps:", ", ".join(all_missing))
        print("Generating Career Development Plan...")
        plan = self.analyzer.generate_development_plan(list(all_missing))
        
        print("\n=== Career Development & Learning Action Items ===")
        for idx, item in enumerate(plan):
            print(f"\n{idx+1}. Skill: {item['skill']} ({item['difficulty']})")
            print(f"   Recommended Action: {item['action']}")

if __name__ == "__main__":
    cli = JobAgentCLI()
    cli.run()

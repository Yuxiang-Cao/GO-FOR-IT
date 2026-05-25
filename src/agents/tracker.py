import os
from src.database import JobDatabase

class AppTracker:
    def __init__(self, db_path="data/database.db", dashboard_path="applications.md"):
        self.db = JobDatabase(db_path)
        self.dashboard_path = dashboard_path

    def log_application(self, job_id, tailored_cv_path=None, notes=None):
        """Register application in the database and update the Markdown dashboard."""
        self.db.add_application(job_id, tailored_cv_path, notes)
        self.generate_markdown_dashboard()
        print(f"Logged application for Job ID {job_id} successfully.")

    def update_status(self, job_id, status):
        """Update interview/application status."""
        self.db.update_application_status(job_id, status)
        self.generate_markdown_dashboard()
        print(f"Updated status for Job ID {job_id} to '{status}'.")

    def generate_markdown_dashboard(self):
        """Generates a clean, readable Markdown dashboard of active applications."""
        apps = self.db.get_applications()
        
        content = """# Job Application Tracker Dashboard

This file is automatically synchronized with your SQLite database. You can review your application statuses below.

| Company | Role | Date Applied | Status | Tailored CV | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
"""
        
        if not apps:
            content += "| *No applications logged yet.* | | | | | |\n"
        else:
            for app in apps:
                # Format variables
                company = app["company"]
                title = app["title"]
                date_applied = app["applied_date"].split("T")[0]
                status = app["status"].upper()
                cv_path = app["tailored_cv_path"] or "None"
                if cv_path != "None":
                    # Make relative link
                    cv_path = f"[Link]({cv_path})"
                notes = app["notes"] or ""
                
                # Apply emojis to statuses
                status_emoji = {
                    "APPLIED": "📨 APPLIED",
                    "INTERVIEWING": "🤝 INTERVIEWING",
                    "OFFER": "🎉 OFFER",
                    "REJECTED": "❌ REJECTED"
                }.get(status, status)

                content += f"| **{company}** | {title} | {date_applied} | {status_emoji} | {cv_path} | {notes} |\n"
                
        with open(self.dashboard_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return self.dashboard_path

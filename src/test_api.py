import os
import shutil
import json
import unittest
from fastapi.testclient import TestClient

import src.api as api
from src.database import JobDatabase
from src.agents.job_monitor import JobMonitor
from src.agents.analyzer import JDAnalyzer
from src.agents.tracker import AppTracker

class TestAPIEndpoints(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # 1. Close current connections in api module to release file locks on Windows
        api.db.close()
        api.monitor.db.close()
        api.analyzer.db.close()
        api.tracker.db.close()
        
        # 2. Back up existing files
        cls.backups = {}
        for path in [api.db_path, api.resume_json_path, api.base_cv_path]:
            if os.path.exists(path):
                cls.backups[path] = path + ".bak"
                # If backup already exists, delete it first
                if os.path.exists(path + ".bak"):
                    os.remove(path + ".bak")
                shutil.copy2(path, path + ".bak")
                os.remove(path)
                
        # 3. Re-initialize connection references with fresh test databases
        api.db = JobDatabase(api.db_path)
        api.monitor = JobMonitor(config_path=api.config_path, db_path=api.db_path)
        api.analyzer = JDAnalyzer(config_path=api.config_path, db_path=api.db_path)
        api.tracker = AppTracker(db_path=api.db_path, dashboard_path=os.path.join(api.project_dir, "applications.md"))
        
        cls.client = TestClient(api.app)
 
    @classmethod
    def tearDownClass(cls):
        # 1. Close test connections to release file locks
        api.db.close()
        api.monitor.db.close()
        api.analyzer.db.close()
        api.tracker.db.close()
        
        # 2. Delete test database and files
        for path in [api.db_path, api.resume_json_path, api.base_cv_path]:
            if os.path.exists(path):
                os.remove(path)
                
        # 3. Restore backups
        for path, backup_path in cls.backups.items():
            if os.path.exists(backup_path):
                shutil.move(backup_path, path)
                
        # 4. Re-establish original connections
        api.db = JobDatabase(api.db_path)
        api.monitor = JobMonitor(db_path=api.db_path)
        api.analyzer = JDAnalyzer(db_path=api.db_path)
        api.tracker = AppTracker(db_path=api.db_path)

    def test_01_status_onboarding_check(self):
        """Verify that the status endpoint returns not onboarded initially."""
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["onboarded"])
        self.assertIsNone(data["cv_details"])

    def test_02_upload_and_onboard_flow(self):
        """Test uploading a LaTeX file, parsing it, and submitting onboarding questions."""
        # Clean up any residual resume base JSON
        if os.path.exists(api.resume_json_path):
            os.remove(api.resume_json_path)
            
        latex_content = (
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "\\section{Experience}\n"
            "\\begin{itemize}\n"
            "\\item Programmed enterprise Python microservices.\n"
            "\\end{itemize}\n"
            "\\section{Skills}\n"
            "Python, Git, SQL.\n"
            "\\end{document}"
        )
        
        # Write to temporary file for upload
        temp_cv = "data/temp_cv_upload.tex"
        with open(temp_cv, "w", encoding="utf-8") as f:
            f.write(latex_content)
            
        with open(temp_cv, "rb") as f:
            response = self.client.post("/api/upload-cv", files={"file": ("cv.tex", f, "text/plain")})
            
        if os.path.exists(temp_cv):
            os.remove(temp_cv)
            
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["detail"], "CV parsed successfully")
        self.assertIn("questions", data)
        self.assertTrue(len(data["questions"]) > 0)
        
        # Submit onboarding answers
        answers_payload = {
            "answers": [
                {"question": q["question"], "answer": "Yes, I have 5 years experience.", "category": q.get("category", "general")}
                for q in data["questions"]
            ]
        }
        response = self.client.post("/api/onboard/answers", json=answers_payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "Onboarding answers saved successfully.")
        
        # Verify status endpoint shows onboarded now
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        status_data = response.json()
        self.assertTrue(status_data["onboarded"])
        self.assertIsNotNone(status_data["cv_details"])

    def test_03_jobs_management_and_tailoring(self):
        """Test adding a job description, analyzing match score, grilling, tailoring, and applying."""
        # 1. Add job description manually
        job_payload = {
            "company": "Volvo Group IT",
            "title": "Python Developer",
            "jd_text": "Looking for a Python Developer experienced in Kubernetes and Apache Kafka.",
            "location": "Gothenburg"
        }
        response = self.client.post("/api/jobs/manual", json=job_payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        job_id = data["job_id"]
        self.assertIsNotNone(job_id)
        
        # 2. Get jobs list
        response = self.client.get("/api/jobs")
        self.assertEqual(response.status_code, 200)
        jobs_list = response.json()
        self.assertTrue(any(j["id"] == job_id for j in jobs_list))
        
        # 3. Analyze job match
        response = self.client.post(f"/api/jobs/{job_id}/analyze")
        self.assertEqual(response.status_code, 200)
        analysis_data = response.json()
        self.assertEqual(analysis_data["job_id"], job_id)
        self.assertIn("score", analysis_data)
        
        # 4. Get target grill questions
        response = self.client.get(f"/api/jobs/{job_id}/questions")
        self.assertEqual(response.status_code, 200)
        grill_data = response.json()
        self.assertIn("questions", grill_data)
        
        # 5. Submit answers to grill questions
        answers_payload = {
            "answers": [
                {"question": q["question"], "answer": "I have experience with Kafka in RabbitMQ environments.", "category": q["skill_target"]}
                for q in grill_data["questions"]
            ]
        }
        response = self.client.post(f"/api/jobs/{job_id}/answers", json=answers_payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["detail"], "Answers submitted. Ready for tailoring.")
        
        # 6. Tailor CV
        response = self.client.post(f"/api/jobs/{job_id}/tailor")
        self.assertEqual(response.status_code, 200)
        tailor_data = response.json()
        self.assertEqual(tailor_data["status"], "tailored")
        self.assertIn("tex_file", tailor_data)
        
        # 7. Apply for the job
        apply_payload = {
            "status": "applied",
            "notes": "Applied through internal portal"
        }
        response = self.client.post(f"/api/jobs/{job_id}/apply", json=apply_payload)
        self.assertEqual(response.status_code, 200)
        
        # 8. Check tracker
        response = self.client.get("/api/tracker")
        self.assertEqual(response.status_code, 200)
        tracker_list = response.json()
        self.assertEqual(len(tracker_list), 1)
        self.assertEqual(tracker_list[0]["company"], "Volvo Group IT")
        
        # 9. Update application status
        response = self.client.put(f"/api/tracker/{job_id}", json={"status": "interviewing"})
        self.assertEqual(response.status_code, 200)
        
        # Verify status updated
        response = self.client.get("/api/tracker")
        self.assertEqual(response.json()[0]["status"], "interviewing")
        
        # 10. Check development plan
        response = self.client.get("/api/devplan")
        self.assertEqual(response.status_code, 200)
        dev_plan = response.json()
        self.assertIn("plan", dev_plan)

if __name__ == "__main__":
    unittest.main()

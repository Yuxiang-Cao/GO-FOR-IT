import os
import unittest
import json
import sqlite3
import re
from src.database import JobDatabase
from src.utils.latex_parser import LatexCVParser
from src.utils.latex_compiler import LatexCompiler
from src.agents.job_monitor import JobMonitor
from src.agents.analyzer import JDAnalyzer
from src.agents.cv_tailor import CVTailor
from src.agents.tracker import AppTracker

class TestJobAgentSystem(unittest.TestCase):
    
    def setUp(self):
        # Use a temporary database for testing
        self.db_path = "data/test_database.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.db = JobDatabase(self.db_path)
        
    def tearDown(self):
        self.db.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            
    def test_database_creation_and_job_hash(self):
        """Verifies database initialization and duplicate checks."""
        company = "Volvo Group"
        title = "Senior Python Developer"
        jd = "We need an engineer experienced in Python, Git, and SQL."
        
        job_id1 = self.db.add_job(company, title, jd)
        job_id2 = self.db.add_job(company, title, jd)
        
        self.assertEqual(job_id1, job_id2, "Same job content should produce same unique hash")
        
        job = self.db.get_job(job_id1)
        self.assertIsNotNone(job)
        self.assertEqual(job["company"], company)
        self.assertEqual(job["status"], "discovered")
        
    def test_qa_deduplication(self):
        """Checks if exact questions are hashed and deduplicated."""
        q = "Have you worked with Kubernetes?"
        a = "Yes, in my previous role for 2 years."
        
        self.db.add_qa(q, a, "Kubernetes")
        
        # Test hash generation and retrieve
        q_hash = self.db.get_qa_hash(q)
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM qa_history WHERE question_hash = ?", (q_hash,))
        row = cursor.fetchone()
        
        self.assertIsNotNone(row)
        self.assertEqual(row["answer"], a)
        
    def test_latex_parser_integrity(self):
        """Verifies parsing a LaTeX string to JSON and rebuilding it."""
        sample_latex = (
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "\\section{Experience}\n"
            "\\begin{itemize}\n"
            "\\item Developed backend APIs in Python.\n"
            "\\item Optimized SQL queries.\n"
            "\\end{itemize}\n"
            "\\section{Skills}\n"
            "Languages: Python, JS.\n"
            "\\end{document}"
        )
        
        parser = LatexCVParser()
        parsed = parser.parse(sample_latex)
        
        self.assertEqual(len(parsed["sections"]), 2)
        self.assertEqual(parsed["sections"][0]["title"], "Experience")
        self.assertEqual(len(parsed["sections"][0]["list_items"]), 2)
        
        rebuilt = parser.rebuild(parsed)
        # Verify it still contains structural tags
        self.assertIn("\\section{Experience}", rebuilt)
        self.assertIn("\\item Developed backend APIs in Python.", rebuilt)
        
    def test_latex_parser_multiple_itemlists(self):
        """Verifies parsing and rebuilding a LaTeX string with multiple itemize blocks in one section."""
        sample_latex = (
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "\\section{Experience}\n"
            "\\subsection{Role A}\n"
            "\\begin{itemize}\n"
            "\\item Completed Task 1.\n"
            "\\end{itemize}\n"
            "Some mid text.\n"
            "\\subsection{Role B}\n"
            "\\begin{itemize}\n"
            "\\item Completed Task 2.\n"
            "\\item Completed Task 3.\n"
            "\\end{itemize}\n"
            "\\end{document}"
        )
        
        parser = LatexCVParser()
        parsed = parser.parse(sample_latex)
        
        # Verify both lists are parsed into list_items flat list
        self.assertEqual(len(parsed["sections"]), 1)
        self.assertEqual(parsed["sections"][0]["title"], "Experience")
        self.assertEqual(len(parsed["sections"][0]["list_items"]), 3)
        self.assertEqual(parsed["sections"][0]["list_items"][0], "Completed Task 1.")
        self.assertEqual(parsed["sections"][0]["list_items"][1], "Completed Task 2.")
        self.assertEqual(parsed["sections"][0]["list_items"][2], "Completed Task 3.")
        
        # Verify lengths are preserved
        self.assertEqual(parsed["sections"][0]["list_lengths"], [1, 2])
        
        rebuilt = parser.rebuild(parsed)
        # Verify the structure is preserved perfectly
        self.assertIn("\\subsection{Role A}", rebuilt)
        self.assertIn("Some mid text.", rebuilt)
        self.assertIn("\\subsection{Role B}", rebuilt)
        self.assertIn("\\item Completed Task 1.\n\\end{itemize}", rebuilt)
        self.assertIn("\\item Completed Task 3.\n\\end{itemize}", rebuilt)

    def test_job_monitor_filters(self):
        """Verifies filtering by location, language and citizenship restrictions."""
        monitor = JobMonitor(db_path=self.db_path)
        # Mock config values manually
        monitor.config = {
            "search": {
                "keywords": ["Python"],
                "countries": ["Sweden"],
                "cities": ["Gothenburg"],
                "remote": True,
                "citizenship_restrictions": ["EU Citizen"]
            }
        }
        
        # Job 1: Match
        job1 = {
            "title": "Python Developer",
            "company": "Volvo",
            "jd_text": "We need a Python coder in Gothenburg.",
            "location": "Gothenburg, Sweden"
        }
        self.assertTrue(monitor.filter_job(job1))
        
        # Job 2: Mismatch (Language or clearance requirement mismatch)
        job2 = {
            "title": "Python Specialist",
            "company": "US Defense Agency",
            "jd_text": "Must be US Citizen and hold active TS/SCI security clearance.",
            "location": "Washington, USA"
        }
        self.assertFalse(monitor.filter_job(job2))
        
        # Close connection to release file lock on Windows
        monitor.db.close()

    def test_application_tracker(self):
        """Verifies tracking status updates and dashboard file generation."""
        tracker_file = "test_applications.md"
        if os.path.exists(tracker_file):
            os.remove(tracker_file)
            
        tracker = AppTracker(db_path=self.db_path, dashboard_path=tracker_file)
        
        # Insert a job
        job_id = self.db.add_job("TestCorp", "Test Engineer", "Details of test job")
        
        # Log application
        tracker.log_application(job_id, tailored_cv_path="cv_test.pdf", notes="Direct email")
        
        # Check database application entry
        apps = self.db.get_applications()
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0]["company"], "TestCorp")
        self.assertEqual(apps[0]["status"], "applied")
        
        # Verify markdown file exists and contains correct data
        self.assertTrue(os.path.exists(tracker_file))
        with open(tracker_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("TestCorp", content)
        self.assertIn("Test Engineer", content)
        
        # Update status and verify change
        tracker.update_status(job_id, "interviewing")
        apps_updated = self.db.get_applications()
        self.assertEqual(apps_updated[0]["status"], "interviewing")
        
        # Close connection to release file lock on Windows
        tracker.db.close()
        
        # Cleanup
        if os.path.exists(tracker_file):
            os.remove(tracker_file)

if __name__ == "__main__":
    unittest.main()

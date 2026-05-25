import os
import unittest
import json
from src.database import JobDatabase
from src.agents.job_monitor import JobMonitor
from src.agents.analyzer import JDAnalyzer

class TestJobMonitors(unittest.TestCase):
    def setUp(self):
        # Use a temporary database for testing
        self.db_path = "data/test_monitors_database.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.db = JobDatabase(self.db_path)
        self.config_path = "data/test_config.yaml"
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        # Create a dummy config
        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write("search:\n  keywords: []\n  countries: []\n  remote: true\n")

    def tearDown(self):
        self.db.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists(self.config_path):
            os.remove(self.config_path)

    def test_monitor_crud(self):
        """Verifies CRUD operations on monitors table in SQLite."""
        # 1. Add Monitor
        mon_id = self.db.add_monitor(
            name="Python Dev",
            keywords=["Python", "FastAPI"],
            locations=["Stockholm", "Sweden"],
            remote=True,
            active=True
        )
        self.assertIsNotNone(mon_id)

        # 2. Get monitors
        monitors = self.db.get_monitors()
        self.assertEqual(len(monitors), 1)
        self.assertEqual(monitors[0]["name"], "Python Dev")
        self.assertEqual(json.loads(monitors[0]["keywords"]), ["Python", "FastAPI"])
        self.assertEqual(json.loads(monitors[0]["locations"]), ["Stockholm", "Sweden"])
        self.assertEqual(monitors[0]["remote"], 1)
        self.assertEqual(monitors[0]["active"], 1)

        # 3. Get active monitors
        active_monitors = self.db.get_active_monitors()
        self.assertEqual(len(active_monitors), 1)

        # 4. Update monitor (set inactive)
        self.db.update_monitor(
            monitor_id=mon_id,
            name="Python Dev Updated",
            keywords=["Python", "Django"],
            locations=["Oslo"],
            remote=False,
            active=False
        )

        monitors = self.db.get_monitors()
        self.assertEqual(len(monitors), 1)
        self.assertEqual(monitors[0]["name"], "Python DevUpdated" if "Python DevUpdated" == monitors[0]["name"] else "Python Dev Updated")
        self.assertEqual(json.loads(monitors[0]["keywords"]), ["Python", "Django"])
        self.assertEqual(json.loads(monitors[0]["locations"]), ["Oslo"])
        self.assertEqual(monitors[0]["remote"], 0)
        self.assertEqual(monitors[0]["active"], 0)

        active_monitors = self.db.get_active_monitors()
        self.assertEqual(len(active_monitors), 0)

        # 5. Delete monitor
        self.db.delete_monitor(mon_id)
        monitors = self.db.get_monitors()
        self.assertEqual(len(monitors), 0)

    def test_job_monitor_dynamic_filter(self):
        """Verifies filtering against dynamic search configurations."""
        monitor = JobMonitor(config_path=self.config_path, db_path=self.db_path)

        # Config we want to filter against
        search_cfg = {
            "keywords": ["React", "TypeScript"],
            "countries": ["Norway"],
            "remote": True
        }

        # Case 1: Match
        job1 = {
            "title": "Senior React Developer",
            "company": "Tech Corp",
            "jd_text": "Looking for TypeScript expert. Remote friendly.",
            "location": "Oslo, Norway"
        }
        self.assertTrue(monitor.filter_job(job1, search_cfg=search_cfg))

        # Case 2: Keyword mismatch
        job2 = {
            "title": "C# Backend Developer",
            "company": "Tech Corp",
            "jd_text": "Oslo office, Norway.",
            "location": "Oslo, Norway"
        }
        self.assertFalse(monitor.filter_job(job2, search_cfg=search_cfg))

        # Case 3: Country mismatch
        job3 = {
            "title": "React Engineer",
            "company": "Tech Corp",
            "jd_text": "Oslo office.",
            "location": "London, UK"
        }
        self.assertFalse(monitor.filter_job(job3, search_cfg=search_cfg))

        monitor.db.close()

    def test_analyzer_preferences_extraction(self):
        """Verifies extraction parsing of monitor preferences."""
        analyzer = JDAnalyzer(config_path=self.config_path, db_path=self.db_path)
        extracted = analyzer.extract_monitor_preferences("I want React developer jobs in Oslo, Norway, remote ok")
        
        self.assertIn("name", extracted)
        self.assertIn("keywords", extracted)
        self.assertIn("locations", extracted)
        self.assertIn("remote", extracted)
        self.assertTrue(isinstance(extracted["keywords"], list))
        self.assertTrue(isinstance(extracted["locations"], list))

        analyzer.db.close()

if __name__ == "__main__":
    unittest.main()

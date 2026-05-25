import sqlite3
import os
import hashlib
from datetime import datetime

class JobDatabase:
    def __init__(self, db_path="data/database.db"):
        self.db_path = db_path
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        # Enable Write-Ahead Logging for better concurrency on Windows
        try:
            self.conn.execute("PRAGMA journal_mode=WAL;")
        except sqlite3.OperationalError:
            # Fallback if WAL is not supported in the running environment
            pass
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        
        # 1. Jobs Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            location TEXT,
            jd_text TEXT NOT NULL,
            url TEXT,
            status TEXT DEFAULT 'discovered', -- 'discovered', 'ignored', 'grilled', 'tailored', 'applied', 'rejected'
            confidence_score REAL,
            match_report TEXT,                -- JSON string detailing analysis
            created_at TEXT NOT NULL
        )
        """)
        
        # 2. QA History Table for Q&A deduplication
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS qa_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_hash TEXT UNIQUE,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            category TEXT,
            created_at TEXT NOT NULL
        )
        """)
        
        # 3. Applications Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            job_id TEXT PRIMARY KEY,
            applied_date TEXT NOT NULL,
            tailored_cv_path TEXT,
            status TEXT DEFAULT 'applied',     -- 'applied', 'interviewing', 'offer', 'rejected'
            notes TEXT,
            FOREIGN KEY (job_id) REFERENCES jobs (id)
        )
        """)
        
        # 4. Monitors Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS monitors (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            keywords TEXT NOT NULL,  -- JSON string list
            locations TEXT NOT NULL, -- JSON string list
            remote INTEGER NOT NULL, -- 0 or 1
            active INTEGER NOT NULL, -- 0 or 1
            created_at TEXT NOT NULL
        )
        """)
        
        self.conn.commit()

    def get_job_hash(self, company, title, jd_text):
        """Generate a unique ID for a job description."""
        unique_str = f"{company.strip().lower()}|{title.strip().lower()}|{jd_text.strip()}"
        return hashlib.sha256(unique_str.encode('utf-8')).hexdigest()

    def add_job(self, company, title, jd_text, url=None, location=None):
        job_id = self.get_job_hash(company, title, jd_text)
        created_at = datetime.now().isoformat()
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO jobs (id, company, title, location, jd_text, url, status, created_at) VALUES (?, ?, ?, ?, ?, ?, 'discovered', ?)",
                (job_id, company, title, location, jd_text, url, created_at)
            )
            self.conn.commit()
            return job_id
        except sqlite3.IntegrityError:
            # Job already exists
            return job_id

    def get_job(self, job_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_job_status(self, job_id, status):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
        self.conn.commit()

    def update_job_analysis(self, job_id, confidence_score, match_report):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE jobs SET confidence_score = ?, match_report = ? WHERE id = ?",
            (confidence_score, match_report, job_id)
        )
        self.conn.commit()

    def get_qa_hash(self, question):
        """Generate a hash for normalized questions to support exact duplicate checking."""
        normalized = question.strip().lower()
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def add_qa(self, question, answer, category=None):
        q_hash = self.get_qa_hash(question)
        created_at = datetime.now().isoformat()
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO qa_history (question_hash, question, answer, category, created_at) VALUES (?, ?, ?, ?, ?)",
                (q_hash, question, answer, category, created_at)
            )
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error adding QA to history: {e}")

    def get_all_qa(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT question, answer, category FROM qa_history")
        return [dict(row) for row in cursor.fetchall()]

    def add_application(self, job_id, tailored_cv_path=None, notes=None):
        applied_date = datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO applications (job_id, applied_date, tailored_cv_path, status, notes) VALUES (?, ?, ?, 'applied', ?)",
            (job_id, applied_date, tailored_cv_path, notes)
        )
        cursor.execute("UPDATE jobs SET status = 'applied' WHERE id = ?", (job_id,))
        self.conn.commit()

    def get_applications(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT a.job_id, j.company, j.title, a.applied_date, a.status, a.tailored_cv_path, a.notes 
            FROM applications a 
            JOIN jobs j ON a.job_id = j.id
            ORDER BY a.applied_date DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def update_application_status(self, job_id, status):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE applications SET status = ? WHERE job_id = ?", (status, job_id))
        # Sync jobs status too
        cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
        self.conn.commit()

    def add_monitor(self, name, keywords, locations, remote, active=True):
        import json
        monitor_id = hashlib.sha256(f"{name}|{datetime.now().isoformat()}".encode('utf-8')).hexdigest()
        created_at = datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO monitors (id, name, keywords, locations, remote, active, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (monitor_id, name, json.dumps(keywords), json.dumps(locations), 1 if remote else 0, 1 if active else 0, created_at)
        )
        self.conn.commit()
        return monitor_id

    def get_monitors(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM monitors ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    def get_active_monitors(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM monitors WHERE active = 1 ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    def update_monitor(self, monitor_id, name, keywords, locations, remote, active):
        import json
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE monitors SET name = ?, keywords = ?, locations = ?, remote = ?, active = ? WHERE id = ?",
            (name, json.dumps(keywords), json.dumps(locations), 1 if remote else 0, 1 if active else 0, monitor_id)
        )
        self.conn.commit()

    def delete_monitor(self, monitor_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM monitors WHERE id = ?", (monitor_id,))
        self.conn.commit()

    def close(self):
        self.conn.close()

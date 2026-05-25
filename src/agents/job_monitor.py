import os
import yaml
import urllib.parse
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup
from src.database import JobDatabase

class JobMonitor:
    def __init__(self, config_path="config.yaml", db_path="data/database.db"):
        self.config_path = config_path
        self.db = JobDatabase(db_path)
        self.config = self._load_config()

    def _load_config(self):
        if not os.path.exists(self.config_path):
            return {}
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def fetch_rss_jobs(self, feed_url):
        """Fetches jobs from a given RSS feed url."""
        jobs_found = []
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            response = requests.get(feed_url, headers=headers, timeout=10)
            if response.status_code != 200:
                return []
            
            root = ET.fromstring(response.content)
            for item in root.findall(".//item"):
                title = item.find("title").text if item.find("title") is not None else "Unknown Title"
                link = item.find("link").text if item.find("link") is not None else ""
                desc = item.find("description").text if item.find("description") is not None else ""
                
                # Strip HTML from description
                soup = BeautifulSoup(desc, "html.parser")
                clean_desc = soup.get_text()
                
                # Assume company name is in title or description (parse or default)
                company = "Unknown Company"
                if " at " in title:
                    title, company = title.rsplit(" at ", 1)
                elif " - " in title:
                    parts = title.split(" - ")
                    title = parts[0]
                    company = parts[1] if len(parts) > 1 else "Unknown Company"

                jobs_found.append({
                    "title": title.strip(),
                    "company": company.strip(),
                    "jd_text": clean_desc.strip(),
                    "url": link.strip()
                })
        except Exception as e:
            print(f"Error fetching RSS feed: {e}")
        return jobs_found

    def filter_job(self, job):
        """Applies filters defined in config.yaml."""
        search_cfg = self.config.get("search", {})
        
        # 1. Keywords check (in title or description)
        keywords = search_cfg.get("keywords", [])
        title_lower = job["title"].lower()
        desc_lower = job["jd_text"].lower()
        
        if keywords:
            keyword_match = any(kw.lower() in title_lower or kw.lower() in desc_lower for kw in keywords)
            if not keyword_match:
                return False
                
        # 2. Country/City check
        countries = [c.lower() for c in search_cfg.get("countries", [])]
        cities = [c.lower() for c in search_cfg.get("cities", [])]
        
        # Check if country/city mentioned in description or url if location is not explicitly set
        location = job.get("location") or ""
        loc_lower = location.lower()
        
        # If specific cities/countries are requested, verify they aren't explicitly mismatching
        # (e.g., if JD mentions a city/country not in our list, but if location is empty we let it pass check)
        if cities or countries:
            has_valid_location = False
            # Check explicit location field
            if location:
                if any(c in loc_lower for c in cities) or any(co in loc_lower for co in countries):
                    has_valid_location = True
            else:
                # Check description text as fallback
                if any(c in desc_lower for c in cities) or any(co in desc_lower for co in countries):
                    has_valid_location = True
                else:
                    # If location isn't specified in JD or text, but we allow remote, proceed
                    if search_cfg.get("remote", False) and "remote" in desc_lower:
                        has_valid_location = True
            
            if not has_valid_location and (cities or countries):
                # If location is explicitly specified and doesn't match, filter out
                if location:
                    return False

        # 3. Citizenship restrictions
        citizenship_cfg = search_cfg.get("citizenship_restrictions", [])
        # If JD says "US citizenship required" but we are looking in Sweden (e.g. EU), skip it
        if "us citizen" in desc_lower or "security clearance" in desc_lower:
            # If "US Citizen" is not in our approved list, skip US clearance-locked jobs
            if not any("us citizen" in str(c).lower() for c in citizenship_cfg):
                return False
                
        # 4. Language checks
        languages = [lang.lower() for lang in search_cfg.get("languages", ["english"])]
        # If job description is entirely in a language we don't speak (e.g., Swedish if only English config'd)
        # For simplicity, search for language keywords or use a basic set.
        # Most tech resumes are English; if Swedish is required and we don't want it, look for language tags.
        # This is a soft filter.
        
        return True

    def monitor_and_store(self, custom_feeds=None):
        """Main loop to discover and filter jobs, logging them to SQLite db."""
        feeds = custom_feeds or []
        # If no feeds, we fetch from a default mock search or standard feed URL
        if not feeds:
            # Example public tech job feeds
            feeds = [
                "https://weworkremotely.com/categories/remote-programming-jobs.rss",
                "https://remoteok.com/remote-jobs.rss"
            ]

        discovered_count = 0
        new_jobs = []

        for feed in feeds:
            jobs = self.fetch_rss_jobs(feed)
            for job in jobs:
                if self.filter_job(job):
                    job_id = self.db.add_job(
                        company=job["company"],
                        title=job["title"],
                        jd_text=job["jd_text"],
                        url=job["url"],
                        location=job.get("location")
                    )
                    # Check if this is a newly inserted job by looking up the status
                    existing = self.db.get_job(job_id)
                    if existing and existing["status"] == "discovered":
                        discovered_count += 1
                        new_jobs.append(existing)
                        
        print(f"Job Monitor run completed: Discovered {discovered_count} new matching jobs.")
        return new_jobs

    def add_mock_job(self, company, title, jd_text, location="Remote", url=None):
        """Allows injecting jobs directly (useful for manual testing)."""
        job_id = self.db.add_job(company, title, jd_text, url, location)
        return job_id

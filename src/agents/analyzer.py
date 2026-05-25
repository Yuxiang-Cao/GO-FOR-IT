import os
import json
import yaml
import google.generativeai as genai
from src.database import JobDatabase

class JDAnalyzer:
    def __init__(self, config_path="config.yaml", db_path="data/database.db"):
        self.config_path = config_path
        self.db = JobDatabase(db_path)
        self.config = self._load_config()
        self._init_gemini()

    def _load_config(self):
        if not os.path.exists(self.config_path):
            return {}
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _init_gemini(self):
        # Retrieve API key from environment variable
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            model_name = self.config.get("gemini", {}).get("model_name", "gemini-1.5-flash")
            self.model = genai.GenerativeModel(model_name)
            
            # Initialize pro model for complex tailoring/analysis
            pro_model_name = self.config.get("gemini", {}).get("expert_model_name", "gemini-1.5-pro")
            self.pro_model = genai.GenerativeModel(pro_model_name)
        else:
            self.model = None
            self.pro_model = None
            print("WARNING: GEMINI_API_KEY environment variable not set. Gemini API functions will be mocked.")

    def run_ai_query(self, prompt: str, use_pro=False, return_json=True) -> str:
        """Helper to run a query to Gemini API."""
        if not self.model:
            # Fallback mock responses for testing without API keys
            return self._mock_ai_query(prompt)
            
        model_to_use = self.pro_model if (use_pro and self.pro_model) else self.model
        
        try:
            if return_json:
                response = model_to_use.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
            else:
                response = model_to_use.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Gemini API Error: {e}")
            return self._mock_ai_query(prompt)

    def _mock_ai_query(self, prompt: str) -> str:
        """Mock responses to ensure the system is testable even without network/API credentials."""
        # Simple heuristics to return mocked JSON structures based on prompts
        if "extract_skills" in prompt or "analyze_jd" in prompt:
            return json.dumps({
                "confidence_score": 78.0,
                "skills_matched": ["Python", "Git"],
                "skills_missing": ["Docker", "Kubernetes", "Apache Kafka"],
                "transferable_skills": [
                    {"missing": "Apache Kafka", "transferable": "RabbitMQ", "reason": "Both are messaging/queue systems."}
                ],
                "culture_assessment": "Swedish culture values work-life balance and agile collaboration.",
                "analysis_summary": "Strong core Python development matching, but missing containerization and event-streaming."
            })
        elif "interview_questions" in prompt:
            return json.dumps({
                "questions": [
                    {
                        "id": "q1",
                        "question": "The JD requests Kubernetes container orchestration. Have you worked with Docker or any container runtimes in your previous roles?",
                        "skill_target": "Docker/Kubernetes"
                    },
                    {
                        "id": "q2",
                        "question": "This role involves event-driven architecture using Kafka. Have you set up message brokers like RabbitMQ, ActiveMQ, or Celery?",
                        "skill_target": "Apache Kafka"
                    }
                ]
            })
        elif "general_profile" in prompt:
            return json.dumps({
                "questions": [
                    {"question": "Could you list 2-3 of your proudest engineering accomplishments?", "category": "general"},
                    {"question": "What is your typical role inside an Agile software team?", "category": "general"}
                ]
            })
        elif "development_plan" in prompt:
            return json.dumps({
                "missing_skills": ["Docker", "Apache Kafka"],
                "plan": [
                    {"skill": "Docker", "difficulty": "Beginner", "action": "Take Docker container fundamentals on freeCodeCamp, containerize a Python flask app."},
                    {"skill": "Apache Kafka", "difficulty": "Intermediate", "action": "Build a small local producer-consumer system in Python using kafka-python."}
                ]
            })
        elif "extract_monitor_preferences" in prompt:
            return json.dumps({
                "name": "Python Backend Stockholm",
                "keywords": ["Python", "FastAPI", "SQL"],
                "locations": ["Stockholm", "Sweden"],
                "remote": True
            })
        elif "structure_raw_cv_text" in prompt:
            return json.dumps({
                "preamble": "\\documentclass{article}\n\\begin{document}",
                "sections": [
                    {
                        "title": "Summary",
                        "raw_before_items": "Experienced Software Engineer.",
                        "list_items": [],
                        "raw_after_items": ""
                    },
                    {
                        "title": "Experience",
                        "raw_before_items": "",
                        "list_items": ["Developed software in Python at TechCorp."],
                        "raw_after_items": ""
                    },
                    {
                        "title": "Skills",
                        "raw_before_items": "",
                        "list_items": ["Python", "Git"],
                        "raw_after_items": ""
                    }
                ]
            })
        return "{}"

    def analyze_jd(self, jd_text: str, cv_json: dict) -> dict:
        """Compares the Job Description with the parsed CV."""
        culture = self.config.get("culture", {}).get("target_culture", "Nordic")
        
        prompt = f"""# analyze_jd
        You are a job recruitment analyzer specializing in {culture} recruitment culture.
        Analyze the following Job Description (JD) and parsed CV.
        
        Culture Context:
        - Nordic culture values flat hierarchies, collaboration, soft skills, and work-life balance.
        - US culture values explicit metrics, scaling achievements, and ownership of delivery.
        
        Perform a semantic comparison and output a JSON object containing:
        1. "confidence_score": (float, 0-100) representing how well the CV matches the JD. Scale soft/hard skills according to target culture: {culture}.
        2. "skills_matched": list of strings of skills present in both.
        3. "skills_missing": list of key hard/soft skills required by the JD that are not directly on the CV.
        4. "transferable_skills": list of objects with keys: "missing", "transferable", "reason" (identifying if a missing skill can be bridged by something in their CV).
        5. "culture_assessment": brief paragraph describing cultural alignment.
        6. "analysis_summary": brief summary of fit.

        CV JSON:
        {json.dumps(cv_json)}

        Job Description:
        {jd_text}
        """
        response_text = self.run_ai_query(prompt, use_pro=True)
        try:
            analysis = json.loads(response_text)
            return analysis
        except Exception:
            return json.loads(self._mock_ai_query("analyze_jd"))

    def generate_interview_questions(self, jd_text: str, cv_json: dict, analysis: dict) -> list:
        """Generates tailored /grill-me questions for missing JD requirements, cross-referencing previous answers to avoid duplicates."""
        missing_skills = analysis.get("skills_missing", [])
        if not missing_skills:
            return []

        # Fetch past questions and answers from database to prevent duplication
        past_qa = self.db.get_all_qa()
        past_qa_str = json.dumps(past_qa)

        prompt = f"""
        # interview_questions
        You are an expert interviewer using the '/grill-me' concept.
        Given the following missing skills from a job description, generate up to 3 highly tailored interview questions to extract hidden experiences, stories, or transferable skills from the user.
        
        Rules:
        - Do NOT ask questions similar to those already answered in the Q&A history below.
        - Focus on extracting transferable skills or projects the user might have worked on but omitted from their CV.
        - Keep questions conversational, professional, and clear.
        
        Q&A History (DO NOT DUPLICATE THESE):
        {past_qa_str}

        Missing Skills to address:
        {json.dumps(missing_skills)}

        Job Description:
        {jd_text}

        Output a JSON object with a single key "questions" containing a list of objects, each with:
        - "question": the question string
        - "skill_target": the skill this question is aiming to verify
        """
        response_text = self.run_ai_query(prompt, use_pro=False)
        try:
            data = json.loads(response_text)
            return data.get("questions", [])
        except Exception:
            return json.loads(self._mock_ai_query("interview_questions")).get("questions", [])

    def generate_general_profiling_questions(self, cv_json: dict) -> list:
        """Generates general profiling questions when CV is first loaded."""
        prompt = f"""
        # general_profile
        You are an onboarding agent. The user has just uploaded their CV.
        Review the CV and generate 3 general questions to harvest more depth about their career history, achievements, work preferences, and transferable skills.
        
        CV JSON:
        {json.dumps(cv_json)}
        
        Output a JSON object with a single key "questions" containing a list of objects:
        - "question": the question string
        - "category": a classification string (e.g. "achievements", "leadership", "technical")
        """
        response_text = self.run_ai_query(prompt, use_pro=False)
        try:
            data = json.loads(response_text)
            return data.get("questions", [])
        except Exception:
            return json.loads(self._mock_ai_query("general_profile")).get("questions", [])

    def generate_development_plan(self, missing_skills: list) -> list:
        """Creates a professional development plan for skills the user confirmed they do not possess."""
        if not missing_skills:
            return []
            
        prompt = f"""
        # development_plan
        Create a concise career development plan for the following missing skills. 
        Provide concrete courses, actions, or projects to learn them.
        
        Missing Skills:
        {json.dumps(missing_skills)}
        
        Output a JSON array of objects:
        - "skill": name of skill
        - "difficulty": Beginner, Intermediate, or Advanced
        - "action": concrete steps to learn it
        """
        response_text = self.run_ai_query(prompt, use_pro=False)
        try:
            data = json.loads(response_text)
            if isinstance(data, dict) and "plan" in data:
                return data["plan"]
            return data
        except Exception:
            return json.loads(self._mock_ai_query("development_plan")).get("plan", [])

    def extract_monitor_preferences(self, user_text: str) -> dict:
        """Extracts job search preferences from free text query."""
        prompt = f"""
        # extract_monitor_preferences
        Extract job search preferences from the user's input text.
        
        Input Text: "{user_text}"
        
        Output a JSON object with keys:
        - "name": a short 2-4 word descriptive name for this monitor (e.g., "Python Stockholm Remote")
        - "keywords": a list of key technical terms, frameworks, or job roles mentioned (e.g., ["Python", "FastAPI"])
        - "locations": a list of cities or countries mentioned (e.g., ["Stockholm", "Sweden"])
        - "remote": a boolean indicating if remote is mentioned/requested
        """
        response_text = self.run_ai_query(prompt, use_pro=False)
        try:
            return json.loads(response_text)
        except Exception:
            return json.loads(self._mock_ai_query("extract_monitor_preferences"))

    def structure_raw_cv_text(self, raw_text: str) -> dict:
        """Structures raw extracted CV text into standard resume JSON using Gemini."""
        prompt = f"""
        # structure_raw_cv_text
        You are an expert resume parsing AI.
        Analyze the following raw text extracted from a resume.
        Identify all personal summaries, work experiences, skills, and education sections.
        
        Structure this information into a JSON object containing:
        1. "preamble": A string containing LaTeX preamble declarations, or simply leave empty/default if not relevant.
        2. "sections": A list of section objects. Each section object MUST have:
           - "title": Title of the section (e.g. "Summary", "Experience", "Skills", "Education").
           - "raw_before_items": Introductory text in the section before any bullet points.
           - "list_items": A list of bullet points / items in that section.
           - "raw_after_items": Closing text / content in the section after the bullet list.
           
        Keep the descriptions clean and preserve professional detail.
        
        Raw CV Text:
        {raw_text}
        """
        response_text = self.run_ai_query(prompt, use_pro=True)
        try:
            return json.loads(response_text)
        except Exception:
            return json.loads(self._mock_ai_query("structure_raw_cv_text"))

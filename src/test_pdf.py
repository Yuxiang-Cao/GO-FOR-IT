import os
import unittest
import json
from src.utils.latex_compiler import LatexCompiler
from pypdf import PdfReader

class TestPDFSupport(unittest.TestCase):
    def setUp(self):
        self.compiler = LatexCompiler()
        self.test_pdf_path = "data/test_resume_output.pdf"
        if os.path.exists(self.test_pdf_path):
            os.remove(self.test_pdf_path)
            
    def tearDown(self):
        if os.path.exists(self.test_pdf_path):
            os.remove(self.test_pdf_path)

    def test_html_to_pdf_generation_and_reading(self):
        """Verifies Playwright HTML-to-PDF compilation and pypdf text extraction."""
        # 1. Create a mock CV JSON
        cv_json = {
            "preamble": "\\title{Jane Doe - Data Scientist}\n\\author{jane.doe@example.com}",
            "sections": [
                {
                    "title": "Summary",
                    "raw_before_items": "Passionate data scientist with 3 years of ML experience.",
                    "list_items": [],
                    "raw_after_items": ""
                },
                {
                    "title": "Experience",
                    "raw_before_items": "",
                    "list_items": [
                        "Designed neural networks in Python.",
                        "Optimized database indexing."
                    ],
                    "raw_after_items": ""
                }
            ]
        }
        
        # 2. Compile to PDF using Playwright HTML-to-PDF compiler
        self.compiler.compile_html_to_pdf(cv_json, self.test_pdf_path)
        
        # 3. Check if PDF file was created
        self.assertTrue(os.path.exists(self.test_pdf_path))
        self.assertTrue(os.path.getsize(self.test_pdf_path) > 0)
        
        # 4. Use pypdf to read the text back and check contents
        reader = PdfReader(self.test_pdf_path)
        self.assertTrue(len(reader.pages) > 0)
        
        raw_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                raw_text += text + "\n"
                
        # 5. Validate the extracted text contains expected words
        self.assertIn("Jane Doe", raw_text)
        self.assertIn("Data Scientist", raw_text)
        self.assertIn("jane.doe@example.com", raw_text)
        self.assertIn("Passionate data scientist", raw_text)
        self.assertIn("Designed neural networks in Python", raw_text)

if __name__ == "__main__":
    unittest.main()

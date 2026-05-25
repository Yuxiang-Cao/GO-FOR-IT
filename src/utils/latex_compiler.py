import subprocess
import shutil
import os
import re

class LatexCompiler:
    def __init__(self, preferred_compiler="auto"):
        self.compiler = self._detect_compiler(preferred_compiler)

    def _detect_compiler(self, preferred):
        if preferred != "auto" and shutil.which(preferred):
            return preferred
            
        # Order of preference: tectonic (lightweight, auto-downloads packages), xelatex, pdflatex
        for cmd in ["tectonic", "xelatex", "pdflatex"]:
            if shutil.which(cmd):
                return cmd
        return None

    def compile(self, tex_path: str, output_dir: str = ".") -> str:
        """Compiles the .tex file to PDF.
        Returns the path to the generated PDF or raises RuntimeError on failure.
        """
        if not self.compiler:
            raise RuntimeError(
                "No LaTeX compiler detected on PATH (tried tectonic, xelatex, pdflatex).\n"
                "Please install Tectonic (https://tectonic-typesetting.github.io) or TeX Live/MiKTeX."
            )
            
        tex_path = os.path.abspath(tex_path)
        output_dir = os.path.abspath(output_dir)
        
        # Build command based on compiler
        if self.compiler == "tectonic":
            cmd = ["tectonic", "-o", output_dir, tex_path]
        elif self.compiler in ["pdflatex", "xelatex"]:
            cmd = [self.compiler, "-interaction=nonstopmode", f"-output-directory={output_dir}", tex_path]
        else:
            cmd = [self.compiler, tex_path]
            
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            # Find the output PDF path
            base_name = os.path.splitext(os.path.basename(tex_path))[0]
            pdf_path = os.path.join(output_dir, f"{base_name}.pdf")
            if os.path.exists(pdf_path):
                return pdf_path
            raise FileNotFoundError(f"PDF compiled but not found at {pdf_path}")
        except subprocess.CalledProcessError as e:
            error_log = e.stdout.decode('utf-8', errors='ignore') + "\n" + e.stderr.decode('utf-8', errors='ignore')
            raise RuntimeError(f"LaTeX Compilation Failed using {self.compiler}:\n{error_log}")

    def get_pdf_page_count(self, pdf_path: str) -> int:
        """Determine page count of a PDF using basic binary parsing to avoid extra dependencies."""
        if not os.path.exists(pdf_path):
            return 0
            
        with open(pdf_path, 'rb') as f:
            content = f.read()
            
        # Try to find /Type /Pages /Count X
        pages_matches = re.findall(br'/Type\s*/Pages\s*/Count\s*(\d+)', content)
        if pages_matches:
            return int(pages_matches[-1])
            
        # Fallback to general /Count X pattern
        count_matches = re.findall(br'/Count\s*(\d+)', content)
        if count_matches:
            return int(count_matches[-1])
            
        # Fallback: parse page objects count manually
        page_objects = re.findall(br'/Type\s*/Page\b', content)
        if page_objects:
            return len(page_objects)
            
        return 1  # Default fallback

    def compile_html_to_pdf(self, cv_json: dict, pdf_out_path: str):
        """Generates an HTML version of the CV JSON and prints it to PDF using Playwright."""
        # 1. Build a professional, clean HTML resume layout
        title = cv_json.get("preamble", "")
        # Extract title cleanly if it has LaTeX command like \title{John Doe - Software Engineer}
        import re
        title_match = re.search(r'\\title\{([^}]+)\}', title)
        title_text = title_match.group(1) if title_match else "Resume"
        
        author_match = re.search(r'\\author\{([^}]+)\}', title)
        author_text = author_match.group(1) if author_match else ""
        
        sections_html = ""
        for sec in cv_json.get("sections", []):
            sec_title = sec.get("title", "")
            raw_before = sec.get("raw_before_items", "")
            items = sec.get("list_items", [])
            raw_after = sec.get("raw_after_items", "")
            
            # Simple LaTeX command cleanups for HTML readability
            raw_before = re.sub(r'\\[a-zA-Z]+\{([^}]+)\}', r'\1', raw_before)
            raw_after = re.sub(r'\\[a-zA-Z]+\{([^}]+)\}', r'\1', raw_after)
            raw_before = raw_before.replace('\\%', '%').replace('\\&', '&')
            raw_after = raw_after.replace('\\%', '%').replace('\\&', '&')
            
            items_html = ""
            if items:
                cleaned_items = []
                for item in items:
                    item_clean = re.sub(r'\\[a-zA-Z]+\{([^}]+)\}', r'\1', item)
                    item_clean = item_clean.replace('\\%', '%').replace('\\&', '&')
                    cleaned_items.append(item_clean)
                items_html = "<ul>" + "".join(f"<li>{item}</li>" for item in cleaned_items) + "</ul>"
                
            sections_html += f"""
            <div class="section">
                <div class="section-title">{sec_title}</div>
                {f'<p class="intro">{raw_before}</p>' if raw_before.strip() else ''}
                {items_html}
                {f'<p class="outro">{raw_after}</p>' if raw_after.strip() else ''}
            </div>
            """
            
        html_content = f"""<!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
            body {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                color: #1e293b;
                line-height: 1.5;
                margin: 0;
                padding: 1.5cm;
                font-size: 13px;
                background-color: #ffffff;
            }}
            .header {{
                text-align: center;
                border-bottom: 2px solid #3b82f6;
                padding-bottom: 15px;
                margin-bottom: 20px;
            }}
            .name {{
                font-size: 24px;
                font-weight: 700;
                color: #0f172a;
                margin: 0 0 5px 0;
            }}
            .contact {{
                color: #64748b;
                font-size: 12px;
            }}
            .section {{
                margin-bottom: 18px;
            }}
            .section-title {{
                font-size: 15px;
                font-weight: 600;
                color: #0f172a;
                border-bottom: 1px solid #e2e8f0;
                padding-bottom: 4px;
                margin-bottom: 8px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            p.intro, p.outro {{
                margin: 0 0 8px 0;
            }}
            ul {{
                margin: 0 0 8px 0;
                padding-left: 20px;
            }}
            li {{
                margin-bottom: 4px;
            }}
        </style>
        </head>
        <body>
            <div class="header">
                <div class="name">{title_text}</div>
                {f'<div class="contact">{author_text}</div>' if author_text else ''}
            </div>
            {sections_html}
        </body>
        </html>
        """
        
        # 2. Run Playwright to convert HTML to PDF
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(html_content)
            page.pdf(
                path=pdf_out_path,
                format="A4",
                margin={"top": "1.2cm", "bottom": "1.2cm", "left": "1.2cm", "right": "1.2cm"},
                print_background=True
            )
            browser.close()

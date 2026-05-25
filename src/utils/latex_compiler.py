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

import os
import sys
import subprocess
import webbrowser
import time
from threading import Timer

def open_browser():
    time.sleep(2.0)  # Wait for uvicorn to startup
    webbrowser.open("http://localhost:8000")

def main():
    print("==================================================")
    print("Starting GO FOR IT Local Server")
    print("==================================================")
    
    project_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Check virtual environment
    venv_dir = os.path.join(project_dir, ".venv")
    if os.path.exists(venv_dir):
        print("Using virtual environment...")
        if sys.platform == "win32":
            python_bin = os.path.join(venv_dir, "Scripts", "python.exe")
        else:
            python_bin = os.path.join(venv_dir, "bin", "python")
    else:
        python_bin = sys.executable
        print(f"Using system python: {python_bin}")
        
    # 2. Make sure frontend is compiled
    frontend_dist = os.path.join(project_dir, "frontend", "dist")
    if not os.path.exists(frontend_dist):
        print("Frontend build not found. Attempting to build frontend...")
        frontend_dir = os.path.join(project_dir, "frontend")
        try:
            # Check npm presence (using shell=True is more robust on Windows)
            subprocess.run(["npm", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, shell=True)
            print("Installing node packages...")
            subprocess.run(["npm", "install"], cwd=frontend_dir, check=True, shell=True)
            print("Building frontend assets...")
            subprocess.run(["npm", "run", "build"], cwd=frontend_dir, check=True, shell=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("WARNING: Could not build frontend automatically because npm/node is missing or failed.")
            print("If you run uvicorn now, the frontend UI may not load unless built manually.")
            
    # 3. Schedule browser opening
    Timer(1.5, open_browser).start()
    
    # 4. Start backend FastAPI server
    try:
        # Set PYTHONPATH so that 'src.api' can be imported correctly
        env = os.environ.copy()
        env["PYTHONPATH"] = project_dir
        
        # Start uvicorn
        cmd = [python_bin, "-m", "uvicorn", "src.api:app", "--host", "127.0.0.1", "--port", "8000"]
        print(f"Running command: {' '.join(cmd)}")
        subprocess.run(cmd, cwd=project_dir, env=env, check=True)
    except KeyboardInterrupt:
        print("\nShutdown requested by user. Exiting...")
    except Exception as e:
        print(f"Error starting server: {e}")

if __name__ == "__main__":
    main()

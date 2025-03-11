import os
import sys
import warnings
from waitress import serve
from app import create_app, scheduler
import atexit

# Suppress Flask development server warnings
if not sys.warnoptions:
    warnings.simplefilter("ignore")
    os.environ["PYTHONWARNINGS"] = "ignore"

app = create_app()

# Ensure scheduler stops when application exits
atexit.register(lambda: scheduler.shutdown(wait=False))

if __name__ == "__main__":
    print("╔═══════════════════════════════════════════════╗")
    print("║          Uptime Monitor is running!           ║")
    print("║                                               ║")
    print("║    Login with:                                ║")
    print("║    - Username: admin                          ║")
    print("║    - Password: admin                          ║")
    print("║                                               ║")
    print("║    Server running at: http://0.0.0.0:5001     ║")
    print("╚═══════════════════════════════════════════════╝")
    
    # Using waitress for production-ready server without development warnings
    serve(app, host='0.0.0.0', port=5001, threads=4)

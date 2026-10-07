"""Re-scan EDGAR for new merger proxies since the latest deal in the DB. Run manually or on a schedule.
Windows Task Scheduler (daily 07:00), run once in PowerShell from the backend folder:
  schtasks /Create /SC DAILY /ST 07:00 /TN PrecedentRefresh /TR "powershell -NoProfile -Command cd '$PWD'; .\\.venv\\Scripts\\python.exe scripts\\refresh.py"
Needs SEC_USER_AGENT set as a user environment variable (setx SEC_USER_AGENT "PrecedentFinder Your Name you@email.com")."""
import sys, subprocess, datetime as dt, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.db import rows
from app.features import refresh_window
latest = (rows("SELECT MAX(ann_date) m FROM deals") or [{"m": None}])[0]["m"]
start, end = refresh_window(latest if latest and latest != "None" else None, dt.date.today())
print(f"refreshing {start} -> {end}")
sys.exit(subprocess.call([sys.executable, "-m", "app.ingest", "--start", start, "--end", end, "--forms", "DEFM14A", "--max", "200"]))

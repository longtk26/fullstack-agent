"""Imports the app, serves it with uvicorn, and requires GET /health → 200 within the deadline."""

import subprocess
import sys
import time
import urllib.request

DEADLINE_S = 40

proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "src.main:app", "--host", "127.0.0.1", "--port", "8765"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)
deadline = time.monotonic() + DEADLINE_S
ok = False
while time.monotonic() < deadline and proc.poll() is None:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=2) as response:
            ok = response.status == 200
            break
    except Exception:
        time.sleep(0.5)
proc.terminate()
try:
    output, _ = proc.communicate(timeout=10)
except subprocess.TimeoutExpired:
    proc.kill()
    output, _ = proc.communicate()
print(output[-20000:])
print("STARTUP_OK" if ok else "STARTUP_FAILED")
sys.exit(0 if ok else 1)

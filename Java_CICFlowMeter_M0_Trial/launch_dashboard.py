"""Start the API owner and Streamlit UI with one command, both on loopback."""
import os
import secrets
import subprocess
import sys
import threading
from pathlib import Path

import uvicorn

TRIAL = Path(__file__).resolve().parent
os.environ["JAVA_M0_TRIAL_TOKEN"] = secrets.token_hex(24)
sys.path.insert(0, str(TRIAL))
from service import app, manager  # noqa: E402


def main():
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8765, log_level="warning"))
    api_thread = threading.Thread(target=server.run, daemon=True)
    api_thread.start()
    env = os.environ.copy()
    ui = subprocess.Popen([sys.executable, "-m", "streamlit", "run", str(TRIAL / "dashboard.py"),
                           "--server.address", "127.0.0.1", "--server.port", "8502"],
                          cwd=TRIAL, env=env)
    print("Java–M0/M1 dashboard: http://127.0.0.1:8502", flush=True)
    try:
        ui.wait()
    except KeyboardInterrupt:
        pass
    finally:
        if manager.phase in ("capturing", "stopping"):
            try:
                manager.stop()
                if manager.thread:
                    manager.thread.join(timeout=12)
            except Exception as exc:
                print(f"Capture cleanup: {exc}")
        if ui.poll() is None:
            ui.terminate()
            ui.wait(timeout=8)
        server.should_exit = True
        api_thread.join(timeout=8)


if __name__ == "__main__":
    main()

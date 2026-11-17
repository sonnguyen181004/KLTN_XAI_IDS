"""Short end-to-end API lifecycle check on the selected real Npcap interface."""
import os
import time
import argparse

os.environ["JAVA_M0_TRIAL_TOKEN"] = "offline-lifecycle-test"
from fastapi import HTTPException
from service import manager, list_interfaces

devices = list_interfaces()
parser = argparse.ArgumentParser()
parser.add_argument("--interface", default="WiFi", help="Part of the Npcap description, e.g. VMnet1")
args = parser.parse_args()
wifi = next(name for name, desc in devices if args.interface.lower() in desc.lower())
manager.start(wifi, 8)
try:
    assert manager.status()["phase"] == "starting"
    try:
        manager.start(wifi, 8)
        raise AssertionError("Duplicate capture start unexpectedly succeeded")
    except HTTPException as exc:
        assert exc.status_code == 409
    # Java's 8-second timer starts after Gradle startup, so do not stop it early.
    for _ in range(75):
        status = manager.status()
        if status["phase"] in ("finished", "error"):
            break
        time.sleep(1)
    assert status["phase"] == "finished", status
    assert status["packet_summary"] is not None, status
    assert "capture_started=" in manager.log_path.read_text(encoding="utf-8", errors="replace")
    assert manager.status("M1")["rows"] == status["rows"]
    assert all(len(r["probabilities"]) == 13 for r in manager.flows("M1") if r["prediction"])
    print({"phase": status["phase"], "rows": status["rows"],
           "m0_labels": status["labels"], "m1_labels": manager.status("M1")["labels"],
           "packet_summary": status["packet_summary"]})
    if status["rows"] == 0:
        print("Lifecycle/card opening verified; no flow observed, prediction path not exercised by this run.")
finally:
    if manager.status()["phase"] in ("starting", "capturing"):
        manager.stop()
    if manager.thread:
        manager.thread.join(timeout=25)

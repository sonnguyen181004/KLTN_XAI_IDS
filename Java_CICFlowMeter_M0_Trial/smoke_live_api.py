"""Short end-to-end API lifecycle check on the selected real Npcap interface."""
import os
import time

os.environ["JAVA_M0_TRIAL_TOKEN"] = "offline-lifecycle-test"
from fastapi import HTTPException
from service import manager, list_interfaces

devices = list_interfaces()
wifi = next(name for name, desc in devices if "RTL8852BE" in desc)
manager.start(wifi, 20)
try:
    try:
        manager.start(wifi, 20)
        raise AssertionError("Duplicate capture start unexpectedly succeeded")
    except HTTPException as exc:
        assert exc.status_code == 409
    time.sleep(12)  # allow Gradle startup and a few seconds of packet capture
    if manager.status()["phase"] == "capturing":
        manager.stop()
    for _ in range(40):
        status = manager.status()
        if status["phase"] in ("finished", "error"):
            break
        time.sleep(1)
    assert status["phase"] == "finished", status
    assert status["packet_summary"] is not None, status
    print({"phase": status["phase"], "rows": status["rows"],
           "labels": status["labels"], "packet_summary": status["packet_summary"]})
finally:
    if manager.status()["phase"] == "capturing":
        manager.stop()
    if manager.thread:
        manager.thread.join(timeout=25)

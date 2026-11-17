"""Render the standalone dashboard against its local API without live capture."""
import os
import csv
import threading
import time
from pathlib import Path

os.environ["JAVA_M0_TRIAL_TOKEN"] = "offline-ui-test"
import uvicorn
from streamlit.testing.v1 import AppTest
from service import app, manager

server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8765, log_level="error"))
thread = threading.Thread(target=server.run, daemon=True)
thread.start()
time.sleep(1)
try:
    state = AppTest.from_file(str(Path(__file__).parent / "dashboard.py"), default_timeout=40).run()
    assert not state.exception, [x.message for x in state.exception]
    assert state.title and "Java CICFlowMeter" in state.title[0].value
    assert state.selectbox, "Interface picker did not render"
    with (Path(__file__).parent / "output/test.pcap_Flow.csv").open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            manager._accept_row(row)
    alert = next(r for r in manager.flows() if r["prediction"] not in (None, "Benign"))
    state = state.run()
    assert not state.exception, [x.message for x in state.exception]
    assert len(state.selectbox) >= 2, "Flow selector did not render"
    state.selectbox[1].set_value(alert["id"])
    state = state.run()
    lime_button = next(b for b in state.button if b.label == "Tính LIME cho flow này")
    state = lime_button.click().run()
    assert not state.exception, [x.message for x in state.exception]
    assert manager.flow(alert["id"])["lime"] is not None
    print({"titles": [x.value for x in state.title], "selectboxes": len(state.selectbox),
           "buttons": [x.label for x in state.button], "selected_alert": alert["id"],
           "lime_status": manager.flow(alert["id"])["lime"]["status"]})
finally:
    server.should_exit = True
    thread.join(timeout=8)

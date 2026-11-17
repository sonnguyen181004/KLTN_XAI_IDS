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
import service

# UI test does not need Gradle/Npcap device enumeration.
service.list_interfaces = lambda: [(r"\Device\NPF_FAKE", "WiFi 6 test")]

server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8765, log_level="error"))
thread = threading.Thread(target=server.run, daemon=True)
thread.start()
time.sleep(1)
try:
    state = AppTest.from_file(str(Path(__file__).parent / "dashboard.py"), default_timeout=40).run()
    assert not state.exception, [x.message for x in state.exception]
    assert state.title and "Java CICFlowMeter" in state.title[0].value
    assert state.selectbox, "Interface picker did not render"
    assert state.radio and state.radio[0].value == "M0"
    with (Path(__file__).parent / "output/test.pcap_Flow.csv").open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            manager._accept_row(row)
    alert = next(r for r in manager.flows() if r["prediction"] not in (None, "Benign"))
    state = state.run()
    assert not state.exception, [x.message for x in state.exception]
    assert len(state.selectbox) >= 2, "Flow selector did not render"
    flow_picker = next(x for x in state.selectbox if x.label == "Chọn flow để xem chi tiết")
    flow_picker.set_value(alert["id"])
    state = state.run()
    lime_button = next(b for b in state.button if b.label == "Tính LIME cho flow này")
    state = lime_button.click().run()
    assert not state.exception, [x.message for x in state.exception]
    assert manager.flow(alert["id"], "M0")["lime"] is not None
    state.radio[0].set_value("M1")
    state = state.run()
    assert not state.exception, [x.message for x in state.exception]
    assert manager.status("M1")["n_classes"] == 13
    assert any("M1" in x.value for x in state.subheader if isinstance(x.value, str))
    print({"titles": [x.value for x in state.title], "selectboxes": len(state.selectbox),
           "buttons": [x.label for x in state.button], "selected_alert": alert["id"],
           "lime_status": manager.flow(alert["id"], "M0")["lime"]["status"],
           "m1_rows": manager.status("M1")["rows"]})
finally:
    server.should_exit = True
    thread.join(timeout=8)

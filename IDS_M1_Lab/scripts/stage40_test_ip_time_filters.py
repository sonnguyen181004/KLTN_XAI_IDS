"""Bộ lọc IP nguồn/đích và khoảng giờ cho giám sát (HT6.2). DB tạm, không chạm DB thật, không mở API."""
import sys
import tempfile
import unittest
from pathlib import Path

import _testdb  # noqa: F401  (đặt IDS_DB_PATH về thư mục tạm trước khi import app)

RQ3 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RQ3 / "app"))
import db  # noqa: E402
import monitoring  # noqa: E402
from alert_hints import lime_badge, shap_short  # noqa: E402

ATTACKER, VICTIM, OTHER = "192.168.56.101", "192.168.56.1", "192.168.1.6"
ROWS = [  # (id, nhận lúc, src, dst, nhãn)
    ("f1", "2026-10-20T01:00:10+00:00", ATTACKER, VICTIM, "DoS attacks-Hulk"),
    ("f2", "2026-10-20T01:05:10+00:00", ATTACKER, VICTIM, "DoS attacks-Hulk"),
    ("f3", "2026-10-20T02:00:10+00:00", ATTACKER, VICTIM, "Benign"),
    ("f4", "2026-10-20T01:03:10+00:00", OTHER, "8.8.8.8", "Benign"),
    ("f5", "2026-10-20T01:04:10+00:00", VICTIM, ATTACKER, "Benign"),
]


class IpTimeFilters(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.TemporaryDirectory()
        cls.conn = db.init_db(Path(cls.dir.name) / "filters.db")
        for flow_id, at, src, dst, label in ROWS:
            db.insert_flow(cls.conn, flow_id, at, "feeder_live", {"Dst Port": 80}, None)
            cls.conn.execute("UPDATE FlowRecord SET src_ip=?, dst_ip=? WHERE flow_id=?", (src, dst, flow_id))
            db.insert_prediction(cls.conn, flow_id, label, {label: 0.9}, "m", at)
            if label != "Benign":
                db.insert_alert(cls.conn, "a_" + flow_id, flow_id, "g", label, at)
        cls.conn.commit()

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        cls.dir.cleanup()

    def ids(self, **filters):
        return sorted(f["flow_id"] for f in monitoring.flows(self.conn, filters)["flows"])

    def test_source_ip_separates_attacker_traffic(self):
        self.assertEqual(self.ids(src_ip=ATTACKER), ["f1", "f2", "f3"])
        self.assertEqual(self.ids(src_ip=OTHER), ["f4"])

    def test_destination_ip_and_combination(self):
        self.assertEqual(self.ids(dst_ip=ATTACKER), ["f5"])
        self.assertEqual(self.ids(src_ip=ATTACKER, dst_ip=VICTIM, alerts_only=True), ["f1", "f2"])

    def test_time_window_with_ip(self):
        window = dict(since="2026-10-20T01:00:00+00:00", until="2026-10-20T01:10:00+00:00")
        self.assertEqual(self.ids(src_ip=ATTACKER, **window), ["f1", "f2"])
        self.assertEqual(self.ids(**window), ["f1", "f2", "f4", "f5"])

    def test_summary_counts_follow_the_same_scope(self):
        summary = monitoring.summary(self.conn, dict(src_ip=ATTACKER))
        self.assertEqual((summary["flows"], summary["alerts"], summary["benign"]), (3, 2, 1))

    def test_lime_validity_counts_only_checked_runs_per_source(self):
        import json
        for alert, status in (("a_f1", "ok"), ("a_f2", "insufficient_neighborhood")):
            db.upsert_reliability(self.conn, alert, lime_diagnostics_json=json.dumps({"status": status}))
        self.conn.commit()
        sources = {r["source"]: (r["ran"], r["valid"]) for r in monitoring.lime_validity(self.conn)["sources"]}
        self.assertEqual(sources, {"feeder_live": (2, 1)})

    def test_api_validation_rejects_bad_ip_and_normalizes(self):
        import main
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as caught:
            main.monitor_filters(src_ip="999.1.1.1")
        self.assertEqual(caught.exception.status_code, 422)
        with self.assertRaises(HTTPException):
            main.monitor_filters(dst_ip="not-an-ip")
        self.assertEqual(main.monitor_filters(src_ip=" 192.168.56.101 ")["src_ip"], ATTACKER)
        self.assertEqual(main.monitor_filters(src_ip="::1")["src_ip"], "::1")
        self.assertIsNone(main.monitor_filters(src_ip="")["src_ip"])
        with self.assertRaises(HTTPException):  # Từ sau Đến
            main.monitor_filters(since="2026-10-20T02:00:00+00:00", until="2026-10-20T01:00:00+00:00")


class ShortLabels(unittest.TestCase):
    def test_table_labels_are_short(self):
        alert = dict(is_alert=True)
        self.assertEqual(lime_badge({**alert, "lime_status": "insufficient_neighborhood"}, short=True), "Không tin cậy")
        self.assertEqual(lime_badge({**alert, "lime_status": "not_requested"}, short=True), "Chưa")
        self.assertEqual(lime_badge({**alert, "lime_status": "ok"}, short=True), "Hợp lệ")
        self.assertEqual(shap_short({**alert, "explanation_status": "processed"}), "Có")
        self.assertEqual(shap_short({**alert, "explanation_status": "queued"}), "Chờ")
        self.assertEqual(shap_short({**alert, "explanation_status": "dropped_queue_full"}), "Bỏ")
        self.assertEqual(shap_short(dict(is_alert=False)), "—")


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Hàng đợi giải thích bất đồng bộ (đúng kiến trúc Làn B, bước "Vào hàng đợi" +
"Lưu tác vụ XAI"): /predict TẠO Alert và TRẢ LỜI NGAY, không chờ SHAP tính xong.
SHAP được tính trong 1 THREAD NỀN riêng, đọc việc cần làm từ 1 hàng đợi có giới
hạn (mặc định 50, lấy từ config `api.max_explain_queue`).

Nếu hàng đợi ĐẦY: bỏ việc giải thích (không chặn, không chờ), NHƯNG Alert vẫn
đã được tạo và trả về cho analyst từ trước — đúng nguyên tắc "đầy thì bỏ giải
thích, giữ cảnh báo".
"""
from __future__ import annotations

import json
import queue
import threading
import time
from datetime import datetime, timezone

import pandas as pd


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExplainQueue:
    def __init__(self, maxsize: int, shap_explainer, reliability_scorer, db_module, db_path):
        self._q: queue.Queue = queue.Queue(maxsize=maxsize)
        self.maxsize = maxsize
        self.shap_explainer = shap_explainer
        self.reliability_scorer = reliability_scorer
        self.db = db_module
        self.db_path = db_path
        self.n_queued = 0
        self.n_dropped = 0
        self.n_processed = 0
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def submit(self, alert_id: str, flow_id: str, predicted_label: str, normalized_row: pd.DataFrame) -> str:
        """Trả về 'queued' nếu đưa vào hàng đợi thành công, 'dropped_queue_full' nếu
        hàng đợi đã đầy (CHỈ bỏ phần giải thích — Alert đã được tạo từ trước đó rồi)."""
        task = {
            "alert_id": alert_id, "flow_id": flow_id,
            "predicted_label": predicted_label, "normalized_row": normalized_row,
            "enqueued_at": time.perf_counter(),
        }
        try:
            self._q.put_nowait(task)
            self.n_queued += 1
            return "queued"
        except queue.Full:
            self.n_dropped += 1
            return "dropped_queue_full"

    def qsize(self) -> int:
        return self._q.qsize()

    def _run(self) -> None:
        while True:
            task = self._q.get()  # chờ (block) tới khi có việc, không tốn CPU lúc rỗng
            try:
                self._process(task)
            except Exception as e:  # noqa: BLE001 — worker nền không được chết vì 1 task lỗi
                print(f"[explain_queue] Lỗi khi xử lý alert_id={task['alert_id']}: {e}")
            finally:
                self._q.task_done()

    def _process(self, task: dict) -> None:
        wait_ms = (time.perf_counter() - task["enqueued_at"]) * 1000
        t0 = time.perf_counter()
        shap_result = self.shap_explainer.explain(task["normalized_row"], task["predicted_label"], top_k=5)
        shap_ms = (time.perf_counter() - t0) * 1000

        # Bước 8 — Đánh giá độ tin cậy + gắn cờ: chạy NGAY SAU SHAP, dùng Top-5 SHAP
        # vừa tính làm input (xem app/reliability.py).
        t0 = time.perf_counter()
        reliability_result = self.reliability_scorer.score(
            task["normalized_row"], task["predicted_label"], shap_result["top_k"],
        )
        reliability_ms = (time.perf_counter() - t0) * 1000

        conn = self.db.get_connection(self.db_path)
        try:
            self.db.upsert_reliability(
                conn, task["alert_id"],
                shap_top5_json=json.dumps(shap_result["top_k"]),
                faithfulness_proxy_drop=reliability_result["faithfulness_proxy_drop"],
                env_fingerprint_count=reliability_result["env_fingerprint_count"],
                env_fingerprint_flag=reliability_result["env_fingerprint_flag"],
                rare_class_flag=reliability_result["rare_class_flag"],
                branch=reliability_result["branch"],
                branch_reason=reliability_result["branch_reason"],
            )
            self.db.insert_timing(conn, task["flow_id"], "shap_queue_wait", wait_ms, now_iso())
            self.db.insert_timing(conn, task["flow_id"], "shap", shap_ms, now_iso())
            self.db.insert_timing(conn, task["flow_id"], "reliability", reliability_ms, now_iso())
        finally:
            conn.close()
        self.n_processed += 1

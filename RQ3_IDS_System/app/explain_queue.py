"""Hàng đợi giải thích bất đồng bộ (đúng kiến trúc Làn B, bước "Vào hàng đợi" +
"Lưu tác vụ XAI"): /predict TẠO Alert và TRẢ LỜI NGAY, không chờ SHAP tính xong.
SHAP được tính trong 1 THREAD NỀN riêng, đọc việc cần làm từ 1 hàng đợi có giới
hạn (hiện cấu hình 200 tác vụ chờ, lấy từ `api.max_explain_queue`).

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
    def __init__(self, maxsize: int, shap_explainer, reliability_scorer, db_module, db_path,
                 recovery_feature_names=None, model_version=None):
        self._q: queue.Queue = queue.Queue(maxsize=maxsize)
        self.maxsize = maxsize
        self.shap_explainer = shap_explainer
        self.reliability_scorer = reliability_scorer
        self.db = db_module
        self.db_path = db_path
        self.n_queued = 0
        self.n_dropped = 0
        self.n_processed = 0
        self.n_recovered = 0
        self.recovery_feature_names = recovery_feature_names
        self.model_version = model_version
        if recovery_feature_names is not None:
            if model_version is None:
                raise ValueError('SHAP recovery requires model_version')
            # Prevent a second API process from treating this worker's live jobs
            # as interrupted. OS releases the lock even after a hard process exit.
            from ingestion_checkpoint import checkpoint_lock
            self._ownership = checkpoint_lock(str(db_path) + '.worker')
            try:
                self._ownership.__enter__()
            except RuntimeError as exc:
                raise RuntimeError('DB đang được một API worker khác sử dụng. Chạy một tiến trình API cho mỗi DB.') from exc
            # Deployment contract: ONE API process owns the explanation worker.
            # Reconstruct interrupted jobs from saved alerts/features, not RAM.
            conn = self.db.get_connection(self.db_path)
            try:
                conn.execute("""UPDATE AlertRecord SET explanation_status='recovery_pending'
                    WHERE explanation_status IN ('queued','pending_dispatch')""")
                conn.execute("""UPDATE AlertRecord SET explanation_status='processed'
                    WHERE explanation_status='recovery_pending' AND alert_id IN
                    (SELECT alert_id FROM Reliability WHERE shap_top5_json IS NOT NULL)""")
                conn.execute("""UPDATE AlertRecord SET explanation_status='failed'
                    WHERE explanation_status='recovery_pending' AND flow_id IN
                    (SELECT flow_id FROM Prediction WHERE model_version != ?)""", (model_version,))
                conn.commit()
            finally:
                conn.close()
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
            self._set_status(alert_id, 'queued')
            self._q.put_nowait(task)
            self.n_queued += 1
            return "queued"
        except queue.Full:
            self._set_status(alert_id, 'dropped_queue_full')
            self.n_dropped += 1
            return "dropped_queue_full"

    def qsize(self) -> int:
        return self._q.qsize()

    def recovery_pending(self):
        conn = self.db.get_connection(self.db_path)
        try:
            return conn.execute("SELECT COUNT(*) FROM AlertRecord WHERE explanation_status='recovery_pending'").fetchone()[0]
        finally:
            conn.close()

    def _take_recovery(self):
        if self.recovery_feature_names is None:
            return None
        conn = self.db.get_connection(self.db_path)
        try:
            row = conn.execute("""SELECT a.alert_id,a.flow_id,a.predicted_label,f.features_json
                FROM AlertRecord a JOIN FlowRecord f ON f.flow_id=a.flow_id
                WHERE a.explanation_status='recovery_pending' ORDER BY a.created_at LIMIT 1""").fetchone()
            if row is None:
                return None
            claimed = conn.execute("UPDATE AlertRecord SET explanation_status='queued' WHERE alert_id=? AND explanation_status='recovery_pending'", (row[0],)).rowcount
            conn.commit()
            if not claimed:
                return None
            try:
                from normalize import normalize_flow
                normalized = normalize_flow(json.loads(row[3]), self.recovery_feature_names)
            except Exception:
                conn.execute("UPDATE AlertRecord SET explanation_status='failed' WHERE alert_id=?", (row[0],))
                conn.commit()
                raise
            self.n_recovered += 1
            return dict(alert_id=row[0], flow_id=row[1], predicted_label=row[2],
                        normalized_row=normalized, enqueued_at=time.perf_counter(), recovered=True)
        finally:
            conn.close()

    def _set_status(self, alert_id, status):
        conn = self.db.get_connection(self.db_path)
        try:
            conn.execute('UPDATE AlertRecord SET explanation_status=? WHERE alert_id=?', (status, alert_id))
            conn.commit()
        finally:
            conn.close()

    def _run(self) -> None:
        while True:
            from_memory = True
            try:
                task = self._q.get(timeout=1)
            except queue.Empty:
                from_memory = False
                try:
                    task = self._take_recovery()
                except Exception as exc:
                    print(f'[explain_queue] Recovery failed: {exc}')
                    continue
                if task is None:
                    continue
            try:
                self._process(task)
            except Exception as e:  # noqa: BLE001 — worker nền không được chết vì 1 task lỗi
                print(f"[explain_queue] Lỗi khi xử lý alert_id={task['alert_id']}: {e}")
                try:
                    self._set_status(task['alert_id'], 'failed')
                except Exception as status_error:
                    print(f'[explain_queue] Không ghi được trạng thái lỗi: {status_error}')
            finally:
                if from_memory:
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
            # Recovery wait starts at this process's claim, not before downtime.
            wait_step = 'shap_recovery_wait' if task.get('recovered') else 'shap_queue_wait'
            self.db.insert_timing(conn, task["flow_id"], wait_step, wait_ms, now_iso())
            self.db.insert_timing(conn, task["flow_id"], "shap", shap_ms, now_iso())
            self.db.insert_timing(conn, task["flow_id"], "reliability", reliability_ms, now_iso())
        finally:
            conn.close()
        self.n_processed += 1
        self._set_status(task['alert_id'], 'processed')

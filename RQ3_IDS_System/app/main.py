"""Tầng 6 (phần API) — FastAPI, ghép tầng 2 (chuẩn hóa) + tầng 3 (dự đoán) + ghi DB.

Chạy thử: uvicorn app.main:app --reload --port 8000  (chạy từ thư mục RQ3_IDS_System/)
"""
from __future__ import annotations

import hashlib
import json
import os
from ipaddress import ip_address
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import yaml
from fastapi import FastAPI, HTTPException, Query, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402
import monitoring
from flow_metadata import timestamp_utc
from feature_reference import FeatureReference
from normalize import normalize_flow, FlowValidationError  # noqa: E402
from predict import Detector  # noqa: E402
from explain_shap import ShapExplainer  # noqa: E402
from explain_lime import LimeExplainer  # noqa: E402
from reliability import ReliabilityScorer  # noqa: E402
from explain_queue import ExplainQueue  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
RQ3_ROOT = Path(__file__).resolve().parents[1]


def load_config() -> dict:
    with open(RQ3_ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---- Khởi tạo 1 lần lúc server bật lên --------------------------------------------
cfg = load_config()
detector = Detector(REPO_ROOT / cfg["paths"]["model"], REPO_ROOT / cfg["paths"]["label_encoder"])
shap_explainer = ShapExplainer(detector.model, detector.class_names)
DB_PATH = Path(os.environ.get('IDS_DB_PATH', str(REPO_ROOT / cfg['paths']['sqlite_db'])))
db.init_db(DB_PATH).close()

# Bước 8 — thống kê train tính sẵn 1 lần (median toàn cục + số mẫu/lớp), xem
# scripts/stage08_compute_train_stats.py. Phải chạy script đó trước khi bật server.
TRAIN_STATS_PATH = RQ3_ROOT / "data" / "train_stats.json"
with open(TRAIN_STATS_PATH, encoding="utf-8") as f:
    train_stats = json.load(f)

reliability_scorer = ReliabilityScorer(
    detector=detector,
    global_median=train_stats["global_median"],
    train_samples_per_class=train_stats["train_samples_per_class"],
    env_fingerprint_features=cfg["environment_fingerprint_features"],
    env_fingerprint_flag_threshold=cfg["environment_fingerprint_flag_threshold"],
    rare_class_min_train_samples=cfg["rare_class_min_train_samples"],
    faithfulness_k=cfg["faithfulness_proxy"]["k"],
)

# Hàng đợi giải thích bất đồng bộ (đúng kiến trúc bước "Vào hàng đợi" — xem app/explain_queue.py).
# /predict KHÔNG gọi SHAP trực tiếp nữa; chỉ đưa việc vào đây rồi trả lời ngay.
explain_queue = ExplainQueue(
    maxsize=cfg["api"]["max_explain_queue"],
    shap_explainer=shap_explainer,
    reliability_scorer=reliability_scorer,
    db_module=db,
    db_path=DB_PATH,
    recovery_feature_names=detector.feature_names,
    model_version=detector.model_version,
)

# Bước 9 — LIME theo yêu cầu. Nền 2.000 dòng tính sẵn ở scripts/stage09_compute_lime_background.py
# (phải chạy script đó trước khi bật server).
LIME_BACKGROUND_PATH = RQ3_ROOT / "data" / "lime_background.npy"
lime_background = np.load(LIME_BACKGROUND_PATH)
feature_reference = FeatureReference(detector.feature_names, lime_background,
                                     REPO_ROOT / cfg['paths']['clean_set_out'])
lime_explainer = LimeExplainer(
    model=detector.model,
    feature_names=detector.feature_names,
    class_names=detector.class_names,
    background=lime_background,
    lime_cfg=cfg["lime"],
    base_seed=cfg["seed"],
)
# LIME chạy ĐỒNG BỘ trong request /explain (analyst đang chờ), không qua hàng đợi nền
# như SHAP — giới hạn số lượt chạy cùng lúc bằng semaphore, vượt ngưỡng thì 429.
lime_semaphore = threading.Semaphore(cfg["api"]["max_concurrent_lime"])


def jaccard_at_k(rank_a: list[str], rank_b: list[str], k: int) -> float:
    """Jaccard@k giữa 2 tập Top-k — ĐÚNG cách RQ2 tính Agreement (xem
    RQ2/scripts/stage07_agreement.py): so trực tiếp tên đặc trưng SHAP (sạch) với
    feature_desc thô của LIME (có thể kèm bất đẳng thức, vd "Dst Port <= 8080.00"),
    KHÔNG tự "sửa" để khớp đẹp hơn — đây là lý do Jaccard@5 trung bình RQ2 chỉ 0,141."""
    sa, sb = set(rank_a[:k]), set(rank_b[:k])
    union = sa | sb
    return len(sa & sb) / len(union) if union else float("nan")


app = FastAPI(title="RQ3 IDS System API")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": detector.model is not None,
        "model_version": detector.model_version,
        "n_features_expected": len(detector.feature_names),
        "n_classes": len(detector.class_names),
        "class_names": detector.class_names,
        "ingestion_idempotency": True,
    }


@app.post("/predict")
def predict(flow: Dict[str, float], source: str = "api", flow_timestamp: Optional[str] = None,
            capture_run_id: Optional[str] = Query(None, max_length=128),
            run_name: Optional[str] = Query(None, max_length=200),
            src_ip: Optional[str] = None, dst_ip: Optional[str] = None,
            src_port: Optional[int] = Query(None, ge=0, le=65535),
            capture_timezone: Optional[str] = None,
            extractor_version: Optional[str] = Query(None, max_length=128),
            idempotency_key: Optional[str] = Header(None, alias='Idempotency-Key', min_length=1, max_length=256)):
    """`source`/`flow_timestamp` là 2 tham số query TÙY CHỌN, KHÔNG thuộc 78 đặc
    trưng — thêm sau khi test thực tế: khi phát lại CSV/PCAP cũ, mọi flow được XỬ
    LÝ gần như cùng lúc (lúc bạn bấm gửi), nếu chỉ lưu "lúc xử lý" thì Dashboard
    hiện giờ hiện tại dồn cục cho hàng chục flow, không phản ánh đúng thứ tự traffic
    THẬT đã xảy ra, gây khó hiểu khi xem bảng cảnh báo. `source` cho biết flow tới
    từ đâu (csv_upload/pcap_replay/feeder_live/api) để phân biệt các đợt gửi khác
    nhau trên Dashboard."""
    try:
        src_ip = str(ip_address(src_ip)) if src_ip else None
        dst_ip = str(ip_address(dst_ip)) if dst_ip else None
        utc_time = timestamp_utc(flow_timestamp, capture_timezone)
    except ValueError as exc:
        raise HTTPException(422, f'Metadata không hợp lệ: {exc}') from exc
    received_at = now_iso()
    flow_id = str(uuid.uuid4())
    t_start = time.perf_counter()
    # Mở 1 connection RIÊNG cho request này (xem lý do trong app/db.py::get_connection).
    conn = db.get_connection(DB_PATH)
    try:
        # ---- Tầng 2: chuẩn hóa ------------------------------------------------------
        # Lỗi (422) thì KHÔNG ghi FlowRecord/Timing — flow coi như chưa vào hệ thống,
        # chỉ ghi vào DataError.
        t0 = time.perf_counter()
        try:
            normalized = normalize_flow(flow, detector.feature_names, convert_seconds_to_microseconds=False)
        except FlowValidationError as e:
            db.insert_error(conn, flow_id, now_iso(), 422, e.reason, flow)
            raise HTTPException(status_code=422, detail={"reason": e.reason, **e.details})
        t_normalize_ms = (time.perf_counter() - t0) * 1000

        features = normalized.iloc[0].to_dict()
        metadata = dict(source=source, flow_timestamp=flow_timestamp, flow_timestamp_utc=utc_time,
                        capture_run_id=capture_run_id, run_name=run_name, src_ip=src_ip,
                        dst_ip=dst_ip, src_port=src_port, extractor_version=extractor_version)
        fingerprint = hashlib.sha256(json.dumps({'features': features, 'metadata': metadata},
            sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        headers = {'Idempotency-Key': idempotency_key} if idempotency_key else {}
        existing = db.ingestion_response(conn, idempotency_key, fingerprint)
        if existing is not None:
            return JSONResponse(existing, headers={**headers, 'Idempotency-Replayed': 'true'})

        # Tầng 3. Commit core records together before asynchronous explanation.
        t0 = time.perf_counter()
        result = detector.predict_flow(normalized)
        t_predict_ms = (time.perf_counter() - t0) * 1000
        alert_id = str(uuid.uuid4()) if result['predicted_label'] != 'Benign' else None
        body = dict(flow_id=flow_id, **result, is_alert=alert_id is not None, alert_id=alert_id,
                    explanation_status='pending_dispatch' if alert_id else None,
                    timing_ms={'normalize': round(t_normalize_ms, 3), 'predict': round(t_predict_ms, 3)})
        body, created = db.persist_prediction(conn, body, features, metadata, received_at, now_iso(),
                                             idempotency_key, fingerprint, t_start)
        if created and alert_id:
            try:
                body['explanation_status'] = explain_queue.submit(alert_id, flow_id, result['predicted_label'], normalized)
            except Exception as exc:
                # Core prediction is durable. Do not convert a dispatch failure
                # into a failed ingestion acknowledgement; expose it explicitly.
                conn.execute("UPDATE AlertRecord SET explanation_status='failed' WHERE alert_id=?", (alert_id,))
                conn.commit()
                body['explanation_status'] = 'failed'
                print(f'[predict] SHAP dispatch failed for {alert_id}: {exc}')
        return JSONResponse(body, headers={**headers, 'Idempotency-Replayed': 'false' if created else 'true'})
    except db.IngestionConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    finally:
        conn.close()


class ExplainRequest(BaseModel):
    alert_id: str
    method: str = "lime"


@app.post("/explain")
def explain(req: ExplainRequest):
    if req.method != "lime":
        raise HTTPException(status_code=400, detail=f"method '{req.method}' không hỗ trợ — chỉ nhận 'lime' "
                                                      "(SHAP đã tự động chạy ở /predict, không cần xin lại qua đây).")

    conn = db.get_connection(DB_PATH)
    try:
        alert = db.get_alert(conn, req.alert_id)
        if alert is None:
            raise HTTPException(status_code=404, detail=f"Không có alert_id={req.alert_id}")

        if not lime_semaphore.acquire(blocking=False):
            raise HTTPException(status_code=429, detail="Đang có quá nhiều lượt LIME chạy cùng lúc, thử lại sau.")
        try:
            t_start = time.perf_counter()
            features = db.get_flow_features(conn, alert["flow_id"])
            normalized = normalize_flow(features, detector.feature_names, convert_seconds_to_microseconds=False)

            # Seed riêng theo từng alert (đúng nguyên tắc RQ2: tái lập được độc lập mỗi
            # flow) — alert_id là UUID (chuỗi), không phải số nguyên như cohort RQ2, nên
            # băm ra 1 số nguyên ổn định thay vì dùng hash() (có PYTHONHASHSEED ngẫu nhiên).
            flow_seed_key = int(hashlib.sha256(req.alert_id.encode()).hexdigest()[:8], 16)

            lime_result = lime_explainer.explain(normalized, alert["predicted_label"], flow_seed_key, top_k=5)
            t_lime_ms = (time.perf_counter() - t_start) * 1000

            shap_top5 = db.get_shap_top5(conn, req.alert_id)
            agreement = None
            if shap_top5 is not None and lime_result['status'] == 'ok':
                shap_rank = [item["feature"] for item in shap_top5]
                lime_rank = [item["feature_desc"] for item in lime_result["top_k"]]
                agreement = jaccard_at_k(shap_rank, lime_rank, k=5)

            db.upsert_reliability(
                conn, req.alert_id,
                lime_top5_json=json.dumps(lime_result["top_k"]),
                agreement_jaccard5=agreement,
                lime_local_r2=lime_result['local_r2'],
                lime_diagnostics_json=json.dumps(lime_result['diagnostics']),
            )
            db.insert_timing(conn, alert["flow_id"], "lime", t_lime_ms, now_iso())
        finally:
            lime_semaphore.release()
    finally:
        conn.close()

    return JSONResponse({
        "alert_id": req.alert_id,
        "class_explained": lime_result["class_explained"],
        "local_r2": lime_result["local_r2"],
        "status": lime_result['status'],
        "diagnostics": lime_result['diagnostics'],
        "top_k": lime_result["top_k"],
        "agreement_jaccard5": agreement,
        "timing_ms": {"lime": round(t_lime_ms, 3)},
    })


@app.get("/alerts")
def list_alerts(
    since: Optional[str] = None, until: Optional[str] = None,
    label: Optional[str] = None, branch: Optional[str] = None,
    capture_run_id: Optional[str] = None, source: Optional[str] = None,
    limit: int = Query(200, ge=1, le=1000), offset: int = Query(0, ge=0),
):
    """Bước 12 — Tầng 6: danh sách Alert kèm trạng thái giải thích, lọc theo
    thời gian nhận (`since`/`until`, ISO 8601 có múi giờ),
    nhãn (`label` = predicted_label) và nhánh (`branch`
    = 'A'/'B', đúng bảng API trong tài liệu kiến trúc)."""
    if branch is not None and branch not in ("A", "B"):
        raise HTTPException(status_code=422, detail="branch chỉ nhận 'A' hoặc 'B'")

    conn = db.get_connection(DB_PATH)
    try:
        result = monitoring.flows(conn, monitor_filters(since, until, label, branch,
                                  source, capture_run_id, True, None), limit, offset)
    finally:
        conn.close()
    # Preserve completed explanation names for existing /alerts consumers.
    for alert in result['flows']:
        if alert['shap_top5']:
            alert['explanation_status'] = 'shap_and_lime' if alert['lime_top5'] else 'shap_only'
    return {'count': result['count'], 'alerts': result['flows']}


@app.get("/flows")
def list_flows(
    since: Optional[str] = None, until: Optional[str] = None,
    label: Optional[str] = None, limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0), capture_run_id: Optional[str] = None,
    source: Optional[str] = None, branch: Optional[str] = Query(None, pattern='^[AB]$'),
    alerts_only: bool = False, group_key: Optional[str] = None,
):
    """Bổ sung ngoài 4 điểm gọi gốc trong tài liệu kiến trúc (POST /predict, POST
    /explain, GET /alerts, GET /health) — theo yêu cầu thực tế khi test: `GET
    /alerts` CHỈ trả Alert (nhãn khác Benign), nên flow Benign (bình thường,
    không tấn công) không bao giờ xuất hiện ở đó. Dashboard cần thấy CẢ traffic
    bình thường để biết hệ thống có đang hoạt động, không chỉ thấy mỗi cảnh báo."""
    conn = db.get_connection(DB_PATH)
    try:
        result = monitoring.flows(conn, monitor_filters(since, until, label, branch, source,
                                  capture_run_id, alerts_only, group_key), limit, offset)
    finally:
        conn.close()
    return result


def monitor_filters(since: Optional[str] = None, until: Optional[str] = None,
                    label: Optional[str] = None, branch: Optional[str] = Query(None, pattern='^[AB]$'),
                    source: Optional[str] = None, capture_run_id: Optional[str] = None,
                    alerts_only: bool = False, group_key: Optional[str] = None):
    try:
        times = {key: timestamp_utc(value) for key, value in [('since', since), ('until', until)]}
        if (since and not times['since']) or (until and not times['until']):
            raise ValueError('Mốc lọc phải kèm múi giờ')
        if times['since'] and times['until'] and times['since'] > times['until']:
            raise ValueError('Từ thời gian phải trước Đến thời gian')
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return dict(**times, label=label, branch=branch, source=source,
                capture_run_id=capture_run_id, alerts_only=alerts_only, group_key=group_key)


def read_monitor(function, *args):
    conn = db.get_connection(DB_PATH)
    try:
        return function(conn, *args)
    finally:
        conn.close()


@app.get('/runs')
def list_runs():
    return read_monitor(monitoring.runs)


@app.get('/dashboard/summary')
def dashboard_summary(filters: dict = Depends(monitor_filters)):
    return read_monitor(monitoring.summary, filters)


@app.get('/flows/{flow_id}')
def flow_detail(flow_id: str):
    result = read_monitor(monitoring.detail, flow_id)
    if result is None:
        raise HTTPException(404, 'Không có flow này')
    return result


@app.get('/flows/{flow_id}/comparison')
def flow_comparison(flow_id: str):
    return feature_reference.compare(flow_detail(flow_id))


@app.get("/explain_queue_status")
def explain_queue_status():
    """Chỉ để quan sát/debug: xem hàng đợi giải thích đang ở trạng thái nào."""
    return {
        "qsize": explain_queue.qsize(),
        "maxsize": explain_queue.maxsize,
        "n_queued": explain_queue.n_queued,
        "n_processed": explain_queue.n_processed,
        "n_dropped": explain_queue.n_dropped,
        "n_recovered": explain_queue.n_recovered,
        "recovery_pending": explain_queue.recovery_pending(),
    }

"""Schema SQLite cho hệ thống IDS (RQ3) — 6 bảng theo đúng "Thực thể dữ liệu"
trong tài liệu kiến trúc. Dùng sqlite3 chuẩn của Python (không ORM) để đơn giản,
dễ đọc, dễ debug bằng tay (mở file .db bằng bất kỳ công cụ SQLite nào).

78 đặc trưng của một flow được lưu gộp thành 1 cột JSON (`features_json`) thay vì
78 cột riêng — vì tên đặc trưng có khoảng trắng/dấu "/" (ví dụ "Flow Byts/s") rất
phiền khi đặt tên cột SQL, và hệ thống không cần lọc theo từng đặc trưng bằng SQL,
chỉ cần đọc nguyên khối 78 số để đưa vào model.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS FlowRecord (
    flow_id         TEXT PRIMARY KEY,
    received_at     TEXT NOT NULL,      -- lúc API xử lý xong request này (giờ hệ thống, KHÔNG phải lúc gói tin thật xảy ra)
    source          TEXT NOT NULL,      -- 'csv_upload' | 'pcap_replay' | 'feeder_live' | 'api' (Swagger/test tay) | 'rq2_cohort' | 'clean_set'
    flow_timestamp  TEXT,               -- lúc gói tin THẬT được bắt (cột "timestamp" CICFlowMeter ghi) — NULL nếu nguồn không có (vd Tập A/B)
    features_json   TEXT NOT NULL,      -- JSON: {"Dst Port": 80, "Protocol": 6, ...} đúng 78 đặc trưng
    label_true      TEXT                -- nhãn thật nếu biết trước (Tập A/B); NULL nếu traffic thật
);

CREATE TABLE IF NOT EXISTS DataError (
    error_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id         TEXT NOT NULL,
    occurred_at     TEXT NOT NULL,
    error_code      INTEGER NOT NULL,   -- 422 = thiếu cột / NaN
    reason          TEXT NOT NULL,
    raw_input_json  TEXT
);

CREATE TABLE IF NOT EXISTS Prediction (
    flow_id             TEXT PRIMARY KEY REFERENCES FlowRecord(flow_id),
    predicted_label     TEXT NOT NULL,
    probabilities_json  TEXT NOT NULL,  -- JSON: {"Benign": 0.01, "Bot": 0.97, ...} 15 lớp
    model_version       TEXT NOT NULL,
    predicted_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS AlertRecord (
    alert_id        TEXT PRIMARY KEY,
    flow_id         TEXT NOT NULL REFERENCES FlowRecord(flow_id),
    group_key       TEXT NOT NULL,      -- khóa gộp cảnh báo cùng loại (vd: theo predicted_label)
    predicted_label TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'new',  -- 'new' | 'explained' | 'reviewed'
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Reliability (
    alert_id                TEXT PRIMARY KEY REFERENCES AlertRecord(alert_id),
    shap_top5_json          TEXT,       -- JSON list [[feature, value, phi], ...]
    lime_top5_json          TEXT,       -- NULL cho tới khi analyst bấm xin LIME
    agreement_jaccard5      REAL,       -- chỉ có khi đã chạy LIME
    faithfulness_proxy_drop REAL,       -- PROXY nhanh — không phải phép đo đầy đủ của RQ2
    env_fingerprint_count   INTEGER NOT NULL DEFAULT 0,  -- đếm trong Top-5 (0..5)
    env_fingerprint_flag    INTEGER NOT NULL DEFAULT 0,  -- 0/1 — chỉ là cờ cảnh báo, không phải bằng chứng
    rare_class_flag         INTEGER NOT NULL DEFAULT 0,  -- 0/1
    stability_lookup        REAL,       -- tra sẵn theo lớp từ RQ2 (rq2_master_summary.json)
    robustness_lookup_json  TEXT,       -- tra sẵn theo lớp từ RQ2
    branch                  TEXT,       -- 'A' | 'B'
    branch_reason           TEXT
);

CREATE TABLE IF NOT EXISTS Timing (
    timing_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id         TEXT NOT NULL REFERENCES FlowRecord(flow_id),
    step            TEXT NOT NULL,      -- 'normalize' | 'predict' | 'shap' | 'lime' | 'reliability'
    duration_ms     REAL NOT NULL,
    recorded_at     TEXT NOT NULL
);
"""

TABLE_NAMES = ["FlowRecord", "DataError", "Prediction", "AlertRecord", "Reliability", "Timing"]


def init_db(db_path: str | Path) -> sqlite3.Connection:
    """Tạo file DB (nếu chưa có) và đủ 6 bảng. Gọi lại nhiều lần an toàn (IF NOT EXISTS)."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=10.0)
    conn.execute("PRAGMA foreign_keys = ON")
    # WAL: cho phép nhiều connection đọc/ghi đồng thời mà ít khóa nhau hơn mode
    # mặc định (rollback journal). Cần thiết khi nhiều request /predict tới cùng
    # lúc (traffic thật dồn dập) — nếu không, lỗi thật đã gặp khi test:
    # "sqlite3.OperationalError: database is locked".
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA_SQL)
    _migrate_add_flow_timestamp(conn)
    conn.commit()
    return conn


def _migrate_add_flow_timestamp(conn: sqlite3.Connection) -> None:
    """DB tạo từ trước khi có cột `flow_timestamp` (thêm sau, để phân biệt lúc gói
    tin THẬT xảy ra với lúc hệ thống xử lý) sẽ thiếu cột này — `CREATE TABLE IF NOT
    EXISTS` không tự thêm cột cho bảng đã có sẵn. An toàn gọi lại nhiều lần."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(FlowRecord)").fetchall()]
    if "flow_timestamp" not in cols:
        conn.execute("ALTER TABLE FlowRecord ADD COLUMN flow_timestamp TEXT")


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    """Mở 1 connection MỚI tới DB đã có sẵn bảng (không chạy lại CREATE TABLE).

    QUAN TRỌNG: sqlite3.Connection KHÔNG được dùng xuyên thread (mặc định
    check_same_thread=True). FastAPI chạy mỗi request sync trong 1 thread riêng
    từ thread pool, nên app/main.py phải gọi hàm này để mở 1 connection RIÊNG
    cho MỖI request rồi đóng lại — không dùng chung 1 connection toàn cục.

    `timeout=10.0`: nếu DB đang bị 1 connection khác khóa để ghi, CHỜ tối đa 10
    giây rồi mới báo lỗi, thay vì báo lỗi ngay (mặc định sqlite3 timeout=5s
    nhưng vẫn có thể không đủ khi nhiều request tới đồng thời — đã gặp lỗi thật
    "database is locked" khi dội 70 request song song lúc test bước 7b).
    """
    db_path = Path(db_path)
    conn = sqlite3.connect(str(db_path), timeout=10.0)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def list_tables(conn: sqlite3.Connection) -> list[str]:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [r[0] for r in cur.fetchall()]


def table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return [r[1] for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Hàm ghi dữ liệu — dùng chung bởi app/main.py (API) và các script test.
# ---------------------------------------------------------------------------

def insert_flow(conn, flow_id: str, received_at: str, source: str, features: dict, label_true: str | None,
                 flow_timestamp: str | None = None) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO FlowRecord (flow_id, received_at, source, flow_timestamp, features_json, label_true) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (flow_id, received_at, source, flow_timestamp, json.dumps(features), label_true),
    )
    conn.commit()


def insert_error(conn, flow_id: str, occurred_at: str, error_code: int, reason: str, raw_input: dict) -> None:
    conn.execute(
        "INSERT INTO DataError (flow_id, occurred_at, error_code, reason, raw_input_json) "
        "VALUES (?, ?, ?, ?, ?)",
        (flow_id, occurred_at, error_code, reason, json.dumps(raw_input)),
    )
    conn.commit()


def insert_prediction(conn, flow_id: str, predicted_label: str, probabilities: dict,
                       model_version: str, predicted_at: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO Prediction (flow_id, predicted_label, probabilities_json, model_version, predicted_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (flow_id, predicted_label, json.dumps(probabilities), model_version, predicted_at),
    )
    conn.commit()


def insert_alert(conn, alert_id: str, flow_id: str, group_key: str, predicted_label: str, created_at: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO AlertRecord (alert_id, flow_id, group_key, predicted_label, status, created_at) "
        "VALUES (?, ?, ?, ?, 'new', ?)",
        (alert_id, flow_id, group_key, predicted_label, created_at),
    )
    conn.commit()


def upsert_reliability(conn, alert_id: str, **fields) -> None:
    """Ghi/cập nhật MỘT PHẦN bảng Reliability cho 1 alert_id.

    Các bước 7-11 lần lượt điền thêm cột khác nhau cho CÙNG 1 alert_id (bước 7
    điền shap_top5_json, bước 8 điền cờ + faithfulness, bước 9 điền lime_top5_json
    + agreement, ...), nên dùng INSERT-nếu-chưa-có rồi UPDATE các cột được truyền
    vào, thay vì ghi đè toàn bộ dòng (sẽ xóa mất dữ liệu bước trước đã ghi)."""
    conn.execute("INSERT OR IGNORE INTO Reliability (alert_id) VALUES (?)", (alert_id,))
    if fields:
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(
            f"UPDATE Reliability SET {set_clause} WHERE alert_id = ?",
            (*fields.values(), alert_id),
        )
    conn.commit()


def get_alert(conn, alert_id: str) -> dict | None:
    """Dùng ở POST /explain (bước 9): tra flow_id + predicted_label từ alert_id, để
    LIME biết cần giải thích flow nào, cho đúng lớp nào."""
    row = conn.execute(
        "SELECT alert_id, flow_id, predicted_label FROM AlertRecord WHERE alert_id = ?", (alert_id,),
    ).fetchone()
    if row is None:
        return None
    return {"alert_id": row[0], "flow_id": row[1], "predicted_label": row[2]}


def get_flow_features(conn, flow_id: str) -> dict | None:
    """Tra lại 78 đặc trưng gốc (chưa chuẩn hóa) của 1 flow đã lưu — cần ở POST /explain
    vì request đó chỉ gửi alert_id, không gửi lại 78 số."""
    row = conn.execute("SELECT features_json FROM FlowRecord WHERE flow_id = ?", (flow_id,)).fetchone()
    if row is None:
        return None
    return json.loads(row[0])


def get_shap_top5(conn, alert_id: str) -> list[dict] | None:
    """Tra Top-5 SHAP đã ghi sẵn (từ bước 7, qua hàng đợi) — dùng để tính Agreement
    khi LIME chạy xong ở bước 9. None nếu hàng đợi SHAP chưa xử lý xong flow này."""
    row = conn.execute("SELECT shap_top5_json FROM Reliability WHERE alert_id = ?", (alert_id,)).fetchone()
    if row is None or row[0] is None:
        return None
    return json.loads(row[0])


def get_alerts(
    conn, since: str | None = None, until: str | None = None,
    label: str | None = None, branch: str | None = None,
) -> list[dict]:
    """Bước 12 — `GET /alerts`: danh sách Alert kèm trạng thái giải thích, lọc
    theo thời gian/nhãn/nhánh (đúng bảng API trong tài liệu kiến trúc). LEFT JOIN
    với Reliability vì SHAP/branch có thể CHƯA xử lý xong (hàng đợi bất đồng bộ từ
    bước 7b) hoặc đã bị bỏ do hàng đợi đầy (khi đó không có dòng Reliability nào)."""
    query = """
        SELECT a.alert_id, a.flow_id, a.predicted_label, a.status, a.created_at,
               f.source, f.flow_timestamp,
               r.shap_top5_json, r.lime_top5_json, r.branch, r.branch_reason,
               r.agreement_jaccard5, r.faithfulness_proxy_drop, r.env_fingerprint_count,
               r.env_fingerprint_flag, r.rare_class_flag, r.stability_lookup, r.robustness_lookup_json
        FROM AlertRecord a
        LEFT JOIN Reliability r ON a.alert_id = r.alert_id
        LEFT JOIN FlowRecord f ON a.flow_id = f.flow_id
        WHERE 1=1
    """
    params: list = []
    if since is not None:
        query += " AND a.created_at >= ?"
        params.append(since)
    if until is not None:
        query += " AND a.created_at <= ?"
        params.append(until)
    if label is not None:
        query += " AND a.predicted_label = ?"
        params.append(label)
    if branch is not None:
        query += " AND r.branch = ?"
        params.append(branch)
    # Sắp theo flow_timestamp (lúc gói tin THẬT xảy ra) nếu có, lùi về created_at
    # (lúc hệ thống tạo Alert) nếu không có — xem giải thích đầy đủ ở get_flows().
    query += " ORDER BY COALESCE(f.flow_timestamp, a.created_at) DESC"

    rows = conn.execute(query, params).fetchall()
    result = []
    for (alert_id, flow_id, predicted_label, status, created_at, source, flow_timestamp,
         shap_json, lime_json, br, br_reason,
         agreement, faith_drop, env_count, env_flag, rare_flag, stability, robustness_json) in rows:
        if shap_json is None:
            explanation_status = "pending_or_dropped"  # chưa xử lý xong HOẶC bị bỏ vì hàng đợi đầy (bước 7b)
        elif lime_json is None:
            explanation_status = "shap_only"
        else:
            explanation_status = "shap_and_lime"
        result.append({
            "alert_id": alert_id, "flow_id": flow_id, "predicted_label": predicted_label,
            "status": status, "created_at": created_at,
            "source": source, "flow_timestamp": flow_timestamp,
            "explanation_status": explanation_status,
            "branch": br, "branch_reason": br_reason,
            "shap_top5": json.loads(shap_json) if shap_json else None,
            "lime_top5": json.loads(lime_json) if lime_json else None,
            "agreement_jaccard5": agreement,
            "faithfulness_proxy_drop": faith_drop,
            "env_fingerprint_count": env_count,
            "env_fingerprint_flag": env_flag,
            "rare_class_flag": rare_flag,
            "stability_lookup": stability,
            "robustness_lookup": json.loads(robustness_json) if robustness_json else None,
        })
    return result


def get_flows(
    conn, since: str | None = None, until: str | None = None,
    label: str | None = None, limit: int = 200,
) -> list[dict]:
    """Bước 12 (bổ sung) — `GET /flows`: danh sách MỌI flow đã xử lý, kể cả Benign
    (Benign không tạo Alert nên không xuất hiện ở `get_alerts()` — bạn cần thấy cả
    traffic bình thường, không chỉ cảnh báo, để biết hệ thống có đang hoạt động và
    tỉ lệ Benign/tấn công thực tế). LEFT JOIN Prediction vì về lý thuyết 1 flow lỗi
    ở tầng chuẩn hóa (422) thì có FlowRecord... thực ra flow lỗi 422 KHÔNG được ghi
    vào FlowRecord (xem main.py — chỉ insert_flow sau khi normalize_flow thành
    công), nên LEFT JOIN ở đây chỉ để phòng hờ, không phải vì có flow thiếu dự đoán
    trong vận hành bình thường."""
    query = """
        SELECT f.flow_id, f.received_at, f.source, f.flow_timestamp, f.label_true,
               p.predicted_label, p.predicted_at
        FROM FlowRecord f
        LEFT JOIN Prediction p ON f.flow_id = p.flow_id
        WHERE 1=1
    """
    params: list = []
    if since is not None:
        query += " AND f.received_at >= ?"
        params.append(since)
    if until is not None:
        query += " AND f.received_at <= ?"
        params.append(until)
    if label is not None:
        query += " AND p.predicted_label = ?"
        params.append(label)
    # Sắp theo flow_timestamp (lúc gói tin THẬT xảy ra) nếu có — đúng thứ tự thời
    # gian thật của traffic (quan trọng khi phát lại CSV/PCAP cũ: mọi flow được
    # XỬ LÝ gần như cùng lúc lúc bạn bấm gửi, received_at dồn cục, không phản ánh
    # đúng thứ tự traffic thật đã xảy ra). Thiếu flow_timestamp (vd Tập A/B không
    # có cột timestamp gốc) thì lùi về received_at.
    query += " ORDER BY COALESCE(f.flow_timestamp, f.received_at) DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    return [
        {
            "flow_id": flow_id, "received_at": received_at, "source": source,
            "flow_timestamp": flow_timestamp,
            "label_true": label_true, "predicted_label": predicted_label,
            "is_alert": predicted_label is not None and predicted_label != "Benign",
        }
        for flow_id, received_at, source, flow_timestamp, label_true, predicted_label, predicted_at in rows
    ]


def insert_timing(conn, flow_id: str, step: str, duration_ms: float, recorded_at: str) -> None:
    conn.execute(
        "INSERT INTO Timing (flow_id, step, duration_ms, recorded_at) VALUES (?, ?, ?, ?)",
        (flow_id, step, duration_ms, recorded_at),
    )
    conn.commit()

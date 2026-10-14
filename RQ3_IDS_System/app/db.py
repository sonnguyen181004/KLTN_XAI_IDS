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
    received_at     TEXT NOT NULL,
    source          TEXT NOT NULL,      -- 'rq2_cohort' | 'clean_set' | 'lab' | 'pcap'
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
    conn.commit()
    return conn


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

def insert_flow(conn, flow_id: str, received_at: str, source: str, features: dict, label_true: str | None) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO FlowRecord (flow_id, received_at, source, features_json, label_true) "
        "VALUES (?, ?, ?, ?, ?)",
        (flow_id, received_at, source, json.dumps(features), label_true),
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


def insert_timing(conn, flow_id: str, step: str, duration_ms: float, recorded_at: str) -> None:
    conn.execute(
        "INSERT INTO Timing (flow_id, step, duration_ms, recorded_at) VALUES (?, ?, ?, ?)",
        (flow_id, step, duration_ms, recorded_at),
    )
    conn.commit()

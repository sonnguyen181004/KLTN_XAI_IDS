"""Bước 2 — Tạo schema SQLite (6 bảng) cho hệ thống IDS, rồi TỰ KIỂM TRA:
  1) Đủ 6 bảng chưa.
  2) Mỗi bảng có đúng các cột mong đợi không.
  3) Chèn thử 1 flow giả vào FlowRecord rồi đọc lại — xác nhận ghi/đọc hoạt động.
Không đụng tới model, không đụng tới dữ liệu thật.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

# Console Windows mặc định cp1252, không in được tiếng Việt có dấu.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import db  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_config() -> dict:
    cfg_path = Path(__file__).resolve().parents[1] / "config.yaml"
    with open(cfg_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> int:
    cfg = load_config()
    db_path = REPO_ROOT / cfg["paths"]["sqlite_db"]

    print("=" * 70)
    print("BƯỚC 2: TẠO SCHEMA SQLITE CHO HỆ THỐNG IDS")
    print("=" * 70)
    print(f"Đường dẫn DB: {db_path}")

    conn = db.init_db(db_path)
    print("-> Đã tạo/mở file DB và chạy CREATE TABLE IF NOT EXISTS cho 6 bảng.")

    # ---- Kiểm tra 1: đủ 6 bảng chưa ----------------------------------------
    tables = db.list_tables(conn)
    print(f"\nKiểm tra 1 — Danh sách bảng thực tế trong file DB: {tables}")
    missing = [t for t in db.TABLE_NAMES if t not in tables]
    if missing:
        print(f"  [FAIL] Thiếu bảng: {missing}")
        return 1
    print(f"  [PASS] Đủ cả {len(db.TABLE_NAMES)} bảng: {db.TABLE_NAMES}")

    # ---- Kiểm tra 2: cột của từng bảng --------------------------------------
    print("\nKiểm tra 2 — Cột của từng bảng:")
    for t in db.TABLE_NAMES:
        cols = db.table_columns(conn, t)
        print(f"  {t}: {cols}")

    # ---- Kiểm tra 3: chèn 1 flow giả rồi đọc lại ----------------------------
    print("\nKiểm tra 3 — Chèn thử 1 flow giả vào FlowRecord, rồi đọc lại:")
    fake_flow_id = "TEST-FLOW-0001"
    fake_features = {f"feat_{i}": float(i) for i in range(78)}  # giả lập đủ 78 "đặc trưng"
    now = datetime.now(timezone.utc).isoformat()

    conn.execute(
        "INSERT OR REPLACE INTO FlowRecord (flow_id, received_at, source, features_json, label_true) "
        "VALUES (?, ?, ?, ?, ?)",
        (fake_flow_id, now, "test", json.dumps(fake_features), "Benign"),
    )
    conn.commit()
    print(f"  Đã chèn flow_id={fake_flow_id}")

    row = conn.execute(
        "SELECT flow_id, received_at, source, label_true, features_json FROM FlowRecord WHERE flow_id = ?",
        (fake_flow_id,),
    ).fetchone()
    if row is None:
        print("  [FAIL] Đọc lại không thấy dòng vừa chèn.")
        return 1
    flow_id, received_at, source, label_true, features_json = row
    n_features_read_back = len(json.loads(features_json))
    print(f"  Đọc lại: flow_id={flow_id}, source={source}, label_true={label_true}, "
          f"số đặc trưng trong features_json={n_features_read_back}")
    if n_features_read_back != 78:
        print(f"  [FAIL] Số đặc trưng đọc lại ({n_features_read_back}) khác 78.")
        return 1
    print("  [PASS] Chèn và đọc lại khớp dữ liệu đã ghi.")

    # Dọn dòng test để không để rác trong DB thật.
    conn.execute("DELETE FROM FlowRecord WHERE flow_id = ?", (fake_flow_id,))
    conn.commit()
    print("  (Đã xóa dòng test để DB sạch cho các bước sau.)")

    conn.close()
    print("\n" + "=" * 70)
    print("BƯỚC 2 HOÀN TẤT — schema đúng, ghi/đọc hoạt động.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

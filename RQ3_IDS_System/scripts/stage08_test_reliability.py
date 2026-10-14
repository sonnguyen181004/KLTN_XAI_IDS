"""Bước 8 — Test độ tin cậy + gắn cờ (app/reliability.py) qua API thật:
  1) Flow SQL Injection (lớp hiếm, 70 mẫu train < ngưỡng 100) -> rare_class_flag PHẢI = 1.
  2) Flow Bot (lớp thường, 100650 mẫu train) -> rare_class_flag PHẢI = 0.
  3) Cả 2 -> faithfulness_proxy_drop PHẢI có giá trị (không None), nằm trong [-1, 1]
     (xác suất là số trong [0,1], nên hiệu 2 xác suất luôn trong [-1,1]).
  4) env_fingerprint_flag = 1 khi và chỉ khi env_fingerprint_count >= ngưỡng config.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import requests
import yaml

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[2]
RQ3_ROOT = Path(__file__).resolve().parents[1]


def load_config() -> dict:
    with open(RQ3_ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def wait_for_server(url: str, timeout_s: float = 20.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            if requests.get(url, timeout=1).status_code == 200:
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(0.3)
    return False


def row_payload(df: pd.DataFrame, label: str, feature_cols: list[str]) -> dict:
    row = df[df["label_true"] == label].iloc[0]
    return {col: float(row[col]) for col in feature_cols}


def wait_for_reliability(conn, alert_id: str, timeout_s: float = 10.0):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        row = conn.execute(
            "SELECT faithfulness_proxy_drop, env_fingerprint_count, env_fingerprint_flag, rare_class_flag "
            "FROM Reliability WHERE alert_id = ?", (alert_id,)
        ).fetchone()
        if row is not None and row[0] is not None:
            return row
        time.sleep(0.3)
    return row


def main() -> int:
    cfg = load_config()
    host, port = cfg["api"]["host"], cfg["api"]["port"]
    base_url = f"http://{host}:{port}"
    env_threshold = cfg["environment_fingerprint_flag_threshold"]

    print("=" * 70)
    print("BƯỚC 8: TEST ĐỘ TIN CẬY + GẮN CỜ (faithfulness proxy, env flag, rare class flag)")
    print("=" * 70)

    df = pd.read_csv(RQ3_ROOT / "data" / "clean_holdout_set.csv")
    feature_cols = [c for c in df.columns if c not in ("label_true", "flow_id")]

    server_log_path = RQ3_ROOT / "data" / "stage08_test_server.log"
    server_log_path.parent.mkdir(parents=True, exist_ok=True)
    server_log_file = open(server_log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", host, "--port", str(port)],
        cwd=str(RQ3_ROOT), stdout=server_log_file, stderr=subprocess.STDOUT,
    )

    all_ok = True
    try:
        if not wait_for_server(f"{base_url}/health"):
            server_log_file.flush()
            print("[FAIL] Server không lên được. Log:")
            print(server_log_path.read_text(encoding="utf-8", errors="replace"))
            return 1
        print("Server đã sẵn sàng.\n")

        sys.path.insert(0, str(RQ3_ROOT / "app"))
        import db  # noqa: E402
        conn = db.get_connection(REPO_ROOT / cfg["paths"]["sqlite_db"])

        cases = [
            ("SQL Injection", True),   # 70 mẫu train -> PHẢI rare_class_flag=1
            ("Bot", False),            # 100650 mẫu train -> PHẢI rare_class_flag=0
        ]

        for label, expect_rare in cases:
            print(f"--- Flow nhãn thật = {label} (kỳ vọng rare_class_flag = {int(expect_rare)}) ---")
            payload = row_payload(df, label, feature_cols)
            r = requests.post(f"{base_url}/predict", json=payload)
            body = r.json()
            print(f"  status={r.status_code}, predicted_label={body['predicted_label']}, "
                  f"is_alert={body['is_alert']}, explanation_status={body['explanation_status']}")

            if not body["is_alert"]:
                print("  [FAIL] Model đoán ra Benign -> không tạo Alert -> không có gì để kiểm tra bước 8.")
                all_ok = False
                continue

            row = wait_for_reliability(conn, body["alert_id"])
            if row is None:
                print("  [FAIL] Không thấy dữ liệu Reliability sau 10s chờ hàng đợi xử lý.")
                all_ok = False
                continue

            drop, env_count, env_flag, rare_flag = row
            print(f"  faithfulness_proxy_drop = {drop:.4f}")
            print(f"  env_fingerprint_count   = {env_count} (ngưỡng flag = {env_threshold})")
            print(f"  env_fingerprint_flag    = {env_flag}")
            print(f"  rare_class_flag         = {rare_flag}")

            ok = True
            ok &= drop is not None and -1.0 <= drop <= 1.0
            ok &= env_flag == int(env_count >= env_threshold)
            ok &= rare_flag == int(expect_rare)
            print(f"  [{'PASS' if ok else 'FAIL'}]\n")
            all_ok &= ok

        conn.close()

    finally:
        print("Đang tắt server...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        server_log_file.close()

    print("=" * 70)
    print("BƯỚC 8 " + ("HOÀN TẤT — mọi kiểm tra đúng như kỳ vọng." if all_ok else "CÓ LỖI, xem [FAIL] ở trên."))
    print("=" * 70)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

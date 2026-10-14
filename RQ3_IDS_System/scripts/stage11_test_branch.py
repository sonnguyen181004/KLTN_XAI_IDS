"""Bước 11 — Test luật quyết định nhánh A/B (tầng 5) qua API thật:
  1) Flow Bot (cả 2 cờ = 0) -> branch PHẢI = 'A'.
  2) Flow SQL Injection (rare_class_flag = 1) -> branch PHẢI = 'B'.
  3) Flow DoS attacks-Hulk (kỳ vọng env_fingerprint_flag = 1, theo SHAP toàn cục RQ2:
     Top-5 gồm Fwd Seg Size Min + Init Fwd Win Byts) -> branch PHẢI = 'B'.
Chỉ dựa vào 2 cờ của bước 8 — không dùng ngưỡng dev-set, không dùng Agreement.
"""
from __future__ import annotations

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


def wait_for_branch(conn, alert_id: str, timeout_s: float = 10.0):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        row = conn.execute(
            "SELECT branch, branch_reason, env_fingerprint_flag, rare_class_flag "
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

    print("=" * 70)
    print("BƯỚC 11: TEST LUẬT QUYẾT ĐỊNH NHÁNH A/B")
    print("=" * 70)

    df = pd.read_csv(RQ3_ROOT / "data" / "clean_holdout_set.csv")
    feature_cols = [c for c in df.columns if c not in ("label_true", "flow_id")]

    server_log_path = RQ3_ROOT / "data" / "stage11_test_server.log"
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
            ("Bot", "A"),
            ("SQL Injection", "B"),
            ("DoS attacks-Hulk", "B"),
        ]

        for label, expect_branch in cases:
            print(f"--- Flow nhãn thật = {label} (kỳ vọng branch = {expect_branch}) ---")
            payload = row_payload(df, label, feature_cols)
            r = requests.post(f"{base_url}/predict", json=payload)
            body = r.json()
            print(f"  status={r.status_code}, predicted_label={body['predicted_label']}, is_alert={body['is_alert']}")

            if not body["is_alert"]:
                print("  [FAIL] Model đoán ra Benign -> không tạo Alert -> không có gì để kiểm tra.")
                all_ok = False
                continue

            row = wait_for_branch(conn, body["alert_id"])
            if row is None:
                print("  [FAIL] Không thấy dữ liệu Reliability sau 10s chờ hàng đợi xử lý.")
                all_ok = False
                continue

            branch, branch_reason, env_flag, rare_flag = row
            print(f"  env_fingerprint_flag={env_flag}, rare_class_flag={rare_flag}")
            print(f"  branch={branch}")
            print(f"  branch_reason={branch_reason}")

            ok = branch == expect_branch
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
    print("BƯỚC 11 " + ("HOÀN TẤT — mọi kiểm tra đúng như kỳ vọng." if all_ok else "CÓ LỖI, xem [FAIL] ở trên."))
    print("=" * 70)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

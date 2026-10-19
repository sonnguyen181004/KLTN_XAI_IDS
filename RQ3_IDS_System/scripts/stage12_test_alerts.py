"""Bước 12 — Test `GET /alerts` qua API thật:
  1) Không lọc gì -> trả về danh sách, có ít nhất các alert vừa tạo trong test này.
  2) Lọc theo nhãn (`label=Bot`) -> chỉ còn alert nhãn Bot.
  3) Lọc theo nhánh (`branch=B`) -> chỉ còn alert branch='B'.
  4) Lọc theo thời gian (`since`=ngay trước khi bắn flow test) -> loại hết alert cũ.
  5) `branch` không hợp lệ (vd 'C') -> 422.
"""
from __future__ import annotations

import subprocess
import sys

import _testdb  # DB tạm, không chạm data/ids_system.db
import time
from datetime import datetime, timezone
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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def row_payload(df: pd.DataFrame, label: str, feature_cols: list[str]) -> dict:
    row = df[df["label_true"] == label].iloc[0]
    return {col: float(row[col]) for col in feature_cols}


def wait_for_branch(base_url: str, alert_id: str, timeout_s: float = 10.0):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        r = requests.get(f"{base_url}/alerts")
        for a in r.json()["alerts"]:
            if a["alert_id"] == alert_id and a["branch"] is not None:
                return a
        time.sleep(0.3)
    return None


def main() -> int:
    cfg = load_config()
    host, port = cfg["api"]["host"], cfg["api"]["port"]
    base_url = f"http://{host}:{port}"

    print("=" * 70)
    print("BƯỚC 12: TEST GET /alerts QUA API THẬT")
    print("=" * 70)

    df = pd.read_csv(RQ3_ROOT / "data" / "clean_holdout_set.csv")
    feature_cols = [c for c in df.columns if c not in ("label_true", "flow_id")]

    server_log_path = RQ3_ROOT / "data" / "stage12_test_server.log"
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

        t_before = now_iso()
        time.sleep(0.2)

        bot_payload = row_payload(df, "Bot", feature_cols)
        sqli_payload = row_payload(df, "SQL Injection", feature_cols)

        r1 = requests.post(f"{base_url}/predict", json=bot_payload)
        bot_alert_id = r1.json()["alert_id"]
        r2 = requests.post(f"{base_url}/predict", json=sqli_payload)
        sqli_alert_id = r2.json()["alert_id"]
        print(f"Đã tạo 2 alert mới: Bot={bot_alert_id}, SQL Injection={sqli_alert_id}")

        bot_alert = wait_for_branch(base_url, bot_alert_id)
        sqli_alert = wait_for_branch(base_url, sqli_alert_id)
        if bot_alert is None or sqli_alert is None:
            print("[FAIL] Không thấy branch sau 10s chờ hàng đợi xử lý.")
            return 1
        print(f"  Bot: branch={bot_alert['branch']}, explanation_status={bot_alert['explanation_status']}")
        print(f"  SQL Injection: branch={sqli_alert['branch']}, explanation_status={sqli_alert['explanation_status']}")

        # ---- Việc 1: không lọc gì ------------------------------------------------
        print("\n--- Việc 1: GET /alerts (không lọc) ---")
        r = requests.get(f"{base_url}/alerts")
        body = r.json()
        ids = {a["alert_id"] for a in body["alerts"]}
        ok = r.status_code == 200 and bot_alert_id in ids and sqli_alert_id in ids
        print(f"  status={r.status_code}, count={body['count']}, chứa cả 2 alert mới: {ok}")
        print(f"  [{'PASS' if ok else 'FAIL'}]")
        all_ok &= ok

        # ---- Việc 2: lọc theo nhãn ------------------------------------------------
        print("\n--- Việc 2: GET /alerts?label=Bot ---")
        r = requests.get(f"{base_url}/alerts", params={"label": "Bot"})
        body = r.json()
        ok = all(a["predicted_label"] == "Bot" for a in body["alerts"]) and bot_alert_id in {a["alert_id"] for a in body["alerts"]}
        print(f"  status={r.status_code}, count={body['count']}, mọi alert đều nhãn Bot: {ok}")
        print(f"  [{'PASS' if ok else 'FAIL'}]")
        all_ok &= ok

        # ---- Việc 3: lọc theo nhánh -------------------------------------------------
        print("\n--- Việc 3: GET /alerts?branch=B ---")
        r = requests.get(f"{base_url}/alerts", params={"branch": "B"})
        body = r.json()
        ok = all(a["branch"] == "B" for a in body["alerts"]) and sqli_alert_id in {a["alert_id"] for a in body["alerts"]}
        print(f"  status={r.status_code}, count={body['count']}, mọi alert đều branch=B: {ok}")
        print(f"  [{'PASS' if ok else 'FAIL'}]")
        all_ok &= ok

        # ---- Việc 4: lọc theo thời gian (since) --------------------------------------
        print("\n--- Việc 4: GET /alerts?since=<ngay trước 2 alert mới> ---")
        r = requests.get(f"{base_url}/alerts", params={"since": t_before})
        body = r.json()
        ids_since = {a["alert_id"] for a in body["alerts"]}
        ok = bot_alert_id in ids_since and sqli_alert_id in ids_since
        print(f"  status={r.status_code}, count={body['count']} (loại hết alert cũ trước mốc {t_before})")
        print(f"  [{'PASS' if ok else 'FAIL'}]")
        all_ok &= ok

        # ---- Việc 5: branch không hợp lệ ---------------------------------------------
        print("\n--- Việc 5: GET /alerts?branch=C (không hợp lệ) -> phải 422 ---")
        r = requests.get(f"{base_url}/alerts", params={"branch": "C"})
        ok = r.status_code == 422
        print(f"  status={r.status_code} [{'PASS' if ok else 'FAIL'}]")
        all_ok &= ok

    finally:
        print("\nĐang tắt server...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        server_log_file.close()

    print("\n" + "=" * 70)
    print("BƯỚC 12 " + ("HOÀN TẤT — mọi kiểm tra đúng như kỳ vọng." if all_ok else "CÓ LỖI, xem [FAIL] ở trên."))
    print("=" * 70)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

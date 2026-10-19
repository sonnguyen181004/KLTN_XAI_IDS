"""Bước 9 — Test LIME theo yêu cầu qua API thật:
  1) Flow tấn công (Bot) -> /predict tạo alert -> /explain method=lime -> trả Top-5 LIME,
     local_r2 hợp lệ (0..1), agreement_jaccard5 có giá trị (SHAP bước 7 đã xong trước).
  2) /explain với alert_id không tồn tại -> 404.
  3) /explain với method khác lime -> 400.
  4) Mở DB xác nhận lime_top5_json + agreement_jaccard5 đã ghi vào Reliability.
  5) Gọi lại LẦN 2 cùng alert_id -> Top-5 LIME phải GIỐNG HỆT lần 1 (seed cố định theo
     flow, đúng nguyên tắc tái lập của RQ2).
"""
from __future__ import annotations

import json
import subprocess
import sys

import _testdb  # DB tạm, không chạm data/ids_system.db
import time
from pathlib import Path

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


def wait_for_queue_drain(base_url: str, n_expect_processed: int, timeout_s: float = 15.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        status = requests.get(f"{base_url}/explain_queue_status").json()
        if status["n_processed"] >= n_expect_processed:
            return True
        time.sleep(0.2)
    return False


def main() -> int:
    cfg = load_config()
    host, port = cfg["api"]["host"], cfg["api"]["port"]
    base_url = f"http://{host}:{port}"

    print("=" * 70)
    print("BƯỚC 9: TEST LIME THEO YÊU CẦU QUA API THẬT")
    print("=" * 70)

    server_log_path = RQ3_ROOT / "data" / "stage09_server.log"
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
        print("Server đã sẵn sàng.")

        attack_payload = json.loads((RQ3_ROOT / "data/samples/sample_attack.json").read_text(encoding="utf-8"))
        r = requests.post(f"{base_url}/predict", json=attack_payload)
        body = r.json()
        alert_id = body["alert_id"]
        print(f"\n/predict -> predicted_label={body['predicted_label']}, alert_id={alert_id}")
        wait_for_queue_drain(base_url, 1)  # chờ SHAP (bước 7) + reliability (bước 8) xong trước

        # ---- Việc 1: /explain method=lime -> Top-5 hợp lệ ------------------------------
        print("\n--- Việc 1: POST /explain method=lime ---")
        t0 = time.time()
        r = requests.post(f"{base_url}/explain", json={"alert_id": alert_id, "method": "lime"})
        dt_ms = (time.time() - t0) * 1000
        body1 = r.json()
        ok = (r.status_code == 200 and len(body1["top_k"]) == 5
              and 0.0 <= body1["local_r2"] <= 1.0 and body1["agreement_jaccard5"] is not None)
        print(f"  status={r.status_code}, local_r2={body1.get('local_r2')}, "
              f"agreement_jaccard5={body1.get('agreement_jaccard5')}, thời gian gọi={dt_ms:.1f}ms "
              f"(RQ2 tham chiếu ~148ms/flow)")
        if ok:
            print("  Top-5 LIME:")
            for item in body1["top_k"]:
                print(f"    {item['feature_desc']:35s} weight={item['weight']:+.5f}")
        print(f"  [{'PASS' if ok else 'FAIL'}]")
        all_ok &= ok

        # ---- Việc 2: alert_id không tồn tại -> 404 --------------------------------------
        print("\n--- Việc 2: alert_id không tồn tại -> phải 404 ---")
        r = requests.post(f"{base_url}/explain", json={"alert_id": "khong-ton-tai", "method": "lime"})
        ok = r.status_code == 404
        print(f"  status={r.status_code} [{'PASS' if ok else 'FAIL'}]")
        all_ok &= ok

        # ---- Việc 3: method khác lime -> 400 --------------------------------------------
        print("\n--- Việc 3: method='shap' (không hỗ trợ qua /explain) -> phải 400 ---")
        r = requests.post(f"{base_url}/explain", json={"alert_id": alert_id, "method": "shap"})
        ok = r.status_code == 400
        print(f"  status={r.status_code} [{'PASS' if ok else 'FAIL'}]")
        all_ok &= ok

        # ---- Việc 4: mở DB xác nhận đã ghi -----------------------------------------------
        print("\n--- Việc 4: mở lại DB, xác nhận lime_top5_json + agreement_jaccard5 ---")
        sys.path.insert(0, str(RQ3_ROOT / "app"))
        import db  # noqa: E402
        conn = db.init_db(_testdb.TEST_DB)
        row = conn.execute(
            "SELECT lime_top5_json, agreement_jaccard5 FROM Reliability WHERE alert_id = ?", (alert_id,),
        ).fetchone()
        ok = row is not None and row[0] is not None and len(json.loads(row[0])) == 5 and row[1] is not None
        print(f"  lime_top5_json có {len(json.loads(row[0])) if row and row[0] else 0} phần tử, "
              f"agreement_jaccard5={row[1] if row else None} -> [{'PASS' if ok else 'FAIL'}]")
        all_ok &= ok

        # ---- Việc 5: gọi lại lần 2 -> phải GIỐNG HỆT lần 1 (seed cố định theo flow) -----
        print("\n--- Việc 5: gọi lại /explain LẦN 2 cùng alert_id -> Top-5 phải giống hệt lần 1 ---")
        r = requests.post(f"{base_url}/explain", json={"alert_id": alert_id, "method": "lime"})
        body2 = r.json()
        ok = body2["top_k"] == body1["top_k"] and abs(body2["local_r2"] - body1["local_r2"]) < 1e-9
        print(f"  Lần 1 local_r2={body1['local_r2']:.6f}, lần 2 local_r2={body2['local_r2']:.6f}")
        print(f"  [{'PASS' if ok else 'FAIL'}]")
        all_ok &= ok

        conn.close()

    finally:
        print("\nĐang tắt server...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        server_log_file.close()

    print("\n" + "=" * 70)
    print("BƯỚC 9 " + ("HOÀN TẤT — mọi kiểm tra đúng như kỳ vọng." if all_ok else "CÓ LỖI, xem [FAIL] ở trên."))
    print("=" * 70)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

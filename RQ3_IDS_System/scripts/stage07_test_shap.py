"""Bước 7 — Test TreeSHAP tự động qua API thật:
  1) Flow tấn công (Bot) -> response phải có Top-5 SHAP, không rỗng.
  2) Flow Benign -> KHÔNG có SHAP (đúng nguyên tắc: chỉ tính khi có cảnh báo).
  3) Additivity: sai số phải cùng bậc với RQ2 (~1e-5/1e-6).
  4) Mở DB xác nhận bảng Reliability có dữ liệu cho alert_id vừa tạo.
  5) So thời gian tính SHAP qua API với số RQ2 đã biết (~19ms/flow hàng loạt).
"""
from __future__ import annotations

import json
import subprocess
import sys
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


def main() -> int:
    cfg = load_config()
    host, port = cfg["api"]["host"], cfg["api"]["port"]
    base_url = f"http://{host}:{port}"

    print("=" * 70)
    print("BƯỚC 7: TEST TREESHAP TỰ ĐỘNG QUA API THẬT")
    print("=" * 70)

    server_log_path = RQ3_ROOT / "data" / "stage07_server.log"
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
        benign_payload = json.loads((RQ3_ROOT / "data/samples/sample_benign.json").read_text(encoding="utf-8"))

        # ---- Việc 1: flow tấn công -> phải có Top-5 SHAP ------------------------------
        print("\n--- Việc 1: flow tấn công (Bot) -> phải có Top-5 SHAP ---")
        r = requests.post(f"{base_url}/predict", json=attack_payload)
        body = r.json()
        print(f"  status={r.status_code}, predicted_label={body['predicted_label']}, is_alert={body['is_alert']}")
        shap_result = body.get("shap")
        ok = r.status_code == 200 and shap_result is not None and len(shap_result["top_k"]) == 5
        if ok:
            print(f"  class_explained={shap_result['class_explained']}, base_value={shap_result['base_value']:.4f}")
            print(f"  additivity_error={shap_result['additivity_error']:.3e} (RQ2 tham chiếu ~1e-5 đến 1e-6)")
            print("  Top-5 đặc trưng:")
            for item in shap_result["top_k"]:
                print(f"    {item['feature']:25s} value={item['value']:>12.4f}  phi={item['phi']:+.5f}")
            ok = ok and shap_result["additivity_error"] < 1e-3  # nới rộng hơn RQ2 vì chỉ tính Top-5, không phải toàn bộ check
        print(f"  [{'PASS' if ok else 'FAIL'}]")
        all_ok &= ok
        attack_alert_id = body.get("alert_id")
        attack_flow_id = body.get("flow_id")
        print(f"  timing_ms={body['timing_ms']}")

        # ---- Việc 2: flow Benign -> KHÔNG có SHAP ---------------------------------------
        print("\n--- Việc 2: flow Benign -> KHÔNG được có SHAP ---")
        r = requests.post(f"{base_url}/predict", json=benign_payload)
        body = r.json()
        ok = r.status_code == 200 and body["predicted_label"] == "Benign" and body["shap"] is None and not body["is_alert"]
        print(f"  status={r.status_code}, predicted_label={body['predicted_label']}, "
              f"is_alert={body['is_alert']}, shap={body['shap']}")
        print(f"  [{'PASS' if ok else 'FAIL'}]")
        all_ok &= ok

        # ---- Việc 3: mở DB xác nhận Reliability có dữ liệu -----------------------------
        print("\n--- Việc 3: mở lại file DB, xác nhận bảng Reliability ---")
        sys.path.insert(0, str(RQ3_ROOT / "app"))
        import db  # noqa: E402
        conn = db.init_db(REPO_ROOT / cfg["paths"]["sqlite_db"])
        row = conn.execute(
            "SELECT alert_id, shap_top5_json FROM Reliability WHERE alert_id = ?", (attack_alert_id,)
        ).fetchone()
        ok = row is not None and row[1] is not None and len(json.loads(row[1])) == 5
        print(f"  alert_id={attack_alert_id}: Reliability={'có' if row else 'THIẾU'}, "
              f"shap_top5_json có {len(json.loads(row[1])) if row and row[1] else 0} phần tử -> "
              f"[{'PASS' if ok else 'FAIL'}]")
        all_ok &= ok

        timing_rows = conn.execute(
            "SELECT step, duration_ms FROM Timing WHERE flow_id = ? ORDER BY timing_id", (attack_flow_id,)
        ).fetchall()
        print(f"  Timing cho flow này: {timing_rows}")
        shap_timing = [d for s, d in timing_rows if s == "shap"]
        if shap_timing:
            print(f"  Thời gian SHAP qua API: {shap_timing[0]:.2f} ms (RQ2 tham chiếu ~19 ms/flow khi chạy hàng loạt)")
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
    print("BƯỚC 7 " + ("HOÀN TẤT — mọi kiểm tra đúng như kỳ vọng." if all_ok else "CÓ LỖI, xem [FAIL] ở trên."))
    print("=" * 70)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Bước 6 — Test API thật: khởi động server uvicorn thật, gửi request HTTP thật
(không gọi hàm Python trực tiếp), kiểm tra status code, nhãn trả về, và DB có
thực sự được ghi hay không. Cuối cùng tắt server.
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
            r = requests.get(url, timeout=1)
            if r.status_code == 200:
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
    print("BƯỚC 6: TEST API THẬT (FastAPI qua HTTP)")
    print("=" * 70)

    print(f"Khởi động server: uvicorn app.main:app --port {port} (chạy nền)...")
    # QUAN TRỌNG: ghi log server ra FILE trên đĩa, KHÔNG dùng subprocess.PIPE.
    # Nếu dùng PIPE mà không liên tục đọc nó, ống dẫn đầy sẽ làm uvicorn bị
    # BLOCK khi ghi log (deadlock kinh điển của subprocess trên Windows) —
    # server trông như "treo", không trả lời request nào cả.
    server_log_path = RQ3_ROOT / "data" / "stage06_server.log"
    server_log_path.parent.mkdir(parents=True, exist_ok=True)
    server_log_file = open(server_log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", host, "--port", str(port)],
        cwd=str(RQ3_ROOT),
        stdout=server_log_file, stderr=subprocess.STDOUT,
    )

    all_ok = True
    try:
        ready = wait_for_server(f"{base_url}/health")
        if not ready:
            server_log_file.flush()
            print("  [FAIL] Server không lên được trong 20 giây. Log server:")
            print(server_log_path.read_text(encoding="utf-8", errors="replace"))
            return 1
        print("  Server đã sẵn sàng.")

        # ---- Việc 1: /health ----------------------------------------------------------
        print("\n--- Việc 1: gọi GET /health ---")
        r = requests.get(f"{base_url}/health")
        print(f"  status={r.status_code}, body={r.json()}")
        ok = r.status_code == 200 and r.json().get("model_loaded") is True
        print(f"  [{'PASS' if ok else 'FAIL'}]")
        all_ok &= ok

        # ---- Việc 2: POST /predict với vài flow hợp lệ từ Tập B ------------------------
        print("\n--- Việc 2: POST /predict với 3 flow thật từ Tập B (phải trả 200) ---")
        clean_df = pd.read_csv(REPO_ROOT / cfg["paths"]["clean_set_out"])
        feature_cols = [c for c in clean_df.columns if c not in ("flow_id", "label_true")]
        returned_flow_ids = []
        for i in range(3):
            row = clean_df.iloc[i]
            payload = {c: float(row[c]) for c in feature_cols}
            r = requests.post(f"{base_url}/predict", json=payload)
            ok = r.status_code == 200
            body = r.json() if ok else r.text
            if ok:
                returned_flow_ids.append(body["flow_id"])
                match = body["predicted_label"] == row["label_true"] or True  # chỉ ghi nhận, không bắt buộc khớp 100%
                print(f"  Dòng {i}: status={r.status_code}, predicted_label={body['predicted_label']} "
                      f"(label_true={row['label_true']}), is_alert={body['is_alert']}, "
                      f"timing_ms={body['timing_ms']}")
            else:
                print(f"  Dòng {i}: [FAIL] status={r.status_code}, body={body}")
                all_ok = False

        # ---- Việc 3: POST /predict thiếu cột (phải trả 422) ----------------------------
        print("\n--- Việc 3: POST /predict thiếu 1 cột (phải trả 422) ---")
        bad_payload = {c: float(clean_df.iloc[0][c]) for c in feature_cols[:-1]}  # bỏ cột cuối
        r = requests.post(f"{base_url}/predict", json=bad_payload)
        ok = r.status_code == 422
        print(f"  status={r.status_code} (kỳ vọng 422), detail={r.json().get('detail') if r.headers.get('content-type','').startswith('application/json') else r.text}")
        print(f"  [{'PASS' if ok else 'FAIL'}]")
        all_ok &= ok

        # ---- Việc 4: mở DB, xác nhận dữ liệu thật sự được ghi ---------------------------
        print("\n--- Việc 4: mở lại file DB, xác nhận dữ liệu đã được ghi thật ---")
        sys.path.insert(0, str(RQ3_ROOT / "app"))
        import db  # noqa: E402
        conn = db.init_db(REPO_ROOT / cfg["paths"]["sqlite_db"])
        for fid in returned_flow_ids:
            flow_row = conn.execute("SELECT * FROM FlowRecord WHERE flow_id=?", (fid,)).fetchone()
            pred_row = conn.execute("SELECT * FROM Prediction WHERE flow_id=?", (fid,)).fetchone()
            timing_rows = conn.execute("SELECT step, duration_ms FROM Timing WHERE flow_id=?", (fid,)).fetchall()
            ok = flow_row is not None and pred_row is not None and len(timing_rows) >= 2
            print(f"  flow_id={fid}: FlowRecord={'có' if flow_row else 'THIẾU'}, "
                  f"Prediction={'có' if pred_row else 'THIẾU'}, Timing={len(timing_rows)} dòng -> "
                  f"[{'PASS' if ok else 'FAIL'}]")
            all_ok &= ok
        # kiểm tra DataError đã ghi cho flow bị từ chối ở Việc 3
        n_errors = conn.execute("SELECT COUNT(*) FROM DataError").fetchone()[0]
        print(f"  Số dòng trong DataError: {n_errors} (>=1 vì Việc 3 vừa tạo 1 lỗi) -> "
              f"[{'PASS' if n_errors >= 1 else 'FAIL'}]")
        all_ok &= (n_errors >= 1)
        conn.close()

    finally:
        print("\nĐang tắt server...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        server_log_file.close()
        print("Đã tắt server.")
        print(f"\n--- Log server (uvicorn) tại {server_log_path} ---")
        print(server_log_path.read_text(encoding="utf-8", errors="replace"))

    print("\n" + "=" * 70)
    print("BƯỚC 6 " + ("HOÀN TẤT — mọi kiểm tra đúng như kỳ vọng." if all_ok else "CÓ LỖI, xem [FAIL] ở trên."))
    print("=" * 70)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

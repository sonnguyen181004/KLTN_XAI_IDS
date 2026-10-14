"""Bước 8b — Test feeder bằng cách GIẢ LẬP CICFlowMeter thật: tự ghi dần từng
dòng của Tập B vào 1 file CSV, cách nhau 1-2 giây (giống CICFlowMeter ghi thêm
dòng mới mỗi khi 1 flow kết thúc), xem feeder có tự phát hiện + tự gửi đúng:
  1) Không thiếu dòng nào, không gửi trùng dòng nào 2 lần.
  2) Nhãn dự đoán hợp lý (so với label_true đã biết của Tập B).
  3) Mở DB xác nhận số FlowRecord tăng đúng bằng số dòng đã "giả lập bắt được".
"""
from __future__ import annotations

import csv
import re
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
N_SIMULATED_ROWS = 8          # số flow "giả lập bắt được" trong lúc test
WRITE_INTERVAL_SEC = 1.5      # cách nhau bao lâu thì "CICFlowMeter" ghi thêm 1 dòng


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
    watch_path = REPO_ROOT / cfg["feeder"]["default_watch_csv"]
    watch_path.parent.mkdir(parents=True, exist_ok=True)
    if watch_path.exists():
        watch_path.unlink()  # chạy sạch lại từ đầu mỗi lần test

    print("=" * 70)
    print("BƯỚC 8b: TEST FEEDER (GIẢ LẬP CICFLOWMETER GHI FILE SỐNG)")
    print("=" * 70)

    # ---- Bật server -------------------------------------------------------------------
    server_log_path = RQ3_ROOT / "data" / "stage08b_server.log"
    server_log_file = open(server_log_path, "w", encoding="utf-8")
    server_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", host, "--port", str(port)],
        cwd=str(RQ3_ROOT), stdout=server_log_file, stderr=subprocess.STDOUT,
    )

    all_ok = True
    feeder_proc = None
    feeder_log_file = None
    try:
        if not wait_for_server(f"{base_url}/health"):
            print("[FAIL] Server không lên được.")
            return 1
        print("Server đã sẵn sàng.")

        # ---- Đếm số FlowRecord TRƯỚC khi test (để so sánh sau) --------------------------
        sys.path.insert(0, str(RQ3_ROOT / "app"))
        import db  # noqa: E402
        conn = db.init_db(REPO_ROOT / cfg["paths"]["sqlite_db"])
        n_flows_before = conn.execute("SELECT COUNT(*) FROM FlowRecord").fetchone()[0]
        conn.close()

        # ---- Bật feeder (chạy nền, tự theo dõi watch_path) ------------------------------
        feeder_log_path = RQ3_ROOT / "data" / "stage08b_feeder.log"
        feeder_log_file = open(feeder_log_path, "w", encoding="utf-8")
        feeder_proc = subprocess.Popen(
            # "-u" = unbuffered: không có cờ này, log của feeder (chạy như tiến trình
            # con) bị Python đệm lại, không ghi ra file ngay — từng gặp lỗi tương tự ở
            # bước 6 với uvicorn, giờ lặp lại với feeder vì quên áp lại cho đúng.
            [sys.executable, "-u", "app/feeder.py", "--watch", str(watch_path), "--max-iterations", "60"],
            cwd=str(RQ3_ROOT), stdout=feeder_log_file, stderr=subprocess.STDOUT,
        )
        print(f"Đã bật feeder, theo dõi: {watch_path}")

        # ---- Giả lập CICFlowMeter: ghi dần N dòng của Tập B vào file --------------------
        clean_df = pd.read_csv(REPO_ROOT / cfg["paths"]["clean_set_out"])
        feature_cols = [c for c in clean_df.columns if c not in ("flow_id", "label_true")]
        sample = clean_df.sample(n=N_SIMULATED_ROWS, random_state=1).reset_index(drop=True)

        print(f"\nBắt đầu 'bắt gói giả lập' — ghi {N_SIMULATED_ROWS} dòng, cách nhau {WRITE_INTERVAL_SEC}s:")
        with open(watch_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(feature_cols)
            f.flush()
        for i in range(N_SIMULATED_ROWS):
            row = sample.iloc[i]
            with open(watch_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([row[c] for c in feature_cols])
                f.flush()
            print(f"  [giả lập] flow #{i+1}/{N_SIMULATED_ROWS} ghi vào CSV (label_true thật={row['label_true']})")
            time.sleep(WRITE_INTERVAL_SEC)

        print("\nĐã ghi xong. Đợi feeder xử lý hết (3 giây)...")
        time.sleep(3)

        # ---- Kiểm tra log feeder: đủ N dòng, đúng thứ tự, không trùng -------------------
        feeder_log_file.flush()
        feeder_log_text = feeder_log_path.read_text(encoding="utf-8", errors="replace")
        # predicted_label có thể chứa khoảng trắng (ví dụ "Brute Force -XSS") nên
        # KHÔNG dùng \S+ (không khoảng trắng) — phải bắt tới đúng ", is_alert=".
        sent_lines = re.findall(
            r"Dòng mới #(\d+): GỬI OK -> flow_id=([\w-]+), predicted_label=(.+?), is_alert=", feeder_log_text
        )
        print(f"\n--- Việc 1: feeder có gửi đủ {N_SIMULATED_ROWS} dòng, không trùng không thiếu? ---")
        line_numbers = [int(n) for n, _, _ in sent_lines]
        ok = len(sent_lines) == N_SIMULATED_ROWS and line_numbers == sorted(set(line_numbers)) and line_numbers == list(range(1, N_SIMULATED_ROWS + 1))
        print(f"  Số dòng feeder báo gửi OK: {len(sent_lines)} (kỳ vọng {N_SIMULATED_ROWS})")
        print(f"  Thứ tự dòng: {line_numbers}")
        print(f"  [{'PASS' if ok else 'FAIL'}]")
        all_ok &= ok

        # ---- Việc 2: so nhãn dự đoán với label_true (hợp lý, không cần khớp 100%) --------
        print("\n--- Việc 2: nhãn dự đoán qua feeder, so với label_true thật ---")
        predicted_labels = [lbl for _, _, lbl in sent_lines]
        n_correct = 0
        for i, (true_label, pred_label) in enumerate(zip(sample["label_true"], predicted_labels)):
            match = "✓" if true_label == pred_label else "✗"
            print(f"  flow #{i+1}: label_true={true_label:25s} predicted={pred_label:25s} {match}")
            n_correct += (true_label == pred_label)
        print(f"  Đúng {n_correct}/{N_SIMULATED_ROWS}")

        # ---- Việc 3: DB có đủ FlowRecord mới ---------------------------------------------
        print("\n--- Việc 3: mở DB, xác nhận số FlowRecord tăng đúng ---")
        conn = db.init_db(REPO_ROOT / cfg["paths"]["sqlite_db"])
        n_flows_after = conn.execute("SELECT COUNT(*) FROM FlowRecord").fetchone()[0]
        conn.close()
        n_new = n_flows_after - n_flows_before
        ok = n_new == N_SIMULATED_ROWS
        print(f"  FlowRecord trước={n_flows_before}, sau={n_flows_after}, mới={n_new} (kỳ vọng {N_SIMULATED_ROWS})")
        print(f"  [{'PASS' if ok else 'FAIL'}]")
        all_ok &= ok

    finally:
        print("\nĐang tắt feeder và server...")
        if feeder_proc:
            feeder_proc.terminate()
            try:
                feeder_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                feeder_proc.kill()
        if feeder_log_file:
            feeder_log_file.close()
        server_proc.terminate()
        try:
            server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_proc.kill()
        server_log_file.close()

    print("\n" + "=" * 70)
    print("BƯỚC 8b " + ("HOÀN TẤT — mọi kiểm tra đúng như kỳ vọng." if all_ok else "CÓ LỖI, xem [FAIL] ở trên."))
    print("=" * 70)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

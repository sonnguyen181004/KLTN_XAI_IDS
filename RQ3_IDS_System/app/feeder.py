"""Bước 8b — Bộ "feeder": nối CICFlowMeter với hệ thống TỰ ĐỘNG, không qua tay người.

Theo dõi 1 file CSV (CICFlowMeter ghi thêm dòng mới vào đây mỗi khi 1 flow kết
thúc — dù là bắt traffic SỐNG hay phát lại PCAP, CICFlowMeter đều ghi theo cùng
1 kiểu, nên feeder dùng chung cho cả 2 nguồn 1 và 2 ở plan.md mục 0.1).

Mỗi khi phát hiện dòng MỚI: đọc, đổi đơn vị thời gian nếu cần (CICFlowMeter thật
xuất giây, model cần micro giây), rồi tự POST /predict. KHÔNG cần CICFlowMeter
thật để test — xem scripts/stage08b_test_feeder.py (giả lập bằng cách tự ghi
từng dòng Tập B vào file này, cách nhau vài giây).

Chạy: python app/feeder.py --watch <đường_dẫn_csv> [--convert-units]
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalize import TIME_COLUMNS  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[2]
RQ3_ROOT = Path(__file__).resolve().parents[1]


def load_config() -> dict:
    with open(RQ3_ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def wait_for_file(path: Path, poll_s: float) -> None:
    while not path.exists():
        print(f"[feeder] Đang chờ file {path} xuất hiện (CICFlowMeter chưa ghi gì)...")
        time.sleep(poll_s)


def row_to_payload(row: dict, header: list[str], convert_units: bool) -> dict:
    """Chuyển 1 dòng CSV (dict tên_cột -> chuỗi) thành payload float, đổi đơn vị
    thời gian nếu cần. KHÔNG tự lọc cột ở đây — để /predict tự kiểm tra 78 cột
    (tầng 2 đã làm ở bước 4), feeder chỉ lo việc đọc + đổi đơn vị + gửi."""
    payload = {}
    for col in header:
        val = row.get(col)
        if val is None or val == "":
            continue
        try:
            payload[col] = float(val)
        except ValueError:
            continue  # cột không phải số (ví dụ Flow ID dạng chuỗi) -> bỏ, để /predict tự báo thiếu cột nếu cần
    if convert_units:
        for col in TIME_COLUMNS:
            if col in payload:
                payload[col] = payload[col] * 1_000_000
    return payload


def run_feeder(watch_path: Path, api_url: str, poll_interval_sec: float, convert_units: bool,
               max_iterations: int | None = None) -> None:
    print(f"[feeder] Bắt đầu theo dõi: {watch_path}")
    print(f"[feeder] Gửi tới: {api_url}/predict | đổi đơn vị μs: {convert_units} | "
          f"chu kỳ kiểm tra: {poll_interval_sec}s")
    wait_for_file(watch_path, poll_interval_sec)

    header: list[str] | None = None
    n_lines_processed = 0  # không tính dòng header
    n_sent = 0
    iteration = 0

    while max_iterations is None or iteration < max_iterations:
        iteration += 1
        with open(watch_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            all_rows = list(reader)

        if not all_rows:
            time.sleep(poll_interval_sec)
            continue

        if header is None:
            header = all_rows[0]
            print(f"[feeder] Đọc được header: {len(header)} cột")

        data_rows = all_rows[1:]
        new_rows = data_rows[n_lines_processed:]

        for raw_row in new_rows:
            if len(raw_row) != len(header):
                continue  # dòng chưa ghi xong hết (CICFlowMeter đang flush) -> bỏ qua, chờ lần sau
            row_dict = dict(zip(header, raw_row))
            payload = row_to_payload(row_dict, header, convert_units)
            n_lines_processed += 1

            try:
                r = requests.post(f"{api_url}/predict", json=payload, timeout=5)
                if r.status_code == 200:
                    body = r.json()
                    n_sent += 1
                    print(f"[feeder] Dòng mới #{n_lines_processed}: GỬI OK -> "
                          f"flow_id={body['flow_id']}, predicted_label={body['predicted_label']}, "
                          f"is_alert={body['is_alert']}, explanation_status={body['explanation_status']}")
                else:
                    print(f"[feeder] Dòng mới #{n_lines_processed}: LỖI {r.status_code} -> {r.text[:200]}")
            except requests.exceptions.RequestException as e:
                print(f"[feeder] Dòng mới #{n_lines_processed}: KHÔNG GỬI ĐƯỢC -> {e}")

        time.sleep(poll_interval_sec)

    print(f"[feeder] Dừng sau {iteration} lần kiểm tra. Tổng dòng đã xử lý: {n_lines_processed}, gửi OK: {n_sent}.")


def main():
    cfg = load_config()
    parser = argparse.ArgumentParser(description="Feeder: theo dõi CSV, tự gửi flow mới vào /predict")
    parser.add_argument("--watch", type=str, default=str(REPO_ROOT / cfg["feeder"]["default_watch_csv"]))
    parser.add_argument("--convert-units", action="store_true", default=cfg["feeder"]["convert_seconds_to_microseconds"])
    parser.add_argument("--max-iterations", type=int, default=None, help="Dừng sau N lần kiểm tra (dùng khi test; để trống = chạy mãi)")
    args = parser.parse_args()

    watch_path = Path(args.watch)
    api_url = f"http://{cfg['api']['host']}:{cfg['api']['port']}"
    run_feeder(watch_path, api_url, cfg["feeder"]["poll_interval_sec"], args.convert_units, args.max_iterations)


if __name__ == "__main__":
    main()

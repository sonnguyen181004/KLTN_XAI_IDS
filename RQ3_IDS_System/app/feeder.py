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
import uuid
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalize import TIME_COLUMNS  # noqa: E402
from flow_metadata import row_metadata

# CICFlowMeter 0.5.0 (cài ở RQ3_IDS_System/.venv_capture) xuất tên cột kiểu
# snake_case, hoàn toàn khác 78 tên cột model cần (chữ Hoa, có khoảng trắng —
# đúng kiểu CICIDS2018 gốc). Phát hiện khi bắt traffic thật lần đầu (bước
# "test real" sau bước 8b) — map 1-1 toàn bộ 78 cột, chỉ riêng cwr_flag_count
# (tên CICFlowMeter 0.5) khớp với CWE Flag Count (tên gốc CICIDS2018, cùng ý
# nghĩa cờ congestion). 4 cột định danh (src_ip, dst_ip, src_port, timestamp)
# không có trong 78 cột model cần nên không map — feeder cứ để nguyên, phía
# /predict tự bỏ qua (chỉ đọc đúng 78 cột nó cần).
CICFLOWMETER_COLUMN_MAP = {
    "dst_port": "Dst Port", "protocol": "Protocol", "flow_duration": "Flow Duration",
    "tot_fwd_pkts": "Tot Fwd Pkts", "tot_bwd_pkts": "Tot Bwd Pkts",
    "totlen_fwd_pkts": "TotLen Fwd Pkts", "totlen_bwd_pkts": "TotLen Bwd Pkts",
    "fwd_pkt_len_max": "Fwd Pkt Len Max", "fwd_pkt_len_min": "Fwd Pkt Len Min",
    "fwd_pkt_len_mean": "Fwd Pkt Len Mean", "fwd_pkt_len_std": "Fwd Pkt Len Std",
    "bwd_pkt_len_max": "Bwd Pkt Len Max", "bwd_pkt_len_min": "Bwd Pkt Len Min",
    "bwd_pkt_len_mean": "Bwd Pkt Len Mean", "bwd_pkt_len_std": "Bwd Pkt Len Std",
    "flow_byts_s": "Flow Byts/s", "flow_pkts_s": "Flow Pkts/s",
    "flow_iat_mean": "Flow IAT Mean", "flow_iat_std": "Flow IAT Std",
    "flow_iat_max": "Flow IAT Max", "flow_iat_min": "Flow IAT Min",
    "fwd_iat_tot": "Fwd IAT Tot", "fwd_iat_mean": "Fwd IAT Mean", "fwd_iat_std": "Fwd IAT Std",
    "fwd_iat_max": "Fwd IAT Max", "fwd_iat_min": "Fwd IAT Min",
    "bwd_iat_tot": "Bwd IAT Tot", "bwd_iat_mean": "Bwd IAT Mean", "bwd_iat_std": "Bwd IAT Std",
    "bwd_iat_max": "Bwd IAT Max", "bwd_iat_min": "Bwd IAT Min",
    "fwd_psh_flags": "Fwd PSH Flags", "bwd_psh_flags": "Bwd PSH Flags",
    "fwd_urg_flags": "Fwd URG Flags", "bwd_urg_flags": "Bwd URG Flags",
    "fwd_header_len": "Fwd Header Len", "bwd_header_len": "Bwd Header Len",
    "fwd_pkts_s": "Fwd Pkts/s", "bwd_pkts_s": "Bwd Pkts/s",
    "pkt_len_min": "Pkt Len Min", "pkt_len_max": "Pkt Len Max",
    "pkt_len_mean": "Pkt Len Mean", "pkt_len_std": "Pkt Len Std", "pkt_len_var": "Pkt Len Var",
    "fin_flag_cnt": "FIN Flag Cnt", "syn_flag_cnt": "SYN Flag Cnt", "rst_flag_cnt": "RST Flag Cnt",
    "psh_flag_cnt": "PSH Flag Cnt", "ack_flag_cnt": "ACK Flag Cnt", "urg_flag_cnt": "URG Flag Cnt",
    "cwr_flag_count": "CWE Flag Count", "ece_flag_cnt": "ECE Flag Cnt",
    "down_up_ratio": "Down/Up Ratio", "pkt_size_avg": "Pkt Size Avg",
    "fwd_seg_size_avg": "Fwd Seg Size Avg", "bwd_seg_size_avg": "Bwd Seg Size Avg",
    "fwd_byts_b_avg": "Fwd Byts/b Avg", "fwd_pkts_b_avg": "Fwd Pkts/b Avg",
    "fwd_blk_rate_avg": "Fwd Blk Rate Avg", "bwd_byts_b_avg": "Bwd Byts/b Avg",
    "bwd_pkts_b_avg": "Bwd Pkts/b Avg", "bwd_blk_rate_avg": "Bwd Blk Rate Avg",
    "subflow_fwd_pkts": "Subflow Fwd Pkts", "subflow_fwd_byts": "Subflow Fwd Byts",
    "subflow_bwd_pkts": "Subflow Bwd Pkts", "subflow_bwd_byts": "Subflow Bwd Byts",
    "init_fwd_win_byts": "Init Fwd Win Byts", "init_bwd_win_byts": "Init Bwd Win Byts",
    "fwd_act_data_pkts": "Fwd Act Data Pkts", "fwd_seg_size_min": "Fwd Seg Size Min",
    "active_mean": "Active Mean", "active_std": "Active Std",
    "active_max": "Active Max", "active_min": "Active Min",
    "idle_mean": "Idle Mean", "idle_std": "Idle Std", "idle_max": "Idle Max", "idle_min": "Idle Min",
}

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
    """Chuyển 1 dòng CSV (dict tên_cột -> chuỗi) thành payload float, đổi tên cột
    nếu là kiểu CICFlowMeter (snake_case) sang đúng tên model cần, đổi đơn vị thời
    gian nếu cần. KHÔNG tự lọc cột thừa ở đây — để /predict tự kiểm tra đủ 78 cột
    (tầng 2 đã làm ở bước 4); các cột định danh (src_ip, dst_ip...) không có
    trong CICFLOWMETER_COLUMN_MAP cứ để nguyên, /predict sẽ tự bỏ qua."""
    payload = {}
    for col in header:
        val = row.get(col)
        if val is None or val == "":
            continue
        try:
            value = float(val)
        except ValueError:
            continue  # cột không phải số (ví dụ src_ip dạng chuỗi) -> bỏ, để /predict tự báo thiếu cột nếu cần
        mapped_col = CICFLOWMETER_COLUMN_MAP.get(col, col)  # đã đúng tên (Tập A/B) thì giữ nguyên
        payload[mapped_col] = value
    if convert_units:
        for col in TIME_COLUMNS:
            if col in payload:
                payload[col] = payload[col] * 1_000_000
    return payload


def run_feeder(watch_path: Path, api_url: str, poll_interval_sec: float, convert_units: bool,
               max_iterations: int | None = None, capture_timezone: str | None = None) -> None:
    print(f"[feeder] Bắt đầu theo dõi: {watch_path}")
    print(f"[feeder] Gửi tới: {api_url}/predict | đổi đơn vị μs: {convert_units} | "
          f"chu kỳ kiểm tra: {poll_interval_sec}s")
    wait_for_file(watch_path, poll_interval_sec)

    header: list[str] | None = None
    n_lines_processed = 0  # không tính dòng header
    n_sent = 0
    run_id = str(uuid.uuid4())
    local_offset = datetime.now().astimezone().strftime('%z')
    capture_zone = capture_timezone or local_offset[:3] + ':' + local_offset[3:]
    print(f'[feeder] Lượt: {run_id} — {watch_path.name}. File có sẵn sẽ được đọc lại từ đầu.')
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

        data_rows = [row for row in all_rows[1:] if row]
        new_rows = data_rows[n_lines_processed:]

        for raw_row in new_rows:
            if len(raw_row) != len(header):
                break  # retry partial row next poll; never advance past it
            row_dict = dict(zip(header, raw_row))
            payload = row_to_payload(row_dict, header, convert_units)
            n_lines_processed += 1

            # Preserve packet time/IP separately; the live table sorts by API receive time.
            params = {'source': 'feeder_live', **row_metadata(row_dict, run_id, watch_path.name, capture_zone)}

            try:
                r = requests.post(f"{api_url}/predict", json=payload, params=params, timeout=5)
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
    parser.add_argument('--capture-timezone', default=None, help='Múi giờ timestamp CSV, ví dụ +07:00; mặc định giờ máy bắt')
    args = parser.parse_args()

    watch_path = Path(args.watch)
    api_url = f"http://{cfg['api']['host']}:{cfg['api']['port']}"
    api_url = os.environ.get('IDS_API_URL', api_url)
    run_feeder(watch_path, api_url, cfg["feeder"]["poll_interval_sec"], args.convert_units, args.max_iterations, args.capture_timezone)


if __name__ == "__main__":
    main()

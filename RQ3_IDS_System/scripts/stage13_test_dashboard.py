"""Bước 13 — Test Streamlit Dashboard bằng `streamlit.testing.v1.AppTest` — chạy
THẬT script `app/dashboard.py` ở chế độ headless (không cần trình duyệt/WebSocket),
bắt được exception thật nếu code có lỗi (khác với chỉ kiểm tra server HTTP có lên
không — HTML tĩnh của Streamlit không tiết lộ lỗi bên trong script, vì nội dung
thật chỉ render sau khi có kết nối WebSocket).

Cần API thật đang chạy ở config.yaml: api.host/api.port trước khi chạy test này
(dashboard gọi API qua HTTP, không đọc DB trực tiếp — đúng tách bạch Tầng 6).
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
        except requests.exceptions.RequestException:
            pass
        time.sleep(0.3)
    return False


def row_payload(df: pd.DataFrame, label: str, feature_cols: list[str]) -> dict:
    row = df[df["label_true"] == label].iloc[0]
    return {col: float(row[col]) for col in feature_cols}


def main() -> int:
    cfg = load_config()
    api_host, api_port = cfg["api"]["host"], cfg["api"]["port"]
    api_url = f"http://{api_host}:{api_port}"

    print("=" * 70)
    print("BƯỚC 13: TEST STREAMLIT DASHBOARD (AppTest — chạy thật, headless)")
    print("=" * 70)

    df = pd.read_csv(RQ3_ROOT / "data" / "clean_holdout_set.csv")
    feature_cols = [c for c in df.columns if c not in ("label_true", "flow_id")]

    api_log = open(RQ3_ROOT / "data" / "stage13_api.log", "w", encoding="utf-8")
    api_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", api_host, "--port", str(api_port)],
        cwd=str(RQ3_ROOT), stdout=api_log, stderr=subprocess.STDOUT,
    )

    all_ok = True
    try:
        if not wait_for_server(f"{api_url}/health"):
            print("[FAIL] API không lên được.")
            return 1
        print("API đã sẵn sàng.")

        alert_ids = []
        for label in ["Bot", "SQL Injection", "DoS attacks-Hulk"]:
            payload = row_payload(df, label, feature_cols)
            r = requests.post(f"{api_url}/predict", json=payload)
            alert_ids.append(r.json()["alert_id"])
        print(f"Đã bắn 3 flow (Bot, SQL Injection, DoS attacks-Hulk) để có dữ liệu hiển thị: {alert_ids}")
        time.sleep(3)  # cho hàng đợi SHAP xử lý xong

        # Xin thêm LIME cho 1 alert, để test được cả tab LIME (không chỉ tab SHAP).
        requests.post(f"{api_url}/explain", json={"alert_id": alert_ids[0], "method": "lime"})
        print(f"Đã xin LIME cho alert {alert_ids[0]} để test được cả tab LIME.")

        sys.path.insert(0, str(RQ3_ROOT))
        from streamlit.testing.v1 import AppTest

        print("\n--- Việc 1: Chạy app/dashboard.py bằng AppTest (lần đầu, chưa chọn gì) ---")
        at = AppTest.from_file(str(RQ3_ROOT / "app" / "dashboard.py"))
        at.run(timeout=30)
        ok = not at.exception
        print(f"  Số exception bắt được: {len(at.exception)}")
        if at.exception:
            for e in at.exception:
                print(f"  [FAIL] {e.value!r}\n{e.stack_trace}")
        print(f"  [{'PASS' if ok else 'FAIL'}]")
        all_ok &= ok

        print("\n--- Việc 2: Trang có tiêu đề + ít nhất 1 bảng (bảng cảnh báo) ---")
        has_title = any("IDS" in t.value for t in at.title)
        has_dataframe = len(at.dataframe) >= 1
        ok = has_title and has_dataframe
        print(f"  có tiêu đề chứa 'IDS': {has_title}, số bảng dataframe tìm thấy: {len(at.dataframe)}")
        print(f"  [{'PASS' if ok else 'FAIL'}]")
        all_ok &= ok

        print("\n--- Việc 3: Chọn cảnh báo có LIME trong selectbox, chạy lại, không lỗi ---")
        # Nhận diện theo LABEL, không theo số lượng lựa chọn — khi DB ít alert (sau
        # khi dọn sạch để test), ô lọc nhánh ("(tất cả)"/A/B = 3) và ô chọn alert có
        # thể TRÙNG số lượng lựa chọn, lấy theo max(len(options)) sẽ chọn nhầm ô
        # (lỗi thật đã gặp khi DB chỉ có đúng 3 alert).
        alert_select = next(sb for sb in at.selectbox if sb.label == "Chọn cảnh báo để xem chi tiết")
        target_option = next((o for o in alert_select.options if alert_ids[0][:8] in o), None)
        ok = target_option is not None
        if ok:
            alert_select.set_value(target_option).run(timeout=30)
            ok = not at.exception
            print(f"  Đã chọn đúng cảnh báo có LIME, số exception sau khi chạy lại: {len(at.exception)}")
            if at.exception:
                for e in at.exception:
                    print(f"  [FAIL] {e.value!r}\n{e.stack_trace}")
            has_lime_table = len(at.dataframe) >= 2  # ít nhất bảng cảnh báo + 1 bảng chi tiết (SHAP hoặc LIME)
            ok = ok and has_lime_table
            print(f"  số bảng dataframe sau khi chọn: {len(at.dataframe)}")
        else:
            print("  [FAIL] Không tìm thấy cảnh báo có LIME trong danh sách lựa chọn.")
        print(f"  [{'PASS' if ok else 'FAIL'}]")
        all_ok &= ok

        print("\n--- Việc 4: Tab 'Gửi file CSV' — upload Tập B, bấm gửi, kiểm tra alert mới xuất hiện ---")
        count_before = requests.get(f"{api_url}/alerts").json()["count"]
        at2 = AppTest.from_file(str(RQ3_ROOT / "app" / "dashboard.py"))
        at2.run(timeout=30)
        csv_bytes = (RQ3_ROOT / "data" / "clean_holdout_set.csv").read_bytes()
        csv_uploader = next(fu for fu in at2.file_uploader if fu.key == "csv_uploader")
        csv_uploader.upload("clean_holdout_set.csv", csv_bytes, "text/csv").run(timeout=30)
        ok = not at2.exception
        print(f"  Sau khi upload CSV, số exception: {len(at2.exception)}")
        send_button = next((b for b in at2.button if b.key == "send_csv"), None)
        ok = ok and send_button is not None
        if ok:
            send_button.set_value(True).run(timeout=120)  # 241 dòng, mỗi dòng 1 request /predict qua API thật
            ok = not at2.exception
            print(f"  Sau khi bấm gửi, số exception: {len(at2.exception)}")
            if at2.exception:
                for e in at2.exception:
                    print(f"  [FAIL] {e.value!r}\n{e.stack_trace}")
        count_after = requests.get(f"{api_url}/alerts").json()["count"]
        ok = ok and count_after > count_before
        print(f"  Số alert trước khi gửi: {count_before}, sau khi gửi: {count_after} (phải tăng)")
        print(f"  [{'PASS' if ok else 'FAIL'}]")
        all_ok &= ok

        print("\n--- Việc 5: Tab 'Phát lại PCAP' — upload 1 file .pcap thật, trích xuất + gửi ---")
        venv_python = RQ3_ROOT / ".venv_capture" / "Scripts" / "python.exe"
        synthetic_pcap = RQ3_ROOT / "data" / "stage13_synthetic.pcap"
        if not venv_python.exists():
            print(f"  [BỎ QUA] Chưa có {venv_python} (chưa cài môi trường bắt gói — xem M3/5.1 trong plan.md).")
        else:
            gen = subprocess.run(
                [str(venv_python), str(RQ3_ROOT / "scripts" / "make_synthetic_pcap.py"), str(synthetic_pcap)],
                cwd=str(RQ3_ROOT), capture_output=True, text=True, timeout=30,
                encoding="utf-8", errors="replace",
            )
            if gen.returncode != 0 or not synthetic_pcap.exists():
                print(f"  [FAIL] Không tạo được file pcap giả lập để test: {gen.stdout}{gen.stderr}")
                all_ok = False
            else:
                count_before_pcap = requests.get(f"{api_url}/alerts").json()["count"]
                at3 = AppTest.from_file(str(RQ3_ROOT / "app" / "dashboard.py"))
                at3.run(timeout=30)
                pcap_bytes = synthetic_pcap.read_bytes()
                pcap_uploader = next(fu for fu in at3.file_uploader if fu.key == "pcap_uploader")
                pcap_uploader.upload("stage13_synthetic.pcap", pcap_bytes, "application/octet-stream").run(timeout=30)
                ok = not at3.exception
                send_pcap_button = next((b for b in at3.button if b.key == "send_pcap"), None)
                ok = ok and send_pcap_button is not None
                if ok:
                    send_pcap_button.set_value(True).run(timeout=60)
                    ok = not at3.exception
                    print(f"  Sau khi bấm 'Trích xuất + gửi vào /predict', số exception: {len(at3.exception)}")
                    if at3.exception:
                        for e in at3.exception:
                            print(f"  [FAIL] {e.value!r}\n{e.stack_trace}")
                count_after_pcap = requests.get(f"{api_url}/alerts").json()["count"] if ok else count_before_pcap
                # File pcap giả lập chỉ có 1 flow TCP thường (không phải tấn công) -> model
                # rất có thể đoán Benign (không tạo alert) -> KHÔNG kiểm tra count tăng ở
                # đây, chỉ cần không exception VÀ không còn file CSV cũ lẫn vào (unlink
                # trước đó trong code dashboard) là đủ xác nhận luồng chạy đúng.
                print(f"  Số alert trước: {count_before_pcap}, sau: {count_after_pcap} (không bắt buộc tăng — "
                      "flow giả lập không phải tấn công)")
                print(f"  [{'PASS' if ok else 'FAIL'}]")
                all_ok &= ok

    finally:
        print("\nĐang tắt API...")
        api_proc.terminate()
        try:
            api_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            api_proc.kill()
        api_log.close()

    print("\n" + "=" * 70)
    print("BƯỚC 13 " + ("HOÀN TẤT — mọi kiểm tra tự động đúng như kỳ vọng." if all_ok else "CÓ LỖI, xem [FAIL] ở trên."))
    print("=" * 70)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

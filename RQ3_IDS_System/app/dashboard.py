"""Bước 13 — Tầng 6 (Khối 7): Streamlit Dashboard, 1 trang duy nhất — đúng mục 3 của
plan.md: bảng cảnh báo, biểu đồ SHAP/LIME có dấu (2 tab), bảng độ tin cậy, nhãn
nhánh A/B, GET /health. Dashboard KHÔNG đọc trực tiếp file DB — chỉ gọi API (đúng
tách bạch Tầng 6 API / Tầng 6 Dashboard trong kiến trúc), giống hệt cách
scripts/stageNN_test_*.py đã làm từ bước 6 tới giờ.

Chạy: streamlit run app/dashboard.py  (từ thư mục RQ3_IDS_System/)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
import yaml

RQ3_ROOT = Path(__file__).resolve().parents[1]

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


@st.cache_data(ttl=5)
def load_config() -> dict:
    with open(RQ3_ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


cfg = load_config()
API_URL = f"http://{cfg['api']['host']}:{cfg['api']['port']}"

st.set_page_config(page_title="RQ3 — IDS có giải thích", layout="wide")
st.title("Hệ thống IDS có giải thích (RQ3)")


# ---------------------------------------------------------------------------
# GET /health — trạng thái model + hàng đợi
# ---------------------------------------------------------------------------
def fetch_health() -> dict | None:
    try:
        r = requests.get(f"{API_URL}/health", timeout=3)
        return r.json() if r.status_code == 200 else None
    except requests.exceptions.RequestException:
        return None


def fetch_queue_status() -> dict | None:
    try:
        r = requests.get(f"{API_URL}/explain_queue_status", timeout=3)
        return r.json() if r.status_code == 200 else None
    except requests.exceptions.RequestException:
        return None


health = fetch_health()
if health is None:
    st.error(f"Không kết nối được API tại {API_URL}. Hãy chạy: uvicorn app.main:app --port {cfg['api']['port']}")
    st.stop()

q = fetch_queue_status() or {}
cols = st.columns(5)
cols[0].metric("Model", "Đã nạp" if health["model_loaded"] else "LỖI")
cols[1].metric("Phiên bản model", health["model_version"])
cols[2].metric("Số lớp", health["n_classes"])
cols[3].metric("Hàng đợi SHAP", f"{q.get('qsize', '?')}/{q.get('maxsize', '?')}")
cols[4].metric("Đã bỏ (hàng đợi đầy)", q.get("n_dropped", "?"))

st.divider()

# ---------------------------------------------------------------------------
# Nạp dữ liệu vào hệ thống — CSV có đặc trưng sẵn / PCAP phát lại (nguồn 2 ở plan.md
# mục 0.1). Vẫn qua HTTP /predict như mọi nguồn khác — Dashboard chỉ là tiện ích gửi
# hộ, không tự ý gọi tắt qua hàm Python nào khác.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent))
from feeder import CICFLOWMETER_COLUMN_MAP, row_to_payload  # noqa: E402


def extract_flow_timestamp(row_dict: dict) -> str | None:
    """Lấy lúc gói tin THẬT xảy ra từ cột `timestamp` CICFlowMeter ghi sẵn (dạng
    "YYYY-MM-DD HH:MM:SS", không có timezone) — đổi sang dạng gần ISO (thay khoảng
    trắng bằng "T") để so sánh thứ tự đúng với `received_at` (ISO 8601 có timezone)
    khi sắp xếp trên Dashboard. Trả None nếu nguồn không có cột này (vd Tập A/B)."""
    ts = row_dict.get("timestamp")
    if not ts:
        return None
    return ts.replace(" ", "T")


st.subheader("Nạp dữ liệu vào hệ thống")
tab_csv, tab_pcap = st.tabs(["Gửi file CSV (đặc trưng có sẵn)", "Phát lại file PCAP"])

with tab_csv:
    st.caption("Dùng cho CSV đã có đủ 78 đặc trưng (Tập A/B, hoặc CSV do CICFlowMeter ghi ra sẵn) — "
               "mỗi dòng sẽ được gửi vào `/predict`, giống hệt cách `scripts/feeder.py` vẫn làm qua terminal.")
    csv_file = st.file_uploader("Chọn file .csv", type=["csv"], key="csv_uploader")
    convert_units_csv = st.checkbox(
        "Đổi đơn vị thời gian giây -> micro giây (chỉ tick nếu CSV này do CICFlowMeter THẬT xuất ra)",
        value=False, key="csv_convert_units")
    if csv_file is not None:
        raw_text = csv_file.getvalue().decode("utf-8-sig")
        lines = raw_text.splitlines()
        import csv as csv_module
        reader = csv_module.reader(lines)
        rows = list(reader)
        header, data_rows = rows[0], rows[1:]
        st.write(f"Đọc được {len(data_rows)} dòng, {len(header)} cột.")
        if st.button(f"Gửi {len(data_rows)} dòng vào /predict", key="send_csv"):
            progress = st.progress(0.0)
            results = []
            for i, raw_row in enumerate(data_rows):
                if len(raw_row) != len(header):
                    results.append({"dòng": i + 1, "kết quả": "BỎ QUA — số cột không khớp header"})
                    continue
                row_dict = dict(zip(header, raw_row))
                payload = row_to_payload(row_dict, header, convert_units_csv)
                flow_ts = extract_flow_timestamp(row_dict)
                try:
                    r = requests.post(f"{API_URL}/predict", json=payload, timeout=10,
                                       params={"source": "csv_upload", "flow_timestamp": flow_ts} if flow_ts
                                       else {"source": "csv_upload"})
                    if r.status_code == 200:
                        b = r.json()
                        results.append({"dòng": i + 1, "kết quả": f"OK — {b['predicted_label']} "
                                                                    f"(is_alert={b['is_alert']})"})
                    else:
                        results.append({"dòng": i + 1, "kết quả": f"LỖI {r.status_code} — {r.text[:150]}"})
                except requests.exceptions.RequestException as e:
                    results.append({"dòng": i + 1, "kết quả": f"KHÔNG GỬI ĐƯỢC — {e}"})
                progress.progress((i + 1) / len(data_rows))
            st.dataframe(pd.DataFrame(results), width="stretch", hide_index=True)
            st.toast(f"Đã gửi xong {len(data_rows)} dòng — bảng cảnh báo bên dưới vừa được làm mới.", icon="✅")
            st.rerun()

with tab_pcap:
    st.caption("Đọc lại 1 file .pcap đã ghi sẵn — dùng CICFlowMeter (môi trường `.venv_capture`) để trích đặc "
               "trưng, KHÔNG cần tcpreplay, giống đúng nguồn 2 ở `docs/plan.md` mục 0.1.")
    venv_python = RQ3_ROOT / ".venv_capture" / "Scripts" / "python.exe"
    if not venv_python.exists():
        st.error(f"Chưa thấy môi trường bắt gói tại {venv_python} — xem mục M3/5.1 trong docs/plan.md để cài "
                 "Npcap + cicflowmeter trước khi dùng tab này.")
    else:
        pcap_file = st.file_uploader("Chọn file .pcap", type=["pcap", "pcapng"], key="pcap_uploader")
        if pcap_file is not None and st.button("Trích xuất + gửi vào /predict", key="send_pcap"):
            upload_path = RQ3_ROOT / "data" / "dashboard_uploaded_replay.pcap"
            output_csv = RQ3_ROOT / "data" / "dashboard_replay_output.csv"
            upload_path.write_bytes(pcap_file.getvalue())
            output_csv.unlink(missing_ok=True)  # xóa kết quả lần trước, tránh đọc nhầm dữ liệu cũ

            timed_out = False
            with st.spinner("Đang chạy CICFlowMeter trích đặc trưng từ file pcap..."):
                try:
                    # encoding="utf-8": LỖI THẬT đã gặp — mặc định subprocess.run() đọc
                    # output bằng encoding hệ thống (cp1252 trên Windows), nhưng log DEBUG
                    # của CICFlowMeter có byte không giải mã được bằng cp1252. Khi đó,
                    # thread đọc output nội bộ của subprocess CHẾT ÂM THẦM (in traceback ra
                    # console server, không ném lên luồng chính) và để proc.stdout = None,
                    # gây crash khác hẳn (TypeError khi cộng None với chuỗi ở dưới). Ép đúng
                    # utf-8 (khớp `sys.stdout.reconfigure(encoding="utf-8")` ở các script con)
                    # để không bao giờ rơi vào trường hợp đó.
                    proc = subprocess.run(
                        [str(venv_python), str(RQ3_ROOT / "scripts" / "run_live_capture.py"),
                         "--pcap-input", str(upload_path), "--output", str(output_csv)],
                        cwd=str(RQ3_ROOT), capture_output=True, text=True, timeout=120,
                        encoding="utf-8", errors="replace",
                    )
                    proc_stdout, proc_stderr, proc_returncode = proc.stdout, proc.stderr, proc.returncode
                except subprocess.TimeoutExpired as e:
                    timed_out = True
                    proc_stdout, proc_stderr, proc_returncode = e.stdout, e.stderr, None

            # proc_stdout/proc_stderr có thể là None (vd khi hết 120s timeout, tiến trình
            # bị kill trước khi kịp trả hết output) — không được cộng thẳng 2 chuỗi lại,
            # phải phòng hờ None trước (lỗi thật đã gặp: TypeError unsupported operand
            # 'NoneType' và 'str').
            with st.expander("Log CICFlowMeter (bấm để xem)"):
                st.code((proc_stdout or "") + (proc_stderr or ""))

            if timed_out:
                st.error("CICFlowMeter chạy quá 120 giây không xong (file pcap có thể quá lớn, hoặc tiến trình bị "
                         "treo) — đã tự dừng. Thử lại với file nhỏ hơn, hoặc báo lại nếu file nhỏ mà vẫn bị vậy.")
            elif proc_returncode != 0 or not output_csv.exists():
                st.error("CICFlowMeter chạy lỗi hoặc không ghi ra file — xem log phía trên.")
            else:
                with open(output_csv, encoding="utf-8-sig", newline="") as f:
                    import csv as csv_module
                    rows = list(csv_module.reader(f))
                if len(rows) <= 1:
                    st.warning("File pcap không trích được flow nào (có thể quá ngắn hoặc không có TCP/UDP).")
                else:
                    header, data_rows = rows[0], rows[1:]
                    st.write(f"Trích được {len(data_rows)} flow từ pcap. Đang gửi vào /predict "
                             "(tự đổi đơn vị giây -> micro giây vì CICFlowMeter thật xuất ra giây)...")
                    results = []
                    for i, raw_row in enumerate(data_rows):
                        if len(raw_row) != len(header):
                            continue
                        row_dict = dict(zip(header, raw_row))
                        payload = row_to_payload(row_dict, header, convert_units=True)
                        flow_ts = extract_flow_timestamp(row_dict)
                        try:
                            r = requests.post(f"{API_URL}/predict", json=payload, timeout=10,
                                               params={"source": "pcap_replay", "flow_timestamp": flow_ts} if flow_ts
                                               else {"source": "pcap_replay"})
                            if r.status_code == 200:
                                b = r.json()
                                results.append({"flow": i + 1, "kết quả": f"OK — {b['predicted_label']} "
                                                                           f"(is_alert={b['is_alert']})"})
                            else:
                                results.append({"flow": i + 1, "kết quả": f"LỖI {r.status_code}"})
                        except requests.exceptions.RequestException as e:
                            results.append({"flow": i + 1, "kết quả": f"KHÔNG GỬI ĐƯỢC — {e}"})
                    st.dataframe(pd.DataFrame(results), width="stretch", hide_index=True)
                    st.toast(f"Đã gửi xong {len(results)} flow trích từ pcap — bảng cảnh báo bên dưới vừa được "
                             "làm mới.", icon="✅")
                    st.rerun()

st.divider()

# ---------------------------------------------------------------------------
# GET /flows — TẤT CẢ flow đã xử lý, kể cả Benign (Benign không tạo Alert nên
# không có ở bảng cảnh báo bên dưới — theo yêu cầu thực tế khi test: cần thấy cả
# traffic bình thường để biết hệ thống có đang hoạt động).
# ---------------------------------------------------------------------------
st.subheader("Tất cả flow đã xử lý (kể cả Benign)")
try:
    r = requests.get(f"{API_URL}/flows", params={"limit": 200}, timeout=10)
    r.raise_for_status()
    flows = r.json()["flows"]
except requests.exceptions.RequestException as e:
    st.error(f"GET /flows lỗi: {e}")
    flows = []

if not flows:
    st.info("Chưa có flow nào được xử lý.")
else:
    n_benign = sum(1 for f in flows if f["predicted_label"] == "Benign")
    n_alert = sum(1 for f in flows if f["is_alert"])
    st.caption(f"{len(flows)} flow gần nhất — {n_benign} Benign, {n_alert} tạo cảnh báo (khác Benign).")
    flows_df = pd.DataFrame([
        {
            "flow_id": f["flow_id"][:8] + "…",
            "thời điểm gói tin thật (nếu biết)": f["flow_timestamp"] or "(không rõ — nguồn không kèm mốc thời gian gốc)",
            "lúc hệ thống xử lý": f["received_at"],
            "nguồn": f["source"],
            "predicted_label": f["predicted_label"] or "(đang xử lý)",
            "is_alert": f["is_alert"],
            "nhãn thật (nếu biết)": f["label_true"] or "",
        }
        for f in flows
    ])
    st.dataframe(flows_df, width="stretch", hide_index=True)

st.divider()

# ---------------------------------------------------------------------------
# Bộ lọc + GET /alerts — bảng cảnh báo
# ---------------------------------------------------------------------------
st.subheader("Danh sách cảnh báo")

filt_cols = st.columns(4)
f_label = filt_cols[0].text_input("Lọc theo nhãn (predicted_label)", value="")
f_branch = filt_cols[1].selectbox("Lọc theo nhánh", ["(tất cả)", "A", "B"])
f_since = filt_cols[2].text_input("Từ thời gian (ISO, bỏ trống = không lọc)", value="")
f_limit = filt_cols[3].number_input("Số dòng hiển thị tối đa", min_value=10, max_value=1000, value=100, step=10)

params = {}
if f_label.strip():
    params["label"] = f_label.strip()
if f_branch != "(tất cả)":
    params["branch"] = f_branch
if f_since.strip():
    params["since"] = f_since.strip()

try:
    r = requests.get(f"{API_URL}/alerts", params=params, timeout=10)
    r.raise_for_status()
    alerts = r.json()["alerts"]
except requests.exceptions.RequestException as e:
    st.error(f"GET /alerts lỗi: {e}")
    st.stop()

st.caption(f"Tổng số cảnh báo khớp bộ lọc: {len(alerts)} (hiển thị tối đa {f_limit} dòng mới nhất)")

if not alerts:
    st.info("Chưa có cảnh báo nào khớp bộ lọc.")
    st.stop()

table_df = pd.DataFrame([
    {
        "alert_id": a["alert_id"][:8] + "…",
        "thời điểm gói tin thật (nếu biết)": a["flow_timestamp"] or "(không rõ — nguồn không kèm mốc thời gian gốc)",
        "lúc hệ thống tạo cảnh báo": a["created_at"],
        "nguồn": a["source"],
        "predicted_label": a["predicted_label"],
        "branch": a["branch"] or "(chưa xử lý)",
        "explanation_status": a["explanation_status"],
        "rare_class_flag": a["rare_class_flag"],
        "env_fingerprint_flag": a["env_fingerprint_flag"],
    }
    for a in alerts[: int(f_limit)]
])
st.dataframe(table_df, width="stretch", hide_index=True)

st.divider()

# ---------------------------------------------------------------------------
# Chọn 1 Alert để xem chi tiết: SHAP/LIME có dấu + bảng độ tin cậy + nhánh A/B
# ---------------------------------------------------------------------------
st.subheader("Chi tiết 1 cảnh báo")

alert_options = {f"{a['created_at']} — {a['predicted_label']} — {a['alert_id'][:8]}…": a for a in alerts[: int(f_limit)]}
chosen_key = st.selectbox("Chọn cảnh báo để xem chi tiết", list(alert_options.keys()))
alert = alert_options[chosen_key]

st.markdown(f"**Nhãn dự đoán:** `{alert['predicted_label']}`  |  "
            f"**Nhánh:** `{alert['branch'] or '(chưa xử lý)'}`  |  "
            f"**Trạng thái giải thích:** `{alert['explanation_status']}`")
if alert["branch"] == "B":
    st.warning(f"⚠️ Cần xem lại — {alert['branch_reason']}")
elif alert["branch"] == "A":
    st.success("Không có cờ nào được bật — giải thích hiển thị bình thường.")

tab_shap, tab_lime = st.tabs(["SHAP (tự động)", "LIME (theo yêu cầu)"])

with tab_shap:
    if alert["shap_top5"] is None:
        st.info("SHAP chưa xử lý xong (đang chờ hàng đợi) hoặc đã bị bỏ do hàng đợi đầy lúc tạo cảnh báo này.")
    else:
        shap_df = pd.DataFrame(alert["shap_top5"])
        shap_df = shap_df.sort_values("phi")
        st.caption("Đóng góp có dấu (phi) của Top-5 đặc trưng — dương = đẩy về nhãn dự đoán, âm = đẩy ra khỏi.")
        st.bar_chart(shap_df.set_index("feature")["phi"])
        st.dataframe(shap_df, width="stretch", hide_index=True)

with tab_lime:
    if alert["lime_top5"] is None:
        st.info("Chưa có LIME cho cảnh báo này — bấm nút dưới để xin giải thích LIME (chạy chậm hơn SHAP ~8 lần, "
                "chỉ chạy khi analyst chủ động bấm, đúng nguyên tắc kiến trúc).")
        if st.button("Xin giải thích LIME cho cảnh báo này", key=f"lime_{alert['alert_id']}"):
            try:
                r = requests.post(f"{API_URL}/explain", json={"alert_id": alert["alert_id"], "method": "lime"}, timeout=30)
                if r.status_code == 200:
                    st.success("Đã có LIME — bấm lại nút lọc/refresh phía trên để tải lại dữ liệu mới.")
                else:
                    st.error(f"Lỗi {r.status_code}: {r.text[:300]}")
            except requests.exceptions.RequestException as e:
                st.error(f"Gọi /explain lỗi: {e}")
    else:
        lime_df = pd.DataFrame(alert["lime_top5"])
        lime_df = lime_df.sort_values("weight")
        st.caption("Trọng số có dấu (weight) của Top-5 mô tả đặc trưng LIME — "
                   f"Agreement Jaccard@5 với SHAP: {alert['agreement_jaccard5']:.3f}" if alert["agreement_jaccard5"] is not None else "")
        st.bar_chart(lime_df.set_index("feature_desc")["weight"])
        st.dataframe(lime_df, width="stretch", hide_index=True)

st.divider()
st.subheader("Bảng độ tin cậy")
reliability_df = pd.DataFrame([{
    "faithfulness_proxy_drop (PROXY, không phải đo đầy đủ RQ2)": alert["faithfulness_proxy_drop"],
    "env_fingerprint_count": alert["env_fingerprint_count"],
    "env_fingerprint_flag (cờ cảnh báo, chưa phải bằng chứng)": alert["env_fingerprint_flag"],
    "rare_class_flag": alert["rare_class_flag"],
    "stability_lookup (RQ2, bước 10 — chưa làm)": alert["stability_lookup"],
    "agreement_jaccard5": alert["agreement_jaccard5"],
    "branch": alert["branch"],
}])
st.dataframe(reliability_df, width="stretch", hide_index=True)
st.caption("⚠️ faithfulness_proxy_drop chỉ là proxy một bước/một giá trị nền — không phải phép đo faithfulness "
           "đầy đủ của RQ2. env_fingerprint_flag chỉ là cờ cảnh báo (giả thuyết chưa kiểm chứng, xem E4), "
           "không phải bằng chứng model sai. Xem mục 3 'Lưu ý quan trọng — tránh overclaim' trong docs/plan.md.")

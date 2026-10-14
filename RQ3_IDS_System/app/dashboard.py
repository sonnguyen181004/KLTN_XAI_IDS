"""Bước 13 — Tầng 6 (Khối 7): Streamlit Dashboard, 1 trang duy nhất — đúng mục 3 của
plan.md: bảng cảnh báo, biểu đồ SHAP/LIME có dấu (2 tab), bảng độ tin cậy, nhãn
nhánh A/B, GET /health. Dashboard KHÔNG đọc trực tiếp file DB — chỉ gọi API (đúng
tách bạch Tầng 6 API / Tầng 6 Dashboard trong kiến trúc), giống hệt cách
scripts/stageNN_test_*.py đã làm từ bước 6 tới giờ.

Chạy: streamlit run app/dashboard.py  (từ thư mục RQ3_IDS_System/)
"""
from __future__ import annotations

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
        "created_at": a["created_at"],
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

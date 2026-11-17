"""Standalone Streamlit view for the isolated Java extractor and frozen M0."""
import os

import altair as alt
import pandas as pd
import requests
import streamlit as st

API = "http://127.0.0.1:8765"
TOKEN = os.environ.get("JAVA_M0_TRIAL_TOKEN", "")
HEADERS = {"X-Trial-Token": TOKEN}


def call(method, path, **kwargs):
    response = requests.request(method, API + path, headers=HEADERS, timeout=30, **kwargs)
    if not response.ok:
        raise RuntimeError(f"{response.status_code}: {response.text[:350]}")
    return response.json()


st.set_page_config(page_title="Java CICFlowMeter · M0", layout="wide")
st.title("IDS thử nghiệm · Java CICFlowMeter + M0")
st.caption("Card mạng → Java gom flow → M0 dự đoán → SHAP; LIME chạy khi yêu cầu. Khu thử độc lập với hệ thống chính.")

try:
    options = call("GET", "/interfaces")
except Exception as exc:
    st.error(f"Không kết nối được dịch vụ Java–M0: {exc}")
    st.stop()


@st.fragment(run_every="2s")
def live_view():
    state = call("GET", "/status")
    a, b, c = st.columns(3)
    a.metric("Trạng thái", state["phase"])
    b.metric("Flow đã xuất", state["rows"])
    c.metric("Cảnh báo", sum(v for k, v in state["labels"].items() if k != "Benign"))
    if state["error"]:
        st.error(state["error"])
    if state["packet_summary"]:
        st.caption("Java: " + state["packet_summary"])

    names = [f"{x['description']} [{x['name']}]" for x in options]
    choice = st.selectbox("Interface cần bắt", range(len(options)), format_func=lambda i: names[i],
                          index=next((i for i, x in enumerate(options) if "WiFi 6" in x["description"]), 0),
                          disabled=state["phase"] in ("capturing", "stopping"))
    seconds = st.number_input("Thời gian (giây); 0 = chạy đến khi bấm Dừng", min_value=0, max_value=3600,
                              value=0, step=10, disabled=state["phase"] in ("capturing", "stopping"))
    start_col, stop_col = st.columns(2)
    if start_col.button("Bắt đầu Java", disabled=state["phase"] in ("capturing", "stopping"), type="primary"):
        try:
            call("POST", "/start", json={"interface": options[choice]["name"], "seconds": int(seconds)})
            st.rerun()
        except Exception as exc:
            st.error(f"Không bắt đầu được: {exc}")
    if stop_col.button("Dừng và ghi nốt flow", disabled=state["phase"] != "capturing"):
        try:
            call("POST", "/stop")
            st.rerun()
        except Exception as exc:
            st.error(f"Không dừng được: {exc}")

    rows = call("GET", "/flows")
    if not rows:
        st.info("Chưa có flow được Java xuất. Kết nối còn mở sẽ xuất khi đóng hoặc khi bạn dừng capture.")
        return
    labels = pd.Series([r["prediction"] or "Không hợp lệ" for r in rows]).value_counts()
    st.subheader("Dự đoán của M0")
    st.bar_chart(labels)
    view = pd.DataFrame([{k: r.get(k) for k in ("id", "time", "src_ip", "src_port", "dst_ip", "dst_port", "protocol", "prediction", "confidence")}
                         for r in rows[::-1]])
    view["confidence"] = (view["confidence"] * 100).round(1)
    st.dataframe(view, use_container_width=True, height=310, hide_index=True)
    ids = [r["id"] for r in rows[::-1]]
    flow_id = st.selectbox("Chọn flow để xem giải thích", ids, format_func=lambda v: f"Flow {v}")
    detail = call("GET", f"/flows/{flow_id}")
    st.write(f"**M0:** {detail['prediction'] or 'Không dự đoán'} · "
             f"**Xác suất lớp thắng:** {(detail['confidence'] or 0):.1%}")
    if detail["error"]:
        st.warning(detail["error"])
    shap = detail["shap"]
    if shap:
        st.subheader("SHAP · đặc trưng ảnh hưởng tới lớp M0 dự đoán")
        data = pd.DataFrame(shap["top_k"])
        fig = alt.Chart(data).mark_bar().encode(
            x=alt.X("phi:Q", title="Đóng góp SHAP (raw margin)"),
            y=alt.Y("feature:N", sort="-x", title=None),
            color=alt.condition(alt.datum.phi >= 0, alt.value("#e0716d"), alt.value("#4d9bdb")),
            tooltip=["feature:N", "value:Q", "phi:Q"])
        st.altair_chart(fig, use_container_width=True)
        st.caption(f"SHAP ở raw margin, không phải % xác suất. Sai số cộng tính: {shap['additivity_error']:.2g}.")
    elif detail["prediction"] == "Benign":
        st.caption("SHAP tự động đang dành cho flow cảnh báo; có thể xem 78 giá trị đặc trưng bên dưới.")
    else:
        st.caption("SHAP đang tính hoặc chưa có kết quả.")
    st.subheader("LIME theo yêu cầu")
    if st.button("Tính LIME cho flow này", key=f"lime_{flow_id}", disabled=detail["prediction"] is None):
        try:
            with st.spinner("Đang tính LIME..."):
                call("POST", f"/flows/{flow_id}/lime")
            st.rerun()
        except Exception as exc:
            st.error(f"LIME lỗi: {exc}")
    lime = detail["lime"]
    if lime:
        if lime["status"] == "ok":
            weights = pd.DataFrame(lime["top_k"])
            fig = alt.Chart(weights).mark_bar(color="#d09256").encode(
                x=alt.X("weight:Q", title="Trọng số LIME"),
                y=alt.Y("feature_desc:N", sort="-x", title=None),
                tooltip=["feature_desc:N", "weight:Q"])
            st.altair_chart(fig, use_container_width=True)
            st.caption(f"LIME R² cục bộ: {lime['local_r2']:.3f}; trọng số không phải xác suất.")
        else:
            st.warning(f"LIME chưa cho giải thích tin cậy: {lime['status']} (ESS={lime['diagnostics'].get('effective_sample_size'):.2f}).")
    with st.expander("78 đặc trưng của flow"):
        st.dataframe(pd.DataFrame([{"Đặc trưng": k, "Giá trị": v} for k, v in detail["features"].items()]),
                     use_container_width=True, hide_index=True)
    st.caption("Nhãn và SHAP/LIME mô tả quyết định của model; không xác nhận traffic thật là tấn công.")


live_view()

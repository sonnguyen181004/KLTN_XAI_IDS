"""Standalone Java flow dashboard with separate M0 and M1 views."""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import altair as alt
import pandas as pd
import requests
import streamlit as st

TRIAL = Path(__file__).resolve().parent
sys.path.insert(0, str(TRIAL.parent / "RQ3_IDS_System" / "app"))
from feature_help import describe  # noqa: E402

API = "http://127.0.0.1:8765"
HEADERS = {"X-Trial-Token": os.environ.get("JAVA_M0_TRIAL_TOKEN", "")}


def call(method, path, model=None, timeout=30, **kwargs):
    params = kwargs.pop("params", {})
    if model:
        params["model"] = model
    response = requests.request(method, API + path, headers=HEADERS, params=params,
                                timeout=timeout, **kwargs)
    if not response.ok:
        raise RuntimeError(f"{response.status_code}: {response.text[:350]}")
    return response.json()


@st.cache_data(ttl=60)
def interfaces():
    return call("GET", "/interfaces")


def bars(data, name, value, signed=False, percent=False):
    if not data:
        st.info("Chưa có dữ liệu.")
        return
    frame = pd.DataFrame(data)
    chart = alt.Chart(frame).mark_bar().encode(
        y=alt.Y(name + ":N", sort="-x", title=None, axis=alt.Axis(labelLimit=320)),
        x=alt.X(value + ":Q", title=value, axis=alt.Axis(format=".0%") if percent else alt.Axis()),
        tooltip=list(frame.columns))
    if signed:
        chart = chart.encode(color=alt.condition(alt.datum[value] >= 0,
                            alt.value("#dc706e"), alt.value("#63a9dc")))
    st.altair_chart(chart.properties(height=max(150, 28 * len(frame))), width="stretch")


def show_detail(flow_id, model):
    flow = call("GET", f"/flows/{flow_id}", model)
    info_model = call("GET", "/model-info", model)
    st.subheader(f"Chi tiết flow {flow_id} · {model}")
    a, b, c = st.columns(3)
    a.metric("Dự đoán", flow["prediction"] or "Không hợp lệ")
    b.metric("Xác suất lớp thắng", f"{flow['confidence']:.2%}" if flow["confidence"] is not None else "—")
    c.metric("SHAP", "Đã có" if flow["shap"] else "Theo yêu cầu" if flow["prediction"] else "—")
    st.caption("Nhãn model không xác nhận tấn công. M0 và M1 có tập lớp, nền LIME và kết quả riêng.")
    left, right = st.columns(2)
    left.write(f"Nguồn: {flow['src_ip'] or '?'}:{flow['src_port'] or '?'}")
    left.write(f"Đích: {flow['dst_ip'] or '?'}:{flow['dst_port'] or '?'}")
    right.write(f"Giao thức: {flow['protocol'] or '?'}")
    right.write(f"Gói đầu của flow: {flow['time'] or '?'}")
    if flow["error"]:
        st.warning(flow["error"])
    if flow["branch"]:
        st.info(f"Nhánh {flow['branch']} · {flow['env_fingerprint_count']} đặc trưng nhạy môi trường trong Top-5 SHAP"
                + (" · lớp hiếm trong train" if flow["rare_class_flag"] else "")
                + ". Nhánh chỉ nhắc xem lại giải thích, không đổi dự đoán.")

    probability, shap_tab, lime_tab, feature_tab, raw_tab = st.tabs(
        ["Xác suất các lớp", "SHAP", "LIME theo yêu cầu", "Đối chứng đặc trưng", "78 đặc trưng"])
    with probability:
        bars([{"Lớp": k, "Xác suất": v} for k, v in flow["probabilities"].items()],
             "Lớp", "Xác suất", percent=True)
    with shap_tab:
        shap = flow["shap"]
        if shap is None and flow["prediction"]:
            if st.button("Tính SHAP cho flow này", key=f"shap_{model}_{flow_id}"):
                call("POST", f"/flows/{flow_id}/shap", model)
                st.rerun()
        if shap:
            bars(shap["top_k"], "feature", "phi", signed=True)
            st.caption("Đỏ tăng điểm lớp đang giải thích; xanh giảm điểm. SHAP ở raw margin, không phải phần trăm xác suất.")
            st.dataframe(pd.DataFrame(shap["top_k"]), hide_index=True, width="stretch")
            st.caption(f"Sai số cộng tính: {shap['additivity_error']:.2g}")
    with lime_tab:
        if flow["prediction"]:
            if st.button("Tính LIME cho flow này", key=f"lime_{model}_{flow_id}"):
                with st.spinner("Đang tính LIME..."):
                    call("POST", f"/flows/{flow_id}/lime", model, timeout=90)
                st.rerun()
            lime = flow["lime"]
            if lime:
                diag = lime.get("diagnostics", {})
                if lime["status"] == "ok":
                    bars(lime["top_k"], "feature_desc", "weight", signed=True)
                    st.dataframe(pd.DataFrame(lime["top_k"]), hide_index=True, width="stretch")
                    st.caption(f"R² cục bộ: {lime['local_r2']:.3f} · Cỡ mẫu hiệu dụng: {diag.get('effective_sample_size', 0):.1f}")
                else:
                    st.warning(f"LIME chưa cho giải thích hữu ích: {lime['status']} · cỡ mẫu hiệu dụng {diag.get('effective_sample_size', 0):.1f}.")
                st.caption("LIME xấp xỉ cục bộ trên xác suất; không so trực tiếp trọng số với SHAP raw margin.")
    with feature_tab:
        rows = []
        for name, value in flow["features"].items():
            info = describe(name)
            median = info_model["global_median"].get(name)
            note = info.get("note", "")
            if "Python" in note or "rq3-cfm" in note:
                note = "Cần đối chiếu cách Java tính cột này; ghi chú của Python không áp dụng."
            rows.append({"Đặc trưng": name, "Giá trị": value, "Trung vị train": median,
                         "Khác trung vị": value - median if median is not None and value is not None else None,
                         "Đơn vị": info["unit"],
                         "Ý nghĩa": info["meaning"], "Lưu ý": note})
        st.caption("Nền là trung vị train của đúng model đang xem. Khác nền không đồng nghĩa đặc trưng quan trọng.")
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", height=480)
    with raw_tab:
        st.json({"flow_id": flow_id, "model": model, "features": flow["features"]})


@st.fragment(run_every="3s")
def monitor(model):
    status = call("GET", "/status", model)
    rows = call("GET", "/flows", model)
    benign = sum(r["prediction"] == "Benign" for r in rows)
    alerts = sum(r["prediction"] not in (None, "Benign") for r in rows)
    st.caption(f"Lượt: {status['run_id'] or 'chưa có'} · Java: {status['phase']} · {status['n_classes']} lớp · làm mới 3 giây")
    a, b, c, d = st.columns(4)
    a.metric("Tổng flow", len(rows))
    b.metric("Benign", benign)
    c.metric("Cảnh báo", alerts)
    d.metric("SHAP có kết quả", sum(r["shap"] is not None for r in rows))
    st.caption("Tỷ lệ cảnh báo không phải FPR; cần nhãn thật để đo báo nhầm.")
    if status["error"]:
        st.error(status["error"])
    if status["packet_summary"]:
        st.caption("Java: " + status["packet_summary"])
    if not rows:
        st.info("Chưa có flow. Java xuất flow khi kết nối đóng hoặc khi bạn dừng và ghi nốt flow.")
        return
    labels = pd.Series([r["prediction"] or "Không hợp lệ" for r in rows]).value_counts()
    left, right = st.columns(2)
    with left:
        st.markdown("**Phân bố nhãn dự đoán**")
        bars([{"Nhãn": k, "Flow": int(v)} for k, v in labels.items()], "Nhãn", "Flow")
    with right:
        st.markdown("**Flow theo phút**")
        times = pd.to_datetime([r["time"] for r in rows], format="mixed", errors="coerce", dayfirst=True)
        timeline = pd.DataFrame({"Phút": times.strftime("%H:%M"),
                                 "Loại": ["Benign" if r["prediction"] == "Benign" else "Cảnh báo" for r in rows]})
        timeline = timeline.dropna().groupby(["Phút", "Loại"]).size().reset_index(name="Flow")
        if not timeline.empty:
            st.altair_chart(alt.Chart(timeline).mark_bar().encode(
                x=alt.X("Phút:O", title="Giờ flow"), y="Flow:Q", color="Loại:N",
                tooltip=["Phút", "Loại", "Flow"]).properties(height=210), width="stretch")
    st.subheader(f"Lịch sử flow · {model}")
    src = st.text_input("Lọc IP nguồn hoặc đích", key=f"ip_{model}").strip().lower()
    chosen = st.selectbox("Lọc nhãn", ["Tất cả"] + list(labels.index), key=f"label_{model}")
    window = st.selectbox("Khoảng thời gian gói đầu", ["Toàn bộ lượt", "5 phút", "15 phút", "1 giờ", "Hôm nay"],
                          key=f"window_{model}")
    alerts_only = st.checkbox("Chỉ cảnh báo", key=f"alerts_{model}")
    now = pd.Timestamp.now()
    minutes = {"5 phút": 5, "15 phút": 15, "1 giờ": 60}
    cutoff = now - pd.Timedelta(minutes=minutes[window]) if window in minutes else None
    def within_window(row):
        if window == "Toàn bộ lượt":
            return True
        timestamp = pd.to_datetime(row["time"], format="mixed", errors="coerce", dayfirst=True)
        if pd.isna(timestamp):
            return False
        if window == "Hôm nay":
            return timestamp.date() == now.date()
        return cutoff <= timestamp <= now
    filtered = [r for r in rows if (not src or src in (r["src_ip"] or "").lower() or src in (r["dst_ip"] or "").lower())
                and (chosen == "Tất cả" or r["prediction"] == chosen)
                and within_window(r)
                and (not alerts_only or r["prediction"] not in (None, "Benign"))]
    pages = max(1, (len(filtered) + 49) // 50)
    page = st.number_input("Trang (50 flow/trang)", 1, pages, 1, key=f"page_{model}")
    subset = filtered[::-1][(page - 1) * 50:page * 50]
    st.caption(f"{len(filtered)} flow khớp bộ lọc · trang {page}/{pages} · mới nhất trước")
    st.dataframe(pd.DataFrame([{"ID": r["id"], "Gói đầu": r["time"],
        "Nguồn": f"{r['src_ip'] or '?'}:{r['src_port'] or '?'}",
        "Đích": f"{r['dst_ip'] or '?'}:{r['dst_port'] or '?'}", "Nhãn": r["prediction"],
        "Xác suất": f"{r['confidence']:.1%}" if r["confidence"] is not None else "—",
        "SHAP": "Có" if r["shap"] else "Theo yêu cầu", "Nhánh": r["branch"] or "—"} for r in subset]),
        hide_index=True, width="stretch", height=350)
    if subset:
        selected = st.selectbox("Chọn flow để xem chi tiết", [r["id"] for r in subset],
                                format_func=lambda v: f"Flow {v}", key=f"flow_{model}_{page}")
        show_detail(selected, model)
    with st.expander("Nhóm cảnh báo · cửa sổ 5 phút"):
        groups = {}
        for row in filtered:
            if row["prediction"] in (None, "Benign"):
                continue
            when = pd.to_datetime(row["time"], format="mixed", errors="coerce", dayfirst=True)
            bucket = when.floor("5min").strftime("%d/%m/%Y %H:%M") if not pd.isna(when) else "Không rõ giờ"
            key = (bucket, row["src_ip"], row["dst_ip"], row["dst_port"], row["prediction"])
            groups.setdefault(key, []).append(row["id"])
        st.caption("Chỉ gom để xem; mỗi flow vẫn giữ nguyên dự đoán và giải thích riêng.")
        if groups:
            summary = [{"Cửa sổ": k[0], "Nguồn": k[1], "Đích": k[2], "Cổng đích": k[3],
                        "Nhãn": k[4], "Số flow": len(ids), "Flow ID": ", ".join(map(str, ids))}
                       for k, ids in list(groups.items())[-100:][::-1]]
            st.dataframe(pd.DataFrame(summary), hide_index=True, width="stretch", height=260)
        else:
            st.info("Chưa có cảnh báo để gom nhóm.")


@st.fragment(run_every="3s")
def capture_controls(model):
    state = call("GET", "/status", model)
    st.caption("Một phiên Java/Npcap cấp flow cho hai model. Chuyển M0 ↔ M1 không bắt lại traffic.")
    st.caption("Lab VMware 192.168.11.x: chọn VMnet1; duyệt web trên Windows: chọn Wi-Fi. Card được chọn phải nhìn thấy traffic của hai máy lab.")
    options = interfaces()
    if not options:
        st.error("Java/Npcap chưa thấy card mạng.")
        return
    choice = st.selectbox("Interface cần bắt", range(len(options)),
        format_func=lambda i: f"{options[i]['description']} [{options[i]['name']}]",
        index=next((i for i, x in enumerate(options) if "WiFi" in x["description"]), 0),
        disabled=state["phase"] in ("starting", "capturing", "stopping"))
    seconds = st.number_input("Thời gian (giây); 0 = đến khi bấm Dừng", 0, 3600, 0,
                              disabled=state["phase"] in ("starting", "capturing", "stopping"))
    a, b = st.columns(2)
    if a.button("Bắt đầu Java", type="primary", disabled=state["phase"] in ("starting", "capturing", "stopping")):
        call("POST", "/start", json={"interface": options[choice]["name"], "seconds": int(seconds)})
        st.rerun()
    if b.button("Dừng và ghi nốt flow", disabled=state["phase"] not in ("starting", "capturing")):
        call("POST", "/stop")
        st.rerun()
    st.write(f"Trạng thái: **{state['phase']}** · Flow: **{state['rows']}**")
    if state["phase"] == "starting":
        st.info("Java/Gradle đang khởi động; chưa xác nhận đã mở card mạng.")
    elif state["phase"] == "capturing":
        st.caption("Java đã mở card mạng. Có flow mới khi Java đóng flow hoặc khi bấm Dừng.")
    if state["error"]:
        st.error(state["error"])
    if state["packet_summary"]:
        st.caption(state["packet_summary"])
        if state["packet_summary"].startswith("accepted_packets=0 "):
            st.warning("Phiên đã kết thúc nhưng Java không nhận được gói TCP/UDP hợp lệ. Kiểm tra đúng card và tạo traffic trên mạng đó; chưa có dữ liệu để đánh giá model.")
    st.info("Flow còn mở chưa có dự đoán; khi dừng, Java ghi nốt flow rồi hai model xử lý.")


def import_files():
    st.caption("Nạp dữ liệu riêng trong khu thử Java. Lượt mới thay danh sách flow đang xem.")
    csv_tab, pcap_tab = st.tabs(["CSV 78 đặc trưng", "PCAP / PCAPNG qua Java"])
    with csv_tab:
        uploaded = st.file_uploader("Chọn CSV 78 đặc trưng", type="csv", key="java_csv")
        convert = st.checkbox("Đổi đơn vị thời gian giây → micro giây (chỉ CSV Python CICFlowMeter xuất giây)")
        if uploaded and st.button("Nạp CSV và dự đoán", key="import_csv"):
            data = uploaded.getvalue()
            if len(data) > 20_000_000:
                st.error("CSV vượt 20 MB.")
            else:
                result = call("POST", "/import/csv", json={"name": uploaded.name,
                              "content": data.decode("utf-8-sig"), "convert_seconds": convert}, timeout=300)
                st.success(f"Đã nạp {result['rows']} flow cho M0 và M1.")
    with pcap_tab:
        uploaded = st.file_uploader("Chọn PCAP/PCAPNG (tối đa 100 MB)",
                                    type=["pcap", "pcapng"], key="java_pcap")
        if uploaded and st.button("Java trích flow và dự đoán", key="import_pcap"):
            data = uploaded.getvalue()
            if len(data) > 100_000_000:
                st.error("PCAP vượt 100 MB.")
            else:
                folder = TRIAL / "output" / "imports"
                folder.mkdir(parents=True, exist_ok=True)
                filename = uuid.uuid4().hex[:12] + Path(uploaded.name).suffix.lower()
                (folder / filename).write_bytes(data)
                with st.spinner("Java đang trích flow..."):
                    result = call("POST", "/import/pcap", json={"filename": filename}, timeout=330)
                st.success(f"Java xuất {result['rows']} flow; M0 và M1 đã dự đoán riêng.")
    st.caption("CSV đã có đặc trưng không thể trích lại bằng Java. PCAPNG cần Wireshark editcap.")


st.set_page_config(page_title="IDS Java · M0 / M1", layout="wide")
st.title("IDS · Java CICFlowMeter và giải thích")
st.caption("Gói tin → Java gom flow → model dự đoán → SHAP cho cảnh báo → LIME theo yêu cầu.")
model = st.radio("Hệ thống đang xem", ["M0", "M1"], horizontal=True,
                 format_func=lambda x: "M0 · mô hình gốc (15 lớp)" if x == "M0" else "M1 · mô hình mới (13 lớp)")
try:
    monitor_tab, realtime_tab, upload_tab = st.tabs(["Giám sát flow", "Realtime", "Nạp CSV / PCAP"])
    with monitor_tab:
        monitor(model)
    with realtime_tab:
        capture_controls(model)
    with upload_tab:
        import_files()
except Exception as exc:
    st.error(f"Dịch vụ Java–{model} chưa sẵn sàng: {exc}")

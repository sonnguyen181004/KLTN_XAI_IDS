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
from ui_style import badge, card, paint, COLORS

API = os.environ.get("JAVA_TRIAL_API_URL", "http://127.0.0.1:8765")
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


def feature_meaning(name):
    info = describe(name).copy()
    if 'Python' in info['meaning']:
        info['meaning'] = 'Thống kê ' + info['title'].lower() + ' do Java CICFlowMeter xuất; cần đối chiếu quy ước Java khi so với dataset.'
    return info


def explain_features(items, features, label, method):
    st.markdown('**Đọc từng đặc trưng bằng lời**')
    st.caption('Fwd cùng chiều gói đầu của flow; Bwd là chiều ngược lại.')
    for item in items:
        name = item.get('feature', item.get('feature_desc'))
        weight = item.get('phi', item.get('weight'))
        info = feature_meaning(name)
        with st.expander(f"{name} — {info['title']}"):
            st.write(info['meaning'])
            st.write(f"Giá trị flow: {features.get(name)} {info['unit']}")
            if weight is not None:
                direction = 'tăng' if weight > 0 else 'giảm' if weight < 0 else 'không đổi'
                st.write(f"Đóng góp {method}: {weight:.4g}; {direction} điểm lớp {label} trong lời giải thích này.")
            st.caption('Không dùng riêng đặc trưng này làm quy tắc kết luận tấn công.')


def show_detail(flow_id, model):
    try:
        flow = call("GET", f"/flows/{flow_id}", model)
        info_model = call("GET", "/model-info", model)
    except (RuntimeError, requests.RequestException) as exc:
        st.error(f"Không tải được chi tiết flow {flow_id}: {exc}")
        return
    st.subheader("Chi tiết flow đang chọn")
    st.caption(f"Flow ID: {flow_id} · Model: {model}")
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
    if flow.get("invalid_features"):
        st.error("Flow có đặc trưng không hợp lệ nên không được dự đoán. Các ô này hiển thị trống; không thay bằng 0.")
        st.dataframe([{"Đặc trưng lỗi": k, "Giá trị gốc": v} for k, v in flow["invalid_features"].items()], hide_index=True)
    if flow["branch"]:
        st.info(f"Nhánh {flow['branch']} · {flow['env_fingerprint_count']} đặc trưng nhạy môi trường trong Top-5 SHAP"
                + (" · lớp hiếm trong train" if flow["rare_class_flag"] else "")
                + ". Nhánh chỉ nhắc xem lại giải thích, không đổi dự đoán.")

    probability, shap_tab, lime_tab, feature_tab, reliability_tab, raw_tab = st.tabs(
        ["Xác suất các lớp", "SHAP tự động", "LIME theo yêu cầu", "Đối chứng đặc trưng", "Đánh giá giải thích", "Đặc trưng và thời gian"])
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
            st.caption(f"Sai số cộng tính: {shap['additivity_error']}")
            explain_features(shap['top_k'], flow['features'], flow['prediction'], 'SHAP')
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
                    st.caption(f"R² cục bộ: {lime.get('local_r2')} · Cỡ mẫu hiệu dụng: {diag.get('effective_sample_size')}")
                    explain_features(lime['top_k'], flow['features'], flow['prediction'], 'LIME')
                else:
                    st.warning(f"LIME chưa cho giải thích hữu ích: {lime['status']} · cỡ mẫu hiệu dụng {diag.get('effective_sample_size')}.")
                    st.write('LIME tạo các mẫu biến đổi quanh flow rồi học mô hình đơn giản. Khi gần như chỉ một mẫu có trọng số, không đủ dữ liệu lân cận để giải thích; đây không phải xác nhận model đúng.')
                st.caption("LIME xấp xỉ cục bộ trên xác suất; không so trực tiếp trọng số với SHAP raw margin.")
    with feature_tab:
        rows = []
        for name, value in flow["features"].items():
            info = feature_meaning(name)
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
        feature = st.selectbox('Đặc trưng để đối chứng', list(flow['features']), key=f'feature_{model}_{flow_id}')
        st.write(feature_meaning(feature)['meaning'])
        value = flow['features'][feature]
        median = info_model['global_median'].get(feature)
        bars([{'Nguồn': k, 'Giá trị': v} for k, v in [('Flow', value), ('Trung vị train', median)] if v is not None], 'Nguồn', 'Giá trị')
    with reliability_tab:
        lime = flow.get("lime") or {}
        shap = flow.get("shap") or {}
        diagnostics = lime.get("diagnostics") or {}
        st.dataframe([{"Chỉ số": k, "Giá trị": str(v) if v is not None else "Chưa có"} for k, v in [
            ("Nhánh", flow.get("branch")), ("Số đặc trưng nhạy môi trường", flow.get("env_fingerprint_count")),
            ("Cờ lớp hiếm", flow.get("rare_class_flag")), ("Sai số cộng tính SHAP", shap.get("additivity_error")),
            ("Trạng thái LIME", lime.get("status")), ("R² cục bộ", lime.get("local_r2")),
            ("Cỡ mẫu hiệu dụng", diagnostics.get("effective_sample_size"))]], hide_index=True, width="stretch")
        st.caption("Các chỉ số đánh giá lời giải thích; không xác nhận nhãn đúng và không tạo điểm tin cậy tổng hợp.")
    with raw_tab:
        st.write("Gói đầu của flow: " + str(flow.get("time") or "Chưa có"))
        duration = flow["features"].get("Flow Duration")
        st.write(f"Thời lượng flow: {duration / 1e6:.6f} giây" if duration is not None else "Thời lượng không hợp lệ")
        st.json({"flow_id": flow_id, "model": model, "features": flow["features"]})


@st.fragment(run_every="3s")
def capture_controls(model):
    state = call("GET", "/status", model)
    st.caption("Mỗi lượt dùng extractor riêng theo model đã chọn. Đổi model cần nạp hoặc bắt một lượt mới.")
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
        call("POST", "/start", json={"model": model, "interface": options[choice]["name"], "seconds": int(seconds)})
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
    st.info("Flow còn mở chưa có dự đoán; khi dừng, Java ghi nốt flow rồi model đã chọn xử lý.")


def import_files(model):
    st.caption("Nạp dữ liệu riêng trong khu thử Java. Lượt mới thay danh sách flow đang xem.")
    csv_tab, pcap_tab = st.tabs(["CSV 78 đặc trưng", "PCAP / PCAPNG qua Java"])
    with csv_tab:
        uploaded = st.file_uploader("Chọn CSV 78 đặc trưng", type="csv", key="java_csv")
        st.caption("CSV dùng nguyên đặc trưng có sẵn; hệ thống chưa xác minh nguồn extractor. Chỉ nạp dữ liệu phù hợp model đã chọn, không tự sửa cờ PSH/FIN.")
        convert = st.checkbox("Đổi đơn vị thời gian giây → micro giây (chỉ CSV Python CICFlowMeter xuất giây)")
        if uploaded and st.button("Nạp CSV và dự đoán", key="import_csv"):
            data = uploaded.getvalue()
            if len(data) > 20_000_000:
                st.error("CSV vượt 20 MB.")
            else:
                result = call("POST", "/import/csv", json={"model": model, "name": uploaded.name,
                              "content": data.decode("utf-8-sig"), "convert_seconds": convert}, timeout=300)
                st.success(f"Đã nạp {result['rows']} flow cho {model}.")
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
                    result = call("POST", "/import/pcap", json={"model": model, "filename": filename}, timeout=330)
                st.success(f"Java xuất {result['rows']} flow cho {model}.")
    st.caption("CSV đã có đặc trưng không thể trích lại bằng Java. PCAPNG cần Wireshark editcap.")


st.set_page_config(page_title="IDS · Giám sát và giải thích", layout="wide")
st.markdown('<style>[data-stale="true"] {opacity: 1 !important; transition: none !important;}</style>', unsafe_allow_html=True)
st.markdown("## IDS · Giám sát traffic và giải thích")
st.caption("Java CICFlowMeter → flow hoàn tất → dự đoán → SHAP. LIME chạy khi yêu cầu.")
try:
    with st.sidebar:
        st.header("Phạm vi giám sát")
        model = st.radio("Hệ thống đang xem", ["M0", "M1"], horizontal=True)
        info = call("GET", "/model-info", model)
        st.selectbox("Lượt dữ liệu", ["Lượt hiện tại"])
        st.caption("Khu Java hiện lưu lượt đang chạy trong RAM; chưa có lịch sử DB.")
        window = st.selectbox("Khoảng thời gian gói đầu", ["Toàn bộ lượt", "5 phút", "15 phút", "1 giờ", "Hôm nay"])
        src = st.text_input("IP nguồn (để trống = tất cả)").strip()
        dst = st.text_input("IP đích (để trống = tất cả)").strip()
        label = st.selectbox("Nhãn dự đoán", ["Tất cả", "Không hợp lệ"] + info["classes"], key="label_"+model)
        alerts = st.checkbox("Chỉ cảnh báo")
        paused = st.checkbox("Tạm dừng tự làm mới")
        st.button("Làm mới ngay")
        st.caption(f"Model: {model} · {len(info['classes'])} lớp")
    state = call("GET", "/status", model)
    st.caption(f"Nguồn đặc trưng: {state.get('extractor_profile', 'chưa có')} · Model của lượt: {state.get('active_model') or 'chưa chọn'}")
    if state.get("active_model") and state["active_model"] != model:
        st.warning("Lượt hiện tại thuộc model khác. Chọn lại model hoặc nạp/bắt lượt mới; không dùng lẫn quy ước đặc trưng.")
    if model == "M0":
        st.warning("M0: chưa xác minh đầy đủ extractor với phiên bản tạo dataset gốc. Nhãn dự đoán cần được kiểm chứng bằng nhật ký lab.")
    else:
        st.caption("M1: PCAP/realtime dùng Java cải tiến ghim phiên bản 2022. Chưa chứng minh trùng tuyệt đối pipeline tạo dataset.")
    scope = dict(label=label, src_ip=src, dst_ip=dst, alerts=alerts, window=window)
    from monitor_ui import render_monitor
    monitor_tab, realtime_tab, upload_tab = st.tabs(["Giám sát flow", "Realtime", "Nạp CSV / PCAP"])
    with monitor_tab:
        st.fragment(run_every=None if paused else "5s")(render_monitor)(model, scope, call, show_detail)
    with realtime_tab:
        capture_controls(model)
    with upload_tab:
        import_files(model)
except (RuntimeError, requests.RequestException) as exc:
    st.error(f"Dịch vụ Java chưa sẵn sàng: {exc}")

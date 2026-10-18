"""Live IDS dashboard. Read data through API; explanations remain architecture-driven."""
import hashlib
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import altair as alt
import pandas as pd
import requests
import streamlit as st
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
from ingestion_ui import render_ingestion
from xai_reading_ui import explain_top_features, lime_problem, feature_guide

cfg = yaml.safe_load((ROOT / 'config.yaml').read_text(encoding='utf-8'))
API = os.environ.get('IDS_API_URL', f"http://{cfg['api']['host']}:{cfg['api']['port']}")
LOCAL = timezone(timedelta(hours=7))
STATUS = {'not_required': 'Không cần (Benign)', 'queued': 'Chờ SHAP',
          'pending_dispatch': 'Đã lưu dự đoán; chưa đưa vào SHAP',
          'recovery_pending': 'Chờ khôi phục SHAP sau restart',
          'processed': 'Đã có SHAP', 'failed': 'SHAP lỗi',
          'dropped_queue_full': 'Bỏ SHAP: hàng đợi đầy', 'unknown_legacy': 'Chưa rõ (dữ liệu cũ)'}


def local_time(value):
    if not value:
        return 'Chưa có'
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        return dt.strftime('%d/%m/%Y %H:%M:%S') + ' (chưa rõ múi giờ)'
    return dt.astimezone(LOCAL).strftime('%d/%m/%Y %H:%M:%S')


def get(path, params=None):
    response = requests.get(API + path, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def bars(data, name, value, signed=False):
    if not data:
        st.info('Chưa có dữ liệu.'); return
    frame = pd.DataFrame(data)
    chart = alt.Chart(frame).mark_bar().encode(
        y=alt.Y(name + ':N', sort='-x', title=None),
        x=alt.X(value + ':Q', title=value),
        tooltip=list(frame.columns))
    if signed:
        chart = chart.encode(color=alt.condition(alt.datum[value] >= 0,
                            alt.value('#ef7070'), alt.value('#69b9ee')))
    st.altair_chart(chart.properties(height=max(180, len(frame) * 26)), width='stretch')


def show_detail(flow_id):
    flow = get('/flows/' + flow_id)
    reference = get('/flows/' + flow_id + '/comparison')
    st.subheader('Chi tiết flow đang chọn')
    st.caption('Flow ID: ' + flow_id)
    cols = st.columns(3)
    cols[0].metric('Dự đoán', flow['predicted_label'])
    cols[1].metric('Xác suất lớp thắng', f"{flow['confidence']:.2%}" if flow['confidence'] is not None else 'Chưa có')
    cols[2].metric('Giải thích', STATUS.get(flow['explanation_status'], flow['explanation_status']))
    st.caption('Xác suất do model trả về, không phải bằng chứng tấn công đã xác nhận. Giờ hiển thị GMT+7.')
    left, right = st.columns(2)
    with left:
        st.write(f"Nguồn: {flow['src_ip'] or 'Không được cung cấp'} : {flow['src_port'] if flow['src_port'] is not None else '?'}")
        st.write(f"Đích: {flow['dst_ip'] or 'Không được cung cấp'} : {flow['dst_port'] if flow['dst_port'] is not None else '?'}")
        st.write(f"Protocol: {flow['protocol']} · Nguồn dữ liệu: {flow['source']}")
        st.write('Lượt: ' + (flow['run_name'] or 'Lịch sử chưa gắn lượt'))
        st.caption('Bộ trích xuất: ' + (flow.get('extractor_version') or 'Nguồn chưa cung cấp phiên bản'))
        if (flow.get('extractor_version') or '').startswith('rq3-train-conventions-experimental'):
            st.warning('Flow dùng bộ trích xuất thử nghiệm một phần quy ước train; chưa được xác nhận tương thích đầy đủ.')
    with right:
        st.write('Gói đầu tiên của flow: ' + local_time(flow['flow_timestamp_utc'] or flow['flow_timestamp']))
        st.write('API nhận: ' + local_time(flow['received_at']))
        st.write('Dự đoán: ' + local_time(flow['predicted_at']))
        duration = (flow.get('features') or {}).get('Flow Duration')
        st.write('Thời lượng flow: ' + (f'{duration / 1e6:.6f} giây' if duration is not None else 'Chưa có'))
    if not flow['is_alert']:
        st.info('Benign: vẫn lưu dự đoán, không tạo cảnh báo và không chạy SHAP/LIME theo thiết kế.')
    elif flow['branch']:
        st.info(f"Nhánh {flow['branch']}: {flow['branch_reason']}. Nhánh A/B không đổi nhãn dự đoán.")
    prediction, shap_tab, lime_tab, comparison, reliability, raw = st.tabs(
        ['Xác suất các lớp', 'SHAP tự động', 'LIME theo yêu cầu', 'Đối chứng đặc trưng', 'Đánh giá giải thích', 'Đặc trưng và thời gian'])
    with prediction:
        bars([{'Lớp': k, 'Xác suất': v} for k, v in flow['probabilities'].items()], 'Lớp', 'Xác suất')
        st.caption(f"Model: {flow['model_version']} · Nhãn thật: {flow['label_true'] or 'Không biết (traffic thật không có nhãn xác nhận)'}")
    with shap_tab:
        if flow.get('shap_top5'):
            bars(flow['shap_top5'], 'feature', 'phi', signed=True)
            st.caption('Đỏ/dương: tăng điểm lớp đang giải thích; xanh/âm: giảm điểm. SHAP ở raw margin, không phải phần trăm xác suất.')
            explain_top_features(flow, 'SHAP')
            with st.expander('Số liệu SHAP gốc'):
                st.dataframe(flow['shap_top5'], hide_index=True, width='stretch')
        else:
            st.info(STATUS.get(flow['explanation_status'], 'Chưa có SHAP'))
    with lime_tab:
        lime_status = flow.get('lime_status', 'not_requested')
        if not flow['is_alert']:
            st.info('Không yêu cầu LIME cho flow Benign.')
        elif lime_status in ('insufficient_neighborhood', 'zero_coefficients', 'undefined_fit'):
            lime_problem(flow, reference)
        elif flow.get('lime_top5'):
            bars(flow['lime_top5'], 'feature_desc', 'weight', signed=True)
            st.caption('Đỏ/dương và xanh/âm là dấu hệ số trong mô hình LIME xấp xỉ, không phải phần trăm gây ra dự đoán.')
            explain_top_features(flow, 'LIME')
            with st.expander('Số liệu LIME gốc'):
                st.dataframe(flow['lime_top5'], hide_index=True, width='stretch')
            if lime_status == 'legacy_unchecked':
                st.info('Kết quả cũ chưa có kiểm tra lân cận. Bấm kiểm tra lại để bổ sung chẩn đoán.')
            st.caption(f"Local R²: {flow.get('lime_local_r2') if flow.get('lime_local_r2') is not None else 'Chưa có'} · Jaccard@5: {flow.get('agreement_jaccard5') if flow.get('agreement_jaccard5') is not None else 'Chưa có'}")
            st.caption('LIME là mô hình thay thế cục bộ trên xác suất; không so độ lớn trực tiếp với SHAP raw margin.')
            st.caption('R² đo độ khớp trên các mẫu LIME, không phải độ chính xác IDS. Jaccard@5 đo mức trùng các tên/mô tả Top-5 được so sánh, không xác nhận nhãn đúng.')
        if flow['is_alert'] and st.button('Yêu cầu / kiểm tra lại LIME', key='lime_' + flow_id):
            with st.spinner('Đang tính LIME theo yêu cầu…'):
                response = requests.post(API + '/explain', json={'alert_id': flow['alert_id'], 'method': 'lime'}, timeout=60)
                response.raise_for_status()
            st.rerun()
    with comparison:
        feature_guide(flow, reference)
    with reliability:
        st.dataframe([{'Chỉ số': name, 'Giá trị': str(flow.get(key)) if flow.get(key) is not None else 'Chưa có'}
            for name, key in [('Nhánh', 'branch'), ('Số đặc trưng môi trường trong Top-5', 'env_fingerprint_count'),
              ('Cờ môi trường', 'env_fingerprint_flag'), ('Cờ lớp hiếm', 'rare_class_flag'),
              ('Faithfulness proxy drop', 'faithfulness_proxy_drop'), ('Jaccard@5', 'agreement_jaccard5'),
              ('Stability tham chiếu RQ2', 'stability_lookup')]], hide_index=True, width='stretch')
        st.caption('Proxy không phải phép đo faithfulness đầy đủ RQ2. Cờ môi trường/lớp hiếm chỉ yêu cầu xem xét, không chứng minh model sai. Không tạo điểm tin cậy tổng hợp.')
        if flow.get('robustness_lookup'):
            st.json(flow['robustness_lookup'])
    with raw:
        timings = flow.get('timing') or []
        if timings:
            latest = {row['step']: row for row in timings}
            bars(list(latest.values()), 'step', 'duration_ms')
            st.caption('Đơn vị ms. Total là thời gian request /predict, có chứa các bước con; không cộng tất cả thanh. SHAP/LIME chạy riêng.')
            st.dataframe([{**row, 'recorded_at': local_time(row['recorded_at'])} for row in timings], hide_index=True)
        with st.expander('78 đặc trưng đầu vào và metadata gốc'):
            st.json(flow)


st.set_page_config(page_title='IDS · Giám sát và giải thích', layout='wide')
st.title('IDS · Giám sát traffic và giải thích')
st.caption('Flow hoàn tất → dự đoán → cảnh báo → SHAP nền. LIME chỉ chạy khi bạn yêu cầu.')
try:
    health = get('/health')
    available_runs = get('/runs')['runs']
except requests.RequestException as exc:
    st.error(f'Không kết nối được API mới tại {API}. Khởi động lại API sau khi cập nhật. {exc}')
    st.stop()

run_names = {r['capture_run_id']: f"{r['run_name'] or 'Dữ liệu cũ'} · {local_time(r['started_at'])} · {r['capture_run_id'][:8]}" for r in available_runs}
options = ['__latest__', '__all__'] + list(run_names)
pending = st.session_state.pop('pending_run_choice', None)
if pending in options:
    st.session_state['run_choice'] = pending
if st.session_state.get('run_choice') not in options:
    st.session_state['run_choice'] = '__latest__'
with st.sidebar:
    st.header('Phạm vi giám sát')
    choice = st.selectbox('Lượt dữ liệu', options, key='run_choice',
        format_func=lambda x: {'__latest__': 'Lượt nhận dữ liệu gần nhất', '__all__': 'Tất cả lịch sử'}.get(x, run_names.get(x, x)))
    source = st.selectbox('Nguồn', ['Tất cả', 'feeder_live', 'csv_upload', 'pcap_replay', 'api'])
    window = st.selectbox('Khoảng thời gian nhận', ['Toàn bộ lượt', '5 phút', '15 phút', '1 giờ', 'Hôm nay'])
    label = st.selectbox('Nhãn dự đoán', ['Tất cả'] + health.get('class_names', []))
    branch = st.selectbox('Nhánh giải thích', ['Tất cả', 'A', 'B'])
    alerts_only = st.checkbox('Chỉ cảnh báo')
    paused = st.checkbox('Tạm dừng tự làm mới')
    st.button('Làm mới ngay')
    page = st.number_input('Trang (50 flow/trang)', min_value=1, value=1, step=1)
    st.caption(f"Model: {'Đã nạp' if health['model_loaded'] else 'LỖI'} · {health['n_classes']} lớp")
    st.caption('Phiên bản: ' + health['model_version'])

live, capture_help, upload = st.tabs(['Giám sát flow', 'Hướng dẫn live', 'Nạp CSV / PCAP'])


@st.fragment(run_every=None if paused else '5s')
def monitor():
    try:
        current_runs = get('/runs')['runs']
        selected_run = current_runs[0]['capture_run_id'] if choice == '__latest__' and current_runs else choice
        params = {}
        if selected_run not in ('__all__', '__latest__'):
            params['capture_run_id'] = selected_run
        for key, value in [('source', source), ('label', label), ('branch', branch)]:
            if value != 'Tất cả':
                params[key] = value
        params['alerts_only'] = alerts_only
        # Stable identity excludes the rolling cutoff: polling must not reset selected flow.
        signature = str((params, window))
        if st.session_state.get('scope_signature') != signature:
            st.session_state['selected_flow'] = None
            st.session_state['scope_signature'] = signature
        now = datetime.now(timezone.utc)
        if window != 'Toàn bộ lượt':
            since = now.astimezone(LOCAL).replace(hour=0, minute=0, second=0, microsecond=0) if window == 'Hôm nay' else now - timedelta(minutes={'5 phút': 5, '15 phút': 15, '1 giờ': 60}[window])
            params['since'] = since.astimezone(timezone.utc).isoformat()
        stats = get('/dashboard/summary', params)
        queue = get('/explain_queue_status')
        st.caption(f"Cập nhật: {local_time(now.isoformat())} · Lượt: {selected_run} · SHAP toàn hệ thống: {queue['qsize']}/{queue['maxsize']}")
        if queue.get('recovery_pending'):
            st.caption(f"Đang chờ khôi phục SHAP từ DB: {queue['recovery_pending']} cảnh báo; xử lý dần khi hàng đợi hiện tại rảnh.")
        cols = st.columns(6)
        for col, title, val in zip(cols, ['Tổng flow', 'Benign', 'Cảnh báo', 'Chờ SHAP', 'SHAP xong', 'SHAP bỏ / lỗi'],
                                  [stats['flows'], stats['benign'], stats['alerts'], stats['queued'], stats['processed'], f"{stats['dropped']} / {stats['failed']}"]):
            col.metric(title, val)
        st.caption('Chỉ số và biểu đồ tính trên TOÀN BỘ bộ lọc, không chỉ 50 dòng của trang.')
        st.write('Flow cuối được nhận trong phạm vi: ' + local_time(stats['last_received_at']))
        if not stats['last_received_at'] or (now - datetime.fromisoformat(stats['last_received_at'])).total_seconds() > 30:
            st.info('Chưa nhận flow mới gần đây. Có packet chưa đồng nghĩa đã xuất flow: project v3 xuất khi tuổi flow đạt 90 giây, quan sát đóng TCP/mở phiên mới hoặc dừng để ghi nốt. API không biết chắc bộ bắt còn chạy hay đã dừng; bản v2/nguồn khác có thể dùng chính sách khác.')
        if not stats['flows']:
            st.info('Không có flow khớp bộ lọc. Thử chọn Tất cả lịch sử hoặc bỏ bớt bộ lọc.')
            return
        left, right = st.columns(2)
        with left:
            st.subheader('Flow được nhận theo phút')
            timeline = pd.DataFrame(stats['timeline'])
            timeline['Giờ GMT+7'] = timeline['minute'].map(local_time)
            st.altair_chart(alt.Chart(timeline).mark_bar().encode(
                x=alt.X('Giờ GMT+7:O', sort=list(dict.fromkeys(timeline['Giờ GMT+7'])), title=None),
                y=alt.Y('count:Q', title='Số flow'), color=alt.Color('category:N', title='Kết quả'),
                tooltip=['Giờ GMT+7', 'category', 'count']).properties(height=220), width='stretch')
        with right:
            st.subheader('Phân bố nhãn dự đoán')
            bars(stats['labels'], 'label', 'count')
        result = get('/flows', {**params, 'limit': 50, 'offset': (page - 1) * 50})
        records = result['flows']
        st.subheader('Flow mới nhất trước')
        st.caption(f"Trang {page} / {max(1, (result['count'] + 49) // 50)} · Chọn một dòng để xem chi tiết. Flow đang xem được giữ khi làm mới.")
        if records:
            key = 'flows_' + hashlib.sha256((signature + str(page)).encode()).hexdigest()[:12]
            ids = [f['flow_id'] for f in records]
            def on_select():
                indices = st.session_state[key]['selection']['rows']
                if indices:
                    st.session_state['selected_flow'] = ids[indices[0]]
            table = [{'API nhận (GMT+7)': local_time(f['received_at']),
                      'Nguồn IP': f['src_ip'] or 'Chưa có', 'Đích IP': f['dst_ip'] or 'Chưa có',
                      'Nhãn': f['predicted_label'], 'Xác suất': f"{f['confidence']:.2%}" if f['confidence'] is not None else 'Chưa có',
                      'SHAP': STATUS.get(f['explanation_status'], f['explanation_status']),
                      'Nhánh': f['branch'] or '—', 'Flow ID': f['flow_id'][:8]} for f in records]
            st.dataframe(table, hide_index=True, width='stretch', key=key,
                         selection_mode='single-row', on_select=on_select)
            if not st.session_state.get('selected_flow'):
                st.session_state['selected_flow'] = ids[0]
        else:
            st.info('Trang này chưa có dữ liệu; chọn trang 1.')
        with st.expander('Nhóm cảnh báo · cửa sổ 5 phút (tối đa 100 nhóm mới nhất)'):
            groups = stats['groups']
            st.caption('Chỉ gom hiển thị theo lượt/cặp IP/cổng đích/lớp; không xóa hoặc gộp mất flow.')
            if groups:
                group = st.selectbox('Nhóm', groups, format_func=lambda g: f"{g['label']} · {g['src_ip'] or '?'} → {g['dst_ip'] or '?'} · {g['count']} flow · {local_time(g['last_seen'])}")
                group_page = st.number_input('Trang trong nhóm (50 flow/trang)', min_value=1,
                    max_value=max(1, (group['count'] + 49) // 50), value=1,
                    key='group_page_' + hashlib.sha256(str((group['group_key'], group['window'])).encode()).hexdigest()[:12])
                members = get('/flows', {**params, 'group_key': group['group_key'],
                    'since': group['first_seen'], 'until': group['last_seen'], 'limit': 50,
                    'offset': (group_page - 1) * 50})['flows']
                child = st.selectbox('Flow trong nhóm', members,
                    format_func=lambda f: f"{local_time(f['received_at'])} · {f['flow_id']}")
                if child and st.button('Mở flow trong nhóm'):
                    st.session_state['selected_flow'] = child['flow_id']
        if st.session_state.get('selected_flow'):
            show_detail(st.session_state['selected_flow'])
    except (requests.RequestException, ValueError) as exc:
        st.error(f'Không tải được dữ liệu: {exc}')


with live:
    monitor()
with capture_help:
    st.subheader('Bắt traffic trên máy → gom flow → dự đoán')
    st.info('Tab này hướng dẫn chạy capture/feeder trong terminal, chưa có nút bật hoặc tắt bộ bắt. API nhận flow không đủ để xác nhận capture còn đang chạy.')
    st.write('1. Trong VS Code, mở hai terminal tại thư mục RQ3_IDS_System. API và Dashboard giữ chạy; không bật thêm API thứ hai cùng DB.')
    st.write('2. Chọn đúng interface và tên CSV mới cho mỗi phiên. Thay live_review_01.csv nếu tên này đã dùng.')
    st.code('.\\.venv_capture\\Scripts\\python.exe scripts\\run_live_capture.py --interface "Wi-Fi" --output data\\live_review_01.csv', language='powershell')
    st.write('3. Ở terminal còn lại, chạy feeder theo dõi đúng CSV:')
    st.code('python app\\feeder.py --watch data\\live_review_01.csv --convert-units --capture-timezone +07:00', language='powershell')
    st.write('4. Mở tab Giám sát flow, chọn Nguồn = feeder_live và chọn đúng lượt live_review_01.csv. Dữ liệu CSV/PCAP đã nạp vẫn giữ trong lịch sử.')
    st.caption('Chỉ bắt trên máy/mạng bạn được phép kiểm thử. +07:00 phải khớp múi giờ timestamp capture. Có traffic nền ngay cả khi chưa mở trình duyệt.')
    st.warning('Project v3 xuất flow khi tuổi tính từ packet đầu đạt 90 giây, quan sát đóng TCP/mở phiên mới hoặc flush lúc dừng; không dự đoán từng packet. Packet lệch thời gian được tách riêng, có lý do trong CSV. Ctrl+C capture để ghi nốt, đợi feeder gửi hết rồi mới dừng feeder. Đây không phải chứng nhận đầu vào khớp train.')
    st.write('Feeder bị ngắt: chạy lại cùng lệnh và giữ checkpoint để tiếp tục. Không ghi đè CSV. Queue 200 chỉ giới hạn SHAP đang chờ, không giới hạn số flow được dự đoán/lưu.')
with upload:
    st.caption('CSV có đặc trưng sẵn hoặc PCAP qua extractor đều gửi về cùng /predict. Sau khi nạp, mở Giám sát flow để xem lượt tương ứng; không cần xóa lịch sử.')
    render_ingestion(API, ROOT)

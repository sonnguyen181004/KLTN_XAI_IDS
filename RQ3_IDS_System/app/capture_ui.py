"""Streamlit is a control client only: no subprocesses or worker state ownership."""
import os
import uuid
import requests
import streamlit as st
from ipaddress import ip_address

LABELS = {'starting': 'Đang khởi động', 'running': 'Đang bắt', 'stopping': 'Đang dừng và ghi nốt',
          'draining': 'Đang gửi nốt flow', 'completed': 'Đã hoàn tất', 'failed': 'Thất bại / chưa đầy đủ',
          'unknown': 'Cần đối soát tiến trình'}


def local_browser():
    # Streamlit 1.65 deliberately maps loopback client IPs to None. Client
    # context is not an authentication boundary: require an explicit local
    # listener, keep API token checks, and never deploy control behind a proxy.
    try:
        if not ip_address(st.get_option('server.address')).is_loopback:
            return False
    except (ValueError, TypeError):
        return False
    browser_ip = st.context.ip_address
    if browser_ip is None:
        return True
    try:
        return ip_address(browser_ip).is_loopback
    except ValueError:
        return False


@st.fragment(run_every='3s')
def render_capture(api):
    st.subheader('Điều khiển bắt traffic realtime')
    token = os.environ.get('IDS_CAPTURE_CONTROL_TOKEN', '')
    if len(token) < 32:
        st.info('Chưa bật điều khiển: đặt cùng IDS_CAPTURE_CONTROL_TOKEN (ít nhất 32 ký tự) cho API và UI rồi khởi động lại. Hướng dẫn terminal bên dưới vẫn dùng được.')
        return
    if not local_browser():
        st.error('Điều khiển capture yêu cầu UI bind loopback: chạy Streamlit với --server.address 127.0.0.1 và mở http://127.0.0.1:8501 trên máy này. Không triển khai qua LAN/proxy/tunnel.')
        return
    headers = {'X-IDS-Control-Token': token}
    try:
        response = requests.get(api+'/capture/status', headers=headers, timeout=5)
        response.raise_for_status()
        report = response.json()
    except (requests.RequestException, ValueError) as exc:
        st.error(f'Không đọc được trạng thái capture. Không suy ra đã dừng: {exc}')
        return
    state = report.get('session') or {}
    active = state.get('active', False)
    status = state.get('status', 'idle')
    st.write('Trạng thái: ' + LABELS.get(status, 'Chưa có phiên được quản lý'))
    interface = st.text_input('Interface bắt mạng', value='Wi-Fi', disabled=active, key='capture_interface')
    st.caption('Chỉ bắt trên máy/mạng được phép. Không tự dừng sau 60 giây; chạy tới khi bấm Dừng hoặc gặp lỗi/giới hạn tài nguyên. Không chạy thêm capture terminal trên cùng interface.')
    start_col, stop_col, reconcile_col = st.columns(3)

    def send(path, body):
        try:
            response = requests.post(api+'/capture/'+path, json=body, headers=headers, timeout=8)
            response.raise_for_status()
            return True
        except requests.RequestException as exc:
            st.error(f'Lệnh chưa được xác nhận: {exc}. Đọc lại trạng thái; không mặc định thành công.')
            return False

    if start_col.button('Bắt đầu capture', disabled=active or not interface.strip()):
        pending = st.session_state.get('capture_start_request')
        if not pending or pending['interface'] != interface:
            pending = dict(request_id=uuid.uuid4().hex, interface=interface)
            st.session_state['capture_start_request'] = pending
        if send('start', pending):
            st.session_state.pop('capture_start_request', None)
            st.rerun()
    if stop_col.button('Dừng capture', disabled=not active or status not in ('starting', 'running', 'stopping', 'draining')):
        if send('stop', {'run_id': state['run_id']}):
            st.info('Đã gửi yêu cầu dừng. Đợi trạng thái Hoàn tất; API sẽ ghi nốt CSV và gửi hết flow.')
    if reconcile_col.button('Đối soát sau restart', disabled=not active or status != 'unknown'):
        if send('reconcile', {'run_id': state['run_id']}):
            st.rerun()
    if not state:
        return
    st.caption('Mã phiên điều khiển: '+state['run_id'])
    capture = state.get('telemetry', {}).get('capture', {})
    st.caption(f"Packet đã nhận: {capture.get('accepted_packets') if capture.get('accepted_packets') is not None else 'Chưa có số liệu'} · Flow đã xuất: {capture.get('exported_flows') if capture.get('exported_flows') is not None else 'Chưa có số liệu'}")
    left, right = st.columns(2)
    left.metric('Flow đã được API xác nhận', state.get('acknowledged_rows') if state.get('acknowledged_rows') is not None else 'Chưa có')
    final = state.get('capture_result') or {}
    right.metric('Flow xuất cuối phiên', final.get('rows') if final.get('rows') is not None else 'Chưa chốt')
    if state.get('prediction_run_id'):
        st.caption('Mã lượt dự đoán: '+state['prediction_run_id'])
        if st.button('Xem flow của phiên này'):
            st.session_state['pending_run_choice'] = state['prediction_run_id']
            st.rerun()
    if state.get('workers'):
        st.dataframe([{'Worker': role, 'Sẵn sàng': worker.get('ready'),
                       'Heartbeat (UTC)': worker.get('heartbeat_at'), 'Mã thoát': worker.get('exit_code')}
                      for role, worker in state['workers'].items()], hide_index=True)
    if state.get('reason') or report.get('supervisor_error'):
        st.warning(state.get('reason') or report['supervisor_error'])
    for role, telemetry in state.get('telemetry', {}).items():
        if telemetry.get('error_message'):
            st.error(f"{role}: {telemetry['error_message']}")
    if status == 'unknown':
        st.warning('Chưa đủ bằng chứng worker đã dừng. Không khởi chạy phiên khác, không xóa journal hoặc kill PID tùy ý.')
    st.caption('Chưa có flow không đồng nghĩa không có packet: flow thường xuất khi đóng TCP, tới timeout hoặc khi Dừng. ACK không phải số packet; số nhãn cảnh báo không phải FPR. Biểu đồ và SHAP/LIME nằm trong Giám sát flow.')

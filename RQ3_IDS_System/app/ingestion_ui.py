"""Upload workflows; every prediction is submitted through HTTP, never the DB."""
import csv
import io
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st
from feeder import row_to_payload
from flow_metadata import row_metadata


def send_csv(text, api_url, name, source, convert, zone):
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    if not reader.fieldnames or not rows:
        st.warning('File chưa có dòng dữ liệu.'); return
    run_id = str(uuid.uuid4())
    errors, success = [], 0
    progress = st.progress(0.0)
    for i, row in enumerate(rows):
        try:
            if None in row or any(v is None for v in row.values()):
                raise ValueError('Số cột không khớp header')
            payload = row_to_payload(row, reader.fieldnames, convert)
            params = {'source': source, **row_metadata(row, run_id, name, zone)}
            response = requests.post(api_url + '/predict', params=params, json=payload, timeout=15)
            response.raise_for_status()
            success += 1
        except (ValueError, requests.RequestException) as exc:
            errors.append(f'Dòng {i + 2}: {exc}')
        progress.progress((i + 1) / len(rows))
    st.session_state['upload_result'] = (success, errors)
    if success:
        st.session_state['pending_run_choice'] = run_id
    st.rerun()


def render_ingestion(api_url, root):
    st.subheader('Nạp CSV / phát lại PCAP')
    st.caption('Mỗi lần gửi là một lượt riêng; mọi flow đều qua /predict. Không tự gửi lại khi làm mới.')
    if 'upload_result' in st.session_state:
        success, errors = st.session_state['upload_result']
        st.info(f'Lượt gửi vừa rồi: {success} flow thành công, {len(errors)} dòng lỗi.')
        if errors:
            with st.expander('Chi tiết lỗi gửi'):
                st.text('\n'.join(errors))
    csv_tab, pcap_tab = st.tabs(['CSV đặc trưng', 'PCAP đã ghi'])
    with csv_tab:
        uploaded = st.file_uploader('Chọn CSV', type=['csv'], key='csv_uploader')
        convert = st.checkbox('Đổi giây → micro giây (CSV CICFlowMeter thật)', key='csv_convert_units')
        zone = st.selectbox('Múi giờ timestamp trong CSV', ['Không rõ', '+07:00', '+00:00'])
        if uploaded is not None and st.button('Gửi CSV vào /predict', key='send_csv'):
            try:
                send_csv(uploaded.getvalue().decode('utf-8-sig'), api_url, uploaded.name,
                         'csv_upload', convert, None if zone == 'Không rõ' else zone)
            except UnicodeError:
                st.error('CSV cần mã hóa UTF-8.')
    with pcap_tab:
        uploaded = st.file_uploader('Chọn PCAP', type=['pcap', 'pcapng'], key='pcap_uploader')
        capture_python = root / '.venv_capture/Scripts/python.exe'
        st.caption('CICFlowMeter trích đặc trưng rồi gửi dự đoán. Giới hạn trích xuất: 120 giây.')
        if not capture_python.exists():
            st.warning('Chưa có .venv_capture; chức năng PCAP chưa sẵn sàng.')
        if uploaded is not None and st.button('Trích xuất và gửi', key='send_pcap', disabled=not capture_python.exists()):
            try:
                with tempfile.TemporaryDirectory(prefix='ids_pcap_') as folder:
                    input_path = Path(folder) / ('input' + Path(uploaded.name).suffix)
                    output_path = Path(folder) / 'flows.csv'
                    input_path.write_bytes(uploaded.getvalue())
                    with st.spinner('Đang trích xuất flow…'):
                        proc = subprocess.run([str(capture_python), str(root / 'scripts/run_live_capture.py'),
                            '--pcap-input', str(input_path), '--output', str(output_path)],
                            cwd=root, capture_output=True, text=True, encoding='utf-8', errors='replace',
                            timeout=120, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                    if proc.returncode or not output_path.exists():
                        st.error('Không trích được CSV.'); st.code((proc.stdout + proc.stderr)[-5000:])
                    else:
                        offset = datetime.now().astimezone().strftime('%z')
                        send_csv(output_path.read_text(encoding='utf-8-sig'), api_url,
                                 uploaded.name, 'pcap_replay', True, offset[:3] + ':' + offset[3:])
            except subprocess.TimeoutExpired:
                st.error('Trích xuất quá 120 giây; đã dừng tiến trình. Hãy thử file nhỏ hơn.')
            except OSError as exc:
                st.error(f'Không đọc/chạy được file: {exc}')

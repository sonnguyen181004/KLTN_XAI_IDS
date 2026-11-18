"""IDS_M1-style monitoring view, backed exclusively by the Java trial API."""
import hashlib
import pandas as pd
import altair as alt
import requests
import streamlit as st
from ui_style import badge, card, paint, COLORS


def render_monitor(model, scope, call, show_detail):
    try:
        state = call('GET', '/status', model)
        rows = call('GET', '/flows', model)
    except (RuntimeError, requests.RequestException) as exc:
        st.error(f'Không đọc được dữ liệu: {exc}')
        return
    if state.get('active_model') and state['active_model'] != model:
        st.info(f"Lượt này được chạy cho {state['active_model']}, chưa dự đoán bằng {model}. Chọn lại model của lượt hoặc nạp PCAP cho {model}. Đây không phải lỗi đặc trưng.")
        return
    run = state['run_id'] or 'empty'
    now = pd.Timestamp.now()
    def matches(row):
        if scope['label'] != 'Tất cả' and (row['prediction'] or 'Không hợp lệ') != scope['label']:
            return False
        if scope['alerts'] and row['prediction'] in (None, 'Benign'):
            return False
        for key in ('src_ip', 'dst_ip'):
            if scope[key] and scope[key] != row[key]:
                return False
        if scope['window'] != 'Toàn bộ lượt':
            t = pd.to_datetime(row['time'], format='mixed', dayfirst=True, errors='coerce')
            if pd.isna(t):
                return False
            if scope['window'] == 'Hôm nay':
                return t.date() == now.date()
            return now - pd.Timedelta(minutes={'5 phút': 5, '15 phút': 15, '1 giờ': 60}[scope['window']]) <= t <= now
        return True
    filtered = [r for r in rows if matches(r)]
    for column, args in zip(st.columns(4), [('API', 'Hoạt động', 'ok'), ('Model', f'{model} · {state["n_classes"]} lớp', 'ok'),
                                            ('Capture', state['phase'], 'ok' if state['phase'] == 'capturing' else 'neutral'),
                                            ('Bộ trích xuất', 'Java CICFlowMeter', 'neutral')]):
        column.markdown(badge(*args), unsafe_allow_html=True)
    st.caption(f'Lượt: {run} · Gói đầu theo giờ CSV · Số liệu trong phạm vi bộ lọc')
    benign = sum(r['prediction'] == 'Benign' for r in filtered)
    alerts = sum(r['prediction'] not in (None, 'Benign') for r in filtered)
    invalid = sum(r['prediction'] is None for r in filtered)
    done = sum(r['shap'] is not None for r in filtered)
    failed = sum(bool(r['error']) and r['prediction'] is not None for r in filtered)
    for column, args in zip(st.columns(6), [('Tổng flow', len(filtered), 'trong bộ lọc'), ('Benign', benign, 'nhãn bình thường', 'ok'),
            ('Cảnh báo', alerts, 'không phải FPR', 'warn'), ('Không hợp lệ', invalid, 'không đưa vào model', 'off'),
            ('SHAP xong', done, 'đã có giải thích', 'ok'), ('Giải thích lỗi', failed, 'cần kiểm tra', 'bad' if failed else 'neutral')]):
        column.markdown(card(*args), unsafe_allow_html=True)
    if state['error']:
        st.error(state['error'])
    if state['packet_summary']:
        st.caption(state['packet_summary'])
    if not filtered:
        st.info('Không có flow khớp bộ lọc. Flow còn mở sẽ xuất khi đóng hoặc khi dừng capture.')
        return
    left, right = st.columns(2)
    with left:
        st.markdown('**Flow theo phút**')
        times = pd.to_datetime([r['time'] for r in filtered], format='mixed', errors='coerce', dayfirst=True)
        timeline = pd.DataFrame({'Giờ': times.strftime('%d/%m %H:%M'), 'Kết quả': [
            'Không hợp lệ' if r['prediction'] is None else 'Benign' if r['prediction'] == 'Benign' else 'Cảnh báo' for r in filtered]})
        timeline = timeline.dropna().groupby(['Giờ', 'Kết quả']).size().reset_index(name='Flow')
        st.altair_chart(alt.Chart(timeline).mark_bar().encode(x='Giờ:O', y='Flow:Q',
            color=alt.Color('Kết quả:N', scale=alt.Scale(domain=['Benign', 'Cảnh báo', 'Không hợp lệ'], range=[COLORS['ok'], COLORS['warn'], COLORS['off']])),
            tooltip=['Giờ', 'Kết quả', 'Flow']).properties(height=210), width='stretch')
    with right:
        st.markdown('**Phân bố nhãn dự đoán**')
        counts = pd.Series([r['prediction'] or 'Không hợp lệ' for r in filtered]).value_counts()
        data = pd.DataFrame([{'Nhãn': k, 'Flow': int(v)} for k, v in counts.items()])
        st.altair_chart(alt.Chart(data).mark_bar().encode(y=alt.Y('Nhãn:N', sort='-x', axis=alt.Axis(labelLimit=320)), x='Flow:Q',
            color=alt.condition(alt.datum['Nhãn'] == 'Benign', alt.value(COLORS['ok']), alt.value(COLORS['warn'])),
            tooltip=['Nhãn', 'Flow']).properties(height=max(160, len(data)*28)), width='stretch')
    st.subheader('Lịch sử & phân tích flow')
    signature = hashlib.sha256(str((model, run, scope)).encode()).hexdigest()[:12]
    page_key, selection_key = 'page_' + signature, 'selected_' + signature
    pages = max(1, (len(filtered) + 49) // 50)
    page = max(1, min(pages, st.session_state.get(page_key, 1)))
    st.session_state[page_key] = page
    subset = filtered[::-1][(page-1)*50:page*50]
    ids = [r['id'] for r in subset]
    table_key = 'table_' + signature + '_' + str(page)
    def select_row():
        selected = st.session_state[table_key]['selection']['rows']
        if selected and selected[0] < len(ids):
            st.session_state[selection_key] = ids[selected[0]]
    table = pd.DataFrame([{'Flow ID': r['id'], 'Gói đầu (GMT+7)': r['time'],
        'Nguồn →': f"{r['src_ip'] or '?'}:{r['src_port'] or '?'}", 'Đích · giao thức': f"{r['dst_ip'] or '?'}:{r['dst_port'] or '?'} · {r['protocol']}",
        'Nhãn': r['prediction'] or 'Không hợp lệ', 'Xác suất': f"{r['confidence']:.2%}" if r['confidence'] is not None else '—',
        'Nhánh': r['branch'] or '—', 'SHAP': 'Đã có' if r['shap'] else 'Không dự đoán' if not r['prediction'] else 'Theo yêu cầu',
        'LIME': (r['lime'] or {}).get('status', 'Chưa yêu cầu')} for r in subset])
    st.caption('Mới nhất trước · Bấm một dòng để hiện chi tiết ngay bên dưới. Flow đang xem được giữ khi làm mới.')
    st.dataframe(paint(table), hide_index=True, width='stretch', height=min(560, 38+35*len(table)),
                 key=table_key, selection_mode='single-row', on_select=select_row)
    back, forward, where = st.columns([1, 1, 6])
    def move(delta):
        st.session_state[page_key] = max(1, min(pages, page + delta))
    back.button('← Trang trước', disabled=page <= 1, on_click=move, args=(-1,), key='back_'+signature)
    forward.button('Trang sau →', disabled=page >= pages, on_click=move, args=(1,), key='next_'+signature)
    where.caption(f'Trang {page}/{pages} · {len(filtered)} flow · 50 flow/trang')
    if st.session_state.get(selection_key) not in [r['id'] for r in filtered]:
        st.session_state[selection_key] = ids[0]
    with st.container(border=True):
        show_detail(st.session_state[selection_key], model)
    with st.expander('Nhóm cảnh báo · cửa sổ 5 phút'):
        groups = {}
        for r in filtered:
            if r['prediction'] in (None, 'Benign'):
                continue
            t = pd.to_datetime(r['time'], format='mixed', errors='coerce', dayfirst=True)
            key = (t.floor('5min').strftime('%d/%m %H:%M') if not pd.isna(t) else '?', r['src_ip'], r['dst_ip'], r['dst_port'], r['prediction'])
            groups.setdefault(key, []).append(r['id'])
        st.dataframe([dict(zip(['Cửa sổ', 'Nguồn', 'Đích', 'Cổng', 'Nhãn'], k), **{'Số flow': len(v), 'Flow ID': ', '.join(map(str,v))})
                      for k,v in groups.items()], hide_index=True, width='stretch')

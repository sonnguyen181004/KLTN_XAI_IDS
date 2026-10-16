"""Plain-language feature cards and LIME failure explanation, presentation only."""
import streamlit as st
from feature_help import describe, reading, number, effect


def feature_card(name, value):
    info = describe(name)
    st.markdown(f"**{name} — {info['title']}**")
    st.write(info['meaning'])
    st.write('Giá trị flow này: ' + reading(name, value))
    if info['note']:
        st.caption(info['note'])


def explain_top_features(flow, method):
    items = flow.get('shap_top5' if method == 'SHAP' else 'lime_top5') or []
    st.markdown('**Đọc từng đặc trưng bằng lời**')
    st.caption('Fwd = cùng chiều gói đầu tiên của flow; Bwd = chiều ngược lại. Không luôn đồng nghĩa máy bạn gửi/nhận.')
    for index, item in enumerate(items):
        name = item['feature'] if method == 'SHAP' else item['feature_desc']
        weight = item['phi'] if method == 'SHAP' else item['weight']
        value = item.get('value', (flow.get('features') or {}).get(name))
        info = describe(name)
        with st.expander(f"{name} — {info['title']} · hệ số {number(weight)}", expanded=index == 0):
            feature_card(name, value)
            st.write(effect(weight, flow['predicted_label'], method))
            st.caption('Đây là giải thích kết quả model cho flow này, không phải quy tắc rằng cứ có đặc trưng này là tấn công.')


def lime_problem(flow, reference):
    diagnostics = flow.get('lime_diagnostics') or {}
    status = flow.get('lime_status')
    st.warning('LIME chưa giải thích được đáng tin cậy cho flow này — không phải lỗi vẽ biểu đồ.')
    st.markdown('**LIME làm gì?**')
    st.write('LIME tạo nhiều phiên bản thay đổi đặc trưng của flow, hỏi model dự đoán từng phiên bản, rồi học một mô hình đơn giản để giải thích. Những phiên bản càng gần flow gốc càng được coi trọng.')
    st.markdown('**Vì sao flow này không có thanh LIME?**')
    if status == 'insufficient_neighborhood' and diagnostics:
        count = diagnostics.get('samples', 0)
        nonzero = diagnostics.get('nonzero_weights', 0)
        st.write(f"Trong {number(count)} mẫu, {number(count - nonzero)} mẫu có trọng số bằng 0; chỉ {number(nonzero)} mẫu còn trọng số. Cỡ mẫu hiệu dụng chỉ khoảng {number(diagnostics.get('effective_sample_size'))} mẫu.")
        if nonzero == 1:
            st.write('Nói đơn giản: LIME gần như chỉ còn nhìn vào chính flow gốc, không còn các ví dụ lân cận hữu ích để học vì sao dự đoán thay đổi. Vì vậy không nên đọc các hệ số 0 như một bảng xếp hạng đặc trưng.')
        else:
            st.write('Các mẫu khác đóng góp quá ít; kết quả gần như bị chi phối bởi một mẫu, nên không đủ cơ sở cho lời giải thích cục bộ.')
        rows = reference.get('features', [])
        mismatches = [r for r in rows if r['constant_mismatch']]
        if mismatches:
            st.markdown('**Dấu hiệu lệch mẫu nền đang thấy ở flow này**')
            for row in mismatches[:2]:
                st.write(f"• {row['feature']} ({describe(row['feature'])['title']}): flow = {number(row['value'])}; cả {number(reference['background_n'])} mẫu nền đều = {number(row['background_min'])}.")
            st.caption('Các lệch này góp vào khoảng cách chuẩn hóa lớn. Chẩn đoán phía trên xác nhận mất tác dụng mẫu lân cận; chưa chứng minh đây là lỗi đơn vị hay tấn công thật.')
    elif status == 'zero_coefficients':
        st.write('Các hệ số LIME đã lưu đều bằng 0, nên không có thanh dài/ngắn để so. Kết quả này không chỉ ra được đặc trưng nào có tác động khác 0.')
        if not diagnostics:
            st.write('Đây là kết quả cũ, chưa lưu thông tin các mẫu lân cận. Bấm kiểm tra lại để biết có phải mẫu sinh đã mất tác dụng hay không.')
    else:
        st.write('Phép đo độ khớp của mô hình LIME không xác định trong lần tính này, nên hệ thống không trình bày nó như một giải thích hợp lệ.')
    st.markdown('**Nên hiểu kết quả thế nào?**')
    st.write('Dự đoán của XGBoost vẫn giữ nguyên. SHAP vẫn xem được ở tab bên cạnh; LIME lần này không đủ cơ sở để dùng làm đối chiếu. R² = 1 trong trường hợp chỉ còn một mẫu không chứng minh giải thích tốt.')
    st.caption('Bấm lại với cùng flow/cấu hình thường cho cùng kết quả. Không cần bấm liên tục; muốn khắc phục tận gốc cần đánh giá riêng dữ liệu/định nghĩa đặc trưng và cách lấy mẫu LIME, không tự đổi cấu hình RQ2 để có biểu đồ.')
    if diagnostics:
        with st.expander('Thông số kỹ thuật LIME (dành cho kiểm tra sâu)'):
            st.json(diagnostics)


def feature_guide(flow, reference):
    st.subheader('Đặc trưng này là gì?')
    st.write('Chọn tên bạn vừa thấy trên SHAP hoặc LIME để đọc ý nghĩa và giá trị của nó trong flow đang xem.')
    st.caption('Fwd: chiều từ nguồn sang đích theo gói đầu tiên; Bwd: chiều ngược lại. IAT: thời gian giữa gói; Min/Max: nhỏ/lớn nhất; Mean: trung bình; Std: mức phân tán.')
    rows = reference['features']
    by_name = {row['feature']: row for row in rows}
    preferred = [r['feature'] for r in flow.get('shap_top5') or []]
    if flow.get('lime_status') == 'ok':
        preferred += [r['feature_desc'] for r in flow.get('lime_top5') or []]
    names = list(dict.fromkeys([name for name in preferred if name in by_name] + sorted(by_name)))
    name = st.selectbox('Tra cứu tên đặc trưng (ưu tiên tên trong SHAP/LIME)', names,
                        key='feature_guide_' + flow['flow_id'],
                        format_func=lambda n: f"{n} — {describe(n)['title']}")
    row = by_name[name]
    feature_card(name, row['value'])
    st.write('SHAP: ' + effect(row['shap_phi'], flow['predicted_label'], 'SHAP'))
    if flow.get('lime_status') == 'ok':
        st.write('LIME: ' + effect(row['lime_weight'], flow['predicted_label'], 'LIME'))
    else:
        st.caption('LIME: chưa có kết quả đã kiểm tra hợp lệ để diễn giải cho đặc trưng này.')
    st.caption('Không nằm trong Top-5 chỉ có nghĩa chưa được hiển thị, không có nghĩa đóng góp bằng 0.')
    with st.expander('So sánh số liệu tham chiếu của đặc trưng đang chọn'):
        st.caption(reference['background_source'] + '. ' + reference['class_reference_source'])
        st.dataframe([{'Nhóm': title, 'Số mẫu': row[key]['n'], 'P05': row[key]['p05'],
                       'Trung vị': row[key]['median'], 'P95': row[key]['p95']}
                      for title, key in [('Nền LIME', 'background'), ('Benign có nhãn', 'benign'),
                                        ('Lớp ' + flow['predicted_label'] + ' có nhãn', 'predicted_class')]],
                      hide_index=True, width='stretch')
        st.caption('Trung vị là giá trị giữa khi sắp mẫu; P05–P95 là khoảng từ phân vị 5% đến 95%. Đây không phải ngưỡng phân loại tấn công.')
    with st.expander('Tra cứu toàn bộ 78 đặc trưng'):
        st.dataframe([{'Tên': r['feature'], 'Tên dễ hiểu': describe(r['feature'])['title'],
                       'Giá trị': reading(r['feature'], r['value']), 'Ý nghĩa': describe(r['feature'])['meaning']}
                      for r in sorted(rows, key=lambda r: r['feature'])], hide_index=True, width='stretch')
    with st.expander('Chẩn đoán lệch mẫu nền (nâng cao)'):
        st.caption(reference['warning'])
        st.dataframe([{'Đặc trưng': r['feature'], 'Flow': r['value'], 'Nền min': r['background_min'],
                       'Nền max': r['background_max'], 'Khác nền hằng': r['constant_mismatch'],
                       'Độ lệch chuẩn hóa': r['background_scaled_deviation']} for r in rows], hide_index=True, width='stretch')
        st.caption('Thứ tự ở bảng này là mức lệch mẫu nền, không phải mức quan trọng SHAP/LIME.')

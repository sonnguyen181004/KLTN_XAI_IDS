"""Giao diện giải thích nhánh A/B: thẻ nhánh, các bước quyết định của flow, và trang "A/B là gì". Chỉ trình bày."""
import streamlit as st

from branch_help import (branch_facts, decision_steps, drift_note, evidence_rows, flag_chips, hypothesis_status, rare_classes,
                         summary)
from feature_help import describe

COLORS = {'ok': '#27a884', 'warn': '#ed9851'}


def _card(info, chips):
    color = COLORS[info['level']]
    chip_html = ''.join(
        f"<span title='{tip}' style='display:inline-block;margin:2px 8px 2px 0;padding:2px 10px;border-radius:12px;"
        f"border:1px solid {COLORS[level]};font-size:.8rem'><b>{name}:</b> {text}</span>" for name, text, level, tip in chips)
    st.markdown(
        f"<div style='border-left:6px solid {color};padding:8px 14px;background:rgba(128,128,128,.08);border-radius:6px'>"
        f"<div style='font-size:1.1rem;font-weight:700'>{info['title']}</div>"
        f"<div style='margin-top:2px'>{info['meaning']}</div>"
        f"<div style='margin-top:4px;opacity:.85'><b>Nên làm:</b> {info['action']}</div>"
        f"<div style='margin-top:6px'>{chip_html}</div></div>", unsafe_allow_html=True)


def render_branch(flow, rules):
    """Tầng 1 (thẻ) + tầng 2 (các bước quyết định) + tầng 3 (A/B là gì). rules=None nếu API chưa trả được."""
    facts = branch_facts(flow, rules) if rules else None
    if not flow.get('branch'):
        st.info('Chưa phân nhánh A/B vì SHAP chưa xong cho cảnh báo này.')
        return facts
    if not facts:
        st.info(f"Nhánh {flow['branch']}: {flow.get('branch_reason') or ''} Không đọc được luật từ API nên chưa giải thích chi tiết.")
        return facts
    _card(summary(facts), flag_chips(facts))
    note = drift_note(facts)
    if note:
        (st.warning if facts['current_branch'] != facts['branch'] else st.caption)(note)
    with st.expander('Nhánh này được quyết định thế nào?'):
        for number, title, detail in decision_steps(facts):
            st.markdown(f'**Bước {number}. {title}.** {detail}')
        st.caption('Nhánh chỉ đổi cách hiển thị và lời nhắc. Không đổi nhãn dự đoán, không ẩn cảnh báo, không phải điểm tin cậy.')
    render_about(rules, key=flow['flow_id'])
    return facts


def render_about(rules, key=''):
    with st.expander('A/B là gì? Vì sao hệ thống có nhánh này?'):
        st.markdown('**Vì sao có nhánh.** Giải thích của AI (SHAP, LIME) không phải lúc nào cũng đáng tin như nhau. '
                    'Thay vì chấm một điểm tin cậy chưa được kiểm chứng, hệ thống dùng hai dấu hiệu đơn giản, đọc được, '
                    'để quyết định **cách hiển thị**: nhánh A hiện bình thường, nhánh B hiện kèm lời nhắc xem lại và gợi ý xem LIME.')
        st.markdown('**Quyết định thế nào.** Không dấu hiệu nào bật → **A**. Có ít nhất một dấu hiệu bật → **B**. Không có tiêu chí nào khác.')
        st.markdown('**Nhánh A/B không phải:** điểm tin cậy; kết luận tấn công thật hay giả; thứ làm đổi nhãn dự đoán hay ẩn cảnh báo. '
                    'A không có nghĩa là kết quả đúng; B không có nghĩa là báo nhầm.')
        st.markdown('**Dấu hiệu 1: nhạy môi trường (giả thuyết).** Một số đặc trưng có thể phản ánh cách dựng mạng lab của bộ dữ liệu '
                    '(cổng, kích thước header TCP, cửa sổ nhận, cờ FIN) thay vì hành vi tấn công. Nếu Top-5 SHAP của flow có từ '
                    f"{(rules or {}).get('env_threshold', '?')} đặc trưng như vậy thì bật dấu hiệu.")
        st.warning(hypothesis_status())
        if rules:
            st.dataframe(evidence_rows(rules, describe), hide_index=True, width='stretch')
            st.caption('Cột «Đã đo được» tính trực tiếp từ model đang chạy (tổng gain theo mọi lớp). Độ quan trọng cao chưa chứng minh '
                       'đặc trưng đó là dấu vết môi trường; đó chính là phần còn là giả thuyết (cột «Phản ánh môi trường lab?»). Ngược lại, độ quan trọng toàn model thấp chưa có nghĩa là không đáng lưu ý: '
                       'có đặc trưng chỉ quyết định ở một vùng giá trị hẹp.')
            rare = rare_classes(rules)
            st.markdown(f"**Dấu hiệu 2: lớp hiếm.** Lớp dự đoán có ít hơn {rules.get('rare_min_samples', '?')} mẫu train. "
                        'Model học ít về lớp đó nên giải thích dễ kém ổn định. '
                        + ('Hiện có: ' + ', '.join(f'{label} ({n} mẫu)' for label, n in rare) + '.' if rare else 'Hiện không có lớp nào dưới ngưỡng.'))
        st.markdown('**Đã cố ý không dùng** làm tiêu chí: độ trùng giữa SHAP và LIME (Agreement), vì ở kết quả RQ2 nó thiếu ổn định '
                    '(Jaccard@5 trung bình khoảng 0,14); điểm faithfulness tính nhanh, vì chỉ là bản rút gọn; và ngưỡng từ tập dev 250 flow của RQ2, '
                    'vì tập đó không đại diện (phần lớn là Benign).')

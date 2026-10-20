"""Gợi ý đọc cảnh báo bằng lời: chỉ là lớp trình bày, không đổi nhãn, xác suất hay nhánh A/B."""

# Đo trên train_set.parquet (2,8 triệu dòng) ngày 19/10/2026: trong vùng
# FIN Flag Cnt>=1, Fwd Pkt Len Max>=66, Fwd Seg Size Min<32 có 445 flow, 445 là Hulk, 0 là Benign.
HULK_FIN_TRAIN = dict(hulk=445, benign=0)
LIME_BAD = ('insufficient_neighborhood', 'zero_coefficients', 'undefined_fit')
# Đo ngày 19/10/2026 trên máy này: số flow cảnh báo mà LIME cho kết quả hợp lệ / số đã chạy.
LIME_VALID = dict(lab=(143, 198), realtime=(1, 113), pcap=(0, 8))
LIME_LIVE_NOTE = (
    'Với traffic thật (realtime, PCAP), LIME thường không đủ tin cậy: LIME tạo các mẫu giả quanh flow dựa trên '
    '2.000 flow mẫu của tập train, mà flow thật thường nằm xa dữ liệu đó nên các mẫu giả không đại diện cho flow. '
    f"Đo ngày 19/10/2026: hợp lệ {LIME_VALID['realtime'][0]}/{LIME_VALID['realtime'][1]} flow realtime và "
    f"{LIME_VALID['pcap'][0]}/{LIME_VALID['pcap'][1]} flow PCAP, so với {LIME_VALID['lab'][0]}/{LIME_VALID['lab'][1]} trên dữ liệu lab. "
    'Khi đó hệ thống ghi «Không đủ tin cậy» thay vì hiện kết quả sai; SHAP vẫn dùng được.')
SHAP_SHORT = {'processed': 'Có', 'queued': 'Chờ', 'pending_dispatch': 'Chờ', 'recovery_pending': 'Chờ',
              'failed': 'Lỗi', 'dropped_queue_full': 'Bỏ', 'unknown_legacy': 'Cũ'}


def fin_data_hint(label, fin, fwd_pkt_len_max, fwd_seg_size_min):
    """Trả về dict(tag, text) khi cảnh báo Hulk khớp vùng "đóng bằng FIN + có gửi dữ liệu", ngược lại None."""
    if label != 'DoS attacks-Hulk' or None in (fin, fwd_pkt_len_max, fwd_seg_size_min):
        return None
    if fin >= 1 and fwd_pkt_len_max >= 66 and fwd_seg_size_min < 32:
        return dict(
            tag='FIN + có dữ liệu',
            text=('Flow này đóng kết nối bằng FIN và có gửi dữ liệu. Trong dữ liệu train, kiểu này chỉ gặp ở Hulk '
                  f"({HULK_FIN_TRAIN['hulk']}/{HULK_FIN_TRAIN['hulk']} flow, {HULK_FIN_TRAIN['benign']} Benign) vì mọi flow Benign "
                  'đóng bằng FIN trong train đều không gửi dữ liệu. Với traffic duyệt web bình thường, đây có thể là báo nhầm, '
                  'cần xem lại. Đây là gợi ý, không phải kết luận.'))
    return None


def lime_badge(flow, short=False):
    """Trạng thái LIME; short=True là nhãn ngắn cho cột của bảng."""
    if not flow.get('is_alert', flow.get('alert_id') is not None):
        return '—'
    status = flow.get('lime_status', 'not_requested')
    if status == 'ok':
        return 'Hợp lệ'
    if status in LIME_BAD:
        return 'Không tin cậy' if short else 'Không đủ tin cậy'
    if status == 'legacy_unchecked':
        return 'Cũ' if short else 'Cũ, chưa kiểm'
    return 'Chưa' if short else 'Chưa chạy'


def why_suspect(shap_top5, describe, reading, limit=2):
    """Một câu tiếng Việt từ các đặc trưng SHAP đẩy điểm lớp đang giải thích mạnh nhất."""
    pushing = sorted((i for i in shap_top5 or [] if i.get('phi', 0) > 0), key=lambda i: -i['phi'])[:limit]
    if not pushing:
        return None
    short = lambda text: text.split(' — ')[0]
    parts = [f"«{short(describe(i['feature'])['title'])}» ({short(reading(i['feature'], i.get('value')))})" for i in pushing]
    return 'Đặc trưng đẩy điểm lớp này mạnh nhất: ' + ' và '.join(parts) + '.'


def shap_short(flow):
    """Nhãn SHAP ngắn cho cột của bảng."""
    if not flow.get('is_alert'):
        return '—'
    return SHAP_SHORT.get(flow.get('explanation_status'), '?')

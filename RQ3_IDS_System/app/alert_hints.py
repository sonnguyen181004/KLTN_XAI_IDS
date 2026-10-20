"""Gợi ý đọc cảnh báo bằng lời: chỉ là lớp trình bày, không đổi nhãn, xác suất hay nhánh A/B.
Không ghi cứng số liệu: ngưỡng ở config.yaml (hulk_fin_hint), số đếm tính từ file train thật, số LIME tính từ DB."""
import functools
from pathlib import Path

import yaml

RQ3 = Path(__file__).resolve().parents[1]
LIME_BAD = ('insufficient_neighborhood', 'zero_coefficients', 'undefined_fit')
SHAP_SHORT = {'processed': 'Có', 'queued': 'Chờ', 'pending_dispatch': 'Chờ', 'recovery_pending': 'Chờ',
              'failed': 'Lỗi', 'dropped_queue_full': 'Bỏ', 'unknown_legacy': 'Cũ'}


def thousands(number):
    return f'{number:,}'.replace(',', '.')


@functools.lru_cache(maxsize=1)
def hint_rule():
    """(ngưỡng từ config.yaml, đường dẫn train_set)."""
    cfg = yaml.safe_load((RQ3 / 'config.yaml').read_text(encoding='utf-8'))
    return cfg['hulk_fin_hint'], RQ3.parent / cfg['paths']['train_set']


@functools.lru_cache(maxsize=1)
def train_counts():
    """Đếm trực tiếp trên train_set: vùng khớp luật, trong đó bao nhiêu Hulk/Benign, và tổng Benign đóng bằng FIN.
    Không đọc được file train thì trả None (khi đó không hiện gợi ý, không bịa số)."""
    rule, path = hint_rule()
    try:
        import pandas as pd
        frame = pd.read_parquet(path, columns=['Label', 'FIN Flag Cnt', 'Fwd Pkt Len Max', 'Fwd Seg Size Min'])
    except Exception:  # noqa: BLE001 - thiếu file/thư viện: bỏ gợi ý thay vì làm hỏng giao diện
        return None
    fin = frame['FIN Flag Cnt'] >= rule['min_fin_flag_cnt']
    region = fin & (frame['Fwd Pkt Len Max'] >= rule['min_fwd_pkt_len_max']) & (frame['Fwd Seg Size Min'] < rule['below_fwd_seg_size_min'])
    benign = frame['Label'] == rule['benign_label']
    hulk = frame['Label'] == rule['label']
    return dict(region=int(region.sum()), hulk=int((region & hulk).sum()), benign=int((region & benign).sum()),
                benign_fin=int((fin & benign).sum()), rows=int(len(frame)))


def fin_data_hint(label, fin, fwd_pkt_len_max, fwd_seg_size_min):
    """Trả về dict(tag, text) khi cảnh báo Hulk khớp vùng "đóng bằng FIN + có gửi dữ liệu", ngược lại None."""
    rule, _ = hint_rule()
    if label != rule['label'] or None in (fin, fwd_pkt_len_max, fwd_seg_size_min):
        return None
    if not (fin >= rule['min_fin_flag_cnt'] and fwd_pkt_len_max >= rule['min_fwd_pkt_len_max']
            and fwd_seg_size_min < rule['below_fwd_seg_size_min']):
        return None
    n = train_counts()
    if not n or not n['region']:
        return None
    if n['benign'] == 0:
        evidence = (f"Trong dữ liệu train, kiểu này chỉ gặp ở Hulk ({thousands(n['hulk'])}/{thousands(n['region'])} flow, 0 Benign) "
                    f"vì mọi flow Benign đóng bằng FIN trong train ({thousands(n['benign_fin'])} flow) đều không gửi dữ liệu. "
                    'Với traffic duyệt web bình thường, đây có thể là báo nhầm, cần xem lại. ')
    else:
        evidence = (f"Trong dữ liệu train, kiểu này gặp ở Hulk {thousands(n['hulk'])}/{thousands(n['region'])} flow và ở Benign "
                    f"{thousands(n['benign'])}/{thousands(n['region'])} flow, nên cần xem thêm bối cảnh. ")
    return dict(tag='FIN + có dữ liệu',
                text='Flow này đóng kết nối bằng FIN và có gửi dữ liệu. ' + evidence + 'Đây là gợi ý, không phải kết luận.')


def lime_note(validity, background_n=None):
    """Chú thích đặt trên nút LIME. Số liệu lấy từ chính DB (validity = /lime_validity), không gõ cứng."""
    sizes = f' {thousands(background_n)}' if background_n else ''
    why = (f'LIME tạo các mẫu giả quanh flow dựa trên{sizes} flow mẫu của tập train; flow thật nằm xa dữ liệu mẫu '
           'thì các mẫu giả không đại diện cho flow đó, và hệ thống ghi «Không đủ tin cậy» thay vì hiện kết quả sai. ')
    names = {'feeder_live': 'realtime', 'pcap_replay': 'PCAP', 'csv_upload': 'CSV', 'api': 'API'}
    parts = [f"{names.get(r['source'], r['source'])} {r['valid']}/{r['ran']}" for r in (validity or {}).get('sources', []) if r['ran']]
    stats = ('Số lần LIME cho kết quả hợp lệ trên dữ liệu của hệ thống này (hợp lệ/đã chạy): ' + ' · '.join(parts) + '. ') if parts \
        else 'Chưa có lần chạy LIME nào được kiểm tra để thống kê. '
    return 'Với traffic thật, LIME có thể không đủ tin cậy. ' + why + stats + 'SHAP vẫn dùng được.'


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

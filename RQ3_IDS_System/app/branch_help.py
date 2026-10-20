"""Giải thích nhánh A/B bằng lời. Chỉ là lớp trình bày: không đổi nhánh, nhãn, xác suất hay luật.

Luật thật nằm ở app/reliability.py (ReliabilityScorer._decide_branch): không cờ nào bật -> A, có ít nhất một cờ -> B.
Ngưỡng, danh sách đặc trưng môi trường và số mẫu train từng lớp đến từ API (/branch_rules, đọc config.yaml và
train_stats.json), không gõ cứng ở đây.
"""

from alert_hints import thousands

# Giả thuyết "đặc trưng môi trường" (model nhận ra tấn công qua dấu vết mạng lab) mới là giả thuyết.
# Chỉ đổi thành True khi thực nghiệm kiểm chứng (E4 trong docs/plan.md) đã làm xong và có kết quả.
ENV_HYPOTHESIS_VALIDATED = False

SHORT = {'A': '✓ Bình thường', 'B': '⚠ Xem lại'}
FULL = {'A': 'Giải thích bình thường', 'B': 'Cần xem lại giải thích'}


def branch_short(branch):
    """Nhãn ngắn cho cột bảng."""
    return SHORT.get(branch, '—')


def branch_option(value):
    """Tên hiển thị trong bộ lọc; giá trị gửi API vẫn là A/B."""
    return {'Tất cả': 'Tất cả', 'A': 'A · bình thường', 'B': 'B · cần xem lại'}.get(value, value)


def branch_facts(flow, rules):
    """Gom các con số của chính flow này để giải thích vì sao ra nhánh đó. Trả None nếu chưa phân nhánh (SHAP chưa xong)."""
    if not flow.get('branch'):
        return None
    top_k = rules.get('top_k', 5)
    env = set(rules.get('env_features', []))
    shap = (flow.get('shap_top5') or [])[:top_k]
    hits = [item for item in shap if item['feature'] in env]
    stored = flow.get('env_fingerprint_count')
    facts = dict(
        branch=flow['branch'], label=flow.get('predicted_label'), top_k=top_k, shap=shap,
        env_features=sorted(env), env_total=len(env), threshold=rules.get('env_threshold'),
        env_count=stored if stored is not None else len(hits), env_on=bool(flow.get('env_fingerprint_flag')), hits=hits,
        # Số đã lưu lúc tính là chuẩn; nếu config đổi sau đó thì danh sách đối chiếu hiện tại có thể lệch.
        hits_match=stored is None or stored == len(hits),
        rare_on=bool(flow.get('rare_class_flag')), n_train=(rules.get('train_samples_per_class') or {}).get(flow.get('predicted_label')),
        rare_min=rules.get('rare_min_samples'))
    # Nếu danh sách đặc trưng trong config đã đổi sau lúc tính, kết luận theo cấu hình hiện tại có thể khác nhánh đã lưu.
    current_env_on = len(hits) >= (rules.get('env_threshold') or 0) and bool(hits)
    facts['config_drift'] = not facts['hits_match']
    facts['current_branch'] = 'B' if (current_env_on or facts['rare_on']) else 'A'
    return facts


def drift_note(facts):
    """Câu cảnh báo khi cảnh báo này được tính theo danh sách đặc trưng cũ. None nếu không lệch."""
    if not facts['config_drift']:
        return None
    base = ('Cảnh báo này được tính khi danh sách đặc trưng nhạy môi trường còn khác hiện nay (cấu hình đã đổi sau đó); '
            f"số đếm và nhánh hiển thị ở trên là số đã lưu lúc tính. Danh sách hiện tại khớp {len(facts['hits'])} đặc trưng trong Top-{facts['top_k']}.")
    if facts['current_branch'] != facts['branch']:
        return base + f" Nếu tính lại theo cấu hình hiện tại, nhánh sẽ là {facts['current_branch']}."
    return base


def reasons(facts):
    out = []
    if facts['env_on']:
        out.append(f"{facts['env_count']}/{facts['env_total']} đặc trưng nhạy môi trường nằm trong Top-{facts['top_k']} SHAP (bật khi từ {facts['threshold']} trở lên)")
    if facts['rare_on']:
        n = facts['n_train']
        out.append(f"lớp «{facts['label']}» chỉ có {thousands(n) if n is not None else '?'} mẫu train (ít hơn {facts['rare_min']})")
    return out


def summary(facts):
    """Nội dung thẻ nhánh: tiêu đề, một câu nghĩa, và nên làm gì. Không bao giờ nói B là báo nhầm hay A là đúng."""
    if facts['branch'] == 'A':
        return dict(level='ok', title='✓ Giải thích bình thường (nhánh A)',
                    meaning='Không có dấu hiệu nào cần lưu ý: Top-%d SHAP không nghiêng về đặc trưng nhạy môi trường và lớp dự đoán đủ mẫu train.' % facts['top_k'],
                    action='Đọc SHAP như bình thường. Nhánh A không có nghĩa là kết quả đúng.')
    why = reasons(facts)
    return dict(level='warn', title='⚠ Cần xem lại giải thích (nhánh B)',
                meaning='Có ít nhất một dấu hiệu cần lưu ý: ' + '; '.join(why) + '.',
                action='Đọc giải thích thận trọng, đối chiếu với bối cảnh mạng và thử xem LIME. Nhánh B không có nghĩa là báo nhầm; đây là dấu hiệu, không phải kết luận.')


def flag_chips(facts):
    """Hai dấu hiệu (cờ) của flow: (tên, trạng thái, mức màu, giải thích ngắn)."""
    env = ('Dấu hiệu môi trường', f"BẬT · {facts['env_count']}/{facts['env_total']} (ngưỡng {facts['threshold']})" if facts['env_on']
           else f"tắt · {facts['env_count']}/{facts['env_total']} (ngưỡng {facts['threshold']})",
           'warn' if facts['env_on'] else 'ok',
           'Số đặc trưng nhạy môi trường nằm trong Top-%d SHAP của flow này. Đây là giả thuyết, chưa kiểm chứng.' % facts['top_k'])
    n = facts['n_train']
    rare = ('Dấu hiệu lớp hiếm', ('BẬT' if facts['rare_on'] else 'tắt') + f" · {thousands(n) if n is not None else '?'} mẫu train (ngưỡng {facts['rare_min']})",
            'warn' if facts['rare_on'] else 'ok', 'Lớp dự đoán có ít mẫu train thì model học ít và giải thích dễ kém ổn định.')
    return [env, rare]


def decision_steps(facts):
    """Các bước quyết định của chính flow này, để vẽ thành danh sách có đánh dấu."""
    names = ', '.join(f"{i['feature']}" for i in facts['hits']) or 'không có đặc trưng nào'
    steps = [
        ('1', f"Lấy Top-{facts['top_k']} đặc trưng SHAP của flow", ', '.join(i['feature'] for i in facts['shap']) or 'chưa có SHAP'),
        ('2', 'Đếm đặc trưng nhạy môi trường trong đó',
         (f"{facts['env_count']} (số đã lưu lúc tính, theo danh sách đặc trưng lúc đó)" if facts['config_drift'] else f"{facts['env_count']} ({names})")
         + f"; ngưỡng {facts['threshold']} → dấu hiệu môi trường {'BẬT' if facts['env_on'] else 'tắt'}"),
        ('3', 'Kiểm tra lớp dự đoán có ít mẫu train không',
         f"«{facts['label']}» có {thousands(facts['n_train']) if facts['n_train'] is not None else '?'} mẫu; ngưỡng {facts['rare_min']} → dấu hiệu lớp hiếm {'BẬT' if facts['rare_on'] else 'tắt'}"),
        ('4', 'Luật', 'Không dấu hiệu nào bật → nhánh A. Có ít nhất một dấu hiệu bật → nhánh B. Kết quả: nhánh ' + facts['branch'] + '.')]
    return steps


def evidence_rows(rules, describe):
    """Bảng đặc trưng nhạy môi trường: nghĩa + cái đã đo được từ model (độ quan trọng) + phần còn là giả thuyết."""
    rows = []
    importance = rules.get('importance') or {}
    for feature in rules.get('env_features', []):
        info = importance.get(feature) or {}
        measured = (f"Hạng {info['rank']}/{info['of']} về độ quan trọng trong model ({info['share_pct']}% tổng gain)"
                    if info.get('rank') else 'Model không dùng đặc trưng này')
        rows.append({'Đặc trưng': feature, 'Nghĩa': describe(feature)['title'], 'Đã đo được (từ model)': measured,
                     'Phản ánh môi trường lab?': 'Đã kiểm chứng' if ENV_HYPOTHESIS_VALIDATED else 'Chưa kiểm chứng'})
    return rows


def rare_classes(rules):
    """Các lớp đang dưới ngưỡng, tính từ số mẫu train thật."""
    minimum = rules.get('rare_min_samples')
    counts = rules.get('train_samples_per_class') or {}
    return sorted(((label, n) for label, n in counts.items() if minimum is not None and n < minimum), key=lambda x: x[1])


def hypothesis_status():
    return ('Đã kiểm chứng ở thực nghiệm E4.' if ENV_HYPOTHESIS_VALIDATED else
            'Giả thuyết, chưa kiểm chứng (thực nghiệm E4 trong kế hoạch chưa làm): chưa biết model có thật sự nhận ra tấn công qua dấu vết môi trường hay không.')

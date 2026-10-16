"""Vietnamese reading guide for the 78 input features; no detection rules."""
GLOSSARY = {}


def add(name, title, meaning, unit, note=''):
    GLOSSARY[name] = dict(title=title, meaning=meaning, unit=unit, note=note)


add('Dst Port', 'Cổng đích', 'Số cổng ở phía nhận của chiều forward.', 'mã cổng',
    '443 thường dùng cho HTTPS, nhưng chỉ số cổng không xác nhận ứng dụng hay tấn công.')
add('Protocol', 'Giao thức mạng', 'Mã giao thức của gói IP: 6 là TCP, 17 là UDP.', 'mã giao thức')
add('Flow Duration', 'Thời lượng flow', 'Khoảng thời gian từ gói đầu đến gói cuối của flow.', 'µs')
stats = {'Min': 'nhỏ nhất', 'Max': 'lớn nhất', 'Mean': 'trung bình', 'Std': 'độ lệch chuẩn', 'Var': 'phương sai'}
for prefix, direction in [('Fwd', 'chiều đi (forward)'), ('Bwd', 'chiều về (backward)')]:
    add(f'Tot {prefix} Pkts', f'Tổng gói {direction}', f'Số gói quan sát được theo {direction}.', 'gói')
    add(f'TotLen {prefix} Pkts', f'Tổng độ dài gói {direction}', f'Cộng độ dài các gói theo {direction}.', 'byte')
    for suffix in ('Min', 'Max', 'Mean', 'Std'):
        add(f'{prefix} Pkt Len {suffix}', f'Độ dài gói {stats[suffix]} — {direction}',
            f'Thống kê {stats[suffix]} của độ dài các gói theo {direction}.', 'byte')
    for suffix in ('Tot', 'Mean', 'Std', 'Max', 'Min'):
        stat = 'tổng' if suffix == 'Tot' else stats[suffix]
        add(f'{prefix} IAT {suffix}', f'Khoảng cách giữa gói: {stat} — {direction}',
            f'IAT là thời gian giữa hai gói liên tiếp cùng chiều; cột này ghi {stat} theo {direction}.', 'µs',
            'Giá trị 0 có thể do các gói có cùng timestamp/độ phân giải, hoặc thiếu khoảng đo; không tự suy ra tấn công.')
    add(f'{prefix} Header Len', f'Tổng độ dài header {direction}', f'Tổng kích thước phần đầu gói theo {direction}.', 'byte',
        'CICFlowMeter Python 0.5.0 hiện cộng header IPv4; không nhầm với kích thước dữ liệu ứng dụng.')
    add(f'{prefix} Pkts/s', f'Tốc độ gói {direction}', f'Số gói {direction} chia cho thời lượng toàn flow.', 'gói/giây')
    add(f'{prefix} Seg Size Avg', f'Kích thước segment trung bình {direction}', f'Kích thước trung bình theo {direction}.', 'byte',
        'Extractor Python 0.5.0 đang dùng cùng giá trị với Pkt Len Mean tương ứng.')
    for part, title, unit in [('Byts', 'Số byte', 'byte/bulk'), ('Pkts', 'Số gói', 'gói/bulk')]:
        add(f'{prefix} {part}/b Avg', f'{title} trung bình mỗi đợt truyền {direction}',
            f'{title} chia cho số bulk theo {direction}; bulk là nhóm gói truyền liên tiếp được extractor nhận diện.', unit,
            'Không có bulk được ghi nhận thì extractor có thể trả 0; không đồng nghĩa không có traffic.')
    add(f'{prefix} Blk Rate Avg', f'Tốc độ truyền theo đợt {direction}',
        f'Tổng byte trong bulk chia cho tổng thời gian bulk theo {direction}.', 'byte/giây',
        'Khoảng thời gian bulk rất ngắn có thể tạo tốc độ lớn; không phải tốc độ trung bình toàn flow hay ngưỡng tấn công.')
    for part, title, unit in [('Pkts', 'Số gói', 'gói'), ('Byts', 'Số byte', 'byte')]:
        add(f'Subflow {prefix} {part}', f'{title} trong subflow {direction}', f'{title} theo {direction} trong thống kê subflow.', unit,
            'Ở extractor Python 0.5.0, cột này sao chép tổng gói/byte của chiều tương ứng, chưa phải tách subflow độc lập.')
    add(f'Init {prefix} Win Byts', f'Cửa sổ TCP ban đầu {direction}',
        f'Giá trị window TCP ban đầu ghi nhận theo {direction}, liên quan khả năng nhận dữ liệu.', 'byte (giá trị window)',
        'Không diễn giải giá trị thiếu/đặc biệt như số byte payload. Cách xử lý window scaling tùy extractor.')

for suffix in ('Min', 'Max', 'Mean', 'Std', 'Var'):
    add(f'Pkt Len {suffix}', f'Độ dài gói {stats[suffix]} (hai chiều)',
        f'Thống kê {stats[suffix]} của độ dài tất cả gói trong flow.', 'byte²' if suffix == 'Var' else 'byte')
for suffix in ('Mean', 'Std', 'Max', 'Min'):
    add(f'Flow IAT {suffix}', f'Khoảng cách gói {stats[suffix]} (hai chiều)',
        f'Thời gian giữa các gói liên tiếp toàn flow; lấy {stats[suffix]}.', 'µs')
    for prefix, phrase in [('Active', 'hoạt động trước khoảng nghỉ'), ('Idle', 'nghỉ giữa các đợt hoạt động')]:
        add(f'{prefix} {suffix}', f'Thời gian {phrase}: {stats[suffix]}',
            f'Thống kê {stats[suffix]} các khoảng {phrase} do extractor nhận diện.', 'µs',
            'Phụ thuộc ngưỡng active/idle của extractor; giá trị 0 không tự chứng minh kết nối không hoạt động.')
flag_meanings = {'FIN': 'yêu cầu kết thúc một chiều kết nối TCP', 'SYN': 'đồng bộ để thiết lập kết nối TCP',
    'RST': 'đặt lại/ngắt kết nối TCP', 'PSH': 'yêu cầu chuyển dữ liệu tới ứng dụng',
    'ACK': 'xác nhận thông tin TCP đã nhận', 'URG': 'báo trường con trỏ dữ liệu khẩn có ý nghĩa',
    'ECE': 'thông tin ECN liên quan thông báo nghẽn', 'CWE': 'tên cột dataset cho cờ CWR liên quan phản hồi nghẽn'}
for flag, meaning in flag_meanings.items():
    name = 'CWE Flag Count' if flag == 'CWE' else f'{flag} Flag Cnt'
    add(name, f'Số gói có cờ {flag}', f'Cờ {flag}: {meaning}. Cột đếm số gói mang cờ này.', 'gói có cờ',
        'Cờ TCP cũng xuất hiện trong kết nối bình thường; riêng cờ này không chứng minh tấn công. Cách đếm dataset có thể khác extractor live.')
for prefix, direction in [('Fwd', 'chiều đi'), ('Bwd', 'chiều về')]:
    for flag in ('PSH', 'URG'):
        add(f'{prefix} {flag} Flags', f'Số gói có cờ {flag} {direction}',
            f'Đếm gói {direction} có cờ {flag}: {flag_meanings[flag]}.', 'gói có cờ')
GLOSSARY['CWE Flag Count']['note'] = 'Lưu ý: Python CICFlowMeter 0.5.0 hiện sao chép Fwd URG Flags vào cột này; không coi dữ liệu đó là phép đếm CWR độc lập.'
add('Flow Byts/s', 'Tốc độ byte toàn flow', 'Tổng độ dài các gói chia cho thời lượng flow.', 'byte/giây')
add('Flow Pkts/s', 'Tốc độ gói toàn flow', 'Tổng số gói chia cho thời lượng flow.', 'gói/giây')
add('Down/Up Ratio', 'Tỉ lệ gói chiều về / chiều đi', 'Số gói backward chia cho số gói forward.', 'tỉ lệ', 'Không phải tỉ lệ byte tải xuống/tải lên.')
add('Pkt Size Avg', 'Kích thước gói trung bình', 'Kích thước trung bình của các gói toàn flow theo extractor.', 'byte')
add('Fwd Act Data Pkts', 'Gói chiều đi có dữ liệu', 'Số gói forward có payload TCP/UDP, không chỉ header.', 'gói')
add('Fwd Seg Size Min', 'Header nhỏ nhất chiều đi', 'Trong extractor Python hiện tại: kích thước header IPv4 nhỏ nhất ở chiều forward.', 'byte',
    'Ví dụ 20 byte là kích thước header IPv4 không có tùy chọn; không phải 20 byte dữ liệu ứng dụng.')


def describe(name):
    return GLOSSARY.get(name, dict(title=name, meaning='Chưa có giải nghĩa cho tên này; không tự gán nghĩa.', unit='', note=''))


def number(value):
    if value is None:
        return 'Chưa có'
    # Spaces group thousands; decimal comma avoids confusing ESS=1.000 with 1000.
    return f'{float(value):,.6f}'.rstrip('0').rstrip('.').replace(',', ' ').replace('.', ',')


def reading(name, value):
    info = describe(name)
    text = f"{number(value)} {info['unit']}".strip()
    if value is None:
        return text
    if name == 'Protocol':
        text += {6: ' — TCP', 17: ' — UDP', 1: ' — ICMP'}.get(value, '')
    if info['unit'] == 'µs':
        text += f' ≈ {number(float(value) / 1000)} ms'
    if name == 'FIN Flag Cnt':
        text += ' — số gói được ghi nhận có cờ kết thúc kết nối, không phải số cuộc tấn công'
    if name == 'Dst Port' and value == 443:
        text += ' — thường dùng cho HTTPS; không tự xác nhận ứng dụng'
    return text


def effect(weight, label, method):
    if weight is None:
        return 'Chưa có đóng góp được hiển thị.'
    if weight == 0:
        return 'Hệ số bằng 0; không cung cấp hướng tác động trong kết quả này.'
    direction = 'tăng' if weight > 0 else 'giảm'
    if method == 'SHAP':
        return f'Đẩy điểm model về lớp {label} ({direction} điểm).' if weight > 0 else f'Kéo điểm model ra khỏi lớp {label} ({direction} điểm).'
    return f'Hệ số {"dương" if weight > 0 else "âm"} trong mô hình LIME xấp xỉ: theo chiều {direction} điểm xấp xỉ cho lớp {label}. Không phải quan hệ nhân quả.'

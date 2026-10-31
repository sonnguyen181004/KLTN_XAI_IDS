"""Presentation only: never infer missing telemetry or change predictions."""
import math
from datetime import datetime, timedelta, timezone

LOCAL = timezone(timedelta(hours=7))  # mọi giờ hiển thị đều là GMT+7


def integer_text(value):
    if value is None:
        return 'Chưa có'
    try:
        number = float(value)
        return str(int(number)) if math.isfinite(number) and number.is_integer() else str(value)
    except (TypeError, ValueError):
        return str(value)


def protocol_text(value):
    code = integer_text(value)
    return {'6': 'TCP', '17': 'UDP', '1': 'ICMP'}.get(code, code)


def endpoint(ip, port):
    return f"{ip or 'IP chưa được cung cấp'} : {integer_text(port)}"


def bounded_page(page, count, size=50):
    pages = max(1, (count + size - 1) // size)
    return min(max(1, int(page)), pages), pages


def _parse(value):
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace('Z', '+00:00'))


def time_text(value, compact=False, seconds=True, now=None):
    """Một định dạng giờ duy nhất cho cả giao diện, luôn GMT+7.

    Đầy đủ:   20/10/2026 07:08:12
    Rút gọn:  20/10 07:08:12 (bỏ năm khi là năm hiện tại; khác năm thì vẫn hiện năm)
    Không có giờ -> 'Chưa có'; giờ không ISO -> giữ nguyên chữ gốc, không đoán.
    Giờ không kèm múi giờ không bị đổi, chỉ ghi chú '(chưa rõ múi giờ)'.
    """
    if value is None or value == '':
        return 'Chưa có'
    try:
        moment = _parse(value)
    except (TypeError, ValueError):
        return str(value)
    note = ''
    if moment.tzinfo is None:
        note = ' (chưa rõ múi giờ)'
    else:
        moment = moment.astimezone(LOCAL)
    year = (now or datetime.now(LOCAL)).astimezone(LOCAL).year
    date = '%d/%m' if compact and moment.year == year else '%d/%m/%Y'
    return moment.strftime(date + (' %H:%M:%S' if seconds else ' %H:%M')) + note


def age_text(value, now=None):
    """Cách đây bao lâu bằng lời ngắn gọn: 'vừa xong', '5 giây trước', '3 phút trước', '4 giờ trước', '2 ngày trước'."""
    try:
        moment = _parse(value)
    except (TypeError, ValueError):
        return ''
    if moment.tzinfo is None:
        return ''
    seconds = int(((now or datetime.now(timezone.utc)) - moment).total_seconds())
    if seconds < 0:
        return 'giờ ở tương lai (kiểm tra đồng hồ máy)'
    if seconds < 5:
        return 'vừa xong'
    for limit, unit, size in ((60, 'giây', 1), (3600, 'phút', 60), (86400, 'giờ', 3600)):
        if seconds < limit:
            return f'{seconds // size} {unit} trước'
    return f'{seconds // 86400} ngày trước'

"""Presentation only: never infer missing telemetry or change predictions."""
import math


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

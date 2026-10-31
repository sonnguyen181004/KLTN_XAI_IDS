"""Capture metadata stays separate from the model's numeric features."""
from datetime import datetime, timezone, timedelta


def timestamp_utc(raw, offset=None):
    if not raw:
        return None
    value = datetime.fromisoformat(raw.replace('Z', '+00:00'))
    if value.tzinfo is None:
        if not offset:
            return None  # Legacy timestamps must not be assigned a guessed timezone.
        import re
        if not re.fullmatch(r'[+-]\d{2}:\d{2}', offset):
            raise ValueError('Múi giờ cần dạng +07:00')
        hours, minutes = map(int, offset[1:].split(':'))
        if hours > 23 or minutes > 59:
            raise ValueError('Múi giờ không hợp lệ')
        delta = timedelta(hours=hours, minutes=minutes)
        value = value.replace(tzinfo=timezone(delta if offset[0] == '+' else -delta))
    return value.astimezone(timezone.utc).isoformat()


def row_metadata(row, run_id, name, offset=None):
    result = {'capture_run_id': run_id, 'run_name': name[:200]}
    if row.get('extractor_version'):
        result['extractor_version'] = row['extractor_version'][:128]
    for key in ('src_ip', 'dst_ip', 'src_port'):
        if row.get(key):
            result[key] = row[key]
    if row.get('timestamp'):
        result['flow_timestamp'] = row['timestamp'].replace(' ', 'T')
        if offset:
            result['capture_timezone'] = offset
    return result

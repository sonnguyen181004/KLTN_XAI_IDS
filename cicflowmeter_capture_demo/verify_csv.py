"""Show whether CICFlowMeter wrote a non-empty CSV and list the first feature names."""
import csv
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

path = Path(sys.argv[1] if len(sys.argv) > 1 else 'flows.csv')
if not path.exists():
    raise SystemExit(f'Không tìm thấy file: {path}')
if path.stat().st_size == 0:
    raise SystemExit('CSV có 0 byte: chưa có flow được ghi.')

with path.open(encoding='utf-8-sig', newline='') as handle:
    reader = csv.reader(handle)
    header = next(reader, [])
    first_row = next((row for row in reader if any(row)), [])

print(f'CSV: {path.resolve()}')
print(f'Số feature/cột: {len(header)}')
print(f'Có flow đầu tiên: {bool(first_row)}')
print('10 feature đầu:')
for name in header[:10]:
    print(f'  - {name}')

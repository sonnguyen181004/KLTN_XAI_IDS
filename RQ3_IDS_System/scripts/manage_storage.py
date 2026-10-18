"""Explicit local maintenance. Never deletes or replaces an existing DB."""
import argparse
import json
import os
from pathlib import Path
import sys
import yaml

RQ3 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RQ3/'app'))
from storage import storage_status, backup_db, verify_bundle, restore_bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('status', 'backup', 'verify', 'restore'))
    parser.add_argument('--db', type=Path, help='Source DB; default IDS_DB_PATH or config.yaml')
    parser.add_argument('--bundle', type=Path, help='New backup directory, or existing bundle to verify/restore')
    parser.add_argument('--destination', type=Path, help='NEW directory for restored snapshot.db; never live replacement')
    args = parser.parse_args()
    cfg = yaml.safe_load((RQ3/'config.yaml').read_text(encoding='utf-8'))
    source = args.db or Path(os.environ.get('IDS_DB_PATH', str(RQ3.parent/cfg['paths']['sqlite_db'])))
    if args.action == 'status':
        result = storage_status(source, cfg.get('storage', {}).get('warning_free_bytes', 1073741824))
    elif not args.bundle:
        parser.error('--bundle is required')
    elif args.action == 'backup':
        result = backup_db(source, args.bundle)
    elif args.action == 'verify':
        result = verify_bundle(args.bundle)
    else:
        if not args.destination:
            parser.error('--destination must be a NEW directory')
        result = restore_bundle(args.bundle, args.destination)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

"""Private supervisor bootstrap: prove identity before executing a worker CLI."""
import argparse
import json
from pathlib import Path
import runpy
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'app'))
from worker_control import WorkerControl


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--role', choices=['capture', 'feeder'], required=True)
    parser.add_argument('--control-dir', required=True)
    parser.add_argument('--worker-token', required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    control = WorkerControl(args.control_dir, args.worker_token, args.role)
    try:
        deadline = time.monotonic()+30
        while True:
            command = control.tick('starting')
            if command:
                raise RuntimeError('Cancelled before worker release')
            go = Path(args.control_dir)/'go.json'
            if go.exists():
                if json.loads(go.read_text()) != {'worker_token': args.worker_token}:
                    raise RuntimeError('Invalid release token')
                break
            if time.monotonic() > deadline:
                raise RuntimeError('Startup gate timeout')
            time.sleep(.1)
        target, *arguments = args.command
        sys.path.insert(0, str(Path(target).parent))
        sys.argv = [target, *arguments, '--control-dir', args.control_dir, '--worker-token', args.worker_token]
        runpy.run_path(target, run_name='__main__')
    except BaseException as exc:
        if not isinstance(exc, SystemExit) or exc.code not in (None, 0):
            control.finish(False, error_type=type(exc).__name__)
        raise


if __name__ == '__main__':
    main()

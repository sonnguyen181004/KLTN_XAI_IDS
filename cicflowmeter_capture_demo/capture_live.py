"""Reliable Windows launcher for CICFlowMeter 0.5.x live CSV capture.

The upstream 0.5.0 console entry point passes two positional arguments in the
wrong order. This launcher calls its public factory with keyword arguments.
"""
import argparse
import sys
from pathlib import Path

from cicflowmeter.sniffer import create_sniffer


def main():
    parser = argparse.ArgumentParser(description='Capture live CICFlowMeter features to CSV.')
    parser.add_argument('--interface', required=True, help='Network interface, for example Wi-Fi')
    parser.add_argument('--output', default='flows.csv', help='Output CSV file')
    args = parser.parse_args()
    output = Path(args.output).resolve()

    print(f'Capturing CICFlowMeter features on: {args.interface}')
    print(f'CSV output: {output}')
    print('Browse websites for 1-2 minutes, then press Ctrl+C once to stop and flush flows.')

    sniffer, session = create_sniffer(
        input_file=None,
        input_interface=args.interface,
        output_mode='csv',
        output=str(output),
        input_directory=None,
        fields=None,
        verbose=False,
    )
    sniffer.start()
    try:
        sniffer.join()
    except KeyboardInterrupt:
        print('\nStopping capture and flushing remaining flows...')
        sniffer.stop()
    finally:
        if hasattr(session, '_gc_stop'):
            session._gc_stop.set()
            session._gc_thread.join(timeout=2.0)
        session.flush_flows()
        print(f'Capture finished. CSV exists: {output.exists()}')


if __name__ == '__main__':
    main()

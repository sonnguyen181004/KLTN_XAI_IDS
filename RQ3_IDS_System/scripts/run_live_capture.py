"""Bắt/đọc traffic bằng adapter có phiên bản `rq3-cfm-0.5.0-fixes-v2` mặc định.
`--extractor legacy` giữ đường baseline Python CICFlowMeter 0.5.0 cũ.

Đường legacy GỌI THẲNG hàm `create_sniffer()` bằng
keyword argument — né một lỗi thật của thư viện gốc: `cicflowmeter.sniffer.main()`
gọi `create_sniffer(...)` bằng tham số VỊ TRÍ nhưng thứ tự không khớp chữ ký hàm
(`args.verbose` bị nhét nhầm vào tham số `fields`, gây
`AttributeError: 'bool' object has no attribute 'split'`). Dùng keyword argument
ở đây thì không bị ảnh hưởng bởi lỗi thứ tự đó.

Bắt SỐNG (cần quyền Administrator để bắt gói tin trên Windows):
  RQ3_IDS_System/.venv_capture/Scripts/python.exe RQ3_IDS_System/scripts/run_live_capture.py --interface "Wi-Fi" --output RQ3_IDS_System/data/real_capture.csv --seconds 90

Đọc lại 1 file .pcap đã ghi sẵn (nguồn 2 ở plan.md mục 0.1 — KHÔNG cần quyền
Administrator, KHÔNG cần tcpreplay: tự đọc file, chạy xong tự dừng vì không còn gói
nào để đọc):
  RQ3_IDS_System/.venv_capture/Scripts/python.exe RQ3_IDS_System/scripts/run_live_capture.py --pcap-input duong_dan/file.pcap --output RQ3_IDS_System/data/replay_capture.csv

LỖI THẬT đã gặp + đã né: `create_sniffer(input_file=...)` của thư viện gốc gắn cứng
bộ lọc BPF `filter="ip and (tcp or udp)"` cho CẢ chế độ đọc file lẫn bắt sống — với
file pcap, scapy áp bộ lọc này bằng cách tự shell ra chạy `tcpdump -w -`, nhưng
Windows không có sẵn `tcpdump` -> luôn lỗi `Scapy_Exception: tcpdump is not
available`. Bắt sống không bị ảnh hưởng vì dùng Npcap trực tiếp, không qua tcpdump.
Chế độ đọc file ở đây KHÔNG gọi `create_sniffer()` nữa mà tự dựng `AsyncSniffer`
thẳng, bỏ hẳn tham số `filter` — không mất gì vì `FlowSession.process()` (bên trong
thư viện) đã tự bỏ qua mọi gói không phải TCP/UDP, đúng việc bộ lọc kia định làm.
"""
from __future__ import annotations

import argparse
import signal
import sys
import time
import threading
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from cicflowmeter.flow_session import FlowSession
from cicflowmeter.sniffer import GC_INTERVAL, _start_periodic_gc, create_sniffer
from scapy.sendrecv import AsyncSniffer
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from capture_adapter import (ProjectFlowSession, ProjectFlow, ProjectFlowV1,
                             TrainCandidateFlow, EXTRACTOR_VERSION, LEGACY_VERSION)

PROJECT_MODES = {'project': ProjectFlow, 'project-v1': ProjectFlowV1,
                 'train-candidate': TrainCandidateFlow}


def make_session(output, extractor):
    kwargs = dict(output_mode='csv', output=output, fields=None, verbose=False)
    if extractor == 'legacy':
        return FlowSession(**kwargs)
    return ProjectFlowSession(**kwargs, flow_class=PROJECT_MODES[extractor])


def create_replay_sniffer(pcap_path: str, output: str, extractor='project'):
    """Thay cho `create_sniffer(input_file=...)` — xem lý do ở docstring đầu file:
    bản gốc gắn cứng bộ lọc BPF cần `tcpdump`, Windows không có sẵn."""
    session = make_session(output, extractor)
    # Offline PCAP clock can be years old; wall-clock GC would split flows
    # depending on CPU speed. Project session collects by packet timestamps.
    if extractor == 'legacy':
        _start_periodic_gc(session, interval=GC_INTERVAL)
    sniffer = AsyncSniffer(offline=pcap_path, prn=session.process, store=False)
    return sniffer, session


def wait_for_capture(sniffer, seconds=0, stop_event=None, cleanup=None):
    """Keep Python's main thread responsive; never block in Thread.join().

    Windows/Python capture environments can defer Ctrl+C while joining a native
    thread indefinitely. Signal handlers request a stop, including while draining,
    rather than raising another KeyboardInterrupt halfway through CSV export.
    """
    requested = stop_event if stop_event is not None else threading.Event()
    previous = {}
    def request_stop(signum, frame):
        if not requested.is_set():
            print('\nNhận yêu cầu dừng, đang dừng capture và ghi nốt flow...', flush=True)
        requested.set()
    for signum in (signal.SIGINT, getattr(signal, 'SIGBREAK', None)):
        if signum is not None:
            previous[signum] = signal.signal(signum, request_stop)
    deadline = time.monotonic() + seconds if seconds > 0 else None
    try:
        sniffer.start()
        announced = False
        stop_deadline = None
        while sniffer.thread.is_alive():
            if sniffer.running and not announced:
                print('[capture] receiving_started', flush=True)
                announced = True
            if requested.is_set() or (deadline is not None and time.monotonic() >= deadline):
                if stop_deadline is None:
                    stop_deadline = time.monotonic() + 15
                if time.monotonic() >= stop_deadline:
                    raise RuntimeError('Không nhận được tín hiệu sẵn sàng dừng từ capture sau 15 giây.')
                # Scapy installs stop_cb during startup; don't call stop before it exists.
                if hasattr(sniffer, 'stop_cb') and sniffer.running:
                    if not requested.is_set():
                        print(f'\nĐã đủ {seconds} giây, tự dừng...', flush=True)
                    sniffer.stop(join=False)
                    break
            time.sleep(0.1)
        # Bound shutdown without interruptible join/lock ownership side effects.
        limit = time.monotonic() + 15
        while sniffer.thread.is_alive():
            if time.monotonic() >= limit:
                raise RuntimeError('Capture chưa dừng sau 15 giây; không flush CSV khi thread còn ghi. Không coi phiên này đã dừng an toàn.')
            time.sleep(0.1)
        sniffer.join(timeout=0)  # Thread ended; propagate Scapy's stored exception.
    finally:
        try:
            if cleanup is not None:
                cleanup()
        finally:
            for signum, handler in previous.items():
                signal.signal(signum, handler)


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--interface", help='Bắt SỐNG: tên interface, ví dụ "Wi-Fi" (xem bằng Get-NetAdapter)')
    group.add_argument("--pcap-input", help="Đọc lại 1 file .pcap đã ghi sẵn (nguồn 2 — phát lại), thay vì bắt sống")
    parser.add_argument("--output", required=True, help="Đường dẫn file CSV để ghi flow ra")
    parser.add_argument('--extractor', choices=[*PROJECT_MODES, 'legacy'], default='project',
                        help='project: v2; project-v1/legacy: baseline; train-candidate: thử nghiệm một phần quy ước train')
    parser.add_argument('--overwrite', action='store_true', help='Cho phép ghi đè CSV có sẵn; không dùng khi feeder đang theo dõi')
    parser.add_argument("--seconds", type=int, default=0,
                         help="Chỉ áp dụng khi bắt SỐNG: tự dừng sau N giây (0 = chạy tới khi Ctrl+C)")
    args = parser.parse_args()
    if args.seconds < 0:
        parser.error('--seconds phải >= 0')
    if Path(args.output).exists() and Path(args.output).stat().st_size and not args.overwrite:
        parser.error('CSV đầu ra đã có dữ liệu. Chọn tên mới; --overwrite chỉ dành cho ghi đè có chủ đích.')
    print('Extractor: ' + (LEGACY_VERSION if args.extractor == 'legacy' else PROJECT_MODES[args.extractor].extractor_version))
    if args.extractor == 'train-candidate':
        print('THỬ NGHIỆM: chỉ đổi một phần quy ước; chưa chứng nhận tương thích train/V3.')

    is_replay = args.pcap_input is not None
    if is_replay:
        print(f"Đọc lại file pcap có sẵn: {args.pcap_input}, ghi ra: {args.output}")
    else:
        print(f"Bắt đầu bắt traffic trên interface '{args.interface}', ghi ra: {args.output}")
        print("Hãy mở trình duyệt, lướt web bình thường trong lúc này. Nhấn Ctrl+C để dừng sớm.")

    if is_replay:
        sniffer, session = create_replay_sniffer(args.pcap_input, args.output, args.extractor)
    elif args.extractor == 'legacy':
        sniffer, session = create_sniffer(
            input_file=None,
            input_interface=args.interface,
            output_mode="csv",
            output=args.output,
            input_directory=None,
            fields=None,
            verbose=True,
        )
    else:
        session = make_session(args.output, args.extractor)
        _start_periodic_gc(session, interval=GC_INTERVAL)
        sniffer = AsyncSniffer(iface=args.interface, filter='ip and (tcp or udp)',
                               prn=session.process, store=False)
    def finish_capture():
        gc_stop = getattr(session, "_gc_stop", None)
        if gc_stop:
            gc_stop.set()
            session._gc_thread.join(timeout=3)
        # Never race a still-running capture thread with final CSV export.
        if sniffer.thread and sniffer.thread.is_alive():
            raise RuntimeError('Thread capture còn chạy; chưa thể ghi nốt an toàn.')
        print('[capture] receiving_stopped', flush=True)
        # Project v1 ghi CSV khi chạm timeout (duration >=90s / idle >=240s),
        # hoặc khi dừng và flush; chưa triển khai TCP close handshake riêng.
        # Dừng sớm (ví dụ test vài chục giây) mà
        # không gọi flush_flows() thì mọi flow còn "đang mở" (phần lớn traffic
        # HTTPS/keep-alive) sẽ KHÔNG được ghi ra — file CSV trông như trống dù đã bắt
        # được rất nhiều gói tin. scapy's AsyncSniffer.stop() không tự gọi việc này.
        n_remaining = len(session.get_flows())
        session.flush_flows()
        if args.extractor != 'legacy':
            print(f'[capture] accepted_packets={session.packets_count} exported_packets={session.n_exported_packets} '
                  f'exported_flows={session.n_exported} ignored_packets={session.n_ignored}')
        print(f"Đã ép ghi nốt {n_remaining} flow còn đang mở lúc dừng.")
        print(f"Đã dừng. Kiểm tra file: {args.output}")

    wait_for_capture(sniffer, 0 if is_replay else args.seconds, cleanup=finish_capture)
    if is_replay:
        print("\nĐã đọc hết file pcap.")


if __name__ == "__main__":
    main()

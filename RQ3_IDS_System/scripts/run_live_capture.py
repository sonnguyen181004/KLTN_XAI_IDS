"""Bắt traffic thật bằng CICFlowMeter 0.5.0, GỌI THẲNG hàm `create_sniffer()` bằng
keyword argument — né một lỗi thật của thư viện gốc: `cicflowmeter.sniffer.main()`
gọi `create_sniffer(...)` bằng tham số VỊ TRÍ nhưng thứ tự không khớp chữ ký hàm
(`args.verbose` bị nhét nhầm vào tham số `fields`, gây
`AttributeError: 'bool' object has no attribute 'split'`). Dùng keyword argument
ở đây thì không bị ảnh hưởng bởi lỗi thứ tự đó.

Chạy (cần quyền Administrator để bắt gói tin trên Windows):
  RQ3_IDS_System/.venv_capture/Scripts/python.exe RQ3_IDS_System/scripts/run_live_capture.py --interface "Wi-Fi" --output RQ3_IDS_System/data/real_capture.csv --seconds 90
"""
from __future__ import annotations

import argparse
import sys
import time

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from cicflowmeter.sniffer import create_sniffer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interface", required=True, help='Tên interface, ví dụ "Wi-Fi" (xem bằng Get-NetAdapter)')
    parser.add_argument("--output", required=True, help="Đường dẫn file CSV để ghi flow ra")
    parser.add_argument("--seconds", type=int, default=0, help="Tự dừng sau N giây (0 = chạy tới khi Ctrl+C)")
    args = parser.parse_args()

    print(f"Bắt đầu bắt traffic trên interface '{args.interface}', ghi ra: {args.output}")
    print("Hãy mở trình duyệt, lướt web bình thường trong lúc này. Nhấn Ctrl+C để dừng sớm.")

    sniffer, session = create_sniffer(
        input_file=None,
        input_interface=args.interface,
        output_mode="csv",
        output=args.output,
        input_directory=None,
        fields=None,
        verbose=True,
    )
    sniffer.start()

    try:
        if args.seconds > 0:
            time.sleep(args.seconds)
            print(f"\nĐã đủ {args.seconds} giây, tự dừng...")
            sniffer.stop()
        else:
            sniffer.join()
    except KeyboardInterrupt:
        print("\nNhận Ctrl+C, đang dừng...")
        sniffer.stop()
    finally:
        sniffer.join()
        gc_stop = getattr(session, "_gc_stop", None)
        if gc_stop:
            gc_stop.set()
        # QUAN TRỌNG: CICFlowMeter chỉ ghi 1 flow ra CSV khi flow đã "đóng" (FIN/RST)
        # hoặc hết hạn (idle/duration timeout). Dừng sớm (ví dụ test vài chục giây) mà
        # không gọi flush_flows() thì mọi flow còn "đang mở" (phần lớn traffic
        # HTTPS/keep-alive) sẽ KHÔNG được ghi ra — file CSV trông như trống dù đã bắt
        # được rất nhiều gói tin. scapy's AsyncSniffer.stop() không tự gọi việc này.
        n_remaining = len(session.get_flows())
        session.flush_flows()
        print(f"Đã ép ghi nốt {n_remaining} flow còn đang mở lúc dừng.")
        print(f"Đã dừng. Kiểm tra file: {args.output}")


if __name__ == "__main__":
    main()

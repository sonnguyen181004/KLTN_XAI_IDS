"""Tạo 1 file .pcap nhỏ, hợp lệ, KHÔNG cần Npcap/quyền Administrator (chỉ dựng gói
tin giả bằng scapy rồi lưu ra file, không bắt gói thật nào) — dùng để test tab
"Phát lại PCAP" của Dashboard (bước 13) khi chưa có sẵn file pcap thật nào.

Chạy bằng Python của .venv_capture (cần scapy):
  RQ3_IDS_System/.venv_capture/Scripts/python.exe RQ3_IDS_System/scripts/make_synthetic_pcap.py [đường_dẫn_ra]
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from scapy.all import IP, TCP, Raw, wrpcap


def main():
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "data" / "test_synthetic.pcap"

    t0 = time.time()
    fwd = dict(src="10.0.0.5", dst="10.0.0.9")
    bwd = dict(src="10.0.0.9", dst="10.0.0.5")
    # Giả lập 1 cuộc trao đổi TCP đơn giản: SYN, SYN-ACK, ACK, PSH+data, FIN, FIN.
    p1 = IP(**fwd) / TCP(sport=51000, dport=80, flags="S", seq=100); p1.time = t0
    p2 = IP(**bwd) / TCP(sport=80, dport=51000, flags="SA", seq=200, ack=101); p2.time = t0 + 0.01
    p3 = IP(**fwd) / TCP(sport=51000, dport=80, flags="A", seq=101, ack=201); p3.time = t0 + 0.02
    p4 = IP(**fwd) / TCP(sport=51000, dport=80, flags="PA", seq=101, ack=201) / Raw(b"GET / HTTP/1.1"); p4.time = t0 + 0.03
    p5 = IP(**bwd) / TCP(sport=80, dport=51000, flags="FA", seq=201, ack=115); p5.time = t0 + 0.05
    p6 = IP(**fwd) / TCP(sport=51000, dport=80, flags="FA", seq=115, ack=202); p6.time = t0 + 0.06
    pkts = [p1, p2, p3, p4, p5, p6]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wrpcap(str(out_path), pkts)
    print(f"Da tao {out_path}, {len(pkts)} goi tin.")


if __name__ == "__main__":
    main()

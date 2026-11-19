"""Bước 2: truy nguyên chênh lệch packet giữa PCAP và flow Java (profile M0, upstream 98a5eba).

Cách làm: mô phỏng lại đúng máy trạng thái FlowGenerator.addPacket của bản Java (timeout 120 s,
nhánh FIN, nhánh RST, bỏ packet khi flow đã nhận FIN, chỉ ghi flow còn mở cuối file nếu có hơn 1 packet)
trên bảng packet TShark, rồi so số flow và số packet theo từng cặp IP:cổng với CSV Java thật.
Nếu khớp, chênh lệch được giải thích bằng quy tắc của extractor, không phải mất gói khi capture.
"""
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
SRC = ROOT / "Java_CICFlowMeter_M0_Trial/output/attack_load_report_20261118"
TIMEOUT = 120.0
man = pd.read_csv(HERE / "manifests/pcaps.csv")


def simulate(p):
    cur, out, dropped = {}, [], defaultdict(int)
    def emit(f):
        out.append(f)
    for r in p.itertuples(index=False):
        a, b = (r.src, r.sport), (r.dst, r.dport)
        key = (min(a, b), max(a, b))
        f = cur.get(key)
        if f is None:
            cur[key] = dict(key=key, src=a, start=r.t, n=1, fwdfin=0, bwdfin=0, close="open")
            continue
        if r.t - f["start"] > TIMEOUT:
            if f["n"] > 1:
                f["close"] = "timeout"; emit(f)
            else:
                dropped["timeout_single"] += 1
            cur[key] = dict(key=key, src=f["src"], start=r.t, n=1, fwdfin=0, bwdfin=0, close="open")
        elif r.fin:
            if a == f["src"]:
                f["fwdfin"] += 1
                if f["fwdfin"] == 1:
                    f["n"] += 1
                    if f["bwdfin"] == 1:  # mã gốc: getBwdFINFlags()+getBwdFINFlags()==2
                        f["close"] = "fin"; emit(f); del cur[key]
                else:
                    dropped["repeat_fwd_fin"] += 1
            else:
                f["bwdfin"] += 1
                if f["bwdfin"] == 1:  # luôn đúng ở FIN chiều về đầu tiên, nên flow đóng ngay
                    f["n"] += 1; f["close"] = "fin"; emit(f); del cur[key]
                else:
                    dropped["repeat_bwd_fin"] += 1
        elif r.rst:
            f["n"] += 1; f["close"] = "rst"; emit(f); del cur[key]
        elif (a == f["src"] and f["fwdfin"] == 0) or f["bwdfin"] == 0:
            f["n"] += 1
        else:
            dropped["after_fin"] += 1
    for f in cur.values():
        if f["n"] > 1:
            f["close"] = "end_of_file"; emit(f)
        else:
            dropped["single_packet_open_at_end"] += 1
    return out, dict(dropped)


report = {}
for m in man.itertuples():
    key = m.pcap.split("/")[-1].replace(".pcapng", "").strip()
    pk = pd.read_csv(SRC / f"{key}_packets.csv")
    pk = pk.rename(columns={"frame.time_epoch": "t", "ip.src": "src", "ip.dst": "dst", "tcp.srcport": "sport", "tcp.dstport": "dport",
                            "tcp.flags.fin": "fin", "tcp.flags.reset": "rst"})
    pk["fin"] = pk["fin"].astype(str).eq("True"); pk["rst"] = pk["rst"].astype(str).eq("True")
    pk = pk.sort_values("t", kind="stable")
    sim, dropped = simulate(pk[["t", "src", "dst", "sport", "dport", "fin", "rst"]])

    j = pd.read_csv(SRC / "M0" / f"{key}.pcap_Flow.csv")
    j.columns = j.columns.str.strip()
    lab = j[j["Src IP"].isin(["192.168.11.133", "192.168.11.134"]) & j["Dst IP"].isin(["192.168.11.133", "192.168.11.134"]) & j["Protocol"].eq(6)]
    jk = lab.apply(lambda r: tuple(sorted([(r["Src IP"], int(r["Src Port"])), (r["Dst IP"], int(r["Dst Port"]))])), axis=1)
    jn = (lab["Total Fwd Packet"] + lab["Total Bwd packets"]).groupby(jk).agg(["sum", "count"])
    sn = pd.DataFrame([(f["key"], f["n"]) for f in sim], columns=["k", "n"]).groupby("k")["n"].agg(["sum", "count"])
    allk = jn.index.union(sn.index)
    jn, sn = jn.reindex(allk, fill_value=0), sn.reindex(allk, fill_value=0)
    mism = int(((jn["sum"] != sn["sum"]) | (jn["count"] != sn["count"])).sum())
    closes = pd.Series([f["close"] for f in sim]).value_counts().to_dict()
    report[m.run_id] = dict(pcap_lab_tcp_packets=len(pk), java_flows=len(lab), java_packets=int(jn["sum"].sum()),
                            sim_flows=len(sim), sim_packets=int(sn["sum"].sum()), endpoint_pairs=len(allk),
                            pairs_mismatch_java_vs_sim=mism, packets_not_in_any_flow=len(pk) - int(jn["sum"].sum()),
                            sim_dropped_by_rule=dropped, sim_close_reason=closes)
    print(m.run_id, report[m.run_id], flush=True)

json.dump(report, open(HERE / "results/extraction_audit/packet_accounting.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

"""Lấy flow realtime (nguồn feeder_live) từ DB RQ3, chỉ đọc, để dựng bộ T3.
Giữ flow có IP máy người dùng ở một đầu, bỏ multicast và broadcast. Không lấy flow pcap_replay.
Nhãn Benign chỉ được xác nhận cho phiên nào có ghi chú hoạt động trong results/t3_session_log.csv."""
import ipaddress
import json
import sqlite3
import pandas as pd
from rq4_common import *

DB = REPO / "RQ3_IDS_System" / "data" / "ids_system.db"
USER_IPS = {"172.16.1.163", "172.20.10.2"}     # Wi-Fi nhà và điểm phát sóng điện thoại, xem phiên trong DB


def is_local_noise(ip: str) -> bool:
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return a.is_multicast or ip.endswith(".255") or ip == "255.255.255.255"


con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
rows = con.execute("""select f.flow_id, f.capture_run_id, f.received_at, f.src_ip, f.dst_ip, f.src_port, f.features_json
                      from FlowRecord f where f.source='feeder_live' order by f.received_at""").fetchall()
recs = []
for fid, run, ts, s, d, sp, fj in rows:
    feats = json.loads(fj)
    own = s in USER_IPS or d in USER_IPS
    recs.append(dict(flow_id=fid, run=run, received_at=ts, src_ip=s, dst_ip=d, own=own, noise=is_local_noise(s) or is_local_noise(d),
                     **{k: feats[k] for k in FEATURES}))
df = pd.DataFrame(recs)
df["keep"] = df.own & ~df.noise
print("flow feeder_live:", len(df), "| của máy người dùng, không multicast:", int(df.keep.sum()))
print(df.groupby("run").agg(flows=("keep", "size"), giu=("keep", "sum"), dau=("received_at", "min"), cuoi=("received_at", "max")).to_string())
df[df.keep].drop(columns=["own", "noise", "keep"]).to_parquet(DATA / "t3_candidates.parquet", index=False)
df.groupby("run").agg(flows=("keep", "size"), kept=("keep", "sum"), start=("received_at", "min"), end=("received_at", "max")).reset_index().assign(
    activity="", benign_confirmed="").to_csv(RESULTS / "t3_session_log_template.csv", index=False, encoding="utf-8-sig")

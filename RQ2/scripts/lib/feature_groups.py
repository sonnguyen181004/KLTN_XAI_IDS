"""Heuristic grouping of CICIDS2018's 78 flow features into semantic families.

Used by GĐ7 (Agreement) to re-run Jaccard at group level: bất đồng do SHAP và LIME chọn
hai cột khác nhau TRONG CÙNG MỘT NHÓM (ví dụ Fwd Pkt Len Max vs Pkt Len Mean) sẽ biến mất
sau khi gộp nhóm. Đây là một quy ước đơn giản dựa trên tên cột — không phải một bảng tri
thức chuẩn hoá — ghi rõ ở đây để không bị hiểu nhầm là kiểm định thống kê.
"""
from __future__ import annotations

RULES: list[tuple[str, str]] = [
    ("IAT", "IAT"),
    ("Flag", "TCP_Flags"),
    ("Win Byts", "Window_Size"),
    ("Header Len", "Header_Len"),
    ("Active", "Active_Idle"),
    ("Idle", "Active_Idle"),
    ("Byts/b", "Rate"),
    ("Pkts/b", "Rate"),
    ("Blk Rate", "Rate"),
    ("Byts/s", "Rate"),
    ("Pkts/s", "Rate"),
    ("Pkt Len", "Packet_Size"),
    ("Seg Size", "Packet_Size"),
    ("Pkt Size", "Packet_Size"),
    ("Subflow", "Packet_Byte_Totals"),
    ("Tot Fwd Pkts", "Packet_Byte_Totals"),
    ("Tot Bwd Pkts", "Packet_Byte_Totals"),
    ("TotLen Fwd Pkts", "Packet_Byte_Totals"),
    ("TotLen Bwd Pkts", "Packet_Byte_Totals"),
    ("Fwd Act Data Pkts", "Packet_Byte_Totals"),
    ("Flow Duration", "Duration"),
    ("Dst Port", "Port"),
    ("Protocol", "Protocol"),
    ("Down/Up Ratio", "Ratio"),
]

DEFAULT_GROUP = "Other"


def feature_to_group(feature_name: str) -> str:
    for substr, group in RULES:
        if substr in feature_name:
            return group
    return DEFAULT_GROUP


def build_group_map(feature_names: list[str]) -> dict[str, str]:
    return {f: feature_to_group(f) for f in feature_names}

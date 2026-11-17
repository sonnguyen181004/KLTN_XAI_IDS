"""Compare two frozen extractors without assuming CSV row order or ground truth."""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "RQ4_Retrain_Compare" / "scripts"))
sys.path.insert(0, str(ROOT / "RQ3_IDS_System" / "app"))
from rq4_common import FEATURES, FEATURE_MAP  # noqa: E402
from feeder import row_to_payload  # noqa: E402


def normalized_frame(path, kind):
    df = pd.read_csv(path, low_memory=False)
    if kind == "java":
        x = df[[FEATURE_MAP[n] for n in FEATURES]].copy()
        x.columns = FEATURES
        identity = ("Src IP", "Src Port", "Dst IP", "Dst Port", "Protocol", "Timestamp")
    else:
        x = pd.DataFrame([row_to_payload(row, list(df.columns), True)
                          for row in df.to_dict("records")]).reindex(columns=FEATURES)
        identity = ("src_ip", "src_port", "dst_ip", "dst_port", "protocol", "timestamp")
    x = x.apply(pd.to_numeric, errors="coerce")
    return df, x, identity


def key(row, fields):
    a, b, c, d, p, t = fields
    time = pd.to_datetime(row[t], errors="coerce", dayfirst=t == "Timestamp")
    return (str(row[a]), int(row[b]), str(row[c]), int(row[d]), int(row[p]),
            str(time.floor("s")) if pd.notna(time) else "unknown")


def main():
    out = {}
    base = Path(__file__).parent / "output"
    for name in ("test", "tesst2"):
        j, jx, ji = normalized_frame(base / f"{name}.pcap_Flow.csv", "java")
        p, px, pi = normalized_frame(base / f"{name}_python.csv", "python")
        groups = [defaultdict(list), defaultdict(list)]
        for rows, fields, group in ((j, ji, groups[0]), (p, pi, groups[1])):
            for i, row in rows.iterrows():
                group[key(row, fields)].append(i)
        pairs = [(groups[0][k][0], groups[1][k][0]) for k in groups[0].keys() & groups[1].keys()
                 if len(groups[0][k]) == len(groups[1][k]) == 1]
        diffs = []
        for feature in FEATURES:
            a = np.array([jx.at[i, feature] for i, _ in pairs], dtype=float)
            b = np.array([px.at[i, feature] for _, i in pairs], dtype=float)
            valid = np.isfinite(a) & np.isfinite(b)
            if valid.any():
                equal = np.isclose(a[valid], b[valid], rtol=1e-5, atol=1e-5)
                diffs.append(dict(feature=feature, compared=int(valid.sum()), different=int((~equal).sum()),
                                  median_abs_diff=float(np.median(np.abs(a[valid] - b[valid])))))
        predictions = []
        for kind in ("java", "python"):
            path = base / f"{name}_{kind}_m0.csv"
            frame = pd.read_csv(path) if path.exists() else pd.DataFrame()
            fields = ji if kind == "java" else pi
            labels = defaultdict(list)
            for _, row in frame.iterrows():
                labels[key(row, fields)].append(row["predicted_label"])
            predictions.append(labels)
        label_pairs = [(predictions[0][k][0], predictions[1][k][0])
                       for k in predictions[0].keys() & predictions[1].keys()
                       if len(predictions[0][k]) == len(predictions[1][k]) == 1]
        out[name] = dict(java_rows=len(j), python_rows=len(p),
                         java_packet_sum=int((jx["Tot Fwd Pkts"] + jx["Tot Bwd Pkts"]).sum()),
                         python_packet_sum=int((px["Tot Fwd Pkts"] + px["Tot Bwd Pkts"]).sum()),
                         uniquely_matched_pairs=len(pairs),
                         unmatched_or_ambiguous_java=len(j)-len(pairs),
                         unmatched_or_ambiguous_python=len(p)-len(pairs),
                         m0_java_labels=dict(Counter(pd.read_csv(base / f"{name}_java_m0.csv")["predicted_label"])),
                         m0_python_labels=dict(Counter(pd.read_csv(base / f"{name}_python_m0.csv")["predicted_label"])),
                         uniquely_matched_prediction_pairs=len(label_pairs),
                         matched_prediction_disagreements=sum(a != b for a, b in label_pairs),
                         features_with_any_difference=sum(v["different"] > 0 for v in diffs),
                         top_feature_differences=sorted(diffs, key=lambda v: v["different"], reverse=True)[:20])
    target = base / "extractor_comparison.json"
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

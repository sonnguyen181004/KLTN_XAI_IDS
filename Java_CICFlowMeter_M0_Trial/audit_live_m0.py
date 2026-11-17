"""Recompute M0 predictions and SHAP for a saved Java live CSV, without mutation."""
import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'RQ4_Retrain_Compare/scripts'))
sys.path.insert(0, str(ROOT / 'RQ3_IDS_System/app'))
from rq4_common import FEATURE_MAP
from explain_shap import ShapExplainer

parser = argparse.ArgumentParser()
parser.add_argument('csv', type=Path)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
data = args.csv.read_bytes()
raw = pd.read_csv(io.BytesIO(data))
model_path = ROOT / 'RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl'
model = joblib.load(model_path)
classes = joblib.load(model_path.with_name('label_encoder.pkl')).classes_
names = list(model.feature_names_in_)
x = raw[[FEATURE_MAP[n] for n in names]].apply(pd.to_numeric, errors='coerce')
x.columns = names
valid = np.isfinite(x.to_numpy()).all(axis=1)
proba = model.predict_proba(x.loc[valid])
labels = pd.Series(classes[proba.argmax(axis=1)], index=x.index[valid])
shap = ShapExplainer(model, list(classes))
report = {'source': args.csv.name, 'source_sha256': hashlib.sha256(data).hexdigest(),
          'model_sha256': hashlib.sha256(model_path.read_bytes()).hexdigest(),
          'csv_rows': len(raw), 'valid_rows': int(valid.sum()),
          'invalid_rows': int((~valid).sum()), 'labels': labels.value_counts().to_dict(),
          'ground_truth': 'User reports this session contains normal traffic; no per-flow independent labels',
          'per_label': {}, 'examples': []}
for label in labels.unique():
    idx = labels.index[labels == label]
    report['per_label'][label] = {'fin_values': x.loc[idx, 'FIN Flag Cnt'].value_counts().to_dict(),
        'destination_ports': raw.loc[idx, 'Dst Port'].value_counts().to_dict()}
    if label == 'Benign':
        continue
    top_positive = Counter()
    max_error = 0
    for i in idx:
        explanation = shap.explain(x.loc[[i]], label, top_k=5)
        max_error = max(max_error, explanation['additivity_error'])
        positives = [v for v in explanation['top_k'] if v['phi'] > 0]
        if positives:
            top_positive[max(positives, key=lambda v: v['phi'])['feature']] += 1
        if list(idx).index(i) < 3:
            report['examples'].append({'flow_id': int(i)+1, 'label': label,
                'confidence': float(proba[list(labels.index).index(i)].max()),
                'features': {n: float(x.at[i,n]) for n in ['FIN Flag Cnt','Fwd Pkt Len Max','Fwd Seg Size Min','ACK Flag Cnt','Dst Port','Flow Duration']},
                'shap': explanation})
    report['per_label'][label]['top_positive_shap_feature_counts'] = dict(top_positive)
    report['per_label'][label]['max_additivity_error'] = max_error
log_path = args.csv.with_suffix('.log')
if log_path.exists():
    log = log_path.read_text(encoding='utf-8', errors='replace')
    report['java_log_evidence'] = [line for line in log.splitlines() if line.startswith((':liveTrial', 'capture_started=', 'accepted_packets=', 'BUILD SUCCESSFUL'))]
args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))

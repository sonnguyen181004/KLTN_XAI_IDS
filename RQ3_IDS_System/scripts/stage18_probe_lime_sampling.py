"""Read-only diagnostic experiment, NOT a replacement for locked RQ2 LIME.

Compare background-centered and instance-centered sampling with three seeds.
Only in-memory explainer objects change; no API calls or DB/config writes.
"""
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from itertools import combinations

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
RQ3 = ROOT / 'RQ3_IDS_System'
sys.path.insert(0, str(RQ3 / 'app'))
from predict import Detector
from normalize import normalize_flow
from explain_lime import LimeExplainer


def main():
    cfg = yaml.safe_load((RQ3 / 'config.yaml').read_text(encoding='utf-8'))
    with sqlite3.connect((ROOT / cfg['paths']['sqlite_db']).as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        rows = [dict(r) for r in db.execute('''SELECT f.flow_id, f.features_json,
            f.run_name, a.alert_id, p.predicted_label FROM FlowRecord f
            JOIN Prediction p ON p.flow_id=f.flow_id
            JOIN AlertRecord a ON a.flow_id=f.flow_id
            WHERE f.source='pcap_replay' ORDER BY f.flow_id''')]
    detector = Detector(ROOT / cfg['paths']['model'], ROOT / cfg['paths']['label_encoder'])
    background = np.load(RQ3 / 'data/lime_background.npy')
    for around in (False, True):
        lime = LimeExplainer(detector.model, detector.feature_names, detector.class_names,
                             background, cfg['lime'], cfg['seed'])
        lime.explainer.sample_around_instance = around
        for record in rows:
            row = normalize_flow(json.loads(record['features_json']), detector.feature_names)
            label = record['predicted_label']
            index = detector.class_names.index(label)
            probability = float(lime._predict_proba_fn(row.to_numpy())[0, index])
            results, tops = [], []
            for offset in (0, 1, 2):
                extra = {}
                original_fit = lime.explainer.base.explain_instance_with_data
                original_predict = lime._predict_proba_fn

                def inspect_fit(data, labels, distances, target, *args, **kwargs):
                    result = original_fit(data, labels, distances, target, *args, **kwargs)
                    extra['local_prediction'] = float(np.asarray(result[3]).reshape(-1)[0])
                    extra['neighborhood_probability_std'] = float(labels[1:, target].std())
                    return result

                def inspect_predict(x):
                    # Protocol and TCP flags are discrete, irrespective of count/binary convention.
                    cols = [i for i, name in enumerate(detector.feature_names)
                            if 'Flag' in name or name == 'Protocol']
                    samples = np.asarray(x)[1:, cols]
                    extra['fraction_samples_with_fractional_flags_or_protocol'] = float(
                        np.any(np.abs(samples - np.round(samples)) > 1e-8, axis=1).mean())
                    return original_predict(x)

                lime.explainer.base.explain_instance_with_data = inspect_fit
                lime._predict_proba_fn = inspect_predict
                seed = int(hashlib.sha256(record['alert_id'].encode()).hexdigest()[:8], 16) + offset
                try:
                    result = lime.explain(row, label, seed)
                finally:
                    lime.explainer.base.explain_instance_with_data = original_fit
                    lime._predict_proba_fn = original_predict
                diag = result['diagnostics']
                tops.append({v['feature_desc'] for v in result['top_k']})
                results.append(dict(seed_offset=offset, status=result['status'],
                    ess=diag['effective_sample_size'], raw_r2=diag['raw_local_r2'],
                    local_error=abs(extra['local_prediction'] - probability), **extra))
            overlap = [len(a & b) / len(a | b) for a, b in combinations(tops, 2) if a | b]
            print(json.dumps(dict(flow=record['flow_id'], run=record['run_name'],
                sample_around_instance=around, probability=probability, results=results,
                mean_top5_jaccard=float(np.mean(overlap)) if overlap else None)), flush=True)


if __name__ == '__main__':
    main()

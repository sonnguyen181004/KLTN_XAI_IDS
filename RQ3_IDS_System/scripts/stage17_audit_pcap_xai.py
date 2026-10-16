"""Read-only audit of stored PCAP runs. No API calls or production DB writes.

Re-extract originals to temporary files; recompute model, SHAP and LIME in memory.
Printed JSON is diagnostic evidence, not an accuracy evaluation without labels.
"""
import csv
import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
RQ3 = ROOT / 'RQ3_IDS_System'
sys.path.insert(0, str(RQ3 / 'app'))
from predict import Detector
from normalize import normalize_flow
from explain_shap import ShapExplainer
from explain_lime import LimeExplainer
from feeder import row_to_payload


def main():
    cfg = yaml.safe_load((RQ3 / 'config.yaml').read_text(encoding='utf-8'))
    conn = sqlite3.connect((ROOT / cfg['paths']['sqlite_db']).as_uri() + '?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    records = [dict(row) for row in conn.execute('''SELECT f.*, p.predicted_label,
        p.probabilities_json, p.model_version, a.alert_id, r.shap_top5_json,
        r.lime_top5_json, r.lime_diagnostics_json
        FROM FlowRecord f JOIN Prediction p ON p.flow_id=f.flow_id
        LEFT JOIN AlertRecord a ON a.flow_id=f.flow_id
        LEFT JOIN Reliability r ON r.alert_id=a.alert_id
        WHERE f.source='pcap_replay' ORDER BY f.received_at, f.flow_id''')]
    conn.close()
    detector = Detector(ROOT / cfg['paths']['model'], ROOT / cfg['paths']['label_encoder'])
    background = np.load(RQ3 / 'data/lime_background.npy')
    lime = LimeExplainer(detector.model, detector.feature_names, detector.class_names, background, cfg['lime'], cfg['seed'])
    shap = ShapExplainer(detector.model, detector.class_names)
    runs = defaultdict(list)
    alerts, controls = [], []
    prediction_errors = []
    max_probability_error = 0.0
    for record in records:
        runs[(record['capture_run_id'], record['run_name'])].append(record)
        features = json.loads(record['features_json'])
        normalized = normalize_flow(features, detector.feature_names)
        result = detector.predict_flow(normalized)
        old = json.loads(record['probabilities_json'])
        error = max(abs(old[k] - result['probabilities'][k]) for k in old)
        max_probability_error = max(max_probability_error, error)
        if error > 1e-7 or result['predicted_label'] != record['predicted_label'] or record['model_version'] != detector.model_version:
            prediction_errors.append(record['flow_id'])
        if not record['alert_id']:
            continue
        explanation = shap.explain(normalized, result['predicted_label'])
        old_shap = json.loads(record['shap_top5_json']) if record['shap_top5_json'] else []
        shap_matches = len(old_shap) == len(explanation['top_k']) and all(
            a['feature'] == b['feature'] and abs(a['phi'] - b['phi']) < 1e-7 and a['value'] == b['value']
            for a, b in zip(old_shap, explanation['top_k']))
        seed = int(hashlib.sha256(record['alert_id'].encode()).hexdigest()[:8], 16)
        outcome = lime.explain(normalized, result['predicted_label'], seed)
        diag = outcome['diagnostics']
        old_diag = json.loads(record['lime_diagnostics_json']) if record['lime_diagnostics_json'] else None
        scaled = (normalized.to_numpy()[0] - lime.explainer.scaler.mean_) / lime.explainer.scaler.scale_
        top = np.argsort(-np.abs(scaled))[:5]
        alert = dict(flow_id=record['flow_id'], run=record['run_name'], label=result['predicted_label'],
            probability=result['probabilities'][result['predicted_label']],
            shap_matches_stored=shap_matches, shap_additivity_error=explanation['additivity_error'],
            shap_top=explanation['top_k'], lime_status=outcome['status'],
            lime_nonzero=diag['nonzero_weights'], lime_ess=diag['effective_sample_size'],
            max_other_weight=diag['max_other_weight'], min_other_distance=diag['min_other_distance'],
            raw_r2=diag['raw_local_r2'], stored_lime_matches=(old_diag == diag if old_diag else None),
            outliers=[dict(feature=str(detector.feature_names[i]), value=float(normalized.iloc[0,i]),
                           background_min=float(background[:,i].min()), background_max=float(background[:,i].max()),
                           standardized_value=float(scaled[i])) for i in top])
        alerts.append(alert)
        print('ALERT ' + json.dumps(alert, ensure_ascii=False), flush=True)
    # Controls demonstrate whether the exact same implementation can produce LIME.
    clean = pd.read_csv(RQ3 / 'data/clean_holdout_set.csv')
    for label, group in clean.groupby('label_true'):
        row = normalize_flow({name: float(group.iloc[0][name]) for name in detector.feature_names}, detector.feature_names)
        result = detector.predict_flow(row)
        outcome = lime.explain(row, result['predicted_label'], 42)
        controls.append(dict(reference_label=label, predicted_label=result['predicted_label'],
            status=outcome['status'], ess=outcome['diagnostics']['effective_sample_size'],
            nonzero=outcome['diagnostics']['nonzero_weights'], r2=outcome['local_r2']))
    extraction = []
    capture_python = RQ3 / '.venv_capture/Scripts/python.exe'
    for (run_id, name), saved in runs.items():
        original = ROOT / Path(name).name
        if not original.is_file() or not capture_python.is_file():
            extraction.append(dict(run=name, skipped='Original PCAP or capture environment missing'))
            continue
        with tempfile.TemporaryDirectory(prefix='ids_pcap_audit_') as folder:
            output = Path(folder) / 'flows.csv'
            proc = subprocess.run([str(capture_python), str(RQ3 / 'scripts/run_live_capture.py'),
                '--pcap-input', str(original), '--output', str(output), '--extractor', 'legacy'], cwd=RQ3,
                capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if proc.returncode or not output.exists():
                raise RuntimeError(proc.stdout[-2000:] + proc.stderr[-2000:])
            with output.open(encoding='utf-8-sig', newline='') as stream:
                reader = csv.DictReader(stream)
                fresh = [(row, row_to_payload(row, reader.fieldnames, True)) for row in reader]
            unmatched = list(fresh)
            mismatches = []
            for record in saved:
                stored = json.loads(record['features_json'])
                found = None
                for idx, (row, payload) in enumerate(unmatched):
                    if row['src_ip'] != record['src_ip'] or row['dst_ip'] != record['dst_ip'] or int(row['src_port']) != record['src_port']:
                        continue
                    if np.allclose([stored[n] for n in detector.feature_names], [payload[n] for n in detector.feature_names], rtol=1e-10, atol=1e-8):
                        found = idx
                        break
                if found is None:
                    mismatches.append(record['flow_id'])
                else:
                    unmatched.pop(found)
            extraction.append(dict(run=name, run_id=run_id, stored_flows=len(saved), extracted_flows=len(fresh),
                matches=len(saved)-len(mismatches), mismatches=mismatches, unmatched_extracted=len(unmatched),
                source_sha256=hashlib.sha256(original.read_bytes()).hexdigest()))
    summary = dict(total_flows=len(records), predictions_match=len(records)-len(prediction_errors),
        max_probability_error=max_probability_error, prediction_errors=prediction_errors,
        alert_count=len(alerts), shap_match_count=sum(a['shap_matches_stored'] for a in alerts),
        max_shap_additivity_error=max((a['shap_additivity_error'] for a in alerts), default=0),
        lime_status_counts=dict(Counter(a['lime_status'] for a in alerts)),
        control_status_counts=dict(Counter(c['status'] for c in controls)), controls=controls, extraction=extraction)
    print('SUMMARY ' + json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()

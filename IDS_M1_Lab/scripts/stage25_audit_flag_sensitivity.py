"""HT2.1 diagnostic: inspect actual model splits and binarize flags in memory.

Offline only. Uses project-v2 PCAP extraction in a temporary directory; never
changes the production adapter, input files, model or DB. Not an accuracy/FPR
measurement and not a recommendation to change the feature contract.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
RQ3 = ROOT / 'RQ3_IDS_System'
sys.path.insert(0, str(RQ3 / 'app'))
from predict import Detector
from feeder import row_to_payload
from normalize import normalize_flow


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def audit():
    cfg = yaml.safe_load((RQ3 / 'config.yaml').read_text(encoding='utf-8'))
    model_path = ROOT / cfg['paths']['model']
    detector = Detector(model_path, ROOT / cfg['paths']['label_encoder'])
    flags = [name for name in detector.feature_names if 'Flag' in name]
    trees = detector.model.get_booster().trees_to_dataframe()
    splits = {name: sorted(trees.loc[trees.Feature == name, 'Split'].dropna().unique().tolist())
              for name in flags}
    # Numeric XGBoost splits route using value < threshold. For positive integer
    # counts, mapping to 1 preserves the branch if every used split is <=1.
    safe_splits = all(value <= 1 for thresholds in splits.values() for value in thresholds)
    report = dict(model_version=detector.model_version,
                  scope='In-memory flag sensitivity, no ground truth or accuracy claim',
                  flag_split_thresholds=splits,
                  positive_integer_to_one_preserves_all_flag_splits=safe_splits,
                  pcaps={}, sha256={})
    paths = [model_path, ROOT / cfg['paths']['label_encoder'], Path(__file__).resolve(),
             RQ3 / 'app/capture_adapter.py', RQ3 / 'scripts/run_live_capture.py',
             RQ3 / 'app/feeder.py', RQ3 / 'app/normalize.py']
    with tempfile.TemporaryDirectory(prefix='ids_flag_audit_') as folder:
        for name in ('test.pcapng', 'tesst2.pcapng'):
            pcap, output = ROOT / name, Path(folder) / (name + '.csv')
            paths.append(pcap)
            subprocess.run([str(RQ3 / '.venv_capture/Scripts/python.exe'),
                            str(RQ3 / 'scripts/run_live_capture.py'),
                            '--pcap-input', str(pcap), '--output', str(output),
                            '--extractor', 'project-v2'], check=True, capture_output=True,
                           timeout=120, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            frame = pd.read_csv(output)
            rows = [normalize_flow(row_to_payload(row, list(frame.columns), True),
                                   detector.feature_names)
                    for row in frame.to_dict('records')]
            if not rows:
                raise ValueError('PCAP produced no rows: ' + name)
            original = pd.concat(rows, ignore_index=True)
            values = original[flags].to_numpy()
            if not (np.isfinite(values).all() and (values >= 0).all()
                    and (values == np.floor(values)).all()):
                raise ValueError('Flag counts are not finite nonnegative integers')
            candidate = original.copy()
            candidate[flags] = (candidate[flags] > 0).astype(float)
            before = detector.model.predict_proba(original)
            after = detector.model.predict_proba(candidate)
            before_leaves = detector.model.apply(original)
            after_leaves = detector.model.apply(candidate)
            report['pcaps'][name] = dict(
                flows=len(original),
                changed_feature_rows=int(np.any(original.to_numpy() != candidate.to_numpy(), axis=1).sum()),
                changed_labels=int((before.argmax(axis=1) != after.argmax(axis=1)).sum()),
                max_probability_difference=float(np.max(np.abs(before - after))),
                identical_leaf_routes=bool(np.array_equal(before_leaves, after_leaves)),
                predicted_counts={label: int((before.argmax(axis=1) == i).sum())
                                  for i, label in enumerate(detector.class_names)
                                  if (before.argmax(axis=1) == i).any()})
    report['sha256'] = {str(path.relative_to(ROOT)): sha256(path) for path in paths}
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, help='Optional NEW aggregate evidence JSON; refuses overwrite')
    args = parser.parse_args()
    if args.output and args.output.exists():
        parser.error('Evidence output already exists; choose a new filename')
    result = audit()
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        with args.output.open('x', encoding='utf-8') as stream:
            stream.write(text + '\n')

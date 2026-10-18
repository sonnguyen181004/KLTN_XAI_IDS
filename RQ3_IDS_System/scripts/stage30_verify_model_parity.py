"""Main-environment worker for Stage30; no API or DB writes."""
import csv
import json
from pathlib import Path
import sys
import numpy as np
import yaml

RQ3 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RQ3/'app'))
from predict import Detector
from normalize import normalize_flow
from feeder import row_to_payload


def main(before, after):
    cfg = yaml.safe_load((RQ3/'config.yaml').read_text(encoding='utf-8'))
    detector = Detector(RQ3.parent/cfg['paths']['model'], RQ3.parent/cfg['paths']['label_encoder'])
    with open(before, encoding='utf-8', newline='') as stream:
        left = list(csv.DictReader(stream))
    with open(after, encoding='utf-8', newline='') as stream:
        right = list(csv.DictReader(stream))
    assert len(left) == len(right) and left
    for a, b in zip(left, right):
        x = normalize_flow(row_to_payload(a, list(a), True), detector.feature_names)
        y = normalize_flow(row_to_payload(b, list(b), True), detector.feature_names)
        np.testing.assert_array_equal(x, y)
        assert detector.predict_flow(x) == detector.predict_flow(y)
    print(json.dumps(dict(flows=len(left), exact_normalized_features=True,
                          exact_predictions=True, model_version=detector.model_version)))


if __name__ == '__main__':
    main(*sys.argv[1:])

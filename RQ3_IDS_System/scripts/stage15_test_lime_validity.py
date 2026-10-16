"""Numerical checks without model artifacts or live DB writes."""
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from explain_lime import LimeExplainer
from monitoring import decorate


class LinearProbability:
    def predict_proba(self, x):
        p = 1 / (1 + np.exp(-np.clip(np.asarray(x)[:, 0], -50, 50)))
        return np.column_stack([1 - p, p])


def main():
    cfg = dict(discretize_continuous=False, kernel_width=3.312, num_samples=1000, num_features=2)
    background = np.column_stack([np.random.RandomState(42).normal(size=2000), np.zeros(2000)])
    explainer = LimeExplainer(LinearProbability(), ['signal', 'constant'], ['Benign', 'Attack'], background, cfg, 42)
    normal = pd.DataFrame([[.5, 0]], columns=['signal', 'constant'])
    result = explainer.explain(normal, 'Attack', 7)
    assert result['status'] == 'ok' and result['local_r2'] > .5
    extreme = pd.DataFrame([[.5, 1e9]], columns=['signal', 'constant'])
    invalid = explainer.explain(extreme, 'Attack', 7)
    assert invalid['status'] == 'insufficient_neighborhood'
    assert invalid['top_k'] == [] and invalid['local_r2'] is None
    assert invalid['diagnostics']['nonzero_weights'] == 1
    assert explainer.explain(normal, 'Attack', 7) == result  # state restored after invalid call
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: explainer.explain(normal, 'Attack', 7), range(8)))
    assert all(item == result for item in results)
    class FlatProbability:
        def predict_proba(self, x):
            return np.tile([.5, .5], (len(x), 1))
    flat = LimeExplainer(FlatProbability(), ['signal', 'constant'], ['Benign', 'Attack'], background, cfg, 42)
    assert flat.explain(normal, 'Attack', 7)['status'] == 'zero_coefficients'
    legacy = decorate({'predicted_label': 'Attack', 'alert_id': 'old', 'lime_local_r2': 1.0,
                       'agreement_jaccard5': .1, 'lime_top5_json': '[{"feature_desc":"signal","weight":0}]'})
    assert legacy['lime_status'] == 'zero_coefficients' and legacy['lime_local_r2'] is None
    assert legacy['agreement_jaccard5'] is None
    print('PASS normal/degenerate/flat LIME, RNG restoration and concurrent reproducibility')


if __name__ == '__main__':
    main()

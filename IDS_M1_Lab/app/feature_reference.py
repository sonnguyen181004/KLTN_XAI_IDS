"""Descriptive comparisons only; never alter features, predictions or A/B rules."""
import numpy as np
import pandas as pd
from feature_help import describe


class FeatureReference:
    def __init__(self, feature_names, background, clean_path):
        self.names = list(feature_names)
        self.background = np.asarray(background)
        self.groups = {}
        if clean_path.exists():
            frame = pd.read_csv(clean_path)
            for label, group in frame.groupby('label_true'):
                self.groups[label] = group[self.names].to_numpy(dtype=float)

    @staticmethod
    def stats(values):
        if values is None or not len(values):
            return {'n': 0, 'p05': None, 'median': None, 'p95': None}
        low, median, high = np.quantile(values, [.05, .5, .95])
        return dict(n=len(values), p05=float(low), median=float(median), p95=float(high))

    def compare(self, flow):
        shap = {x['feature']: x['phi'] for x in flow.get('shap_top5') or []}
        # Current configuration disables discretization, so descriptions are feature names.
        lime = {x['feature_desc']: x['weight'] for x in flow.get('lime_top5') or []}
        valid_lime = flow.get('lime_status') == 'ok'
        result = []
        for i, name in enumerate(self.names):
            value = float(flow['features'][name])
            bg = self.background[:, i]
            scale = float(bg.std())
            constant = bool(np.ptp(bg) == 0)
            mismatch = constant and value != float(bg[0])
            help_info = describe(name)
            result.append(dict(feature=name, value=value, unit=help_info['unit'], meaning=help_info['meaning'],
                background=self.stats(bg), background_min=float(bg.min()), background_max=float(bg.max()),
                constant_background=constant, constant_mismatch=bool(mismatch),
                background_scaled_deviation=float((value - bg.mean()) / (scale if scale > 0 else 1)),
                benign=self.stats(self.groups['Benign'][:, i] if 'Benign' in self.groups else None),
                predicted_class=self.stats(self.groups[flow['predicted_label']][:, i] if flow['predicted_label'] in self.groups else None),
                shap_phi=shap.get(name), lime_weight=lime.get(name) if valid_lime else None))
        result.sort(key=lambda r: (r['constant_mismatch'], abs(r['background_scaled_deviation'])), reverse=True)
        return {'features': result, 'background_n': len(self.background),
                'background_source': 'lime_background.npy — mẫu nền train của LIME',
                'class_reference_source': 'clean_holdout_set.csv — tập B nhỏ có nhãn, không phải toàn bộ train',
                'predicted_label': flow['predicted_label'],
                'warning': 'Đối chứng mô tả, không phải ngưỡng phát hiện tấn công. Ngoài P05–P95 không chứng minh tấn công. Không có trong Top-5 không đồng nghĩa đóng góp bằng 0.'}

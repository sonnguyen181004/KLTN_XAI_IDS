"""Thử các cấu hình LIME trên 1 flow PCAP (chỉ trong lab M1, không đổi config.yaml)."""
import sys, os, copy, numpy as np, pandas as pd, yaml
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, 'app')
from feeder import CICFLOWMETER_COLUMN_MAP
from normalize import normalize_flow
from predict import Detector
from explain_lime import LimeExplainer
from explain_shap import ShapExplainer
cfg = yaml.safe_load(open('config.yaml', encoding='utf-8'))
d = Detector('models/m1_xgboost_model.pkl', 'models/m1_label_encoder.pkl')
row = pd.read_csv(sys.argv[1]).iloc[0].to_dict()
f = {CICFLOWMETER_COLUMN_MAP[k]: float(v) for k, v in row.items() if k in CICFLOWMETER_COLUMN_MAP}
n = normalize_flow(f, d.feature_names, convert_seconds_to_microseconds=True)
label = d.predict_flow(n)['predicted_label']; print('Nhãn M1:', label)
bg = np.load('data/lime_background.npy')
for kw, disc in [(3.312, False), (30, False), (300, False), (3000, False), (10000, False), (100000, False), (3.312, True), (30, True)]:
    c = copy.deepcopy(cfg['lime']); c['kernel_width'] = kw; c['discretize_continuous'] = disc
    r = LimeExplainer(d.model, d.feature_names, d.class_names, bg, c, cfg['seed']).explain(n, label, 12345, top_k=5)
    dg = r['diagnostics']
    top = [x['feature_desc'] for x in (r['top_k'] or dg.get('raw_top_k', []))][:5]
    print(f"kw={kw:>8} disc={disc!s:5} -> {r['status']:25} r2={r['local_r2']} n_eff={dg['effective_sample_size']:.1f} top={top}")

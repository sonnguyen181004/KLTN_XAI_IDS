"""Helper duoc phuc dung tu mo ta trong Bao_cao_RQ_SHAP_XGBoost.docx, muc "Do nhay truoc
nhieu thoi gian" (doan van: "Moi mau duoc co gian cac dai luong thoi gian khong am voi he
so s = 1 + aU, U deu trong [-1, 1], a bang 1%, 5% hoac 10%; cac toc do tuong ung chia cho
s."). File goc khong con trong repo; noi dung duoi day duoc viet lai dung theo mo ta do,
KHONG suy doan them co che khac.

TIME_COLUMNS: cac dai luong thoi gian khong am trong 78 feature (Flow Duration, cac IAT,
Active/Idle) - duoc NHAN voi he so s.
RATE_COLUMNS: cac dai luong toc do (so luong / thoi gian) tuong ung - duoc CHIA cho s de
giu nhat quan vat ly voi thoi gian da co gian (cung mot luong du lieu, thoi gian khac di
thi toc do phai doi nguoc chieu).

Chi ap dung cho gia tri > 0 (giu nguyen cac sentinel -1 hoac 0 the hien "khong ap dung"
trong CICFlowMeter, tranh tao gia tri phi thuc te).
"""
import numpy as np
import pandas as pd


TIME_COLUMNS = [
    "Flow Duration",
    "Flow IAT Mean", "Flow IAT Std", "Flow IAT Max", "Flow IAT Min",
    "Fwd IAT Tot", "Fwd IAT Mean", "Fwd IAT Std", "Fwd IAT Max", "Fwd IAT Min",
    "Bwd IAT Tot", "Bwd IAT Mean", "Bwd IAT Std", "Bwd IAT Max", "Bwd IAT Min",
    "Active Mean", "Active Std", "Active Max", "Active Min",
    "Idle Mean", "Idle Std", "Idle Max", "Idle Min",
]

RATE_COLUMNS = [
    "Flow Byts/s", "Flow Pkts/s", "Fwd Pkts/s", "Bwd Pkts/s",
    "Fwd Blk Rate Avg", "Bwd Blk Rate Avg",
]


def rescale_time(X, factors):
    """Co gian TIME_COLUMNS boi factors (nhan) va RATE_COLUMNS nguoc lai (chia), chi tren
    gia tri > 0. X: DataFrame (n_rows, n_features). factors: mang 1D dai n_rows, mot he so
    s moi dong (dung chung cho ca thoi gian va toc do trong dong do)."""
    factors = np.asarray(factors, dtype=float)
    if len(factors) != len(X):
        raise ValueError("factors phai co cung do dai voi X")
    out = X.copy()
    for col in TIME_COLUMNS:
        if col not in out.columns:
            continue
        mask = out[col].to_numpy() > 0
        if mask.any():
            out.loc[mask, col] = out.loc[mask, col].to_numpy() * factors[mask]
    for col in RATE_COLUMNS:
        if col not in out.columns:
            continue
        mask = out[col].to_numpy() > 0
        if mask.any():
            out.loc[mask, col] = out.loc[mask, col].to_numpy() / factors[mask]
    return out

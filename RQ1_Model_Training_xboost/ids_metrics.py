"""Binary IDS metrics from a multiclass confusion matrix.

Rows = truth, columns = predictions. Attack (any non-Benign class) is positive.
Rates are percentages; absent denominators yield NaN, never a misleading zero.
"""
import numpy as np


def ids_detection_metrics(cm, benign_idx):
    cm = np.asarray(cm)
    if cm.ndim != 2 or cm.shape[0] != cm.shape[1] or not cm.size:
        raise ValueError('Expected a non-empty square confusion matrix')
    if not isinstance(benign_idx, (int, np.integer)) or not 0 <= benign_idx < len(cm):
        raise ValueError('Invalid Benign index')
    if not np.isfinite(cm).all() or (cm < 0).any() or (cm != np.floor(cm)).any():
        raise ValueError('Expected finite nonnegative integer counts')
    tn = int(cm[benign_idx, benign_idx])
    fp = int(cm[benign_idx, :].sum()) - tn
    fn = int(cm[:, benign_idx].sum()) - tn
    tp = int(cm.sum()) - tn - fp - fn
    return dict(fp=fp, tn=tn, fn=fn, tp=tp,
                fpr_pct=100 * fp / (fp + tn) if fp + tn else float('nan'),
                fnr_pct=100 * fn / (fn + tp) if fn + tp else float('nan'))

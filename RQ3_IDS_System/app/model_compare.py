"""Đối chiếu song song hai mô hình trên cùng các flow đã lưu: M0 (mô hình RQ1, dữ liệu cũ) và M1 (mô hình RQ4, dữ liệu improved).

Không đổi API, DB hay pipeline chính. Chỉ đọc FlowRecord (chế độ chỉ đọc), tự dự đoán lại bằng cả hai mô hình rồi so.
Dùng lại Detector (app/predict.py) và ShapExplainer (app/explain_shap.py), nên SHAP của hai mô hình tính đúng cách RQ3 đang tính.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from explain_shap import ShapExplainer
from predict import Detector

REPO_ROOT = Path(__file__).resolve().parents[2]
RQ3_ROOT = Path(__file__).resolve().parents[1]
M1_DIR = REPO_ROOT / "RQ4_Retrain_Compare" / "models"
KEY_FEATURES = ["FIN Flag Cnt", "Fwd Pkt Len Max", "Fwd Seg Size Min", "Init Fwd Win Byts", "Init Bwd Win Byts", "Dst Port", "Tot Fwd Pkts", "Flow Duration"]


def load_config() -> dict:
    return yaml.safe_load((RQ3_ROOT / "config.yaml").read_text(encoding="utf-8"))


class ModelPair:
    """Giữ M0 và M1 cùng bộ giải thích SHAP của từng mô hình. Nạp một lần."""

    def __init__(self, cfg: dict | None = None, m1_model: Path | None = None, m1_encoder: Path | None = None):
        self.cfg = cfg or load_config()
        m0 = (REPO_ROOT / self.cfg["paths"]["model"], REPO_ROOT / self.cfg["paths"]["label_encoder"])
        m1 = (m1_model or M1_DIR / "m1_xgboost_model.pkl", m1_encoder or M1_DIR / "m1_label_encoder.pkl")
        for p in (*m0, *m1):
            if not Path(p).exists():
                raise FileNotFoundError(f"Thiếu file mô hình: {p}")
        self.det = {"M0": Detector(*m0), "M1": Detector(*m1)}
        self.shap = {k: ShapExplainer(d.model, d.class_names) for k, d in self.det.items()}
        z = self.cfg["hulk_fin_hint"]
        self.zone_rule = (z["min_fin_flag_cnt"], z["min_fwd_pkt_len_max"], z["below_fwd_seg_size_min"])

    def in_zone(self, df: pd.DataFrame) -> pd.Series:
        fin, ln, seg = self.zone_rule
        return (df["FIN Flag Cnt"] >= fin) & (df["Fwd Pkt Len Max"] >= ln) & (df["Fwd Seg Size Min"] < seg)

    def predict_table(self, flows: pd.DataFrame) -> pd.DataFrame:
        """flows: cột flow_id, source, flow_timestamp, label_true và 78 đặc trưng. Trả bảng nhãn và độ tin cậy của cả hai mô hình."""
        out = flows[["flow_id", "source", "flow_timestamp", "label_true"]].copy()
        for k, d in self.det.items():
            proba = d.model.predict_proba(flows[d.feature_names])
            idx = proba.argmax(1)
            out[f"{k}_label"] = np.array(d.class_names)[idx]
            out[f"{k}_conf"] = proba[np.arange(len(idx)), idx]
        out["in_zone"] = self.in_zone(flows).to_numpy()
        out["M0_attack"] = out["M0_label"] != "Benign"
        out["M1_attack"] = out["M1_label"] != "Benign"
        out["disagree"] = out["M0_label"] != out["M1_label"]
        return out

    def explain_flow(self, row: pd.DataFrame, top_k: int = 5) -> dict:
        """row: DataFrame 1 dòng với 78 cột. Trả nhãn, xác suất top 3 và SHAP top-k của từng mô hình."""
        res = {}
        for k, d in self.det.items():
            x = row[d.feature_names]
            pred = d.predict_flow(x)
            top3 = sorted(pred["probabilities"].items(), key=lambda kv: -kv[1])[:3]
            res[k] = dict(label=pred["predicted_label"], top3=top3,
                          shap=self.shap[k].explain(x, pred["predicted_label"], top_k=top_k), model_version=pred["model_version"])
        return res


def open_readonly(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True, timeout=10)


def load_flows(db_path: Path, source: str | None = None, limit: int = 500, run_id: str | None = None) -> pd.DataFrame:
    q = "SELECT flow_id, source, flow_timestamp, label_true, features_json FROM FlowRecord WHERE 1=1"
    params: list = []
    if source:
        q += " AND source = ?"
        params.append(source)
    if run_id:
        q += " AND capture_run_id = ?"
        params.append(run_id)
    q += " ORDER BY COALESCE(flow_timestamp, received_at) DESC LIMIT ?"
    params.append(int(limit))
    conn = open_readonly(db_path)
    try:
        rows = conn.execute(q, params).fetchall()
    finally:
        conn.close()
    meta = pd.DataFrame([r[:4] for r in rows], columns=["flow_id", "source", "flow_timestamp", "label_true"])
    feats = pd.DataFrame([json.loads(r[4]) for r in rows])
    return pd.concat([meta, feats], axis=1)


def list_runs(db_path: Path) -> list[tuple[str, str, str]]:
    """(capture_run_id, run_name, lần nhận đầu tiên), mới nhất trước. Rỗng nếu DB cũ chưa có cột lượt."""
    conn = open_readonly(db_path)
    try:
        return conn.execute("SELECT capture_run_id, COALESCE(run_name, ''), MIN(received_at) FROM FlowRecord "
                            "WHERE capture_run_id IS NOT NULL GROUP BY capture_run_id ORDER BY MIN(received_at) DESC").fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


def list_sources(db_path: Path) -> list[str]:
    conn = open_readonly(db_path)
    try:
        return [r[0] for r in conn.execute("SELECT DISTINCT source FROM FlowRecord ORDER BY 1").fetchall()]
    finally:
        conn.close()

"""Tầng 3 — Model phát hiện. Nạp lại nguyên model + encoder đã huấn luyện ở RQ1
(KHÔNG huấn luyện lại gì), nhận 1 dòng đã chuẩn hóa (từ app/normalize.py), trả
về nhãn dự đoán + xác suất cả 15 lớp + phiên bản model (để truy vết).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import joblib
import pandas as pd


def sha256_of_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


class Detector:
    """Gói model + encoder + model_version lại một chỗ, nạp 1 lần lúc khởi động."""

    def __init__(self, model_path: Path, encoder_path: Path):
        self.model = joblib.load(model_path)
        self.label_encoder = joblib.load(encoder_path)
        self.model_version = sha256_of_file(model_path)[:16]  # rút gọn cho dễ đọc log
        self.feature_names = list(self.model.feature_names_in_)
        self.class_names = list(self.label_encoder.classes_)

    def predict_flow(self, normalized_row: pd.DataFrame) -> dict:
        """normalized_row: DataFrame 1 dòng, đúng 78 cột, đúng thứ tự (đầu ra của
        app.normalize.normalize_flow). Trả về dict: predicted_label, probabilities
        (dict 15 lớp -> xác suất), model_version."""
        proba = self.model.predict_proba(normalized_row)[0]
        pred_idx = int(proba.argmax())
        return {
            "predicted_label": self.class_names[pred_idx],
            "probabilities": {cls: float(p) for cls, p in zip(self.class_names, proba)},
            "model_version": self.model_version,
        }

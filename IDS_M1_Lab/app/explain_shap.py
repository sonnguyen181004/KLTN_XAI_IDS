"""Tầng 4a — TreeSHAP tự động. Chạy cho MỌI Alert (khác LIME ở app/explain_lime.py,
chỉ chạy khi analyst bấm xin — xem bước 9). Dùng đúng cách RQ2 đã làm: TreeSHAP
trên margin thô (raw), giải thích cho ĐÚNG lớp vừa được dự đoán.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import shap
import xgboost as xgb


class ShapExplainer:
    def __init__(self, model, class_names: list[str]):
        self.model = model
        self.class_names = class_names
        self.explainer = shap.TreeExplainer(model)
        self.booster = model.get_booster()

    def explain(self, normalized_row: pd.DataFrame, predicted_label: str, top_k: int = 5) -> dict:
        """normalized_row: DataFrame 1 dòng, đúng 78 cột, đúng thứ tự (đầu ra của
        app.normalize.normalize_flow). Trả về Top-k đặc trưng có dấu cho ĐÚNG lớp
        predicted_label, kèm sai số additivity để tự kiểm tra."""
        class_idx = self.class_names.index(predicted_label)
        feature_names = list(normalized_row.columns)

        exp = self.explainer(normalized_row, check_additivity=False)
        phi = exp.values[0, :, class_idx]  # 78 giá trị SHAP cho đúng lớp dự đoán
        base_value = float(np.array(exp.base_values)[0, class_idx])

        # Additivity: base_value + tổng 78 phi phải ≈ margin thật của model (RQ2 ~1e-5/1e-6).
        dmatrix = xgb.DMatrix(normalized_row, feature_names=feature_names)
        margin = self.booster.predict(dmatrix, output_margin=True)[0, class_idx]
        additivity_error = float(abs((base_value + phi.sum()) - margin))

        order = np.argsort(-np.abs(phi))[:top_k]
        top_k_list = [
            {"feature": feature_names[i], "value": float(normalized_row.iloc[0, i]), "phi": float(phi[i])}
            for i in order
        ]

        return {
            "class_explained": predicted_label,
            "base_value": base_value,
            "top_k": top_k_list,
            "additivity_error": additivity_error,
        }

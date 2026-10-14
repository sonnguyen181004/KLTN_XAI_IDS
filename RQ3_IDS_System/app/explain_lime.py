"""Bước 9 — Tầng 4b: LIME theo yêu cầu. KHÔNG chạy tự động như SHAP (chậm hơn ~8 lần,
~148ms so với ~19ms) — chỉ chạy khi analyst bấm xin qua `POST /explain`.

Dùng ĐÚNG cấu hình đã khóa ở RQ2 GĐ5 (`config.yaml: lime.*`) và ĐÚNG cách seed của
RQ2/scripts/lib/common.py::set_lime_explainer_seed — xem docstring hàm đó: lime==0.2.0.1
không có tham số random_state ở explain_instance(), phải tự gán lại 2-3 tham chiếu
RandomState TRƯỚC MỖI LẦN gọi, nếu không kết quả sẽ không tái lập được.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from lime.lime_tabular import LimeTabularExplainer


def set_lime_explainer_seed(explainer, seed: int) -> None:
    """Sao chép nguyên vẹn từ RQ2/scripts/lib/common.py — xem docstring gốc ở đó
    giải thích vì sao phải gán lại CẢ 2-3 tham chiếu, không chỉ 1."""
    rs = np.random.RandomState(seed)
    explainer.random_state = rs
    explainer.base.random_state = rs
    if getattr(explainer, "discretizer", None) is not None:
        explainer.discretizer.random_state = rs


class LimeExplainer:
    def __init__(self, model, feature_names: list[str], class_names: list[str],
                 background: np.ndarray, lime_cfg: dict, base_seed: int):
        self.model = model
        self.feature_names = feature_names
        self.class_names = class_names
        self.lime_cfg = lime_cfg
        self.base_seed = base_seed

        self.explainer = LimeTabularExplainer(
            training_data=background,
            feature_names=feature_names,
            class_names=class_names,
            discretize_continuous=lime_cfg["discretize_continuous"],
            kernel_width=lime_cfg["kernel_width"],
            random_state=base_seed,
        )

    def _predict_proba_fn(self, x: np.ndarray) -> np.ndarray:
        df_x = pd.DataFrame(x, columns=self.feature_names)
        return self.model.predict_proba(df_x)

    def explain(self, normalized_row: pd.DataFrame, predicted_label: str, flow_seed_key: int, top_k: int = 5) -> dict:
        """normalized_row: DataFrame 1 dòng, đúng 78 cột, đúng thứ tự.
        flow_seed_key: số nguyên dùng để seed riêng cho flow này (vd hash alert_id),
        giữ đúng nguyên tắc RQ2 "random_state cố định THEO TỪNG FLOW" để tái lập được
        độc lập mỗi flow."""
        class_idx = self.class_names.index(predicted_label)
        row = normalized_row.iloc[0].to_numpy()

        flow_seed = (self.base_seed * 1_000_003 + flow_seed_key) % (2 ** 31 - 1)
        set_lime_explainer_seed(self.explainer, flow_seed)

        exp = self.explainer.explain_instance(
            row, self._predict_proba_fn,
            num_features=self.lime_cfg["num_features"],
            num_samples=self.lime_cfg["num_samples"],
            labels=[class_idx],
        )

        local_r2 = exp.score[class_idx] if isinstance(exp.score, dict) else exp.score
        weights = exp.as_list(label=class_idx)  # [(feature_desc, weight), ...] đã sắp theo |weight| giảm dần
        top_k_list = [
            {"feature_desc": desc, "weight": float(w)}
            for desc, w in weights[:top_k]
        ]

        return {
            "class_explained": predicted_label,
            "local_r2": float(local_r2),
            "top_k": top_k_list,
        }

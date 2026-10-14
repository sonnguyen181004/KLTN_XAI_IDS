"""Bước 8 — Đánh giá độ tin cậy + gắn cờ (tầng 4b). Chạy NGAY SAU TreeSHAP (cần Top-5
SHAP làm input), cho MỖI Alert — tất cả đều "tính tại chỗ" (rẻ), đúng mục đích kiến
trúc tách "tính tại chỗ" (chạy mỗi flow) khỏi "tra bảng có sẵn" (đắt, lấy từ RQ2,
chưa làm ở bước này).

⚠️ Đọc kỹ `docs/plan.md` mục "Lưu ý quan trọng — tránh overclaim" trước khi dùng kết
quả của module này trong báo cáo: cờ môi trường chỉ là cờ cảnh báo (giả thuyết chưa
kiểm chứng, xem E4), faithfulness ở đây là PROXY một bước/một giá trị nền, KHÔNG phải
phép đo faithfulness đầy đủ của RQ2 (xóa k=1..10, 3 giá trị nền, AUC, đối chứng ngẫu
nhiên, kiểm định Wilcoxon).
"""
from __future__ import annotations

import pandas as pd


class ReliabilityScorer:
    def __init__(
        self,
        detector,
        global_median: dict[str, float],
        train_samples_per_class: dict[str, int],
        env_fingerprint_features: list[str],
        env_fingerprint_flag_threshold: int,
        rare_class_min_train_samples: int,
        faithfulness_k: int = 5,
    ):
        self.detector = detector
        self.global_median = global_median
        self.train_samples_per_class = train_samples_per_class
        self.env_fingerprint_features = set(env_fingerprint_features)
        self.env_fingerprint_flag_threshold = env_fingerprint_flag_threshold
        self.rare_class_min_train_samples = rare_class_min_train_samples
        self.faithfulness_k = faithfulness_k

    def score(self, normalized_row: pd.DataFrame, predicted_label: str, shap_top_k: list[dict]) -> dict:
        """normalized_row: DataFrame 1 dòng, đúng 78 cột (đầu vào gốc, CHƯA xóa gì).
        shap_top_k: kết quả `top_k` từ ShapExplainer.explain() — list dict có 'feature'.
        predicted_label: nhãn XGBoost vừa đoán (dùng để tra xác suất trước/sau xóa).
        """
        top_features = [item["feature"] for item in shap_top_k[: self.faithfulness_k]]

        faithfulness_proxy_drop = self._faithfulness_proxy(normalized_row, predicted_label, top_features)

        env_fingerprint_count = sum(1 for f in top_features if f in self.env_fingerprint_features)
        env_fingerprint_flag = int(env_fingerprint_count >= self.env_fingerprint_flag_threshold)

        n_train = self.train_samples_per_class.get(predicted_label)
        rare_class_flag = int(n_train is not None and n_train < self.rare_class_min_train_samples)

        return {
            "faithfulness_proxy_drop": faithfulness_proxy_drop,
            "env_fingerprint_count": env_fingerprint_count,
            "env_fingerprint_flag": env_fingerprint_flag,
            "rare_class_flag": rare_class_flag,
        }

    def _faithfulness_proxy(self, normalized_row: pd.DataFrame, predicted_label: str, top_features: list[str]) -> float:
        """Xóa (đặt về global_median) đúng Top-k đặc trưng SHAP đã chỉ ra, hỏi lại
        model, đo xác suất lớp dự đoán tụt bao nhiêu (0..1). Tụt càng nhiều thì lời
        giải thích càng "trúng" phần model thực sự dựa vào — đây là PROXY một bước,
        xem cảnh báo overclaim ở đầu file."""
        proba_before = self.detector.predict_flow(normalized_row)["probabilities"][predicted_label]

        ablated_row = normalized_row.copy()
        for feature in top_features:
            ablated_row.at[ablated_row.index[0], feature] = self.global_median[feature]

        proba_after = self.detector.predict_flow(ablated_row)["probabilities"][predicted_label]
        return float(proba_before - proba_after)

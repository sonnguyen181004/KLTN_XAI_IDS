"""Tầng 2 — Chuẩn hóa flow: đứng giữa "dữ liệu thô" và "model".

Một flow hợp lệ phải: đủ 78 cột đặc trưng model mong đợi, không có NaN/Inf, và
được xếp ĐÚNG THỨ TỰ cột như lúc huấn luyện model (XGBoost rất nhạy thứ tự cột
— sai thứ tự vẫn chạy ra kết quả nhưng SAI mà không báo lỗi gì).

`convert_seconds_to_microseconds`: CICFlowMeter bản mới xuất thời gian theo giây,
còn model được huấn luyện trên dữ liệu gốc tính bằng micro giây (lệch 1e6 lần).
Tập A (cohort RQ2) và Tập B (GĐ3) đã sẵn đúng đơn vị micro giây, nên khi test
bằng 2 tập này tham số này phải để False. Khi nào có traffic thật từ CICFlowMeter
(M4), bật tham số này lên True — không cần sửa logic nào khác.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Các cột CICFlowMeter tính bằng đơn vị thời gian (giây ở bản mới) — chuyển sang
# micro giây bằng cách nhân 1e6 khi convert_seconds_to_microseconds=True.
TIME_COLUMNS = [
    "Flow Duration", "Flow IAT Mean", "Flow IAT Std", "Flow IAT Max", "Flow IAT Min",
    "Fwd IAT Tot", "Fwd IAT Mean", "Fwd IAT Std", "Fwd IAT Max", "Fwd IAT Min",
    "Bwd IAT Tot", "Bwd IAT Mean", "Bwd IAT Std", "Bwd IAT Max", "Bwd IAT Min",
    "Active Mean", "Active Std", "Active Max", "Active Min",
    "Idle Mean", "Idle Std", "Idle Max", "Idle Min",
]


class FlowValidationError(Exception):
    """Flow không đủ điều kiện để dự đoán — tương ứng mã lỗi 422."""

    def __init__(self, reason: str, details: dict | None = None):
        super().__init__(reason)
        self.reason = reason
        self.details = details or {}


def normalize_flow(
    raw: dict[str, float],
    expected_columns: list[str],
    convert_seconds_to_microseconds: bool = False,
) -> pd.DataFrame:
    """Chuẩn hóa 1 flow thô (dict tên_cột -> giá trị) thành 1 dòng DataFrame
    đúng 78 cột, đúng thứ tự `expected_columns`, sẵn sàng đưa vào model.

    Ném FlowValidationError nếu flow không đủ điều kiện (thiếu cột, NaN, Inf).
    KHÔNG tự động điền giá trị thiếu — một flow thiếu dữ liệu thì bị từ chối,
    không đoán bừa bằng giá trị giả.
    """
    # ---- 1) Kiểm tra đủ cột không ------------------------------------------------
    missing = [c for c in expected_columns if c not in raw]
    if missing:
        raise FlowValidationError(
            reason=f"Thiếu {len(missing)} cột đặc trưng bắt buộc",
            details={"missing_columns": missing},
        )

    # ---- 2) Xếp đúng thứ tự cột --------------------------------------------------
    ordered = {c: raw[c] for c in expected_columns}
    df = pd.DataFrame([ordered], columns=expected_columns)

    # ---- 3) Đổi đơn vị thời gian (nếu cần, dành cho traffic thật từ CICFlowMeter) -
    if convert_seconds_to_microseconds:
        cols_present = [c for c in TIME_COLUMNS if c in df.columns]
        df[cols_present] = df[cols_present] * 1_000_000

    # ---- 4) Kiểm tra NaN / Inf ----------------------------------------------------
    numeric = df.to_numpy(dtype="float64")
    nan_cols = [expected_columns[i] for i in np.where(np.isnan(numeric[0]))[0]]
    if nan_cols:
        raise FlowValidationError(
            reason=f"Có {len(nan_cols)} cột giá trị NaN (trống)",
            details={"nan_columns": nan_cols},
        )
    inf_cols = [expected_columns[i] for i in np.where(np.isinf(numeric[0]))[0]]
    if inf_cols:
        raise FlowValidationError(
            reason=f"Có {len(inf_cols)} cột giá trị Inf (vô cực)",
            details={"inf_columns": inf_cols},
        )

    return df

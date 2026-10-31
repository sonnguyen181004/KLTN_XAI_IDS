"""Bước 4 — Test hàm chuẩn hóa flow (tầng 2) bằng 4 tình huống:
  1) Vài dòng thật từ Tập B -> phải PASS.
  2) Dòng thiếu 1 cột -> phải bị từ chối (422), đúng lý do.
  3) Dòng có NaN -> phải bị từ chối (422), đúng lý do.
  4) Dòng sai thứ tự cột -> phải được TỰ sắp lại, không bị từ chối oan.
Chưa đụng tới model thật — chỉ test logic chuẩn hóa độc lập.
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from normalize import normalize_flow, FlowValidationError  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_config() -> dict:
    with open(Path(__file__).resolve().parents[1] / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> int:
    cfg = load_config()
    print("=" * 70)
    print("BƯỚC 4: TEST HÀM CHUẨN HÓA FLOW (TẦNG 2)")
    print("=" * 70)

    model = joblib.load(REPO_ROOT / cfg["paths"]["model"])
    expected_columns = list(model.feature_names_in_)
    print(f"Model mong đợi {len(expected_columns)} cột, 5 cột đầu: {expected_columns[:5]}")
    assert len(expected_columns) == cfg["n_features_expected"]

    clean_set_path = REPO_ROOT / cfg["paths"]["clean_set_out"]
    df = pd.read_csv(clean_set_path)
    sample_rows = df.head(3).to_dict("records")

    all_ok = True

    # ---- Tình huống 1: dòng thật từ Tập B, phải PASS ----------------------------
    print("\n--- Tình huống 1: vài dòng thật từ Tập B (phải PASS) ---")
    for i, row in enumerate(sample_rows):
        raw = {c: row[c] for c in expected_columns}  # chỉ lấy đúng 78 cột đặc trưng
        try:
            out = normalize_flow(raw, expected_columns, convert_seconds_to_microseconds=False)
            same_order = list(out.columns) == expected_columns
            print(f"  Dòng {i} (flow_id={row.get('flow_id')}, label_true={row.get('label_true')}): "
                  f"PASS, đúng thứ tự cột = {same_order}")
            if not same_order:
                all_ok = False
        except FlowValidationError as e:
            print(f"  Dòng {i}: [FAIL] bị từ chối oan — {e.reason}")
            all_ok = False

    # ---- Tình huống 2: thiếu 1 cột ------------------------------------------------
    print("\n--- Tình huống 2: dòng thiếu 1 cột (phải bị từ chối 422) ---")
    raw_missing = {c: sample_rows[0][c] for c in expected_columns}
    removed_col = expected_columns[10]
    del raw_missing[removed_col]
    try:
        normalize_flow(raw_missing, expected_columns)
        print(f"  [FAIL] Không bị từ chối dù thiếu cột '{removed_col}'!")
        all_ok = False
    except FlowValidationError as e:
        ok = removed_col in e.details.get("missing_columns", [])
        print(f"  [PASS] Bị từ chối đúng: '{e.reason}', cột thiếu có liệt kê '{removed_col}' = {ok}")
        if not ok:
            all_ok = False

    # ---- Tình huống 3: có NaN ------------------------------------------------------
    print("\n--- Tình huống 3: dòng có NaN (phải bị từ chối 422) ---")
    raw_nan = {c: sample_rows[0][c] for c in expected_columns}
    nan_col = expected_columns[20]
    raw_nan[nan_col] = float("nan")
    try:
        normalize_flow(raw_nan, expected_columns)
        print(f"  [FAIL] Không bị từ chối dù cột '{nan_col}' là NaN!")
        all_ok = False
    except FlowValidationError as e:
        ok = nan_col in e.details.get("nan_columns", [])
        print(f"  [PASS] Bị từ chối đúng: '{e.reason}', cột NaN có liệt kê '{nan_col}' = {ok}")
        if not ok:
            all_ok = False

    # ---- Tình huống 4: sai thứ tự cột, phải tự sắp lại -----------------------------
    print("\n--- Tình huống 4: dòng sai thứ tự cột (phải tự sắp lại, không từ chối oan) ---")
    raw_shuffled = {c: sample_rows[0][c] for c in reversed(expected_columns)}  # đảo ngược thứ tự
    try:
        out = normalize_flow(raw_shuffled, expected_columns)
        same_order = list(out.columns) == expected_columns
        print(f"  [{'PASS' if same_order else 'FAIL'}] Input bị đảo ngược thứ tự, "
              f"output đúng thứ tự model mong đợi = {same_order}")
        if not same_order:
            all_ok = False
    except FlowValidationError as e:
        print(f"  [FAIL] Bị từ chối oan dù chỉ sai thứ tự cột: {e.reason}")
        all_ok = False

    print("\n" + "=" * 70)
    print("BƯỚC 4 " + ("HOÀN TẤT — mọi tình huống đúng như kỳ vọng." if all_ok else "CÓ LỖI, xem [FAIL] ở trên."))
    print("=" * 70)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

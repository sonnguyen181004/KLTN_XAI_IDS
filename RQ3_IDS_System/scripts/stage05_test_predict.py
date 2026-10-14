"""Bước 5 — Test tầng 3 (hàm dự đoán) bằng 3 việc:
  1) Tự nhất quán: xác suất 15 lớp cộng ~1.0, khớp lớp cao nhất.
  2) So với label_true của Tập B (241 flow) -> % đúng theo từng lớp.
  3) So với pred_label đã có sẵn trong cohort_ids.csv của RQ2 (Tập A) cho vài
     chục flow -> phải khớp Y HỆT (kiểm tra sớm, thu nhỏ của thí nghiệm E5).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from normalize import normalize_flow  # noqa: E402
from predict import Detector  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_config() -> dict:
    with open(Path(__file__).resolve().parents[1] / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> int:
    cfg = load_config()
    seed = cfg["seed"]
    print("=" * 70)
    print("BƯỚC 5: TEST HÀM DỰ ĐOÁN (TẦNG 3)")
    print("=" * 70)

    detector = Detector(
        REPO_ROOT / cfg["paths"]["model"],
        REPO_ROOT / cfg["paths"]["label_encoder"],
    )
    print(f"Nạp model xong. model_version={detector.model_version}, "
          f"{len(detector.feature_names)} cột, {len(detector.class_names)} lớp.")

    all_ok = True

    # ---- Việc 1: tự nhất quán ----------------------------------------------------
    print("\n--- Việc 1: tự nhất quán (xác suất cộng ~1.0, khớp lớp cao nhất) ---")
    clean_df = pd.read_csv(REPO_ROOT / cfg["paths"]["clean_set_out"])
    row0 = clean_df.iloc[0]
    raw0 = {c: row0[c] for c in detector.feature_names}
    normalized0 = normalize_flow(raw0, detector.feature_names)
    result0 = detector.predict_flow(normalized0)
    proba_sum = sum(result0["probabilities"].values())
    top_class_by_proba = max(result0["probabilities"], key=result0["probabilities"].get)
    consistent = (abs(proba_sum - 1.0) < 1e-6) and (top_class_by_proba == result0["predicted_label"])
    print(f"  Flow mẫu: label_true={row0['label_true']}, predicted_label={result0['predicted_label']}")
    print(f"  Tổng xác suất 15 lớp = {proba_sum:.8f} (kỳ vọng ~1.0)")
    print(f"  Lớp xác suất cao nhất = '{top_class_by_proba}', predicted_label = '{result0['predicted_label']}' "
          f"-> khớp = {consistent}")
    print(f"  [{'PASS' if consistent else 'FAIL'}]")
    all_ok &= consistent

    # ---- Việc 2: so với label_true của Tập B ------------------------------------
    print(f"\n--- Việc 2: so với label_true của Tập B ({len(clean_df)} flow) ---")
    correct_by_class: dict[str, list[bool]] = {}
    for _, row in clean_df.iterrows():
        raw = {c: row[c] for c in detector.feature_names}
        normalized = normalize_flow(raw, detector.feature_names)
        result = detector.predict_flow(normalized)
        is_correct = result["predicted_label"] == row["label_true"]
        correct_by_class.setdefault(row["label_true"], []).append(is_correct)

    total_correct = sum(sum(v) for v in correct_by_class.values())
    total_n = sum(len(v) for v in correct_by_class.values())
    print(f"  Độ chính xác tổng: {total_correct}/{total_n} = {total_correct/total_n*100:.1f}%")
    print("  Theo từng lớp:")
    for cls, results in sorted(correct_by_class.items()):
        acc = sum(results) / len(results) * 100
        print(f"    {cls:30s}: {sum(results):3d}/{len(results):3d} = {acc:5.1f}%")

    # ---- Việc 3: so với pred_label đã có sẵn trong cohort_ids.csv (Tập A) --------
    print("\n--- Việc 3: so với pred_label có sẵn trong cohort_ids.csv của RQ2 (Tập A) ---")
    cohort_df = pd.read_csv(REPO_ROOT / cfg["paths"]["rq2_cohort_ids"])
    test_set_df = pd.read_parquet(REPO_ROOT / cfg["paths"]["test_set"])

    rng = np.random.default_rng(seed)
    n_check = min(50, len(cohort_df))
    sample_idx = rng.choice(len(cohort_df), size=n_check, replace=False)
    sample = cohort_df.iloc[sample_idx]

    n_match = 0
    mismatches = []
    for _, crow in sample.iterrows():
        flow_id = int(crow["flow_id"])
        test_row = test_set_df.iloc[flow_id]
        raw = {c: test_row[c] for c in detector.feature_names}
        normalized = normalize_flow(raw, detector.feature_names)
        result = detector.predict_flow(normalized)
        if result["predicted_label"] == crow["pred_label"]:
            n_match += 1
        else:
            mismatches.append((flow_id, crow["pred_label"], result["predicted_label"]))

    print(f"  Kiểm tra {n_check} flow lấy ngẫu nhiên từ cohort 1.339 flow (Tập A):")
    print(f"  Khớp y hệt với RQ2: {n_match}/{n_check} = {n_match/n_check*100:.1f}%")
    if mismatches:
        print(f"  [FAIL] Có {len(mismatches)} flow KHÔNG khớp:")
        for fid, rq2_label, new_label in mismatches[:10]:
            print(f"    flow_id={fid}: RQ2='{rq2_label}' vs hệ thống mới='{new_label}'")
        all_ok = False
    else:
        print("  [PASS] Khớp 100% — hàm dự đoán mới cho kết quả giống hệt RQ2 trên cùng dữ liệu.")

    print("\n" + "=" * 70)
    print("BƯỚC 5 " + ("HOÀN TẤT — mọi kiểm tra đúng như kỳ vọng." if all_ok else "CÓ LỖI, xem [FAIL] ở trên."))
    print("=" * 70)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

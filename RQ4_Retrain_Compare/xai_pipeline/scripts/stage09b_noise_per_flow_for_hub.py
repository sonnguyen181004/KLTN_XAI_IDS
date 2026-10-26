"""GĐ 9b (bổ sung, không thuộc 14 giai đoạn chính) — tính lại robustness TỪNG FLOW và TỪNG
LỚP (không chỉ số tổng hợp như GĐ9) để phục vụ trang xai-ids-study-hub (bảng robustness
theo lớp). Dùng lại đúng cách sinh nhiễu của GĐ9 (cùng seed) nhưng lưu chi tiết hơn: thêm
cờ 'dự đoán có đổi nhãn không' — điều GĐ9 không cần cho báo cáo .docx nhưng hub cần để
phân biệt 'explanation robustness' và 'prediction robustness'.
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from lime.lime_tabular import LimeTabularExplainer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.common import load_config, resolve_path, latest_run_dir, get_logger, set_lime_explainer_seed  # noqa: E402


def jaccard(a: set, b: set) -> float:
    u = a | b
    return len(a & b) / len(u) if u else float("nan")


def top5_shap(row: np.ndarray, feature_names: list[str]) -> set:
    order = np.argsort(-np.abs(row))[:5]
    return {feature_names[i] for i in order}


def main() -> int:
    cfg = load_config()
    run_dir = latest_run_dir()
    logger = get_logger("stage09b_noise_per_flow_for_hub", run_dir)
    out_dir = run_dir / "gd9_stability_robustness"

    logger.info("GĐ 9b: robustness per-flow/per-class cho study hub")

    seed = cfg["seed"]
    locked = cfg["lime"]["locked_config"]
    model = joblib.load(resolve_path(cfg["paths"]["model"]))
    le = joblib.load(resolve_path(cfg["paths"]["label_encoder"]))
    train_df = pd.read_parquet(resolve_path(cfg["paths"]["train_set"]))
    test_df = pd.read_parquet(resolve_path(cfg["paths"]["test_set"])).reset_index(drop=True)
    X_test = test_df.drop(columns=["Label"])
    feature_names = list(X_test.columns)

    cohort = pd.read_csv(run_dir / "gd3_cohorts" / "cohort_ids.csv")
    flow_ids = cohort["flow_id"].to_numpy()
    X_cohort = X_test.iloc[flow_ids]
    proba_cohort = model.predict_proba(X_cohort)
    pred_idx_cohort = proba_cohort.argmax(axis=1)
    n = len(flow_ids)

    X_train_feat = train_df.drop(columns=["Label"])
    feat_std = X_train_feat.std().to_numpy()
    feat_min = X_train_feat.min().to_numpy()
    feat_max = X_train_feat.max().to_numpy()
    background = X_train_feat.sample(n=locked["background_sample_size"], random_state=locked["background_seed"]).to_numpy()

    def predict_proba_fn(x):
        return model.predict_proba(pd.DataFrame(x, columns=feature_names))

    lime_explainer = LimeTabularExplainer(
        training_data=background, feature_names=feature_names, class_names=list(le.classes_),
        discretize_continuous=locked["discretize_continuous"], kernel_width=locked["kernel_width"], random_state=seed,
    )
    shap_explainer = shap.TreeExplainer(model)

    shap_topk = pd.read_csv(run_dir / "gd4_shap_per_flow" / "shap_per_flow_topk.csv")
    lime_topk = pd.read_csv(run_dir / "gd6_lime_per_flow" / "lime_per_flow_topk.csv")
    ref_shap_top5 = {r.flow_id: set(r.top_features.split(";")) for r in shap_topk[shap_topk.k == 5].itertuples()}
    ref_lime_top5 = {r.flow_id: set(r.top_features.split(";")) for r in lime_topk[lime_topk.k == 5].itertuples()}

    rng = np.random.default_rng(seed)
    all_rows = []
    CHUNK = 200
    for sigma in cfg["noise"]["sigma_fractions"]:
        noise = rng.normal(0, 1, size=X_cohort.shape) * (feat_std * sigma)
        X_noisy = np.clip(X_cohort.to_numpy() + noise, feat_min, feat_max)
        X_noisy_df = pd.DataFrame(X_noisy, columns=feature_names, index=X_cohort.index)
        pred_idx_noisy = model.predict_proba(X_noisy_df).argmax(axis=1)

        shap_j = np.empty(n)
        for start in range(0, n, CHUNK):
            end = min(start + CHUNK, n)
            exp = shap_explainer(X_noisy_df.iloc[start:end], check_additivity=False)
            for j in range(end - start):
                fid = int(flow_ids[start + j])
                pidx = int(pred_idx_cohort[start + j])
                shap_j[start + j] = jaccard(top5_shap(exp.values[j, :, pidx], feature_names), ref_shap_top5[fid])

        lime_j = np.empty(n)
        for i in range(n):
            fid = int(flow_ids[i])
            pidx = int(pred_idx_cohort[i])
            flow_seed = (seed * 1_000_003 + fid) % (2 ** 31 - 1)
            set_lime_explainer_seed(lime_explainer, flow_seed)
            exp = lime_explainer.explain_instance(
                X_noisy_df.iloc[i].to_numpy(), predict_proba_fn,
                num_features=locked["num_features"], num_samples=locked["num_samples"], labels=[pidx],
            )
            top5 = {t[0] for t in sorted(exp.as_list(label=pidx), key=lambda t: -abs(t[1]))[:5]}
            lime_j[i] = jaccard(top5, ref_lime_top5[fid])

        for i in range(n):
            fid = int(flow_ids[i])
            all_rows.append({
                "flow_id": fid,
                "true_label": cohort.iloc[i]["true_label"],
                "sigma_fraction": sigma,
                "shap_jaccard5": shap_j[i],
                "lime_jaccard5": lime_j[i],
                "pred_changed": bool(pred_idx_noisy[i] != pred_idx_cohort[i]),
            })
        logger.info("sigma=%.0f%% xong", sigma * 100)

    df = pd.DataFrame(all_rows)
    df.to_csv(out_dir / "rq2_2_noise_per_flow_for_hub.csv", index=False, encoding="utf-8-sig")

    by_class = df.groupby(["true_label", "sigma_fraction"]).agg(
        shap_jaccard5=("shap_jaccard5", "mean"),
        lime_jaccard5=("lime_jaccard5", "mean"),
        pred_changed_rate=("pred_changed", "mean"),
        n=("flow_id", "count"),
    ).reset_index()
    by_class.to_csv(out_dir / "rq2_2_noise_by_class_for_hub.csv", index=False, encoding="utf-8-sig")
    logger.info("Đã lưu per-flow và per-class noise cho hub.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Chạy lại toàn bộ chuỗi giải thích RQ2 (GĐ0 đến GĐ13) cho một mô hình RQ4, đúng mã và đúng tham số của RQ2.

  python 08_run_xai.py m1            tạo xai_runs/m1, cấu hình riêng, rồi chạy các giai đoạn theo thứ tự
  python 08_run_xai.py m1 --from 5   chạy tiếp từ GĐ5

GĐ9 (độ ổn định và chịu nhiễu) được bỏ qua theo yêu cầu của người dùng. GĐ13 tự bỏ phần GĐ9 khi thiếu dữ liệu.

Chỉ ba thứ khác RQ2: đường dẫn (mô hình, bộ mã hóa nhãn, train, test), số lớp (13) và số liệu tham chiếu để GĐ1 kiểm tra
(lấy từ kết quả huấn luyện của chính mô hình đó). Cấu hình LIME KHÔNG chọn lại: dùng đúng cấu hình đã khóa ở RQ2 GĐ5
(kernel_width 3,312, num_samples 1000, discretize false, nền 2000 dòng, seed 42), nên GĐ5 được bỏ qua và báo cáo khóa của RQ2 được chép sang.
"""
import argparse
import os
import re
import subprocess
import sys

import pandas as pd
import yaml

from rq4_common import *

STAGES = ["stage00_prepare_run", "stage01_verify_env", "stage02_shap_global", "stage03_cohorts", "stage04_shap_per_flow",
          "stage05_lock_lime_config", "stage06_lime_per_flow", "stage07_agreement", "stage08_quality_gate",
          "stage09_stability_robustness", "stage10_faithfulness", "stage11_domain_validation", "stage12_error_cohort",
          "stage13_build_report_data"]

ap = argparse.ArgumentParser()
ap.add_argument("name")
ap.add_argument("--from", dest="start", type=int, default=0)
ap.add_argument("--to", dest="stop", type=int, default=13)
a = ap.parse_args()

work = RQ4 / "xai_runs" / a.name
work.mkdir(parents=True, exist_ok=True)
sets = DATA / "xai_sets"
sets.mkdir(parents=True, exist_ok=True)


def old13(path):
    d = pd.read_parquet(path)
    return d[d.Label.isin(CLASSES_13)].reset_index(drop=True)


# 1. bộ train và test đúng như lúc huấn luyện mô hình này
tr_p, te_p = sets / f"{a.name}_train.parquet", sets / f"{a.name}_test.parquet"
if not tr_p.exists():
    if a.name == "m0b":
        train, test = old13(TRAIN_OLD), old13(TEST_OLD)
    elif a.name == "m1":
        train, test = pd.read_parquet(DATA / "d2_train.parquet"), pd.read_parquet(DATA / "d2_test.parquet")
    else:
        n = int(a.name.split("_")[1])
        train = pd.concat([old13(TRAIN_OLD), pd.read_parquet(DATA / f"m2_add_{n}.parquet")], ignore_index=True).sample(frac=1.0, random_state=SEED).reset_index(drop=True)
        test = old13(TEST_OLD)
    train.to_parquet(tr_p, index=False); test.to_parquet(te_p, index=False)

# 2. cấu hình: bản của RQ2, đổi đường dẫn, số lớp và số liệu tham chiếu
cfg = yaml.safe_load((REPO / "RQ2" / "config.yaml").read_text(encoding="utf-8"))
rel = lambda p: str(p.relative_to(REPO)).replace("\\", "/")
cfg["paths"].update(train_set=rel(tr_p), test_set=rel(te_p), model=rel(MODELS / f"{a.name}_xgboost_model.pkl"),
                    label_encoder=rel(MODELS / f"{a.name}_label_encoder.pkl"), rq1_summary_csv=rel(RESULTS / a.name / "bang_2_ket_qua_chinh_thuc.csv"),
                    v1_archive=rel(RQ4 / "xai_runs" / a.name))
summ = pd.read_csv(RESULTS / a.name / "bang_2_ket_qua_chinh_thuc.csv")
val = lambda i: float(re.match(r"[\d.]+", str(summ.iloc[i, 1])).group())
cfg["rq1_reference_metrics"] = dict(accuracy_pct=val(0), macro_precision_pct=val(1), macro_recall_pct=val(2), macro_f1_pct=val(3))
cfg["n_classes_expected"] = len(CLASSES_13)
assert cfg["lime"]["locked_config"]["kernel_width"] == 3.312   # cấu hình đã khóa của RQ2, không đổi
cfg_p = work / "config.yaml"
if a.start == 0 or not cfg_p.exists():
    cfg_p.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")

import shutil
gd5 = work / "runs"
env = dict(os.environ, XAI_WORKDIR=str(work), PYTHONIOENCODING="utf-8")
for i, st in enumerate(STAGES):
    if i < a.start or i > a.stop:
        continue
    if st == "stage09_stability_robustness":
        print(f"=== {a.name}: GĐ9 bỏ qua theo yêu cầu của người dùng (độ ổn định và chịu nhiễu)", flush=True)
        continue
    if st == "stage05_lock_lime_config":
        run_dirs = sorted((work / "runs").glob("*"))
        d = run_dirs[-1] / "gd5_lime_dev_tuning"
        d.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / "RQ2/runs/20261009/gd5_lime_dev_tuning/lime_config_lock_report.json", d / "lime_config_lock_report.json")
        (d / "NOTE.txt").write_text("GĐ5 không chạy lại trong RQ4. Dùng cấu hình LIME đã khóa ở RQ2 (xem config.yaml, lime.locked_config); đây là bản sao báo cáo khóa của RQ2.\n", encoding="utf-8")
        print(f"=== {a.name}: GĐ5 bỏ qua, dùng cấu hình LIME đã khóa của RQ2", flush=True)
        continue
    print(f"=== {a.name}: GĐ{i} {st}", flush=True)
    r = subprocess.run([sys.executable, "-X", "utf8", str(RQ4 / "xai_pipeline" / "scripts" / f"{st}.py")], env=env, cwd=RQ4 / "xai_pipeline" / "scripts")
    if r.returncode:
        print(f"!!! GĐ{i} thất bại (mã {r.returncode}), dừng.", flush=True)
        sys.exit(r.returncode)
print("xong chuỗi giải thích cho", a.name)

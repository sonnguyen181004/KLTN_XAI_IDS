"""RQ1 - Cách 1: đánh giá độ ổn định và chẩn đoán overfit/underfit cho cấu hình XGBoost CỐ ĐỊNH
(max_depth=8, learning_rate=0.08, n_estimators=100), đúng cấu hình của mô hình chính thức.

KHÔNG chọn lại siêu tham số, KHÔNG ghi đè saved_models/, KHÔNG sửa kết quả cũ.
Mô hình train trong script chỉ dùng tạm rồi bỏ, không lưu ra file.
Mọi đầu ra ghi vào results/cv_diagnostics/.

Các bước (--stage):
  audit    : dòng trùng và nhãn mâu thuẫn (cùng 78 đặc trưng, khác nhãn) trên train+test;
             trần độ chính xác lý thuyết mà KHÔNG mô hình nào vượt được trên dữ liệu này.
  cv       : 5-fold stratified CV trên train_set.parquet (tập test chính thức không bị dùng).
             Mỗi fold đo trên: phần train của fold, phần validation đầy đủ, phần validation "sạch"
             (bỏ dòng giống hệt một dòng train của fold); ghi đường cong mlogloss/merror theo từng cây.
  curve    : đường cong loss mở rộng tới --curve-rounds cây trên fold 0, xem sau 100 cây còn cải thiện hay bắt đầu overfit.
  learning : learning curve trên fold 0 với 5%, 10%, 25%, 50%, 100% dữ liệu train của fold.
  resplit  : gộp train+test, chia lại 80/20 phân tầng với các seed 1..--seeds (cùng giao thức 3_repeat_resplits.py).
  report   : gom kết quả thành bảng CSV, biểu đồ PNG và BAO_CAO_CACH1.md.
  all      : chạy tất cả theo thứ tự trên.

Kết quả từng fold/seed lưu ngay vào results/cv_diagnostics/_cache; chạy lại sẽ bỏ qua phần đã xong
(thêm --force để chạy lại). Có thể dừng giữa chừng rồi chạy tiếp.

Ví dụ:
  python 4_cv_overfit_cach1.py --stage all
  python 4_cv_overfit_cach1.py --stage cv
  python 4_cv_overfit_cach1.py --stage all --sample-frac 0.02     (chạy thử nhanh, ghi vào cv_diagnostics_thu)
"""
import argparse
import io
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

if hasattr(sys.stdout, "buffer") and (sys.stdout.encoding or "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ids_metrics import ids_detection_metrics  # noqa: E402

DATA = HERE.parent / "dataset" / "CICID-2018_processed"
OFFICIAL_CSV = HERE / "results" / "bang_2_ket_qua_chinh_thuc_rq1.csv"
OLD_REPEAT = HERE / "results" / "repeat_runs"

# Cấu hình chính thức của RQ1 (2_train_optimal_model.py). Không đổi.
CFG = dict(n_estimators=100, max_depth=8, learning_rate=0.08, tree_method="hist", random_state=42, n_jobs=-1)
CV_SEED = 42
LEARN_FRACS = [0.05, 0.10, 0.25, 0.50, 1.00]
METRICS = ["accuracy", "macro_precision", "macro_recall", "macro_f1", "fpr", "fnr"]
METRIC_VI = {"accuracy": "Accuracy", "macro_precision": "Macro Precision", "macro_recall": "Macro Recall",
             "macro_f1": "Macro F1", "fpr": "FPR (báo động giả)", "fnr": "FNR (bỏ sót)"}


# ----------------------------------------------------------------------------- tiện ích

def log(msg):
    print(time.strftime("[%H:%M:%S] ") + msg, flush=True)


def save_json(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    tmp.replace(path)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_set(name, sample_frac):
    df = pd.read_parquet(DATA / name)
    y = df["Label"].astype(str).to_numpy()
    X = df.drop(columns=["Label"]).to_numpy(dtype=np.float32)
    del df
    if sample_frac:
        keep = stratified_take(y, sample_frac, np.random.default_rng(0), min_per_class=40)
        X, y = X[keep], y[keep]
    return X, y


def stratified_take(y, frac, rng, min_per_class=5):
    """Lấy ngẫu nhiên frac số dòng mỗi lớp, mỗi lớp ít nhất min_per_class dòng (để lớp hiếm không biến mất)."""
    keep = []
    for c in np.unique(y):
        idx = np.flatnonzero(y == c)
        n = min(len(idx), max(min_per_class, int(round(len(idx) * frac))))
        keep.append(rng.choice(idx, n, replace=False))
    return np.sort(np.concatenate(keep))


def row_hash(X):
    return pd.util.hash_pandas_object(pd.DataFrame(X), index=False).to_numpy()


def scores(y_true, y_pred, K, benign):
    """Chỉ số macro chỉ tính trên các lớp có mặt trong y_true (giống cách RQ1 tính trên test đủ 15 lớp)."""
    present = np.unique(y_true)
    p, r, f, _ = precision_recall_fscore_support(y_true, y_pred, labels=present, average="macro", zero_division=0)
    pc_p, pc_r, pc_f, sup = precision_recall_fscore_support(y_true, y_pred, labels=np.arange(K), average=None, zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=np.arange(K))
    d = ids_detection_metrics(cm, benign)
    return dict(n=int(len(y_true)), n_classes_present=int(len(present)),
                accuracy=100 * accuracy_score(y_true, y_pred), macro_precision=100 * p, macro_recall=100 * r,
                macro_f1=100 * f, fpr=d["fpr_pct"], fnr=d["fnr_pct"], fp=d["fp"], fn=d["fn"], tp=d["tp"], tn=d["tn"],
                per_class=dict(precision=(100 * pc_p).tolist(), recall=(100 * pc_r).tolist(),
                               f1=(100 * pc_f).tolist(), support=sup.astype(int).tolist()))


def make_model(n_estimators=None, seed=None):
    kw = dict(CFG)
    if n_estimators:
        kw["n_estimators"] = n_estimators
    if seed is not None:
        kw["random_state"] = seed
    return XGBClassifier(eval_metric=["mlogloss", "merror"], **kw)


def fit(model, X, y, evals=None):
    t = time.time()
    if evals:
        model.fit(X, y, eval_set=evals, verbose=False)
    else:
        model.fit(X, y, verbose=False)
    return time.time() - t


def get_curves(model):
    res = model.evals_result()
    out = {}
    for name, key in (("train", "validation_0"), ("val", "validation_1")):
        if key in res:
            out[name] = {m: [float(v) for v in vals] for m, vals in res[key].items()}
    return out


def predict_at(model, X, n_trees):
    try:
        return model.predict(X, iteration_range=(0, n_trees))
    except TypeError:  # xgboost rất cũ
        return model.predict(X, ntree_limit=n_trees)


def encode(y_raw):
    le = LabelEncoder().fit(y_raw)
    y = le.transform(y_raw)
    return le, y, int(list(le.classes_).index("Benign"))


def cv_splits(y, folds):
    skf = StratifiedKFold(n_splits=folds, shuffle=True, random_state=CV_SEED)
    return list(skf.split(np.zeros(len(y)), y))


def summarize(values):
    a = np.asarray(values, dtype=float)
    a = a[np.isfinite(a)]
    if not len(a):
        return dict(mean=float("nan"), std=float("nan"), min=float("nan"), max=float("nan"), ci95=float("nan"), n=0)
    std = float(a.std(ddof=1)) if len(a) > 1 else 0.0
    ci = float("nan")
    if len(a) > 1:
        try:
            from scipy.stats import t as tdist
            ci = float(tdist.ppf(0.975, len(a) - 1) * std / np.sqrt(len(a)))
        except Exception:
            ci = 1.96 * std / np.sqrt(len(a))
    return dict(mean=float(a.mean()), std=std, min=float(a.min()), max=float(a.max()), ci95=ci, n=int(len(a)))


# ----------------------------------------------------------------------------- các bước

def stage_audit(a):
    path = a.cache / "audit.json"
    if path.exists() and not a.force:
        log("audit: đã có, bỏ qua")
        return
    log("audit: nạp train + test")
    Xtr, ytr = load_set("train_set.parquet", a.sample_frac)
    Xte, yte = load_set("test_set.parquet", a.sample_frac)
    htr, hte = row_hash(Xtr), row_hash(Xte)
    del Xtr, Xte
    h = np.concatenate([htr, hte])
    y = np.concatenate([ytr, yte])
    df = pd.DataFrame({"h": h, "y": y})
    n = len(df)
    log(f"audit: {n:,} dòng, tính trùng và mâu thuẫn")

    exact_dup = df.duplicated(["h", "y"])                       # trùng hoàn toàn (đặc trưng + nhãn) với một dòng trước đó
    n_labels = df.groupby("h")["y"].transform("nunique")
    conflict = n_labels > 1                                       # vector đặc trưng xuất hiện với >1 nhãn

    cnt = df.groupby(["h", "y"]).size().rename("n").reset_index()
    cnt["mx"] = cnt.groupby("h")["n"].transform("max")
    cnt["win"] = cnt["n"] == cnt["mx"]
    acc_ceiling = 100 * cnt.groupby("h")["mx"].first().sum() / n
    rec_ceiling = (cnt[cnt.win].groupby("y")["n"].sum() / cnt.groupby("y")["n"].sum() * 100).to_dict()

    test_in_train = np.isin(hte, htr)
    per_class = []
    for c in sorted(np.unique(y)):
        m = y == c
        mt = yte == c
        per_class.append(dict(
            label=c, rows=int(m.sum()), unique_vectors=int(df.loc[m, "h"].nunique()),
            exact_dup_rows=int(exact_dup[m].sum()), exact_dup_pct=100 * float(exact_dup[m].mean()),
            conflict_rows=int(conflict[m].sum()), conflict_pct=100 * float(conflict[m].mean()),
            recall_ceiling_pct=float(rec_ceiling.get(c, 100.0)),
            test_rows=int(mt.sum()), test_rows_also_in_train=int(test_in_train[mt].sum()),
            test_in_train_pct=100 * float(test_in_train[mt].mean()) if mt.any() else float("nan")))

    # Các cặp nhãn hay mâu thuẫn với nhau nhất
    conf_groups = df[conflict].groupby("h")["y"].agg(lambda s: " | ".join(sorted(set(s))))
    pairs = conf_groups.value_counts().head(15)
    out = dict(rows=n, unique_vectors=int(df["h"].nunique()), exact_dup_rows=int(exact_dup.sum()),
               exact_dup_pct=100 * float(exact_dup.mean()), conflict_rows=int(conflict.sum()),
               conflict_pct=100 * float(conflict.mean()), conflict_vectors=int(conf_groups.shape[0]),
               accuracy_ceiling_pct=float(acc_ceiling),
               test_rows=int(len(yte)), test_rows_also_in_train=int(test_in_train.sum()),
               test_in_train_pct=100 * float(test_in_train.mean()),
               top_conflict_label_sets={k: int(v) for k, v in pairs.items()},
               per_class=per_class)
    save_json(out, path)
    log(f"audit: xong. Trùng hoàn toàn {out['exact_dup_pct']:.2f}% | dòng mâu thuẫn nhãn {out['conflict_pct']:.3f}% "
        f"| trần accuracy {acc_ceiling:.3f}% | test trùng train {out['test_in_train_pct']:.2f}%")


def stage_cv(a):
    log("cv: nạp train_set.parquet (tập test chính thức không dùng ở bước này)")
    X, y_raw = load_set("train_set.parquet", a.sample_frac)
    le, y, benign = encode(y_raw)
    K = len(le.classes_)
    h = row_hash(X)
    splits = cv_splits(y, a.folds)
    rng = np.random.default_rng(CV_SEED)
    for k, (tr, va) in enumerate(splits):
        path = a.cache / f"cv_fold{k}.json"
        if path.exists() and not a.force:
            log(f"cv: fold {k} đã có, bỏ qua")
            continue
        log(f"cv: fold {k + 1}/{a.folds} | train {len(tr):,} | val {len(va):,}")
        Xtr, ytr, Xva, yva = X[tr], y[tr], X[va], y[va]
        sub = rng.choice(len(tr), min(len(tr), a.train_eval_rows), replace=False)
        model = make_model()
        sec = fit(model, Xtr, ytr, evals=[(Xtr[sub], ytr[sub]), (Xva, yva)])
        p_tr, p_va = model.predict(Xtr), model.predict(Xva)
        clean = ~np.isin(h[va], h[tr])
        rec = dict(fold=k, train_seconds=sec, n_train=int(len(tr)), n_val=int(len(va)),
                   val_dup_with_train=int((~clean).sum()), classes=list(le.classes_),
                   train=scores(ytr, p_tr, K, benign), val=scores(yva, p_va, K, benign),
                   val_clean=scores(yva[clean], p_va[clean], K, benign), curve=get_curves(model))
        save_json(rec, path)
        log(f"cv: fold {k + 1} xong sau {sec / 60:.1f} phút | train F1 {rec['train']['macro_f1']:.2f} "
            f"| val F1 {rec['val']['macro_f1']:.2f} | val sạch F1 {rec['val_clean']['macro_f1']:.2f}")
        del Xtr, Xva, model


def stage_curve(a):
    path = a.cache / "curve_long.json"
    if path.exists() and not a.force:
        log("curve: đã có, bỏ qua")
        return
    X, y_raw = load_set("train_set.parquet", a.sample_frac)
    le, y, benign = encode(y_raw)
    K = len(le.classes_)
    tr, va = cv_splits(y, a.folds)[0]
    Xtr, ytr, Xva, yva = X[tr], y[tr], X[va], y[va]
    del X
    sub = np.random.default_rng(CV_SEED).choice(len(tr), min(len(tr), a.train_eval_rows), replace=False)
    log(f"curve: fold 0, {a.curve_rounds} cây (cấu hình giữ nguyên, chỉ kéo dài số cây để quan sát)")
    model = make_model(n_estimators=a.curve_rounds)
    sec = fit(model, Xtr, ytr, evals=[(Xtr[sub], ytr[sub]), (Xva, yva)])
    checkpoints = sorted({c for c in [10, 25, 50, 75, 100, 150, 200, 250, 300, 400, 500] if c <= a.curve_rounds} | {a.curve_rounds})
    f1_at = []
    for c in checkpoints:
        st = scores(ytr[sub], predict_at(model, Xtr[sub], c), K, benign)
        sv = scores(yva, predict_at(model, Xva, c), K, benign)
        f1_at.append(dict(trees=c, train_macro_f1=st["macro_f1"], val_macro_f1=sv["macro_f1"],
                          train_accuracy=st["accuracy"], val_accuracy=sv["accuracy"], val_fpr=sv["fpr"], val_fnr=sv["fnr"]))
        log(f"curve: {c:>4} cây | train F1 {st['macro_f1']:.2f} | val F1 {sv['macro_f1']:.2f}")
    save_json(dict(rounds=a.curve_rounds, train_seconds=sec, curve=get_curves(model), f1_at=f1_at), path)


def stage_learning(a):
    X, y_raw = load_set("train_set.parquet", a.sample_frac)
    le, y, benign = encode(y_raw)
    K = len(le.classes_)
    tr, va = cv_splits(y, a.folds)[0]
    Xva, yva = X[va], y[va]
    for frac in LEARN_FRACS:
        path = a.cache / f"learning_{int(frac * 100):03d}.json"
        if path.exists() and not a.force:
            log(f"learning: {frac:.0%} đã có, bỏ qua")
            continue
        fold0 = a.cache / "cv_fold0.json"
        if frac == 1.0 and fold0.exists() and not a.force:
            r = load_json(fold0)   # 100% chính là fold 0 của bước cv, dùng lại
            save_json(dict(frac=1.0, n_train=r["n_train"], train_seconds=r["train_seconds"],
                           train=r["train"], val=r["val"], reused_from="cv_fold0"), path)
            log("learning: 100% dùng lại kết quả fold 0 của bước cv")
            continue
        pick = tr[stratified_take(y[tr], frac, np.random.default_rng(CV_SEED))] if frac < 1 else tr
        log(f"learning: {frac:.0%} dữ liệu train = {len(pick):,} dòng")
        model = make_model()
        sec = fit(model, X[pick], y[pick])
        rec = dict(frac=frac, n_train=int(len(pick)), train_seconds=sec,
                   train=scores(y[pick], model.predict(X[pick]), K, benign),
                   val=scores(yva, model.predict(Xva), K, benign))
        save_json(rec, path)
        log(f"learning: {frac:.0%} | train F1 {rec['train']['macro_f1']:.2f} | val F1 {rec['val']['macro_f1']:.2f}")


def stage_resplit(a):
    log("resplit: nạp và gộp train + test")
    Xa, ya = load_set("train_set.parquet", a.sample_frac)
    Xb, yb = load_set("test_set.parquet", a.sample_frac)
    X = np.concatenate([Xa, Xb])
    y_raw = np.concatenate([ya, yb])
    del Xa, Xb
    le, y, benign = encode(y_raw)
    K = len(le.classes_)
    h = row_hash(X)
    for s in range(1, a.seeds + 1):
        path = a.cache / f"resplit_seed{s}.json"
        if path.exists() and not a.force:
            log(f"resplit: seed {s} đã có, bỏ qua")
            continue
        tr, te = train_test_split(np.arange(len(y)), test_size=0.2, stratify=y, random_state=s)
        model = make_model(seed=s)
        sec = fit(model, X[tr], y[tr])
        pred = model.predict(X[te])
        clean = ~np.isin(h[te], h[tr])
        rec = dict(seed=s, train_seconds=sec, n_train=int(len(tr)), n_test=int(len(te)),
                   test_dup_with_train=int((~clean).sum()), classes=list(le.classes_),
                   full=scores(y[te], pred, K, benign), clean=scores(y[te][clean], pred[clean], K, benign))
        save_json(rec, path)
        log(f"resplit: seed {s}/{a.seeds} xong sau {sec / 60:.1f} phút | F1 {rec['full']['macro_f1']:.2f} "
            f"| F1 sạch {rec['clean']['macro_f1']:.2f} | FPR {rec['full']['fpr']:.3f} | FNR {rec['full']['fnr']:.3f}")
        del model


# ----------------------------------------------------------------------------- báo cáo

def read_official():
    out = {}
    if not OFFICIAL_CSV.exists():
        return out
    df = pd.read_csv(OFFICIAL_CSV, encoding="utf-8-sig")
    keymap = {"Accuracy": "accuracy", "Macro Precision": "macro_precision", "Macro Recall": "macro_recall",
              "Macro F1": "macro_f1", "FPR": "fpr", "FNR": "fnr"}
    for _, r in df.iterrows():
        name, val = str(r.iloc[0]), str(r.iloc[1])
        for k, v in keymap.items():
            if k in name and v not in out:
                try:
                    out[v] = float(val.split("%")[0])
                except ValueError:
                    pass
    return out


def fmt(x, d=2):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{d}f}"


def ms(s, d=2):
    return f"{fmt(s['mean'], d)} ± {fmt(s['std'], d)}"


def md_table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def plot_setup():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt
    except Exception as e:  # noqa: BLE001
        log(f"report: không vẽ được biểu đồ ({e})")
        return None


def stage_report(a):
    out, cache = a.out, a.cache
    plt = plot_setup()
    md = ["# RQ1 – Cách 1: độ ổn định và chẩn đoán overfit/underfit của XGBoost",
          "",
          f"Cấu hình cố định: max_depth={CFG['max_depth']}, learning_rate={CFG['learning_rate']}, "
          f"n_estimators={CFG['n_estimators']}, tree_method=hist (đúng mô hình chính thức). "
          "Không chọn lại siêu tham số, mô hình chính thức trong saved_models/ không bị thay đổi.",
          ""]
    if a.sample_frac:
        md += [f"> **CHẠY THỬ trên {a.sample_frac:.0%} dữ liệu. Số liệu dưới đây không dùng để báo cáo.**", ""]
    official = read_official()
    audit = load_json(cache / "audit.json") if (cache / "audit.json").exists() else None
    audit_cls = {r["label"]: r for r in audit["per_class"]} if audit else {}

    # 1. Audit -----------------------------------------------------------------
    if audit:
        md += ["## 1. Dòng trùng và nhãn mâu thuẫn (train + test)", "",
               md_table(["Chỉ số", "Giá trị"], [
                   ["Tổng số dòng", f"{audit['rows']:,}"],
                   ["Số vector đặc trưng khác nhau", f"{audit['unique_vectors']:,}"],
                   ["Dòng trùng hoàn toàn (cùng đặc trưng, cùng nhãn)", f"{audit['exact_dup_rows']:,} ({fmt(audit['exact_dup_pct'])}%)"],
                   ["Dòng có nhãn mâu thuẫn (cùng đặc trưng, khác nhãn)", f"{audit['conflict_rows']:,} ({fmt(audit['conflict_pct'], 3)}%)"],
                   ["Dòng test giống hệt một dòng train (tập chia chính thức)", f"{audit['test_rows_also_in_train']:,} ({fmt(audit['test_in_train_pct'])}%)"],
                   ["Trần accuracy lý thuyết", f"{fmt(audit['accuracy_ceiling_pct'], 3)}%"]]),
               "",
               "Trần accuracy là mức cao nhất mà bất kỳ mô hình nào đạt được khi chỉ nhìn 78 đặc trưng: "
               "với một vector xuất hiện dưới nhiều nhãn, mô hình chỉ đoán đúng được nhãn chiếm đa số.",
               ""]
        rows = sorted(audit["per_class"], key=lambda r: -r["conflict_pct"])
        md += ["Theo từng lớp (xếp theo tỷ lệ mâu thuẫn nhãn):", "",
               md_table(["Lớp", "Số dòng", "Trùng hoàn toàn %", "Mâu thuẫn nhãn %", "Trần recall %", "Test trùng train %"],
                        [[r["label"], f"{r['rows']:,}", fmt(r["exact_dup_pct"]), fmt(r["conflict_pct"]),
                          fmt(r["recall_ceiling_pct"]), fmt(r["test_in_train_pct"])] for r in rows]),
               ""]
        if audit["top_conflict_label_sets"]:
            md += ["Các nhóm nhãn hay dùng chung một vector đặc trưng (số vector):", "",
                   md_table(["Nhóm nhãn", "Số vector"], [[k, f"{v:,}"] for k, v in audit["top_conflict_label_sets"].items()]), ""]
        pd.DataFrame(audit["per_class"]).to_csv(out / "01_audit_theo_lop.csv", index=False, encoding="utf-8-sig")

    # 2. CV --------------------------------------------------------------------
    folds = [load_json(p) for p in sorted(cache.glob("cv_fold*.json"))]
    cv_cls = None
    if folds:
        classes = folds[0]["classes"]
        rows = []
        for f in folds:
            for part in ("train", "val", "val_clean"):
                rows.append(dict(fold=f["fold"], phan=part, n=f[part]["n"], **{m: f[part][m] for m in METRICS},
                                 train_seconds=f["train_seconds"]))
        pd.DataFrame(rows).to_csv(out / "02_cv_theo_fold.csv", index=False, encoding="utf-8-sig")
        summ = {part: {m: summarize([f[part][m] for f in folds]) for m in METRICS} for part in ("train", "val", "val_clean")}
        gap = summarize([f["train"]["macro_f1"] - f["val"]["macro_f1"] for f in folds])
        save_json(dict(summary=summ, gap_macro_f1=gap, n_folds=len(folds)), out / "02_cv_tom_tat.json")

        md += [f"## 2. Cross-validation {len(folds)} fold trên tập train (tập test chính thức không dùng)", "",
               "Giá trị: trung bình ± độ lệch chuẩn qua các fold, đơn vị %.", "",
               md_table(["Chỉ số", "Phần train của fold", "Validation", "Validation sạch", "Chính thức RQ1 (test)"],
                        [[METRIC_VI[m], ms(summ["train"][m], 3 if m == "fpr" else 2), ms(summ["val"][m], 3 if m == "fpr" else 2),
                          ms(summ["val_clean"][m], 3 if m == "fpr" else 2), fmt(official.get(m), 3 if m == "fpr" else 2)]
                         for m in METRICS]),
               "",
               f"Validation sạch: bỏ các dòng validation giống hệt một dòng train của cùng fold "
               f"(trung bình {np.mean([f['val_dup_with_train'] / f['n_val'] * 100 for f in folds]):.1f}% số dòng validation).",
               ""]
        sv = summ["val"]["macro_f1"]
        verdict_stab = ("ổn định" if sv["std"] < 1 else "dao động đáng kể")
        g = gap["mean"]
        verdict_fit = ("không có dấu hiệu overfit đáng kể" if g <= 2 else
                       "overfit nhẹ" if g <= 5 else "overfit rõ")
        md += ["**Đọc kết quả:**", "",
               f"- Độ ổn định: Macro F1 validation dao động {fmt(sv['std'])} điểm giữa các fold "
               f"(thấp nhất {fmt(sv['min'])}, cao nhất {fmt(sv['max'])}), mô hình {verdict_stab}.",
               f"- Overfit: Macro F1 trên phần train cao hơn validation trung bình {fmt(g)} điểm, {verdict_fit} "
               "(quy ước: ≤ 2 điểm là không đáng kể, 2–5 điểm là nhẹ, > 5 điểm là rõ).",
               (f"- Underfit: Macro F1 ngay trên phần train chỉ đạt {fmt(summ['train']['macro_f1']['mean'])}%, "
                "tức mô hình chưa khớp được một số lớp ngay cả trên dữ liệu đã học. "
                "Bảng theo lớp bên dưới cho biết đó là lớp nào; đối chiếu với tỷ lệ mâu thuẫn nhãn ở mục 1."
                if summ["train"]["macro_f1"]["mean"] < 95 else
                f"- Underfit: Macro F1 trên phần train đạt {fmt(summ['train']['macro_f1']['mean'])}%, "
                "mô hình khớp tốt dữ liệu đã học, không có dấu hiệu underfit tổng thể."),
               ""]
        if official.get("macro_f1") is not None:
            md += [f"- So với tập test chính thức: Macro F1 test = {fmt(official['macro_f1'])}%, "
                   f"{'nằm trong' if abs(official['macro_f1'] - sv['mean']) <= 2 * sv['std'] + 1e-9 else 'nằm ngoài'} "
                   f"khoảng trung bình ± 2 độ lệch chuẩn của CV ({fmt(sv['mean'] - 2 * sv['std'])}–{fmt(sv['mean'] + 2 * sv['std'])}).", ""]

        # Theo lớp
        recs = []
        for i, c in enumerate(classes):
            tf = [f["train"]["per_class"]["f1"][i] for f in folds]
            vf = [f["val"]["per_class"]["f1"][i] for f in folds]
            vcf = [f["val_clean"]["per_class"]["f1"][i] for f in folds if f["val_clean"]["per_class"]["support"][i] > 0]
            vr = [f["val"]["per_class"]["recall"][i] for f in folds]
            sup = int(np.sum([f["val"]["per_class"]["support"][i] for f in folds]))
            t_m, v_m = float(np.mean(tf)), float(np.mean(vf))
            a_c = audit_cls.get(c, {})
            if t_m < 90:
                verdict = "Underfit: train cũng thấp" + (" (do mâu thuẫn nhãn)" if a_c.get("conflict_pct", 0) >= 5 else "")
            elif t_m - v_m > 5:
                verdict = "Overfit: train cao, val thấp" + (" (lớp rất ít mẫu)" if sup < 500 else "")
            else:
                verdict = "Tốt"
            recs.append(dict(lop=c, so_mau_val=sup, train_f1=t_m, val_f1=v_m, val_f1_std=float(np.std(vf, ddof=1)) if len(vf) > 1 else 0.0,
                             val_sach_f1=float(np.mean(vcf)) if vcf else float("nan"), val_recall=float(np.mean(vr)),
                             chenh_train_val=t_m - v_m, mau_thuan_nhan_pct=a_c.get("conflict_pct", float("nan")),
                             tran_recall_pct=a_c.get("recall_ceiling_pct", float("nan")), nhan_xet=verdict))
        cv_cls = pd.DataFrame(recs)
        cv_cls.to_csv(out / "02_cv_theo_lop.csv", index=False, encoding="utf-8-sig")
        md += ["F1 theo từng lớp (%, trung bình qua các fold):", "",
               md_table(["Lớp", "Mẫu val", "Train F1", "Val F1", "± std", "Val sạch F1", "Chênh", "Mâu thuẫn %", "Trần recall %", "Nhận xét"],
                        [[r.lop, f"{r.so_mau_val:,}", fmt(r.train_f1), fmt(r.val_f1), fmt(r.val_f1_std), fmt(r.val_sach_f1),
                          fmt(r.chenh_train_val), fmt(r.mau_thuan_nhan_pct), fmt(r.tran_recall_pct), r.nhan_xet]
                         for r in cv_cls.sort_values("val_f1").itertuples()]),
               "",
               "Quy ước nhận xét: Train F1 < 90% là underfit (mô hình chưa khớp được lớp này ngay trên dữ liệu đã học); "
               "Train F1 – Val F1 > 5 điểm là overfit; còn lại là tốt.",
               ""]

        if plt:
            fig, ax = plt.subplots(figsize=(9, 6))
            d = cv_cls.sort_values("val_f1")
            yy = np.arange(len(d))
            ax.barh(yy - 0.2, d.train_f1, 0.4, label="Train F1", color="#9bb7d4")
            ax.barh(yy + 0.2, d.val_f1, 0.4, xerr=d.val_f1_std, label="Validation F1", color="#1f4e79")
            ax.set_yticks(yy, d.lop)
            ax.set_xlabel("F1 (%)")
            ax.set_xlim(0, 105)
            ax.set_title("F1 theo lớp: train so với validation (CV)")
            ax.legend(loc="lower right")
            fig.tight_layout()
            fig.savefig(out / "02_cv_f1_theo_lop.png", dpi=150)
            plt.close(fig)

            curves = [f["curve"] for f in folds if f.get("curve")]
            if curves and "train" in curves[0]:
                fig, axes = plt.subplots(1, 2, figsize=(11, 4))
                for ax, metric, title in ((axes[0], "mlogloss", "Log loss"), (axes[1], "merror", "Tỷ lệ lỗi")):
                    for part, color in (("train", "#9bb7d4"), ("val", "#1f4e79")):
                        arr = np.array([c[part][metric] for c in curves])
                        x = np.arange(1, arr.shape[1] + 1)
                        ax.plot(x, arr.mean(0), color=color, label=f"{'Train' if part == 'train' else 'Validation'} (TB {len(curves)} fold)")
                        ax.fill_between(x, arr.min(0), arr.max(0), color=color, alpha=0.2)
                    ax.set_xlabel("Số cây")
                    ax.set_title(title)
                    ax.set_yscale("log")
                    ax.legend()
                fig.suptitle("Đường cong học theo số cây (CV, 100 cây)")
                fig.tight_layout()
                fig.savefig(out / "03_loss_theo_so_cay_cv.png", dpi=150)
                plt.close(fig)

    # 3. Đường cong mở rộng ------------------------------------------------------
    if (cache / "curve_long.json").exists():
        cl = load_json(cache / "curve_long.json")
        tr_l = np.array(cl["curve"]["train"]["mlogloss"])
        va_l = np.array(cl["curve"]["val"]["mlogloss"])
        best = int(va_l.argmin()) + 1
        at100 = float(va_l[min(99, len(va_l) - 1)])
        rise = (va_l[-1] - va_l.min()) / va_l.min() * 100
        gain_after_100 = (at100 - va_l.min()) / at100 * 100
        pd.DataFrame(dict(so_cay=np.arange(1, len(va_l) + 1), train_mlogloss=tr_l, val_mlogloss=va_l,
                          train_merror=cl["curve"]["train"]["merror"], val_merror=cl["curve"]["val"]["merror"])
                     ).to_csv(out / "03_loss_theo_so_cay_fold0.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame(cl["f1_at"]).to_csv(out / "03_f1_theo_so_cay_fold0.csv", index=False, encoding="utf-8-sig")
        if best < 100 and rise > 1:
            vtxt = f"Loss validation thấp nhất ở cây {best} rồi tăng lại: dấu hiệu overfit khi dùng nhiều cây hơn."
        elif best > 100 and gain_after_100 > 1:
            vtxt = (f"Loss validation còn giảm sau 100 cây (thấp nhất ở cây {best}, thấp hơn mức ở 100 cây {fmt(gain_after_100)}%): "
                    "100 cây hơi ít, mô hình còn có thể khớp thêm (underfit nhẹ theo số cây).")
        else:
            vtxt = (f"Loss validation gần như đi ngang quanh 100 cây (thấp nhất ở cây {best}, chênh {fmt(gain_after_100)}% so với 100 cây; "
                    f"tăng {fmt(rise)}% ở cây cuối): 100 cây là hợp lý, không overfit, không thiếu cây.")
        md += [f"## 3. Đường cong loss mở rộng tới {cl['rounds']} cây (fold 0)", "",
               "Cấu hình giữ nguyên, chỉ kéo dài số cây để xem điều gì xảy ra sau mốc 100 cây đang dùng.", "",
               md_table(["Số cây", "Train F1", "Val F1", "Val Accuracy", "Val FPR", "Val FNR"],
                        [[r["trees"], fmt(r["train_macro_f1"]), fmt(r["val_macro_f1"]), fmt(r["val_accuracy"]),
                          fmt(r["val_fpr"], 3), fmt(r["val_fnr"], 3)] for r in cl["f1_at"]]),
               "", f"**Đọc kết quả:** {vtxt}", ""]
        if plt:
            fig, axes = plt.subplots(1, 2, figsize=(11, 4))
            x = np.arange(1, len(va_l) + 1)
            axes[0].plot(x, tr_l, color="#9bb7d4", label="Train")
            axes[0].plot(x, va_l, color="#1f4e79", label="Validation")
            axes[0].axvline(100, color="grey", ls="--", lw=1)
            axes[0].axvline(best, color="#c00000", ls=":", lw=1, label=f"Val thấp nhất (cây {best})")
            axes[0].set_yscale("log")
            axes[0].set_xlabel("Số cây")
            axes[0].set_title("Log loss")
            axes[0].legend()
            fa = pd.DataFrame(cl["f1_at"])
            axes[1].plot(fa.trees, fa.train_macro_f1, "o-", color="#9bb7d4", label="Train")
            axes[1].plot(fa.trees, fa.val_macro_f1, "o-", color="#1f4e79", label="Validation")
            axes[1].axvline(100, color="grey", ls="--", lw=1)
            axes[1].set_xlabel("Số cây")
            axes[1].set_title("Macro F1 (%)")
            axes[1].legend()
            fig.suptitle("Đường cong theo số cây (fold 0, đường đứt: 100 cây đang dùng)")
            fig.tight_layout()
            fig.savefig(out / "03_loss_mo_rong_fold0.png", dpi=150)
            plt.close(fig)

    # 4. Learning curve ---------------------------------------------------------
    lc = [load_json(p) for p in sorted(cache.glob("learning_*.json"))]
    if lc:
        lc.sort(key=lambda r: r["frac"])
        df = pd.DataFrame([dict(ty_le=r["frac"], so_dong_train=r["n_train"], train_f1=r["train"]["macro_f1"],
                                val_f1=r["val"]["macro_f1"], val_accuracy=r["val"]["accuracy"],
                                val_fpr=r["val"]["fpr"], val_fnr=r["val"]["fnr"]) for r in lc])
        df.to_csv(out / "04_learning_curve.csv", index=False, encoding="utf-8-sig")
        txt = ""
        if len(df) >= 2:
            last_gain = df.val_f1.iloc[-1] - df.val_f1.iloc[-2]
            gap_last = df.train_f1.iloc[-1] - df.val_f1.iloc[-1]
            txt = (f"Tăng dữ liệu từ {df.ty_le.iloc[-2]:.0%} lên {df.ty_le.iloc[-1]:.0%} làm val F1 thay đổi {fmt(last_gain)} điểm. "
                   + ("Đường cong đã gần bão hòa: thêm dữ liệu cùng loại khó cải thiện thêm. " if abs(last_gain) < 0.5 else
                      "Val F1 còn tăng rõ: thêm dữ liệu (nhất là lớp hiếm) có thể còn giúp. ")
                   + f"Khoảng cách train–val ở mức 100% là {fmt(gap_last)} điểm"
                   + (", khoảng cách nhỏ nên vấn đề chính không phải overfit." if gap_last <= 2 else
                      ", khoảng cách còn rộng: có phần overfit hoặc lớp hiếm quá ít mẫu."))
        md += ["## 4. Learning curve (fold 0)", "",
               "Huấn luyện cùng cấu hình trên một phần dữ liệu train của fold 0, đo trên cùng phần validation.", "",
               md_table(["Tỷ lệ dữ liệu", "Số dòng train", "Train F1", "Val F1", "Val Accuracy", "Val FPR", "Val FNR"],
                        [[f"{r.ty_le:.0%}", f"{r.so_dong_train:,}", fmt(r.train_f1), fmt(r.val_f1), fmt(r.val_accuracy),
                          fmt(r.val_fpr, 3), fmt(r.val_fnr, 3)] for r in df.itertuples()]),
               "", f"**Đọc kết quả:** {txt}", "",
               "Cách đọc: hai đường cùng thấp và sát nhau là underfit; hai đường cách xa nhau và đường validation "
               "còn đi lên là overfit hoặc thiếu dữ liệu; hai đường cao và sát nhau là tốt.", ""]
        if plt:
            fig, ax = plt.subplots(figsize=(6.5, 4))
            ax.plot(df.so_dong_train, df.train_f1, "o-", color="#9bb7d4", label="Train")
            ax.plot(df.so_dong_train, df.val_f1, "o-", color="#1f4e79", label="Validation")
            ax.set_xscale("log")
            ax.set_xlabel("Số dòng train (thang log)")
            ax.set_ylabel("Macro F1 (%)")
            ax.set_title("Learning curve")
            ax.legend()
            fig.tight_layout()
            fig.savefig(out / "04_learning_curve.png", dpi=150)
            plt.close(fig)

    # 5. Resplit -----------------------------------------------------------------
    rs = [load_json(p) for p in sorted(cache.glob("resplit_seed*.json"), key=lambda p: int(p.stem.split("seed")[1]))]
    if rs:
        rows = [dict(seed=r["seed"], phan=part, n=r[part]["n"], **{m: r[part][m] for m in METRICS}, train_seconds=r["train_seconds"])
                for r in rs for part in ("full", "clean")]
        pd.DataFrame(rows).to_csv(out / "05_chia_lai_80_20_theo_seed.csv", index=False, encoding="utf-8-sig")
        summ = {part: {m: summarize([r[part][m] for r in rs]) for m in METRICS} for part in ("full", "clean")}
        save_json(dict(summary=summ, n_seeds=len(rs)), out / "05_chia_lai_tom_tat.json")
        dup = np.mean([r["test_dup_with_train"] / r["n_test"] * 100 for r in rs])
        md += [f"## 5. Chia lại 80/20 với {len(rs)} seed (gộp train + test)", "",
               "Giá trị: trung bình ± độ lệch chuẩn [khoảng tin cậy 95%], đơn vị %.", "",
               md_table(["Chỉ số", "Test đầy đủ", "Test sạch", "Chính thức RQ1"],
                        [[METRIC_VI[m],
                          f"{ms(summ['full'][m], 3 if m == 'fpr' else 2)} [±{fmt(summ['full'][m]['ci95'], 3 if m == 'fpr' else 2)}]",
                          f"{ms(summ['clean'][m], 3 if m == 'fpr' else 2)} [±{fmt(summ['clean'][m]['ci95'], 3 if m == 'fpr' else 2)}]",
                          fmt(official.get(m), 3 if m == "fpr" else 2)] for m in METRICS]),
               "",
               f"Test sạch: bỏ các dòng test giống hệt một dòng train (trung bình {dup:.1f}% số dòng test).", ""]
        f1 = summ["full"]["macro_f1"]
        if official.get("macro_f1") is not None:
            inside = f1["min"] - 1e-9 <= official["macro_f1"] <= f1["max"] + 1e-9
            md += [f"**Đọc kết quả:** kết quả chính thức Macro F1 {fmt(official['macro_f1'])}% "
                   f"{'nằm trong' if inside else 'nằm ngoài'} khoảng các lần chia lại ({fmt(f1['min'])}–{fmt(f1['max'])}). "
                   f"Độ lệch chuẩn {fmt(f1['std'])} điểm cho thấy cách chia ngẫu nhiên "
                   f"{'ảnh hưởng rất ít' if f1['std'] < 1 else 'ảnh hưởng đáng kể'} tới kết quả. "
                   f"Bỏ dòng trùng làm Macro F1 giảm {fmt(f1['mean'] - summ['clean']['macro_f1']['mean'])} điểm: "
                   "một phần điểm trên test đầy đủ đến từ các dòng mô hình đã thấy y hệt khi train.", ""]
        old = sorted(OLD_REPEAT.glob("seed_*.json")) if OLD_REPEAT.exists() else []
        if old and not a.sample_frac:
            cmp_rows = []
            for p in old:
                o = load_json(p)
                n = next((r for r in rs if r["seed"] == o["seed"]), None)
                if n:
                    cmp_rows.append([o["seed"], fmt(o["full"]["macro_f1"]), fmt(n["full"]["macro_f1"]),
                                     fmt(o["dedup"]["macro_f1"]), fmt(n["clean"]["macro_f1"])])
            if cmp_rows:
                md += ["Kiểm tra tái lập với lần chạy cũ (3_repeat_resplits.py, cùng seed):", "",
                       md_table(["Seed", "F1 cũ", "F1 lần này", "F1 sạch cũ", "F1 sạch lần này"], cmp_rows), ""]
        if plt:
            fig, ax = plt.subplots(figsize=(6.5, 4))
            ax.boxplot([[r["full"]["macro_f1"] for r in rs], [r["clean"]["macro_f1"] for r in rs]])
            ax.set_xticks([1, 2], ["Test đầy đủ", "Test sạch"])
            if official.get("macro_f1") is not None:
                ax.axhline(official["macro_f1"], color="#c00000", ls="--", lw=1, label="Chính thức RQ1")
                ax.legend()
            ax.set_ylabel("Macro F1 (%)")
            ax.set_title(f"Macro F1 qua {len(rs)} lần chia lại 80/20")
            fig.tight_layout()
            fig.savefig(out / "05_chia_lai_80_20.png", dpi=150)
            plt.close(fig)

    # Kết luận ngắn ------------------------------------------------------------------
    if cv_cls is not None:
        under = cv_cls[cv_cls.nhan_xet.str.startswith("Underfit")].lop.tolist()
        over = cv_cls[cv_cls.nhan_xet.str.startswith("Overfit")].lop.tolist()
        md += ["## 6. Tóm tắt", "",
               f"- Lớp underfit (train F1 < 90%): {', '.join(under) if under else 'không có'}.",
               f"- Lớp overfit (train cao hơn val > 5 điểm): {', '.join(over) if over else 'không có'}.",
               "- Các lớp còn lại được học tốt và tổng quát hóa tốt.",
               "- Mọi kết luận trên dựa trên cấu hình cố định của mô hình chính thức; mô hình đã lưu không bị thay đổi.", ""]
    (out / "BAO_CAO_CACH1.md").write_text("\n".join(md), encoding="utf-8")
    log(f"report: đã ghi {out / 'BAO_CAO_CACH1.md'}")


# ----------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", default="all", choices=["audit", "cv", "curve", "learning", "resplit", "report", "all"])
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--seeds", type=int, default=10, help="số lần chia lại 80/20 (seed 1..N)")
    ap.add_argument("--curve-rounds", type=int, default=300, help="số cây cho đường cong mở rộng")
    ap.add_argument("--train-eval-rows", type=int, default=200_000, help="số dòng train lấy mẫu để vẽ loss train theo từng cây")
    ap.add_argument("--sample-frac", type=float, default=0.0, help="chạy thử trên một phần dữ liệu (ví dụ 0.02)")
    ap.add_argument("--force", action="store_true", help="chạy lại cả phần đã có trong _cache")
    a = ap.parse_args()
    a.out = HERE / "results" / ("cv_diagnostics_thu" if a.sample_frac else "cv_diagnostics")
    a.cache = a.out / "_cache"
    a.cache.mkdir(parents=True, exist_ok=True)
    log(f"Đầu ra: {a.out}")
    stages = ["audit", "cv", "curve", "learning", "resplit", "report"] if a.stage == "all" else [a.stage]
    t0 = time.time()
    for s in stages:
        globals()[f"stage_{s}"](a)
        if s != "report" and a.stage == "all":
            stage_report(a)   # cập nhật báo cáo sau mỗi bước, dừng giữa chừng vẫn có báo cáo phần đã xong
    log(f"Hoàn tất sau {(time.time() - t0) / 60:.1f} phút")


if __name__ == "__main__":
    main()

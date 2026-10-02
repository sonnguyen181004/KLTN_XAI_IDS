"""Tinh lai SHAP tu model va test; xuat CSV va Top 5 duong/am rieng tung lop.

Ca hai nhom xep hang theo mean(abs(SHAP)); phan nhom theo dau mean(SHAP).
Khong doc CSV SHAP cu. Moi lan chay mac dinh tao mot thu muc ket qua moi.
"""
from pathlib import Path
from datetime import datetime
import argparse
import hashlib
import json
import platform
import re
import sys
import time

import joblib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import shap
import xgboost
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def save_json(path, data):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


def feature_table(features, absolute, signed, label, n):
    absolute, signed = np.asarray(absolute, float), np.asarray(signed, float)
    if not np.isfinite(absolute).all() or not np.isfinite(signed).all():
        raise ValueError('Chi so SHAP khong huu han.')
    if np.any(absolute < 0) or np.any(np.abs(signed) > absolute + 1e-6):
        raise ValueError('Mean absolute va mean signed SHAP khong nhat quan.')
    table = pd.DataFrame(dict(feature=features, mean_abs_shap_raw=absolute,
                              mean_signed_shap_raw=signed))
    if table.feature.duplicated().any():
        raise ValueError('Ten dac trung bi trung.')
    table['net_direction'] = np.where(signed > 0, 'positive', np.where(signed < 0, 'negative', 'zero'))
    # Cung mot chi so xep hang cho ca hai dau; KHONG xep theo mean_signed.
    table = table.sort_values(['mean_abs_shap_raw', 'feature'], ascending=[False, True]).reset_index(drop=True)
    table.insert(0, 'rank_overall', np.arange(1, len(table) + 1))
    table['rank_within_direction'] = pd.Series(pd.NA, index=table.index, dtype='Int64')
    for direction in ('positive', 'negative'):
        mask = table.net_direction.eq(direction)
        table.loc[mask, 'rank_within_direction'] = np.arange(1, mask.sum() + 1)
    table['is_top5_positive'] = table.net_direction.eq('positive') & table.rank_within_direction.le(5).fillna(False)
    table['is_top5_negative'] = table.net_direction.eq('negative') & table.rank_within_direction.le(5).fillna(False)
    table.insert(0, 'n_samples', int(n))
    table.insert(0, 'explained_class', label)
    table.insert(0, 'true_class', label)
    return table


def plot_top5(table, direction, path, axis_max, partial=False):
    selected = table[table['is_top5_' + direction]]
    label = table.true_class.iloc[0]
    n = int(table.n_samples.iloc[0])
    positive = direction == 'positive'
    name = 'DƯƠNG' if positive else 'ÂM'
    fig, ax = plt.subplots(figsize=(11, 5.5))
    title = f'TOP 5 NHÓM TÁC ĐỘNG RÒNG {name}\n{label} | n = {n:,} mẫu'
    if partial:
        title = 'CHẠY THỬ — CHƯA HẾT TẬP TEST\n' + title
    ax.set_title(title, fontsize=13, pad=16)
    if len(selected):
        bars = ax.barh(range(len(selected)), selected.mean_abs_shap_raw,
                       color='#C9365A' if positive else '#277EB5', height=.58)
        ax.set_yticks(range(len(selected)), selected.feature)
        ax.invert_yaxis()
        ax.bar_label(bars, labels=[f'{v:.6g}' for v in selected.mean_abs_shap_raw], padding=5, fontsize=10)
    else:
        ax.text(.5, .5, f'Không có đặc trưng có Mean signed SHAP {"> 0" if positive else "< 0"}.',
                ha='center', va='center', transform=ax.transAxes, fontsize=11)
        ax.set_yticks([])
    ax.set_xlim(0, max(axis_max, 1e-8) * 1.25)
    ax.set_xlabel('Mức quan trọng: Mean absolute SHAP (raw margin)', fontsize=11)
    ax.grid(axis='x', alpha=.2)
    ax.set_axisbelow(True)
    ax.spines[['top', 'right']].set_visible(False)
    note = f'Phân nhóm: Mean signed SHAP {"> 0" if positive else "< 0"}. Xếp hạng: Mean absolute SHAP giảm dần.'
    note += '\nDấu là tác động ròng trung bình; không khẳng định mọi mẫu cùng chiều. Âm không có nghĩa không quan trọng.'
    if len(selected) < 5:
        note += f'\nChỉ có {len(selected)} đặc trưng thuộc nhóm; không thêm số 0 để đủ 5.'
    fig.text(.5, .015, note, ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .12, 1, 1))
    fig.savefig(path, dpi=170, bbox_inches='tight')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parent,
                        help='Thu muc goc du an; mac dinh la noi dat script')
    parser.add_argument('--test-file', type=Path, help='Chi dinh parquet khac; mac dinh test_set.parquet cua du an')
    parser.add_argument('--output', type=Path, help='Thu muc ket qua MOI hoac rong')
    parser.add_argument('--batch-size', type=int, default=1000)
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--include-benign', action='store_true', help='Xuat them lop Benign de tham chieu')
    parser.add_argument('--max-batches', type=int, default=0,
                        help='0 = chay het test; gia tri > 0 chi de chay thu')
    args = parser.parse_args()
    if args.batch_size < 1 or args.threads < 1 or args.max_batches < 0:
        parser.error('batch-size/threads phai > 0; max-batches phai >= 0')
    root = args.project.resolve()
    model_path = root / 'RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl'
    encoder_path = model_path.with_name('label_encoder.pkl')
    test_path = (args.test_file or root / 'dataset/CICID-2018_processed/test_set.parquet').resolve()
    for path in (model_path, encoder_path, test_path):
        if not path.is_file():
            raise FileNotFoundError(f'Khong tim thay: {path}. Hay dat script vao thu muc goc du an hoac dung --project.')
    model, encoder = joblib.load(model_path), joblib.load(encoder_path)
    model.set_params(n_jobs=args.threads)
    features = model.get_booster().feature_names
    labels = encoder.classes_.astype(str).tolist()
    source = pq.ParquetFile(test_path)
    if not features or len(features) != len(set(features)):
        raise ValueError('Model khong co danh sach feature hop le.')
    if set(source.schema_arrow.names) != set(features) | {'Label'}:
        raise ValueError('Cot du lieu test khong khop cac feature cua model va Label.')
    if not np.array_equal(model.classes_, np.arange(len(labels))):
        raise ValueError('Anh xa lop model va label_encoder khong khop.')
    total = source.metadata.num_rows
    if total == 0:
        raise ValueError('Tap test rong.')
    out = (args.output or root / 'shap_results/top5_each_attack' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError(f'Thu muc da co du lieu: {out}. Dung --output moi hoac bo --output de tao lan chay moi.')
    out.mkdir(parents=True, exist_ok=True)
    lines = []

    def say(text):
        print(text, flush=True)
        lines.append(text)

    say(f'Tính lại SHAP từ đầu trên {total:,} dòng của: {test_path}')
    say('Mỗi lớp thật được giải thích cho chính đầu ra lớp đó, gồm cả dự đoán đúng và sai.')
    say('Hai nhóm cùng xếp theo Mean absolute SHAP; dấu Mean signed SHAP chỉ dùng phân nhóm.')
    say('Đang ghi dấu kiểm đầu vào...')
    info = dict(status='processing', protocol='mean_abs_rank_by_mean_signed_direction_v1',
        project=str(root), test_file=str(test_path), total_rows=total, processed_rows=0,
        input_sha256={str(p): sha256(p) for p in (model_path, encoder_path, test_path)},
        script_sha256=sha256(Path(__file__)), features=features, classes=labels,
        batch_size=args.batch_size, threads=args.threads, max_batches=args.max_batches,
        include_benign=args.include_benign, model_retrained=False, reused_saved_shap=False,
        shap_settings=dict(model_output='raw', feature_perturbation='tree_path_dependent', approximate=False),
        explained_output='true class on all examples of that true class, correct and wrong together',
        importance_metric='mean(abs(SHAP))', grouping='mean(SHAP)>0 positive; <0 negative; ==0 zero',
        tie_break='feature name ascending', units='raw margin',
        versions=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
                      shap=shap.__version__, xgboost=xgboost.__version__, matplotlib=matplotlib.__version__))
    save_json(out / 'run_info.json', info)
    counts = np.zeros(len(labels), dtype=np.int64)
    sum_abs = np.zeros((len(labels), len(features)), dtype=np.float64)
    sum_signed = np.zeros_like(sum_abs)
    explainer = shap.TreeExplainer(model, model_output='raw', feature_perturbation='tree_path_dependent')
    processed, max_error = 0, 0.0
    start = time.perf_counter()
    for batch_id, batch in enumerate(source.iter_batches(batch_size=args.batch_size, columns=features + ['Label'])):
        if args.max_batches and batch_id >= args.max_batches:
            break
        frame = batch.to_pandas()
        X = frame[features].astype(float)
        if not np.isfinite(X.to_numpy()).all():
            raise ValueError(f'Co NaN/Infinity tai lo {batch_id + 1}.')
        true = encoder.transform(frame.Label.astype(str))
        raw = model.predict(X, output_margin=True)
        explanation = explainer(X, check_additivity=True, approximate=False)
        values = explanation.values
        if values.shape != (len(X), len(features), len(labels)):
            raise ValueError(f'Kich thuoc SHAP khong dung (mau, feature, lop): {values.shape}')
        if not np.isfinite(values).all() or not np.isfinite(raw).all():
            raise ValueError('SHAP/model output khong huu han.')
        reconstructed = explanation.base_values + values.sum(axis=1)
        np.testing.assert_allclose(reconstructed, raw, atol=1e-4, rtol=1e-4)
        max_error = max(max_error, float(np.max(np.abs(reconstructed - raw))))
        phi = values[np.arange(len(X)), :, true].astype(np.float64)
        for c in np.unique(true):
            mask = true == c
            counts[c] += mask.sum()
            sum_abs[c] += np.abs(phi[mask]).sum(axis=0)
            sum_signed[c] += phi[mask].sum(axis=0)
        processed += len(X)
        elapsed = time.perf_counter() - start
        info.update(processed_rows=processed, shap_compute_seconds=elapsed, max_additivity_error=max_error)
        if batch_id % 10 == 0 or processed == total or args.max_batches == batch_id + 1:
            save_json(out / 'run_info.json', info)
            say(f'Đã tính {processed:,}/{total:,} mẫu ({100*processed/total:.1f}%) | {elapsed/60:.1f} phút')
    if int(counts.sum()) != processed or processed == 0:
        raise ValueError('So mau tong hop khong hop le.')
    partial = processed != total
    summary, used_names = [], set()
    for c, label in enumerate(labels):
        n = int(counts[c])
        if label == 'Benign' and not args.include_benign:
            continue
        if n == 0:
            say(f'Không có mẫu của lớp {label} trong các dòng đã xử lý; không tạo xếp hạng.')
            summary.append(dict(true_class=label, n_samples=0, status='no_samples'))
            continue
        folder_name = re.sub(r'[^A-Za-z0-9_-]+', '_', label).strip('_')
        if not folder_name or folder_name.casefold() in used_names:
            raise ValueError(f'Ten thu muc xung dot: {label}')
        used_names.add(folder_name.casefold())
        folder = out / folder_name
        folder.mkdir()
        table = feature_table(features, sum_abs[c]/n, sum_signed[c]/n, label, n)
        table['run_scope'] = 'partial_input' if partial else 'complete_input'
        table.to_csv(folder / 'feature_importance.csv', index=False, encoding='utf-8-sig')
        pos, neg = table[table.is_top5_positive], table[table.is_top5_negative]
        axis_max = max([*pos.mean_abs_shap_raw, *neg.mean_abs_shap_raw, 1e-8])
        plot_top5(table, 'positive', folder / 'top5_positive.png', axis_max, partial)
        plot_top5(table, 'negative', folder / 'top5_negative.png', axis_max, partial)
        say(f'\n{"=" * 70}\nLOẠI: {label} | n = {n:,} | Đầu ra giải thích: {label}')
        say('TOP 5 DƯƠNG — xếp theo Mean absolute SHAP (raw margin)')
        shown = pos[['rank_within_direction', 'feature', 'mean_abs_shap_raw', 'mean_signed_shap_raw']]
        say(shown.to_string(index=False, float_format=lambda v: f'{v:.8g}') if len(pos) else 'Không có đặc trưng có Mean signed SHAP > 0.')
        say(f'Đã lưu 1 CSV và 2 biểu đồ: {folder}')
        if len(neg) < 5:
            say(f'Nhóm âm chỉ có {len(neg)} đặc trưng; hình thể hiện đúng số lượng này.')
        summary.append(dict(true_class=label, n_samples=n, n_features=len(features),
            positive_count=int(table.net_direction.eq('positive').sum()),
            negative_count=int(table.net_direction.eq('negative').sum()),
            zero_count=int(table.net_direction.eq('zero').sum()), folder=folder_name, status='exported'))
    info.update(status='partial' if partial else 'complete', exported_classes=summary,
                all_class_counts={label:int(n) for label,n in zip(labels,counts)},
                seconds_including_export=time.perf_counter()-start)
    save_json(out / 'run_info.json', info)
    say(('CHẠY THỬ CHƯA HẾT TEST. ' if partial else 'HOÀN TẤT. ') + f'Kết quả: {out}')
    (out / 'terminal_top5_positive.txt').write_text('\n'.join(lines), encoding='utf-8-sig')


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    main()

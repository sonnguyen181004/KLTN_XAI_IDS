"""Full-test time-scaling sensitivity, streamed with resumable parquet checkpoints.
Requires shap_noise_robustness.py (previous pilot script) in the same directory.
"""
from pathlib import Path
import argparse
import hashlib
import json
import time
import platform
import joblib
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import shap
import xgboost
from shap_noise_robustness import rescale_time, TIME_COLUMNS, RATE_COLUMNS


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(8388608), b''):
            h.update(block)
    return h.hexdigest()


def save_json(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--batch-size', type=int, default=1000)
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--max-batches', type=int, default=0)
    args = parser.parse_args()
    if args.batch_size < 1 or args.threads < 1 or args.max_batches < 0:
        raise ValueError('Invalid arguments')
    root = args.project.resolve()
    out = args.output or root / 'shap_results/noise_full_test'
    chunks = out / 'chunks'
    chunks.mkdir(parents=True, exist_ok=True)
    model_path = root / 'RQ1_Model_Training_xboost/saved_models/best_xgboost_model.pkl'
    encoder_path = model_path.with_name('label_encoder.pkl')
    test_path = root / 'dataset/CICID-2018_processed/test_set.parquet'
    model, encoder = joblib.load(model_path), joblib.load(encoder_path)
    model.set_params(n_jobs=args.threads)
    features = model.get_booster().feature_names
    source = pq.ParquetFile(test_path)
    if features is None or set(source.schema_arrow.names) != set(features) | {'Label'}:
        raise ValueError('Feature mismatch')
    if not set(TIME_COLUMNS + RATE_COLUMNS).issubset(features):
        raise ValueError('Missing time/rate features')
    if not np.array_equal(model.classes_, np.arange(len(encoder.classes_))):
        raise ValueError('Encoder/model mismatch')
    levels, seeds = [0.01, 0.05, 0.10], [42, 123, 2026]
    config = dict(script_sha256=sha(Path(__file__)), helper_sha256=sha(Path(__file__).with_name('shap_noise_robustness.py')),
        model_sha256=sha(model_path), encoder_sha256=sha(encoder_path), test_sha256=sha(test_path),
        total_rows=source.metadata.num_rows, batch_size=args.batch_size, threads=args.threads,
        levels=levels, seeds=seeds, shap_version=shap.__version__, xgboost_version=xgboost.__version__,
        numpy_version=np.__version__, python=platform.python_version(),
        time_columns=TIME_COLUMNS, inverse_rate_columns=RATE_COLUMNS,
        explained_output='Original predicted class fixed under perturbation; raw/tree_path_dependent',
        rng='For each seed, uniform(-1,1,total_test_rows) in original parquet row order; paired across levels',
        limits='Feature-space sensitivity, not packet replay or adversarial robustness. Perturbed labels not validated. Low-support Top10 ties may inflate overlap. Repetitions not independent samples.')
    path = out / 'config.json'
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8')) != config:
            raise ValueError('Changed configuration/inputs: use a new output directory')
    else:
        if list(chunks.glob('*.parquet')):
            raise ValueError('Chunks without config')
        save_json(path, config)
    signature = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    # ~17 MB for 700k rows: makes noise independent of batches and resuming.
    directions = {s: np.random.default_rng(s).uniform(-1, 1, source.metadata.num_rows) for s in seeds}
    explainer = shap.TreeExplainer(model, model_output='raw', feature_perturbation='tree_path_dependent')
    def evaluate(frame):
        raw = model.predict(frame, output_margin=True)
        e = explainer(frame, check_additivity=True)
        if e.values.shape != (len(frame), len(features), len(encoder.classes_)):
            raise ValueError('Unexpected SHAP shape')
        reconstructed = e.base_values + e.values.sum(axis=1)
        np.testing.assert_allclose(reconstructed, raw, rtol=1e-4, atol=1e-4)
        return raw.argmax(axis=1), e.values, float(np.abs(reconstructed - raw).max())
    offset, elapsed, max_error, paths = 0, 0.0, 0.0, []
    for batch_id, batch in enumerate(source.iter_batches(batch_size=args.batch_size, columns=features + ['Label'])):
        if args.max_batches and batch_id >= args.max_batches:
            break
        count = batch.num_rows
        dest = chunks / f'batch_{batch_id:06d}.parquet'
        if dest.exists():
            saved = pq.ParquetFile(dest)
            meta = json.loads(saved.schema_arrow.metadata[b'experiment'])
            if meta['signature'] != signature or meta['start'] != offset or meta['rows'] != count or saved.metadata.num_rows != count * 10:
                raise ValueError('Checkpoint mismatch')
        else:
            started = time.perf_counter()
            frame = batch.to_pandas()
            X = frame[features].astype(float)
            true = encoder.transform(frame.Label)
            if not np.isfinite(X.to_numpy()).all():
                raise ValueError('Non-finite data')
            target, clean_values, error = evaluate(X)
            rr = np.arange(count)
            clean = clean_values[rr, :, target].astype(float)
            del clean_values
            clean_probs = model.predict_proba(X)[rr, target]
            clean_top = np.argsort(-np.abs(clean), axis=1, kind='stable')[:, :10]
            support = (np.abs(clean) > 1e-8).sum(axis=1)
            rank_clean = pd.DataFrame(np.abs(clean)).rank(axis=1).to_numpy(copy=True)
            rank_clean -= rank_clean.mean(axis=1, keepdims=True)
            denom = np.abs(clean).sum(axis=1)
            pieces = []
            for level, seed in [(0.0, 42)] + [(a, s) for a in levels for s in seeds]:
                factors = 1 + level * directions[seed][offset:offset + count]
                noisy = rescale_time(X, factors)
                if not np.isfinite(noisy.to_numpy()).all():
                    raise ValueError('Non-finite perturbation')
                pred, all_values, err = evaluate(noisy)
                error = max(error, err)
                values = all_values[rr, :, target].astype(float)
                del all_values
                probability = model.predict_proba(noisy)[rr, target]
                if level == 0:
                    pd.testing.assert_frame_equal(X, noisy)
                    np.testing.assert_array_equal(pred, target)
                    np.testing.assert_allclose(values, clean, rtol=0, atol=1e-7)
                top = np.argsort(-np.abs(values), axis=1, kind='stable')[:, :10]
                common = (clean_top[:, :, None] == top[:, None, :]).any(axis=2).sum(axis=1)
                ranks = pd.DataFrame(np.abs(values)).rank(axis=1).to_numpy(copy=True)
                ranks -= ranks.mean(axis=1, keepdims=True)
                rank_denom = np.sqrt((rank_clean**2).sum(axis=1) * (ranks**2).sum(axis=1))
                rho = np.divide((rank_clean*ranks).sum(axis=1), rank_denom,
                                out=np.full(count, np.nan), where=rank_denom > 0)
                l1 = np.divide(np.abs(values-clean).sum(axis=1), denom,
                               out=np.full(count, np.nan), where=denom > 1e-12)
                pieces.append(pd.DataFrame(dict(test_row_position=np.arange(offset, offset+count),
                    true_label=frame.Label.astype(str).to_numpy(), noise_percent=level*100, seed=seed,
                    time_factor=factors, explained_class=encoder.classes_[target],
                    perturbed_predicted_class=encoder.classes_[pred], prediction_changed=pred != target,
                    original_correct=true == target, input_changed=(noisy.to_numpy() != X.to_numpy()).any(axis=1),
                    overlap_at_10_percent=10*common, jaccard_at_10=common/(20-common), spearman_abs=rho,
                    relative_l1_change=l1, original_active_feature_count=support,
                    probability_change_pp=100*(probability-clean_probs))))
            meta = dict(signature=signature, start=offset, rows=count, seconds=time.perf_counter()-started,
                        max_additivity_error=error)
            table = pa.Table.from_pandas(pd.concat(pieces, ignore_index=True), preserve_index=False)
            table = table.replace_schema_metadata({**(table.schema.metadata or {}), b'experiment':json.dumps(meta).encode()})
            tmp = dest.with_suffix('.tmp')
            pq.write_table(table, tmp, compression='zstd')
            tmp.replace(dest)
        paths.append(dest)
        offset += count
        elapsed += meta['seconds']
        max_error = max(max_error, meta['max_additivity_error'])
        info = dict(status='processing', processed_rows=offset, total_rows=source.metadata.num_rows,
                    compute_seconds=elapsed, max_additivity_error=max_error, config_signature=signature,
                    perturbed_observations=offset*9, control_observations=offset)
        save_json(out / 'run_info.json', info)
        print(f'{offset:,}/{source.metadata.num_rows:,} | saved | estimate {(source.metadata.num_rows-offset)*elapsed/offset/3600:.2f} h remaining', flush=True)
    # Summarize each shard; disjoint row positions allow exact unique-count sums.
    aggregations = []
    for path in paths:
        frame = pd.read_parquet(path)
        frame['abs_probability_change_pp'] = frame.probability_change_pp.abs()
        frame['low_support'] = (frame.original_active_feature_count < 10).astype(float)
        for (label, level), group in frame.groupby(['true_label', 'noise_percent']):
            for subset, part in [('all', group), ('prediction_changed', group[group.prediction_changed]),
                                 ('prediction_unchanged', group[~group.prediction_changed])]:
                if part.empty:
                    continue
                record = dict(true_label=label, noise_percent=level, subset=subset,
                    n_observations=len(part), n_unique_samples=part.test_row_position.nunique())
                for metric in ['prediction_changed','input_changed','overlap_at_10_percent','jaccard_at_10',
                               'spearman_abs','relative_l1_change','abs_probability_change_pp','low_support']:
                    record[metric+'_sum'] = part[metric].sum()
                    record[metric+'_count'] = part[metric].count()
                aggregations.append(record)
    if not aggregations:
        raise ValueError('No data')
    sums = pd.DataFrame(aggregations).groupby(['true_label','noise_percent','subset']).sum()
    def finish(s):
        result = s[['n_observations','n_unique_samples']].copy()
        for metric in ['prediction_changed','input_changed','overlap_at_10_percent','jaccard_at_10',
                       'spearman_abs','relative_l1_change','abs_probability_change_pp','low_support']:
            result['mean_'+metric] = s[metric+'_sum']/s[metric+'_count'].replace(0,np.nan)
        return result
    finish(sums).to_csv(out / 'summary_by_class.csv', encoding='utf-8-sig')
    finish(sums.groupby(level=['noise_percent','subset']).sum()).to_csv(out / 'summary_overall.csv', encoding='utf-8-sig')
    info['status'] = 'complete' if offset == source.metadata.num_rows else 'partial'
    save_json(out / 'run_info.json', info)
    print(info['status'].upper(), out)


if __name__ == '__main__':
    main()

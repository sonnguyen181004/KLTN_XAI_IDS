"""Streaming, resumable RQ2.4 experiment on every row of the saved test set.
Copy this file to the project root. No retraining or test-row subsampling.
"""
from pathlib import Path
import argparse
import hashlib
import json
import platform
import time
import joblib
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import shap
import xgboost


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, obj):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def softmax(raw):
    ex = np.exp(raw.astype(np.float64) - raw.max(axis=1, keepdims=True))
    return ex / ex.sum(axis=1, keepdims=True)


def training_donors(path, features, count):
    source = pq.ParquetFile(path)
    positions = np.sort(np.random.default_rng(173).choice(source.metadata.num_rows, count, replace=False))
    parts, offset = [], 0
    for batch in source.iter_batches(batch_size=65536, columns=features):
        local = positions[(positions >= offset) & (positions < offset + batch.num_rows)] - offset
        if len(local):
            parts.append(batch.take(local.tolist()).to_pandas()[features])
        offset += batch.num_rows
        if offset > positions[-1]:
            break
    frame = pd.concat(parts, ignore_index=True)
    frame.index = pd.Index(positions, name='train_row_position')
    assert len(frame) == count
    return frame


def summarize(shards, out):
    pieces = []
    metrics = ['shap_margin_drop', 'random_margin_drop', 'margin_drop_advantage',
               'shap_probability_drop_pp', 'random_probability_drop_pp',
               'shap_changed_feature_fraction', 'random_changed_feature_fraction',
               'shap_class_change_fraction', 'random_class_change_fraction',
               'shap_beats_random', 'tie']
    for path in shards:
        frame = pd.read_parquet(path)
        frame['n_original'] = 1
        frame['n_eligible'] = frame.status.eq('eligible').astype(int)
        frame['n_excluded'] = 1 - frame.n_eligible
        frame['n_correct'] = frame.original_correct.astype(int)
        pieces.append(frame.groupby(['true_label', 'k'])[
            ['n_original', 'n_eligible', 'n_excluded', 'n_correct'] + metrics].sum())
    totals = pd.concat(pieces).groupby(level=[0, 1]).sum()
    def finish(table):
        table = table.copy()
        denominator = table.n_eligible.replace(0, np.nan)
        for col in metrics:
            table[col] = table[col] / denominator
        table['coverage_percent'] = 100 * table.n_eligible / table.n_original
        table['win_rate_percent'] = 100 * table.pop('shap_beats_random')
        table['tie_rate_percent'] = 100 * table.pop('tie')
        table['prediction_recall_percent'] = 100 * table.n_correct / table.n_original
        return table
    finish(totals).to_csv(out / 'summary_by_class.csv', encoding='utf-8-sig')
    overall = finish(totals.groupby(level='k').sum())
    overall.to_csv(out / 'summary_overall.csv', encoding='utf-8-sig')
    return overall


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--batch-size', type=int, default=256)
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--max-batches', type=int, default=0,
                        help='Stop after this many total batches; rerun without it to continue all rows.')
    parser.add_argument('--smoke', action='store_true', help='Separate test configuration: 2 donors and 3 random repetitions.')
    args = parser.parse_args()
    if args.batch_size < 1 or args.threads < 1 or args.max_batches < 0:
        raise ValueError('Invalid batch size, thread count or max-batches')
    root = args.project.resolve()
    out = args.output or root / 'shap_results' / ('faithfulness_full_test_smoke' if args.smoke else 'faithfulness_full_test')
    out.mkdir(parents=True, exist_ok=True)
    chunks = out / 'chunks'
    chunks.mkdir(exist_ok=True)
    data = root / 'dataset' / 'CICID-2018_processed'
    test_path, train_path = data / 'test_set.parquet', data / 'train_set.parquet'
    model_path = root / 'RQ1_Model_Training_xboost' / 'saved_models' / 'best_xgboost_model.pkl'
    encoder_path = model_path.with_name('label_encoder.pkl')
    model, encoder = joblib.load(model_path), joblib.load(encoder_path)
    model.set_params(n_jobs=args.threads)
    features = model.get_booster().feature_names
    source = pq.ParquetFile(test_path)
    if features is None or set(source.schema_arrow.names) != set(features) | {'Label'}:
        raise ValueError('Test columns do not match model features plus Label')
    if not np.array_equal(model.classes_, np.arange(len(encoder.classes_))):
        raise ValueError('Model/encoder class mismatch')
    n_donors, repeats = (2, 3) if args.smoke else (10, 20)
    print('Checking input fingerprints...', flush=True)
    config = dict(protocol='positive_shap_train_donor_full_test_v1',
                  script_sha256=digest(Path(__file__)),
                  input_sha256={p.name: digest(p) for p in [test_path, train_path, model_path, encoder_path]},
                  total_test_rows=source.metadata.num_rows, batch_size=args.batch_size,
                  threads=args.threads, smoke=args.smoke, donors=n_donors, random_repeats=repeats,
                  ks=[3, 5, 10], donor_seed=173, control_seed=2026,
                  random_protocol='SeedSequence([2026,k,test_row_position]), reused across donors',
                  positive_threshold=1e-8, win_tolerance=1e-6,
                  python=platform.python_version(), numpy=np.__version__, shap=shap.__version__,
                  xgboost=xgboost.__version__, features=features, classes=encoder.classes_.tolist())
    config_path = out / 'config.json'
    if config_path.exists():
        if json.loads(config_path.read_text(encoding='utf-8')) != config:
            raise ValueError('Configuration/input changed. Use a NEW output directory; do not mix experiments.')
    else:
        if list(chunks.glob('*.parquet')):
            raise ValueError('Chunks exist without config; use a new output directory')
        write_json(config_path, config)
    signature = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    donors = training_donors(train_path, features, n_donors)
    if not np.isfinite(donors.to_numpy()).all():
        raise ValueError('Non-finite donors')
    donors.to_parquet(out / 'train_donors.parquet')
    explainer = shap.TreeExplainer(model, model_output='raw', feature_perturbation='tree_path_dependent')
    completed, offset, elapsed, max_error = [], 0, 0.0, 0.0
    for batch_id, batch in enumerate(source.iter_batches(batch_size=args.batch_size, columns=features + ['Label'])):
        if args.max_batches and batch_id >= args.max_batches:
            break
        path = chunks / f'batch_{batch_id:06d}.parquet'
        count = batch.num_rows
        if path.exists():
            saved = pq.ParquetFile(path)
            meta = json.loads(saved.schema_arrow.metadata[b'experiment'])
            if (meta['signature'] != signature or meta['start'] != offset or
                    meta['rows'] != count or saved.metadata.num_rows != count * 3):
                raise ValueError(f'Checkpoint mismatch: {path}')
        else:
            started = time.perf_counter()
            frame = batch.to_pandas()
            X = frame[features].astype(float)
            labels = frame.Label.astype(str).to_numpy()
            encoder.transform(labels)
            if not np.isfinite(X.to_numpy()).all():
                raise ValueError(f'Non-finite input at batch {batch_id}')
            raw = model.predict(X, output_margin=True)
            probs = softmax(raw)
            np.testing.assert_allclose(probs, model.predict_proba(X), atol=1e-6, rtol=1e-5)
            target = raw.argmax(axis=1)
            explanation = explainer(X, check_additivity=True)
            if explanation.values.shape != (count, len(features), len(encoder.classes_)):
                raise ValueError('Unexpected SHAP shape')
            reconstructed = explanation.base_values + explanation.values.sum(axis=1)
            np.testing.assert_allclose(reconstructed, raw, rtol=1e-4, atol=1e-4)
            error = float(np.abs(reconstructed - raw).max())
            phi = explanation.values[np.arange(count), :, target]
            positive = (phi > 1e-8).sum(axis=1)
            order = np.argsort(-phi, axis=1, kind='stable')
            results = []
            for k in [3, 5, 10]:
                result = pd.DataFrame(dict(test_row_position=np.arange(offset, offset + count),
                    true_label=labels, explained_class=encoder.classes_[target],
                    original_correct=encoder.classes_[target] == labels,
                    original_probability=probs[np.arange(count), target], k=k, n_positive=positive,
                    status=np.where(positive > k, 'eligible', np.where(positive == k,
                        'exactly_k_no_distinct_control', 'fewer_than_k'))))
                eligible = np.flatnonzero(positive > k)
                metric_names = ['margin_drop', 'probability_drop_pp', 'class_change_fraction', 'changed_feature_fraction']
                for name in metric_names:
                    result['shap_' + name] = np.nan
                    result['random_' + name] = np.nan
                for name in ['margin_drop_advantage', 'shap_beats_random', 'tie']:
                    result[name] = np.nan
                if len(eligible):
                    n = len(eligible)
                    selections = np.empty((repeats + 1, n, k), dtype=int)
                    selections[0] = order[eligible, :k]
                    for j, i in enumerate(eligible):
                        rng = np.random.default_rng(np.random.SeedSequence([2026, k, offset + int(i)]))
                        pool = np.flatnonzero(phi[i] > 1e-8)
                        for r in range(repeats):
                            selections[r + 1, j] = rng.choice(pool, k, replace=False)
                    indices = selections.reshape(-1, k)
                    original = np.tile(X.iloc[eligible].to_numpy(), (repeats + 1, 1))
                    targets = np.tile(target[eligible], repeats + 1)
                    old_margin = np.tile(raw[eligible, target[eligible]], repeats + 1)
                    old_prob = np.tile(probs[eligible, target[eligible]], repeats + 1)
                    rr = np.arange(len(original))
                    scores = np.zeros((repeats + 1, n, 4))
                    for donor in donors.to_numpy(dtype=float):
                        masked = original.copy()
                        masked[rr[:, None], indices] = donor[indices]
                        fraction = (masked[rr[:, None], indices] != original[rr[:, None], indices]).mean(axis=1)
                        altered = np.concatenate([model.predict(pd.DataFrame(masked[s:s+8192], columns=features),
                            output_margin=True) for s in range(0, len(masked), 8192)])
                        values = np.column_stack([old_margin - altered[rr, targets],
                            100 * (old_prob - softmax(altered)[rr, targets]), altered.argmax(axis=1) != targets, fraction])
                        scores += values.reshape(repeats + 1, n, 4) / n_donors
                    top, random = scores[0], scores[1:].mean(axis=0)
                    for c, name in enumerate(metric_names):
                        result.loc[eligible, 'shap_' + name] = top[:, c]
                        result.loc[eligible, 'random_' + name] = random[:, c]
                    gap = top[:, 0] - random[:, 0]
                    result.loc[eligible, 'margin_drop_advantage'] = gap
                    result.loc[eligible, 'shap_beats_random'] = (gap > 1e-6).astype(float)
                    result.loc[eligible, 'tie'] = (np.abs(gap) <= 1e-6).astype(float)
                results.append(result)
            meta = dict(signature=signature, start=offset, rows=count,
                        seconds=time.perf_counter() - started, max_additivity_error=error)
            table = pa.Table.from_pandas(pd.concat(results, ignore_index=True), preserve_index=False)
            table = table.replace_schema_metadata({**(table.schema.metadata or {}), b'experiment': json.dumps(meta).encode()})
            temp = path.with_suffix('.tmp')
            pq.write_table(table, temp, compression='zstd')
            temp.replace(path)
        completed.append(path)
        offset += count
        elapsed += meta['seconds']
        max_error = max(max_error, meta['max_additivity_error'])
        info = dict(status='complete' if offset == source.metadata.num_rows else 'partial',
                    processed_rows=offset, total_rows=source.metadata.num_rows, batches=len(completed),
                    compute_seconds=elapsed, max_additivity_error=max_error, smoke=args.smoke,
                    train_donor_positions=donors.index.tolist(), config_signature=signature)
        write_json(out / 'run_info.json', info)
        remaining_hours = (source.metadata.num_rows - offset) * elapsed / offset / 3600
        print(f'{offset:,}/{source.metadata.num_rows:,} rows | estimated remaining {remaining_hours:.2f} h | checkpoint saved', flush=True)
    if completed:
        summary = summarize(completed, out)
        print(summary[['n_original', 'n_eligible', 'coverage_percent', 'win_rate_percent']].to_string())
        print('COMPLETE' if offset == source.metadata.num_rows else 'PARTIAL - rerun without --max-batches to continue')
        print(out)


if __name__ == '__main__':
    main()

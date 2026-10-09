"""Agreement metrics between two feature-importance rankings of the same flow.

Both rankings cover the same 78 features. Each metric is defined precisely in its
docstring because this family of metrics (feature/rank/sign agreement, RBO) has no single
universal definition in the literature — ambiguity here is exactly what caused the old v1
numbers to be hard to interpret.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import spearmanr, kendalltau


def topk_features(ranked_features: list[str], k: int) -> list[str]:
    return ranked_features[:k]


def jaccard_at_k(rank_a: list[str], rank_b: list[str], k: int) -> float:
    """|top-k(A) ∩ top-k(B)| / |top-k(A) ∪ top-k(B)| — ignores sign and within-k order."""
    sa, sb = set(rank_a[:k]), set(rank_b[:k])
    union = sa | sb
    if not union:
        return float("nan")
    return len(sa & sb) / len(union)


def spearman_at_k(rank_a: list[str], rank_b: list[str], k: int) -> float:
    """Spearman correlation of each method's OWN full-78 rank position, restricted to the
    union of the two top-k feature sets. A feature that is top-k in one method but ranked
    e.g. 60th in the other keeps that true rank — this is what makes Spearman sensitive to
    "near misses" that Jaccard (set membership only) cannot see."""
    union = sorted(set(rank_a[:k]) | set(rank_b[:k]))
    if len(union) < 2:
        return float("nan")
    rank_pos_a = {f: i for i, f in enumerate(rank_a)}
    rank_pos_b = {f: i for i, f in enumerate(rank_b)}
    ra = [rank_pos_a[f] for f in union]
    rb = [rank_pos_b[f] for f in union]
    if len(set(ra)) < 2 or len(set(rb)) < 2:
        return float("nan")
    corr, _ = spearmanr(ra, rb)
    return float(corr)


def kendall_at_k(rank_a: list[str], rank_b: list[str], k: int) -> float:
    """Kendall tau, same union-of-top-k construction as spearman_at_k."""
    union = sorted(set(rank_a[:k]) | set(rank_b[:k]))
    if len(union) < 2:
        return float("nan")
    rank_pos_a = {f: i for i, f in enumerate(rank_a)}
    rank_pos_b = {f: i for i, f in enumerate(rank_b)}
    ra = [rank_pos_a[f] for f in union]
    rb = [rank_pos_b[f] for f in union]
    if len(set(ra)) < 2 or len(set(rb)) < 2:
        return float("nan")
    corr, _ = kendalltau(ra, rb)
    return float(corr)


def rbo_at_k(rank_a: list[str], rank_b: list[str], k: int, p: float = 0.9) -> float:
    """Truncated Rank-Biased Overlap up to depth k, normalized to 1.0 for perfect agreement
    at that depth (simple truncation, not the full extrapolated RBO with a tail-correction
    term — documented simplification, adequate for comparing methods at a fixed k)."""
    s = 0.0
    for d in range(1, k + 1):
        set_a, set_b = set(rank_a[:d]), set(rank_b[:d])
        s += (p ** (d - 1)) * (len(set_a & set_b) / d)
    s *= (1 - p)
    norm = 1 - p ** k
    return s / norm if norm > 0 else float("nan")


def sign_agreement_at_k(rank_a: list[str], sign_a: dict, rank_b: list[str], sign_b: dict, k: int) -> float:
    """Among features in the INTERSECTION of the two top-k sets, the fraction where
    sign(importance_A) == sign(importance_B). NaN if the intersection is empty (that case
    is itself a form of disagreement, reported separately via jaccard_at_k)."""
    inter = set(rank_a[:k]) & set(rank_b[:k])
    if not inter:
        return float("nan")
    agree = sum(1 for f in inter if np.sign(sign_a[f]) == np.sign(sign_b[f]))
    return agree / len(inter)


def full_rank_correlation(rank_a: list[str], rank_b: list[str]) -> tuple[float, float]:
    """Spearman and Kendall tau computed over the FULL 78-feature ranking (every feature,
    not just a top-k union). Unlike spearman_at_k/kendall_at_k, this is NOT subject to the
    selection-bias artifact that union-of-top-k correlation has: when agreement is low,
    restricting to "top-k for A" ∪ "top-k for B" mechanically pairs each method's own
    best-ranked features against the OTHER method's near-arbitrary rank for them, which
    pulls the correlation negative even under independence. The full-78 version is the
    number to interpret as "do the two methods broadly agree on importance ordering" —
    the per-k union versions are kept only to see how agreement concentrates at the top."""
    idx_a = {f: i for i, f in enumerate(rank_a)}
    idx_b = {f: i for i, f in enumerate(rank_b)}
    feats = rank_a  # same 78 features in both
    ra = [idx_a[f] for f in feats]
    rb = [idx_b[f] for f in feats]
    sp, _ = spearmanr(ra, rb)
    kt, _ = kendalltau(ra, rb)
    return float(sp), float(kt)


def random_baseline_jaccard(n_features: int, k: int, n_trials: int, rng: np.random.Generator) -> np.ndarray:
    """Simulated Jaccard@k if both methods picked k features uniformly at random (independently)."""
    out = np.empty(n_trials)
    idx = np.arange(n_features)
    for t in range(n_trials):
        a = set(rng.choice(idx, size=k, replace=False).tolist())
        b = set(rng.choice(idx, size=k, replace=False).tolist())
        out[t] = len(a & b) / len(a | b)
    return out


def bootstrap_ci(values: np.ndarray, n_resamples: int, ci: float, rng: np.random.Generator) -> tuple[float, float, float]:
    """Return (mean, lo, hi) from a basic percentile bootstrap over the mean statistic."""
    values = values[~np.isnan(values)]
    if len(values) == 0:
        return float("nan"), float("nan"), float("nan")
    boot_means = np.empty(n_resamples)
    n = len(values)
    for i in range(n_resamples):
        sample = rng.choice(values, size=n, replace=True)
        boot_means[i] = sample.mean()
    alpha = (1 - ci) / 2
    lo, hi = np.quantile(boot_means, [alpha, 1 - alpha])
    return float(values.mean()), float(lo), float(hi)

"""Shared helpers for every RQ2 stage script.

All stage scripts must:
  - load params only from RQ2/config.yaml (never hardcode paths/thresholds)
  - resolve paths relative to the git repo root via repo_root()
  - write into the current run folder via run_dir()
  - log via get_logger()
"""
from __future__ import annotations

import hashlib
import json
import logging
import subprocess
import sys
from pathlib import Path

import yaml

# Windows console defaults to cp1252, which cannot encode Vietnamese text (Đ, ẩ, …).
# Force UTF-8 on stdio for every stage script that imports this module.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

RQ2_DIR = Path(__file__).resolve().parents[2]       # .../SELF_KLTN/RQ2
REPO_ROOT = RQ2_DIR.parent                            # .../SELF_KLTN


def repo_root() -> Path:
    return REPO_ROOT


def load_config() -> dict:
    cfg_path = RQ2_DIR / "config.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_config(cfg: dict) -> None:
    cfg_path = RQ2_DIR / "config.yaml"
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)


def resolve_path(rel: str) -> Path:
    return REPO_ROOT / rel


def latest_run_dir(create_if_missing_date: str | None = None) -> Path:
    """Return RQ2/runs/<date> — the most recent one, or create a new one for the given date."""
    runs_root = RQ2_DIR / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)
    if create_if_missing_date:
        d = runs_root / create_if_missing_date
        d.mkdir(parents=True, exist_ok=True)
        return d
    candidates = sorted([p for p in runs_root.iterdir() if p.is_dir()])
    if not candidates:
        raise FileNotFoundError("No run directory under RQ2/runs yet — run stage00 first.")
    return candidates[-1]


def get_logger(name: str, run_dir: Path) -> logging.Logger:
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    fh = logging.FileHandler(logs_dir / f"{name}.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    return logger


def sha256_of_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit_hash() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, stderr=subprocess.DEVNULL
        )
        return out.decode().strip()
    except Exception:
        return "unknown"


def set_lime_explainer_seed(explainer, seed: int) -> None:
    """Make a LimeTabularExplainer call reproducible for a given seed.

    lime==0.2.0.1's explain_instance() has no random_state kwarg. Its randomness is
    split across THREE separate references, each bound to the ORIGINAL RandomState
    object at __init__ time — reassigning explainer.random_state alone does NOT
    propagate (verified empirically; see RQ2/docs/plan.md):
      1. explainer.random_state            -> __data_inverse's binary sampling
      2. explainer.base.random_state        -> LimeBase (Ridge / feature selection)
      3. explainer.discretizer.random_state -> undiscretize's truncnorm.rvs, i.e. the
                                                actual continuous perturbed feature
                                                values (only exists when
                                                discretize_continuous=True)
    All three must point at the SAME fresh RandomState instance before each call.
    """
    import numpy as np

    rs = np.random.RandomState(seed)
    explainer.random_state = rs
    explainer.base.random_state = rs
    if getattr(explainer, "discretizer", None) is not None:
        explainer.discretizer.random_state = rs


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=str)

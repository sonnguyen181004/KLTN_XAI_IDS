"""GĐ 0 — Chuẩn bị lần chạy.

- Xác nhận RQ2 cũ đã nằm trong v1_archive (đã làm sẵn trước khi script này tồn tại).
- Tạo thư mục chạy mới theo ngày: RQ2/runs/<YYYYMMDD>/
- Chụp lại config.yaml hiện tại vào run dir (config_snapshot.yaml) kèm git commit.
- Đạt khi: run dir tồn tại, config snapshot được ghi, log được ghi.
"""
from __future__ import annotations

import datetime as dt
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.common import (  # noqa: E402
    RQ2_DIR,
    load_config,
    git_commit_hash,
    get_logger,
    write_json,
)


def main() -> int:
    cfg = load_config()
    today = dt.date.today().strftime("%Y%m%d")

    run_dir = RQ2_DIR / "runs" / today
    run_dir.mkdir(parents=True, exist_ok=True)

    logger = get_logger("stage00_prepare_run", run_dir)
    logger.info("=" * 80)
    logger.info("GĐ 0: CHUẨN BỊ LẦN CHẠY")
    logger.info("=" * 80)

    v1_archive = RQ2_DIR.parent / cfg["paths"]["v1_archive"]
    if v1_archive.exists():
        logger.info("Xác nhận v1_archive tồn tại: %s", v1_archive)
    else:
        logger.warning(
            "KHÔNG tìm thấy v1_archive tại %s — kết quả RQ2 cũ có thể chưa được lưu trữ.",
            v1_archive,
        )

    # Snapshot config.yaml into the run dir so later stages can see exactly what was
    # locked in at prepare time (GĐ5 will update RQ2/config.yaml's lime.locked_config,
    # and we re-snapshot then — see stage05).
    snapshot_path = run_dir / "config_snapshot_gd0.yaml"
    shutil.copyfile(RQ2_DIR / "config.yaml", snapshot_path)
    logger.info("Đã chụp config.yaml -> %s", snapshot_path)

    for sub in [
        "gd1_env_check",
        "gd2_shap_global",
        "gd3_cohorts",
        "gd4_shap_per_flow",
        "gd5_lime_dev_tuning",
        "gd6_lime_per_flow",
        "gd7_agreement",
        "gd8_quality_gate",
        "gd9_stability_robustness",
        "gd10_faithfulness",
        "gd11_domain_validation",
        "gd12_error_cohort",
        "gd13_report",
        "logs",
    ]:
        (run_dir / sub).mkdir(parents=True, exist_ok=True)
    logger.info("Đã tạo cấu trúc thư mục con cho 13 giai đoạn trong %s", run_dir)

    run_info = {
        "run_id": today,
        "created_at": dt.datetime.now().isoformat(),
        "git_commit": git_commit_hash(),
        "python_executable": sys.executable,
        "seed": cfg["seed"],
    }
    write_json(run_dir / "run_prepare_info.json", run_info)
    logger.info("run_prepare_info.json: %s", run_info)

    logger.info("GĐ 0 HOÀN TẤT. Run dir: %s", run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

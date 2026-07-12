"""Phase 1 entry point: load, clean, validate, and save Bloomberg data."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ccb_quant.data import (  # noqa: E402
    DataValidationError,
    load_and_validate_bloomberg_csv,
    write_phase1_outputs,
)


def _repository_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def run_phase1(config_path: Path) -> dict[str, object]:
    """Execute only the approved data-processing phase."""

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data_config = config["data"]
    output_config = config["outputs"]

    log_path = _repository_path(output_config["phase1_log_file"])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )

    raw_path = _repository_path(data_config["raw_file"])
    logging.info("Loading immutable Bloomberg source: %s", raw_path)
    frame, report = load_and_validate_bloomberg_csv(
        raw_path,
        header_row=int(data_config["header_row"]),
        delimiter=str(data_config["delimiter"]),
        date_format=str(data_config["date_format"]),
        expected_start_date=str(data_config["expected_start_date"]),
        expected_end_date=str(data_config["expected_end_date"]),
        outlier_review_threshold=float(data_config["outlier_review_threshold"]),
    )
    if raw_path.is_relative_to(PROJECT_ROOT):
        report["source"]["file"] = raw_path.relative_to(PROJECT_ROOT).as_posix()
    elif raw_path.is_relative_to(config_path.parent):
        report["source"]["file"] = raw_path.relative_to(config_path.parent).as_posix()
    else:
        report["source"]["file"] = raw_path.as_posix()

    processed_path = _repository_path(data_config["processed_file"])
    json_report_path = _repository_path(output_config["data_quality_json"])
    markdown_report_path = _repository_path(output_config["data_quality_markdown"])
    write_phase1_outputs(
        frame,
        report,
        processed_path=processed_path,
        json_report_path=json_report_path,
        markdown_report_path=markdown_report_path,
    )
    logging.info("Phase 1 PASS: %s clean rows", len(frame))
    logging.info("Clean data: %s", processed_path)
    logging.info("Validation report: %s", markdown_report_path)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 1 Bloomberg data validation")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/config.yaml"),
        help="Repository-relative YAML configuration path",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = _repository_path(str(args.config))
    try:
        run_phase1(config_path)
    except (OSError, KeyError, TypeError, ValueError, DataValidationError) as exc:
        logging.exception("Phase 1 failed: %s", exc)
        print(f"Phase 1 failed: {exc}", file=sys.stderr)
        return 1
    print("Phase 1 complete. No strategy code has been implemented.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

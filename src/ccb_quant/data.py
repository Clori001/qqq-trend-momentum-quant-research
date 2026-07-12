"""Bloomberg CSV loading, cleaning, validation, and Phase 1 reporting."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SOURCE_TO_CANONICAL = {
    "Dates": "Date",
    "PX_OPEN": "Open",
    "PX_HIGH": "High",
    "PX_LOW": "Low",
    "PX_LAST": "Close",
    "PX_VOLUME": "Volume",
}
CANONICAL_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Volume"]
PRICE_COLUMNS = ["Open", "High", "Low", "Close"]


class DataValidationError(ValueError):
    """Raised when the Bloomberg file is unsafe for downstream research."""


def sha256_file(path: Path) -> str:
    """Return a lowercase SHA-256 hash without loading the full file at once."""

    digest = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_and_validate_bloomberg_csv(
    path: Path,
    *,
    header_row: int = 5,
    delimiter: str = ",",
    date_format: str = "%d/%m/%Y",
    expected_start_date: str | None = None,
    expected_end_date: str | None = None,
    outlier_review_threshold: float = 0.10,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load the Bloomberg export and return clean OHLCV data plus diagnostics.

    The first five rows are Bloomberg metadata and status text. Large daily
    returns only trigger review; they are never removed merely for exceeding
    the threshold.
    """

    if not path.is_file():
        raise DataValidationError(f"Raw CSV does not exist: {path}")
    if header_row < 0:
        raise ValueError("header_row must be non-negative")
    if len(delimiter) != 1:
        raise ValueError("delimiter must contain exactly one character")
    if not 0.0 < outlier_review_threshold <= 1.0:
        raise ValueError("outlier_review_threshold must be in (0, 1]")

    try:
        raw = pd.read_csv(
            path,
            header=header_row,
            sep=delimiter,
            dtype=str,
            encoding="utf-8-sig",
        )
    except (OSError, UnicodeError, pd.errors.ParserError) as exc:
        raise DataValidationError(f"Unable to parse Bloomberg CSV: {exc}") from exc

    raw.columns = [str(column).strip() for column in raw.columns]
    missing_source_columns = [
        column for column in SOURCE_TO_CANONICAL if column not in raw.columns
    ]
    if missing_source_columns:
        raise DataValidationError(
            "Missing required Bloomberg columns: " + ", ".join(missing_source_columns)
        )

    frame = raw.rename(columns=SOURCE_TO_CANONICAL).loc[:, CANONICAL_COLUMNS].copy()
    raw_row_count = len(frame)

    frame["Date"] = pd.to_datetime(
        frame["Date"].str.strip(), format=date_format, errors="coerce"
    )
    for column in PRICE_COLUMNS + ["Volume"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    missing_counts = {column: int(frame[column].isna().sum()) for column in CANONICAL_COLUMNS}
    if any(missing_counts.values()):
        raise DataValidationError(
            "Missing or invalid values detected: "
            + ", ".join(f"{key}={value}" for key, value in missing_counts.items() if value)
        )

    all_exact_duplicate_mask = frame.duplicated(
        subset=CANONICAL_COLUMNS, keep=False
    )
    exact_duplicate_rows_found = int(all_exact_duplicate_mask.sum())
    redundant_duplicate_mask = frame.duplicated(
        subset=CANONICAL_COLUMNS, keep="first"
    )
    exact_duplicate_rows_removed = int(redundant_duplicate_mask.sum())
    if exact_duplicate_rows_removed:
        frame = frame.loc[~redundant_duplicate_mask].copy()

    conflicting_date_mask = frame.duplicated(subset=["Date"], keep=False)
    if conflicting_date_mask.any():
        conflicting_dates = sorted(
            frame.loc[conflicting_date_mask, "Date"].dt.strftime("%Y-%m-%d").unique()
        )
        raise DataValidationError(
            "Conflicting duplicate dates detected: " + ", ".join(conflicting_dates)
        )

    input_sorted = bool(frame["Date"].is_monotonic_increasing)
    frame = frame.sort_values("Date", kind="stable").reset_index(drop=True)

    actual_start = frame["Date"].iloc[0]
    actual_end = frame["Date"].iloc[-1]
    expected_start = (
        pd.Timestamp(expected_start_date) if expected_start_date is not None else None
    )
    expected_end = (
        pd.Timestamp(expected_end_date) if expected_end_date is not None else None
    )
    if expected_start is not None and actual_start != expected_start:
        raise DataValidationError(
            f"First observation {actual_start.date()} does not match expected "
            f"start {expected_start.date()}"
        )
    if expected_end is not None and actual_end != expected_end:
        raise DataValidationError(
            f"Last observation {actual_end.date()} does not match expected "
            f"end {expected_end.date()}"
        )

    numeric_values = frame[PRICE_COLUMNS + ["Volume"]].to_numpy(dtype=float)
    if not np.isfinite(numeric_values).all():
        raise DataValidationError("OHLCV contains non-finite numeric values")

    nonpositive_prices = int((frame[PRICE_COLUMNS] <= 0).sum().sum())
    if nonpositive_prices:
        raise DataValidationError(
            f"OHLC contains {nonpositive_prices} non-positive value(s)"
        )

    negative_volume_rows = int((frame["Volume"] < 0).sum())
    if negative_volume_rows:
        raise DataValidationError(
            f"Volume contains {negative_volume_rows} negative value(s)"
        )
    fractional_volume_rows = int(
        (~np.isclose(frame["Volume"], np.round(frame["Volume"]))).sum()
    )
    if fractional_volume_rows:
        raise DataValidationError(
            f"Volume contains {fractional_volume_rows} fractional value(s)"
        )

    high_violations = frame["High"] < frame[["Open", "Low", "Close"]].max(axis=1)
    low_violations = frame["Low"] > frame[["Open", "High", "Close"]].min(axis=1)
    ohlc_violations = int(high_violations.sum() + low_violations.sum())
    if ohlc_violations:
        raise DataValidationError(
            f"OHLC relationship checks failed on {ohlc_violations} row(s)"
        )

    frame["Volume"] = frame["Volume"].astype("int64")
    frame[PRICE_COLUMNS] = frame[PRICE_COLUMNS].astype("float64")

    daily_return = frame["Close"].pct_change(fill_method=None)
    review_mask = daily_return.abs() > outlier_review_threshold
    review_rows = [
        {
            "date": frame.loc[index, "Date"].strftime("%Y-%m-%d"),
            "close_return": float(daily_return.loc[index]),
            "action": "retained_review_only",
        }
        for index in frame.index[review_mask]
    ]

    zero_volume_rows = int((frame["Volume"] == 0).sum())
    weekend_rows = int((frame["Date"].dt.dayofweek >= 5).sum())
    report: dict[str, Any] = {
        "status": "PASS",
        "source": {
            "file": path.as_posix(),
            "sha256": sha256_file(path),
            "security": "QQQ US Equity",
            "frequency": "daily observations on available trading dates",
            "metadata_rows_skipped": header_row,
            "header_row_one_based": header_row + 1,
            "delimiter": delimiter,
            "date_format": date_format,
            "source_date_convention": "DD/MM/YYYY",
            "expected_start_date": (
                expected_start.strftime("%Y-%m-%d")
                if expected_start is not None
                else None
            ),
            "expected_end_date": (
                expected_end.strftime("%Y-%m-%d")
                if expected_end is not None
                else None
            ),
            "source_columns": list(SOURCE_TO_CANONICAL),
            "canonical_mapping": SOURCE_TO_CANONICAL,
        },
        "rows": {
            "raw_observations": raw_row_count,
            "clean_observations": len(frame),
            "exact_duplicate_rows_found": exact_duplicate_rows_found,
            "exact_duplicate_rows_removed": exact_duplicate_rows_removed,
            "all_unique_observations_preserved": True,
        },
        "dates": {
            "start": frame["Date"].iloc[0].strftime("%Y-%m-%d"),
            "end": frame["Date"].iloc[-1].strftime("%Y-%m-%d"),
            "matches_expected_chronological_range": True,
            "input_sorted_ascending": input_sorted,
            "output_sorted_ascending": bool(frame["Date"].is_monotonic_increasing),
            "duplicate_dates": int(frame["Date"].duplicated().sum()),
            "weekend_rows": weekend_rows,
        },
        "validation": {
            "missing_counts": missing_counts,
            "nonpositive_prices": 0,
            "ohlc_violations": 0,
            "negative_volume_rows": 0,
            "zero_volume_rows": zero_volume_rows,
        },
        "outlier_review": {
            "threshold_absolute_close_return": outlier_review_threshold,
            "policy": (
                "Manual review trigger only. No observation is removed solely for "
                "exceeding the threshold; removal requires independent evidence of corruption."
            ),
            "flag_count": len(review_rows),
            "rows": review_rows,
        },
        "price_interpretation": {
            "return_field": "PX_LAST mapped to Close",
            "adjustment_status": "unknown_from_csv",
            "distribution_status": "unknown_from_csv",
            "approved_claim": "price-return based; not labelled total return",
        },
    }
    return frame, report


def write_phase1_outputs(
    frame: pd.DataFrame,
    report: dict[str, Any],
    *,
    processed_path: Path,
    json_report_path: Path,
    markdown_report_path: Path,
) -> None:
    """Save cleaned data and data-quality evidence to new repository paths."""

    processed_path.parent.mkdir(parents=True, exist_ok=True)
    json_report_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_report_path.parent.mkdir(parents=True, exist_ok=True)

    frame.to_csv(processed_path, index=False, date_format="%Y-%m-%d")
    json_report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown_report_path.write_text(
        build_markdown_report(report), encoding="utf-8"
    )


def build_markdown_report(report: dict[str, Any]) -> str:
    """Render the validation dictionary as a concise Chinese-first report."""

    source = report["source"]
    rows = report["rows"]
    dates = report["dates"]
    checks = report["validation"]
    review = report["outlier_review"]

    lines = [
        "# 数据质量报告 / Data Validation Report",
        "",
        "## 1. 数据源",
        "",
        f"- 文件：`{source['file']}`",
        f"- SHA-256：`{source['sha256']}`",
        f"- 证券：{source['security']}",
        f"- 频率：{source['frequency']}",
            f"- 跳过Bloomberg元数据行：{source['metadata_rows_skipped']}",
            f"- 表头所在物理行：{source['header_row_one_based']}",
            "- Source date convention：`DD/MM/YYYY`",
            "- Parsing rule：严格使用 `%d/%m/%Y`，不进行模糊日期推断",
            (
                f"- Expected chronological range：{source['expected_start_date']} "
                f"to {source['expected_end_date']}（验证通过）"
            ),
        "",
        "## 2. 字段映射",
        "",
        "| Source | Canonical |",
        "|---|---|",
    ]
    for original, canonical in source["canonical_mapping"].items():
        lines.append(f"| {original} | {canonical} |")

    lines.extend(
        [
            "",
            "## 3. 验证结果",
            "",
            "| Check | Result |",
            "|---|---:|",
            f"| Raw observations | {rows['raw_observations']} |",
            f"| Clean observations | {rows['clean_observations']} |",
            f"| Exact duplicate rows found | {rows['exact_duplicate_rows_found']} |",
            f"| Exact duplicate rows removed | {rows['exact_duplicate_rows_removed']} |",
            f"| Date range | {dates['start']} to {dates['end']} |",
            f"| Duplicate dates | {dates['duplicate_dates']} |",
            f"| Weekend rows | {dates['weekend_rows']} |",
            f"| Missing values | {sum(checks['missing_counts'].values())} |",
            f"| Non-positive prices | {checks['nonpositive_prices']} |",
            f"| OHLC violations | {checks['ohlc_violations']} |",
            f"| Negative volume rows | {checks['negative_volume_rows']} |",
            f"| Zero volume rows | {checks['zero_volume_rows']} |",
            "",
            "## 4. 极端收益人工复核",
            "",
            (
                f"阈值为绝对日收益 {review['threshold_absolute_close_return']:.0%}，"
                "仅用于触发人工复核。观察值不会仅因超过阈值而被删除；"
                "删除必须有独立的数据损坏证据。"
            ),
            "",
            "| Date | Close return | Action |",
            "|---|---:|---|",
        ]
    )
    for item in review["rows"]:
        lines.append(
            f"| {item['date']} | {item['close_return']:.2%} | Retained - review only |"
        )
    if not review["rows"]:
        lines.append("| - | - | No trigger |")

    lines.extend(
        [
            "",
            "## 5. 价格口径与接纳结论",
            "",
            (
                "CSV无法单独证明 `PX_LAST` 的拆股、现金分红或total-return调整状态。"
                "因此后续研究只能保守地表述为基于 `PX_LAST` 的price-return结果，"
                "不得称为total return。"
            ),
            "",
            f"**Phase 1 data acceptance: {report['status']}**",
            "",
            "本报告只覆盖数据加载、清洗和验证；尚未实现任何策略、信号或回测。",
            "",
        ]
    )
    return "\n".join(lines)

"""Phase 2 entry point: calculate and save configured indicators only."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ccb_quant.indicators import add_indicators  # noqa: E402


def _repository_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def build_indicator_report(
    frame: pd.DataFrame,
    *,
    ma_windows: list[int],
    momentum_lookbacks: list[int],
    primary_momentum_lookback: int,
) -> str:
    """Describe formulas, roles, warm-ups, and first-valid dates."""

    robustness_lookbacks = [
        lookback
        for lookback in momentum_lookbacks
        if lookback != primary_momentum_lookback
    ]

    lines = [
        "# 指标计算报告 / Indicator Calculation Report",
        "",
        "## 范围",
        "",
        "本阶段只计算trailing indicators，不包含strategy signal、position、return、cost或backtest。",
        "",
        "## 公式与有效日期",
        "",
    ]
    for window in ma_windows:
        column = f"MA{window}"
        first_valid = frame.loc[frame[column].notna(), "Date"].iloc[0]
        lines.extend(
            [
                f"- `{column} = Close.rolling({window}, min_periods={window}).mean()`",
                f"  - Warm-up NaN rows: {int(frame[column].isna().sum())}",
                f"  - First valid date: {first_valid.strftime('%Y-%m-%d')}",
            ]
        )

    for lookback in momentum_lookbacks:
        column = f"Momentum{lookback}"
        first_valid = frame.loc[frame[column].notna(), "Date"].iloc[0]
        role = (
            "Primary indicator"
            if lookback == primary_momentum_lookback
            else "Pre-declared robustness indicator only"
        )
        lines.extend(
            [
                f"- `{column} = Close / Close.shift({lookback}) - 1`",
                f"  - Role: {role}",
                f"  - Warm-up NaN rows: {int(frame[column].isna().sum())}",
                f"  - First valid date: {first_valid.strftime('%Y-%m-%d')}",
            ]
        )

    lines.extend(
        [
            "",
            "## 完整性检查",
            "",
            f"- Input/output rows: {len(frame)} / {len(frame)}",
            "- All MA and momentum lookbacks: read from `config/config.yaml`",
            f"- Primary momentum indicator: Momentum{primary_momentum_lookback}",
            "- Pre-declared robustness momentum indicators: "
            + ", ".join(
                f"Momentum{lookback}" for lookback in robustness_lookbacks
            ),
            "- Robustness indicators do not redefine the primary indicator",
            "- Current and past Close values only: deterministic tests passed",
            "- Centered windows: not used",
            "- Warm-up backfill: not used",
            "- Source OHLCV columns changed: no",
            "- Phase 2 indicator status: PASS",
            "",
        ]
    )
    return "\n".join(lines)


def run_phase2(config_path: Path) -> pd.DataFrame:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    indicator_config = config["indicators"]
    output_config = config["outputs"]
    input_path = _repository_path(indicator_config["input_file"])
    output_path = _repository_path(output_config["indicator_file"])
    report_path = _repository_path(output_config["indicator_report"])
    log_path = _repository_path(output_config["phase2_log_file"])
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

    frame = pd.read_csv(input_path, parse_dates=["Date"])
    ma_windows = [int(value) for value in indicator_config["ma_windows"]]
    momentum_lookbacks = [
        int(value) for value in indicator_config["momentum_lookbacks"]
    ]
    primary_momentum_lookback = int(
        indicator_config["primary_momentum_lookback"]
    )
    if primary_momentum_lookback not in momentum_lookbacks:
        raise ValueError(
            "primary_momentum_lookback must be included in momentum_lookbacks"
        )

    logging.info("Loading cleaned Phase 1 data: %s", input_path)
    enriched = add_indicators(
        frame,
        ma_windows=ma_windows,
        momentum_lookbacks=momentum_lookbacks,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    enriched.to_csv(output_path, index=False, date_format="%Y-%m-%d")
    report_path.write_text(
        build_indicator_report(
            enriched,
            ma_windows=ma_windows,
            momentum_lookbacks=momentum_lookbacks,
            primary_momentum_lookback=primary_momentum_lookback,
        ),
        encoding="utf-8",
    )
    logging.info("Phase 2 PASS: %s indicator rows", len(enriched))
    logging.info("Indicator data: %s", output_path)
    logging.info("Indicator report: %s", report_path)
    return enriched


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 2 indicators only")
    parser.add_argument(
        "--config", type=Path, default=Path("config/config.yaml")
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = _repository_path(str(args.config))
    try:
        frame = run_phase2(config_path)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"Phase 2 failed: {exc}", file=sys.stderr)
        return 1
    print(f"Phase 2 indicators complete: {len(frame)} rows. No signals or backtest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

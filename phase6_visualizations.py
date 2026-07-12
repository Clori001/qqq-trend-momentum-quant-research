"""Phase 6 entry point: render charts from final saved pipeline outputs."""

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

from ccb_quant.visualization import (  # noqa: E402
    plot_drawdown_comparison,
    plot_nav_comparison,
    plot_price_and_mas,
    plot_signal_alignment,
)
from ccb_quant.naming import configured_strategy_specs  # noqa: E402
from ccb_quant.validation import parse_boolean_column  # noqa: E402


def _repository_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _read_saved_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["Date"], float_precision="round_trip")


def _validate_saved_alignment(frame: pd.DataFrame, primary_specs: list[dict]) -> None:
    for spec in primary_specs:
        prefix = spec["prefix"]
        raw = frame[f"{prefix}_RawSignal"]
        position = frame[f"{prefix}_ExecutedPosition"]
        pd.testing.assert_series_equal(
            position,
            raw.shift(1),
            check_names=False,
            obj=f"{prefix} saved one-observation alignment",
        )


def run_phase6(config_path: Path) -> list[Path]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    outputs = config["outputs"]
    visualization = config["visualization"]
    strategy_config = configured_strategy_specs(config["indicators"])
    primary_specs = strategy_config["primary"]
    log_path = _repository_path(outputs["phase6_log_file"])
    report_path = _repository_path(outputs["visualization_report"])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler()],
        force=True,
    )

    import matplotlib.pyplot as plt

    plt.style.use(visualization["style"])
    dpi = int(visualization["dpi"])
    daily = _read_saved_csv(_repository_path(outputs["daily_backtest_file"]))
    drawdowns = _read_saved_csv(_repository_path(outputs["drawdown_series_file"]))
    indicators = _read_saved_csv(_repository_path(outputs["indicator_file"]))
    _validate_saved_alignment(daily, primary_specs)

    chart_paths = [
        _repository_path(outputs["nav_comparison_chart"]),
        _repository_path(outputs["drawdown_comparison_chart"]),
        _repository_path(outputs["price_ma_chart"]),
        _repository_path(outputs["signal_alignment_chart"]),
    ]
    plot_nav_comparison(daily, chart_paths[0], dpi, primary_specs)
    plot_drawdown_comparison(drawdowns, chart_paths[1], dpi, primary_specs)
    plot_price_and_mas(indicators, chart_paths[2], dpi, strategy_config["ma_windows"])
    plot_signal_alignment(daily, chart_paths[3], dpi, primary_specs[1:])

    common_mask = parse_boolean_column(
        daily["InCommonPeriod"], column_name="InCommonPeriod"
    )
    common = daily.loc[common_mask, "Date"]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "\n".join(
            [
                "# Phase 6 Visualization Report",
                "",
                "- Charts consume saved Phase 2, Phase 4, and Phase 5 outputs.",
                "- Strategy indicators, signals, positions, returns, and metrics are not recalculated.",
                f"- Common comparison period: {common.iloc[0]:%Y-%m-%d} to {common.iloc[-1]:%Y-%m-%d}",
                "- Saved raw-signal/executed-position shift(1) alignment: PASS",
                "- Parameter optimization or strategy-rule changes: none",
                "- Phase 6 status: PASS",
                "",
            ]
        ),
        encoding="utf-8",
    )
    for path in chart_paths:
        logging.info("Saved chart: %s", path)
    return chart_paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Render Phase 6 saved-output charts")
    parser.add_argument("--config", type=Path, default=Path("config/config.yaml"))
    args = parser.parse_args()
    try:
        paths = run_phase6(_repository_path(str(args.config)))
    except (AssertionError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"Phase 6 failed: {exc}", file=sys.stderr)
        return 1
    print(f"Phase 6 complete: {len(paths)} charts from saved outputs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

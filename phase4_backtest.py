"""Phase 4 entry point: executed positions and daily return engine only."""

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

from ccb_quant.backtest import add_primary_backtests  # noqa: E402


def _repository_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def build_backtest_report(
    frame: pd.DataFrame,
    *,
    primary_raw_signal_columns: list[str],
    common_start: object,
    transaction_cost_bps: float,
) -> str:
    """Document formulas and alignment without calculating aggregate metrics."""

    start_date = frame.loc[common_start, "Date"]
    common_rows = int(frame["InCommonPeriod"].sum())
    lines = [
        "# 日频回测引擎报告 / Daily Backtest Engine Report",
        "",
        "## 范围",
        "",
        "本阶段只实现executed positions与逐日return engine，不计算aggregate metrics、robustness summary或charts。",
        "",
        "## 固定公式",
        "",
        "- `executed_position = raw_signal.shift(1)`",
        "- `asset_return = Close.pct_change()`",
        "- `turnover = abs(executed_position - executed_position.shift(1))`",
        "- `cost_rate = transaction_cost_bps / 10000`",
        "- `transaction_cost = turnover * cost_rate`",
        "- `gross_return = executed_position * asset_return`",
        "- `net_return = gross_return - transaction_cost`",
        "- `gross_nav = (1 + gross_return).cumprod()`",
        "- `net_nav = (1 + net_return).cumprod()`",
        "",
        "## 比较区间与成本",
        "",
        "- Common start: automatically derived from configured primary shifted signals",
        f"- Derived common start date: {start_date.strftime('%Y-%m-%d')}",
        f"- Common comparison rows: {common_rows}",
        f"- Primary transaction cost: {transaction_cost_bps:g} bps per unit turnover",
        "- Position immediately before common start: Cash (0)",
        "- Initial Long at common start: charged one entry cost",
        "- Pre-common-period return/cost/NAV fields: preserved as NaN",
        "",
        "## Primary daily strategies",
        "",
    ]
    for raw_column in primary_raw_signal_columns:
        prefix = raw_column.removesuffix("_RawSignal")
        lines.append(
            f"- `{raw_column}` remains separate from `{prefix}_ExecutedPosition`"
        )
    lines.extend(
        [
            "",
            "## 未实现内容",
            "",
            "- Aggregate performance metrics: not implemented",
            "- Robustness summaries: not implemented",
            "- Charts: not implemented",
            "- Phase 4 engine status: PASS",
            "",
        ]
    )
    return "\n".join(lines)


def run_phase4(config_path: Path) -> pd.DataFrame:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    indicator_config = config["indicators"]
    backtest_config = config["backtest"]
    output_config = config["outputs"]

    input_path = _repository_path(output_config["raw_signal_file"])
    output_path = _repository_path(output_config["daily_backtest_file"])
    report_path = _repository_path(output_config["backtest_report"])
    log_path = _repository_path(output_config["phase4_log_file"])
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

    frame = pd.read_csv(
        input_path,
        parse_dates=["Date"],
        float_precision="round_trip",
    )
    ma_windows = sorted(int(value) for value in indicator_config["ma_windows"])
    primary_momentum_lookback = int(
        indicator_config["primary_momentum_lookback"]
    )
    primary_raw_signal_columns = [
        "BuyHold_RawSignal",
        f"MA{ma_windows[0]}_{ma_windows[1]}_RawSignal",
        f"TSMOM{primary_momentum_lookback}_RawSignal",
    ]
    common_period_raw_signal_columns = [
        "BuyHold_RawSignal",
        f"MA{ma_windows[0]}_{ma_windows[1]}_RawSignal",
        *[
            f"TSMOM{int(lookback)}_RawSignal"
            for lookback in indicator_config["momentum_lookbacks"]
        ],
    ]
    cost_bps = float(backtest_config["transaction_cost_bps"])
    initial_position = float(backtest_config["initial_position"])

    logging.info("Loading Phase 3 raw signals: %s", input_path)
    enriched, common_start = add_primary_backtests(
        frame,
        primary_raw_signal_columns=primary_raw_signal_columns,
        common_period_raw_signal_columns=common_period_raw_signal_columns,
        transaction_cost_bps=cost_bps,
        initial_position=initial_position,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    enriched.to_csv(output_path, index=False, date_format="%Y-%m-%d")
    report_path.write_text(
        build_backtest_report(
            enriched,
            primary_raw_signal_columns=primary_raw_signal_columns,
            common_start=common_start,
            transaction_cost_bps=cost_bps,
        ),
        encoding="utf-8",
    )
    logging.info(
        "Phase 4 PASS: common period starts %s",
        enriched.loc[common_start, "Date"].strftime("%Y-%m-%d"),
    )
    logging.info("Daily backtest data: %s", output_path)
    logging.info("Backtest report: %s", report_path)
    return enriched


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 4 daily backtest engine")
    parser.add_argument(
        "--config", type=Path, default=Path("config/config.yaml")
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = _repository_path(str(args.config))
    try:
        frame = run_phase4(config_path)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"Phase 4 failed: {exc}", file=sys.stderr)
        return 1
    print(f"Phase 4 daily engine complete: {len(frame)} rows. No aggregate metrics or charts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

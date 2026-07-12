"""Phase 5 aggregate metrics and pre-declared robustness analysis."""

from __future__ import annotations

import argparse
import hashlib
import logging
from pathlib import Path
import sys

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ccb_quant.backtest import run_daily_backtest  # noqa: E402
from ccb_quant.metrics import drawdown_from_nav, summarize_performance  # noqa: E402
from ccb_quant.naming import configured_strategy_specs  # noqa: E402
from ccb_quant.validation import parse_boolean_column  # noqa: E402


def _repository_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _strategy_columns(prefix: str) -> dict[str, str]:
    return {
        "daily_return": f"{prefix}_NetReturn",
        "nav": f"{prefix}_NetNAV",
        "position": f"{prefix}_ExecutedPosition",
        "turnover": f"{prefix}_Turnover",
    }


def _summary_row(
    frame: pd.DataFrame,
    *,
    strategy: str,
    prefix: str,
    lookback: int | None,
    cost_bps: float,
    annual_trading_days: int,
    risk_free_annual_rate: float,
    initial_position: float,
    result_type: str,
) -> dict[str, object]:
    columns = _strategy_columns(prefix)
    metrics = summarize_performance(
        frame[columns["daily_return"]],
        frame[columns["nav"]],
        frame[columns["position"]],
        frame[columns["turnover"]],
        annual_trading_days=annual_trading_days,
        risk_free_annual_rate=risk_free_annual_rate,
        initial_position=initial_position,
    )
    return {
        "ResultType": result_type,
        "Strategy": strategy,
        "MomentumLookback": lookback,
        "TransactionCostBps": cost_bps,
        **metrics,
    }


def validate_phase5_inputs(
    daily: pd.DataFrame,
    raw: pd.DataFrame,
    primary_prefixes: list[str],
    common_prefixes: list[str] | None = None,
) -> tuple[pd.Series, pd.Index]:
    """Fail closed unless Phase 4 and Phase 3 saved rows are exactly aligned."""

    if len(daily) != len(raw):
        raise ValueError("Phase 5 inputs have different row counts")
    for column in ["Date", "Close"]:
        try:
            pd.testing.assert_series_equal(
                daily[column].reset_index(drop=True),
                raw[column].reset_index(drop=True),
                check_names=False,
                check_exact=True,
            )
        except AssertionError as exc:
            raise ValueError(f"Phase 5 input {column} columns do not align") from exc
    if daily["Date"].duplicated().any() or not daily["Date"].is_monotonic_increasing:
        raise ValueError("Phase 5 dates must be unique and increasing")
    for prefix in primary_prefixes:
        expected = raw[f"{prefix}_RawSignal"].shift(1)
        actual = daily[f"{prefix}_ExecutedPosition"]
        try:
            pd.testing.assert_series_equal(
                actual.reset_index(drop=True),
                expected.reset_index(drop=True),
                check_names=False,
                check_exact=True,
            )
        except AssertionError as exc:
            raise ValueError(
                f"{prefix} executed position does not equal raw signal shift(1)"
            ) from exc
    common_mask = parse_boolean_column(
        daily["InCommonPeriod"], column_name="InCommonPeriod"
    )
    common_index = common_mask.index[common_mask]
    if common_index.empty:
        raise ValueError("Phase 4 file contains no common comparison period")
    expected_mask = pd.Series(False, index=daily.index)
    expected_mask.loc[common_index[0] :] = True
    if not common_mask.equals(expected_mask):
        raise ValueError("common-period mask must be one contiguous terminal period")
    executed_columns = [f"{prefix}_ExecutedPosition" for prefix in primary_prefixes]
    if daily.loc[common_index, executed_columns].isna().any().any():
        raise ValueError("common-period mask includes invalid primary positions")
    readiness = pd.DataFrame(
        {
            prefix: raw[f"{prefix}_RawSignal"].shift(1)
            for prefix in (common_prefixes or primary_prefixes)
        }
    ).notna().all(axis=1)
    if not readiness.loc[common_index].all():
        raise ValueError("common-period mask includes invalid configured signals")
    if common_index[0] > 0 and readiness.loc[common_index[0] - 1]:
        raise ValueError("common-period mask starts after all primary positions are valid")
    return common_mask, common_index


def build_report(
    primary: pd.DataFrame,
    robustness: pd.DataFrame,
    *,
    common_start_date: str,
    common_rows: int,
    annual_trading_days: int,
    risk_free_annual_rate: float,
    robustness_labels: list[str],
    input_hashes: dict[str, str],
    primary_cost_bps: float,
) -> str:
    return "\n".join(
        [
            "# Phase 5 Metrics and Robustness Report",
            "",
            "## Methodology",
            "",
            f"- Common comparison start: {common_start_date} (automatically derived in Phase 4)",
            f"- Common daily observations: {common_rows}",
            f"- Annualization: {annual_trading_days} trading observations",
            f"- Sharpe annual risk-free rate: {risk_free_annual_rate:.1%}",
            f"- Phase 4 daily input SHA-256: {input_hashes['daily']}",
            f"- Phase 3 raw-signal input SHA-256: {input_hashes['raw']}",
            f"- Primary results: net returns at {primary_cost_bps:g} bps per unit turnover",
            "- Trade count: number of executed-position changes where turnover > 0",
            "- Entries/exits: positive/negative executed-position changes, including initial entry from Cash",
            "- Maximum drawdown: minimum of NAV / running peak - 1, with initial capital 1 included",
            "",
            "## Output scope",
            "",
            f"- Primary summary rows: {len(primary)}",
            f"- Pre-declared robustness rows: {len(robustness)}",
            "- Primary net drawdown series saved separately for the later chart phase",
            f"- Robustness grid: {', '.join(robustness_labels)} at configured cost sensitivities",
            "- Sensitivity results are not used to redefine the primary strategy",
            "- Charts: not implemented in Phase 5",
            "- Phase 5 status: PASS",
            "",
        ]
    )


def run_phase5(config_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    outputs = config["outputs"]
    backtest = config["backtest"]
    metrics_config = config["metrics"]
    indicators = config["indicators"]
    strategy_config = configured_strategy_specs(indicators)

    daily_path = _repository_path(outputs["daily_backtest_file"])
    raw_path = _repository_path(outputs["raw_signal_file"])
    primary_path = _repository_path(outputs["performance_summary_file"])
    robustness_path = _repository_path(outputs["robustness_summary_file"])
    drawdown_path = _repository_path(outputs["drawdown_series_file"])
    report_path = _repository_path(outputs["metrics_report"])
    log_path = _repository_path(outputs["phase5_log_file"])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler()],
        force=True,
    )

    daily = pd.read_csv(daily_path, parse_dates=["Date"], float_precision="round_trip")
    raw = pd.read_csv(raw_path, parse_dates=["Date"], float_precision="round_trip")
    input_hashes = {"daily": _sha256(daily_path), "raw": _sha256(raw_path)}
    primary_specs = strategy_config["primary"]
    common_mask, common_index = validate_phase5_inputs(
        daily,
        raw,
        [spec["prefix"] for spec in primary_specs],
        [spec["prefix"] for spec in strategy_config["robustness"]],
    )
    common_start = common_index[0]
    common_start_date = daily.loc[common_start, "Date"].strftime("%Y-%m-%d")
    annual_days = int(metrics_config["annual_trading_days"])
    risk_free = float(metrics_config["risk_free_annual_rate"])
    primary_cost = float(backtest["transaction_cost_bps"])
    initial_position = float(backtest["initial_position"])

    primary_rows = [
        _summary_row(
            daily,
            strategy=spec["label"],
            prefix=spec["prefix"],
            lookback=spec["lookback"],
            cost_bps=primary_cost,
            annual_trading_days=annual_days,
            risk_free_annual_rate=risk_free,
            initial_position=initial_position,
            result_type="Primary",
        )
        for spec in primary_specs
    ]
    primary = pd.DataFrame(primary_rows)
    period_metadata = {
        "CommonStart": common_start_date,
        "CommonEnd": daily.loc[common_index[-1], "Date"].strftime("%Y-%m-%d"),
        "Observations": int(common_mask.sum()),
    }
    for column, value in reversed(period_metadata.items()):
        primary.insert(2, column, value)

    robustness_rows: list[dict[str, object]] = []
    for spec in strategy_config["robustness"]:
        raw_column = f'{spec["prefix"]}_RawSignal'
        for cost_bps in backtest["cost_sensitivity_bps"]:
            result = run_daily_backtest(
                raw["Close"],
                raw[raw_column],
                common_start=common_start,
                transaction_cost_bps=float(cost_bps),
                initial_position=initial_position,
            )
            temporary = pd.DataFrame(index=raw.index)
            prefix = "Variant"
            for column in result.columns:
                temporary[f"{prefix}_{column}"] = result[column]
            robustness_rows.append(
                _summary_row(
                    temporary,
                    strategy=spec["label"],
                    prefix=prefix,
                    lookback=spec["lookback"],
                    cost_bps=float(cost_bps),
                    annual_trading_days=annual_days,
                    risk_free_annual_rate=risk_free,
                    initial_position=initial_position,
                    result_type="SensitivityOnly",
                )
            )
    robustness = pd.DataFrame(robustness_rows)
    for column, value in reversed(period_metadata.items()):
        robustness.insert(2, column, value)

    drawdowns = pd.DataFrame({"Date": daily["Date"]})
    for spec in primary_specs:
        prefix = spec["prefix"]
        drawdowns[f"{prefix}_NetDrawdown"] = drawdown_from_nav(
            daily[f"{prefix}_NetNAV"]
        )

    primary_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    primary.to_csv(primary_path, index=False)
    robustness.to_csv(robustness_path, index=False)
    drawdowns.to_csv(drawdown_path, index=False, date_format="%Y-%m-%d")
    report_path.write_text(
        build_report(
            primary,
            robustness,
            common_start_date=common_start_date,
            common_rows=int(common_mask.sum()),
            annual_trading_days=annual_days,
            risk_free_annual_rate=risk_free,
            robustness_labels=[spec["label"] for spec in strategy_config["robustness"]],
            input_hashes=input_hashes,
            primary_cost_bps=primary_cost,
        ),
        encoding="utf-8",
    )
    logging.info("Phase 5 PASS: common start %s", common_start_date)
    logging.info("Primary summary: %s", primary_path)
    logging.info("Robustness summary: %s", robustness_path)
    logging.info("Primary drawdown series: %s", drawdown_path)
    return primary, robustness


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 5 metrics and robustness")
    parser.add_argument("--config", type=Path, default=Path("config/config.yaml"))
    args = parser.parse_args()
    try:
        primary, robustness = run_phase5(_repository_path(str(args.config)))
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"Phase 5 failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"Phase 5 complete: {len(primary)} primary rows, "
        f"{len(robustness)} sensitivity rows. No charts."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

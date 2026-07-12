from pathlib import Path

import pandas as pd
import pytest
import yaml

from ccb_quant.naming import configured_strategy_specs


PROJECT_ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(
    not (PROJECT_ROOT / "results/daily_backtest_results.csv").exists(),
    reason="licensed-data daily artifacts are intentionally absent",
)

CONFIG = yaml.safe_load(
    (PROJECT_ROOT / "config/config.yaml").read_text(encoding="utf-8")
)
PRIMARY_SPECS = configured_strategy_specs(CONFIG["indicators"])["primary"]
STRATEGY_PREFIX = {
    spec["label"]: spec["prefix"] for spec in PRIMARY_SPECS
}
PRIMARY_COST_BPS = float(CONFIG["backtest"]["transaction_cost_bps"])

METRIC_COLUMNS = [
    "CumulativeReturn",
    "AnnualizedReturn",
    "AnnualizedVolatility",
    "SharpeRatio",
    "MaximumDrawdown",
    "CalmarRatio",
    "TradeCount",
    "Entries",
    "Exits",
    "TotalTurnover",
    "TimeInMarket",
]


def _read_csv(relative_path: str) -> pd.DataFrame:
    return pd.read_csv(
        PROJECT_ROOT / relative_path,
        float_precision="round_trip",
    )


def test_primary_cumulative_return_equals_final_net_nav_minus_one() -> None:
    summary = _read_csv("results/performance_summary.csv")
    daily = _read_csv("results/daily_backtest_results.csv")

    for strategy, prefix in STRATEGY_PREFIX.items():
        saved_return = summary.loc[
            summary["Strategy"].eq(strategy), "CumulativeReturn"
        ].iloc[0]
        final_nav = daily[f"{prefix}_NetNAV"].dropna().iloc[-1]
        assert saved_return == final_nav - 1.0


def test_primary_strategies_have_identical_comparison_period_metadata() -> None:
    summary = _read_csv("results/performance_summary.csv")
    period_columns = ["CommonStart", "CommonEnd", "Observations"]

    assert len(summary[period_columns].drop_duplicates()) == 1


def test_primary_cost_rows_exactly_match_robustness_rows() -> None:
    primary = _read_csv("results/performance_summary.csv").set_index("Strategy")
    robustness = _read_csv("results/robustness_summary.csv")
    robustness = robustness.loc[
        robustness["TransactionCostBps"].eq(PRIMARY_COST_BPS)
        & robustness["Strategy"].isin(STRATEGY_PREFIX)
    ].set_index("Strategy")
    comparison_columns = [
        "CommonStart",
        "CommonEnd",
        "Observations",
        "TransactionCostBps",
        *METRIC_COLUMNS,
    ]

    pd.testing.assert_frame_equal(
        primary.loc[list(STRATEGY_PREFIX), comparison_columns],
        robustness.loc[list(STRATEGY_PREFIX), comparison_columns],
        check_exact=True,
    )


def test_saved_maximum_drawdown_equals_saved_daily_series_minimum() -> None:
    summary = _read_csv("results/performance_summary.csv")
    drawdowns = _read_csv("results/daily_drawdowns.csv")

    for strategy, prefix in STRATEGY_PREFIX.items():
        saved_drawdown = summary.loc[
            summary["Strategy"].eq(strategy), "MaximumDrawdown"
        ].iloc[0]
        daily_minimum = drawdowns[f"{prefix}_NetDrawdown"].min()
        assert saved_drawdown == daily_minimum

"""Phase 4 daily execution and return engine.

This module implements one-row execution lag, turnover, costs, daily returns,
and NAV only. It deliberately excludes aggregate metrics, robustness summaries,
and charts.
"""

from __future__ import annotations

from collections.abc import Mapping
from numbers import Real

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype


def execute_raw_signal(raw_signal: pd.Series) -> pd.Series:
    """Apply the required one-observation lag exactly once."""

    if not isinstance(raw_signal, pd.Series):
        raise TypeError("raw_signal must be a pandas Series")
    if not is_numeric_dtype(raw_signal.dtype):
        raise TypeError("raw_signal must be numeric")
    values = raw_signal.dropna()
    if not values.isin([0.0, 1.0]).all():
        raise ValueError("raw_signal must contain only 0, 1, or NaN")
    executed = raw_signal.shift(1)
    executed.name = "ExecutedPosition"
    return executed


def derive_common_start(raw_signals: Mapping[str, pd.Series]) -> object:
    """Return the first row where every shifted primary signal is valid."""

    if not raw_signals:
        raise ValueError("at least one primary raw signal is required")
    positions: dict[str, pd.Series] = {}
    common_index: pd.Index | None = None
    for name, raw_signal in raw_signals.items():
        if common_index is None:
            common_index = raw_signal.index
        elif not raw_signal.index.equals(common_index):
            raise ValueError("all raw signals must use the same index")
        positions[name] = execute_raw_signal(raw_signal)
    position_frame = pd.DataFrame(positions)
    all_valid = position_frame.notna().all(axis=1)
    if not all_valid.any():
        raise ValueError("primary signals have no common valid period")
    start = all_valid.index[all_valid.to_numpy().argmax()]
    if position_frame.loc[start:].isna().any().any():
        raise ValueError("executed positions contain gaps after common start")
    return start


def calculate_asset_return(close: pd.Series) -> pd.Series:
    """Return simple close-to-close percentage change."""

    if not isinstance(close, pd.Series) or not is_numeric_dtype(close.dtype):
        raise TypeError("close must be a numeric pandas Series")
    if close.isna().any() or (close <= 0).any():
        raise ValueError("close must contain positive, non-missing values")
    result = close.pct_change(fill_method=None)
    result.name = "AssetReturn"
    return result


def run_daily_backtest(
    close: pd.Series,
    raw_signal: pd.Series,
    *,
    common_start: object,
    transaction_cost_bps: float,
    initial_position: float = 0.0,
) -> pd.DataFrame:
    """Run one strategy while preserving pre-common-period warm-up values."""

    if not close.index.equals(raw_signal.index):
        raise ValueError("close and raw_signal indexes must match")
    if common_start not in close.index:
        raise ValueError("common_start must be an observed row")
    if isinstance(transaction_cost_bps, bool) or not isinstance(
        transaction_cost_bps, Real
    ):
        raise TypeError("transaction_cost_bps must be numeric")
    if transaction_cost_bps < 0:
        raise ValueError("transaction_cost_bps must be non-negative")
    if initial_position not in (0.0, 1.0):
        raise ValueError("initial_position must be 0 or 1")

    asset_return = calculate_asset_return(close)
    executed = execute_raw_signal(raw_signal)
    comparison_position = executed.loc[common_start:]
    comparison_asset_return = asset_return.loc[common_start:]
    if comparison_position.isna().any() or comparison_asset_return.isna().any():
        raise ValueError("common comparison period must contain valid positions and returns")

    previous_position = comparison_position.shift(1)
    previous_position.iloc[0] = initial_position
    turnover = (comparison_position - previous_position).abs()
    gross_return = comparison_position * comparison_asset_return
    cost_rate = float(transaction_cost_bps) / 10_000.0
    transaction_cost = turnover * cost_rate
    net_return = gross_return - transaction_cost
    gross_nav = (1.0 + gross_return).cumprod()
    net_nav = (1.0 + net_return).cumprod()

    output = pd.DataFrame(index=close.index)
    output["ExecutedPosition"] = executed
    output["Turnover"] = turnover.reindex(close.index)
    output["GrossReturn"] = gross_return.reindex(close.index)
    output["TransactionCost"] = transaction_cost.reindex(close.index)
    output["NetReturn"] = net_return.reindex(close.index)
    output["GrossNAV"] = gross_nav.reindex(close.index)
    output["NetNAV"] = net_nav.reindex(close.index)
    output.attrs["cost_rate"] = cost_rate
    output.attrs["common_start"] = common_start
    return output


def add_primary_backtests(
    raw_signal_frame: pd.DataFrame,
    *,
    primary_raw_signal_columns: list[str],
    common_period_raw_signal_columns: list[str] | None = None,
    transaction_cost_bps: float,
    initial_position: float = 0.0,
) -> tuple[pd.DataFrame, object]:
    """Add primary executed positions and daily backtest fields to a copy."""

    if "Close" not in raw_signal_frame.columns:
        raise ValueError("raw_signal_frame must contain Close")
    common_columns = common_period_raw_signal_columns or primary_raw_signal_columns
    missing = [
        column
        for column in set(primary_raw_signal_columns + common_columns)
        if column not in raw_signal_frame.columns
    ]
    if missing:
        raise ValueError("missing primary raw signals: " + ", ".join(missing))

    raw_signals = {column: raw_signal_frame[column] for column in common_columns}
    common_start = derive_common_start(raw_signals)
    asset_return = calculate_asset_return(raw_signal_frame["Close"])

    enriched = raw_signal_frame.copy(deep=True)
    enriched["AssetReturn"] = asset_return
    enriched["InCommonPeriod"] = False
    enriched.loc[common_start:, "InCommonPeriod"] = True

    for raw_column in primary_raw_signal_columns:
        prefix = raw_column.removesuffix("_RawSignal")
        result = run_daily_backtest(
            raw_signal_frame["Close"],
            raw_signal_frame[raw_column],
            common_start=common_start,
            transaction_cost_bps=transaction_cost_bps,
            initial_position=initial_position,
        )
        for result_column in result.columns:
            enriched[f"{prefix}_{result_column}"] = result[result_column]
    return enriched, common_start


__all__ = [
    "add_primary_backtests",
    "calculate_asset_return",
    "derive_common_start",
    "execute_raw_signal",
    "run_daily_backtest",
]

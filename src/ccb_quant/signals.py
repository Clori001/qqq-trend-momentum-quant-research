"""Raw long/cash signal rules for Phase 3 only.

This module intentionally stops before execution. It contains no shifted
positions, asset returns, transaction costs, NAV, metrics, or charts.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype


def _validate_aligned_series(left: pd.Series, right: pd.Series) -> None:
    if not isinstance(left, pd.Series) or not isinstance(right, pd.Series):
        raise TypeError("indicator inputs must be pandas Series")
    if not left.index.equals(right.index):
        raise ValueError("indicator inputs must have identical indexes")
    if not is_numeric_dtype(left.dtype) or not is_numeric_dtype(right.dtype):
        raise TypeError("indicator inputs must be numeric")


def buy_and_hold_raw_signal(index: pd.Index) -> pd.Series:
    """Return a raw long signal for every available observation."""

    return pd.Series(1.0, index=index, name="BuyHold_RawSignal")


def ma_trend_raw_signal(
    short_average: pd.Series, long_average: pd.Series
) -> pd.Series:
    """Return 1 when short MA is strictly above long MA, otherwise 0.

    Rows where either moving average is unavailable remain ``NaN`` rather
    than being labelled as cash.
    """

    _validate_aligned_series(short_average, long_average)
    ready = short_average.notna() & long_average.notna()
    signal = pd.Series(np.nan, index=short_average.index, dtype=float)
    signal.loc[ready] = (
        short_average.loc[ready] > long_average.loc[ready]
    ).astype(float)
    signal.name = "MA_RawSignal"
    return signal


def completed_month_end_mask(
    dates: pd.Series,
    *,
    exclude_terminal_month_without_next_observation: bool = True,
) -> pd.Series:
    """Identify the last observed row of months confirmed by a later month.

    The final dataset month is excluded when no next-month observation exists.
    This prevents the partial terminal month from being treated as completed.
    """

    if not isinstance(dates, pd.Series):
        raise TypeError("dates must be a pandas Series")
    if not is_datetime64_any_dtype(dates.dtype):
        raise TypeError("dates must contain datetime values")
    if dates.isna().any() or not dates.is_monotonic_increasing:
        raise ValueError("dates must be complete and sorted ascending")

    month = dates.dt.to_period("M")
    mask = month.ne(month.shift(-1))
    if exclude_terminal_month_without_next_observation and not mask.empty:
        mask.iloc[-1] = False
    mask.name = "CompletedMonthEnd"
    return mask


def monthly_momentum_raw_signal(
    momentum: pd.Series,
    dates: pd.Series,
    *,
    exclude_terminal_month_without_next_observation: bool = True,
) -> tuple[pd.Series, pd.Series]:
    """Create a month-end momentum decision and hold it until the next one."""

    if not isinstance(momentum, pd.Series) or not is_numeric_dtype(momentum.dtype):
        raise TypeError("momentum must be a numeric pandas Series")
    if not momentum.index.equals(dates.index):
        raise ValueError("momentum and dates must have identical indexes")

    month_end = completed_month_end_mask(
        dates,
        exclude_terminal_month_without_next_observation=(
            exclude_terminal_month_without_next_observation
        ),
    )
    valid_decision = month_end & momentum.notna()
    decisions = pd.Series(np.nan, index=momentum.index, dtype=float)
    decisions.loc[valid_decision] = (
        momentum.loc[valid_decision] > 0.0
    ).astype(float)

    raw_signal = decisions.ffill()
    raw_signal.name = "TSMOM_RawSignal"
    decision_flag = valid_decision.astype(bool)
    decision_flag.name = "TSMOM_DecisionFlag"
    return raw_signal, decision_flag


def add_raw_signals(
    indicator_frame: pd.DataFrame,
    *,
    ma_windows: Iterable[int],
    momentum_lookbacks: Iterable[int],
    exclude_terminal_month_without_next_observation: bool,
) -> pd.DataFrame:
    """Return a copy of indicator data with raw signals and decision flags."""

    if not isinstance(indicator_frame, pd.DataFrame):
        raise TypeError("indicator_frame must be a pandas DataFrame")
    if "Date" not in indicator_frame or "Close" not in indicator_frame:
        raise ValueError("indicator_frame must contain Date and Close")

    windows = list(ma_windows)
    lookbacks = list(momentum_lookbacks)
    if len(windows) != 2:
        raise ValueError("Phase 3 requires exactly two configured MA windows")
    if not lookbacks:
        raise ValueError("at least one momentum lookback is required")

    short_window, long_window = sorted(windows)
    short_column = f"MA{short_window}"
    long_column = f"MA{long_window}"
    required_columns = [short_column, long_column] + [
        f"Momentum{lookback}" for lookback in lookbacks
    ]
    missing = [column for column in required_columns if column not in indicator_frame]
    if missing:
        raise ValueError("missing configured indicator columns: " + ", ".join(missing))

    enriched = indicator_frame.copy(deep=True)
    enriched["BuyHold_RawSignal"] = buy_and_hold_raw_signal(enriched.index)
    enriched[f"MA{short_window}_{long_window}_RawSignal"] = ma_trend_raw_signal(
        enriched[short_column], enriched[long_column]
    )

    for lookback in lookbacks:
        raw_signal, decision_flag = monthly_momentum_raw_signal(
            enriched[f"Momentum{lookback}"],
            enriched["Date"],
            exclude_terminal_month_without_next_observation=(
                exclude_terminal_month_without_next_observation
            ),
        )
        enriched[f"TSMOM{lookback}_RawSignal"] = raw_signal
        enriched[f"TSMOM{lookback}_DecisionFlag"] = decision_flag
    return enriched


__all__ = [
    "add_raw_signals",
    "buy_and_hold_raw_signal",
    "completed_month_end_mask",
    "ma_trend_raw_signal",
    "monthly_momentum_raw_signal",
]

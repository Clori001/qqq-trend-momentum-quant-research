"""Pure trailing indicators for Phase 2.

This module does not create strategy signals, positions, returns, costs, or
backtests. Warm-up observations remain missing by design.
"""

from __future__ import annotations

from collections.abc import Iterable
from numbers import Integral

import pandas as pd
from pandas.api.types import is_numeric_dtype


def _validate_numeric_series(values: pd.Series, label: str) -> None:
    if not isinstance(values, pd.Series):
        raise TypeError(f"{label} must be a pandas Series")
    if not is_numeric_dtype(values.dtype):
        raise TypeError(f"{label} must contain numeric values")


def _validate_window(window: int, label: str) -> None:
    if isinstance(window, bool) or not isinstance(window, Integral) or window <= 0:
        raise ValueError(f"{label} must be a positive integer")


def simple_moving_average(values: pd.Series, window: int) -> pd.Series:
    """Return a trailing SMA with exactly ``window`` required observations."""

    _validate_numeric_series(values, "values")
    _validate_window(window, "window")
    result = values.rolling(window=window, min_periods=window).mean()
    result.name = f"MA{window}"
    return result


def price_momentum(close: pd.Series, lookback: int) -> pd.Series:
    """Return ``Close / Close.shift(lookback) - 1`` with preserved warm-up."""

    _validate_numeric_series(close, "close")
    _validate_window(lookback, "lookback")
    result = close / close.shift(lookback) - 1.0
    result.name = f"Momentum{lookback}"
    return result


def add_indicators(
    frame: pd.DataFrame,
    *,
    ma_windows: Iterable[int],
    momentum_lookbacks: Iterable[int],
) -> pd.DataFrame:
    """Return a copy of cleaned OHLCV data with configured indicator columns."""

    if not isinstance(frame, pd.DataFrame):
        raise TypeError("frame must be a pandas DataFrame")
    if "Close" not in frame.columns:
        raise ValueError("frame must contain a Close column")
    _validate_numeric_series(frame["Close"], "Close")

    windows = list(ma_windows)
    if not windows:
        raise ValueError("ma_windows must contain at least one window")
    if len(windows) != len(set(windows)):
        raise ValueError("ma_windows must not contain duplicates")
    for window in windows:
        _validate_window(window, "MA window")
    lookbacks = list(momentum_lookbacks)
    if not lookbacks:
        raise ValueError("momentum_lookbacks must contain at least one lookback")
    if len(lookbacks) != len(set(lookbacks)):
        raise ValueError("momentum_lookbacks must not contain duplicates")
    for lookback in lookbacks:
        _validate_window(lookback, "momentum lookback")

    enriched = frame.copy(deep=True)
    for window in windows:
        enriched[f"MA{window}"] = simple_moving_average(
            enriched["Close"], window
        )
    for lookback in lookbacks:
        enriched[f"Momentum{lookback}"] = price_momentum(
            enriched["Close"], lookback
        )
    return enriched


__all__ = ["add_indicators", "price_momentum", "simple_moving_average"]

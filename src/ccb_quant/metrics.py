"""Aggregate performance metrics for completed daily backtests."""

from __future__ import annotations

from numbers import Real

import numpy as np
import pandas as pd


def _valid_returns(daily_return: pd.Series) -> pd.Series:
    if not isinstance(daily_return, pd.Series):
        raise TypeError("daily_return must be a pandas Series")
    values = daily_return.dropna().astype(float)
    if values.empty:
        raise ValueError("daily_return has no valid observations")
    if (values <= -1.0).any():
        raise ValueError("daily returns must be greater than -100%")
    return values


def cumulative_return(daily_return: pd.Series) -> float:
    values = _valid_returns(daily_return)
    return float((1.0 + values).prod() - 1.0)


def annualized_return(daily_return: pd.Series, annual_trading_days: int) -> float:
    values = _valid_returns(daily_return)
    growth = float((1.0 + values).prod())
    return growth ** (annual_trading_days / len(values)) - 1.0


def annualized_volatility(
    daily_return: pd.Series, annual_trading_days: int
) -> float:
    values = _valid_returns(daily_return)
    if len(values) < 2:
        return float("nan")
    return float(values.std(ddof=1) * np.sqrt(annual_trading_days))


def sharpe_ratio(
    daily_return: pd.Series,
    annual_trading_days: int,
    risk_free_annual_rate: float,
) -> float:
    values = _valid_returns(daily_return)
    daily_risk_free = (1.0 + risk_free_annual_rate) ** (
        1.0 / annual_trading_days
    ) - 1.0
    excess = values - daily_risk_free
    volatility = excess.std(ddof=1)
    if len(values) < 2 or np.isclose(volatility, 0.0):
        return float("nan")
    return float(excess.mean() / volatility * np.sqrt(annual_trading_days))


def drawdown_from_nav(nav: pd.Series) -> pd.Series:
    if not isinstance(nav, pd.Series):
        raise TypeError("nav must be a pandas Series")
    values = nav.dropna().astype(float)
    if values.empty or (values <= 0.0).any():
        raise ValueError("nav must contain positive valid observations")
    running_peak = values.cummax().clip(lower=1.0)
    result = values / running_peak - 1.0
    return result.reindex(nav.index)


def maximum_drawdown(nav: pd.Series) -> float:
    return float(drawdown_from_nav(nav).min())


def calmar_ratio(annual_return: float, max_drawdown: float) -> float:
    if np.isclose(max_drawdown, 0.0):
        return float("nan")
    return float(annual_return / abs(max_drawdown))


def position_statistics(
    position: pd.Series, turnover: pd.Series, initial_position: float = 0.0
) -> dict[str, float | int]:
    aligned = pd.concat(
        [position.rename("position"), turnover.rename("turnover")], axis=1
    ).dropna()
    if aligned.empty:
        raise ValueError("position and turnover have no common valid rows")
    previous = aligned["position"].shift(1)
    previous.iloc[0] = initial_position
    change = aligned["position"] - previous
    return {
        "TradeCount": int((aligned["turnover"] > 0.0).sum()),
        "Entries": int((change > 0.0).sum()),
        "Exits": int((change < 0.0).sum()),
        "TotalTurnover": float(aligned["turnover"].sum()),
        "TimeInMarket": float(aligned["position"].mean()),
    }


def summarize_performance(
    daily_return: pd.Series,
    nav: pd.Series,
    position: pd.Series,
    turnover: pd.Series,
    *,
    annual_trading_days: int,
    risk_free_annual_rate: float,
    initial_position: float = 0.0,
) -> dict[str, float | int]:
    ann_return = annualized_return(daily_return, annual_trading_days)
    max_dd = maximum_drawdown(nav)
    summary: dict[str, float | int] = {
        "CumulativeReturn": cumulative_return(daily_return),
        "AnnualizedReturn": ann_return,
        "AnnualizedVolatility": annualized_volatility(
            daily_return, annual_trading_days
        ),
        "SharpeRatio": sharpe_ratio(
            daily_return, annual_trading_days, risk_free_annual_rate
        ),
        "MaximumDrawdown": max_dd,
        "CalmarRatio": calmar_ratio(ann_return, max_dd),
    }
    summary.update(position_statistics(position, turnover, initial_position))
    for name, value in summary.items():
        if isinstance(value, Real) and np.isinf(value):
            raise ValueError(f"metric {name} must not be infinite")
    return summary


__all__ = [
    "annualized_return",
    "annualized_volatility",
    "calmar_ratio",
    "cumulative_return",
    "drawdown_from_nav",
    "maximum_drawdown",
    "position_statistics",
    "sharpe_ratio",
    "summarize_performance",
]

import numpy as np
import pandas as pd

from ccb_quant.metrics import (
    annualized_return,
    annualized_volatility,
    calmar_ratio,
    cumulative_return,
    drawdown_from_nav,
    maximum_drawdown,
    position_statistics,
    sharpe_ratio,
)


def test_cumulative_and_annualized_return_on_simple_growth_path() -> None:
    daily = pd.Series([0.10, 0.10])
    assert np.isclose(cumulative_return(daily), 0.21)
    assert np.isclose(annualized_return(daily, 2), 0.21)


def test_annualized_volatility_uses_sample_standard_deviation() -> None:
    daily = pd.Series([0.01, 0.03])
    expected = daily.std(ddof=1) * np.sqrt(252)
    assert np.isclose(annualized_volatility(daily, 252), expected)


def test_sharpe_uses_daily_excess_return_and_sample_volatility() -> None:
    daily = pd.Series([0.01, 0.03, -0.01])
    expected = daily.mean() / daily.std(ddof=1) * np.sqrt(252)
    assert np.isclose(sharpe_ratio(daily, 252, 0.0), expected)


def test_drawdown_and_calmar_match_hand_calculation() -> None:
    nav = pd.Series([1.0, 2.0, 1.0])
    expected = pd.Series([0.0, 0.0, -0.5])
    pd.testing.assert_series_equal(drawdown_from_nav(nav), expected)
    assert maximum_drawdown(nav) == -0.5
    assert calmar_ratio(0.10, -0.5) == 0.2


def test_drawdown_includes_initial_capital_peak_of_one() -> None:
    nav = pd.Series([0.9, 0.99])
    expected = pd.Series([-0.1, -0.01])
    assert np.allclose(drawdown_from_nav(nav), expected)


def test_position_statistics_count_entries_exits_and_initial_trade() -> None:
    position = pd.Series([1.0, 1.0, 0.0, 1.0])
    turnover = pd.Series([1.0, 0.0, 1.0, 1.0])
    result = position_statistics(position, turnover, initial_position=0.0)
    assert result == {
        "TradeCount": 3,
        "Entries": 2,
        "Exits": 1,
        "TotalTurnover": 3.0,
        "TimeInMarket": 0.75,
    }


def test_zero_drawdown_calmar_is_nan_not_infinite() -> None:
    assert np.isnan(calmar_ratio(0.10, 0.0))

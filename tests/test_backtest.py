import numpy as np
import pandas as pd

from ccb_quant.backtest import (
    add_primary_backtests,
    derive_common_start,
    execute_raw_signal,
    run_daily_backtest,
)


def _transition_backtest() -> pd.DataFrame:
    close = pd.Series([100.0, 110.0, 121.0, 108.9])
    raw_signal = pd.Series([1.0, 1.0, 0.0, 0.0])
    return run_daily_backtest(
        close,
        raw_signal,
        common_start=1,
        transaction_cost_bps=5.0,
        initial_position=0.0,
    )


def test_executed_position_is_exactly_raw_signal_shift_one() -> None:
    raw_signal = pd.Series([0.0, 1.0, 0.0, 1.0])

    executed = execute_raw_signal(raw_signal)

    expected = pd.Series(
        [np.nan, 0.0, 1.0, 0.0], name="ExecutedPosition"
    )
    pd.testing.assert_series_equal(executed, expected)


def test_date_t_signal_does_not_earn_date_t_return() -> None:
    close = pd.Series([100.0, 110.0, 121.0])
    raw_signal = pd.Series([0.0, 1.0, 1.0])
    result = run_daily_backtest(
        close,
        raw_signal,
        common_start=1,
        transaction_cost_bps=0.0,
    )

    assert raw_signal.iloc[1] == 1.0
    assert result["ExecutedPosition"].iloc[1] == 0.0
    assert result["GrossReturn"].iloc[1] == 0.0
    assert np.isclose(result["GrossReturn"].iloc[2], 0.1)


def test_zero_to_one_entry_has_unit_turnover() -> None:
    result = _transition_backtest()
    assert result["Turnover"].iloc[1] == 1.0


def test_one_to_zero_exit_has_unit_turnover() -> None:
    result = _transition_backtest()
    assert result["Turnover"].iloc[3] == 1.0


def test_unchanged_position_has_zero_turnover() -> None:
    result = _transition_backtest()
    assert result["Turnover"].iloc[2] == 0.0


def test_initial_long_entry_is_charged_from_cash() -> None:
    result = _transition_backtest()
    assert result["ExecutedPosition"].iloc[1] == 1.0
    assert result["TransactionCost"].iloc[1] == 0.0005


def test_transaction_cost_is_deducted_exactly_once() -> None:
    result = _transition_backtest()
    expected = result["GrossReturn"] - result["TransactionCost"]
    pd.testing.assert_series_equal(result["NetReturn"], expected, check_names=False)
    assert np.isclose(result["NetReturn"].iloc[1], 0.1 - 0.0005)


def test_nav_compounds_daily_returns() -> None:
    result = _transition_backtest()
    common = result.loc[1:]
    expected_gross = (1.0 + common["GrossReturn"]).cumprod()
    expected_net = (1.0 + common["NetReturn"]).cumprod()
    pd.testing.assert_series_equal(
        common["GrossNAV"], expected_gross, check_names=False
    )
    pd.testing.assert_series_equal(
        common["NetNAV"], expected_net, check_names=False
    )


def test_common_start_is_derived_from_all_shifted_primary_signals() -> None:
    raw_signals = {
        "buy_hold": pd.Series([1.0, 1.0, 1.0, 1.0, 1.0]),
        "ma": pd.Series([np.nan, 0.0, 1.0, 1.0, 1.0]),
        "momentum": pd.Series([np.nan, np.nan, np.nan, 1.0, 1.0]),
    }

    assert derive_common_start(raw_signals) == 4


def test_all_backtest_fields_are_nan_before_automatic_common_period() -> None:
    frame = pd.DataFrame(
        {
            "Close": [100.0, 101.0, 102.0, 103.0, 104.0],
            "BuyHold_RawSignal": [1.0, 1.0, 1.0, 1.0, 1.0],
            "MA_RawSignal": [np.nan, 0.0, 1.0, 1.0, 1.0],
            "Momentum_RawSignal": [np.nan, np.nan, np.nan, 1.0, 1.0],
        }
    )
    raw_columns = [
        "BuyHold_RawSignal",
        "MA_RawSignal",
        "Momentum_RawSignal",
    ]

    result, common_start = add_primary_backtests(
        frame,
        primary_raw_signal_columns=raw_columns,
        transaction_cost_bps=5.0,
    )

    assert common_start == 4
    calculated_suffixes = [
        "Turnover",
        "GrossReturn",
        "TransactionCost",
        "NetReturn",
        "GrossNAV",
        "NetNAV",
    ]
    calculated_columns = [
        f"{raw.removesuffix('_RawSignal')}_{suffix}"
        for raw in raw_columns
        for suffix in calculated_suffixes
    ]
    assert result.loc[: common_start - 1, calculated_columns].isna().all().all()


def test_buy_and_hold_first_valid_long_charges_initial_entry_from_cash() -> None:
    close = pd.Series([100.0, 101.0, 102.0])
    buy_hold_raw = pd.Series([1.0, 1.0, 1.0])

    result = run_daily_backtest(
        close,
        buy_hold_raw,
        common_start=1,
        transaction_cost_bps=5.0,
        initial_position=0.0,
    )

    assert result.loc[1, "ExecutedPosition"] == 1.0
    assert result.loc[1, "Turnover"] == 1.0
    assert result.loc[1, "TransactionCost"] == 0.0005
    assert result.loc[2, "TransactionCost"] == 0.0

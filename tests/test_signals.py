import numpy as np
import pandas as pd

from ccb_quant.signals import (
    add_raw_signals,
    buy_and_hold_raw_signal,
    completed_month_end_mask,
    ma_trend_raw_signal,
    monthly_momentum_raw_signal,
)


def test_buy_and_hold_raw_signal_is_long_on_every_row() -> None:
    index = pd.RangeIndex(4)
    expected = pd.Series([1.0, 1.0, 1.0, 1.0], name="BuyHold_RawSignal")
    pd.testing.assert_series_equal(buy_and_hold_raw_signal(index), expected)


def test_ma_raw_signal_preserves_warmup_and_uses_strict_tie_rule() -> None:
    short = pd.Series([np.nan, 2.0, 2.0, 3.0])
    long = pd.Series([np.nan, 2.0, 2.5, 2.0])

    result = ma_trend_raw_signal(short, long)

    expected = pd.Series([np.nan, 0.0, 0.0, 1.0], name="MA_RawSignal")
    pd.testing.assert_series_equal(result, expected)


def test_ma_boolean_comparison_does_not_convert_warmup_nan_to_zero() -> None:
    short = pd.Series([np.nan, np.nan, np.nan, 3.0])
    long = pd.Series([np.nan, np.nan, np.nan, 2.0])

    result = ma_trend_raw_signal(short, long)

    assert result.iloc[:3].isna().all()
    assert not result.iloc[:3].eq(0.0).any()
    assert result.iloc[3] == 1.0


def test_month_end_momentum_decisions_forward_hold_and_exclude_terminal_month() -> None:
    dates = pd.Series(
        pd.to_datetime(
            [
                "2020-01-30",
                "2020-01-31",
                "2020-02-03",
                "2020-02-28",
                "2020-03-02",
                "2020-03-10",
            ]
        )
    )
    momentum = pd.Series([np.nan, 0.2, 0.1, -0.1, -0.2, 0.3])

    raw_signal, decision_flag = monthly_momentum_raw_signal(momentum, dates)

    expected_signal = pd.Series(
        [np.nan, 1.0, 1.0, 0.0, 0.0, 0.0], name="TSMOM_RawSignal"
    )
    expected_flag = pd.Series(
        [False, True, False, True, False, False],
        name="TSMOM_DecisionFlag",
    )
    pd.testing.assert_series_equal(raw_signal, expected_signal)
    pd.testing.assert_series_equal(decision_flag, expected_flag)

    month_end = completed_month_end_mask(dates)
    assert month_end.tolist() == [False, True, False, True, False, False]


def test_raw_signal_builder_does_not_mutate_indicators_or_create_execution_fields() -> None:
    frame = pd.DataFrame(
        {
            "Date": pd.to_datetime(
                ["2020-01-30", "2020-01-31", "2020-02-03", "2020-02-28", "2020-03-10"]
            ),
            "Close": [10.0, 11.0, 12.0, 11.0, 13.0],
            "MA2": [np.nan, 10.5, 11.5, 11.5, 12.0],
            "MA3": [np.nan, np.nan, 11.0, 11.33, 12.0],
            "Momentum2": [np.nan, np.nan, 0.2, 0.0, 0.1],
        }
    )
    before = frame.copy(deep=True)

    result = add_raw_signals(
        frame,
        ma_windows=[2, 3],
        momentum_lookbacks=[2],
        exclude_terminal_month_without_next_observation=True,
    )

    pd.testing.assert_frame_equal(frame, before)
    assert "BuyHold_RawSignal" in result
    assert "MA2_3_RawSignal" in result
    assert "TSMOM2_RawSignal" in result
    assert "TSMOM2_DecisionFlag" in result
    forbidden = {
        "Position",
        "ExecutedPosition",
        "Return",
        "TransactionCost",
        "NAV",
    }
    assert forbidden.isdisjoint(result.columns)

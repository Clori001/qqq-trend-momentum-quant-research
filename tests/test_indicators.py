from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from ccb_quant.indicators import (
    add_indicators,
    price_momentum,
    simple_moving_average,
)


def test_simple_moving_average_is_trailing_and_preserves_warmup() -> None:
    values = pd.Series([1.0, 2.0, 3.0, 4.0])

    result = simple_moving_average(values, 3)

    expected = pd.Series([np.nan, np.nan, 2.0, 3.0], name="MA3")
    pd.testing.assert_series_equal(result, expected)


def test_price_momentum_requires_full_lookback() -> None:
    close = pd.Series([1.0, 2.0, 3.0, 4.0])

    result = price_momentum(close, 2)

    expected = pd.Series([np.nan, np.nan, 2.0, 1.0], name="Momentum2")
    pd.testing.assert_series_equal(result, expected)


def test_add_indicators_does_not_mutate_input() -> None:
    original = pd.DataFrame(
        {
            "Date": pd.date_range("2020-01-01", periods=5),
            "Close": [10.0, 11.0, 12.0, 13.0, 14.0],
        }
    )
    before = original.copy(deep=True)

    enriched = add_indicators(
        original, ma_windows=[2, 3], momentum_lookbacks=[2]
    )

    pd.testing.assert_frame_equal(original, before)
    assert list(enriched.columns) == ["Date", "Close", "MA2", "MA3", "Momentum2"]
    assert enriched["MA2"].isna().sum() == 1
    assert enriched["MA3"].isna().sum() == 2
    assert enriched["Momentum2"].isna().sum() == 2


def test_configured_indicators_use_no_future_values_and_preserve_warmups() -> None:
    config_path = Path(__file__).resolve().parents[1] / "config" / "config.yaml"
    indicator_config = yaml.safe_load(
        config_path.read_text(encoding="utf-8")
    )["indicators"]
    ma_windows = [int(value) for value in indicator_config["ma_windows"]]
    momentum_lookbacks = [
        int(value) for value in indicator_config["momentum_lookbacks"]
    ]

    original = pd.DataFrame(
        {
            "Date": pd.date_range("2020-01-01", periods=320),
            "Close": np.arange(1.0, 321.0),
        }
    )
    baseline = add_indicators(
        original,
        ma_windows=ma_windows,
        momentum_lookbacks=momentum_lookbacks,
    )

    cutoff = 270
    changed_future = original.copy(deep=True)
    changed_future.loc[cutoff + 1 :, "Close"] *= 100.0
    recalculated = add_indicators(
        changed_future,
        ma_windows=ma_windows,
        momentum_lookbacks=momentum_lookbacks,
    )

    indicator_columns = [f"MA{window}" for window in ma_windows] + [
        f"Momentum{lookback}" for lookback in momentum_lookbacks
    ]
    pd.testing.assert_frame_equal(
        baseline.loc[:cutoff, indicator_columns],
        recalculated.loc[:cutoff, indicator_columns],
    )
    for window in ma_windows:
        assert baseline[f"MA{window}"].isna().sum() == window - 1
    for lookback in momentum_lookbacks:
        assert baseline[f"Momentum{lookback}"].isna().sum() == lookback


@pytest.mark.parametrize("window", [0, -1, True, 1.5])
def test_invalid_indicator_window_is_rejected(window: object) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        simple_moving_average(pd.Series([1.0, 2.0]), window)  # type: ignore[arg-type]

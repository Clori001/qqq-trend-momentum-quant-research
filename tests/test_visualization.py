from pathlib import Path

import pandas as pd

from ccb_quant.visualization import (
    plot_drawdown_comparison,
    plot_nav_comparison,
    plot_price_and_mas,
    plot_signal_alignment,
)


def _dates() -> pd.Series:
    return pd.Series(pd.date_range("2020-01-01", periods=14, freq="B"))


def test_required_charts_are_created_from_supplied_columns(tmp_path: Path) -> None:
    dates = _dates()
    ma_raw = [0.0] * 6 + [1.0] * 8
    momentum_raw = [1.0] * 7 + [0.0] * 7
    daily = pd.DataFrame(
        {
            "Date": dates,
            "InCommonPeriod": [False] + [True] * 13,
            "BuyHold_NetNAV": [float("nan")] + [1.0 + i / 100 for i in range(13)],
            "MA20_60_NetNAV": [float("nan")] + [1.0 + i / 200 for i in range(13)],
            "TSMOM252_NetNAV": [float("nan")] + [1.0 + i / 150 for i in range(13)],
            "MA20_60_RawSignal": ma_raw,
            "MA20_60_ExecutedPosition": pd.Series(ma_raw).shift(1),
            "TSMOM252_RawSignal": momentum_raw,
            "TSMOM252_ExecutedPosition": pd.Series(momentum_raw).shift(1),
        }
    )
    drawdowns = pd.DataFrame(
        {
            "Date": dates,
            "BuyHold_NetDrawdown": [float("nan")] + [0.0] * 13,
            "MA20_60_NetDrawdown": [float("nan")] + [0.0] * 13,
            "TSMOM252_NetDrawdown": [float("nan")] + [0.0] * 13,
        }
    )
    indicators = pd.DataFrame(
        {
            "Date": dates,
            "Close": list(range(10, 24)),
            "MA20": list(range(9, 23)),
            "MA60": list(range(8, 22)),
        }
    )
    paths = [tmp_path / f"chart_{number}.png" for number in range(4)]
    primary_specs = [
        {"label": "Buy & Hold", "prefix": "BuyHold"},
        {"label": "MA20/60 Trend", "prefix": "MA20_60"},
        {"label": "Momentum252", "prefix": "TSMOM252"},
    ]

    plot_nav_comparison(daily, paths[0], 72, primary_specs)
    plot_drawdown_comparison(drawdowns, paths[1], 72, primary_specs)
    plot_price_and_mas(indicators, paths[2], 72, [20, 60])
    plot_signal_alignment(daily, paths[3], 72, primary_specs[1:])

    assert all(path.exists() and path.stat().st_size > 0 for path in paths)

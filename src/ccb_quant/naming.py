"""Config-derived strategy names and saved-column prefixes."""

from __future__ import annotations

from typing import Any


def configured_strategy_specs(indicators: dict[str, Any]) -> dict[str, Any]:
    ma_windows = sorted(int(value) for value in indicators["ma_windows"])
    if len(ma_windows) != 2:
        raise ValueError("exactly two MA windows are required")
    short_window, long_window = ma_windows
    lookbacks = [int(value) for value in indicators["momentum_lookbacks"]]
    primary_lookback = int(indicators["primary_momentum_lookback"])
    if primary_lookback not in lookbacks:
        raise ValueError("primary momentum lookback must be configured")
    ma_prefix = f"MA{short_window}_{long_window}"
    primary_momentum_prefix = f"TSMOM{primary_lookback}"
    return {
        "ma_windows": ma_windows,
        "momentum_lookbacks": lookbacks,
        "primary_momentum_lookback": primary_lookback,
        "primary": [
            {"label": "Buy & Hold", "prefix": "BuyHold", "lookback": None},
            {
                "label": f"MA{short_window}/{long_window} Trend",
                "prefix": ma_prefix,
                "lookback": None,
            },
            {
                "label": f"Momentum{primary_lookback}",
                "prefix": primary_momentum_prefix,
                "lookback": primary_lookback,
            },
        ],
        "robustness": [
            {"label": "Buy & Hold", "prefix": "BuyHold", "lookback": None},
            {
                "label": f"MA{short_window}/{long_window} Trend",
                "prefix": ma_prefix,
                "lookback": None,
            },
            *[
                {
                    "label": f"Momentum{lookback}",
                    "prefix": f"TSMOM{lookback}",
                    "lookback": lookback,
                }
                for lookback in lookbacks
            ],
        ],
    }


__all__ = ["configured_strategy_specs"]

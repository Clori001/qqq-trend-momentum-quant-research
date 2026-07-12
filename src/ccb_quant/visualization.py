"""Phase 6 plots built only from saved pipeline columns."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd

from ccb_quant.validation import parse_boolean_column


COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#9467bd"]


def _save(fig: plt.Figure, output_path: Path, dpi: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_nav_comparison(
    frame: pd.DataFrame, output_path: Path, dpi: int, primary_specs: list[dict]
) -> None:
    required = {"Date", "InCommonPeriod"} | {
        f'{spec["prefix"]}_NetNAV' for spec in primary_specs
    }
    if missing := required.difference(frame.columns):
        raise ValueError(f"missing saved NAV columns: {sorted(missing)}")
    common_mask = parse_boolean_column(
        frame["InCommonPeriod"], column_name="InCommonPeriod"
    )
    common = frame.loc[common_mask]
    fig, ax = plt.subplots(figsize=(11, 6))
    for color, spec in zip(COLORS, primary_specs, strict=False):
        column = f'{spec["prefix"]}_NetNAV'
        ax.plot(common["Date"], common[column], label=spec["label"], color=color)
    ax.set(title="Net NAV Comparison (Common Period)", xlabel="Date", ylabel="Net NAV")
    ax.legend(frameon=False)
    _save(fig, output_path, dpi)


def plot_drawdown_comparison(
    frame: pd.DataFrame, output_path: Path, dpi: int, primary_specs: list[dict]
) -> None:
    required = {"Date"} | {
        f'{spec["prefix"]}_NetDrawdown' for spec in primary_specs
    }
    if missing := required.difference(frame.columns):
        raise ValueError(f"missing saved drawdown columns: {sorted(missing)}")
    common = frame.dropna(subset=list(required - {"Date"}))
    fig, ax = plt.subplots(figsize=(11, 6))
    for color, spec in zip(COLORS, primary_specs, strict=False):
        column = f'{spec["prefix"]}_NetDrawdown'
        ax.plot(common["Date"], common[column], label=spec["label"], color=color)
    ax.axhline(0.0, color="#444444", linewidth=0.8)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.set(title="Net Drawdown Comparison (Common Period)", xlabel="Date", ylabel="Drawdown")
    ax.legend(frameon=False)
    _save(fig, output_path, dpi)


def plot_price_and_mas(
    frame: pd.DataFrame, output_path: Path, dpi: int, ma_windows: list[int]
) -> None:
    short_window, long_window = ma_windows
    required = {"Date", "Close", f"MA{short_window}", f"MA{long_window}"}
    if missing := required.difference(frame.columns):
        raise ValueError(f"missing saved price/MA columns: {sorted(missing)}")
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(frame["Date"], frame["Close"], label="QQQ Close", color="#202020", linewidth=1.1)
    ax.plot(frame["Date"], frame[f"MA{short_window}"], label=f"MA{short_window}", color="#1f77b4", linewidth=0.9)
    ax.plot(frame["Date"], frame[f"MA{long_window}"], label=f"MA{long_window}", color="#d62728", linewidth=0.9)
    ax.set(title=f"QQQ Close with Saved MA{short_window} and MA{long_window} (Full History)", xlabel="Date", ylabel="Price")
    ax.legend(frameon=False)
    _save(fig, output_path, dpi)


def plot_signal_alignment(
    frame: pd.DataFrame, output_path: Path, dpi: int, detail_specs: list[dict]
) -> None:
    pairs = [
        (
            spec["label"],
            f'{spec["prefix"]}_RawSignal',
            f'{spec["prefix"]}_ExecutedPosition',
        )
        for spec in detail_specs
    ]
    if len(pairs) != 2:
        raise ValueError("signal transition chart requires two configured strategies")
    required = {"Date"} | {column for _, raw, position in pairs for column in (raw, position)}
    if missing := required.difference(frame.columns):
        raise ValueError(f"missing saved signal/position columns: {sorted(missing)}")
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharey=True)
    for ax, (label, raw_column, position_column) in zip(axes, pairs, strict=True):
        valid = frame[["Date", raw_column, position_column]].dropna().reset_index(drop=True)
        transitions = valid.index[
            valid[raw_column].ne(valid[raw_column].shift(1))
            & valid[raw_column].shift(1).notna()
        ]
        if len(transitions) == 0:
            raise ValueError(f"{label} has no saved raw-signal transition")
        eligible = transitions[(transitions >= 5) & (transitions + 6 < len(valid))]
        transition = int(eligible[0] if len(eligible) else transitions[0])
        start = max(0, transition - 5)
        stop = min(len(valid), transition + 7)
        window = valid.iloc[start:stop].copy()
        window["ObservedRow"] = range(len(window))
        raw_change_row = transition - start
        executed_change_row = raw_change_row + 1

        ax.step(
            window["ObservedRow"],
            window[raw_column],
            where="post",
            marker="o",
            label="Saved raw signal",
            linewidth=1.6,
        )
        ax.step(
            window["ObservedRow"],
            window[position_column],
            where="post",
            marker="X",
            label="Saved position (recorded row t+1)",
            linewidth=1.4,
            linestyle="--",
        )
        ax.axvline(raw_change_row, color="#1f77b4", linestyle=":", linewidth=1.5)
        ax.axvline(executed_change_row, color="#ff7f0e", linestyle=":", linewidth=1.5)
        raw_date = window.iloc[raw_change_row]["Date"]
        executed_date = window.iloc[executed_change_row]["Date"]
        ax.text(
            raw_change_row - 0.15,
            1.08,
            f"Signal observed with close t\n{raw_date:%Y-%m-%d}",
            ha="right",
            va="bottom",
            color="#1f77b4",
        )
        ax.text(
            executed_change_row + 0.15,
            1.08,
            f"Position stored on row t+1\n{executed_date:%Y-%m-%d}",
            ha="left",
            va="bottom",
            color="#d95f02",
        )
        ax.set_ylabel(label)
        ax.set_yticks([0, 1])
        ax.set_ylim(-0.15, 1.35)
        ax.set_xticks(window["ObservedRow"])
        ax.set_xticklabels(
            window["Date"].dt.strftime("%m-%d"), rotation=45, ha="right"
        )
        ax.legend(loc="lower left", frameon=False, ncol=2)
    axes[0].set_title(
        "Signal observed using close t; position stored on row t+1; next close-to-close return attribution"
    )
    axes[-1].set_xlabel("Observed trading date (approximately five rows either side)")
    fig.tight_layout()
    _save(fig, output_path, dpi)


__all__ = [
    "plot_drawdown_comparison",
    "plot_nav_comparison",
    "plot_price_and_mas",
    "plot_signal_alignment",
]

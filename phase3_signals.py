"""Phase 3 entry point: generate raw signals only."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ccb_quant.signals import add_raw_signals  # noqa: E402


def _repository_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def build_raw_signal_report(
    frame: pd.DataFrame,
    *,
    ma_windows: list[int],
    momentum_lookbacks: list[int],
    primary_momentum_lookback: int,
    terminal_month_excluded: bool,
) -> str:
    """Document exact raw-signal rules and observed signal availability."""

    short_window, long_window = sorted(ma_windows)
    ma_column = f"MA{short_window}_{long_window}_RawSignal"
    lines = [
        "# 原始信号报告 / Raw Signal Report",
        "",
        "## 范围",
        "",
        "本阶段只生成raw signals。尚未应用shift、executed position、return、transaction cost、NAV、metric或chart。",
        "",
        "## 规则",
        "",
        "- `BuyHold_RawSignal = 1` on every observation.",
        (
            f"- `{ma_column} = 1` when `MA{short_window} > MA{long_window}`, "
            "otherwise 0; indicator warm-up remains NaN."
        ),
    ]
    for lookback in momentum_lookbacks:
        column = f"TSMOM{lookback}_RawSignal"
        flag_column = f"TSMOM{lookback}_DecisionFlag"
        first_valid = frame.loc[frame[column].notna(), "Date"].iloc[0]
        role = (
            "Primary"
            if lookback == primary_momentum_lookback
            else "Pre-declared robustness only"
        )
        lines.extend(
            [
                (
                    f"- `{column}`: on a valid completed month-end, 1 when "
                    f"`Momentum{lookback} > 0`, otherwise 0; then forward-hold "
                    "the raw decision until the next valid completed month-end."
                ),
                f"  - Role: {role}",
                f"  - First valid raw-signal date: {first_valid.strftime('%Y-%m-%d')}",
                f"  - Valid decision rows: {int(frame[flag_column].sum())}",
            ]
        )

    ma_first_valid = frame.loc[frame[ma_column].notna(), "Date"].iloc[0]
    lines.extend(
        [
            "",
            "## 验证摘要",
            "",
            f"- Rows preserved: {len(frame)}",
            f"- MA raw-signal first valid date: {ma_first_valid.strftime('%Y-%m-%d')}",
            f"- Terminal dataset month excluded as unconfirmed complete: {terminal_month_excluded}",
            "- Strict MA tie rule: ties are Cash (0)",
            "- Momentum zero rule: zero is Cash (0)",
            "- Warm-up backfill before first valid decision: not used",
            "- Executed positions or shift(1): not implemented",
            "- Returns, costs, NAV, metrics, and charts: not implemented",
            "- Phase 3 raw-signal status: PASS",
            "",
        ]
    )
    return "\n".join(lines)


def run_phase3(config_path: Path) -> pd.DataFrame:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    indicator_config = config["indicators"]
    signal_config = config["signals"]
    output_config = config["outputs"]

    input_path = _repository_path(output_config["indicator_file"])
    output_path = _repository_path(output_config["raw_signal_file"])
    report_path = _repository_path(output_config["raw_signal_report"])
    log_path = _repository_path(output_config["phase3_log_file"])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )

    frame = pd.read_csv(
        input_path,
        parse_dates=["Date"],
        float_precision="round_trip",
    )
    ma_windows = [int(value) for value in indicator_config["ma_windows"]]
    momentum_lookbacks = [
        int(value) for value in indicator_config["momentum_lookbacks"]
    ]
    primary_momentum_lookback = int(
        indicator_config["primary_momentum_lookback"]
    )
    exclude_terminal = bool(
        signal_config["exclude_terminal_month_without_next_observation"]
    )

    logging.info("Loading Phase 2 indicator data: %s", input_path)
    enriched = add_raw_signals(
        frame,
        ma_windows=ma_windows,
        momentum_lookbacks=momentum_lookbacks,
        exclude_terminal_month_without_next_observation=exclude_terminal,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    enriched.to_csv(output_path, index=False, date_format="%Y-%m-%d")
    report_path.write_text(
        build_raw_signal_report(
            enriched,
            ma_windows=ma_windows,
            momentum_lookbacks=momentum_lookbacks,
            primary_momentum_lookback=primary_momentum_lookback,
            terminal_month_excluded=exclude_terminal,
        ),
        encoding="utf-8",
    )
    logging.info("Phase 3 PASS: %s raw-signal rows", len(enriched))
    logging.info("Raw signal data: %s", output_path)
    logging.info("Raw signal report: %s", report_path)
    return enriched


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 3 raw signals only")
    parser.add_argument(
        "--config", type=Path, default=Path("config/config.yaml")
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = _repository_path(str(args.config))
    try:
        frame = run_phase3(config_path)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"Phase 3 failed: {exc}", file=sys.stderr)
        return 1
    print(f"Phase 3 raw signals complete: {len(frame)} rows. No execution or backtest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

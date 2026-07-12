from pathlib import Path
import json
import zipfile

import numpy as np
import pandas as pd
import pytest
import yaml

from ccb_quant.backtest import add_primary_backtests
from ccb_quant.naming import configured_strategy_specs
from phase5_metrics import run_phase5, validate_phase5_inputs
from scripts.build_submission_package import (
    PRIVATE_REPORT,
    PUBLIC_REPORT,
    audit_archive,
    build_packages,
    is_public_allowed,
)
from ccb_quant.report_context import load_report_context
from ccb_quant.validation import parse_boolean_column


def _absolute_outputs(root: Path) -> dict[str, str]:
    names = {
        "data_quality_json": "results/data_quality_report.json",
        "data_quality_markdown": "docs/data_quality_report.md",
        "phase1_log_file": "logs/phase1.log",
        "indicator_file": "data/processed/indicators.csv",
        "indicator_report": "docs/indicator.md",
        "phase2_log_file": "logs/phase2.log",
        "raw_signal_file": "data/processed/signals.csv",
        "raw_signal_report": "docs/signals.md",
        "phase3_log_file": "logs/phase3.log",
        "daily_backtest_file": "results/daily.csv",
        "backtest_report": "docs/backtest.md",
        "phase4_log_file": "logs/phase4.log",
        "performance_summary_file": "results/performance_summary.csv",
        "robustness_summary_file": "results/robustness_summary.csv",
        "drawdown_series_file": "results/drawdowns.csv",
        "metrics_report": "docs/metrics.md",
        "phase5_log_file": "logs/phase5.log",
        "nav_comparison_chart": "results/nav.png",
        "drawdown_comparison_chart": "results/drawdown.png",
        "price_ma_chart": "results/price.png",
        "signal_alignment_chart": "results/signals.png",
        "visualization_report": "docs/visualization.md",
        "phase6_log_file": "logs/phase6.log",
    }
    return {key: str(root / value) for key, value in names.items()}


def _write_config(root: Path, primary: int = 252) -> Path:
    dates = pd.bdate_range("2020-01-01", periods=520)
    config = {
        "data": {
            "raw_file": str(root / "data/raw/synthetic.csv"),
            "processed_file": str(root / "data/processed/clean.csv"),
            "header_row": 5,
            "delimiter": ",",
            "date_format": "%d/%m/%Y",
            "expected_start_date": str(dates[0].date()),
            "expected_end_date": str(dates[-1].date()),
            "outlier_review_threshold": 0.10,
        },
        "indicators": {
            "input_file": str(root / "data/processed/clean.csv"),
            "ma_windows": [20, 60],
            "momentum_lookbacks": [126, 252],
            "primary_momentum_lookback": primary,
        },
        "signals": {"exclude_terminal_month_without_next_observation": True},
        "backtest": {
            "common_period": "auto",
            "transaction_cost_bps": 5,
            "cost_sensitivity_bps": [0, 5, 10],
            "initial_position": 0,
        },
        "metrics": {"annual_trading_days": 252, "risk_free_annual_rate": 0.0},
        "visualization": {"dpi": 40, "style": "seaborn-v0_8-whitegrid"},
        "outputs": _absolute_outputs(root),
    }
    path = root / "config.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path


def _write_synthetic_bloomberg(root: Path) -> None:
    dates = pd.bdate_range("2020-01-01", periods=520)
    x = np.arange(len(dates))
    close = 100.0 * np.exp(0.00025 * x + 0.22 * np.sin(x / 55.0))
    rows = ["metadata"] * 5
    rows.append("Dates,PX_OPEN,PX_HIGH,PX_LOW,PX_LAST,PX_VOLUME")
    for date, value in zip(dates, close, strict=True):
        rows.append(
            f"{date:%d/%m/%Y},{value:.8f},{value*1.01:.8f},{value*0.99:.8f},{value:.8f},1000000"
        )
    path = root / "data/raw/synthetic.csv"
    path.parent.mkdir(parents=True)
    path.write_text("\n".join(rows), encoding="utf-8")


@pytest.mark.parametrize("primary_lookback", [252, 126])
def test_full_phase1_to_phase6_pipeline_in_temporary_folder(
    tmp_path: Path, primary_lookback: int
) -> None:
    from main import run_phase1
    from phase2_indicators import run_phase2
    from phase3_signals import run_phase3
    from phase4_backtest import run_phase4
    from phase6_visualizations import run_phase6

    _write_synthetic_bloomberg(tmp_path)
    config = _write_config(tmp_path, primary=primary_lookback)
    run_phase1(config)
    run_phase2(config)
    run_phase3(config)
    run_phase4(config)
    primary, robustness = run_phase5(config)
    charts = run_phase6(config)

    assert len(primary) == 3
    assert f"Momentum{primary_lookback}" in set(primary["Strategy"])
    assert (tmp_path / f"results/daily.csv").read_text(encoding="utf-8").find(
        f"TSMOM{primary_lookback}_ExecutedPosition"
    ) >= 0
    assert len(robustness) == 12
    assert all(path.exists() and path.stat().st_size > 0 for path in charts)


def test_primary_momentum_126_changes_names_and_fields_from_config() -> None:
    specs = configured_strategy_specs(
        {"ma_windows": [10, 30], "momentum_lookbacks": [126, 252], "primary_momentum_lookback": 126}
    )
    assert specs["primary"][1]["prefix"] == "MA10_30"
    assert specs["primary"][1]["label"] == "MA10/30 Trend"
    assert specs["primary"][2]["prefix"] == "TSMOM126"
    assert specs["primary"][2]["label"] == "Momentum126"


@pytest.mark.parametrize("column", ["Date", "Close"])
def test_phase5_cross_file_mismatch_fails_closed(column: str) -> None:
    dates = pd.date_range("2020-01-01", periods=4)
    daily = pd.DataFrame(
        {
            "Date": dates,
            "Close": [100.0, 101.0, 102.0, 103.0],
            "InCommonPeriod": [False, True, True, True],
            "BuyHold_ExecutedPosition": [np.nan, 1.0, 1.0, 1.0],
            "MA10_30_ExecutedPosition": [np.nan, 0.0, 1.0, 1.0],
            "TSMOM126_ExecutedPosition": [np.nan, 1.0, 1.0, 0.0],
        }
    )
    raw = daily[["Date", "Close"]].copy()
    raw["BuyHold_RawSignal"] = [1.0, 1.0, 1.0, 1.0]
    raw["MA10_30_RawSignal"] = [0.0, 1.0, 1.0, 1.0]
    raw["TSMOM126_RawSignal"] = [1.0, 1.0, 0.0, 0.0]
    raw.loc[2, column] = pd.Timestamp("2021-01-01") if column == "Date" else 999.0
    with pytest.raises(ValueError, match=column):
        validate_phase5_inputs(daily, raw, ["BuyHold", "MA10_30", "TSMOM126"])


def _minimal_package_root(root: Path) -> None:
    (root / "results").mkdir(parents=True)
    (root / "data/raw").mkdir(parents=True)
    (root / "data/processed").mkdir(parents=True)
    (root / "logs").mkdir()
    (root / "README.md").write_text("demo", encoding="utf-8")
    (root / "data/raw/QQQ_US_Equity_20160710_Bloomberg_Raw.csv").write_text("licensed", encoding="utf-8")
    (root / "data/processed/sample.csv").write_text("Date,Close\n2020-01-01,1", encoding="utf-8")
    (root / "results/daily_backtest_results.csv").write_text("Date,Close\n2020-01-01,1", encoding="utf-8")
    (root / "results/daily_drawdowns.csv").write_text("Date,DD\n2020-01-01,0", encoding="utf-8")
    (root / "results/performance_summary.csv").write_text(
        "Strategy,CommonStart,CommonEnd,Observations\nA,2020-01-02,2020-01-10,7\nB,2020-01-02,2020-01-10,7\nC,2020-01-02,2020-01-10,7\n",
        encoding="utf-8",
    )
    (root / "logs/run.log").write_text("private", encoding="utf-8")
    (root / "output/pdf").mkdir(parents=True)
    (root / "output/pdf/QQQ_趋势跟踪与时间序列动量策略研究_PRIVATE_REVIEWER.pdf").write_bytes(b"%PDF-1.4 synthetic private report")
    (root / "output/pdf/QQQ_趋势跟踪与时间序列动量策略研究_Caro.pdf").write_bytes(b"%PDF-1.4 synthetic public report")


def test_manifests_zip_audit_and_variant_file_rules(tmp_path: Path) -> None:
    _minimal_package_root(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "results/daily_returns_backup.csv").write_text(
        "Date,Return\n2020-01-01,0.1", encoding="utf-8"
    )
    (tmp_path / "docs/debug_price_dump.csv").write_text(
        "Date,Close\n2020-01-01,100", encoding="utf-8"
    )
    (tmp_path / "unapproved.csv").write_text("secret", encoding="utf-8")
    result = build_packages(
        tmp_path, run_tests=False, allow_missing_frozen_snapshot=True
    )
    assert result["common_period"] == {"start": "2020-01-02", "end": "2020-01-10", "observations": 7}
    assert result["private"]["status"] == "PASS"
    assert result["public"]["status"] == "PASS"
    assert result["private"]["payload_files_verified"] > result["public"]["payload_files_verified"]
    audit = json.loads((tmp_path / "submission/package_audit.json").read_text(encoding="utf-8"))
    assert audit["private"]["zip_sha256"]
    assert audit["public"]["zip_sha256"]
    with zipfile.ZipFile(tmp_path / "submission/private_submission.zip") as archive:
        private_names = set(archive.namelist())
    with zipfile.ZipFile(tmp_path / "submission/public_demo.zip") as archive:
        public_names = set(archive.namelist())
    assert "data/raw/QQQ_US_Equity_20160710_Bloomberg_Raw.csv" in private_names
    assert "CONFIDENTIAL_DATA_NOTICE.txt" in private_names
    assert PRIVATE_REPORT in private_names
    assert "DATA_NOT_INCLUDED.md" in public_names
    assert PUBLIC_REPORT in public_names
    assert not any(name.startswith(("data/raw/", "data/processed/", "logs/")) for name in public_names)
    assert "results/daily_backtest_results.csv" not in public_names
    assert "results/daily_returns_backup.csv" not in public_names
    assert "docs/debug_price_dump.csv" not in public_names
    assert "unapproved.csv" not in public_names
    with zipfile.ZipFile(tmp_path / "submission/public_demo.zip") as archive:
        public_text = "\n".join(
            archive.read(name).decode("utf-8", errors="ignore")
            for name in archive.namelist()
            if name.endswith((".py", ".md", ".txt", ".yaml", ".yml", ".json"))
        )
    assert "PRIVATE_REVIEWER" not in public_text


def test_production_packaging_requires_frozen_snapshot(tmp_path: Path) -> None:
    _minimal_package_root(tmp_path)
    with pytest.raises(RuntimeError, match="valid frozen baseline audit"):
        build_packages(tmp_path, run_tests=False)


def test_public_allowlist_excludes_unapproved_csv_paths() -> None:
    assert not is_public_allowed("results/daily_returns_backup.csv")
    assert not is_public_allowed("results/price_export.csv")
    assert not is_public_allowed("docs/debug_price_dump.csv")
    assert not is_public_allowed("tmp_prices_final.csv")
    assert is_public_allowed("results/performance_summary.csv")


def test_archive_audit_rejects_unlisted_extra_member(tmp_path: Path) -> None:
    _minimal_package_root(tmp_path)
    build_packages(tmp_path, run_tests=False, allow_missing_frozen_snapshot=True)
    archive_path = tmp_path / "submission/public_demo.zip"
    with zipfile.ZipFile(archive_path, "a") as archive:
        archive.writestr("unlisted.txt", "not in manifest")
    with pytest.raises(ValueError, match="archive membership mismatch"):
        audit_archive(archive_path, "public")


def test_archive_audit_rejects_duplicate_member_name(tmp_path: Path) -> None:
    _minimal_package_root(tmp_path)
    build_packages(tmp_path, run_tests=False, allow_missing_frozen_snapshot=True)
    archive_path = tmp_path / "submission/public_demo.zip"
    with pytest.warns(UserWarning, match="Duplicate name"):
        with zipfile.ZipFile(archive_path, "a") as archive:
            archive.writestr("README.md", "duplicate")
    with pytest.raises(ValueError, match="duplicate member names"):
        audit_archive(archive_path, "public")


def test_phase5_rejects_saved_position_not_equal_to_shift() -> None:
    dates = pd.date_range("2020-01-01", periods=4)
    raw = pd.DataFrame(
        {
            "Date": dates,
            "Close": [100.0, 101.0, 102.0, 103.0],
            "BuyHold_RawSignal": [1.0, 1.0, 1.0, 1.0],
        }
    )
    daily = pd.DataFrame(
        {
            "Date": dates,
            "Close": raw["Close"],
            "InCommonPeriod": [False, True, True, True],
            "BuyHold_ExecutedPosition": [np.nan, 0.0, 1.0, 1.0],
        }
    )
    with pytest.raises(ValueError, match="does not equal raw signal shift"):
        validate_phase5_inputs(daily, raw, ["BuyHold"])


def test_strict_boolean_parser_does_not_treat_false_string_as_true() -> None:
    parsed = parse_boolean_column(
        pd.Series(["False", "TRUE", " false "]),
        column_name="InCommonPeriod",
    )
    assert parsed.tolist() == [False, True, False]
    with pytest.raises(ValueError, match="only true/false"):
        parse_boolean_column(
            pd.Series(["False", "0"]), column_name="InCommonPeriod"
        )


def test_report_values_are_derived_from_config_and_summary(tmp_path: Path) -> None:
    (tmp_path / "config").mkdir()
    (tmp_path / "results").mkdir()
    (tmp_path / "config/config.yaml").write_text(
        yaml.safe_dump(
            {
                "indicators": {
                    "ma_windows": [10, 30],
                    "momentum_lookbacks": [126, 252],
                    "primary_momentum_lookback": 126,
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "results/performance_summary.csv").write_text(
        "Strategy,CommonStart,CommonEnd,Observations\n"
        "Buy & Hold,2020-02-03,2020-12-31,230\n"
        "MA10/30 Trend,2020-02-03,2020-12-31,230\n"
        "Momentum126,2020-02-03,2020-12-31,230\n",
        encoding="utf-8",
    )
    context = load_report_context(tmp_path)
    assert context["strategy_config"]["primary"][1]["label"] == "MA10/30 Trend"
    assert context["strategy_config"]["primary"][2]["label"] == "Momentum126"
    assert context["period"] == {
        "CommonStart": "2020-02-03",
        "CommonEnd": "2020-12-31",
        "Observations": 230,
    }

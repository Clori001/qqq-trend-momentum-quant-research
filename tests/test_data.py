from pathlib import Path

import pandas as pd
import pytest

from ccb_quant.data import DataValidationError, load_and_validate_bloomberg_csv


def _write_bloomberg_csv(path: Path, data_rows: list[str]) -> None:
    preamble = [
        "????,01/01/2020,,,,",
        "????,31/12/2020,,,,",
        ",,,,,",
        ",QQQ US Equity,,,,",
        ",#N/A Requesting Data...,#N/A Requesting Data...,#N/A Requesting Data...,#N/A Requesting Data...,",
        "Dates,PX_OPEN,PX_HIGH,PX_LOW,PX_LAST,PX_VOLUME",
    ]
    path.write_text("\n".join(preamble + data_rows) + "\n", encoding="ascii")


def test_loader_skips_metadata_maps_columns_and_parses_dates(tmp_path: Path) -> None:
    source = tmp_path / "sample.csv"
    _write_bloomberg_csv(
        source,
        [
            "02/01/2020,100,102,99,101,1000",
            "03/01/2020,101,103,100,102,1100",
        ],
    )

    frame, report = load_and_validate_bloomberg_csv(source)

    assert list(frame.columns) == ["Date", "Open", "High", "Low", "Close", "Volume"]
    assert frame["Date"].tolist() == [pd.Timestamp("2020-01-02"), pd.Timestamp("2020-01-03")]
    assert report["source"]["metadata_rows_skipped"] == 5
    assert report["status"] == "PASS"


def test_exact_duplicate_is_logged_and_removed(tmp_path: Path) -> None:
    source = tmp_path / "duplicate.csv"
    row = "02/01/2020,100,102,99,101,1000"
    _write_bloomberg_csv(source, [row, row])

    frame, report = load_and_validate_bloomberg_csv(source)

    assert len(frame) == 1
    assert report["rows"]["exact_duplicate_rows_found"] == 2
    assert report["rows"]["exact_duplicate_rows_removed"] == 1


def test_expected_chronological_range_is_validated(tmp_path: Path) -> None:
    source = tmp_path / "range.csv"
    _write_bloomberg_csv(
        source,
        [
            "02/01/2020,100,102,99,101,1000",
            "03/01/2020,101,103,100,102,1100",
        ],
    )

    frame, report = load_and_validate_bloomberg_csv(
        source,
        expected_start_date="2020-01-02",
        expected_end_date="2020-01-03",
    )

    assert len(frame) == 2
    assert report["source"]["source_date_convention"] == "DD/MM/YYYY"
    assert report["dates"]["matches_expected_chronological_range"] is True

    with pytest.raises(DataValidationError, match="does not match expected start"):
        load_and_validate_bloomberg_csv(
            source,
            expected_start_date="2020-01-01",
            expected_end_date="2020-01-03",
        )


def test_conflicting_duplicate_date_blocks_processing(tmp_path: Path) -> None:
    source = tmp_path / "conflict.csv"
    _write_bloomberg_csv(
        source,
        [
            "02/01/2020,100,102,99,101,1000",
            "02/01/2020,100,103,99,102,1100",
        ],
    )

    with pytest.raises(DataValidationError, match="Conflicting duplicate dates"):
        load_and_validate_bloomberg_csv(source)


def test_impossible_ohlc_blocks_processing(tmp_path: Path) -> None:
    source = tmp_path / "bad_ohlc.csv"
    _write_bloomberg_csv(source, ["02/01/2020,100,99,98,101,1000"])

    with pytest.raises(DataValidationError, match="OHLC relationship"):
        load_and_validate_bloomberg_csv(source)


def test_large_return_is_flagged_but_retained(tmp_path: Path) -> None:
    source = tmp_path / "large_return.csv"
    _write_bloomberg_csv(
        source,
        [
            "02/01/2020,99,101,98,100,1000",
            "03/01/2020,114,116,113,115,1200",
        ],
    )

    frame, report = load_and_validate_bloomberg_csv(
        source, outlier_review_threshold=0.10
    )

    assert len(frame) == 2
    assert report["outlier_review"]["flag_count"] == 1
    assert report["outlier_review"]["rows"][0]["action"] == "retained_review_only"

"""Shared strict parsers for saved pipeline outputs."""

from __future__ import annotations

import pandas as pd
from pandas.api.types import is_bool_dtype


def parse_boolean_column(series: pd.Series, *, column_name: str) -> pd.Series:
    """Accept Boolean dtype or literal true/false strings, and reject all else."""

    if not isinstance(series, pd.Series):
        raise TypeError(f"{column_name} must be a pandas Series")
    if is_bool_dtype(series.dtype):
        return series.astype(bool)
    normalized = series.astype(str).str.strip().str.lower()
    if not normalized.isin({"true", "false"}).all():
        raise ValueError(f"{column_name} must contain only true/false")
    return normalized.map({"true": True, "false": False}).astype(bool)


__all__ = ["parse_boolean_column"]

"""Dynamic report metadata shared by the future LaTeX reporting workflow."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

from ccb_quant.naming import configured_strategy_specs


def load_report_context(root: Path) -> dict[str, object]:
    """Read strategy names, common-period metadata, and audited test status."""

    config = yaml.safe_load((root / "config/config.yaml").read_text(encoding="utf-8"))
    strategy_config = configured_strategy_specs(config["indicators"])
    primary = pd.read_csv(
        root / "results/performance_summary.csv", float_precision="round_trip"
    )
    period = primary[["CommonStart", "CommonEnd", "Observations"]].drop_duplicates()
    if len(period) != 1:
        raise ValueError("report requires one shared primary comparison period")
    audit_path = root / "submission/package_audit.json"
    test_summary = "See docs/test_evidence.md"
    if audit_path.exists():
        test_summary = json.loads(audit_path.read_text(encoding="utf-8"))[
            "test_result"
        ]["summary"]
    return {
        "strategy_config": strategy_config,
        "primary": primary,
        "period": period.iloc[0].to_dict(),
        "test_summary": test_summary,
    }


__all__ = ["load_report_context"]

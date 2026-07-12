"""Build independently audited private and public submission archives."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_NOTICE = "CONFIDENTIAL — LICENSED BLOOMBERG DATA — NOT FOR PUBLIC DISTRIBUTION"
PUBLIC_DATA_NOTE = (
    "# Data Not Included\n\n"
    "Due to data licensing restrictions, the authorized Bloomberg input is not included. "
    "Full reproduction requires the reviewer to provide a properly licensed CSV matching "
    "the documented schema.\n\n"
    "This public package cannot reproduce the frozen empirical results without that authorized input.\n"
)
BASE_EXCLUDES = {
    "external",
    "tmp",
    "submission",
    "output",
    "research_report_latex",
    ".git",
    ".pytest_cache",
}
PUBLIC_ALLOWED_ROOT_FILES = {
    "README.md",
    "environment.yml",
    "main.py",
    "phase2_indicators.py",
    "phase3_signals.py",
    "phase4_backtest.py",
    "phase5_metrics.py",
    "phase6_visualizations.py",
    "scripts/build_submission_package.py",
}
PUBLIC_ALLOWED_DOCS = {
    "docs/ai_work_log.md",
    "docs/backtest_engine_report.md",
    "docs/code_source_statement.md",
    "docs/data_quality_report.md",
    "docs/debugging_guide.md",
    "docs/decision_log.md",
    "docs/dependency_inventory.md",
    "docs/fresh_folder_smoke_test.md",
    "docs/indicator_report.md",
    "docs/methodology_report.md",
    "docs/metrics_robustness_report.md",
    "docs/pytest_output.txt",
    "docs/raw_signal_report.md",
    "docs/reproducibility.md",
    "docs/test_evidence.md",
    "docs/visualization_report.md",
}
PUBLIC_ALLOWED_RESULTS = {
    "results/performance_summary.csv",
    "results/robustness_summary.csv",
    "results/net_nav_comparison.png",
    "results/net_drawdown_comparison.png",
    "results/raw_signal_executed_position.png",
}
PUBLIC_ALLOWED_TEST_FIXTURES = {"tests/fixtures/synthetic_prices.csv"}
PRIVATE_REPORT = "reports/QQQ_趋势跟踪与时间序列动量策略研究_PRIVATE_REVIEWER.pdf"
PUBLIC_REPORT = "reports/QQQ_趋势跟踪与时间序列动量策略研究_Caro.pdf"
REPORT_SOURCES = {
    "private": "output/pdf/QQQ_趋势跟踪与时间序列动量策略研究_PRIVATE_REVIEWER.pdf",
    "public": "output/pdf/QQQ_趋势跟踪与时间序列动量策略研究_Caro.pdf",
}
PRIVATE_REQUIRED_FILES = {
    "data/raw/QQQ_US_Equity_20160710_Bloomberg_Raw.csv",
    "results/daily_backtest_results.csv",
    "results/daily_drawdowns.csv",
    PRIVATE_REPORT,
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def run_project_tests(root: Path) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    output = "\n".join(part for part in [completed.stdout, completed.stderr] if part).strip()
    if completed.returncode != 0:
        raise RuntimeError(f"pytest failed; packaging stopped\n{output}")
    summary = next((line for line in reversed(output.splitlines()) if "passed" in line), output)
    return {"command": "python -m pytest -q", "returncode": 0, "summary": summary}


def derive_common_period(root: Path) -> dict[str, object]:
    summary = pd.read_csv(root / "results/performance_summary.csv")
    columns = ["CommonStart", "CommonEnd", "Observations"]
    unique = summary[columns].drop_duplicates()
    if len(summary) != 3 or len(unique) != 1:
        raise ValueError("primary strategies do not share one common-period metadata row")
    row = unique.iloc[0]
    return {
        "start": str(row["CommonStart"]),
        "end": str(row["CommonEnd"]),
        "observations": int(row["Observations"]),
    }


def verify_frozen_numeric_outputs(root: Path) -> dict[str, object]:
    snapshot_path = root / "results/phase1_6_frozen_hashes_pre_repair.json"
    if not snapshot_path.exists():
        return {"status": "NOT_AVAILABLE", "unchanged": False, "checked_files": 0}
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    allowed_visual_change = "results/raw_signal_executed_position.png"
    mismatches = []
    checked = 0
    for relative, expected in snapshot.items():
        if relative == allowed_visual_change:
            continue
        path = root / relative
        checked += 1
        actual = sha256_file(path) if path.exists() else None
        if actual != expected:
            mismatches.append({"path": relative, "expected": expected, "actual": actual})
    return {
        "status": "PASS" if not mismatches else "FAIL",
        "unchanged": not mismatches,
        "checked_files": checked,
        "approved_visual_text_change_excluded": allowed_visual_change,
        "mismatches": mismatches,
    }


def is_public_allowed(relative: str) -> bool:
    """Return True only for explicitly approved public-demo payloads."""

    if relative in PUBLIC_ALLOWED_ROOT_FILES | PUBLIC_ALLOWED_DOCS | PUBLIC_ALLOWED_RESULTS | {PUBLIC_REPORT}:
        return True
    if relative.startswith("config/") and relative.endswith((".yaml", ".yml")):
        return True
    if relative.startswith("src/") and relative.endswith(".py"):
        return True
    if relative.startswith("tests/") and relative.endswith(".py"):
        return True
    return relative in PUBLIC_ALLOWED_TEST_FIXTURES


def _source_files(root: Path, variant: str) -> list[Path]:
    files = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        rel = relative.as_posix()
        if relative.parts[0] in BASE_EXCLUDES or "__pycache__" in relative.parts:
            continue
        if rel in {"results/run_manifest.json", "results/private_manifest.json", "results/public_manifest.json"}:
            continue
        if rel == "scripts/build_project_report.py":
            continue
        if variant == "public" and not is_public_allowed(rel):
            continue
        files.append(path)
    return sorted(files, key=lambda value: value.relative_to(root).as_posix())


def _copy_variant(root: Path, stage: Path, variant: str) -> None:
    for source in _source_files(root, variant):
        relative = source.relative_to(root)
        target = stage / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    report_relative = PRIVATE_REPORT if variant == "private" else PUBLIC_REPORT
    report_source = root / REPORT_SOURCES[variant]
    if not report_source.is_file():
        raise FileNotFoundError(f"accepted final report missing: {report_source}")
    report_target = stage / report_relative
    report_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(report_source, report_target)
    readme = stage / "README.md"
    original = readme.read_text(encoding="utf-8")
    if variant == "private":
        readme.write_text(f"# {PRIVATE_NOTICE}\n\n{original}", encoding="utf-8")
        (stage / "CONFIDENTIAL_DATA_NOTICE.txt").write_text(
            PRIVATE_NOTICE
            + "\nFor private review by specifically authorized CCB reviewers only.\n"
            + "Do not upload to public GitHub, public cloud drives, or public demo pages.\n",
            encoding="utf-8",
        )
    else:
        readme.write_text(
            "# PUBLIC DEMO — BLOOMBERG DATA NOT INCLUDED\n\n" + original,
            encoding="utf-8",
        )
        (stage / "DATA_NOT_INCLUDED.md").write_text(PUBLIC_DATA_NOTE, encoding="utf-8")
        # Keep the public source/test bundle usable while removing the private
        # reviewer's real-name filename from human-readable packaged files.
        for path in stage.rglob("*"):
            if path.is_file() and path.suffix.lower() == ".py":
                text = path.read_text(encoding="utf-8")
                if "PRIVATE_REVIEWER" in text:
                    path.write_text(text.replace("PRIVATE_REVIEWER", "PRIVATE_REVIEWER"), encoding="utf-8")


def _payload_records(stage: Path, manifest_relative: str) -> list[dict[str, object]]:
    records = []
    for path in sorted(stage.rglob("*")):
        if not path.is_file() or path.relative_to(stage).as_posix() == manifest_relative:
            continue
        records.append(
            {
                "path": path.relative_to(stage).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return records


def _write_manifest(
    stage: Path,
    variant: str,
    test_result: dict[str, object],
    common_period: dict[str, object],
    frozen_audit: dict[str, object],
) -> Path:
    relative = f"results/{variant}_manifest.json"
    path = stage / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "project": "ccb_quant",
        "variant": variant,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "common_period": common_period,
        "test_result": test_result,
        "phase_1_to_6_frozen_audit": frozen_audit,
        "bloomberg_distribution": (
            "private authorized reviewers only" if variant == "private" else "not included"
        ),
        "report_status": "accepted final PDF included",
        "manifest_self_hash_note": (
            "This manifest is excluded from its own circular payload hash list; "
            "the complete archive is covered by the separately reported ZIP SHA-256."
        ),
        "payload_files": _payload_records(stage, relative),
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _zip_stage(stage: Path, archive_path: Path) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(stage).as_posix())


def audit_archive(
    archive_path: Path, variant: str, *, run_extracted_tests: bool = False
) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix=f"ccb_{variant}_audit_") as temp:
        extracted = Path(temp)
        with zipfile.ZipFile(archive_path) as archive:
            members = archive.namelist()
            if len(members) != len(set(members)):
                raise ValueError("archive contains duplicate member names")
            archive.extractall(extracted)
        manifest_relative = f"results/{variant}_manifest.json"
        manifest_path = extracted / manifest_relative
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        payload_names = {record["path"] for record in manifest["payload_files"]}
        expected_names = payload_names | {manifest_relative}
        names = set(members)
        if names != expected_names:
            missing = expected_names - names
            unlisted = names - expected_names
            raise ValueError(
                "archive membership mismatch; "
                f"missing={sorted(missing)}, unlisted={sorted(unlisted)}"
            )
        for record in manifest["payload_files"]:
            path = extracted / record["path"]
            if not path.is_file():
                raise ValueError(f"archive missing payload: {record['path']}")
            if path.stat().st_size != record["bytes"] or sha256_file(path) != record["sha256"]:
                raise ValueError(f"archive payload audit failed: {record['path']}")
        if variant == "public":
            generated_public = {"DATA_NOT_INCLUDED.md", manifest_relative}
            unapproved = {
                name for name in names
                if name not in generated_public and not is_public_allowed(name)
            }
            if unapproved:
                raise ValueError(
                    f"public archive contains non-allowlisted files: {sorted(unapproved)}"
                )
            if "DATA_NOT_INCLUDED.md" not in names:
                raise ValueError("public archive is missing DATA_NOT_INCLUDED.md")
            if PUBLIC_REPORT not in names:
                raise ValueError("public archive is missing the accepted Caro report")
        else:
            missing = PRIVATE_REQUIRED_FILES.difference(names)
            if missing:
                raise ValueError(f"private archive is missing required files: {sorted(missing)}")
        extracted_test = None
        if run_extracted_tests:
            extracted_test = run_project_tests(extracted)
        return {
            "variant": variant,
            "payload_files_verified": len(manifest["payload_files"]),
            "manifest_self_excluded": True,
            "archive_files": len(names),
            "duplicate_member_check": "PASS",
            "exact_membership_check": "PASS",
            "public_allowlist_check": "PASS" if variant == "public" else "NOT_APPLICABLE",
            "zip_bytes": archive_path.stat().st_size,
            "zip_sha256": sha256_file(archive_path),
            "status": "PASS",
            "extracted_test_result": extracted_test,
        }


def build_packages(
    root: Path = ROOT,
    *,
    run_tests: bool = True,
    allow_missing_frozen_snapshot: bool = False,
) -> dict[str, object]:
    root = root.resolve()
    test_result = run_project_tests(root) if run_tests else {"summary": "test execution skipped by caller"}
    common_period = derive_common_period(root)
    frozen_audit = verify_frozen_numeric_outputs(root)
    if frozen_audit["status"] != "PASS":
        missing_allowed = (
            frozen_audit["status"] == "NOT_AVAILABLE"
            and allow_missing_frozen_snapshot
        )
        if not missing_allowed:
            raise RuntimeError(
                "production packaging requires a valid frozen baseline audit; "
                f"status={frozen_audit['status']}"
            )
    submission = root / "submission"
    results: dict[str, object] = {
        "common_period": common_period,
        "test_result": test_result,
        "frozen_audit": frozen_audit,
    }
    for variant in ["private", "public"]:
        with tempfile.TemporaryDirectory(prefix=f"ccb_{variant}_stage_") as temp:
            stage = Path(temp)
            _copy_variant(root, stage, variant)
            _write_manifest(stage, variant, test_result, common_period, frozen_audit)
            archive = submission / f"{variant}_submission.zip" if variant == "private" else submission / "public_demo.zip"
            _zip_stage(stage, archive)
        results[variant] = audit_archive(
            archive, variant, run_extracted_tests=run_tests
        )
        manifest_member = f"results/{variant}_manifest.json"
        with zipfile.ZipFile(archive) as built_archive:
            (submission / f"{variant}_manifest.json").write_bytes(
                built_archive.read(manifest_member)
            )
    audit_path = submission / "package_audit.json"
    audit_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


if __name__ == "__main__":
    print(json.dumps(build_packages(), ensure_ascii=False, indent=2))

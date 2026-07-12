# Fresh-Folder Smoke Test

- Date: 2026-07-12
- Platform: native Windows
- Environment: `D:\anaconda3\envs\ccb_quant\python.exe`
- Source: project files copied to a new workspace-local folder, excluding internal specifications and caches
- Working directory: `tmp/smoke_project` (QA-only, not submitted)
- Command: `python -m pytest -q`
- Superseded baseline result: `42 passed in 1.63s`
- Current engineering-repair archive tests are recorded in `docs/test_evidence.md` and `submission/package_audit.json`.

The smoke test used repository-relative paths and the copied offline data/results. It did not rerun Phase 1-6 generation scripts or alter the frozen submission artifacts.

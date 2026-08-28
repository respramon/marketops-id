"""Static contracts for the production scheduler's fail-closed evidence flow."""

from __future__ import annotations

from marketops.config import REPO_ROOT


def _workflow() -> str:
    return (REPO_ROOT / ".github" / "workflows" / "marketops.yml").read_text(encoding="utf-8")


def test_artifact_upload_requires_a_completed_safety_scan() -> None:
    workflow = _workflow()
    upload = workflow.split("- name: Upload run evidence", maxsplit=1)[1]
    upload = upload.split("- name: Enforce artifact safety", maxsplit=1)[0]
    assert "steps.artifact_scan.outcome == 'success'" in upload
    assert "steps.artifact_scan.outputs.scan_complete == 'true'" in upload


def test_secret_findings_are_enforced_only_after_safe_upload() -> None:
    workflow = _workflow()
    assert workflow.index("- name: Upload run evidence") < workflow.index(
        "- name: Enforce artifact safety"
    )
    enforcement = workflow.split("- name: Enforce artifact safety", maxsplit=1)[1]
    assert '"${SECRET_FINDINGS:-0}" != "0"' in enforcement
    assert "rotate it and inspect the run" in enforcement


def test_sqlite_state_is_detection_scanned_before_cache_save() -> None:
    workflow = _workflow()
    scan_position = workflow.index("- name: Scan persistent state for secrets")
    save_position = workflow.index("- name: Save persistent deduplication state")
    assert scan_position < save_position
    state_scan = workflow[scan_position:save_position]
    assert "--detect-only" in state_scan
    assert "--fail-if-found" in state_scan


def test_weekday_schedule_remains_0717_wib() -> None:
    assert 'cron: "17 0 * * 1-5"' in _workflow()

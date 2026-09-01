#!/usr/bin/env python3
"""Capture verified evidence for genuine `schedule`-triggered Actions runs.

Track 2 requires three GitHub Actions executions whose triggering event is
exactly ``schedule``.  Transcribing those counters by hand (or by asking a
model to read them) risks a wrong number reaching submission evidence, so this
script copies every value straight from the run's own uploaded artifact and
refuses to write anything it could not verify.

Two independent controls run before any value is recorded:

* the artifact tree is scanned with ``marketops.security.scan_secret_tree``;
* the same tree is scanned again with a regex defined here, so a defect in the
  shared scanner cannot silently pass a contaminated artifact.

The script is idempotent.  It only replaces ``[BLOCKED: ...]`` placeholders,
never an already-recorded value, and it leaves the screenshot row alone because
a human still has to capture that image.

Usage:
    uv run python scripts/capture_schedule_evidence.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO = "respramon/marketops-id"
WORKFLOW = "marketops.yml"
EVIDENCE_PATH = Path("evidence/unattended-runs.md")
SLOT_COUNT = 3

# Independent of marketops.security on purpose: two separate implementations
# must both agree an artifact is clean before it becomes submission evidence.
WEBHOOK_PATTERN = re.compile(
    rb"https://(?:canary\.|ptb\.)?discord(?:app)?\.com/"
    rb"api(?:/v\d+)?/webhooks/[0-9]+/[^\s\"'<>]+",
    re.IGNORECASE,
)

PLACEHOLDER = re.compile(r"`\[BLOCKED:[^\]]*\]`")

# Row label -> key in the artifact-derived value mapping.
ROW_FIELDS = {
    "Run ID": "run_id",
    "Trigger type": "trigger",
    "Started time": "started_at",
    "Finished time": "finished_at",
    "Mode": "mode",
    "Status": "status",
    "Events detected": "events_detected",
    "New events": "new_events",
    "Duplicate events suppressed": "duplicate_events_suppressed",
    "Notifications sent": "notifications_sent",
    "Estimated API credits": "estimated_api_credits",
    "Artifact name": "artifact_name",
    "Workflow run URL": "run_url",
}
# A human still has to capture this; never auto-fill it.
SKIP_ROWS = {"Screenshot"}


class VerificationError(RuntimeError):
    """Raised when a run cannot be recorded truthfully."""


def _gh() -> str:
    path = shutil.which("gh")
    if path is None:
        raise VerificationError("the GitHub CLI (gh) is not on PATH")
    return path


def _run_gh(args: list[str]) -> str:
    """Invoke the GitHub CLI with a fixed argument list (never a shell string)."""
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, no user input
        [_gh(), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise VerificationError(f"gh {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def list_schedule_runs() -> list[dict[str, Any]]:
    """Return completed `schedule` runs, oldest first."""
    raw = _run_gh(
        [
            "run",
            "list",
            "--workflow",
            WORKFLOW,
            "--event",
            "schedule",
            "--limit",
            "50",
            "--json",
            "databaseId,event,status,conclusion,createdAt,updatedAt,url",
        ]
    )
    runs = [run for run in json.loads(raw) if run.get("status") == "completed"]
    # Defence in depth: --event should already filter, but never trust it.
    runs = [run for run in runs if run.get("event") == "schedule"]
    runs.sort(key=lambda run: str(run.get("createdAt", "")))
    return runs


def artifact_name(run_id: int) -> str:
    raw = _run_gh(["api", f"repos/{REPO}/actions/runs/{run_id}/artifacts"])
    artifacts = json.loads(raw).get("artifacts", [])
    if not artifacts:
        raise VerificationError(f"run {run_id} uploaded no artifact")
    return str(artifacts[0]["name"])


def download_artifact(run_id: int, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    _run_gh(["run", "download", str(run_id), "--dir", str(destination)])
    if not any(destination.rglob("*")):
        raise VerificationError(f"run {run_id} artifact download produced no files")


def scan_artifact(root: Path) -> None:
    """Fail unless both independent scanners agree the tree is credential-free."""
    from marketops.security import scan_secret_tree

    shared_findings, _ = scan_secret_tree(root)
    local_findings = sum(
        len(WEBHOOK_PATTERN.findall(path.read_bytes()))
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    )
    if shared_findings or local_findings:
        raise VerificationError(
            f"SECURITY REGRESSION in {root.name}: "
            f"shared scanner={shared_findings}, independent scanner={local_findings}. "
            "Nothing was recorded. Rotate the webhook and inspect the run."
        )


def _report_json(root: Path) -> dict[str, Any]:
    candidates = sorted(root.rglob("latest.json"))
    if not candidates:
        raise VerificationError(f"no latest.json inside {root}")
    with candidates[0].open(encoding="utf-8") as handle:
        data: dict[str, Any] = json.load(handle)
    return data


def collect(run: dict[str, Any], workdir: Path) -> dict[str, str]:
    """Download, verify, and transcribe one run's evidence values."""
    run_id = int(run["databaseId"])
    destination = workdir / f"run-{run_id}"
    download_artifact(run_id, destination)
    scan_artifact(destination)
    report = _report_json(destination)

    trigger = str(report.get("trigger", ""))
    mode = str(report.get("mode", ""))
    if trigger != "schedule":
        raise VerificationError(
            f"run {run_id} artifact reports trigger={trigger!r}, not 'schedule'"
        )
    if mode != "live":
        raise VerificationError(f"run {run_id} artifact reports mode={mode!r}, not 'live'")

    name = artifact_name(run_id)
    credits = f"{report['estimated_api_credits']}/{report['credit_budget']}"
    return {
        "run_id": f"`{run_id}`",
        "trigger": f"`{trigger}` (confirmed by GitHub event and run artifact)",
        "started_at": f"`{report['started_at']}`",
        "finished_at": f"`{report['finished_at']}`",
        "mode": f"`{mode}`",
        "status": f"`{report['status']}`",
        "events_detected": str(report["events_detected"]),
        "new_events": str(report["new_events"]),
        "duplicate_events_suppressed": str(report["duplicate_events_suppressed"]),
        "notifications_sent": str(report["notifications_sent"]),
        "estimated_api_credits": credits,
        "artifact_name": f"`{name}`",
        "run_url": f"[{run_id}]({run['url']})",
        "_note": (
            f"Artifact `{name}` was downloaded and scanned on capture: zero webhook-URL "
            "matches from both the shared redaction scanner and an independent regex."
        ),
    }


def _split_slots(text: str) -> list[tuple[int, int]]:
    """Return (start, end) character spans for each 'Genuine Scheduled Run N' block."""
    headings = [m.start() for m in re.finditer(r"^## Genuine Scheduled Run \d+", text, re.M)]
    spans: list[tuple[int, int]] = []
    for index, start in enumerate(headings):
        end = headings[index + 1] if index + 1 < len(headings) else len(text)
        spans.append((start, end))
    return spans


def fill_slot(block: str, values: dict[str, str]) -> str:
    """Replace only placeholder cells inside one run's table."""

    def replace_row(match: re.Match[str]) -> str:
        label = match.group("label").strip()
        cell = match.group("value")
        if label in SKIP_ROWS or label not in ROW_FIELDS:
            return match.group(0)
        if "[BLOCKED:" not in cell and "Must be" not in cell:
            return match.group(0)  # already recorded; never overwrite
        return f"| {match.group('label')} | {values[ROW_FIELDS[label]]} |"

    filled = re.sub(
        r"^\| (?P<label>[^|]+?) \| (?P<value>[^|]*?) \|$",
        replace_row,
        block,
        flags=re.M,
    )
    return filled.replace("Verification note: _pending._", f"Verification note: {values['_note']}")


def update_evidence(text: str, collected: list[dict[str, str]]) -> tuple[str, int]:
    """Fill the earliest unrecorded slots. Returns (new_text, slots_written)."""
    spans = _split_slots(text)
    if len(spans) != SLOT_COUNT:
        raise VerificationError(f"expected {SLOT_COUNT} evidence slots, found {len(spans)}")

    pending = list(collected)
    written = 0
    # Rebuild back-to-front so earlier spans keep their offsets.
    for start, end in reversed(spans):
        block = text[start:end]
        if not PLACEHOLDER.search(block.replace("submission/assets/scheduled-run.png", "")):
            continue  # slot already recorded
        slot_index = spans.index((start, end))
        if slot_index >= len(pending):
            continue
        text = text[:start] + fill_slot(block, pending[slot_index]) + text[end:]
        written += 1
    return text, written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="verify and print findings without writing the evidence file",
    )
    args = parser.parse_args(argv)

    try:
        runs = list_schedule_runs()
    except VerificationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not runs:
        print("No genuine `schedule` run exists yet. Nothing recorded, nothing changed.")
        return 0

    print(f"Found {len(runs)} completed schedule run(s): {[r['databaseId'] for r in runs]}")

    collected: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory(prefix="marketops-evidence-") as tmp:
        workdir = Path(tmp)
        for run in runs[:SLOT_COUNT]:
            try:
                values = collect(run, workdir)
            except VerificationError as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 3
            print(f"  verified run {run['databaseId']}: artifact clean, trigger=schedule")
            collected.append(values)

    text = EVIDENCE_PATH.read_text(encoding="utf-8")
    updated, written = update_evidence(text, collected)

    if args.dry_run:
        print(f"[dry-run] would record {written} slot(s); no file written.")
        return 0

    if written:
        EVIDENCE_PATH.write_text(updated, encoding="utf-8")
        print(f"Recorded {written} slot(s) into {EVIDENCE_PATH}.")
        print("Review the diff, then commit. Screenshot rows still need a human capture.")
    else:
        print("All slots already recorded; nothing changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

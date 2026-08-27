#!/usr/bin/env python3
"""Create an honest, deterministic fixture-replay evidence bundle.

This helper is deliberately for local demo capture, not Track 2 qualification.
It runs two sanitized fixture replays against one SQLite file and writes the
same HTML/JSON/Markdown artifacts used by the scheduler. The first run renders
new-evidence dry previews; the unchanged second replay renders none and records
duplicate suppression. No Sectors API request or external webhook is made.

Example:
    uv run python scripts/capture_demo.py --reset
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from marketops.config import Settings
from marketops.models import RunMode, RunReport
from marketops.pipeline import execute

REPLAY_NOTICE = "SANITIZED HISTORICAL REPLAY - NOT LIVE MARKET DATA"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("data/demo-replay.db"),
        help="SQLite state used by both replays (default: data/demo-replay.db).",
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=Path("artifacts/demo-replay"),
        help="Directory for deterministic HTML/JSON/Markdown output.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Remove only the selected SQLite database and its WAL sidecars before replaying.",
    )
    return parser


def _reset_database(db_path: Path) -> None:
    """Delete only explicitly selected state files, never a directory tree."""
    for path in (db_path, Path(f"{db_path}-wal"), Path(f"{db_path}-shm")):
        if path.exists():
            path.unlink()


def _summary(report: RunReport) -> dict[str, Any]:
    return {
        "run_id": report.run_id,
        "trigger": report.trigger,
        "mode": report.mode.value,
        "status": report.status.value,
        "events_detected": report.events_detected,
        "new_events": report.new_events,
        "duplicate_events_suppressed": report.duplicate_events_suppressed,
        "notification_previews": report.notification_previews,
        "notifications_sent": report.notifications_sent,
        "estimated_api_credits": report.estimated_api_credits,
        "credit_budget": report.credit_budget,
    }


def main() -> int:
    args = _parser().parse_args()
    db_path = args.db_path
    artifact_dir = args.artifact_dir
    if args.reset:
        _reset_database(db_path)

    settings = Settings(db_path=db_path, artifact_dir=artifact_dir)
    first = execute(
        settings=settings,
        mode=RunMode.FIXTURE,
        trigger="manual-demo",
        dry_notify=True,
    )
    second = execute(
        settings=settings,
        mode=RunMode.FIXTURE,
        trigger="manual-demo",
        dry_notify=True,
    )

    artifact_dir.mkdir(parents=True, exist_ok=True)
    proof = {
        "label": REPLAY_NOTICE,
        "purpose": "deterministic local demo and QA only; not scheduled-run proof",
        "first_replay": _summary(first),
        "second_identical_replay": _summary(second),
        "assertions": {
            "first_has_new_evidence": first.new_events > 0,
            "first_has_preview_cards": first.notification_previews > 0,
            "second_has_no_preview_cards": second.notification_previews == 0,
            "second_suppressed_duplicates": second.duplicate_events_suppressed > 0,
            "actual_external_deliveries": 0,
        },
    }
    (artifact_dir / "demo-replay-summary.json").write_text(
        json.dumps(proof, indent=2), encoding="utf-8"
    )

    print(REPLAY_NOTICE)
    print(f"First run:  {json.dumps(_summary(first), sort_keys=True)}")
    print(f"Second run: {json.dumps(_summary(second), sort_keys=True)}")
    print(f"Wrote: {artifact_dir / 'demo-replay-summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

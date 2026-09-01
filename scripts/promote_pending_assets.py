#!/usr/bin/env python3
"""Promote the pending schedule-evidence screenshots once they are real.

`actions-history.png` and `scheduled-run.png` ship as explicit placeholder
graphics reading "EVIDENCE PENDING". Three documents describe them that way. If
someone drops in real captures and forgets to update the prose, the submission
quietly claims placeholder art as evidence; if someone updates the prose first,
it claims evidence that does not exist yet. Both failures are the same class of
mistake SEC-001 taught this project to design against.

So the prose is not edited by hand. This script refuses to touch any document
until both PNGs differ from the recorded placeholder digests, then rewrites all
three in one pass.

Usage:
    uv run python scripts/promote_pending_assets.py [--check]
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ASSETS = Path("submission/assets")

# Digests of the shipped placeholder graphics. A file that still hashes to one
# of these has not been replaced with a real capture.
PLACEHOLDER_DIGESTS = {
    "actions-history.png": "7b1f9d44aad2f479a1b82caeec8544bfe2dbfc10621e1b094d31131057896da6",
    "scheduled-run.png": "06e466dfaa6c34af692138fd761de6423fadb4264f9c6a02d24180f1a7a1dd13",
}

RUN_HISTORY = "33360850299, 33383915122, 33472247776"
RUN_DETAIL = "33472247776"

EDITS: list[tuple[str, str, str]] = [
    (
        "submission/assets/README.md",
        "| `actions-history.png` | PENDING PLACEHOLDER | Must be replaced by a real "
        "public GitHub Actions history after three `schedule` runs. Do not use as proof. |",
        "| `actions-history.png` | SCHEDULED-RUN EVIDENCE | Public GitHub Actions history "
        f"showing the three genuine `schedule` runs ({RUN_HISTORY}). Captured logged out, "
        "so it also demonstrates the runs are publicly verifiable. |",
    ),
    (
        "submission/assets/README.md",
        "| `scheduled-run.png` | PENDING PLACEHOLDER | Must be replaced by a real detail "
        "page for a live schedule run. Do not use as proof. |",
        "| `scheduled-run.png` | SCHEDULED-RUN EVIDENCE | Detail page for genuine schedule "
        f"run `{RUN_DETAIL}` (2026-09-01), showing workflow, `schedule` trigger, status, and "
        "timestamps. |",
    ),
    (
        "submission/storyboard.md",
        "- `assets/actions-history.png` and `assets/scheduled-run.png` remain placeholders",
        "- `assets/actions-history.png` and `assets/scheduled-run.png` are real captures",
    ),
    (
        "evidence/unattended-runs.md",
        "| Screenshot | `[BLOCKED: submission/assets/scheduled-run.png]` |",
        "| Screenshot | `submission/assets/actions-history.png` |",
    ),
    (
        "evidence/unattended-runs.md",
        "Remaining: the screenshot rows are deliberately left `[BLOCKED: ...]` because\n"
        "a human must capture the Actions history/detail images.",
        "The screenshot rows now reference real captures: "
        "`submission/assets/actions-history.png` for the history view and "
        f"`scheduled-run.png` for the detail page of run `{RUN_DETAIL}`.",
    ),
]

# Applied to every remaining screenshot row that still carries the placeholder.
ROW_SWAPS = [
    (
        "| Screenshot | `[BLOCKED: include in submission/assets/actions-history.png]` |",
        "| Screenshot | `submission/assets/actions-history.png` |",
    ),
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pending() -> list[str]:
    """Names of assets that are still the shipped placeholder."""
    still = []
    for name, expected in PLACEHOLDER_DIGESTS.items():
        path = ASSETS / name
        if not path.exists():
            still.append(f"{name} (missing)")
        elif digest(path) == expected:
            still.append(name)
    return still


def apply_edits() -> int:
    changed = 0
    for rel, old, new in EDITS:
        path = Path(rel)
        text = path.read_text(encoding="utf-8")
        if new in text and old not in text:
            continue  # already promoted
        if text.count(old) != 1:
            raise SystemExit(f"{rel}: expected exactly one match for {old[:60]!r}")
        path.write_text(text.replace(old, new), encoding="utf-8")
        changed += 1

    for old, new in ROW_SWAPS:
        path = Path("evidence/unattended-runs.md")
        text = path.read_text(encoding="utf-8")
        if old in text:
            path.write_text(text.replace(old, new), encoding="utf-8")
            changed += 1
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report whether the captures are in without editing anything",
    )
    args = parser.parse_args(argv)

    blocked = pending()
    if blocked:
        print("Captures not in yet - nothing was edited.")
        for name in blocked:
            print(f"  still the placeholder: {name}")
        print("\nReplace both with real 1600x900 captures, then run this again.")
        return 1

    print("Both captures differ from the shipped placeholders.")
    if args.check:
        print("--check given; no files edited.")
        return 0

    changed = apply_edits()
    print(f"Promoted {changed} passage(s) across the submission documents.")
    print("Review the diff before committing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

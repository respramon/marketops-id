"""Rendering: turning a run into artifacts a human (or a judge) can inspect.

Every run writes four things into ``artifacts/``:

``<run_id>.json``    the complete, machine-readable RunReport
``<run_id>.html``    a self-contained HTML research brief (CSS inlined, so it
                     survives being downloaded from a CI artifact zip and
                     opened offline)
``latest.json`` / ``latest.html``  stable filenames for the dashboard and demos
``<run_id>-summary.md``            GitHub Actions step-summary markdown

The HTML brief is deliberately standalone rather than served-only: an
unattended run must leave behind evidence that can be opened later without
starting a web server.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import DISCLAIMER, __version__
from .config import REPO_ROOT
from .models import Priority, RunReport, RunStatus

if TYPE_CHECKING:
    from .state import StateStore

logger = logging.getLogger(__name__)

TEMPLATE_DIR = REPO_ROOT / "templates"
STATIC_DIR = REPO_ROOT / "static"

PRIORITY_ORDER = (Priority.P1, Priority.P2, Priority.P3)


def build_environment(template_dir: Path | None = None) -> Environment:
    """Jinja2 environment with autoescaping on - this renders untrusted text."""
    env = Environment(
        loader=FileSystemLoader(str(template_dir or TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["idr"] = _idr_filter
    return env


def _idr_filter(value: Any) -> str:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return "-"
    if abs(amount) >= 1_000_000_000_000:
        return f"IDR {amount / 1_000_000_000_000:.2f}T"
    if abs(amount) >= 1_000_000_000:
        return f"IDR {amount / 1_000_000_000:.2f}B"
    return f"IDR {amount:,.0f}"


def load_css() -> str:
    """Read the dashboard stylesheet for inlining into standalone reports."""
    path = STATIC_DIR / "styles.css"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def report_context(
    report: RunReport, *, standalone: bool = False, runs: Any = None
) -> dict[str, Any]:
    """Everything the templates need, computed once."""
    return {
        "report": report,
        "version": __version__,
        "disclaimer": DISCLAIMER,
        "standalone": standalone,
        "inline_css": load_css() if standalone else "",
        "bands": [
            {
                "priority": priority,
                "label": priority.label,
                "dossiers": report.by_priority(priority),
            }
            for priority in PRIORITY_ORDER
        ],
        "queue_size": len(report.queue),
        "is_fixture": report.mode.value == "fixture",
        "status_class": {
            RunStatus.OK: "ok",
            RunStatus.PARTIAL: "partial",
            RunStatus.FAILED: "failed",
        }.get(report.status, "ok"),
        "runs": runs or [],
        "sources": report.sources,
    }


def render_report_html(report: RunReport, *, standalone: bool = True) -> str:
    """Render the research brief for one run."""
    env = build_environment()
    template = env.get_template("report.html")
    return template.render(**report_context(report, standalone=standalone))


def render_summary_markdown(report: RunReport) -> str:
    """GitHub Actions step summary - the evidence a judge reads first."""
    lines = [
        "# MarketOps ID - unattended run",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Run ID | `{report.run_id}` |",
        f"| Trigger | `{report.trigger}` |",
        f"| Mode | `{report.mode.value}` |",
        f"| Status | **{report.status.value}** |",
        f"| Started (WIB) | {report.started_at.strftime('%Y-%m-%d %H:%M:%S')} |",
        f"| Duration | {report.duration_seconds:.2f}s |",
        f"| Events detected | {report.events_detected} |",
        f"| New events | {report.new_events} |",
        f"| Duplicates suppressed | {report.duplicate_events_suppressed} |",
        f"| Candidates | {report.candidates} |",
        f"| Enriched tickers | {report.enriched_tickers} |",
        f"| Notifications sent | {report.notifications_sent} |",
        f"| Notification previews | {report.notification_previews} |",
        f"| Estimated API credits | {report.estimated_api_credits} / {report.credit_budget} |",
        "",
    ]

    if report.mode.value == "fixture":
        lines += ["> **SANITIZED HISTORICAL REPLAY - NOT LIVE MARKET DATA.**", ""]

    if report.warnings:
        lines += ["## Warnings", ""]
        lines += [f"- {w}" for w in report.warnings]
        lines += [""]

    lines += [
        "## Source health",
        "",
        "| Source | State | Records | Calls | Credits |",
        "| --- | --- | --- | --- | --- |",
    ]
    for source in report.sources:
        lines.append(
            f"| {source.name.value} | {source.state.value} | {source.records} | "
            f"{source.calls} | {source.credits} |"
        )
    lines.append("")

    if report.queue:
        lines += [
            "## Research queue",
            "",
            "| Priority | Ticker | Score | Why surfaced |",
            "| --- | --- | --- | --- |",
        ]
        for dossier in report.queue:
            why = "<br>".join(f"{c.signed} {c.label}" for c in dossier.score.components)
            lines.append(
                f"| {dossier.score.priority.value} | `{dossier.display_symbol}` | "
                f"{dossier.score.total}/100 | {why} |"
            )
    else:
        lines += ["## Research queue", "", "_Nothing crossed the P3 threshold in this run._"]

    lines += ["", f"_{DISCLAIMER}_", ""]
    return "\n".join(lines)


def write_artifacts(
    report: RunReport,
    artifact_dir: Path | str,
    *,
    store: StateStore | None = None,
) -> dict[str, Path]:
    """Write every artifact for one run. Returns the paths written."""
    target = Path(artifact_dir)
    target.mkdir(parents=True, exist_ok=True)

    written: dict[str, Path] = {}

    json_path = target / f"{report.run_id}.json"
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    written["json"] = json_path

    latest_json = target / "latest.json"
    latest_json.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    written["latest_json"] = latest_json

    try:
        html = render_report_html(report, standalone=True)
    except Exception as exc:  # pragma: no cover - template failure is non-fatal
        logger.error("render.html_failed run=%s error=%s", report.run_id, exc)
    else:
        html_path = target / f"{report.run_id}.html"
        html_path.write_text(html, encoding="utf-8")
        written["html"] = html_path
        latest_html = target / "latest.html"
        latest_html.write_text(html, encoding="utf-8")
        written["latest_html"] = latest_html

    summary_path = target / f"{report.run_id}-summary.md"
    summary_path.write_text(render_summary_markdown(report), encoding="utf-8")
    written["summary"] = summary_path

    if store is not None:
        history_path = target / "run-history.json"
        history_path.write_text(
            json.dumps(store.recent_runs(50), indent=2, default=str), encoding="utf-8"
        )
        written["history"] = history_path

    logger.info("artifacts.written run=%s dir=%s files=%d", report.run_id, target, len(written))
    return written


def console_summary(report: RunReport) -> str:
    """Compact plain-text summary for terminal and CI logs."""
    lines = [
        f"RUN STATUS: {report.status.value}",
        f"  run id            {report.run_id}",
        f"  mode              {report.mode.value}"
        + ("   [SANITIZED REPLAY - NOT LIVE DATA]" if report.mode.value == "fixture" else ""),
        f"  trigger           {report.trigger}",
        f"  events detected   {report.events_detected}",
        f"  new events        {report.new_events}",
        f"  duplicates        {report.duplicate_events_suppressed}",
        f"  candidates        {report.candidates}",
        f"  enriched tickers  {report.enriched_tickers}",
        f"  notifications     {report.notifications_sent}",
        f"  previews          {report.notification_previews}",
        f"  api credits       {report.estimated_api_credits} / {report.credit_budget}",
        f"  duration          {report.duration_seconds:.2f}s",
    ]
    for warning in report.warnings:
        lines.append(f"  WARNING: {warning}")

    lines.append("")
    if report.queue:
        lines.append("RESEARCH QUEUE")
        for dossier in report.queue:
            lines.append(
                f"  [{dossier.score.priority.value}] {dossier.display_symbol:<10} "
                f"{dossier.score.total:>3}/100  "
                f"{', '.join(t.value for t in dossier.event_types)}"
            )
            for component in dossier.score.components:
                lines.append(
                    f"        {component.signed:>4}  {component.label} - {component.evidence}"
                )
    else:
        lines.append("RESEARCH QUEUE: empty (nothing crossed the P3 threshold)")

    lines.append("")
    lines.append(DISCLAIMER)
    return "\n".join(lines)

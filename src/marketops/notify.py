"""Notification delivery: the research queue leaves the machine here.

Two sinks, both optional and independent:

* **Discord** - rich embeds, one card per dossier, colour-coded by priority.
  Large queues are split into limit-safe messages. This is what an analyst
  actually sees at 07:20 in the morning.
* **Generic webhook** - a plain JSON POST for n8n, Slack-compatible receivers,
  or an internal service.

Design rules that matter for a hackathon judge and for a real desk alike:

* A notification failure is **never** fatal. The queue is already on disk and
  in the dashboard; failing to reach Discord degrades the run to PARTIAL and
  is reported, it does not throw the morning's work away.
* Only dossiers containing at least one event not yet delivered to a sink are
  notified. This preserves deduplication while allowing a webhook outage to
  retry safely on the next run.
* ``--dry-notify`` renders the exact payload without transmitting, so the live
  path can be exercised end to end without messaging anyone.
* Webhook URLs are secrets. They are never logged, never rendered, and never
  written into an artifact.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from . import DISCLAIMER
from .config import Settings
from .models import Priority, RunReport, RunStatus, TickerDossier

logger = logging.getLogger(__name__)

MAX_EMBEDS_PER_MESSAGE = 10
"""Discord's hard limit on embeds in a single webhook payload."""

MAX_EMBED_TEXT_PER_MESSAGE = 6000
"""Discord's aggregate character limit across all embeds in one message."""

PRIORITY_COLOURS = {
    Priority.P1: 0xD7263D,  # red    - urgent review
    Priority.P2: 0xE8A33D,  # amber  - review
    Priority.P3: 0x4C8FBF,  # blue   - monitor
    Priority.NONE: 0x8A8F98,
}

STATUS_ICON = {
    RunStatus.OK: "OK",
    RunStatus.PARTIAL: "PARTIAL",
    RunStatus.FAILED: "FAILED",
}


class NotificationError(RuntimeError):
    """A sink could not be reached. Caught by the pipeline, never propagated."""


def notifiable(report: RunReport) -> list[TickerDossier]:
    """Dossiers worth interrupting a human for.

    In the queue (>= P3) **and** carrying at least one event not previously
    delivered to a configured sink. The second clause preserves the
    deduplication contract while keeping failed webhook delivery retryable.
    """
    return [d for d in report.queue if d.needs_notification]


def _card_lines(dossier: TickerDossier) -> str:
    """The 'why surfaced' block - the reason the analyst trusts the queue."""
    lines = [
        f"**Attention Score: {dossier.score.total}/100 - {dossier.score.priority.value} "
        f"({dossier.score.priority.label})**",
        "",
    ]
    lines.append("__Why surfaced__")
    for component in dossier.score.components:
        lines.append(f"`{component.signed:>4}` {component.label} - {component.evidence}")
    if dossier.score.override_reason:
        lines.append("")
        lines.append(f"_{dossier.score.override_reason}_")

    lines.append("")
    lines.append("__Correlated evidence__")
    for event in dossier.events[:6]:
        stamp = event.occurred_display
        if event.source_url:
            lines.append(f"- [{event.headline}]({event.source_url}) ({stamp})")
        else:
            lines.append(f"- {event.headline} ({stamp})")
    if len(dossier.events) > 6:
        lines.append(f"- ...and {len(dossier.events) - 6} more")

    body = "\n".join(lines)
    return body[:4000]


def _discord_embed(report: RunReport, dossier: TickerDossier) -> dict[str, Any]:
    """Build one research card within Discord's per-embed limits."""
    title = f"{dossier.score.priority.value} - {dossier.display_symbol}"
    if dossier.company_name:
        title += f" - {dossier.company_name[:80]}"
    return {
        "title": title[:250],
        "description": _card_lines(dossier),
        "color": PRIORITY_COLOURS.get(dossier.score.priority, 0x8A8F98),
        "footer": {"text": f"{DISCLAIMER} - run {report.run_id}"[:2000]},
    }


def _embed_text_size(embed: dict[str, Any]) -> int:
    """Count fields included in Discord's 6,000-character aggregate limit."""
    size = len(str(embed.get("title", ""))) + len(str(embed.get("description", "")))
    footer = embed.get("footer")
    if isinstance(footer, dict):
        size += len(str(footer.get("text", "")))
    author = embed.get("author")
    if isinstance(author, dict):
        size += len(str(author.get("name", "")))
    for field in embed.get("fields", []):
        if isinstance(field, dict):
            size += len(str(field.get("name", "")))
            size += len(str(field.get("value", "")))
    return size


def _discord_header(report: RunReport) -> list[str]:
    """Build the common context shown above every Discord delivery batch."""
    p1 = len(report.by_priority(Priority.P1))
    p2 = len(report.by_priority(Priority.P2))
    p3 = len(report.by_priority(Priority.P3))

    header_lines = [
        f"**MarketOps ID - research queue for {report.started_at.strftime('%d %b %Y')}**",
        (
            f"Run `{report.run_id}` - {STATUS_ICON.get(report.status, report.status.value)} - "
            f"trigger `{report.trigger}` - mode `{report.mode.value}`"
        ),
        (
            f"{report.events_detected} events detected - {report.new_events} new - "
            f"{report.duplicate_events_suppressed} duplicates suppressed - "
            f"{report.candidates} candidates - ~{report.estimated_api_credits} API credits"
        ),
        f"Queue: **P1 {p1}** / P2 {p2} / P3 {p3}",
    ]
    if report.mode.value == "fixture":
        header_lines.append("_SANITIZED HISTORICAL REPLAY - NOT LIVE MARKET DATA._")
    if report.status is RunStatus.PARTIAL:
        for warning in report.warnings[:4]:
            header_lines.append(f"> WARNING: {warning}")
    return header_lines


def _chunk_discord_embeds(
    report: RunReport, dossiers: list[TickerDossier]
) -> list[list[dict[str, Any]]]:
    """Partition cards by both Discord's count and aggregate text limits."""
    batches: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_size = 0

    for dossier in dossiers:
        embed = _discord_embed(report, dossier)
        embed_size = _embed_text_size(embed)
        count_full = len(current) >= MAX_EMBEDS_PER_MESSAGE
        text_full = bool(current) and current_size + embed_size > MAX_EMBED_TEXT_PER_MESSAGE
        if count_full or text_full:
            batches.append(current)
            current = []
            current_size = 0
        current.append(embed)
        current_size += embed_size

    if current:
        batches.append(current)
    return batches


def build_discord_payloads(
    report: RunReport, dossiers: list[TickerDossier]
) -> list[dict[str, Any]]:
    """Assemble one or more limit-safe Discord webhook bodies for a run."""
    embed_batches = _chunk_discord_embeds(report, dossiers)
    payloads: list[dict[str, Any]] = []
    batch_count = len(embed_batches)
    delivered_before = 0

    for batch_index, embeds in enumerate(embed_batches, start=1):
        header_lines = _discord_header(report)
        if batch_count > 1:
            first_card = delivered_before + 1
            last_card = delivered_before + len(embeds)
            header_lines.append(
                f"Delivery batch **{batch_index}/{batch_count}** - "
                f"research cards {first_card}-{last_card} of {len(dossiers)}"
            )
        payloads.append(
            {
                "username": "MarketOps ID",
                "content": "\n".join(header_lines)[:1900],
                "embeds": embeds,
                "allowed_mentions": {"parse": []},
            }
        )
        delivered_before += len(embeds)
    return payloads


def build_discord_payload(report: RunReport, dossiers: list[TickerDossier]) -> dict[str, Any]:
    """Build the first limit-safe Discord body; retained for API compatibility."""
    payloads = build_discord_payloads(report, dossiers)
    if payloads:
        return payloads[0]
    return {
        "username": "MarketOps ID",
        "content": "\n".join(_discord_header(report))[:1900],
        "embeds": [],
        "allowed_mentions": {"parse": []},
    }


def build_generic_payload(report: RunReport, dossiers: list[TickerDossier]) -> dict[str, Any]:
    """A plain, stable JSON contract for non-Discord receivers."""
    return {
        "product": "MarketOps ID",
        "disclaimer": DISCLAIMER,
        "run": {
            "run_id": report.run_id,
            "mode": report.mode.value,
            "status": report.status.value,
            "trigger": report.trigger,
            "started_at": report.started_at.isoformat(),
            "finished_at": report.finished_at.isoformat() if report.finished_at else None,
            "events_detected": report.events_detected,
            "new_events": report.new_events,
            "duplicate_events_suppressed": report.duplicate_events_suppressed,
            "candidates": report.candidates,
            "estimated_api_credits": report.estimated_api_credits,
            "warnings": report.warnings,
        },
        "queue": [
            {
                "symbol": d.symbol,
                "display_symbol": d.display_symbol,
                "company_name": d.company_name,
                "score": d.score.total,
                "priority": d.score.priority.value,
                "why_surfaced": d.score.why_lines,
                "override_reason": d.score.override_reason,
                "events": [
                    {
                        "event_id": e.event_id,
                        "type": e.event_type.value,
                        "headline": e.headline,
                        "detail": e.detail,
                        "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
                        "source_url": e.source_url,
                    }
                    for e in d.events
                ],
            }
            for d in dossiers
        ],
    }


def _post(url: str, payload: dict[str, Any], timeout: float) -> None:
    """POST a webhook payload, converting any failure into NotificationError.

    The URL is a secret, so it never reaches the exception message or the log -
    only the sink's name and the status code do.
    """
    try:
        response = httpx.post(url, json=payload, timeout=timeout)
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise NotificationError(f"webhook transport failure: {type(exc).__name__}") from exc
    if response.status_code >= 400:
        raise NotificationError(f"webhook rejected the payload with HTTP {response.status_code}")


def dispatch(
    report: RunReport,
    settings: Settings,
    *,
    dry_run: bool = False,
    artifact_dir: Any = None,
) -> tuple[int, list[str], list[str]]:
    """Send the research queue to every configured sink.

    Returns ``(cards_sent, channels_used, errors)``. Never raises: a failed
    sink is an error string the pipeline turns into a PARTIAL status.
    """
    # A dry preview never changes delivery state. Limit it to evidence first
    # observed in this run so repeatedly replaying an unchanged fixture does
    # not manufacture a misleading stream of "new" preview cards. A real run
    # uses the delivery-pending set instead, so an earlier preview cannot make
    # a real notification disappear.
    dossiers = (
        [dossier for dossier in report.queue if dossier.is_new] if dry_run else notifiable(report)
    )
    channels: list[str] = []
    errors: list[str] = []

    if not dossiers:
        logger.info(
            "notify.skipped reason=no_new_evidence run=%s queue=%d",
            report.run_id,
            len(report.queue),
        )
        return 0, channels, errors

    discord_payloads = build_discord_payloads(report, dossiers)
    generic_payload = build_generic_payload(report, dossiers)

    if dry_run:
        if artifact_dir is not None:
            from pathlib import Path

            target = Path(artifact_dir)
            target.mkdir(parents=True, exist_ok=True)
            (target / f"{report.run_id}-notification-preview.json").write_text(
                json.dumps(
                    {"discord": discord_payloads, "generic": generic_payload},
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        logger.info("notify.dry_run cards=%d run=%s", len(dossiers), report.run_id)
        # A preview is evidence of payload construction, not a delivered
        # notification. Keeping this at zero prevents dry runs from masking a
        # required real delivery in run history or unattended-run evidence.
        return 0, ["dry-notify-preview"], errors

    if settings.discord_webhook_url:
        try:
            for batch_index, discord_payload in enumerate(discord_payloads, start=1):
                try:
                    _post(
                        settings.discord_webhook_url.get_secret_value(),
                        discord_payload,
                        settings.http_timeout,
                    )
                except NotificationError as exc:
                    raise NotificationError(
                        f"batch {batch_index}/{len(discord_payloads)} failed: {exc}"
                    ) from exc
            channels.append("discord")
        except NotificationError as exc:
            errors.append(f"discord: {exc}")

    if settings.generic_webhook_url:
        try:
            _post(
                settings.generic_webhook_url.get_secret_value(),
                generic_payload,
                settings.http_timeout,
            )
            channels.append("generic-webhook")
        except NotificationError as exc:
            errors.append(f"generic-webhook: {exc}")

    if not settings.has_any_webhook:
        errors.append(
            "no webhook configured: set DISCORD_WEBHOOK_URL or GENERIC_WEBHOOK_URL "
            "to deliver the research queue"
        )
        return 0, channels, errors

    sent = len(dossiers) if channels else 0
    logger.info(
        "notify.dispatched cards=%d discord_batches=%d channels=%s errors=%d run=%s",
        sent,
        len(discord_payloads) if settings.discord_webhook_url else 0,
        ",".join(channels) or "none",
        len(errors),
        report.run_id,
    )
    return sent, channels, errors

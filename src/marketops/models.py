"""Canonical domain model.

Everything downstream of :mod:`marketops.normalize` speaks in these types.
Raw Sectors API payloads never leak past the normalisation boundary, which is
what lets scoring, correlation and deduplication stay deterministic and
testable without a network.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta, timezone
from enum import StrEnum
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field

WIB = timezone(timedelta(hours=7), name="WIB")
"""Asia/Jakarta. Fixed offset - Indonesia has observed no DST since 1964."""


def now_wib() -> datetime:
    """Current time in Western Indonesian Time."""
    return datetime.now(tz=WIB)


class EventType(StrEnum):
    """The kinds of market evidence MarketOps ingests."""

    SUSPENSION = "suspension"
    FILING = "filing"
    PRICE_MOVE = "price_move"
    NEWS = "news"
    FOREIGN_FLOW = "foreign_flow"
    CORPORATE_ACTION = "corporate_action"


class Priority(StrEnum):
    """Research queue band."""

    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    NONE = "NONE"

    @property
    def label(self) -> str:
        return {
            Priority.P1: "Urgent Review",
            Priority.P2: "Review",
            Priority.P3: "Monitor",
            Priority.NONE: "Below threshold",
        }[self]


class SourceName(StrEnum):
    """One entry per Sectors endpoint the pipeline calls."""

    FILINGS = "filings"
    SUSPENSIONS = "suspensions"
    MOVERS = "movers"
    NEWS = "news"
    FOREIGN_FLOW = "foreign_flow"
    CORPORATE_ACTIONS = "corporate_actions"


class SourceState(StrEnum):
    """Outcome of one source within a run. Drives fail-soft reporting."""

    OK = "ok"
    FAILED = "failed"
    SKIPPED = "skipped"
    BUDGET_EXHAUSTED = "budget_exhausted"


class RunStatus(StrEnum):
    """Overall run verdict."""

    OK = "OK"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class RunMode(StrEnum):
    """Where the data came from.

    Surfaced in every artifact so a sanitized fixture replay can never be
    mistaken for live market data.
    """

    FIXTURE = "fixture"
    LIVE = "live"


def normalize_symbol(raw: str | None) -> str | None:
    """Reduce any Sectors symbol spelling to the canonical bare ticker.

    The API returns ``BBCA.JK`` in responses but accepts ``BBCA`` in query
    parameters, so a single canonical form is required for correlation to
    group evidence about the same company together.
    """
    if raw is None:
        return None
    cleaned = str(raw).strip().upper().removesuffix(".JK")
    return cleaned or None


def safe_source_url(raw: str | None) -> str | None:
    """Return a browser-safe provenance URL or ``None``.

    Sectors payloads are external input. HTML escaping protects markup, but it
    does not make an active ``javascript:`` or ``data:`` URL safe when a user
    clicks it. Provenance links therefore accept only absolute HTTP(S) URLs
    with a real host and reject control characters before they reach Jinja or
    Discord markdown.
    """
    if raw is None:
        return None
    value = str(raw).strip()
    if not value or any(ord(char) < 0x20 for char in value):
        return None
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return None
    return value


def to_wib(value: datetime | date | str | None) -> datetime | None:
    """Coerce any Sectors timestamp spelling into a timezone-aware WIB datetime.

    Sectors returns naive timestamps (``2026-07-09T14:29:39``) and plain dates
    (``2026-07-03``). Naive values are interpreted as already being WIB, which
    is what the exchange publishes in. Unparseable input yields ``None`` rather
    than raising, so one malformed record cannot fail a whole run.
    """
    if value is None:
        return None
    parsed: datetime
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime(value.year, value.month, value.day, tzinfo=WIB)
    else:
        text = str(value).strip()
        if not text:
            return None
        text = text.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            try:
                parsed = datetime.strptime(text[:10], "%Y-%m-%d")  # noqa: DTZ007
            except ValueError:
                return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=WIB)
    return parsed.astimezone(WIB)


def fingerprint(
    event_type: EventType | str,
    symbol: str,
    occurred_at: datetime | None,
    source_ref: str | None,
) -> str:
    """Deterministic SHA-256 identity for a market event.

    Two observations of the same underlying event - across runs, processes or
    machines - must produce the same fingerprint, and any change of substance
    (a different day, a different filing PDF) must produce a different one.
    This is the entire basis of deduplication, so it deliberately depends on
    nothing but its four arguments: no clock, no run id, no ordering.
    """
    stamp = occurred_at.astimezone(WIB).isoformat() if occurred_at else ""
    material = "|".join(
        [
            str(event_type),
            (symbol or "").upper(),
            stamp,
            (source_ref or "").strip(),
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


class MarketEvent(BaseModel):
    """One piece of normalised evidence about one ticker."""

    model_config = ConfigDict(frozen=True)

    event_id: str
    event_type: EventType
    symbol: str
    occurred_at: datetime | None
    headline: str
    detail: str = ""
    source_ref: str | None = None
    source_url: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        event_type: EventType,
        symbol: str,
        occurred_at: datetime | None,
        headline: str,
        detail: str = "",
        source_ref: str | None = None,
        source_url: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> MarketEvent:
        """Construct an event with its fingerprint derived, never supplied."""
        return cls(
            event_id=fingerprint(event_type, symbol, occurred_at, source_ref),
            event_type=event_type,
            symbol=symbol,
            occurred_at=occurred_at,
            headline=headline,
            detail=detail,
            source_ref=source_ref,
            source_url=safe_source_url(source_url),
            payload=payload or {},
        )

    @property
    def occurred_display(self) -> str:
        return self.occurred_at.strftime("%Y-%m-%d %H:%M WIB") if self.occurred_at else "unknown"


class ScoreComponent(BaseModel):
    """A single, human-readable reason the score moved."""

    model_config = ConfigDict(frozen=True)

    label: str
    points: int
    evidence: str
    event_type: EventType | None = None

    @property
    def signed(self) -> str:
        return f"+{self.points}" if self.points >= 0 else str(self.points)


class ScoreBreakdown(BaseModel):
    """The explainable output of the Research Attention Score."""

    model_config = ConfigDict(frozen=True)

    total: int
    priority: Priority
    components: list[ScoreComponent] = Field(default_factory=list)
    override_reason: str | None = None
    capped: bool = False

    @property
    def why_lines(self) -> list[str]:
        return [f"{c.signed} {c.label} - {c.evidence}" for c in self.components]


class TickerDossier(BaseModel):
    """All correlated evidence for one ticker in one run, plus its score."""

    symbol: str
    company_name: str | None = None
    events: list[MarketEvent] = Field(default_factory=list)
    score: ScoreBreakdown
    enriched: bool = False
    new_event_ids: list[str] = Field(default_factory=list)
    pending_alert_event_ids: list[str] = Field(default_factory=list)

    @property
    def display_symbol(self) -> str:
        return f"{self.symbol}.JK"

    @property
    def event_types(self) -> list[EventType]:
        seen: list[EventType] = []
        for event in self.events:
            if event.event_type not in seen:
                seen.append(event.event_type)
        return seen

    @property
    def is_new(self) -> bool:
        """True when at least one event in this dossier was never seen before."""
        return bool(self.new_event_ids)

    @property
    def needs_notification(self) -> bool:
        """True when at least one correlated event has not reached a sink.

        Observation and delivery are deliberately separate facts.  A webhook
        outage must not turn a newly observed filing into a permanently lost
        alert merely because it was persisted for deduplication first.
        """
        return bool(self.pending_alert_event_ids)

    @property
    def sources(self) -> list[str]:
        urls: list[str] = []
        for event in self.events:
            if event.source_url and event.source_url not in urls:
                urls.append(event.source_url)
        return urls


class SourceReport(BaseModel):
    """Per-endpoint outcome, so a partial run can say exactly what is missing."""

    name: SourceName
    state: SourceState
    records: int = 0
    credits: int = 0
    calls: int = 0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.state is SourceState.OK


class RunReport(BaseModel):
    """The complete, serialisable record of one unattended run."""

    run_id: str
    mode: RunMode
    status: RunStatus = RunStatus.OK
    started_at: datetime
    finished_at: datetime | None = None
    trigger: str = "manual"

    sources: list[SourceReport] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    events_detected: int = 0
    new_events: int = 0
    duplicate_events_suppressed: int = 0
    candidates: int = 0
    enriched_tickers: int = 0
    notifications_sent: int = 0
    notification_previews: int = 0
    estimated_api_credits: int = 0
    credit_budget: int = 0

    dossiers: list[TickerDossier] = Field(default_factory=list)
    notify_error: str | None = None

    @property
    def duration_seconds(self) -> float:
        if not self.finished_at:
            return 0.0
        return (self.finished_at - self.started_at).total_seconds()

    @property
    def failed_sources(self) -> list[SourceReport]:
        return [s for s in self.sources if s.state is SourceState.FAILED]

    def by_priority(self, priority: Priority) -> list[TickerDossier]:
        return [d for d in self.dossiers if d.score.priority is priority]

    @property
    def queue(self) -> list[TickerDossier]:
        """Dossiers that reached at least P3, ranked most urgent first."""
        ranked = [d for d in self.dossiers if d.score.priority is not Priority.NONE]
        order = {Priority.P1: 0, Priority.P2: 1, Priority.P3: 2, Priority.NONE: 3}
        return sorted(ranked, key=lambda d: (order[d.score.priority], -d.score.total, d.symbol))

"""Correlation: many loose events become one dossier per ticker.

This is the step that turns "seven things happened today" into "these two
companies are worth your morning". An analyst does not want an insider filing
alert, then a separate price-move alert, then a separate news alert about the
same company - they want one card that says all three happened to the same
ticker, which is precisely what makes it worth opening.
"""

from __future__ import annotations

from collections import defaultdict

from .config import ScoringConfig, Watchlist
from .models import EventType, MarketEvent, TickerDossier
from .scoring import preliminary_score, score_events


def group_by_symbol(events: list[MarketEvent]) -> dict[str, list[MarketEvent]]:
    """Bucket events by canonical ticker, preserving insertion order within."""
    grouped: dict[str, list[MarketEvent]] = defaultdict(list)
    for event in events:
        grouped[event.symbol].append(event)
    return dict(grouped)


def _event_sort_key(event: MarketEvent) -> tuple[int, str, str]:
    """Stable, clock-free ordering: newest first, ties broken by fingerprint."""
    order = {
        EventType.SUSPENSION: 0,
        EventType.FILING: 1,
        EventType.PRICE_MOVE: 2,
        EventType.FOREIGN_FLOW: 3,
        EventType.NEWS: 4,
        EventType.CORPORATE_ACTION: 5,
    }
    stamp = event.occurred_at.isoformat() if event.occurred_at else ""
    # Negate recency by inverting the string sort via a descending marker.
    return (order.get(event.event_type, 9), _invert(stamp), event.event_id)


def _invert(text: str) -> str:
    """Sort key that reverses lexicographic order for ISO timestamps."""
    return "".join(chr(0x10FFFD - ord(ch)) if ord(ch) < 0x10FFFD else ch for ch in text)


def select_candidates(
    events: list[MarketEvent],
    config: ScoringConfig,
    watchlist: Watchlist | None = None,
    *,
    limit: int | None = None,
) -> list[str]:
    """Rank discovery tickers by how much they deserve paid enrichment.

    Ordering is by preliminary score, then by evidence breadth, then
    alphabetically - so the result is fully deterministic and a fixture replay
    enriches the same tickers every time.
    """
    grouped = group_by_symbol(events)
    ranked: list[tuple[int, int, str]] = []
    for symbol, bucket in grouped.items():
        if watchlist and watchlist.is_muted(symbol):
            continue
        prelim = preliminary_score(bucket, config)
        if watchlist and watchlist.is_covered(symbol):
            prelim += watchlist.covered_bonus
        ranked.append((-prelim, -len({e.event_type for e in bucket}), symbol))
    ranked.sort()
    ordered = [symbol for _, _, symbol in ranked]
    return ordered[:limit] if limit is not None else ordered


def build_dossiers(
    events: list[MarketEvent],
    config: ScoringConfig,
    watchlist: Watchlist | None = None,
    *,
    new_event_ids: set[str] | None = None,
    pending_alert_event_ids: set[str] | None = None,
    enriched: set[str] | None = None,
) -> list[TickerDossier]:
    """Correlate, score and rank every ticker with evidence in this run."""
    new_ids = new_event_ids or set()
    pending_ids = pending_alert_event_ids or set()
    enriched_set = enriched or set()
    dossiers: list[TickerDossier] = []

    for symbol, bucket in group_by_symbol(events).items():
        if watchlist and watchlist.is_muted(symbol):
            continue
        ordered = sorted(bucket, key=_event_sort_key)
        breakdown = score_events(symbol, ordered, config, watchlist)
        dossiers.append(
            TickerDossier(
                symbol=symbol,
                company_name=_company_name(ordered),
                events=ordered,
                score=breakdown,
                enriched=symbol in enriched_set,
                new_event_ids=[e.event_id for e in ordered if e.event_id in new_ids],
                pending_alert_event_ids=[e.event_id for e in ordered if e.event_id in pending_ids],
            )
        )

    dossiers.sort(key=lambda d: (-d.score.total, d.symbol))
    return dossiers


def _company_name(events: list[MarketEvent]) -> str | None:
    """Recover a human-readable company name if any source supplied one."""
    for event in events:
        name = event.payload.get("company_name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None

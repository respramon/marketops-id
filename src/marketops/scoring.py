"""The Research Attention Score.

WHAT IT IS
    A deterministic, explainable triage heuristic that decides the ORDER in
    which a human analyst reviews tickers today.

WHAT IT IS NOT
    Not an investment score, not a valuation, not a return forecast, and never
    a buy or sell signal. A high score means "a person should look at this
    first", nothing more.

Three properties are load-bearing and are asserted by the test-suite:

1. **Deterministic** - the same evidence always yields the same score. No
   clock, no randomness, no model call.
2. **Order-independent** - events are aggregated with ``max``/``any`` over the
   whole set, never folded in arrival order, so a reshuffled input list cannot
   move the score or reorder the explanation.
3. **Configurable** - every weight and threshold lives in ``config/scoring.yml``.
   This module contains no magic numbers.
"""

from __future__ import annotations

from .config import ScoringConfig, Watchlist
from .models import (
    EventType,
    MarketEvent,
    Priority,
    ScoreBreakdown,
    ScoreComponent,
)

# The canonical order components are presented in. Fixed here rather than
# derived from input order, so the "why surfaced" block reads the same way in
# the dashboard, the Discord card and the JSON artifact every single time.
_COMPONENT_ORDER: tuple[EventType | None, ...] = (
    EventType.SUSPENSION,
    EventType.FILING,
    EventType.PRICE_MOVE,
    EventType.FOREIGN_FLOW,
    EventType.NEWS,
    EventType.CORPORATE_ACTION,
    None,  # watchlist bonus and any other non-event component sorts last
)


def _of_type(events: list[MarketEvent], event_type: EventType) -> list[MarketEvent]:
    return [e for e in events if e.event_type is event_type]


def _max_payload(events: list[MarketEvent], key: str) -> float | None:
    """Largest numeric ``key`` across ``events``; ``None`` when absent."""
    values = [
        float(e.payload[key])
        for e in events
        if isinstance(e.payload.get(key), int | float) and not isinstance(e.payload.get(key), bool)
    ]
    return max(values) if values else None


def priority_for(total: int, config: ScoringConfig) -> Priority:
    """Map a score onto its queue band."""
    bands = config.priority
    if total >= bands.p1_min:
        return Priority.P1
    if total >= bands.p2_min:
        return Priority.P2
    if total >= bands.p3_min:
        return Priority.P3
    return Priority.NONE


def score_events(
    symbol: str,
    events: list[MarketEvent],
    config: ScoringConfig,
    watchlist: Watchlist | None = None,
) -> ScoreBreakdown:
    """Compute the Research Attention Score for one ticker's evidence set."""
    thresholds = config.thresholds
    components: list[ScoreComponent] = []

    # -- Override: an IDX suspension is categorical, not additive -----------
    suspensions = _of_type(events, EventType.SUSPENSION)
    if suspensions:
        override = config.weight("suspension", "override_score")
        reason = suspensions[0].detail or "IDX trading suspension in effect"
        return ScoreBreakdown(
            total=min(override, config.maximum_score),
            priority=priority_for(override, config),
            components=[
                ScoreComponent(
                    label="IDX trading suspension",
                    points=override,
                    evidence=reason,
                    event_type=EventType.SUSPENSION,
                )
            ],
            override_reason=(
                "Trading is halted. Scoring is overridden because no other evidence "
                "changes what the analyst must do first."
            ),
            capped=override > config.maximum_score,
        )

    # -- Insider / major-shareholder filings --------------------------------
    filings = _of_type(events, EventType.FILING)
    if filings:
        base = config.weight("filing", "base")
        if base:
            holders = sorted(
                {
                    str(e.payload.get("holder_name", "")).strip()
                    for e in filings
                    if e.payload.get("holder_name")
                }
            )
            who = holders[0] if len(holders) == 1 else f"{len(filings)} filings"
            components.append(
                ScoreComponent(
                    label="Insider or major-shareholder filing",
                    points=base,
                    evidence=who or "Filing disclosed to IDX",
                    event_type=EventType.FILING,
                )
            )

        top_pct = _max_payload(filings, "share_percentage_transaction")
        if top_pct is not None and top_pct >= thresholds.ownership_change_pct:
            points = config.weight("filing", "ownership_change_ge_0_5_pct")
            if points:
                components.append(
                    ScoreComponent(
                        label="Significant ownership change",
                        points=points,
                        evidence=(
                            f"{top_pct:.2f}% of shares transacted "
                            f"(threshold {thresholds.ownership_change_pct}%)"
                        ),
                        event_type=EventType.FILING,
                    )
                )

        top_value = _max_payload(filings, "transaction_value")
        if top_value is not None and top_value >= thresholds.transaction_value_idr:
            points = config.weight("filing", "transaction_value_ge_25b_idr")
            if points:
                billions = top_value / 1_000_000_000
                limit_b = thresholds.transaction_value_idr / 1_000_000_000
                components.append(
                    ScoreComponent(
                        label="Large transaction value",
                        points=points,
                        evidence=f"IDR {billions:,.1f}B transacted (threshold IDR {limit_b:,.0f}B)",
                        event_type=EventType.FILING,
                    )
                )

    # -- Price movement (exclusive tiers) -----------------------------------
    moves = _of_type(events, EventType.PRICE_MOVE)
    top_move = _max_payload(moves, "abs_change_pct")
    if top_move is not None:
        if top_move >= thresholds.price_move_large_pct:
            points = config.weight("price_move", "abs_change_ge_7_pct")
            band = f"at or above {thresholds.price_move_large_pct}%"
        elif top_move >= thresholds.price_move_small_pct:
            points = config.weight("price_move", "abs_change_ge_3_pct")
            band = f"at or above {thresholds.price_move_small_pct}%"
        else:
            points = 0
            band = ""
        if points:
            components.append(
                ScoreComponent(
                    label="Large one-day price move",
                    points=points,
                    evidence=f"{top_move:.2f}% one-day move ({band})",
                    event_type=EventType.PRICE_MOVE,
                )
            )

    # -- Foreign-flow anomaly (exclusive tiers) -----------------------------
    flows = _of_type(events, EventType.FOREIGN_FLOW)
    top_ratio = _max_payload(flows, "anomaly_ratio")
    if top_ratio is not None:
        if top_ratio >= thresholds.foreign_flow_ratio_large:
            points = config.weight("foreign_flow", "anomaly_ratio_ge_4x")
            band = f"at or above {thresholds.foreign_flow_ratio_large}x"
        elif top_ratio >= thresholds.foreign_flow_ratio_small:
            points = config.weight("foreign_flow", "anomaly_ratio_ge_2x")
            band = f"at or above {thresholds.foreign_flow_ratio_small}x"
        else:
            points = 0
            band = ""
        if points:
            direction = str(flows[0].payload.get("direction", "flow"))
            components.append(
                ScoreComponent(
                    label="Foreign-flow anomaly",
                    points=points,
                    evidence=f"Net foreign {direction} {top_ratio:.1f}x recent average ({band})",
                    event_type=EventType.FOREIGN_FLOW,
                )
            )

    # -- Relevant news -------------------------------------------------------
    news = _of_type(events, EventType.NEWS)
    if news:
        points = config.weight("relevant_news", "present")
        if points:
            headline = min((e.headline for e in news), key=lambda h: (len(h), h))
            components.append(
                ScoreComponent(
                    label="Relevant news",
                    points=points,
                    evidence=(headline[:120] if headline else f"{len(news)} related article(s)"),
                    event_type=EventType.NEWS,
                )
            )

    # -- Upcoming corporate action -------------------------------------------
    actions = _of_type(events, EventType.CORPORATE_ACTION)
    if actions:
        points = config.weight("corporate_action", "upcoming_within_7_days")
        if points:
            soonest = min(
                actions,
                key=lambda e: (
                    float(e.payload.get("days_until", 99))
                    if isinstance(e.payload.get("days_until"), int | float)
                    else 99.0,
                    e.event_id,
                ),
            )
            components.append(
                ScoreComponent(
                    label="Upcoming corporate action",
                    points=points,
                    evidence=soonest.headline[:120],
                    event_type=EventType.CORPORATE_ACTION,
                )
            )

    # -- Standing analyst coverage -------------------------------------------
    if watchlist and watchlist.covered_bonus and watchlist.is_covered(symbol) and components:
        components.append(
            ScoreComponent(
                label="On analyst watchlist",
                points=watchlist.covered_bonus,
                evidence="Ticker is under active coverage by this desk",
                event_type=None,
            )
        )

    components.sort(key=lambda c: (_COMPONENT_ORDER.index(c.event_type), -c.points, c.label))

    raw_total = sum(c.points for c in components)
    total = min(raw_total, config.maximum_score)
    return ScoreBreakdown(
        total=total,
        priority=priority_for(total, config),
        components=components,
        override_reason=None,
        capped=raw_total > config.maximum_score,
    )


def preliminary_score(events: list[MarketEvent], config: ScoringConfig) -> int:
    """Cheap pre-enrichment ranking used to spend the credit budget well.

    Enrichment costs credits per ticker, so the candidate universe is ordered
    by discovery evidence alone before any paid call is made. This is a
    ranking key, never a published score.

    Magnitude matters here, not just presence: a ticker that moved 8% earns
    enrichment ahead of one that moved 1%, because the credit spent on it is
    far more likely to change what the analyst does.
    """
    weights = config.candidate_selection.preliminary_weights
    present = {e.event_type.value for e in events}
    total = sum(
        points
        for name, points in weights.items()
        if name in present and name not in _MAGNITUDE_RULES
    )

    moves = _of_type(events, EventType.PRICE_MOVE)
    top_move = _max_payload(moves, "abs_change_pct")
    if top_move is not None and top_move >= config.thresholds.price_move_large_pct:
        total += weights.get("large_price_move", 0)

    filings = _of_type(events, EventType.FILING)
    top_value = _max_payload(filings, "transaction_value")
    if top_value is not None and top_value >= config.thresholds.transaction_value_idr:
        total += weights.get("large_filing_value", 0)

    return total


_MAGNITUDE_RULES = frozenset({"large_price_move", "large_filing_value"})
"""Preliminary weights keyed on magnitude, not on mere presence of an event."""


def is_score_pinned(events: list[MarketEvent], config: ScoringConfig) -> bool:
    """True when evidence already forces the maximum score.

    A suspended ticker is going to the top of the queue no matter what else is
    true, so paying credits to enrich it buys the analyst nothing.
    """
    if not config.candidate_selection.skip_enrichment_when_score_pinned:
        return False
    if not any(e.event_type is EventType.SUSPENSION for e in events):
        return False
    return config.weight("suspension", "override_score") >= config.maximum_score

"""Normalisation: raw Sectors payloads to canonical :class:`MarketEvent` objects.

This is the boundary of the system. Above it, field names, symbol spellings,
timezone conventions and null-handling are Sectors' business. Below it,
everything is a ``MarketEvent`` with a canonical bare ticker, a WIB-aware
timestamp and a stable fingerprint.

Every function here is total: a malformed record is counted and dropped, never
raised. One bad row out of thirty must not cost an analyst their morning
briefing, and the count is reported so a silent degradation is still visible.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, NamedTuple

from .models import (
    EventType,
    MarketEvent,
    normalize_symbol,
    to_wib,
)


class Normalized(NamedTuple):
    """Events successfully parsed, plus how many records were unusable."""

    events: list[MarketEvent]
    skipped: int

    def __add__(self, other: object) -> Normalized:
        if not isinstance(other, Normalized):
            return NotImplemented
        return Normalized(self.events + other.events, self.skipped + other.skipped)


def _num(value: Any) -> float | None:
    """Best-effort numeric coercion. Booleans are not numbers here."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _text(value: Any, limit: int = 400) -> str:
    if value is None:
        return ""
    out = " ".join(str(value).split())
    return out[:limit]


def _idr(value: float | None) -> str:
    """Render an IDR amount the way an Indonesian analyst reads it."""
    if value is None:
        return "unknown"
    amount = abs(value)
    sign = "-" if value < 0 else ""
    if amount >= 1_000_000_000_000:
        return f"{sign}IDR {amount / 1_000_000_000_000:.2f}T"
    if amount >= 1_000_000_000:
        return f"{sign}IDR {amount / 1_000_000_000:.2f}B"
    if amount >= 1_000_000:
        return f"{sign}IDR {amount / 1_000_000:.1f}M"
    return f"{sign}IDR {amount:,.0f}"


# ---------------------------------------------------------------------------
# Discovery sources
# ---------------------------------------------------------------------------
def normalize_filings(rows: list[dict[str, Any]]) -> Normalized:
    """GET /v2/filings/ rows to FILING events."""
    events: list[MarketEvent] = []
    skipped = 0
    for row in rows:
        symbol = normalize_symbol(row.get("symbol"))
        if not symbol:
            skipped += 1
            continue
        occurred = to_wib(row.get("timestamp"))
        source = row.get("source") or None
        holder = _text(row.get("holder_name"), 120) or "Undisclosed holder"
        direction = _text(row.get("transaction_type"), 20).lower() or "transaction"
        value = _num(row.get("transaction_value"))
        pct = _num(row.get("share_percentage_transaction"))

        # The fingerprint must survive a null source URL, which the schema
        # explicitly permits. Falling back to holder+direction+value keeps two
        # different filings on the same ticker and day distinguishable.
        ref = source or f"filing:{symbol}:{holder}:{direction}:{value}"

        headline = _text(row.get("title"), 200) or f"{holder} {direction} {symbol}"
        bits: list[str] = [f"{holder} {direction}"]
        if pct is not None:
            bits.append(f"{pct:.2f}% of shares")
        if value is not None:
            bits.append(_idr(value))
        before, after = (
            _num(row.get("share_percentage_before")),
            _num(row.get("share_percentage_after")),
        )
        if before is not None and after is not None:
            bits.append(f"ownership {before:.2f}% to {after:.2f}%")

        events.append(
            MarketEvent.build(
                event_type=EventType.FILING,
                symbol=symbol,
                occurred_at=occurred,
                headline=headline,
                detail="; ".join(bits),
                source_ref=ref,
                source_url=source,
                payload={
                    "holder_name": holder,
                    "holder_type": _text(row.get("holder_type"), 40),
                    "transaction_type": direction,
                    "transaction_value": value,
                    "share_percentage_transaction": pct,
                    "share_percentage_before": before,
                    "share_percentage_after": after,
                    "sub_sector": _text(row.get("sub_sector"), 60),
                },
            )
        )
    return Normalized(events, skipped)


def normalize_suspensions(rows: list[dict[str, Any]]) -> Normalized:
    """GET /v2/suspensions/ rows to SUSPENSION events."""
    events: list[MarketEvent] = []
    skipped = 0
    for row in rows:
        symbol = normalize_symbol(row.get("symbol"))
        if not symbol:
            skipped += 1
            continue
        occurred = to_wib(row.get("suspension_date"))
        pdf = row.get("pdf_url") or None
        reason = _text(row.get("reason"), 300) or "Reason not stated in the IDX notice"
        ref = pdf or f"suspension:{symbol}:{row.get('suspension_date')}"
        events.append(
            MarketEvent.build(
                event_type=EventType.SUSPENSION,
                symbol=symbol,
                occurred_at=occurred,
                headline=f"IDX trading suspension: {symbol}",
                detail=reason,
                source_ref=ref,
                source_url=pdf,
                payload={
                    "reason": reason,
                    "suspension_date": _text(row.get("suspension_date"), 20),
                },
            )
        )
    return Normalized(events, skipped)


def normalize_movers(payload: dict[str, Any], period: str = "1d") -> Normalized:
    """GET /v2/companies/top-changes/ to PRICE_MOVE events.

    ``price_change`` is a decimal fraction in the API (``0.05`` == +5%); it is
    converted to percent here once, so no downstream code has to remember.
    """
    events: list[MarketEvent] = []
    skipped = 0
    for classification in ("top_gainers", "top_losers"):
        bucket = payload.get(classification)
        if not isinstance(bucket, dict):
            continue
        rows = bucket.get(period)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                skipped += 1
                continue
            symbol = normalize_symbol(row.get("symbol"))
            change = _num(row.get("price_change"))
            if not symbol or change is None:
                skipped += 1
                continue
            pct = change * 100.0
            close_date = _text(row.get("latest_close_date"), 20)
            occurred = to_wib(close_date or None)
            close_price = _num(row.get("last_close_price"))
            direction = "gained" if pct >= 0 else "fell"
            events.append(
                MarketEvent.build(
                    event_type=EventType.PRICE_MOVE,
                    symbol=symbol,
                    occurred_at=occurred,
                    headline=f"{symbol} {direction} {abs(pct):.2f}% over {period}",
                    detail=(
                        f"Close IDR {close_price:,.0f} on {close_date}"
                        if close_price is not None
                        else f"Close on {close_date}"
                    ),
                    source_ref=f"top-changes:{classification}:{period}:{symbol}:{close_date}",
                    source_url=None,
                    payload={
                        "price_change_pct": pct,
                        "abs_change_pct": abs(pct),
                        "period": period,
                        "classification": classification,
                        "last_close_price": close_price,
                        "latest_close_date": close_date,
                        "company_name": _text(row.get("name"), 120),
                    },
                )
            )
    return Normalized(events, skipped)


# ---------------------------------------------------------------------------
# Enrichment sources
# ---------------------------------------------------------------------------
def normalize_news(rows: list[dict[str, Any]], candidates: set[str]) -> Normalized:
    """GET /v2/news/ rows to NEWS events, one per (article, related ticker).

    An article naming three candidates becomes three events, because evidence
    is correlated per ticker. Articles naming no candidate are dropped rather
    than counted as malformed - a broad-market story is simply not evidence
    about any one name.
    """
    events: list[MarketEvent] = []
    skipped = 0
    for row in rows:
        source = row.get("source") or None
        title = _text(row.get("title"), 220)
        if not title:
            skipped += 1
            continue
        occurred = to_wib(row.get("timestamp"))
        raw_symbols = row.get("symbols")
        symbols = (
            {normalize_symbol(s) for s in raw_symbols if s}
            if isinstance(raw_symbols, list)
            else set()
        )
        related = sorted({s for s in symbols if s and s in candidates})
        if not related:
            continue
        tags = [t for t in (row.get("tags") or []) if isinstance(t, str)]
        for symbol in related:
            ref = source or f"news:{symbol}:{title[:80]}"
            events.append(
                MarketEvent.build(
                    event_type=EventType.NEWS,
                    symbol=symbol,
                    occurred_at=occurred,
                    headline=title,
                    detail=", ".join(tags[:6]) if tags else "",
                    source_ref=ref,
                    source_url=source,
                    payload={"tags": tags, "sub_sector": row.get("sub_sector") or []},
                )
            )
    return Normalized(events, skipped)


def normalize_foreign_flow(
    payload: dict[str, Any],
    symbol: str,
    *,
    min_baseline_days: int = 3,
) -> Normalized:
    """GET /v2/foreign-flow/{symbol}/ to at most one FOREIGN_FLOW event.

    The raw series is not itself evidence - a stock always has foreign flow.
    What is evidence is the most recent day being anomalous against its own
    recent history, so this computes::

        ratio = |latest net flow| / mean(|net flow| over the preceding days)

    Returns no event when there is too little history for that ratio to mean
    anything, or when the baseline is flat zero (an untraded name), rather
    than manufacturing an infinite ratio.
    """
    ticker = normalize_symbol(symbol) or symbol.upper()
    rows = payload.get("data")
    if not isinstance(rows, list) or not rows:
        return Normalized([], 0)

    series: list[tuple[str, float]] = []
    skipped = 0
    for row in rows:
        if not isinstance(row, dict):
            skipped += 1
            continue
        day = _text(row.get("date"), 20)
        flow = _num(row.get("net_foreign_inflow"))
        if not day or flow is None:
            skipped += 1
            continue
        series.append((day, flow))

    if len(series) < min_baseline_days + 1:
        return Normalized([], skipped)

    series.sort(key=lambda item: item[0])
    latest_day, latest_flow = series[-1]
    baseline = [abs(flow) for _, flow in series[:-1]]
    mean_baseline = sum(baseline) / len(baseline)
    if mean_baseline <= 0:
        return Normalized([], skipped)

    ratio = abs(latest_flow) / mean_baseline
    direction = "inflow" if latest_flow >= 0 else "outflow"
    event = MarketEvent.build(
        event_type=EventType.FOREIGN_FLOW,
        symbol=ticker,
        occurred_at=to_wib(latest_day),
        headline=(f"Foreign net {direction} on {ticker} ran {ratio:.1f}x its recent average"),
        detail=(
            f"{_idr(latest_flow)} net foreign {direction} on {latest_day} versus a "
            f"{_idr(mean_baseline)} average over the prior {len(baseline)} trading days"
        ),
        source_ref=f"foreign-flow:{ticker}:{latest_day}",
        source_url=None,
        payload={
            "anomaly_ratio": ratio,
            "net_foreign_inflow": latest_flow,
            "baseline_mean_abs": mean_baseline,
            "baseline_days": len(baseline),
            "date": latest_day,
            "direction": direction,
        },
    )
    return Normalized([event], skipped)


_ACTION_LABELS = {
    "upcoming_dividend": "Upcoming dividend",
    "dividend": "Dividend",
    "stock_split": "Stock split",
    "right_issue": "Rights issue",
    "warrant": "Warrant issuance",
    "bonus": "Bonus shares",
    "agm": "Annual general meeting",
}

_ACTION_DATE_FIELDS = (
    "ex_date",
    "agm_date",
    "date",
    "payment_date",
    "listing_date",
    "effective_date",
)


def normalize_corporate_actions(
    payload: dict[str, Any],
    symbol: str,
    *,
    reference: date,
    window_days: int = 7,
) -> Normalized:
    """GET /v2/company/corporate-actions/{symbol}/ to CORPORATE_ACTION events.

    Only actions dated inside ``[reference, reference + window_days]`` are
    emitted. Historic dividends are not something an analyst needs triaged
    this morning; a rights issue landing on Thursday is.
    """
    ticker = normalize_symbol(symbol) or symbol.upper()
    actions = payload.get("corporate_actions")
    if not isinstance(actions, dict):
        return Normalized([], 0)

    horizon = reference + timedelta(days=window_days)
    events: list[MarketEvent] = []
    skipped = 0

    for kind, entries in actions.items():
        if not isinstance(entries, list):
            continue
        label = _ACTION_LABELS.get(kind, kind.replace("_", " ").title())
        for entry in entries:
            if not isinstance(entry, dict):
                skipped += 1
                continue
            action_day: date | None = None
            field_used = ""
            for field in _ACTION_DATE_FIELDS:
                parsed = to_wib(entry.get(field))
                if parsed is not None:
                    action_day = parsed.date()
                    field_used = field
                    break
            if action_day is None:
                skipped += 1
                continue
            if not (reference <= action_day <= horizon):
                continue

            days_out = (action_day - reference).days
            extras: list[str] = []
            for key in ("dividend_amount", "dividend_yield", "split_ratio", "agm_place"):
                if entry.get(key) is not None:
                    extras.append(f"{key.replace('_', ' ')}: {entry[key]}")
            events.append(
                MarketEvent.build(
                    event_type=EventType.CORPORATE_ACTION,
                    symbol=ticker,
                    occurred_at=to_wib(action_day),
                    headline=f"{label} for {ticker} in {days_out} day(s)",
                    detail="; ".join(extras)
                    if extras
                    else f"{field_used} {action_day.isoformat()}",
                    source_ref=f"corp-action:{ticker}:{kind}:{action_day.isoformat()}",
                    source_url=None,
                    payload={
                        "action_type": kind,
                        "action_date": action_day.isoformat(),
                        "days_until": days_out,
                        "date_field": field_used,
                    },
                )
            )
    return Normalized(events, skipped)


def dedupe_events(events: list[MarketEvent]) -> list[MarketEvent]:
    """Collapse events sharing a fingerprint, preserving first-seen order.

    Within a single run the same evidence can legitimately arrive twice - a
    ticker appearing in both the gainers and losers feed for different periods,
    or a news article returned by two symbol filters.
    """
    seen: set[str] = set()
    out: list[MarketEvent] = []
    for event in events:
        if event.event_id in seen:
            continue
        seen.add(event.event_id)
        out.append(event)
    return out


def latest_timestamp(events: list[MarketEvent]) -> datetime | None:
    stamps = [e.occurred_at for e in events if e.occurred_at is not None]
    return max(stamps) if stamps else None

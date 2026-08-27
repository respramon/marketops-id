"""Shared test fixtures.

Two rules keep this suite honest:

1. **No network, ever.** Live-path tests go through ``respx``, which intercepts
   httpx at the transport layer. A test that would really call
   api.sectors.app fails rather than silently spending credits.
2. **No ambient environment.** Every ``Settings`` object is constructed with
   ``_env_file=None`` and explicit values, so a developer's real ``.env`` (or a
   real API key in CI) cannot change what a test asserts.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from marketops.config import REPO_ROOT, ScoringConfig, Settings, Watchlist, load_scoring
from marketops.models import WIB, EventType, MarketEvent
from marketops.state import StateStore

FIXTURE_DIR = REPO_ROOT / "fixtures" / "sanitized"


@pytest.fixture(scope="session")
def scoring() -> ScoringConfig:
    """The real production scoring config - tests assert against shipped rules."""
    return load_scoring(REPO_ROOT / "config" / "scoring.yml")


@pytest.fixture
def watchlist() -> Watchlist:
    return Watchlist(covered=["BBCA", "BBRI"], covered_bonus=5, muted=[])


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Isolated settings: temp database, temp artifacts, no ambient .env."""
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        SECTORS_API_KEY="test-key-not-a-real-credential",
        DISCORD_WEBHOOK_URL=None,
        GENERIC_WEBHOOK_URL=None,
        MARKETOPS_DB_PATH=str(tmp_path / "state.db"),
        MARKETOPS_ARTIFACT_DIR=str(tmp_path / "artifacts"),
        MARKETOPS_FIXTURE_DIR=str(FIXTURE_DIR),
        MARKETOPS_MAX_API_CREDITS_PER_RUN=25,
        MARKETOPS_MAX_ENRICH_TICKERS=5,
        MARKETOPS_MAX_RETRIES=2,
        MARKETOPS_HTTP_TIMEOUT=1.0,
        MARKETOPS_LOG_LEVEL="WARNING",
    )


@pytest.fixture
def store(tmp_path: Path) -> Iterator[StateStore]:
    state = StateStore(tmp_path / "state.db")
    yield state
    state.close()


@pytest.fixture
def frozen_clock() -> Any:
    """A deterministic clock so run ids and timestamps never flake."""
    moment = datetime(2026, 8, 26, 7, 17, 0, tzinfo=WIB)

    def clock() -> datetime:
        return moment

    return clock


def load_fixture(name: str) -> Any:
    with (FIXTURE_DIR / f"{name}.json").open("r", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="session")
def raw_filings() -> list[dict[str, Any]]:
    return list(load_fixture("filings")["results"])


@pytest.fixture(scope="session")
def raw_suspensions() -> list[dict[str, Any]]:
    return list(load_fixture("suspensions")["results"])


@pytest.fixture(scope="session")
def raw_movers() -> dict[str, Any]:
    return dict(load_fixture("movers"))


@pytest.fixture(scope="session")
def raw_news() -> list[dict[str, Any]]:
    return list(load_fixture("news")["results"])


# ---------------------------------------------------------------------------
# Event builders - concise, explicit evidence for scoring tests
# ---------------------------------------------------------------------------
def make_event(
    event_type: EventType,
    symbol: str = "TEST",
    *,
    when: datetime | None = None,
    source_ref: str | None = None,
    headline: str | None = None,
    **payload: Any,
) -> MarketEvent:
    """Build one canonical event with an explicit payload."""
    return MarketEvent.build(
        event_type=event_type,
        symbol=symbol,
        occurred_at=when if when is not None else datetime(2026, 8, 25, 10, 0, tzinfo=WIB),
        headline=headline or f"{event_type.value} on {symbol}",
        detail="",
        source_ref=source_ref if source_ref is not None else f"{event_type.value}:{symbol}",
        payload=payload,
    )


def filing_event(
    symbol: str = "TEST",
    *,
    pct: float | None = None,
    value: float | None = None,
    holder: str = "Test Holder",
    **kw: Any,
) -> MarketEvent:
    return make_event(
        EventType.FILING,
        symbol,
        holder_name=holder,
        share_percentage_transaction=pct,
        transaction_value=value,
        **kw,
    )


def price_event(symbol: str = "TEST", *, pct: float = 0.0, **kw: Any) -> MarketEvent:
    return make_event(
        EventType.PRICE_MOVE, symbol, abs_change_pct=abs(pct), price_change_pct=pct, **kw
    )


def flow_event(symbol: str = "TEST", *, ratio: float = 1.0, **kw: Any) -> MarketEvent:
    return make_event(
        EventType.FOREIGN_FLOW, symbol, anomaly_ratio=ratio, direction="outflow", **kw
    )


def news_event(
    symbol: str = "TEST", *, headline: str = "Something happened", **kw: Any
) -> MarketEvent:
    return make_event(EventType.NEWS, symbol, headline=headline, **kw)


def action_event(symbol: str = "TEST", *, days: int = 3, **kw: Any) -> MarketEvent:
    return make_event(
        EventType.CORPORATE_ACTION,
        symbol,
        headline=f"Upcoming dividend for {symbol} in {days} day(s)",
        days_until=days,
        action_type="upcoming_dividend",
        **kw,
    )


def suspension_event(
    symbol: str = "TEST", *, reason: str = "Unusual market activity"
) -> MarketEvent:
    return MarketEvent.build(
        event_type=EventType.SUSPENSION,
        symbol=symbol,
        occurred_at=datetime(2026, 8, 25, 9, 0, tzinfo=WIB),
        headline=f"IDX trading suspension: {symbol}",
        detail=reason,
        source_ref=f"suspension:{symbol}:2026-08-25",
        payload={"reason": reason},
    )

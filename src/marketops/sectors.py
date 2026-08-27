"""Typed client for the Sectors Financial API v2.

Everything here is verified against the published OpenAPI document
(https://docs.sectors.app/schema.json, ``openapi: 3.0.3``, ``version: 2.0.0``)
and mirrored in ``docs/sectors-api-map.md``. No endpoint is invented.

Two implementations satisfy :class:`MarketDataSource`:

* :class:`SectorsClient` - real HTTP, with timeout, bounded retry with
  exponential backoff and jitter, rate-limit awareness and credit accounting.
* :class:`FixtureSource` - sanitized historical replay from ``fixtures/``,
  used by tests and by ``marketops run --mode fixture``. It spends no credits
  and touches no network.

CREDIT MODEL (from the API's own documentation)
    2xx        billed at the endpoint's stated cost (most cost 1)
    404        billed 1 credit - the lookup ran, the resource did not exist
    400        free - rejected before any lookup
    401/403    free
    429        free
    5xx        free - a failure on their side is never billed

:class:`CreditLedger` implements exactly that table, which is what makes the
``estimated_api_credits`` figure in every run report trustworthy rather than a
guess.
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Iterable, Sequence
from datetime import date
from types import TracebackType
from typing import Any, Protocol, Self

import httpx

from .config import SECTORS_BASE_URL, Settings

logger = logging.getLogger(__name__)

MAX_PAGE_LIMIT = 30
"""Hard ceiling documented on every paginated Sectors list endpoint."""

DEFAULT_RECORD_LIMIT = MAX_PAGE_LIMIT
"""One bounded discovery page by default; a ``has_next`` gap is reported."""

FOREIGN_FLOW_MAX_DAYS = 90
DAILY_TRANSACTION_MAX_DAYS = 90


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class SectorsError(RuntimeError):
    """Base class for every Sectors client failure."""


class SectorsAuthError(SectorsError):
    """401/403 - the API key is missing, wrong or lacks the required plan."""


class SectorsRateLimitError(SectorsError):
    """429 - rate limit or quota exhausted. Never billed."""


class SectorsBadRequestError(SectorsError):
    """400 - malformed parameters. Never billed, and never worth retrying."""


class SectorsNotFoundError(SectorsError):
    """404 - the addressed symbol/slug does not exist. Billed 1 credit."""


class SectorsUnavailableError(SectorsError):
    """5xx or transport failure that survived every retry."""


class CreditBudgetExceededError(SectorsError):
    """The run's credit budget would be exceeded by the next call.

    Raised *before* the request leaves the process, so the budget is a real
    guard rather than an after-the-fact report.
    """


# ---------------------------------------------------------------------------
# Credit accounting
# ---------------------------------------------------------------------------
class CreditLedger:
    """Tracks estimated API credit consumption against a per-run budget."""

    def __init__(self, budget: int) -> None:
        self.budget = budget
        self.spent = 0
        self.calls = 0
        self.entries: list[tuple[str, int]] = []

    @property
    def remaining(self) -> int:
        return max(0, self.budget - self.spent)

    def can_afford(self, cost: int) -> bool:
        return self.spent + cost <= self.budget

    def reserve(self, label: str, cost: int) -> None:
        """Refuse the call up front when it would break the budget."""
        if not self.can_afford(cost):
            raise CreditBudgetExceededError(
                f"{label} needs {cost} credit(s) but only {self.remaining} of "
                f"{self.budget} remain in this run's budget"
            )

    def charge(self, label: str, cost: int) -> None:
        if cost <= 0:
            return
        self.spent += cost
        self.entries.append((label, cost))

    def record_call(self) -> None:
        self.calls += 1

    @staticmethod
    def cost_for_status(status_code: int, stated_cost: int) -> int:
        """Apply the documented billing table to one HTTP response."""
        if 200 <= status_code < 300:
            return stated_cost
        if status_code == 404:
            return 1
        return 0


# ---------------------------------------------------------------------------
# Source protocol
# ---------------------------------------------------------------------------
class MarketDataSource(Protocol):
    """The surface the pipeline depends on - satisfied by live and fixture."""

    ledger: CreditLedger

    def fetch_filings(self, start: date, end: date, limit: int = ...) -> list[dict[str, Any]]: ...

    def fetch_suspensions(
        self, start: date, end: date, limit: int = ...
    ) -> list[dict[str, Any]]: ...

    def fetch_top_changes(
        self, periods: Sequence[str] = ..., n_stock: int = ...
    ) -> dict[str, Any]: ...

    def fetch_news(
        self, symbols: Sequence[str], start: date, end: date, limit: int = ...
    ) -> list[dict[str, Any]]: ...

    def fetch_foreign_flow(self, symbol: str, start: date, end: date) -> dict[str, Any]: ...

    def fetch_corporate_actions(self, symbol: str) -> dict[str, Any]: ...


# ---------------------------------------------------------------------------
# Live HTTP client
# ---------------------------------------------------------------------------
class SectorsClient:
    """HTTP client for api.sectors.app/v2.

    Reliability posture, all configurable via :class:`Settings`:

    * ``timeout`` seconds on connect/read/write (default 15)
    * up to ``max_retries`` retries (default 3) on 429, 5xx and transport
      errors, with exponential backoff plus full jitter
    * ``Retry-After`` is honoured when the server supplies it
    * 400/401/403/404 are terminal - retrying them only burns wall clock
    """

    def __init__(
        self,
        settings: Settings,
        *,
        ledger: CreditLedger | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        if not settings.has_api_key:
            raise SectorsAuthError(
                "SECTORS_API_KEY is not set. Add it to .env (local) or to "
                "GitHub Secrets (CI), then re-run. Never hard-code it."
            )
        self.settings = settings
        self.ledger = ledger or CreditLedger(settings.max_api_credits_per_run)
        self.warnings: dict[str, list[str]] = {}
        key = settings.sectors_api_key.get_secret_value() if settings.sectors_api_key else ""
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=SECTORS_BASE_URL,
            timeout=httpx.Timeout(settings.http_timeout),
            headers={
                # Verified: securitySchemes.ApiKeyAuth = apiKey in header named
                # "Authorization". The raw key, with no "Bearer " prefix.
                "Authorization": key,
                "Accept": "application/json",
                "User-Agent": "MarketOps-ID/1.0 (Sectors Hackathon 2026)",
            },
        )

    # -- lifecycle ---------------------------------------------------------
    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    # -- core request ------------------------------------------------------
    def _sleep_for(self, attempt: int, retry_after: float | None) -> float:
        """Exponential backoff with full jitter, capped, honouring Retry-After."""
        if retry_after is not None:
            return min(retry_after, 30.0)
        base = min(2.0**attempt, 8.0)
        return random.uniform(0.0, base)  # noqa: S311 - jitter, not cryptography

    @staticmethod
    def _retry_after(response: httpx.Response) -> float | None:
        raw = response.headers.get("Retry-After")
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            return None

    def _request_json(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        stated_cost: int = 1,
        label: str | None = None,
    ) -> object:
        """Issue one budgeted GET, retrying only what is worth retrying."""
        label = label or path
        self.ledger.reserve(label, stated_cost)
        clean = {k: v for k, v in (params or {}).items() if v is not None and v != ""}

        last_error: Exception | None = None
        for attempt in range(self.settings.max_retries + 1):
            try:
                self.ledger.record_call()
                response = self._client.get(path, params=clean)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                # Transport never reached the server, so nothing was billed.
                last_error = exc
                if attempt >= self.settings.max_retries:
                    break
                delay = self._sleep_for(attempt, None)
                logger.warning(
                    "sectors.transport_error path=%s attempt=%d/%d retry_in=%.2fs err=%s",
                    path,
                    attempt + 1,
                    self.settings.max_retries,
                    delay,
                    type(exc).__name__,
                )
                time.sleep(delay)
                continue

            billed = CreditLedger.cost_for_status(response.status_code, stated_cost)
            self.ledger.charge(label, billed)
            status = response.status_code

            if 200 <= status < 300:
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise SectorsError(f"{path} returned {status} with a non-JSON body") from exc
                return payload

            if status == 400:
                raise SectorsBadRequestError(f"{path} rejected the request: {_snippet(response)}")
            if status in (401, 403):
                raise SectorsAuthError(
                    f"{path} returned {status}. The API key is missing, invalid, "
                    "or the account lacks the Insider plan."
                )
            if status == 404:
                raise SectorsNotFoundError(f"{path} found no such resource: {_snippet(response)}")

            if status == 429 or status >= 500:
                last_error = (
                    SectorsRateLimitError(f"{path} returned 429")
                    if status == 429
                    else (SectorsUnavailableError(f"{path} returned {status}"))
                )
                if attempt >= self.settings.max_retries:
                    break
                delay = self._sleep_for(attempt, self._retry_after(response))
                logger.warning(
                    "sectors.retryable path=%s status=%d attempt=%d/%d retry_in=%.2fs",
                    path,
                    status,
                    attempt + 1,
                    self.settings.max_retries,
                    delay,
                )
                time.sleep(delay)
                continue

            raise SectorsError(f"{path} returned unexpected status {status}")

        if isinstance(last_error, SectorsRateLimitError):
            raise SectorsRateLimitError(
                f"{path} still rate-limited after {self.settings.max_retries} retries"
            ) from last_error
        raise SectorsUnavailableError(
            f"{path} unavailable after {self.settings.max_retries} retries: "
            f"{type(last_error).__name__ if last_error else 'unknown'}"
        ) from last_error

    def _get_object(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        stated_cost: int = 1,
        label: str | None = None,
    ) -> dict[str, Any]:
        """Request a JSON object and reject schema drift explicitly."""
        payload = self._request_json(
            path,
            params=params,
            stated_cost=stated_cost,
            label=label,
        )
        if not isinstance(payload, dict):
            raise SectorsError(f"{path} returned {type(payload).__name__}, expected a JSON object")
        return payload

    def _get_array(
        self,
        path: str,
        *,
        stated_cost: int = 1,
        label: str | None = None,
    ) -> list[Any]:
        """Request a top-level JSON array, used by helper-list diagnostics."""
        payload = self._request_json(path, stated_cost=stated_cost, label=label)
        if not isinstance(payload, list):
            raise SectorsError(f"{path} returned {type(payload).__name__}, expected a JSON array")
        return payload

    def _warn(self, label: str, message: str) -> None:
        self.warnings.setdefault(label, []).append(message)
        logger.warning("sectors.source_gap source=%s detail=%s", label, message)

    def pop_warning(self, label: str) -> str | None:
        """Return and clear accumulated non-fatal gaps for a pipeline source."""
        messages = self.warnings.pop(label, [])
        return "; ".join(messages) if messages else None

    def _fetch_paginated(
        self,
        path: str,
        *,
        params: dict[str, Any],
        label: str,
        max_records: int,
    ) -> list[dict[str, Any]]:
        """Read bounded pages without silently hiding `has_next` evidence.

        Pagination competes with selective enrichment inside the same hard
        credit ledger. If the row cap or credit cap is reached after at least
        one valid page, those rows are retained and the source is marked with
        a gap so the overall run becomes PARTIAL rather than a false all-clear.
        """
        target = max(1, max_records)
        offset = 0
        collected: list[dict[str, Any]] = []

        while len(collected) < target:
            page_size = min(MAX_PAGE_LIMIT, target - len(collected))
            page_params = {**params, "limit": page_size, "offset": offset}
            payload = self._get_object(
                path,
                params=page_params,
                stated_cost=1,
                label=label,
            )
            rows, pagination, malformed = _page(payload, path)
            collected.extend(rows)
            if malformed:
                self._warn(label, f"{malformed} malformed result row(s) dropped")

            has_next = pagination.get("has_next")
            next_offset = pagination.get("next_offset")
            if not isinstance(has_next, bool):
                raise SectorsError(f"{path} returned invalid pagination.has_next={has_next!r}")
            if not has_next:
                break
            if len(collected) >= target:
                self._warn(label, f"record cap {target} reached while API has another page")
                break
            if not isinstance(next_offset, int) or next_offset <= offset:
                raise SectorsError(
                    f"{path} returned invalid pagination.next_offset={next_offset!r}"
                )
            if not self.ledger.can_afford(1):
                self._warn(
                    label,
                    "pagination stopped before the next page because the API credit "
                    "budget is exhausted",
                )
                break
            offset = next_offset

        return collected[:target]

    # -- discovery endpoints ----------------------------------------------
    def fetch_filings(
        self, start: date, end: date, limit: int = DEFAULT_RECORD_LIMIT
    ) -> list[dict[str, Any]]:
        """GET /v2/filings/ - insider and major-shareholder transactions. 1 credit."""
        return self._fetch_paginated(
            "/v2/filings/",
            params={
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            label="filings",
            max_records=limit,
        )

    def fetch_suspensions(
        self, start: date, end: date, limit: int = DEFAULT_RECORD_LIMIT
    ) -> list[dict[str, Any]]:
        """GET /v2/suspensions/ - IDX trading halts. 1 credit."""
        return self._fetch_paginated(
            "/v2/suspensions/",
            params={
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            label="suspensions",
            max_records=limit,
        )

    def fetch_top_changes(
        self, periods: Sequence[str] = ("1d",), n_stock: int = 10
    ) -> dict[str, Any]:
        """GET /v2/companies/top-changes/ - top gainers and losers.

        Billing note that matters: this endpoint costs **1 credit per
        classification x period combination**. Its default (2 classifications
        x 5 periods) would silently cost 10 credits every run. MarketOps pins
        ``periods=1d`` and both classifications, so a discovery sweep costs 2.
        """
        classifications = ("top_gainers", "top_losers")
        cost = len(classifications) * len(periods)
        return self._get_object(
            "/v2/companies/top-changes/",
            params={
                "classifications": ",".join(classifications),
                "periods": ",".join(periods),
                "n_stock": min(max(n_stock, 1), 10),
            },
            stated_cost=cost,
            label="movers",
        )

    # -- enrichment endpoints ----------------------------------------------
    def fetch_news(
        self,
        symbols: Sequence[str],
        start: date,
        end: date,
        limit: int = DEFAULT_RECORD_LIMIT,
    ) -> list[dict[str, Any]]:
        """GET /v2/news/ - IDX news for a batch of symbols. 1 credit total.

        ``symbols`` is comma-separated server-side, so news for the whole
        candidate universe costs one credit rather than one per ticker.
        """
        if not symbols:
            return []
        return self._fetch_paginated(
            "/v2/news/",
            params={
                "symbols": ",".join(symbols),
                "start": start.isoformat(),
                "end": end.isoformat(),
                "extension": "idx",
            },
            label="news",
            max_records=limit,
        )

    def fetch_foreign_flow(self, symbol: str, start: date, end: date) -> dict[str, Any]:
        """GET /v2/foreign-flow/{symbol}/ - daily net foreign inflow. 1 credit/ticker."""
        span = (end - start).days
        if span > FOREIGN_FLOW_MAX_DAYS:
            raise SectorsBadRequestError(
                f"foreign-flow window is {span} days; the endpoint allows at most "
                f"{FOREIGN_FLOW_MAX_DAYS}"
            )
        return self._get_object(
            f"/v2/foreign-flow/{symbol}/",
            params={"start": start.isoformat(), "end": end.isoformat()},
            stated_cost=1,
            label=f"foreign_flow:{symbol}",
        )

    def fetch_corporate_actions(self, symbol: str) -> dict[str, Any]:
        """GET /v2/company/corporate-actions/{symbol}/ - 1 credit/ticker."""
        return self._get_object(
            f"/v2/company/corporate-actions/{symbol}/",
            stated_cost=1,
            label=f"corporate_actions:{symbol}",
        )

    # -- diagnostics -------------------------------------------------------
    def ping(self) -> bool:
        """Cheapest possible authenticated probe, for ``marketops doctor``.

        ``/v2/subsectors/`` is a static helper list costing 1 credit. A 401/403
        proves the key is bad; anything else proves it authenticates.
        """
        self._get_array("/v2/subsectors/", stated_cost=1, label="doctor:ping")
        return True


def _snippet(response: httpx.Response) -> str:
    """A short, safe excerpt of an error body - never headers, never the key."""
    try:
        return str(response.json())[:200]
    except ValueError:
        return response.text[:200]


def _page(payload: dict[str, Any], path: str) -> tuple[list[dict[str, Any]], dict[str, Any], int]:
    """Validate a v2 paginated envelope and retain valid rows."""
    rows = payload.get("results")
    if not isinstance(rows, list):
        raise SectorsError(f"{path} response is missing a list-valued 'results' field")
    pagination = payload.get("pagination")
    if not isinstance(pagination, dict):
        raise SectorsError(f"{path} response is missing an object-valued 'pagination' field")
    valid = [row for row in rows if isinstance(row, dict)]
    return valid, pagination, len(rows) - len(valid)


def _results(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Read fixture envelopes with the same strict shape as live v2 pages."""
    rows, _, _ = _page(payload, "fixture")
    return rows


# ---------------------------------------------------------------------------
# Fixture replay
# ---------------------------------------------------------------------------
class FixtureSource:
    """Deterministic replay of sanitized historical payloads.

    Reads the same JSON shapes the live API returns, so every downstream stage
    is exercised identically.

    **No credits are actually spent** - nothing here touches the network. The
    ledger is still charged with what the equivalent live call *would* cost, for
    two reasons: it exercises the budget guard in tests, and it lets a fixture
    demo show the real credit arithmetic. Every artifact a fixture run produces
    is stamped ``mode: fixture`` and carries the SANITIZED REPLAY banner, so the
    figure can never be mistaken for live spend.

    ``as_of`` anchors the replay to the historical date the fixtures describe,
    which is what keeps date-relative logic (the corporate-action window)
    correct no matter when the replay is run.
    """

    def __init__(self, fixture_dir: Any, *, budget: int = 10_000) -> None:
        from pathlib import Path

        self.fixture_dir = Path(fixture_dir)
        self.ledger = CreditLedger(budget)
        self._cache: dict[str, Any] = {}

    @property
    def as_of(self) -> date | None:
        """The historical date this fixture set represents, if declared."""
        try:
            meta = self._load("_meta")
        except FileNotFoundError:
            return None
        raw = meta.get("as_of") if isinstance(meta, dict) else None
        if not raw:
            return None
        try:
            return date.fromisoformat(str(raw))
        except ValueError:
            return None

    def _load(self, name: str) -> Any:
        if name not in self._cache:
            import json

            path = self.fixture_dir / f"{name}.json"
            if not path.exists():
                raise FileNotFoundError(f"Fixture not found: {path}")
            with path.open("r", encoding="utf-8") as handle:
                self._cache[name] = json.load(handle)
        return self._cache[name]

    def _simulate(self, label: str, cost: int) -> None:
        """Charge what the equivalent live call would have cost."""
        self.ledger.reserve(label, cost)
        self.ledger.record_call()
        self.ledger.charge(label, cost)

    def fetch_filings(
        self, start: date, end: date, limit: int = DEFAULT_RECORD_LIMIT
    ) -> list[dict[str, Any]]:
        self._simulate("filings", 1)
        return _results(self._load("filings"))[:limit]

    def fetch_suspensions(
        self, start: date, end: date, limit: int = DEFAULT_RECORD_LIMIT
    ) -> list[dict[str, Any]]:
        self._simulate("suspensions", 1)
        return _results(self._load("suspensions"))[:limit]

    def fetch_top_changes(
        self, periods: Sequence[str] = ("1d",), n_stock: int = 10
    ) -> dict[str, Any]:
        # Mirrors live billing: 2 classifications x len(periods).
        self._simulate("movers", 2 * len(periods))
        data = self._load("movers")
        return data if isinstance(data, dict) else {}

    def fetch_news(
        self,
        symbols: Sequence[str],
        start: date,
        end: date,
        limit: int = DEFAULT_RECORD_LIMIT,
    ) -> list[dict[str, Any]]:
        wanted = {s.upper().removesuffix(".JK") for s in symbols}
        if not wanted:
            return []
        self._simulate("news", 1)
        rows = _results(self._load("news"))
        keep: list[dict[str, Any]] = []
        for row in rows:
            tickers = {str(s).upper().removesuffix(".JK") for s in (row.get("symbols") or []) if s}
            if tickers & wanted:
                keep.append(row)
        return keep[:limit]

    def fetch_foreign_flow(self, symbol: str, start: date, end: date) -> dict[str, Any]:
        key = symbol.upper().removesuffix(".JK")
        self._simulate(f"foreign_flow:{key}", 1)
        table = self._load("foreign_flow")
        entry = table.get(key) if isinstance(table, dict) else None
        if entry is None or not isinstance(entry, dict):
            raise SectorsNotFoundError(f"Symbol '{key}' not found in fixture foreign-flow data")
        return dict(entry)

    def fetch_corporate_actions(self, symbol: str) -> dict[str, Any]:
        key = symbol.upper().removesuffix(".JK")
        self._simulate(f"corporate_actions:{key}", 1)
        table = self._load("corporate_actions")
        entry = table.get(key) if isinstance(table, dict) else None
        if entry is None or not isinstance(entry, dict):
            raise SectorsNotFoundError(f"Symbol '{key}' not found in fixture corporate actions")
        return dict(entry)


def chunked(items: Iterable[str], size: int) -> list[list[str]]:
    """Split an iterable into fixed-size batches (used for symbol batching)."""
    batch: list[str] = []
    out: list[list[str]] = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            out.append(batch)
            batch = []
    if batch:
        out.append(batch)
    return out

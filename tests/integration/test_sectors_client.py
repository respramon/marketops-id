"""Live HTTP path against a mocked Sectors API.

``respx`` intercepts httpx at the transport layer, so these tests exercise the
real client - real URL building, real header, real retry loop, real credit
accounting - without a network call or a spent credit.

The credit assertions matter as much as the happy path: the API's published
billing table says 400/401/403/429/5xx are free and 404 costs 1, and the run
report's ``estimated_api_credits`` is only trustworthy if the client implements
that table exactly.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from typing import Any

import httpx
import pytest
import respx

from marketops.config import Settings
from marketops.sectors import (
    CreditBudgetExceededError,
    CreditLedger,
    SectorsAuthError,
    SectorsBadRequestError,
    SectorsClient,
    SectorsError,
    SectorsNotFoundError,
    SectorsRateLimitError,
    SectorsUnavailableError,
    chunked,
)

BASE = "https://api.sectors.app"
START = date(2026, 8, 22)
END = date(2026, 8, 25)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Collapse backoff so the retry tests run fast but still retry for real."""
    monkeypatch.setattr("marketops.sectors.time.sleep", lambda _seconds: None)


@pytest.fixture
def client(settings: Settings) -> Iterator[SectorsClient]:
    with SectorsClient(settings) as instance:
        yield instance


def page(
    rows: list[dict[str, Any]],
    *,
    offset: int = 0,
    has_next: bool = False,
    next_offset: int | None = None,
) -> dict[str, Any]:
    return {
        "results": rows,
        "pagination": {
            "total_count": len(rows),
            "showing": len(rows),
            "limit": 30,
            "offset": offset,
            "has_next": has_next,
            "has_previous": False,
            "next_offset": next_offset,
            "previous_offset": None,
        },
    }


class TestAuthAndConstruction:
    def test_missing_key_is_refused_at_construction(self, settings: Settings) -> None:
        blind = settings.model_copy(update={"sectors_api_key": None})
        with pytest.raises(SectorsAuthError, match="SECTORS_API_KEY"):
            SectorsClient(blind)

    @respx.mock
    def test_key_is_sent_raw_in_the_authorization_header(self, client: SectorsClient) -> None:
        """Verified from the OpenAPI securityScheme: apiKey in header
        'Authorization' - no 'Bearer ' prefix."""
        route = respx.get(f"{BASE}/v2/suspensions/").mock(
            return_value=httpx.Response(200, json=page([]))
        )
        client.fetch_suspensions(START, END)
        sent = route.calls[0].request
        assert sent.headers["Authorization"] == "test-key-not-a-real-credential"
        assert not sent.headers["Authorization"].startswith("Bearer")

    @respx.mock
    def test_error_messages_never_leak_the_key(self, client: SectorsClient) -> None:
        respx.get(f"{BASE}/v2/suspensions/").mock(return_value=httpx.Response(403))
        with pytest.raises(SectorsAuthError) as excinfo:
            client.fetch_suspensions(START, END)
        assert "test-key-not-a-real-credential" not in str(excinfo.value)


class TestHappyPath:
    @respx.mock
    def test_filings(self, client: SectorsClient) -> None:
        route = respx.get(f"{BASE}/v2/filings/").mock(
            return_value=httpx.Response(200, json=page([{"symbol": "BBCA.JK"}]))
        )
        rows = client.fetch_filings(START, END)
        assert rows == [{"symbol": "BBCA.JK"}]
        params = route.calls[0].request.url.params
        assert params["start"] == "2026-08-22"
        assert params["end"] == "2026-08-25"
        assert params["limit"] == "30"
        assert client.ledger.spent == 1

    @respx.mock
    def test_suspensions(self, client: SectorsClient) -> None:
        respx.get(f"{BASE}/v2/suspensions/").mock(
            return_value=httpx.Response(200, json=page([{"symbol": "FLMC.JK"}]))
        )
        assert client.fetch_suspensions(START, END)[0]["symbol"] == "FLMC.JK"
        assert client.ledger.spent == 1

    @respx.mock
    def test_top_changes_pins_one_period_and_both_classifications(
        self, client: SectorsClient
    ) -> None:
        """The endpoint bills per classification x period. Its own default
        (2 x 5) would cost 10 credits a run; we pin 1d and pay 2."""
        route = respx.get(f"{BASE}/v2/companies/top-changes/").mock(
            return_value=httpx.Response(200, json={"top_gainers": {}, "top_losers": {}})
        )
        client.fetch_top_changes(periods=("1d",))
        params = route.calls[0].request.url.params
        assert params["periods"] == "1d"
        assert params["classifications"] == "top_gainers,top_losers"
        assert client.ledger.spent == 2

    @respx.mock
    def test_top_changes_cost_scales_with_periods(self, client: SectorsClient) -> None:
        respx.get(f"{BASE}/v2/companies/top-changes/").mock(
            return_value=httpx.Response(200, json={"top_gainers": {}, "top_losers": {}})
        )
        client.fetch_top_changes(periods=("1d", "7d", "30d"))
        assert client.ledger.spent == 6

    @respx.mock
    def test_news_batches_every_symbol_into_one_credit(self, client: SectorsClient) -> None:
        route = respx.get(f"{BASE}/v2/news/").mock(
            return_value=httpx.Response(200, json=page([{"title": "x", "source": "u"}]))
        )
        client.fetch_news(["ANTM", "MDKA", "BBCA", "ADRO", "ASII"], START, END)
        assert route.calls[0].request.url.params["symbols"] == "ANTM,MDKA,BBCA,ADRO,ASII"
        assert client.ledger.spent == 1

    @respx.mock
    def test_news_with_no_symbols_makes_no_call(self, client: SectorsClient) -> None:
        route = respx.get(f"{BASE}/v2/news/")
        assert client.fetch_news([], START, END) == []
        assert route.call_count == 0
        assert client.ledger.spent == 0

    @respx.mock
    def test_foreign_flow(self, client: SectorsClient) -> None:
        respx.get(f"{BASE}/v2/foreign-flow/MDKA/").mock(
            return_value=httpx.Response(
                200,
                json={"symbol": "MDKA.JK", "start": "2026-08-11", "end": "2026-08-25", "data": []},
            )
        )
        assert client.fetch_foreign_flow("MDKA", START, END)["symbol"] == "MDKA.JK"
        assert client.ledger.spent == 1

    def test_foreign_flow_window_over_90_days_is_refused_locally(
        self, client: SectorsClient
    ) -> None:
        """Refuse before spending a credit on a request the API will reject."""
        with pytest.raises(SectorsBadRequestError, match="90"):
            client.fetch_foreign_flow("MDKA", date(2026, 1, 1), date(2026, 8, 25))
        assert client.ledger.spent == 0

    @respx.mock
    def test_corporate_actions(self, client: SectorsClient) -> None:
        respx.get(f"{BASE}/v2/company/corporate-actions/BBCA/").mock(
            return_value=httpx.Response(
                200, json={"symbol": "BBCA.JK", "corporate_actions": {"agm": []}}
            )
        )
        assert client.fetch_corporate_actions("BBCA")["symbol"] == "BBCA.JK"

    @respx.mock
    def test_ping_probe(self, client: SectorsClient) -> None:
        respx.get(f"{BASE}/v2/subsectors/").mock(return_value=httpx.Response(200, json=[]))
        assert client.ping() is True

    @respx.mock
    def test_none_params_are_dropped_from_the_query(self, client: SectorsClient) -> None:
        route = respx.get(f"{BASE}/v2/company/corporate-actions/BBCA/").mock(
            return_value=httpx.Response(200, json={"corporate_actions": {}})
        )
        client.fetch_corporate_actions("BBCA")
        assert route.calls[0].request.url.params == httpx.QueryParams()


class TestRetryBehaviour:
    @respx.mock
    def test_429_then_success(self, client: SectorsClient) -> None:
        route = respx.get(f"{BASE}/v2/filings/").mock(
            side_effect=[
                httpx.Response(429, json={"error": "RATE_LIMIT_EXCEEDED"}),
                httpx.Response(200, json=page([{"symbol": "BBCA.JK"}])),
            ]
        )
        rows = client.fetch_filings(START, END)
        assert len(rows) == 1
        assert route.call_count == 2
        # 429 is free; only the successful call is billed.
        assert client.ledger.spent == 1

    @respx.mock
    def test_retry_after_header_is_honoured(
        self, settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        slept: list[float] = []
        monkeypatch.setattr("marketops.sectors.time.sleep", slept.append)
        respx.get(f"{BASE}/v2/filings/").mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "2.5"}),
                httpx.Response(200, json=page([])),
            ]
        )
        with SectorsClient(settings) as client:
            client.fetch_filings(START, END)
        assert slept == [2.5]

    @respx.mock
    def test_malformed_retry_after_falls_back_to_jitter(self, client: SectorsClient) -> None:
        respx.get(f"{BASE}/v2/filings/").mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "soon"}),
                httpx.Response(200, json=page([])),
            ]
        )
        assert client.fetch_filings(START, END) == []

    @respx.mock
    def test_500_repeatedly_exhausts_retries(self, client: SectorsClient) -> None:
        route = respx.get(f"{BASE}/v2/filings/").mock(return_value=httpx.Response(500))
        with pytest.raises(SectorsUnavailableError):
            client.fetch_filings(START, END)
        assert route.call_count == 3  # initial + max_retries(2)
        assert client.ledger.spent == 0  # 5xx is never billed

    @respx.mock
    def test_persistent_429_raises_rate_limit_not_unavailable(self, client: SectorsClient) -> None:
        respx.get(f"{BASE}/v2/filings/").mock(return_value=httpx.Response(429))
        with pytest.raises(SectorsRateLimitError):
            client.fetch_filings(START, END)
        assert client.ledger.spent == 0

    @respx.mock
    def test_timeout_is_retried_then_surfaced(self, client: SectorsClient) -> None:
        route = respx.get(f"{BASE}/v2/filings/").mock(
            side_effect=httpx.ReadTimeout("read timed out")
        )
        with pytest.raises(SectorsUnavailableError):
            client.fetch_filings(START, END)
        assert route.call_count == 3
        assert client.ledger.spent == 0

    @respx.mock
    def test_timeout_then_recovery(self, client: SectorsClient) -> None:
        respx.get(f"{BASE}/v2/filings/").mock(
            side_effect=[httpx.ConnectTimeout("boom"), httpx.Response(200, json=page([]))]
        )
        assert client.fetch_filings(START, END) == []

    @respx.mock
    def test_transport_error_is_retried(self, client: SectorsClient) -> None:
        respx.get(f"{BASE}/v2/filings/").mock(
            side_effect=[httpx.ConnectError("no route"), httpx.Response(200, json=page([]))]
        )
        assert client.fetch_filings(START, END) == []

    @respx.mock
    @pytest.mark.parametrize("status", [400, 401, 403, 404])
    def test_terminal_statuses_are_never_retried(self, client: SectorsClient, status: int) -> None:
        """Retrying a client error only burns wall clock before the analyst
        gets their queue."""
        route = respx.get(f"{BASE}/v2/filings/").mock(return_value=httpx.Response(status))
        with pytest.raises(SectorsError):
            client.fetch_filings(START, END)
        assert route.call_count == 1


class TestErrorMapping:
    @respx.mock
    def test_400_is_free_and_specific(self, client: SectorsClient) -> None:
        respx.get(f"{BASE}/v2/filings/").mock(
            return_value=httpx.Response(400, json={"error": "Invalid filter parameters."})
        )
        with pytest.raises(SectorsBadRequestError):
            client.fetch_filings(START, END)
        assert client.ledger.spent == 0

    @respx.mock
    @pytest.mark.parametrize("status", [401, 403])
    def test_auth_statuses_are_free(self, client: SectorsClient, status: int) -> None:
        respx.get(f"{BASE}/v2/filings/").mock(return_value=httpx.Response(status))
        with pytest.raises(SectorsAuthError):
            client.fetch_filings(START, END)
        assert client.ledger.spent == 0

    @respx.mock
    def test_404_costs_one_credit_as_documented(self, client: SectorsClient) -> None:
        """'You are billed for the lookup, not the result.'"""
        respx.get(f"{BASE}/v2/foreign-flow/XYZA/").mock(
            return_value=httpx.Response(404, json={"error": "Symbol 'XYZA' not found."})
        )
        with pytest.raises(SectorsNotFoundError):
            client.fetch_foreign_flow("XYZA", START, END)
        assert client.ledger.spent == 1

    @respx.mock
    def test_non_json_success_body_is_an_error(self, client: SectorsClient) -> None:
        respx.get(f"{BASE}/v2/filings/").mock(
            return_value=httpx.Response(200, text="<html>maintenance</html>")
        )
        with pytest.raises(SectorsError, match="non-JSON"):
            client.fetch_filings(START, END)

    @respx.mock
    def test_json_array_where_an_object_was_expected(self, client: SectorsClient) -> None:
        respx.get(f"{BASE}/v2/filings/").mock(return_value=httpx.Response(200, json=[1, 2, 3]))
        with pytest.raises(SectorsError, match="expected a JSON object"):
            client.fetch_filings(START, END)

    @respx.mock
    def test_missing_results_key_is_a_schema_error(self, client: SectorsClient) -> None:
        """A shape change must be named as a partial-source failure, not hidden."""
        respx.get(f"{BASE}/v2/filings/").mock(
            return_value=httpx.Response(200, json={"unexpected": "shape"})
        )
        with pytest.raises(SectorsError, match="results"):
            client.fetch_filings(START, END)

    @respx.mock
    def test_non_dict_rows_inside_results_are_dropped(self, client: SectorsClient) -> None:
        respx.get(f"{BASE}/v2/filings/").mock(
            return_value=httpx.Response(
                200,
                json=page([{"symbol": "A"}, "junk", None]),
            )
        )
        assert client.fetch_filings(START, END) == [{"symbol": "A"}]

    @respx.mock
    def test_missing_pagination_is_a_schema_error(self, client: SectorsClient) -> None:
        respx.get(f"{BASE}/v2/filings/").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        with pytest.raises(SectorsError, match="pagination"):
            client.fetch_filings(START, END)


class TestPagination:
    @respx.mock
    def test_client_fetches_the_next_page_when_explicitly_requested(
        self, client: SectorsClient
    ) -> None:
        route = respx.get(f"{BASE}/v2/filings/").mock(
            side_effect=[
                httpx.Response(
                    200,
                    json=page(
                        [{"symbol": "AAAA"}],
                        has_next=True,
                        next_offset=30,
                    ),
                ),
                httpx.Response(200, json=page([{"symbol": "BBBB"}], offset=30)),
            ]
        )
        assert client.fetch_filings(START, END, limit=60) == [
            {"symbol": "AAAA"},
            {"symbol": "BBBB"},
        ]
        assert route.call_count == 2
        assert route.calls[1].request.url.params["offset"] == "30"
        assert client.ledger.spent == 2

    @respx.mock
    def test_default_page_cap_is_reported_as_a_nonfatal_gap(self, client: SectorsClient) -> None:
        respx.get(f"{BASE}/v2/filings/").mock(
            return_value=httpx.Response(
                200,
                json=page(
                    [{"symbol": f"T{i:03d}"} for i in range(30)],
                    has_next=True,
                    next_offset=30,
                ),
            )
        )
        client.fetch_filings(START, END)
        warning = client.pop_warning("filings")
        assert warning is not None and "record cap 30" in warning

    @respx.mock
    def test_unexpected_status_is_surfaced(self, client: SectorsClient) -> None:
        respx.get(f"{BASE}/v2/filings/").mock(return_value=httpx.Response(302))
        with pytest.raises(SectorsError, match="unexpected status"):
            client.fetch_filings(START, END)


class TestCreditBudget:
    @respx.mock
    def test_budget_refuses_the_call_before_it_is_sent(self, settings: Settings) -> None:
        """The guard must be preventative, not a post-hoc report."""
        tight = settings.model_copy(update={"max_api_credits_per_run": 1})
        route = respx.get(f"{BASE}/v2/companies/top-changes/")
        with (
            SectorsClient(tight) as client,
            pytest.raises(CreditBudgetExceededError, match="2 credit"),
        ):
            client.fetch_top_changes(periods=("1d",))
        assert route.call_count == 0

    @respx.mock
    def test_budget_stops_a_run_partway(self, settings: Settings) -> None:
        tight = settings.model_copy(update={"max_api_credits_per_run": 2})
        respx.get(f"{BASE}/v2/filings/").mock(return_value=httpx.Response(200, json=page([])))
        respx.get(f"{BASE}/v2/suspensions/").mock(return_value=httpx.Response(200, json=page([])))
        with SectorsClient(tight) as client:
            client.fetch_filings(START, END)
            client.fetch_suspensions(START, END)
            assert client.ledger.remaining == 0
            with pytest.raises(CreditBudgetExceededError):
                client.fetch_news(["ANTM"], START, END)

    def test_ledger_billing_table_matches_the_documentation(self) -> None:
        assert CreditLedger.cost_for_status(200, 3) == 3
        assert CreditLedger.cost_for_status(204, 1) == 1
        assert CreditLedger.cost_for_status(404, 5) == 1
        for free in (400, 401, 403, 429, 500, 502, 503):
            assert CreditLedger.cost_for_status(free, 5) == 0

    def test_ledger_tracks_entries_and_remaining(self) -> None:
        ledger = CreditLedger(budget=10)
        ledger.charge("filings", 1)
        ledger.charge("movers", 2)
        ledger.charge("free", 0)
        assert ledger.spent == 3
        assert ledger.remaining == 7
        assert ledger.entries == [("filings", 1), ("movers", 2)]
        assert ledger.can_afford(7) is True
        assert ledger.can_afford(8) is False


class TestHelpers:
    def test_chunked_splits_evenly_and_keeps_the_remainder(self) -> None:
        assert chunked(["a", "b", "c", "d", "e"], 2) == [["a", "b"], ["c", "d"], ["e"]]

    def test_chunked_of_nothing(self) -> None:
        assert chunked([], 3) == []

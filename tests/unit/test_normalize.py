"""Normalisation and the canonical model.

The normalisation boundary has one hard requirement beyond correctness: it must
be **total**. A malformed row is counted and dropped; it never raises, because
one bad record out of thirty must not cost an analyst their morning briefing.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pytest

from marketops.models import (
    WIB,
    EventType,
    MarketEvent,
    Priority,
    fingerprint,
    normalize_symbol,
    safe_source_url,
    to_wib,
)
from marketops.normalize import (
    dedupe_events,
    latest_timestamp,
    normalize_corporate_actions,
    normalize_filings,
    normalize_foreign_flow,
    normalize_movers,
    normalize_news,
    normalize_suspensions,
)


class TestSymbolNormalisation:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("BBCA", "BBCA"),
            ("BBCA.JK", "BBCA"),
            ("bbca.jk", "BBCA"),
            ("  bbca.JK  ", "BBCA"),
            ("BBCA.jk", "BBCA"),
            ("", None),
            ("   ", None),
            (None, None),
        ],
    )
    def test_canonical_form(self, raw: Any, expected: str | None) -> None:
        assert normalize_symbol(raw) == expected

    def test_response_and_query_spellings_converge(self) -> None:
        """The API returns BBCA.JK but accepts BBCA - correlation needs one form."""
        assert normalize_symbol("BBCA.JK") == normalize_symbol("bbca")


class TestTimezoneNormalisation:
    def test_naive_timestamp_is_treated_as_wib(self) -> None:
        parsed = to_wib("2026-07-09T14:29:39")
        assert parsed is not None
        assert parsed.tzinfo == WIB
        assert parsed.hour == 14

    def test_plain_date_becomes_midnight_wib(self) -> None:
        parsed = to_wib("2026-07-03")
        assert parsed == datetime(2026, 7, 3, 0, 0, tzinfo=WIB)

    def test_utc_is_converted_to_wib(self) -> None:
        parsed = to_wib("2026-07-09T00:00:00Z")
        assert parsed is not None
        assert parsed.hour == 7  # UTC+7

    def test_date_object_is_accepted(self) -> None:
        assert to_wib(date(2026, 7, 3)) == datetime(2026, 7, 3, tzinfo=WIB)

    @pytest.mark.parametrize("bad", [None, "", "   ", "not-a-date", "2026-13-45", "??"])
    def test_unparseable_values_yield_none_rather_than_raising(self, bad: Any) -> None:
        assert to_wib(bad) is None


class TestSourceUrlSafety:
    @pytest.mark.parametrize(
        "url",
        [
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "/relative/path",
            "https://",
            "https://idx.co.id/notice.pdf\nmalicious",
        ],
    )
    def test_active_or_non_absolute_urls_are_rejected(self, url: str) -> None:
        assert safe_source_url(url) is None

    def test_http_and_https_provenance_urls_are_preserved(self) -> None:
        assert safe_source_url("https://www.idx.co.id/notice.pdf") == (
            "https://www.idx.co.id/notice.pdf"
        )
        assert safe_source_url("http://localhost/source") == "http://localhost/source"

    def test_event_builder_applies_url_validation(self) -> None:
        event = MarketEvent.build(
            event_type=EventType.NEWS,
            symbol="TEST",
            occurred_at=None,
            headline="Untrusted source",
            source_ref="malicious-ref",
            source_url="javascript:alert(1)",
        )
        assert event.source_url is None


class TestFingerprint:
    def test_same_event_yields_the_same_id(self) -> None:
        a = fingerprint(EventType.FILING, "BBCA", to_wib("2026-08-24T10:00:00"), "http://x/1.pdf")
        b = fingerprint(EventType.FILING, "BBCA", to_wib("2026-08-24T10:00:00"), "http://x/1.pdf")
        assert a == b

    def test_it_is_a_sha256_hex_digest(self) -> None:
        value = fingerprint(EventType.NEWS, "BBCA", None, "ref")
        assert len(value) == 64
        assert set(value) <= set("0123456789abcdef")

    @pytest.mark.parametrize(
        ("field", "changed"),
        [
            ("type", (EventType.NEWS, "BBCA", "2026-08-24T10:00:00", "ref")),
            ("symbol", (EventType.FILING, "BBRI", "2026-08-24T10:00:00", "ref")),
            ("time", (EventType.FILING, "BBCA", "2026-08-25T10:00:00", "ref")),
            ("source", (EventType.FILING, "BBCA", "2026-08-24T10:00:00", "other")),
        ],
    )
    def test_any_material_change_yields_a_different_id(
        self, field: str, changed: tuple[Any, ...]
    ) -> None:
        base = fingerprint(EventType.FILING, "BBCA", to_wib("2026-08-24T10:00:00"), "ref")
        other = fingerprint(changed[0], changed[1], to_wib(changed[2]), changed[3])
        assert base != other, f"{field} must change the fingerprint"

    def test_symbol_case_does_not_change_the_id(self) -> None:
        upper = fingerprint(EventType.FILING, "BBCA", None, "ref")
        lower = fingerprint(EventType.FILING, "bbca", None, "ref")
        assert upper == lower

    def test_equivalent_timestamps_in_different_zones_match(self) -> None:
        """07:00 WIB and 00:00Z are the same instant and the same event."""
        wib = fingerprint(EventType.NEWS, "BBCA", to_wib("2026-08-24T07:00:00"), "ref")
        utc = fingerprint(EventType.NEWS, "BBCA", to_wib("2026-08-24T00:00:00Z"), "ref")
        assert wib == utc

    def test_missing_timestamp_is_stable(self) -> None:
        assert fingerprint(EventType.NEWS, "X", None, "r") == fingerprint(
            EventType.NEWS, "X", None, "r"
        )


class TestFilingNormalisation:
    def test_maps_the_documented_fields(self, raw_filings: list[dict[str, Any]]) -> None:
        result = normalize_filings(raw_filings)
        antm = next(e for e in result.events if e.symbol == "ANTM")
        assert antm.event_type is EventType.FILING
        assert antm.payload["share_percentage_transaction"] == 1.85
        assert antm.payload["transaction_value"] == 412537600000.0
        assert antm.payload["holder_name"] == "Dana Investasi Nusantara"
        assert antm.source_url is not None
        assert antm.source_url.endswith(".pdf")

    def test_malformed_row_is_counted_not_raised(self, raw_filings: list[dict[str, Any]]) -> None:
        result = normalize_filings(raw_filings)
        assert result.skipped == 1
        assert len(result.events) == 2

    def test_symbols_are_canonicalised(self, raw_filings: list[dict[str, Any]]) -> None:
        result = normalize_filings(raw_filings)
        assert all(not e.symbol.endswith(".JK") for e in result.events)

    def test_null_source_url_still_produces_a_usable_event(self) -> None:
        """The schema permits a null source; the fingerprint must still work."""
        rows = [
            {
                "symbol": "BBCA.JK",
                "timestamp": "2026-08-24T10:00:00",
                "source": None,
                "holder_name": "Someone",
                "transaction_type": "buy",
                "transaction_value": 1.0,
                "share_percentage_transaction": 0.1,
            }
        ]
        result = normalize_filings(rows)
        assert len(result.events) == 1
        assert result.events[0].source_url is None
        assert result.events[0].event_id

    def test_two_filings_with_null_source_stay_distinct(self) -> None:
        rows = [
            {
                "symbol": "BBCA.JK",
                "timestamp": "2026-08-24T10:00:00",
                "source": None,
                "holder_name": "Holder A",
                "transaction_type": "buy",
                "transaction_value": 10.0,
                "share_percentage_transaction": 0.1,
            },
            {
                "symbol": "BBCA.JK",
                "timestamp": "2026-08-24T10:00:00",
                "source": None,
                "holder_name": "Holder B",
                "transaction_type": "sell",
                "transaction_value": 20.0,
                "share_percentage_transaction": 0.2,
            },
        ]
        result = normalize_filings(rows)
        assert len({e.event_id for e in result.events}) == 2

    def test_empty_input(self) -> None:
        assert normalize_filings([]) == ([], 0)


class TestSuspensionNormalisation:
    def test_maps_the_documented_fields(self, raw_suspensions: list[dict[str, Any]]) -> None:
        result = normalize_suspensions(raw_suspensions)
        event = result.events[0]
        assert event.symbol == "FLMC"
        assert event.event_type is EventType.SUSPENSION
        assert event.source_url is not None
        assert "idx.co.id" in event.source_url
        assert "signifikan" in event.detail

    def test_null_reason_gets_an_honest_placeholder(self) -> None:
        rows = [
            {"symbol": "XXXX.JK", "suspension_date": "2026-08-25", "reason": None, "pdf_url": None}
        ]
        result = normalize_suspensions(rows)
        assert "not stated" in result.events[0].detail.lower()

    def test_row_without_symbol_is_skipped(self) -> None:
        result = normalize_suspensions([{"symbol": None, "suspension_date": "2026-08-25"}])
        assert result.events == []
        assert result.skipped == 1


class TestMoverNormalisation:
    def test_decimal_change_is_converted_to_percent_once(self, raw_movers: dict[str, Any]) -> None:
        result = normalize_movers(raw_movers)
        antm = next(e for e in result.events if e.symbol == "ANTM")
        assert antm.payload["price_change_pct"] == pytest.approx(8.42)
        assert antm.payload["abs_change_pct"] == pytest.approx(8.42)

    def test_losers_keep_their_sign_but_expose_magnitude(self, raw_movers: dict[str, Any]) -> None:
        result = normalize_movers(raw_movers)
        mdka = next(e for e in result.events if e.symbol == "MDKA")
        assert mdka.payload["price_change_pct"] < 0
        assert mdka.payload["abs_change_pct"] == pytest.approx(7.61)

    def test_both_classifications_are_read(self, raw_movers: dict[str, Any]) -> None:
        result = normalize_movers(raw_movers)
        symbols = {e.symbol for e in result.events}
        assert {"ANTM", "BBCA", "INDF", "MDKA", "ASII"} <= symbols

    def test_absent_period_yields_nothing(self, raw_movers: dict[str, Any]) -> None:
        assert normalize_movers(raw_movers, period="365d").events == []

    def test_malformed_shapes_are_tolerated(self) -> None:
        payload = {"top_gainers": {"1d": ["not-a-dict", {"symbol": None}]}, "top_losers": None}
        result = normalize_movers(payload)
        assert result.events == []
        assert result.skipped == 2

    def test_company_name_is_preserved(self, raw_movers: dict[str, Any]) -> None:
        result = normalize_movers(raw_movers)
        antm = next(e for e in result.events if e.symbol == "ANTM")
        assert "Aneka Tambang" in antm.payload["company_name"]


class TestNewsNormalisation:
    def test_one_event_per_related_candidate(self, raw_news: list[dict[str, Any]]) -> None:
        result = normalize_news(raw_news, {"ANTM", "MDKA"})
        assert {e.symbol for e in result.events} == {"ANTM", "MDKA"}

    def test_article_naming_no_candidate_is_ignored_not_counted_as_bad(
        self, raw_news: list[dict[str, Any]]
    ) -> None:
        result = normalize_news(raw_news, {"ANTM"})
        assert len(result.events) == 1
        assert result.skipped == 0

    def test_multi_symbol_article_fans_out(self) -> None:
        rows = [
            {
                "title": "Two miners respond to the same regulation",
                "source": "https://example.test/a",
                "timestamp": "2026-08-25T08:00:00",
                "symbols": ["ANTM.JK", "MDKA.JK", "PSAB.JK"],
                "tags": [],
            }
        ]
        result = normalize_news(rows, {"ANTM", "MDKA"})
        assert {e.symbol for e in result.events} == {"ANTM", "MDKA"}
        assert len({e.event_id for e in result.events}) == 2

    def test_untitled_article_is_skipped(self) -> None:
        result = normalize_news([{"title": "", "symbols": ["ANTM.JK"]}], {"ANTM"})
        assert result.events == []
        assert result.skipped == 1

    def test_empty_candidate_set_matches_nothing(self, raw_news: list[dict[str, Any]]) -> None:
        assert normalize_news(raw_news, set()).events == []


class TestForeignFlowNormalisation:
    @staticmethod
    def _series(values: list[int]) -> dict[str, Any]:
        return {
            "symbol": "TEST.JK",
            "data": [
                {"date": f"2026-08-{10 + i:02d}", "net_foreign_inflow": v}
                for i, v in enumerate(values)
            ],
        }

    def test_anomaly_ratio_is_latest_over_baseline_mean(self) -> None:
        payload = self._series([1_000, -1_000, 1_000, -1_000, 4_000])
        result = normalize_foreign_flow(payload, "TEST")
        assert result.events[0].payload["anomaly_ratio"] == pytest.approx(4.0)

    def test_too_little_history_yields_no_event(self) -> None:
        payload = self._series([1_000, 9_000])
        assert normalize_foreign_flow(payload, "TEST", min_baseline_days=3).events == []

    def test_flat_zero_baseline_does_not_manufacture_infinity(self) -> None:
        payload = self._series([0, 0, 0, 0, 5_000])
        assert normalize_foreign_flow(payload, "TEST").events == []

    def test_direction_is_recorded(self) -> None:
        out = normalize_foreign_flow(self._series([100, -100, 100, -100, -900]), "TEST")
        assert out.events[0].payload["direction"] == "outflow"
        inn = normalize_foreign_flow(self._series([100, -100, 100, -100, 900]), "TEST")
        assert inn.events[0].payload["direction"] == "inflow"

    def test_series_is_sorted_before_the_latest_is_chosen(self) -> None:
        """Rows arriving out of order must not change which day is 'latest'."""
        payload = self._series([1_000, -1_000, 1_000, -1_000, 4_000])
        shuffled = {"symbol": "TEST.JK", "data": list(reversed(payload["data"]))}
        assert normalize_foreign_flow(shuffled, "TEST").events[0].payload[
            "anomaly_ratio"
        ] == pytest.approx(4.0)

    def test_empty_or_malformed_payload(self) -> None:
        assert normalize_foreign_flow({}, "TEST").events == []
        assert normalize_foreign_flow({"data": "nope"}, "TEST").events == []

    def test_bad_rows_are_counted(self) -> None:
        payload = {
            "data": [
                {"date": "2026-08-10", "net_foreign_inflow": 100},
                {"date": None, "net_foreign_inflow": 100},
                "garbage",
            ]
        }
        result = normalize_foreign_flow(payload, "TEST")
        assert result.skipped == 2


class TestCorporateActionNormalisation:
    REFERENCE = date(2026, 8, 25)

    def test_only_actions_inside_the_window_are_emitted(self) -> None:
        payload = {
            "corporate_actions": {
                "upcoming_dividend": [{"ex_date": "2026-08-29", "dividend_amount": 114}],
                "dividend": [{"ex_date": "2025-12-03", "dividend_amount": 55}],
            }
        }
        result = normalize_corporate_actions(payload, "BBCA", reference=self.REFERENCE)
        assert len(result.events) == 1
        assert result.events[0].payload["days_until"] == 4

    def test_window_boundaries_are_inclusive(self) -> None:
        payload = {
            "corporate_actions": {
                "agm": [
                    {"agm_date": "2026-08-25"},  # today
                    {"agm_date": "2026-09-01"},  # exactly +7
                    {"agm_date": "2026-09-02"},  # +8, outside
                ]
            }
        }
        result = normalize_corporate_actions(payload, "X", reference=self.REFERENCE)
        assert sorted(e.payload["days_until"] for e in result.events) == [0, 7]

    def test_null_action_lists_are_tolerated(self) -> None:
        payload = {"corporate_actions": {"bonus": None, "warrant": None, "dividend": []}}
        assert normalize_corporate_actions(payload, "X", reference=self.REFERENCE).events == []

    def test_entry_without_any_date_is_skipped(self) -> None:
        payload = {"corporate_actions": {"agm": [{"agm_place": "Jakarta"}]}}
        result = normalize_corporate_actions(payload, "X", reference=self.REFERENCE)
        assert result.events == []
        assert result.skipped == 1

    def test_missing_corporate_actions_key(self) -> None:
        assert normalize_corporate_actions({}, "X", reference=self.REFERENCE).events == []


class TestDedupeAndHelpers:
    def test_dedupe_preserves_first_seen_order(self) -> None:
        a = MarketEvent.build(
            event_type=EventType.NEWS, symbol="A", occurred_at=None, headline="a", source_ref="1"
        )
        b = MarketEvent.build(
            event_type=EventType.NEWS, symbol="B", occurred_at=None, headline="b", source_ref="2"
        )
        assert [e.symbol for e in dedupe_events([a, b, a, b, a])] == ["A", "B"]

    def test_latest_timestamp_ignores_nulls(self) -> None:
        events = [
            MarketEvent.build(
                event_type=EventType.NEWS,
                symbol="A",
                occurred_at=None,
                headline="x",
                source_ref="1",
            ),
            MarketEvent.build(
                event_type=EventType.NEWS,
                symbol="A",
                occurred_at=to_wib("2026-08-25T10:00:00"),
                headline="y",
                source_ref="2",
            ),
        ]
        latest = latest_timestamp(events)
        assert latest is not None
        assert latest.day == 25

    def test_latest_timestamp_of_nothing(self) -> None:
        assert latest_timestamp([]) is None

    def test_events_are_immutable(self) -> None:
        event = MarketEvent.build(
            event_type=EventType.NEWS, symbol="A", occurred_at=None, headline="x", source_ref="1"
        )
        with pytest.raises(Exception, match=r"frozen|immutable"):
            event.symbol = "B"  # type: ignore[misc]

    def test_priority_labels_are_human_readable(self) -> None:
        assert Priority.P1.label == "Urgent Review"
        assert Priority.P2.label == "Review"
        assert Priority.P3.label == "Monitor"

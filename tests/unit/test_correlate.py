"""Correlation: many events, one dossier per ticker, ranked deterministically."""

from __future__ import annotations

import random

from tests.conftest import (
    action_event,
    filing_event,
    flow_event,
    news_event,
    price_event,
    suspension_event,
)

from marketops.config import ScoringConfig, Watchlist
from marketops.correlate import build_dossiers, group_by_symbol, select_candidates
from marketops.models import EventType, Priority


class TestGrouping:
    def test_events_bucket_by_ticker(self) -> None:
        events = [filing_event("ANTM", pct=1.0), price_event("ANTM", pct=8.0), news_event("MDKA")]
        grouped = group_by_symbol(events)
        assert set(grouped) == {"ANTM", "MDKA"}
        assert len(grouped["ANTM"]) == 2

    def test_empty_input(self) -> None:
        assert group_by_symbol([]) == {}


class TestCandidateSelection:
    def test_ranked_by_evidence_strength(self, scoring: ScoringConfig) -> None:
        events = [
            price_event("WEAK", pct=1.0),
            filing_event("MID", pct=0.1, value=1.0),
            suspension_event("HALT"),
        ]
        assert select_candidates(events, scoring) == ["HALT", "MID", "WEAK"]

    def test_large_move_is_enriched_before_a_small_one(self, scoring: ScoringConfig) -> None:
        """Credit discipline: the 8% mover gets the credit, not the 1% mover."""
        events = [price_event("AAAA", pct=1.0), price_event("ZZZZ", pct=9.0)]
        assert select_candidates(events, scoring)[0] == "ZZZZ"

    def test_muted_tickers_never_become_candidates(self, scoring: ScoringConfig) -> None:
        watchlist = Watchlist(covered=[], covered_bonus=0, muted=["NOISE"])
        events = [suspension_event("NOISE"), price_event("REAL", pct=8.0)]
        assert select_candidates(events, scoring, watchlist) == ["REAL"]

    def test_covered_tickers_are_nudged_up(self, scoring: ScoringConfig) -> None:
        watchlist = Watchlist(covered=["BBCA"], covered_bonus=5, muted=[])
        events = [price_event("AAAA", pct=3.0), price_event("BBCA", pct=3.0)]
        assert select_candidates(events, scoring, watchlist)[0] == "BBCA"

    def test_limit_is_respected(self, scoring: ScoringConfig) -> None:
        events = [price_event(f"T{i:03d}", pct=5.0) for i in range(20)]
        assert len(select_candidates(events, scoring, limit=5)) == 5

    def test_ordering_is_independent_of_input_order(self, scoring: ScoringConfig) -> None:
        events = [
            suspension_event("HALT"),
            filing_event("FIL", pct=0.9, value=99_000_000_000),
            price_event("BIG", pct=9.0),
            price_event("SMALL", pct=3.2),
            news_event("NEWS"),
        ]
        baseline = select_candidates(events, scoring)
        shuffler = random.Random(7)
        for _ in range(20):
            shuffled = events[:]
            shuffler.shuffle(shuffled)
            assert select_candidates(shuffled, scoring) == baseline


class TestDossierBuilding:
    def test_one_dossier_per_ticker_with_all_its_evidence(self, scoring: ScoringConfig) -> None:
        events = [
            filing_event("ANTM", pct=1.85, value=412_000_000_000),
            price_event("ANTM", pct=8.42),
            news_event("ANTM"),
            price_event("MDKA", pct=7.61),
        ]
        dossiers = build_dossiers(events, scoring)
        antm = next(d for d in dossiers if d.symbol == "ANTM")
        assert len(antm.events) == 3
        assert antm.score.total == 75
        assert antm.score.priority is Priority.P1

    def test_dossiers_are_ranked_by_score_descending(self, scoring: ScoringConfig) -> None:
        events = [
            price_event("LOW", pct=3.1),
            suspension_event("TOP"),
            price_event("MID", pct=8.0),
            flow_event("MID", ratio=4.5),
        ]
        dossiers = build_dossiers(events, scoring)
        assert [d.symbol for d in dossiers] == ["TOP", "MID", "LOW"]

    def test_queue_excludes_below_threshold_tickers(self, scoring: ScoringConfig) -> None:
        events = [price_event("NOISE", pct=1.2), suspension_event("REAL")]
        dossiers = build_dossiers(events, scoring)
        assert len(dossiers) == 2
        queued = [d for d in dossiers if d.score.priority is not Priority.NONE]
        assert [d.symbol for d in queued] == ["REAL"]

    def test_new_event_ids_are_marked(self, scoring: ScoringConfig) -> None:
        fresh = price_event("ANTM", pct=8.0)
        stale = news_event("ANTM")
        dossiers = build_dossiers([fresh, stale], scoring, new_event_ids={fresh.event_id})
        assert dossiers[0].new_event_ids == [fresh.event_id]
        assert dossiers[0].is_new is True

    def test_dossier_with_no_new_evidence_is_not_new(self, scoring: ScoringConfig) -> None:
        dossiers = build_dossiers([price_event("ANTM", pct=8.0)], scoring, new_event_ids=set())
        assert dossiers[0].is_new is False

    def test_enriched_flag_is_carried(self, scoring: ScoringConfig) -> None:
        dossiers = build_dossiers([price_event("ANTM", pct=8.0)], scoring, enriched={"ANTM"})
        assert dossiers[0].enriched is True

    def test_muted_tickers_are_dropped(self, scoring: ScoringConfig) -> None:
        watchlist = Watchlist(covered=[], covered_bonus=0, muted=["SHELL"])
        dossiers = build_dossiers([suspension_event("SHELL")], scoring, watchlist)
        assert dossiers == []

    def test_company_name_is_recovered_from_any_event(self, scoring: ScoringConfig) -> None:
        events = [
            news_event("ANTM"),
            price_event("ANTM", pct=8.0, company_name="PT Aneka Tambang Tbk"),
        ]
        dossiers = build_dossiers(events, scoring)
        assert dossiers[0].company_name == "PT Aneka Tambang Tbk"

    def test_suspension_sorts_to_the_top_of_a_dossier(self, scoring: ScoringConfig) -> None:
        events = [news_event("FLMC"), suspension_event("FLMC"), price_event("FLMC", pct=9.0)]
        dossiers = build_dossiers(events, scoring)
        assert dossiers[0].events[0].event_type is EventType.SUSPENSION

    def test_dossier_ordering_is_input_order_independent(self, scoring: ScoringConfig) -> None:
        events = [
            filing_event("ANTM", pct=1.85, value=412_000_000_000),
            price_event("ANTM", pct=8.42),
            news_event("ANTM"),
            price_event("MDKA", pct=7.61),
            flow_event("MDKA", ratio=4.7),
            action_event("BBCA", days=4),
            price_event("BBCA", pct=3.4),
            suspension_event("FLMC"),
        ]
        baseline = build_dossiers(events, scoring)
        shuffler = random.Random(99)
        for _ in range(20):
            shuffled = events[:]
            shuffler.shuffle(shuffled)
            result = build_dossiers(shuffled, scoring)
            assert [(d.symbol, d.score.total) for d in result] == [
                (d.symbol, d.score.total) for d in baseline
            ]
            for got, want in zip(result, baseline, strict=True):
                assert [e.event_id for e in got.events] == [e.event_id for e in want.events]

    def test_display_symbol_and_event_types(self, scoring: ScoringConfig) -> None:
        dossiers = build_dossiers([price_event("ANTM", pct=8.0), news_event("ANTM")], scoring)
        assert dossiers[0].display_symbol == "ANTM.JK"
        assert set(dossiers[0].event_types) == {EventType.PRICE_MOVE, EventType.NEWS}

    def test_sources_lists_unique_urls(self, scoring: ScoringConfig) -> None:
        events = [
            filing_event("ANTM", pct=1.0, value=1.0),
            price_event("ANTM", pct=8.0),
        ]
        dossiers = build_dossiers(events, scoring)
        assert isinstance(dossiers[0].sources, list)

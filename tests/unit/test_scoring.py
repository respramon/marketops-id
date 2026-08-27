"""Research Attention Score.

The score decides what a human looks at first, so its contract is stricter
than "produces a number": it must be deterministic, order-independent, capped,
and fully explained by its own components.
"""

from __future__ import annotations

import random

import pytest
from tests.conftest import (
    action_event,
    filing_event,
    flow_event,
    news_event,
    price_event,
    suspension_event,
)

from marketops.config import ScoringConfig, Watchlist
from marketops.models import EventType, Priority
from marketops.scoring import is_score_pinned, preliminary_score, priority_for, score_events


class TestSuspensionOverride:
    def test_suspension_pins_score_to_maximum(self, scoring: ScoringConfig) -> None:
        result = score_events("FLMC", [suspension_event("FLMC")], scoring)
        assert result.total == 100
        assert result.priority is Priority.P1

    def test_suspension_overrides_all_other_evidence(self, scoring: ScoringConfig) -> None:
        """A halted stock cannot be scored *down* by weak surrounding evidence."""
        events = [
            suspension_event("FLMC"),
            price_event("FLMC", pct=0.1),
            news_event("FLMC"),
        ]
        result = score_events("FLMC", events, scoring)
        assert result.total == 100
        assert len(result.components) == 1
        assert result.components[0].event_type is EventType.SUSPENSION

    def test_override_reason_is_stated(self, scoring: ScoringConfig) -> None:
        result = score_events("FLMC", [suspension_event("FLMC")], scoring)
        assert result.override_reason
        assert "halted" in result.override_reason.lower()

    def test_suspension_reason_is_carried_into_the_explanation(
        self, scoring: ScoringConfig
    ) -> None:
        result = score_events(
            "FLMC", [suspension_event("FLMC", reason="Penurunan harga kumulatif")], scoring
        )
        assert "Penurunan harga kumulatif" in result.components[0].evidence


class TestFilingWeights:
    def test_bare_filing_scores_base_only(self, scoring: ScoringConfig) -> None:
        result = score_events("TEST", [filing_event(pct=0.1, value=1_000_000)], scoring)
        assert result.total == scoring.weight("filing", "base") == 25

    def test_ownership_threshold_is_inclusive(self, scoring: ScoringConfig) -> None:
        """0.5% exactly must count - thresholds are documented as >=."""
        at = score_events("TEST", [filing_event(pct=0.5, value=0)], scoring)
        just_below = score_events("TEST", [filing_event(pct=0.49, value=0)], scoring)
        assert at.total == 35
        assert just_below.total == 25

    def test_transaction_value_threshold_is_inclusive(self, scoring: ScoringConfig) -> None:
        at = score_events("TEST", [filing_event(pct=0, value=25_000_000_000)], scoring)
        below = score_events("TEST", [filing_event(pct=0, value=24_999_999_999)], scoring)
        assert at.total == 35
        assert below.total == 25

    def test_both_filing_bonuses_stack(self, scoring: ScoringConfig) -> None:
        result = score_events("TEST", [filing_event(pct=1.85, value=412_000_000_000)], scoring)
        assert result.total == 45

    def test_multiple_filings_take_the_strongest_not_the_sum(self, scoring: ScoringConfig) -> None:
        """Three filings must not triple the base - that would let a noisy
        ticker outrank a genuinely material one."""
        events = [
            filing_event(pct=0.6, value=30_000_000_000, source_ref="a"),
            filing_event(pct=0.7, value=40_000_000_000, source_ref="b"),
            filing_event(pct=0.8, value=50_000_000_000, source_ref="c"),
        ]
        result = score_events("TEST", events, scoring)
        assert result.total == 45

    def test_none_valued_filing_fields_do_not_crash(self, scoring: ScoringConfig) -> None:
        result = score_events("TEST", [filing_event(pct=None, value=None)], scoring)
        assert result.total == 25


class TestPriceMoveTiers:
    @pytest.mark.parametrize(
        ("pct", "expected"),
        [(0.0, 0), (2.99, 0), (3.0, 10), (6.99, 10), (7.0, 20), (8.42, 20), (40.0, 20)],
    )
    def test_tier_boundaries(self, scoring: ScoringConfig, pct: float, expected: int) -> None:
        result = score_events("TEST", [price_event(pct=pct)], scoring)
        assert result.total == expected

    def test_tiers_are_exclusive_not_cumulative(self, scoring: ScoringConfig) -> None:
        """A 9% move scores 20, never 10+20=30."""
        assert score_events("TEST", [price_event(pct=9.0)], scoring).total == 20

    def test_negative_moves_use_absolute_magnitude(self, scoring: ScoringConfig) -> None:
        down = score_events("TEST", [price_event(pct=-7.6)], scoring)
        assert down.total == 20

    def test_strongest_move_wins_across_events(self, scoring: ScoringConfig) -> None:
        events = [price_event(pct=1.0, source_ref="a"), price_event(pct=8.0, source_ref="b")]
        assert score_events("TEST", events, scoring).total == 20


class TestForeignFlowTiers:
    @pytest.mark.parametrize(
        ("ratio", "expected"),
        [(1.0, 0), (1.99, 0), (2.0, 15), (3.99, 15), (4.0, 20), (12.0, 20)],
    )
    def test_tier_boundaries(self, scoring: ScoringConfig, ratio: float, expected: int) -> None:
        result = score_events("TEST", [flow_event(ratio=ratio)], scoring)
        assert result.total == expected


class TestOtherWeights:
    def test_news_presence(self, scoring: ScoringConfig) -> None:
        assert score_events("TEST", [news_event()], scoring).total == 10

    def test_many_articles_score_once(self, scoring: ScoringConfig) -> None:
        events = [news_event(headline=f"story {i}", source_ref=f"s{i}") for i in range(5)]
        assert score_events("TEST", events, scoring).total == 10

    def test_corporate_action(self, scoring: ScoringConfig) -> None:
        assert score_events("TEST", [action_event(days=4)], scoring).total == 10

    def test_soonest_action_is_the_one_explained(self, scoring: ScoringConfig) -> None:
        events = [action_event(days=6, source_ref="a"), action_event(days=1, source_ref="b")]
        result = score_events("TEST", events, scoring)
        assert "1 day" in result.components[0].evidence


class TestWatchlistBonus:
    def test_covered_ticker_gains_the_bonus(
        self, scoring: ScoringConfig, watchlist: Watchlist
    ) -> None:
        result = score_events("BBCA", [price_event("BBCA", pct=3.4)], scoring, watchlist)
        assert result.total == 15

    def test_uncovered_ticker_does_not(self, scoring: ScoringConfig, watchlist: Watchlist) -> None:
        result = score_events("ANTM", [price_event("ANTM", pct=3.4)], scoring, watchlist)
        assert result.total == 10

    def test_bonus_never_applies_to_a_zero_score(
        self, scoring: ScoringConfig, watchlist: Watchlist
    ) -> None:
        """Coverage must not manufacture a queue entry out of nothing."""
        result = score_events("BBCA", [price_event("BBCA", pct=0.4)], scoring, watchlist)
        assert result.total == 0
        assert result.priority is Priority.NONE


class TestCapAndBands:
    def test_score_is_capped_at_the_configured_maximum(self, scoring: ScoringConfig) -> None:
        events = [
            filing_event(pct=5.0, value=900_000_000_000),
            price_event(pct=30.0),
            flow_event(ratio=20.0),
            news_event(),
            action_event(days=1),
        ]
        result = score_events("TEST", events, scoring)
        assert result.total == 100
        assert result.capped is True
        assert sum(c.points for c in result.components) > 100

    @pytest.mark.parametrize(
        ("total", "band"),
        [
            (0, Priority.NONE),
            (24, Priority.NONE),
            (25, Priority.P3),
            (49, Priority.P3),
            (50, Priority.P2),
            (74, Priority.P2),
            (75, Priority.P1),
            (100, Priority.P1),
        ],
    )
    def test_priority_band_boundaries(
        self, scoring: ScoringConfig, total: int, band: Priority
    ) -> None:
        assert priority_for(total, scoring) is band


class TestDeterminism:
    def test_event_order_does_not_change_the_score(self, scoring: ScoringConfig) -> None:
        events = [
            filing_event(pct=1.85, value=412_000_000_000),
            price_event(pct=8.42),
            flow_event(ratio=4.7),
            news_event(),
            action_event(days=2),
        ]
        baseline = score_events("TEST", events, scoring)
        shuffler = random.Random(20260826)
        for _ in range(25):
            shuffled = events[:]
            shuffler.shuffle(shuffled)
            result = score_events("TEST", shuffled, scoring)
            assert result.total == baseline.total
            assert [c.label for c in result.components] == [c.label for c in baseline.components]

    def test_repeated_scoring_is_identical(self, scoring: ScoringConfig) -> None:
        events = [filing_event(pct=0.9, value=99_000_000_000), price_event(pct=4.0)]
        first = score_events("TEST", events, scoring)
        second = score_events("TEST", events, scoring)
        assert first.model_dump() == second.model_dump()

    def test_components_sum_to_the_total_when_uncapped(self, scoring: ScoringConfig) -> None:
        """Explainability contract: the arithmetic on screen must be checkable."""
        events = [filing_event(pct=1.0, value=30_000_000_000), price_event(pct=4.0), news_event()]
        result = score_events("TEST", events, scoring)
        assert sum(c.points for c in result.components) == result.total
        assert result.capped is False

    def test_no_evidence_scores_zero(self, scoring: ScoringConfig) -> None:
        result = score_events("TEST", [], scoring)
        assert result.total == 0
        assert result.priority is Priority.NONE
        assert result.components == []


class TestPreliminaryRanking:
    def test_suspension_outranks_everything(self, scoring: ScoringConfig) -> None:
        assert preliminary_score([suspension_event()], scoring) == 100

    def test_magnitude_lifts_a_large_move_above_a_small_one(self, scoring: ScoringConfig) -> None:
        """Enrichment credits should go to the 8% mover, not the 1% one."""
        big = preliminary_score([price_event(pct=8.0)], scoring)
        small = preliminary_score([price_event(pct=1.0)], scoring)
        assert big > small

    def test_large_filing_value_lifts_ranking(self, scoring: ScoringConfig) -> None:
        big = preliminary_score([filing_event(value=400_000_000_000)], scoring)
        small = preliminary_score([filing_event(value=1_000_000)], scoring)
        assert big > small

    def test_pinned_when_suspended(self, scoring: ScoringConfig) -> None:
        assert is_score_pinned([suspension_event()], scoring) is True

    def test_not_pinned_without_a_suspension(self, scoring: ScoringConfig) -> None:
        assert is_score_pinned([price_event(pct=9.0)], scoring) is False

    def test_pinning_can_be_disabled_by_config(self, scoring: ScoringConfig) -> None:
        relaxed = scoring.model_copy(deep=True)
        relaxed.candidate_selection.skip_enrichment_when_score_pinned = False
        assert is_score_pinned([suspension_event()], relaxed) is False

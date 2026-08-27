"""The unattended pipeline.

    Scheduled trigger
      -> discovery      (filings, suspensions, movers)
      -> normalisation  (canonical events)
      -> candidates     (rank by discovery evidence)
      -> enrichment     (news, foreign flow, corporate actions - budgeted)
      -> correlation    (one dossier per ticker)
      -> scoring        (Research Attention Score)
      -> deduplication  (fingerprints seen in earlier runs)
      -> ranking        (P1 / P2 / P3)
      -> notification   (only genuinely new evidence)
      -> persistence    (state + artifacts + audit log)

Two invariants hold throughout:

**Fail-soft.** Every source is attempted independently. If foreign-flow
enrichment is down but filings, suspensions, movers and news are healthy, the
analyst still gets their queue - clearly marked ``PARTIAL``, naming exactly
what is missing. The system never reports "all clear" while a source it wanted
was silently unavailable.

**Budget-guarded.** Discovery is cheap and broad; enrichment is expensive and
narrow. The credit ledger refuses a call *before* it is sent once the run's
budget would be exceeded, so a bad config can waste time but never a thousand
credits.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .config import ScoringConfig, Settings, Watchlist, load_scoring, load_watchlist
from .correlate import build_dossiers, select_candidates
from .models import (
    MarketEvent,
    RunMode,
    RunReport,
    RunStatus,
    SourceName,
    SourceReport,
    SourceState,
    now_wib,
)
from .normalize import (
    Normalized,
    dedupe_events,
    normalize_corporate_actions,
    normalize_filings,
    normalize_foreign_flow,
    normalize_movers,
    normalize_news,
    normalize_suspensions,
)
from .notify import dispatch, notifiable
from .scoring import is_score_pinned
from .sectors import (
    CreditBudgetExceededError,
    FixtureSource,
    MarketDataSource,
    SectorsClient,
)
from .state import StateStore

logger = logging.getLogger(__name__)

DISCOVERY_SOURCES = (SourceName.FILINGS, SourceName.SUSPENSIONS, SourceName.MOVERS)


def make_run_id(when: datetime) -> str:
    """Readable, sortable, collision-resistant run identifier."""
    return f"run-{when.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"


class Pipeline:
    """One unattended MarketOps execution."""

    def __init__(
        self,
        *,
        settings: Settings,
        source: MarketDataSource,
        store: StateStore,
        scoring: ScoringConfig | None = None,
        watchlist: Watchlist | None = None,
        mode: RunMode = RunMode.FIXTURE,
        trigger: str = "manual",
        clock: Callable[[], datetime] | None = None,
        run_id: str | None = None,
    ) -> None:
        self.settings = settings
        self.source = source
        self.store = store
        self.scoring = scoring or load_scoring(settings.scoring_path)
        self.watchlist = watchlist or load_watchlist(settings.watchlist_path)
        self.mode = mode
        self.trigger = trigger
        self.clock = clock or now_wib
        self.started_at = self.clock()
        self.run_id = run_id or make_run_id(self.started_at)
        self._skipped_records = 0

    # -- helpers ------------------------------------------------------------
    @property
    def _today(self) -> date:
        """The date the run reasons about.

        Live runs use the wall clock. A fixture replay uses the date its
        sanitized payloads describe, so date-relative logic (the
        corporate-action window) stays correct however long after the fact the
        replay is executed - and stays byte-identical between two replays.
        """
        anchor = getattr(self.source, "as_of", None)
        if self.mode is RunMode.FIXTURE and isinstance(anchor, date):
            return anchor
        return self.started_at.date()

    def _window(self) -> tuple[date, date]:
        end = self._today
        return end - timedelta(days=self.settings.lookback_days), end

    def _credits(self) -> int:
        return int(getattr(self.source.ledger, "spent", 0))

    def _attempt(
        self,
        name: SourceName,
        action: Callable[[], Normalized],
    ) -> tuple[list[MarketEvent], SourceReport]:
        """Run one source, converting any failure into a reported outcome."""
        before = self._credits()
        calls_before = int(getattr(self.source.ledger, "calls", 0))
        try:
            result = action()
        except CreditBudgetExceededError as exc:
            logger.warning("source.budget_exhausted source=%s detail=%s", name.value, exc)
            return [], SourceReport(
                name=name,
                state=SourceState.BUDGET_EXHAUSTED,
                credits=self._credits() - before,
                calls=int(getattr(self.source.ledger, "calls", 0)) - calls_before,
                error=str(exc),
            )
        except Exception as exc:
            # Deliberately broad. An unattended job must degrade to PARTIAL and
            # name the gap, never die because one source raised something
            # unanticipated. KeyboardInterrupt/SystemExit still propagate.
            logger.error(
                "source.failed source=%s error=%s: %s", name.value, type(exc).__name__, exc
            )
            return [], SourceReport(
                name=name,
                state=SourceState.FAILED,
                credits=self._credits() - before,
                calls=int(getattr(self.source.ledger, "calls", 0)) - calls_before,
                error=f"{type(exc).__name__}: {exc}",
            )
        self._skipped_records += result.skipped
        pop_warning = getattr(self.source, "pop_warning", None)
        source_gap = pop_warning(name.value) if callable(pop_warning) else None
        logger.info(
            "source.ok source=%s events=%d skipped=%d credits=%d",
            name.value,
            len(result.events),
            result.skipped,
            self._credits() - before,
        )
        return result.events, SourceReport(
            name=name,
            state=SourceState.OK,
            records=len(result.events),
            credits=self._credits() - before,
            calls=int(getattr(self.source.ledger, "calls", 0)) - calls_before,
            error=source_gap,
        )

    # -- stages -------------------------------------------------------------
    def discover(self) -> tuple[list[MarketEvent], list[SourceReport]]:
        """Broad, cheap sweep of everything that happened across the exchange."""
        start, end = self._window()
        events: list[MarketEvent] = []
        reports: list[SourceReport] = []

        found, report = self._attempt(
            SourceName.FILINGS,
            lambda: normalize_filings(self.source.fetch_filings(start, end)),
        )
        events += found
        reports.append(report)

        found, report = self._attempt(
            SourceName.SUSPENSIONS,
            lambda: normalize_suspensions(self.source.fetch_suspensions(start, end)),
        )
        events += found
        reports.append(report)

        found, report = self._attempt(
            SourceName.MOVERS,
            lambda: normalize_movers(self.source.fetch_top_changes(periods=("1d",))),
        )
        events += found
        reports.append(report)

        return events, reports

    def enrich(
        self, candidates: list[str], discovery_events: list[MarketEvent]
    ) -> tuple[list[MarketEvent], list[SourceReport], set[str]]:
        """Spend the credit budget on the strongest candidates only."""
        events: list[MarketEvent] = []
        reports: list[SourceReport] = []
        enriched: set[str] = set()

        if not candidates:
            for name in (SourceName.NEWS, SourceName.FOREIGN_FLOW, SourceName.CORPORATE_ACTIONS):
                reports.append(
                    SourceReport(name=name, state=SourceState.SKIPPED, error="no candidates")
                )
            return events, reports, enriched

        start, end = self._window()
        candidate_set = set(candidates)

        # News is batched: one call covers every candidate, so it costs one
        # credit regardless of how many tickers are in the universe.
        found, report = self._attempt(
            SourceName.NEWS,
            lambda: normalize_news(self.source.fetch_news(candidates, start, end), candidate_set),
        )
        events += found
        reports.append(report)

        # Per-symbol enrichment: bounded by max_enrich_tickers AND by budget.
        by_symbol: dict[str, list[MarketEvent]] = {}
        for event in discovery_events:
            by_symbol.setdefault(event.symbol, []).append(event)

        payable = [
            symbol
            for symbol in candidates
            if not is_score_pinned(by_symbol.get(symbol, []), self.scoring)
        ][: self.settings.max_enrich_tickers]

        pinned = [s for s in candidates[: self.settings.max_enrich_tickers] if s not in payable]
        if pinned:
            logger.info(
                "enrich.skipped_pinned symbols=%s reason=score_already_at_maximum",
                ",".join(pinned),
            )

        flow_report = self._enrich_per_symbol(
            SourceName.FOREIGN_FLOW,
            payable,
            self._foreign_flow_for,
            events,
            enriched,
        )
        reports.append(flow_report)

        action_report = self._enrich_per_symbol(
            SourceName.CORPORATE_ACTIONS,
            payable,
            self._corporate_actions_for,
            events,
            enriched,
        )
        reports.append(action_report)

        return events, reports, enriched

    def _foreign_flow_for(self, symbol: str) -> Normalized:
        start = self._today - timedelta(days=self.settings.foreign_flow_window_days)
        payload = self.source.fetch_foreign_flow(symbol, start, self._today)
        return normalize_foreign_flow(
            payload,
            symbol,
            min_baseline_days=self.scoring.thresholds.foreign_flow_min_baseline_days,
        )

    def _corporate_actions_for(self, symbol: str) -> Normalized:
        payload = self.source.fetch_corporate_actions(symbol)
        return normalize_corporate_actions(
            payload,
            symbol,
            reference=self._today,
            window_days=self.scoring.thresholds.corporate_action_window_days,
        )

    def _enrich_per_symbol(
        self,
        name: SourceName,
        symbols: list[str],
        fetch: Callable[[str], Normalized],
        sink: list[MarketEvent],
        enriched: set[str],
    ) -> SourceReport:
        """Enrich each symbol independently; one bad ticker cannot stop the rest."""
        if not symbols:
            return SourceReport(name=name, state=SourceState.SKIPPED, error="no payable candidates")

        before_credits = self._credits()
        before_calls = int(getattr(self.source.ledger, "calls", 0))
        records = 0
        failures: list[str] = []
        budget_hit = False
        completed_symbols: set[str] = set()

        for symbol in symbols:
            try:
                result = fetch(symbol)
            except CreditBudgetExceededError:
                budget_hit = True
                logger.warning(
                    "enrich.budget_exhausted source=%s stopped_at=%s spent=%d budget=%d",
                    name.value,
                    symbol,
                    self._credits(),
                    self.settings.max_api_credits_per_run,
                )
                break
            except Exception as exc:
                logger.warning(
                    "enrich.ticker_failed source=%s symbol=%s error=%s",
                    name.value,
                    symbol,
                    type(exc).__name__,
                )
                failures.append(f"{symbol}: {type(exc).__name__}")
                continue
            self._skipped_records += result.skipped
            sink.extend(result.events)
            records += len(result.events)
            completed_symbols.add(symbol)
            enriched.add(symbol)

        state = SourceState.OK
        error: str | None = None
        if budget_hit:
            state = SourceState.BUDGET_EXHAUSTED
            error = f"credit budget reached after {len(completed_symbols)} ticker(s)"
        elif failures and not completed_symbols:
            state = SourceState.FAILED
            error = "; ".join(failures[:5])
        elif failures:
            error = "partial: " + "; ".join(failures[:5])

        return SourceReport(
            name=name,
            state=state,
            records=records,
            credits=self._credits() - before_credits,
            calls=int(getattr(self.source.ledger, "calls", 0)) - before_calls,
            error=error,
        )

    # -- orchestration ------------------------------------------------------
    def run(self, *, dry_notify: bool = False, notify: bool = True) -> RunReport:
        """Execute the whole pipeline and return its complete report."""
        logger.info(
            "run.start run_id=%s mode=%s trigger=%s budget=%d",
            self.run_id,
            self.mode.value,
            self.trigger,
            self.settings.max_api_credits_per_run,
        )

        discovery_events, discovery_reports = self.discover()
        discovery_events = dedupe_events(discovery_events)

        candidates = select_candidates(discovery_events, self.scoring, self.watchlist)
        enrich_events, enrich_reports, enriched = self.enrich(candidates, discovery_events)

        all_events = dedupe_events(discovery_events + enrich_events)
        fresh = self.store.claim_events(all_events, self.run_id, self.clock())
        alerted = self.store.alerted_event_ids(event.event_id for event in all_events)

        dossiers = build_dossiers(
            all_events,
            self.scoring,
            self.watchlist,
            new_event_ids={e.event_id for e in fresh},
            pending_alert_event_ids={e.event_id for e in all_events if e.event_id not in alerted},
            enriched=enriched,
        )

        sources = discovery_reports + enrich_reports
        status, warnings = self._verdict(sources, discovery_reports)

        report = RunReport(
            run_id=self.run_id,
            mode=self.mode,
            status=status,
            started_at=self.started_at,
            trigger=self.trigger,
            sources=sources,
            warnings=warnings,
            events_detected=len(all_events),
            new_events=len(fresh),
            duplicate_events_suppressed=len(all_events) - len(fresh),
            candidates=len(candidates),
            enriched_tickers=len(enriched),
            estimated_api_credits=self._credits(),
            credit_budget=self.settings.max_api_credits_per_run,
            dossiers=dossiers,
        )

        # Evidence was atomically claimed above. Delivery has its own audit
        # table: if a webhook fails, the event remains pending for a safe retry
        # instead of being falsely considered delivered.

        if notify:
            sent, channels, errors = dispatch(
                report,
                self.settings,
                dry_run=dry_notify,
                artifact_dir=self.settings.artifact_dir,
            )
            report.notifications_sent = sent
            if dry_notify:
                report.notification_previews = len(
                    [dossier for dossier in report.queue if dossier.is_new]
                )
            if errors:
                report.notify_error = "; ".join(errors)
                report.warnings.append(f"Notification issue: {report.notify_error}")
                if report.status is RunStatus.OK:
                    report.status = RunStatus.PARTIAL
            if sent and not dry_notify:
                stamp = self.clock()
                channel = ",".join(channels) or "none"
                for dossier in notifiable(report):
                    self.store.record_alert(self.run_id, dossier, channel, stamp)

        report.finished_at = self.clock()
        self.store.record_run(report)

        logger.info(
            "run.finish run_id=%s status=%s events=%d new=%d dupes=%d queue=%d "
            "notified=%d credits=%d/%d duration=%.2fs",
            self.run_id,
            report.status.value,
            report.events_detected,
            report.new_events,
            report.duplicate_events_suppressed,
            len(report.queue),
            report.notifications_sent,
            report.estimated_api_credits,
            report.credit_budget,
            report.duration_seconds,
        )
        return report

    def _verdict(
        self, sources: list[SourceReport], discovery: list[SourceReport]
    ) -> tuple[RunStatus, list[str]]:
        """Decide OK / PARTIAL / FAILED and say plainly what is missing."""
        warnings: list[str] = []
        failed = [s for s in sources if s.state is SourceState.FAILED]
        exhausted = [s for s in sources if s.state is SourceState.BUDGET_EXHAUSTED]

        usable_discovery = [source for source in discovery if source.state is SourceState.OK]
        if not usable_discovery:
            warnings.append(
                "All discovery sources were unavailable or stopped before returning usable "
                "evidence. No research queue could be produced. "
                "This run is NOT an all-clear."
            )
            return RunStatus.FAILED, warnings

        for source in failed:
            warnings.append(
                f"{source.name.value} enrichment unavailable ({source.error}). "
                "Research queue generated using the remaining sources."
            )
        for source in exhausted:
            warnings.append(
                f"{source.name.value} stopped early: API credit budget reached "
                f"({self._credits()}/{self.settings.max_api_credits_per_run})."
            )
        degraded = [s for s in sources if s.state is SourceState.OK and s.error]
        for source in degraded:
            warnings.append(
                f"{source.name.value} completed with gaps ({source.error}). "
                "Affected tickers are scored on incomplete evidence."
            )
        if self._skipped_records:
            warnings.append(f"{self._skipped_records} source record(s) were malformed and skipped.")

        # A source that partly failed still means some ticker is scored on
        # incomplete evidence. Reporting that run as OK would be the exact
        # "all clear while a source was down" failure this system must not have.
        status = RunStatus.PARTIAL if (failed or exhausted or degraded) else RunStatus.OK
        return status, warnings


def build_source(settings: Settings, mode: RunMode) -> MarketDataSource:
    """Pick the data source for a mode. The only place live/fixture diverges."""
    if mode is RunMode.LIVE:
        return SectorsClient(settings)
    return FixtureSource(settings.fixture_dir, budget=settings.max_api_credits_per_run)


def execute(
    *,
    settings: Settings,
    mode: RunMode,
    trigger: str = "manual",
    dry_notify: bool = False,
    notify: bool = True,
    clock: Callable[[], datetime] | None = None,
    artifact_dir: Path | None = None,
) -> RunReport:
    """Convenience entry point used by the CLI and by CI.

    Owns the lifecycle of the data source and the state store so callers do
    not have to, and always writes run artifacts.
    """
    from .render import write_artifacts

    source = build_source(settings, mode)
    store = StateStore(settings.db_path)
    try:
        pipeline = Pipeline(
            settings=settings,
            source=source,
            store=store,
            mode=mode,
            trigger=trigger,
            clock=clock,
        )
        report = pipeline.run(dry_notify=dry_notify, notify=notify)
        write_artifacts(report, artifact_dir or settings.artifact_dir, store=store)
        return report
    finally:
        close = getattr(source, "close", None)
        if callable(close):
            close()
        store.close()


def source_summary(report: RunReport) -> dict[str, Any]:
    """Compact per-source view used by the CLI and the dashboard."""
    return {
        s.name.value: {
            "state": s.state.value,
            "records": s.records,
            "credits": s.credits,
            "calls": s.calls,
            "error": s.error,
        }
        for s in report.sources
    }

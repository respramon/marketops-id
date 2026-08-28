# MarketOps ID

**Tagline:** Autonomous IDX Research Triage

**Track:** Track 2 - Automation & Workflows
**Primary user:** Indonesian equity research analysts and small research teams

MarketOps ID replaces a repetitive morning research routine: searching for
filings, suspensions, unusual price movement, related news, foreign flow, and
corporate actions; connecting those facts by ticker; deciding what deserves
attention first; and sending the result to the team.

In the production workflow configuration, each weekday scheduled run uses
Sectors Financial API v2 to discover exchange-wide events, normalizes them into
a canonical evidence model, ranks a candidate universe, and selectively
enriches the strongest candidates. It then correlates evidence per ticker and
applies a deterministic Research Attention Score. A suspension can override the
score to 100; other configured rules cover filings, ownership changes,
transaction value, one-day movement, foreign-flow anomalies, relevant news,
upcoming corporate actions, and the team's watchlist. Every point is shown
beside the evidence that produced it.

The score answers only: **what should a human analyst review first?** It is not
an investment score. MarketOps ID produces no BUY/SELL recommendation, target
price, trading signal, brokerage connection, or order.

The workflow is stateful. Each normalized event receives a deterministic
SHA-256 fingerprint and is atomically persisted in SQLite. A rolling data
window may see the same filing on several mornings; delivery stays eligible
only until at least one configured real sink succeeds. In a verified sanitized
replay, the first run found 16 new events and rendered five dry-notify preview
cards; an identical second run suppressed all 16 events and rendered none. The
replay is explicitly labeled
**SANITIZED HISTORICAL REPLAY - NOT LIVE MARKET DATA** and consumes zero real
API credits.

Sectors is essential rather than decorative. Its filings, suspensions, mover,
news, foreign-flow, and corporate-action data create both the candidate set and
the evidence that drives the queue. Removing Sectors removes the live product's
core function.

Operational safeguards include a hard pre-request API-credit budget, batched
news retrieval, selective per-ticker enrichment, bounded retries with jitter,
rate-limit handling, explicit source health, and fail-soft reporting. If an
enrichment source fails, the remaining queue is delivered as `PARTIAL` with a
visible warning. If every discovery source fails, the run is `FAILED` and is
never presented as an all-clear.

Each run persists an audit record and creates structured logs, JSON metadata,
a standalone HTML report, and a Markdown summary. A read-only FastAPI dashboard
shows the latest run, P1/P2/P3 cards, score breakdowns, correlated source
evidence, credit usage, and run history. New queues can be delivered through a
Discord or generic webhook. Discord output is split by both the platform's
embed-count and aggregate-text limits, while delivery eligibility remains
pending if any batch fails.

Current local engineering checks pass: Ruff, strict mypy across 14 source
files, and 400 pytest tests with 95.62% measured coverage (28 August 2026 WIB).
The last public CI checkpoint predates the security remediation and passed 378
tests at 94.93% plus an installed-wheel smoke test. Public manual Actions QA
historically exercised authenticated live Sectors ingestion, the 15-credit
hard budget, fail-soft source warnings, and Discord delivery. One run delivered
16 research cards across three messages; its replay suppressed 77 duplicate
events and delivered zero.

That QA also exposed SEC-001: `httpx` INFO logging wrote the full Discord
webhook URL into three uploaded `workflow.log` artifacts. The affected
artifacts were deleted, the old webhook was revoked, its GitHub Secret was
removed, and the scheduler was disabled. A two-layer redacting-logger and
pre-upload artifact-scrub remediation passes locally but still requires commit,
push, public CI, a newly issued webhook, and a clean replacement delivery.

Those public QA executions were triggered with `workflow_dispatch`. They prove
the production path works, but are deliberately not presented as Track 2
unattended evidence. Three genuine weekday `schedule` runs, final video uploads,
and portal submission remain pending before the project can be called fully
submission-complete. Schedule evidence collection starts only after the
security recovery is verified and automation is safely re-enabled.

> Research triage only. MarketOps ID does not provide investment
> recommendations or execute trades.

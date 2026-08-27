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
Discord or generic webhook.

The engineering checks pass locally and in public CI: Ruff, strict mypy, and
375 pytest tests with 95.08% measured coverage (27 August 2026 WIB). CI also
installs the built wheel outside the checkout. Two public manual hosted fixture
runs verified artifact upload and cross-run state restoration, but are not
presented as Track 2 proof. Authenticated live API execution, webhook delivery
evidence, and genuine scheduled-run proof remain external account actions and
must be completed before this copy is used as a final submission claim.

> Research triage only. MarketOps ID does not provide investment
> recommendations or execute trades.

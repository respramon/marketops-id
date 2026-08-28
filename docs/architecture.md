# MarketOps ID Architecture

MarketOps ID is an unattended research-triage pipeline for an Indonesian equity
research analyst or small research desk. It discovers market events through the
Sectors Financial API v2, joins evidence by IDX ticker, assigns a deterministic
Research Attention Score, suppresses already-seen events, and delivers only new,
prioritized research cards. It does not recommend, predict, price, or trade a
security.

> Research triage only. MarketOps ID does not provide investment
> recommendations or execute trades.

## System Context

```mermaid
flowchart LR
    Scheduler[GitHub Actions weekday schedule<br/>configured; currently disabled] --> CLI[marketops run<br/>trigger=schedule]
    CLI --> Sectors[Sectors Financial API v2]
    Sectors --> Discovery[Filings<br/>Suspensions<br/>1-day movers]
    Discovery --> Candidates[Deterministic<br/>candidate ranking]
    Candidates --> Enrichment[Batched news<br/>Selective foreign flow<br/>Selective corporate actions]
    Discovery --> Normalize[Canonical event<br/>normalization]
    Enrichment --> Normalize
    Normalize --> Correlate[Correlate by<br/>canonical ticker]
    Correlate --> Score[Research Attention<br/>Score + explanation]
    Score --> State[(SQLite state)]
    State --> Dedupe{Any new<br/>event IDs?}
    Dedupe -->|yes| Notify[Limit-safe Discord batches<br/>and/or generic webhook]
    Dedupe -->|no| Suppress[Suppress repeat alert]
    Score --> Staged[Staged reports<br/>and structured logs]
    Staged --> Guard[Pending-release<br/>artifact scrub gate]
    Guard --> Artifacts[Clean JSON<br/>HTML + Markdown]
    State --> Dashboard[Read-only FastAPI<br/>dashboard and API]
```

Sectors is the product's core data dependency. Removing Sectors removes the
filings, suspensions, mover discovery, news, foreign-flow history, corporate
actions, source provenance, candidate universe, and therefore the research
queue itself. Sanitized fixtures mirror verified Sectors response shapes only
to make development and judging replay deterministic without spending credits.

## End-to-End Run

1. The weekday schedule starts `marketops run --mode live --trigger schedule`.
   A manual trigger exists for diagnosis, but is not the Track 2 proof. The
   scheduler was disabled during SEC-001 containment and re-enabled on
   2026-08-28 after the remediation was CI-verified and a clean delivery run
   was inspected; no genuine scheduled execution is documented yet. See
   [`../evidence/unattended-runs.md`](../evidence/unattended-runs.md).
2. The typed HTTP client performs broad discovery over a configured lookback:
   filings, suspensions, and the top gainers and losers for the `1d` period.
3. Raw records cross a normalization boundary. Symbols become bare uppercase
   tickers, timestamps become timezone-aware WIB values, nullable links remain
   nullable, and malformed rows are skipped and counted.
4. Discovery events are ranked deterministically. Suspensions and material
   filings rank ahead of ordinary price movement. Muted tickers are excluded.
5. News is fetched in a batched symbol request. Foreign flow and corporate
   actions are fetched per symbol for at most
   `MARKETOPS_MAX_ENRICH_TICKERS` candidates (default five). A suspension that
   already pins the score at 100 skips paid per-symbol enrichment.
6. Evidence is grouped by canonical ticker. The configured scoring engine
   calculates one score and an ordered list of contributing reasons.
7. SQLite atomically claims normalized event fingerprints, so two overlapping
   processes cannot both call the same evidence new. Dossiers are still shown
   on replay, while real delivery is eligible only for evidence that has not
   reached a sink.
8. Evidence is claimed before notification and successful real delivery is
   separately recorded in the `alerts` table. Discord queues are partitioned
   by both its 10-embed count limit and 6,000-character aggregate embed-text
   limit. A failed webhook or partial batch sequence leaves the cards pending
   for a safe retry rather than losing them to deduplication.
9. The run, source health, warnings, estimated credits, queue, and timestamps
   are persisted. JSON, standalone HTML, Markdown, and run-history artifacts
   are written for CI retention and audit. The pending-release workflow scrubs
   this directory and fails on any redaction before upload.
10. The dashboard reads the latest persisted run. It has no route that can
    start or mutate the pipeline.

## Components

| Component | Responsibility |
|---|---|
| `marketops.cli` | `doctor`, `run`, `report`, `serve`, exit codes, structured-log mode |
| `marketops.sectors` | Authenticated API v2 requests, timeout/retry behavior, response-cost accounting, pre-call budget guard, fixture adapter |
| `marketops.normalize` | Defensive mapping from six raw API shapes into `MarketEvent` |
| `marketops.correlate` | Candidate ordering, ticker grouping, dossier construction, stable evidence ordering |
| `marketops.scoring` | Config-driven score, priority bands, explanations, suspension override |
| `marketops.state` | SQLite schema, event partitioning, run history, delivery audit |
| `marketops.pipeline` | Discovery, selective enrichment, fail-soft orchestration, verdict generation |
| `marketops.notify` | Limit-safe Discord message batches, generic JSON payloads, dry-run preview, safe webhook errors |
| `marketops.security` | Pending-release secret-redacting formatter, quiet HTTP transport logging, recursive artifact scrub, and fail-on-redaction gate |
| `marketops.render` | Standalone HTML, JSON, Markdown, and terminal summaries |
| `marketops.web` | Read-only dashboard plus `/api/latest`, `/api/runs`, and `/healthz` |

## Sectors API Surface

Only endpoints verified in the official v2 documentation are called. Exact
parameters, response fields, costs, and failure semantics are recorded in
[`sectors-api-map.md`](sectors-api-map.md).

| Stage | Capability | Exact path | Planned successful-call cost |
|---|---|---|---:|
| Discovery | Filings | `GET /v2/filings/` | 1 |
| Discovery | Suspensions | `GET /v2/suspensions/` | 1 |
| Discovery | Movers, two classifications x `1d` | `GET /v2/companies/top-changes/` | 2 |
| Enrichment | Batched news | `GET /v2/news/` | 1 |
| Enrichment | Foreign flow | `GET /v2/foreign-flow/{symbol}/` | 1 per selected ticker |
| Enrichment | Corporate actions | `GET /v2/company/corporate-actions/{symbol}/` | 1 per selected ticker |

With five payable candidates, the planned path estimates 15 credits. The
runtime default hard ceiling is 15 credits, configurable with
`MARKETOPS_MAX_API_CREDITS_PER_RUN`. The ledger checks affordability before a
request is sent. Fixture mode makes no network request and spends no real
credit; it simulates the equivalent live cost to test the same guard.

## Canonical Event and Deduplication

Every normalized event contains:

- `event_type`
- canonical `symbol`
- timezone-aware `occurred_at`
- human-readable headline and detail
- `source_ref` and optional `source_url`
- the defensively preserved fields needed for scoring and audit

Its identity is:

```text
SHA256(event_type | symbol | occurred_at-in-WIB | source_ref)
```

The fingerprint is independent of run ID, input ordering, and wall-clock time.
SQLite uses it as the `events.event_id` primary key, so a restarted process
recognizes the same filing or mover event. A changed timestamp or source
reference remains an independent event.

## Research Attention Score

The score is a transparent queue-ordering heuristic configured in
`config/scoring.yml`. It is not a security rating or expected-return model.

- Suspension: override to 100.
- Filing: base points, with ownership-change and transaction-value additions.
- Price move: one exclusive magnitude tier.
- Foreign flow: one exclusive anomaly tier calculated from prior observations.
- News: presence of relevant ticker-linked news.
- Corporate action: a parseable upcoming event within the configured window.
- Watchlist: a small desk-coverage bonus only when other score evidence exists.

The total is capped at 100 and mapped to P1/P2/P3 thresholds. Aggregation uses
`max` and presence checks over the evidence set, so event ordering cannot alter
the result. Every component is shown with points and supporting evidence.

## State Model

SQLite is intentionally small and operationally simple:

| Table | Purpose |
|---|---|
| `events` | One row per first-seen deterministic event ID |
| `alerts` | Successful non-dry-run delivery audit by run, ticker, priority, score, channel, and event IDs |
| `runs` | Counters and the complete serialized `RunReport` for each execution |
| `schema_meta` | Database schema version |

WAL mode and transactions protect local writes. The production workflow must
restore the previous database before a run and save the updated database after
the run; otherwise an ephemeral CI runner cannot deduplicate across days. Run
artifacts are evidence and diagnostics, not the deduplication source of truth.

## Reliability and Failure Semantics

- HTTP timeout defaults to 15 seconds.
- Retryable transport failures, HTTP 429, and HTTP 5xx use bounded exponential
  backoff with full jitter; `Retry-After` is honored up to 30 seconds.
- HTTP 400, 401, 403, and 404 are terminal and mapped to explicit exceptions.
- One failed source or ticker does not discard usable evidence from the others.
- A degraded run is `PARTIAL` and names the unavailable or incomplete source.
- If all three discovery sources are unavailable or budget-stopped before
  returning usable evidence, the run is `FAILED` and explicitly says that the
  result is not an all-clear.
- Paginated discovery and news responses validate the documented envelope.
  The production default reads one maximum-size page (30 rows); if another page
  exists, the source reports a visible gap and the run becomes `PARTIAL` rather
  than silently implying complete coverage.
- Notification failure makes an otherwise healthy run `PARTIAL`. Application
  exceptions omit sink URLs and keys; SEC-001 showed that dependency transport
  logs must also be redacted before artifact publication.
- A Discord channel is recorded as successful only after every message batch
  succeeds. Count-and-text-aware batching prevents valid individual embeds
  from exceeding the aggregate message limit; partial delivery remains pending
  for at-least-once retry.
- A malformed source record is skipped, counted, and disclosed in warnings.

## Trust Boundaries and Secrets

```mermaid
flowchart TB
    GH[GitHub Secrets / local environment] -->|SECTORS_API_KEY| Client[Sectors client]
    GH -->|webhook URL| Notifier[Notifier]
    Client -->|Authorization header| API[api.sectors.app]
    API -->|market data only| Pipeline[Pipeline]
    Pipeline -->|no credentials| DB[(SQLite)]
    Pipeline --> Logs[Rendered run logs and reports]
    Logs --> Guard[Redaction + artifact scrub gate]
    Guard -->|clean only| Files[Run artifacts]
    Notifier -->|research-card JSON| Sink[Discord / generic webhook]
```

Secrets are represented as Pydantic `SecretStr`, loaded from environment
variables, and ignored by Git. That protects source/configuration surfaces but
does not automatically sanitize third-party log records. SEC-001 confirmed
that an `httpx` INFO record put the full Discord request URL in three uploaded
`workflow.log` files. The old webhook and affected artifacts were deleted, the
Discord GitHub Secret was removed, and the scheduler was disabled. The guard
shown above exists in the uncommitted remediation and must be published and
verified before operation resumes. Source URLs and market data are treated as
untrusted display content; Jinja auto-escaping remains enabled. The dashboard
is a local/read-only evidence viewer, not a multi-user service.

## Fixture and Live Data Boundary

All files under `fixtures/sanitized/` are labeled:

```text
SANITIZED HISTORICAL REPLAY - NOT LIVE MARKET DATA
Used for deterministic testing and demo.
```

Ticker symbols are real IDX symbols, but fixture figures and example-news URLs
are synthetic. Every fixture artifact has `mode: fixture` and a visible replay
banner. After security recovery, authenticated `mode: live` manual runs may
validate current data and delivery, but only a run whose GitHub event is
`schedule` can be presented as unattended Track 2 proof.

## Hosted Live Validation

All runs in this section were explicit `workflow_dispatch` QA and are not
scheduled-run evidence. Their counters were verified before incident
containment; affected source artifacts were deleted and only public run
metadata/job pages remain:

- Run `33039796607` exercised all six Sectors capabilities, normalized 77
  events, built 33 candidates, selectively enriched five tickers, and used the
  15-credit ceiling. The only source warning was a visible news-page cap.
- The first real Discord attempt returned HTTP 400 because its embeds exceeded
  the aggregate text limit. Commit `3f3bed7` introduced the batching policy
  described above.
- Run `33040201783` restored the pending cards and historically delivered all
  16 across three Discord messages. Its artifact was later found to contain the
  webhook URL and was deleted under SEC-001.
- Run `33040251479` restored the successful production state, suppressed 77
  duplicate events, and delivered zero notifications.

## Known Scope Boundaries

- The client supports documented offset pagination when a caller explicitly
  requests more than 30 records. The scheduled default deliberately reads one
  30-record page per list endpoint to protect the 15-credit budget; a
  `has_next` response is disclosed as incomplete evidence.
- It is a single-team, single-state workflow without user authentication.
- SQLite cache persistence was verified across two separate manual hosted
  fixture runs and across the successful manual live delivery/replay pair.
  GitHub Actions cache remains operational state rather than a backup, and
  genuine schedule-triggered durability evidence is still pending. The
  scheduler remains disabled until security recovery is complete.
- Webhooks provide delivery, not acknowledgment or escalation tracking.
- `max_concurrency` is configurable for future expansion; the current client
  issues calls sequentially for deterministic budget and retry behavior.
- No brokerage integration, order path, target price, buy/sell output, or LLM
  investment judgment exists by design.

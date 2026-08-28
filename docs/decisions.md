# Engineering Decisions

These records explain the product and engineering choices that materially
shape MarketOps ID. Dates use WIB. All decisions are accepted unless marked
otherwise.

## ADR-001: Optimize for a research desk, not a generic investor app

- **Date:** 2026-08-26
- **Status:** Accepted
- **Decision:** The primary user is an IDX equity research analyst or small
  research team. Output is a prioritized evidence queue, not a market portal.
- **Why:** The recurring job is discovering what deserves human review first.
  A focused user makes priority, provenance, deduplication, and delivery more
  important than broad consumer features.
- **Consequence:** No portfolio tracker, order entry, social feed, or generic
  recommendation surface is included.

## ADR-002: Keep Sectors API v2 on the critical path

- **Date:** 2026-08-26
- **Status:** Accepted
- **Decision:** Use six verified Sectors capabilities for discovery and
  enrichment: filings, suspensions, top changes, news, foreign flow, and
  corporate actions.
- **Why:** Sectors should create the candidate universe and the evidence used
  to prioritize it, rather than appear as a decorative lookup.
- **Consequence:** Without Sectors data, the live workflow cannot produce its
  research queue. Fixture data is restricted to clearly labeled replay and
  tests.

## ADR-003: Use Python 3.12 and a small modular monolith

- **Date:** 2026-08-26
- **Status:** Accepted
- **Decision:** Implement the scheduler entry point, pipeline, API client,
  scoring, storage, rendering, and dashboard in one typed Python package.
- **Why:** A once-daily workflow benefits more from clear boundaries and a
  simple operational unit than from networked services.
- **Consequence:** Modules are independently testable, but deployed together.
  FastAPI serves only the read side.

## ADR-004: Normalize before correlation or scoring

- **Date:** 2026-08-26
- **Status:** Accepted
- **Decision:** Raw endpoint payloads cannot pass beyond `marketops.normalize`.
- **Why:** Sectors endpoints differ in symbols, dates, nullability, and nested
  response shapes. A canonical `MarketEvent` lets every downstream rule be
  deterministic and fixture-testable.
- **Consequence:** New endpoint support requires a normalizer and malformed-row
  behavior before it can influence a score.

## ADR-005: Use deterministic heuristics, not a black-box model

- **Date:** 2026-08-26
- **Status:** Accepted
- **Decision:** Configure score weights and thresholds in
  `config/scoring.yml`; use no LLM or probabilistic model in scoring.
- **Why:** An analyst must be able to audit exactly why a ticker appeared, and
  tests must reproduce threshold behavior exactly.
- **Consequence:** The weights are hackathon product heuristics, not
  scientifically validated investment factors. Tuning is explicit and
  versionable.

## ADR-006: Discover broadly and enrich selectively

- **Date:** 2026-08-26
- **Status:** Accepted
- **Decision:** Spend low fixed cost on exchange-wide discovery, batch news,
  then perform foreign-flow and corporate-action calls only for the strongest
  candidates, at most five by default.
- **Why:** Per-symbol calls across hundreds of tickers would consume the credit
  grant without improving the top of the morning queue.
- **Consequence:** Preliminary ranking controls enrichment order. A suspended
  ticker skips enrichment because its final score is already pinned.

## ADR-007: Enforce the API budget before network calls

- **Date:** 2026-08-26
- **Status:** Accepted
- **Decision:** A per-run credit ledger reserves the documented endpoint cost
  before sending a request.
- **Why:** Reporting overspend after the fact is not protection.
- **Consequence:** When the next call is unaffordable, enrichment stops, the
  available queue is still produced, and the run records `PARTIAL` with a
  budget warning.

## ADR-008: Fingerprint events and persist state in SQLite

- **Date:** 2026-08-26
- **Status:** Accepted
- **Decision:** Use SHA-256 over event type, canonical symbol, WIB timestamp,
  and source reference as the event ID. Store events, alerts, and runs in
  SQLite.
- **Why:** A rolling date window necessarily rediscovers yesterday's records.
  Stable identity and durable state prevent alert fatigue across process
  restarts without operating a database server.
- **Consequence:** CI must restore and save the SQLite file between scheduled
  runs. A changed source reference or timestamp is intentionally a new event.

## ADR-009: Claim evidence before delivery and retry undelivered cards

- **Date:** 2026-08-26
- **Status:** Accepted
- **Decision:** Atomically claim first-seen evidence before posting a webhook;
  record a separate alert row only after at least one real sink succeeds.
- **Why:** The claim eliminates a read-then-write race between overlapping
  runs. Separating observation from delivery means a webhook outage cannot
  permanently lose an alert merely because the event has already been stored.
- **Consequence:** A successful delivery suppresses that evidence on replay.
  A failed delivery remains pending and is retried on the next real run. A
  dry-notify preview is never counted as delivery and never alters this state.

## ADR-010: Fail soft, but never present missing data as an all-clear

- **Date:** 2026-08-26
- **Status:** Accepted
- **Decision:** Isolate every source and per-ticker enrichment call. Produce a
  `PARTIAL` report from surviving evidence and enumerate gaps.
- **Why:** A foreign-flow outage should not erase an urgent suspension, while
  a clean-looking empty report during a discovery outage would be dangerous.
- **Consequence:** All discovery sources failing yields `FAILED`; any smaller
  gap is visibly `PARTIAL`.

## ADR-011: Make the dashboard read-only

- **Date:** 2026-08-26
- **Status:** Accepted
- **Decision:** The web UI reads persisted runs and exposes no pipeline trigger
  or state mutation route.
- **Why:** Track 2 should show that the work already happened unattended. A
  prominent "Run now" button would confuse the product claim and enlarge the
  security surface.
- **Consequence:** Testing and emergency runs stay in the CLI or GitHub Actions
  manual dispatch.

## ADR-012: Use webhooks as delivery adapters

- **Date:** 2026-08-26
- **Status:** Accepted
- **Decision:** Support Discord embeds and a generic JSON webhook, with
  dry-notify previews.
- **Why:** A research team needs the queue in its existing workflow. Webhooks
  demonstrate delivery without building a messaging platform.
- **Consequence:** Sink failure is reported as `PARTIAL`; secrets never appear
  in application-generated error messages. Dependency transport logs and
  generated artifacts are separate security boundaries; ADR-019 addresses the
  disclosure found at that boundary.

## ADR-013: Keep a production-shaped sanitized replay

- **Date:** 2026-08-26
- **Status:** Accepted
- **Decision:** Store sanitized fixture payloads with the same documented JSON
  shapes as live endpoints and a fixed historical `as_of` date.
- **Why:** It prevents development from consuming API credits and makes score,
  correlation, partial failure, and replay behavior reproducible.
- **Consequence:** Every fixture surface must say "SANITIZED HISTORICAL REPLAY -
  NOT LIVE MARKET DATA." Fixture credits are simulated estimates, never actual
  consumption.

## ADR-014: Schedule at 07:17 WIB on weekdays

- **Date:** 2026-08-26
- **Status:** Accepted
- **Decision:** Configure GitHub Actions for `00:17 UTC` Monday-Friday, which is
  07:17 WIB, and retain `workflow_dispatch` for explicit tests.
- **Why:** It is early enough for a morning research queue and avoids a
  top-of-hour scheduler hotspot.
- **Consequence:** Genuine Track 2 proof must show `schedule`, not only a manual
  dispatch. GitHub Actions schedules use UTC and may start a few minutes late.

## ADR-015: Exclude trading behavior by design

- **Date:** 2026-08-26
- **Status:** Accepted
- **Decision:** Produce no BUY/SELL label, target price, trading signal,
  portfolio action, brokerage credential, or execution endpoint.
- **Why:** The product solves research discovery and prioritization, not the
  investment decision itself.
- **Consequence:** A score means "review this evidence sooner" and every user
  surface carries the research-triage disclaimer.

## ADR-016: Package runtime assets and test the installed wheel

- **Date:** 2026-08-27
- **Status:** Accepted
- **Decision:** Include scoring/watchlist configuration, sanitized fixtures,
  templates, and static files beneath `marketops/resources` in the wheel while
  retaining repository-relative paths for source development. CI uninstalls
  the editable package, installs the built wheel, changes to an unrelated
  temporary directory, and runs `doctor` plus a fixture pipeline smoke test.
- **Why:** Editable-source tests can pass even when a built distribution omits
  non-Python runtime assets. The hosted scheduler exposed exactly this class
  of packaging defect.
- **Consequence:** Both source checkouts and normal `pip install .` executions
  resolve the same assets. A future wheel/resource regression fails CI before
  it can break a scheduled run.

## ADR-017: Pin third-party GitHub Actions by immutable commit

- **Date:** 2026-08-27
- **Status:** Accepted
- **Decision:** Reference official `actions/*` releases by their full commit
  SHA and retain the verified release tag in an inline comment.
- **Why:** Immutable references reduce workflow supply-chain exposure and make
  the exact runner implementation auditable.
- **Consequence:** Action upgrades are explicit repository changes. Their tags,
  SHAs, and hosted-run behavior must be re-verified when updated.

## ADR-018: Batch Discord delivery by aggregate text as well as embed count

- **Date:** 2026-08-27
- **Status:** Accepted
- **Decision:** Partition a Discord research queue so every message stays
  within both the 10-embed limit and the 6,000-character aggregate embed-text
  limit. Treat the channel as successful only when every batch succeeds.
- **Why:** Manual authenticated live run `33039918857` showed that eight
  individually valid embeds can still exceed Discord's aggregate message
  limit and receive HTTP 400. Embed count alone is therefore not a sufficient
  payload guard.
- **Consequence:** Large queues are delivered across multiple messages. If any
  batch fails, the cards are not marked delivered and remain eligible for an
  at-least-once retry. Commit `3f3bed7` implemented this policy; manual live run
  `33040201783` delivered 16 cards across three messages, and replay
  `33040251479` delivered zero after suppressing 77 duplicates. These manual
  `workflow_dispatch` runs validate delivery semantics, not scheduled Track 2
  qualification. Their delivery counters remain historical facts, but the
  affected downloadable artifacts were later removed during SEC-001
  containment and are not current submission evidence.

## ADR-019: Treat logs and artifacts as credential-publication boundaries

- **Date:** 2026-08-28
- **Status:** Accepted; implementation pending public verification
- **Decision:** Apply two independent controls before any run evidence is
  uploaded: redact configured secrets and Discord-webhook URL shapes from the
  final rendered log line while silencing `httpx`/`httpcore` INFO transport
  logs, then recursively scrub the artifact directory and fail the workflow if
  any credential occurrence had to be removed.
- **Why:** SEC-001 confirmed that `httpx` logged the full request URL and
  `tee` persisted it to `workflow.log`. Because Discord authenticates in the
  URL path, three public artifacts contained the webhook credential even
  though source code, Git history, exception messages, and the Actions console
  did not intentionally expose it.
- **Consequence:** Artifact upload is no longer allowed to rely on console
  masking or application-level error hygiene. The old webhook and affected
  artifacts were revoked/deleted, the Discord secret was removed, and the
  scheduler was disabled during containment. This decision was then committed
  (`2e51bd8`), pushed, CI-verified (run 33153711435), and exercised with a new webhook
  in delivery run 33155463943, whose replacement artifact was confirmed clean,
  so notification and scheduling are unblocked.

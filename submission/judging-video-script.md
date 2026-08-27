# Judging Video: MarketOps ID

**Target runtime:** 2 minutes 48 seconds.
**Use only after evidence review:** A judging cut that claims Track 2
qualification must replace every `[PENDING EVIDENCE]` shot with the real
GitHub Actions evidence specified below. Until then, describe the scheduler as
configured, not as proven. Public/unlisted video access is
`[BLOCKED: HUMAN ACTION REQUIRED]` until verified anonymously.

| Time | Shot | Narration / on-screen copy |
|---|---|---|
| 00:00–00:14 | Problem title and analyst workflow illustration. | “MarketOps ID helps Indonesian equity research analysts decide what to investigate first when important signals arrive through separate market-data views.” |
| 00:14–00:28 | Sectors dependency diagram. | “Sectors Financial API v2 is the core source: filings, suspensions, one-day movers, ticker news, foreign flow, and corporate actions create the research queue.” |
| 00:28–00:43 | Local workflow YAML or architecture diagram. Label: **Configured locally; not scheduled-run proof**. | “The production workflow is configured for weekdays at 07:17 WIB. It runs live mode, restores its SQLite state, produces artifacts, and saves the state for the next cycle.” |
| 00:43–00:58 | Sanitized fixture replay dashboard with banner. | “For deterministic testing, this sanitized historical replay uses matching response shapes but zero live API credits. It is not live market data.” |
| 00:58–01:17 | One P1 card and score components (fixture is acceptable with banner). | “MarketOps correlates evidence by canonical ticker and applies a deterministic Research Attention Score. The score is transparent: every component and its source evidence are visible.” |
| 01:17–01:34 | Suspension card plus disclaimer. | “A suspension overrides the queue to P1. Other rules consider material filings, price moves, foreign-flow anomalies, news, corporate actions, and the desk watchlist. This is triage, not investment advice.” |
| 01:34–01:50 | Two replay run summaries, fixture banner visible. | “The first verified replay detected 16 new events and rendered five dry-notify cards. The identical second replay suppressed all 16 duplicates. Dry preview is not external delivery.” |
| 01:50–02:12 | Public CI and hosted fixture runs, followed by the `[PENDING EVIDENCE]` schedule placeholder. | “The public repository, CI, artifact upload, and cross-run cache are operational. But Track 2 proof requires genuine runs whose event is `schedule`, not these manual QA dispatches. The API key, webhook, and scheduled history are still pending.” |
| 02:12–02:31 | `[PENDING EVIDENCE]` placeholder, or one real schedule detail/artifact after review. | “Before submission, three scheduled live runs must be recorded with their run IDs, timestamps, artifacts, source health, credit totals, restored state, and truthful delivery outcome.” |
| 02:31–02:48 | Architecture/dossier/dedupe summary; final disclaimer. | “MarketOps ID turns Sectors evidence into an unattended, auditable research queue while keeping a human in charge of any investment decision.” |

## Required Replacement Shots Before a Track 2 Claim

1. Actions history with three completed `schedule` events from the actual public
   repository.
2. One real schedule detail page showing workflow, trigger, status, and time.
3. The matching uploaded artifact and `run_id` from `evidence/unattended-runs.md`.
4. A real webhook delivery only if a notification was actually sent. If none was
   sent, show the run's truthful zero-notification reason instead.

Do not trim the pending disclosure out while retaining a claim that scheduled
automation has been demonstrated.

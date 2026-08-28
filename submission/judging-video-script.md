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
| 00:28–00:43 | Local workflow YAML or architecture diagram. Label: **Configured; currently disabled during SEC-001 recovery**. | “The production workflow is designed for weekdays at 07:17 WIB. It restores SQLite state and produces evidence artifacts, but remains disabled until its security recovery is verified.” |
| 00:43–00:58 | Sanitized fixture replay dashboard with banner. | “For deterministic testing, this sanitized historical replay uses matching response shapes but zero live API credits. It is not live market data.” |
| 00:58–01:17 | One P1 card and score components (fixture is acceptable with banner). | “MarketOps correlates evidence by canonical ticker and applies a deterministic Research Attention Score. The score is transparent: every component and its source evidence are visible.” |
| 01:17–01:34 | Suspension card plus disclaimer. | “A suspension overrides the queue to P1. Other rules consider material filings, price moves, foreign-flow anomalies, news, corporate actions, and the desk watchlist. This is triage, not investment advice.” |
| 01:34–01:50 | Two replay run summaries, fixture banner visible. | “The first verified replay detected 16 new events and rendered five dry-notify cards. The identical second replay suppressed all 16 duplicates. Dry preview is not external delivery.” |
| 01:50–02:12 | Current local QA, prior public CI `33040157886`, and historical `discord-result.png`. Keep **SEC-001 contained**, **not current safe-delivery proof**, and **manual QA** visible. | “The remediation passes 400 local tests at 95.62 percent coverage. Earlier manual QA delivered 16 cards and replayed quietly, but its artifact exposed the webhook URL. We deleted affected artifacts, revoked the webhook, removed its secret, and paused automation. Public CI now verifies the remediation, and a new webhook delivered eighteen cards with a clean, webhook-free artifact. Genuine scheduled runs are still pending.” |
| 02:12–02:31 | `[PENDING CLEAN DELIVERY + SCHEDULE EVIDENCE]`, replaced only after recovery and three firings. | “Track 2 still requires three later live runs whose GitHub event is schedule. Each clean artifact must match its run ID, timestamps, source health, credits, restored state, and truthful delivery outcome.” |
| 02:31–02:48 | Architecture/dossier/dedupe summary; final disclaimer. | “MarketOps ID turns Sectors evidence into an unattended, auditable research queue while keeping a human in charge of any investment decision.” |

## Required Replacement Shots Before a Track 2 Claim

1. Actions history with three completed `schedule` events from the actual public
   repository.
2. One real schedule detail page showing workflow, trigger, status, and time.
3. The matching uploaded artifact and `run_id` from `evidence/unattended-runs.md`.
4. One clean post-remediation manual delivery plus its independently scanned
   artifact. The existing `discord-result.png` is historical containment
   evidence only, not current delivery proof.
5. For a scheduled run, show its truthful delivery outcome—even when that
   outcome is zero because deduplication correctly suppressed it.

Do not trim the pending disclosure out while retaining a claim that scheduled
automation has been demonstrated.

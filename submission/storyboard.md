# MarketOps ID — Submission Storyboard

This is the canonical shot list for both videos. It separates reproducible
local fixture evidence from the external evidence required for a Track 2
qualification claim. Never replace a pending shot with a mock, a
`workflow_dispatch` run, or a dry-notify preview. A manual run may appear in its
own QA segment only when its non-qualifying label stays visible.

## Public teaser — 57 seconds

| Time | Visual | Evidence label | Intended message |
|---|---|---|---|
| 00:00–00:07 | Research-monitoring problem title | None | Analysts must join fragmented IDX evidence before they can decide what to inspect. |
| 00:07–00:14 | MarketOps ID title | `Autonomous IDX Research Triage` | The product turns that work into one research queue. |
| 00:14–00:24 | `assets/architecture.png` | `07:17 WIB schedule configured — currently disabled` | Sectors v2 supplies the core market evidence; recurring operation waits for security revalidation. |
| 00:24–00:36 | `assets/dashboard.png`, then `assets/p1-card.png` | `SANITIZED HISTORICAL REPLAY — NOT LIVE MARKET DATA` | Canonical ticker correlation and an explainable score decide review order, not what to trade. |
| 00:36–00:46 | Historical delivery/containment summary, then replay result | `HISTORICAL MANUAL QA — SEC-001 CONTAINED`; `NOT CURRENT DELIVERY OR SCHEDULED PROOF` | Prior manual QA delivered 16 cards and replayed quietly; its affected artifact was deleted after a webhook leak, so clean replacement proof is pending. |
| 00:46–00:57 | Closing title | `Scheduler disabled during security recovery — schedule history: 0` | MarketOps ID keeps the human responsible for investment decisions and evidence claims. |

## Judging video — 2 minutes 48 seconds

| Time | Visual | Evidence boundary | Intended message |
|---|---|---|---|
| 00:00–00:14 | Problem title | None | Important market evidence arrives through multiple views. |
| 00:14–00:28 | Architecture diagram | Repository diagram, not a run | Sectors v2 capabilities are the core data dependency. |
| 00:28–00:43 | Workflow YAML / architecture | `Configured; currently disabled during SEC-001 recovery` | GitHub Actions is designed for weekdays at 07:17 WIB and persists state/artifacts, but cannot resume until security revalidation. |
| 00:43–00:58 | Fixture dashboard | Fixture banner must remain legible | Fixture mode makes repeatable tests and demos possible without live credits. |
| 00:58–01:17 | P1 card + component list | Fixture banner | The Research Attention Score is deterministic and shows each reason. |
| 01:17–01:34 | Suspension card + disclaimer | `Research triage only` | Suspensions can force P1; this is not a trade recommendation. |
| 01:34–01:50 | Replay result | `Preview only — no external delivery` | SQLite fingerprints make a repeated data window quiet on the second run. |
| 01:50–02:12 | Current local test asset, prior public CI, and `assets/discord-result.png` | `LOCAL: 400 tests / 95.62%`; `PUBLIC CI: prior 378 / 94.93%`; `HISTORICAL DELIVERY — SEC-001 CONTAINED` | The security fix now passes public CI; a clean replacement delivery artifact remains pending. |
| 02:12–02:31 | Pending `actions-history.png` / `scheduled-run.png`, replaced only after recovery and three scheduler firings | Match run ID, timestamp, mode, `schedule` trigger, and clean artifact scan | Schedule count is zero; three genuine post-remediation runs are still required and manual evidence cannot fill the slots. |
| 02:31–02:48 | Closing dashboard/architecture frame | None | MarketOps transforms Sectors evidence into an auditable research queue. |

## Asset use rules

- `assets/dashboard.png` and `assets/p1-card.png` are local fixture captures.
- `assets/actions-history.png` and `assets/scheduled-run.png` remain placeholders
  until replaced by genuine `schedule` evidence. They must not appear as proof.
- `assets/discord-result.png` is now a historical, incident-contained summary.
  Keep **SEC-001 contained**, **not current safe-delivery proof**, **manual QA**,
  and **not scheduled proof** legible. Replace it after clean revalidation.
- `assets/test-pass.png` records successful public push-triggered CI
  `33040157886` at 378 tests / 94.93%; it predates remediation and is not
  scheduled-run proof. `assets/test-pass.svg` and `test-pass-local.png` show the
  current local QA-only result: 400 tests and 95.62% coverage.
- `assets/hosted-dedupe-qa.png` summarizes the two linked public manual fixture
  runs and is visibly labeled non-qualifying QA.
- `marketops-*-visual-no-voice.mp4` files predate SEC-001 and are not final
  public videos. Rebuild them from this storyboard, then regenerate matching
  captions and add narration before upload.

See [video-assembly.md](video-assembly.md) for capture hygiene and the two
timed scripts for narration.

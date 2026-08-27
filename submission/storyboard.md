# MarketOps ID — Submission Storyboard

This is the canonical shot list for both videos. It separates reproducible
local fixture evidence from the external evidence required for a Track 2
qualification claim. Never replace a pending shot with a mock, a
`workflow_dispatch` run, or a dry-notify preview.

## Public teaser — 57 seconds

| Time | Visual | Evidence label | Intended message |
|---|---|---|---|
| 00:00–00:07 | Research-monitoring problem title | None | Analysts must join fragmented IDX evidence before they can decide what to inspect. |
| 00:07–00:14 | MarketOps ID title | `Autonomous IDX Research Triage` | The product turns that work into one research queue. |
| 00:14–00:24 | `assets/architecture.png` | `Configured weekday schedule — 07:17 WIB` | Sectors v2 supplies the core market evidence and the recurring workflow is configured. |
| 00:24–00:36 | `assets/dashboard.png`, then `assets/p1-card.png` | `SANITIZED HISTORICAL REPLAY — NOT LIVE MARKET DATA` | Canonical ticker correlation and an explainable score decide review order, not what to trade. |
| 00:36–00:46 | Two replay summaries / dashboard history | `Preview only — no external delivery` | First local replay: 16 new events and five preview cards; identical replay: 16 duplicates suppressed and zero previews. |
| 00:46–00:57 | Closing title | `Scheduled-run evidence pending account setup` when still true | MarketOps ID keeps the human responsible for investment decisions. |

## Judging video — 2 minutes 48 seconds

| Time | Visual | Evidence boundary | Intended message |
|---|---|---|---|
| 00:00–00:14 | Problem title | None | Important market evidence arrives through multiple views. |
| 00:14–00:28 | Architecture diagram | Repository diagram, not a run | Sectors v2 capabilities are the core data dependency. |
| 00:28–00:43 | Workflow YAML / architecture | `Configured locally; not scheduled-run proof` until real evidence exists | GitHub Actions is configured for weekdays at 07:17 WIB and persists state/artifacts. |
| 00:43–00:58 | Fixture dashboard | Fixture banner must remain legible | Fixture mode makes repeatable tests and demos possible without live credits. |
| 00:58–01:17 | P1 card + component list | Fixture banner | The Research Attention Score is deterministic and shows each reason. |
| 01:17–01:34 | Suspension card + disclaimer | `Research triage only` | Suspensions can force P1; this is not a trade recommendation. |
| 01:34–01:50 | Replay result | `Preview only — no external delivery` | SQLite fingerprints make a repeated data window quiet on the second run. |
| 01:50–02:12 | `assets/test-pass.png`, `assets/hosted-dedupe-qa.png`, then the pending schedule card | Label the first two as public CI/manual QA, **not** scheduled proof | Public engineering infrastructure works; three genuine schedule-triggered runs are still required for Track 2 qualification. |
| 02:12–02:31 | Real `scheduled-run.png`, artifact, and `discord-result.png` only if delivered | Match run ID, timestamp, mode, and trigger | Evidence must show the actual unattended run and truthful delivery outcome. |
| 02:31–02:48 | Closing dashboard/architecture frame | None | MarketOps transforms Sectors evidence into an auditable research queue. |

## Asset use rules

- `assets/dashboard.png` and `assets/p1-card.png` are local fixture captures.
- `assets/actions-history.png`, `assets/scheduled-run.png`, and
  `assets/discord-result.png` are clearly marked placeholders until replaced
  by real external evidence. They must not appear as proof.
- `assets/test-pass.png` records successful public push-triggered CI; it is not
  scheduled-run proof. `assets/test-pass.svg` is the local QA-only summary.
- `assets/hosted-dedupe-qa.png` summarizes the two linked public manual fixture
  runs and is visibly labeled non-qualifying QA.
- `marketops-*-visual-no-voice.mp4` files are visual timelines, not final
  public videos. Add narration and the corresponding captions before upload.

See [video-assembly.md](video-assembly.md) for capture hygiene and the two
timed scripts for narration.

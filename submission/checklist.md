# Final Submission Checklist

Snapshot date: **2026-08-27 WIB**. Checked items are repository facts verified
locally. Unchecked items require external credentials, future scheduler runs,
final media, or portal access. Re-run every check immediately before submission.

## Eligibility and Rules

- [x] Official homepage, rules, and Track 2 page re-verified on 2026-08-27.
- [x] Solo participation is allowed.
- [x] Solo participant explicitly confirmed Sectors onboarding was completed
  before implementation.
- [ ] `[BLOCKED: HUMAN ACTION REQUIRED]` Confirm Indonesian citizenship or
  residency and every other personal eligibility condition.
- [ ] Confirm participant is registered on only one team and submits only this
  project.
- [x] Repository creation and first commit are both dated 2026-08-27, within
  the official build period.
- [ ] Confirm the project is exclusive to this hackathon and not cross-submitted.
- [ ] Reopen official rules immediately before freeze and update
  `docs/rules-verification.md` if anything changed.

## Product and Sectors

- [x] Sectors Financial API v2 is the live core data source.
- [x] Filings ingestion implemented.
- [x] Suspensions ingestion implemented.
- [x] One-day top-mover ingestion implemented.
- [x] Batched news enrichment implemented.
- [x] Selective foreign-flow enrichment implemented.
- [x] Selective corporate-action enrichment implemented.
- [x] Exact endpoint, auth, parameter, field, cost, and failure map documented.
- [x] Canonical symbol and WIB timestamp normalization implemented.
- [x] Malformed record behavior implemented and tested.
- [x] Deterministic evidence correlation by ticker implemented.
- [x] Research Attention Score is config-driven and explainable.
- [x] Suspension override, thresholds, cap, priority boundaries, and input-order
  independence tested.
- [x] Score is consistently described as hackathon product heuristics, not a
  validated investment factor.
- [x] No BUY/SELL recommendation, target price, trading signal, brokerage
  credential, or order execution exists.

## State, Reliability, and Delivery

- [x] SHA-256 event fingerprint implemented.
- [x] Processed events, alerts, and full run history persist in SQLite.
- [x] State survives restart in tests.
- [x] Identical local replay suppresses every duplicate on run two.
- [x] Hard pre-request API-credit budget implemented.
- [x] Discovery is broad and per-ticker enrichment is capped/selective.
- [x] Timeout, bounded retry, exponential backoff, jitter, 429, 5xx, and
  `Retry-After` behavior tested.
- [x] Partial source failure keeps usable output and names the missing evidence.
- [x] Total discovery failure is never shown as an all-clear.
- [x] Discord and generic webhook payloads implemented.
- [x] Dry-notify preview implemented.
- [ ] `[BLOCKED: HUMAN ACTION REQUIRED]` Configure a real webhook in GitHub
  Secrets and capture successful external delivery.

## Dashboard and Artifacts

- [x] Read-only dashboard implemented.
- [x] P1/P2/P3 bands, run metrics, explanations, evidence, URLs, run ID,
  source health, credit use, and disclaimer render.
- [x] Fixture mode and every fixture artifact are visibly labeled replay.
- [x] JSON, standalone HTML, Markdown summary, notification preview, and run
  history can be generated.
- [ ] Verify every source link in the final **live** run artifact.
- [x] Local fixture dashboard and research-card images captured at presentation
  quality with the fixture-disclosure boundary documented in `assets/README.md`.

## Quality Gates

- [x] `ruff check .` passed locally on 2026-08-27.
- [x] `mypy src` passed locally on 2026-08-27 for 13 source files.
- [x] `pytest --cov=marketops --cov-report=term-missing` passed locally on
  2026-08-27: 375 tests, 95.08% coverage.
- [x] Unit and integration coverage includes scoring, normalization,
  deduplication, persistence, retry/failure mapping, pipeline, CLI, notifier,
  rendering, and dashboard.
- [x] CI workflow committed; public
  [run `33036454974`](https://github.com/respramon/marketops-id/actions/runs/33036454974)
  passed every quality gate, including installed-wheel smoke.
- [x] Public logged-out CI capture saved as
  `submission/assets/test-pass.png`; the separate local QA summary is
  `submission/assets/test-pass.svg`.

## Automation and Track 2 Proof

- [x] Scheduled workflow committed with weekday `00:17 UTC` / approximately
  `07:17 WIB` cron.
- [x] `workflow_dispatch` retained only for testing and clearly distinguished.
- [x] SQLite fixture state restore/save verified across separate hosted runners:
  [first run](https://github.com/respramon/marketops-id/actions/runs/33036266340)
  stored 16 new events; the
  [second](https://github.com/respramon/marketops-id/actions/runs/33036310666)
  restored them and suppressed all 16. This is QA, not Track 2 proof.
- [x] Workflow uploads logs, run summary, HTML, JSON metadata, and history.
- [x] GitHub step summary exposes run counters and artifact name.
- [ ] Genuine scheduled run 1 recorded in `evidence/unattended-runs.md`.
- [ ] Genuine scheduled run 2 recorded in `evidence/unattended-runs.md`.
- [ ] Genuine scheduled run 3 recorded in `evidence/unattended-runs.md`.
- [ ] Actions history screenshot visibly shows three `schedule` triggers.
- [ ] Detailed scheduled-run screenshot visibly shows trigger and timestamp.
- [ ] Judging video shows this evidence rather than only a manual dispatch.

## Security and Repository

- [x] Secrets load from environment variables / GitHub Secrets.
- [x] `.env`, databases, artifacts, keys, logs, and caches are ignored.
- [x] `doctor` reports presence/status without printing secret values.
- [x] Pre-publication working-tree and index credential scan returned zero
  strict-pattern matches on 2026-08-27.
- [x] Full Git-history scan returned zero strict-pattern matches at the latest
  pre-freeze checkpoint; repeat after the final freeze commit.
- [ ] If any secret was committed: stop, revoke and rotate it, clean history as
  appropriate before submission, and follow the official post-freeze exception
  if already submitted.
- [x] MIT license and demo-asset provenance are documented; no unlicensed
  third-party visual or font is bundled.
- [x] Repository created during the build period and project history pushed to
  `main`.
- [x] Public repository verified in a logged-out browser:
  <https://github.com/respramon/marketops-id>.
- [ ] Push the final freeze commit/tag and verify the public worktree state.
- [ ] Keep repository public for at least 90 days after the winner announcement.

## Demo Assets and Videos

- [x] `submission/assets/dashboard.png` captured from local sanitized replay.
- [x] `submission/assets/p1-card.png` captured from local sanitized replay.
- [ ] `submission/assets/actions-history.png` captured from real Actions.
- [ ] `submission/assets/scheduled-run.png` captured from a real schedule run.
- [ ] `submission/assets/discord-result.png` captured from real delivery.
- [x] `submission/assets/test-pass.png` captured from successful public CI;
  `test-pass.svg` retains the local QA summary.
- [x] `submission/assets/architecture.png` generated and reviewed.
- [x] 57-second teaser script, storyboard, and captions prepared.
- [x] 2:48 judging script, storyboard, and captions prepared.
- [x] Assembly and truth-labeling instructions prepared.
- [ ] Record and assemble teaser; verify duration is at most 60 seconds.
- [ ] Record and assemble judging video; verify duration is at most 3:00.
- [ ] Watch both final exports with audio and captions from start to finish.
- [ ] Inspect every frame for secrets, private browser data, and fixture/live
  ambiguity.
- [ ] `[BLOCKED: HUMAN ACTION REQUIRED]` Upload videos and verify anonymous
  link access.

## Portal and Social

- [x] One-sentence problem statement prepared.
- [x] Project description and Track 2 justification prepared.
- [x] Solo team snapshot template prepared.
- [x] Social post copy prepared without guessing the official handle.
- [ ] Insert registered participant name.
- [x] Public repository URL inserted:
  <https://github.com/respramon/marketops-id>.
- [ ] Insert final teaser URL and judging video URL.
- [ ] Verify official Sectors social handle and replace placeholder.
- [ ] `[BLOCKED: HUMAN ACTION REQUIRED]` Publish social post and save its URL.
- [ ] `[BLOCKED: HUMAN ACTION REQUIRED]` Complete portal fields and uploads.

## Final Freeze Sequence

- [ ] Verify official rules and portal requirements once more.
- [ ] Run `ruff check .`.
- [ ] Run `mypy src`.
- [ ] Run `pytest --cov=marketops --cov-report=term-missing`.
- [ ] Run fixture mode twice against a clean dedicated database; verify first
  run creates notifiable cards and second run sends/renders zero while
  suppressing duplicates.
- [ ] Run `marketops doctor`.
- [ ] Run authenticated `marketops run --mode live --dry-notify` smoke test.
- [ ] Verify final CI is green and all public links work anonymously.
- [ ] Run final security and content audit.
- [ ] Commit final version, push, tag the submission version, and verify a clean
  Git worktree.
- [ ] Decide whether to disable production scheduling at freeze; document the
  decision without modifying the project after submission.
- [ ] Submit through the authenticated portal only after every prior required
  item is complete.
- [ ] After submitting, make no code, app, documentation, or asset changes
  unless following the official credential-leak exception.

## Current Human Gate

`[BLOCKED: HUMAN ACTION REQUIRED]` Add `SECTORS_API_KEY` and either
`DISCORD_WEBHOOK_URL` or `GENERIC_WEBHOOK_URL` as repository Actions Secrets.
The public repository, CI, and fixture workflow are already operational; this
single account-owner action unlocks live smoke testing, scheduled-run evidence,
webhook evidence, and final recording.

# Final Submission Checklist

Snapshot date: **2026-08-28 WIB**. Checked items are repository facts verified
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
- [x] `SECTORS_API_KEY` remains configured as a GitHub Actions Secret; its
  value was not retrieved or printed.
- [ ] `[BLOCKED: HUMAN ACTION REQUIRED AFTER REMEDIATION]` Create a new Discord
  webhook and configure `DISCORD_WEBHOOK_URL`; the stale secret was deleted.
- [x] Historical Discord delivery verified before containment in manual run
  [`33040201783`](https://github.com/respramon/marketops-id/actions/runs/33040201783):
  16 research cards across three limit-safe messages. Its affected source
  artifact was later deleted under SEC-001 and is not current safe proof.
- [x] Identical live replay
  [`33040251479`](https://github.com/respramon/marketops-id/actions/runs/33040251479)
  restored production state, suppressed 77 duplicates, and sent zero alerts.
- [x] Partial-batch delivery behavior keeps the full alert set eligible for an
  at-least-once retry; the original HTTP 400 and successful fixed retry are
  recorded in `evidence/manual-live-qa.md`.
- [ ] Commit, push, and publicly CI-verify the secret-redacting logger plus
  pre-upload artifact scrub.
- [ ] Run one controlled delivery with a new webhook; independently scan its
  job log and every artifact file before restoring Notification to PASS.

## Dashboard and Artifacts

- [x] Read-only dashboard implemented.
- [x] P1/P2/P3 bands, run metrics, explanations, evidence, URLs, run ID,
  source health, credit use, and disclaimer render.
- [x] Fixture mode and every fixture artifact are visibly labeled replay.
- [x] JSON, standalone HTML, Markdown summary, notification preview, and run
  history can be generated.
- [ ] Verify every source link in the final **scheduled live** run artifact.
- [x] Local fixture dashboard and research-card images captured at presentation
  quality with the fixture-disclosure boundary documented in `assets/README.md`.
- [x] Authenticated live reports were generated through public Actions; manual
  trigger is disclosed and not presented as scheduled proof.
- [ ] Generate a replacement clean live-delivery artifact after SEC-001. The
  affected historical delivery artifacts were deleted.

## Quality Gates

- [x] `ruff check .` passed locally on 2026-08-28.
- [x] `mypy src` passed locally on 2026-08-28 for 14 source files.
- [x] `pytest --cov=marketops --cov-report=term-missing` passed locally on
  2026-08-28: 400 tests, 95.62% coverage.
- [x] Unit and integration coverage includes scoring, normalization,
  deduplication, persistence, retry/failure mapping, pipeline, CLI, notifier,
  rendering, and dashboard.
- [x] CI workflow committed; public
  [run `33040157886`](https://github.com/respramon/marketops-id/actions/runs/33040157886)
  passed every quality gate, including installed-wheel smoke.
- [x] `submission/assets/test-pass.svg` and `test-pass-local.png` show the
  current local 400-test / 95.62% result.
- [x] `submission/assets/test-pass.png` remains the truthful public CI capture
  for `33040157886` at 378 tests / 94.93% coverage.
- [ ] Replace the public CI capture after the security remediation is pushed
  and its new hosted run passes.

## Automation and Track 2 Proof

- [x] Scheduled workflow committed with weekday `00:17 UTC` / approximately
  `07:17 WIB` cron.
- [x] Scheduler disabled manually during SEC-001 containment.
- [x] Scheduler re-enabled on 2026-08-28 after clean replacement webhook run
  [`33155463943`](https://github.com/respramon/marketops-id/actions/runs/33155463943) delivered 18 cards with a webhook-free artifact.
- [x] `workflow_dispatch` retained only for testing and clearly distinguished.
- [x] SQLite fixture state restore/save verified across separate hosted runners:
  [first run](https://github.com/respramon/marketops-id/actions/runs/33036266340)
  stored 16 new events; the
  [second](https://github.com/respramon/marketops-id/actions/runs/33036310666)
  restored them and suppressed all 16. This is QA, not Track 2 proof.
- [x] Workflow uploads logs, run summary, HTML, JSON metadata, and history.
- [x] Historical authenticated live `workflow_dispatch` QA exercised Sectors
  ingestion, production-state restore, Discord delivery, and a quiet replay.
  These runs are linked separately, affected artifacts are retired/deleted,
  and none is counted as scheduler proof.
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
- [x] SEC-001 recorded: five full webhook-URL occurrences were confirmed across
  three public `workflow.log` artifacts.
- [x] All three affected artifacts deleted irreversibly; sensitive local log
  copies deleted; old webhook revoked with HTTP 204; stale Discord secret
  deleted; scheduler disabled.
- [x] Six remaining MarketOps artifacts (38 files) and 9/9 accessible job logs
  scanned after containment with zero findings for the defined secret patterns.
- [ ] Redacting formatter, quiet HTTP transport logging, and fail-on-redaction
  artifact scrub committed and pushed.
- [ ] Post-remediation public CI and clean replacement artifact verified.
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
- [x] `submission/assets/discord-result.png` / `.svg` now disclose historical
  manual QA and SEC-001 containment; they are **not current safe delivery proof**.
- [ ] Replace or supplement the historical Discord summary with a clean
  post-remediation result before final video assembly.
- [x] Local test assets refreshed for 400 tests / 95.62%; public
  `test-pass.png` remains the prior 378-test CI capture until replacement CI.
- [x] `submission/assets/architecture.png` generated and reviewed.
- [x] 57-second teaser script and storyboard updated for SEC-001 status.
- [x] 2:48 judging script and storyboard updated for SEC-001 status.
- [ ] Regenerate both caption files to match the revised incident-aware
  narration before final assembly.
- [x] Assembly and truth-labeling instructions prepared.
- [ ] Rebuild both no-voice visual timelines from the incident-aware storyboard.
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
- [x] Authenticated manual live dry-notify smoke test completed in public run
  [`33039796607`](https://github.com/respramon/marketops-id/actions/runs/33039796607).
- [ ] Re-run authenticated live dry-notify only if needed at final freeze; avoid
  spending credits merely to repeat an unchanged passing check.
- [ ] Verify final CI is green and all public links work anonymously.
- [ ] Run final security and content audit.
- [ ] Verify a newly issued webhook never appears in console logs, downloaded
  artifacts, screenshots, or video frames.
- [ ] Commit final version, push, tag the submission version, and verify a clean
  Git worktree.
- [ ] Decide whether to disable production scheduling at freeze; document the
  decision without modifying the project after submission.
- [ ] Submit through the authenticated portal only after every prior required
  item is complete.
- [ ] After submitting, make no code, app, documentation, or asset changes
  unless following the official credential-leak exception.

## Current Human Gate

`[BLOCKED: AWAITING SCHEDULED RUNS + HUMAN ACTION REQUIRED]` The two-layer
SEC-001 fix is published and CI-verified (run 33153711435), a new Discord webhook is
stored only as a GitHub Secret, its clean manual delivery artifact was
inspected (run 33155463943: 18 cards, zero errors, no webhook material), and
the scheduler is re-enabled. Three later genuine `schedule` events must still
be collected (first possible fire: Monday 2026-08-31, 07:17 WIB).
Citizenship/team declarations, final video recording/upload, social post, and
portal submission still require the owner.

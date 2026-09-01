# Unattended Run Evidence

## Track 2 Qualification

**Status: `PASS` for the three run records; screenshots still pending.**

Three genuine GitHub Actions executions whose triggering event is exactly
`schedule` completed successfully and are recorded below. Every value was
transcribed mechanically from each run's own uploaded artifact by
`scripts/capture_schedule_evidence.py`, which refuses to record a run unless
the GitHub event and the artifact's own `trigger` field both read `schedule`
and the mode reads `live`. No manual or fixture execution was substituted.

Deduplication is demonstrated across the unattended cycles rather than
asserted: run 1 saw 63 events (59 new, 4 suppressed), run 2 saw 80 events and
suppressed 40 duplicates carried over from run 1, and run 3 saw 84 events and
suppressed 30. Each run stayed inside its 15/15 credit budget and returned
`PARTIAL`, which is the intended fail-soft verdict for the explicit one-page
news cap, not an error.

Two disclosures, so the record cannot be read as stronger than it is. First,
the two 31 August firings came from a temporary observation-window cron
(`7,17,27 4 * * 1`, commit `10ff99b`) added to shorten the post-remediation
wait; they are still genuine unattended `schedule` events using production
state and the same safeguards, not manual dispatches. Second, GitHub's
scheduler delivered all three later than their cron minute, which is normal
hosted-cron behaviour; the times in each table are the artifact's real
start/finish stamps, not the cron's nominal time.

Security: each artifact was downloaded and scanned twice before recording, by
the shared `marketops.security` scanner and by an independent regex in the
capture script. All three returned zero webhook-URL matches, confirming the
SEC-001 fix holds on unattended live deliveries.

Remaining: the screenshot rows are deliberately left `[BLOCKED: ...]` because
a human must capture the Actions history/detail images.

## Genuine Scheduled Run 1

| Field | Evidence |
|---|---|
| Run ID | `33360850299` |
| Trigger type | `schedule` (confirmed by GitHub event and run artifact) |
| Started time | `2026-08-31T12:31:55.159439+07:00` |
| Finished time | `2026-08-31T12:32:01.467645+07:00` |
| Mode | `live` |
| Status | `PARTIAL` |
| Events detected | 63 |
| New events | 59 |
| Duplicate events suppressed | 4 |
| Notifications sent | 8 |
| Estimated API credits | 15/15 |
| Artifact name | `marketops-schedule-live-33360850299-1` |
| Workflow run URL | [33360850299](https://github.com/respramon/marketops-id/actions/runs/33360850299) |
| Screenshot | `[BLOCKED: submission/assets/scheduled-run.png]` |

Verification note: Artifact `marketops-schedule-live-33360850299-1` was downloaded and scanned on capture: zero webhook-URL matches from both the shared redaction scanner and an independent regex.

## Genuine Scheduled Run 2

| Field | Evidence |
|---|---|
| Run ID | `33383915122` |
| Trigger type | `schedule` (confirmed by GitHub event and run artifact) |
| Started time | `2026-08-31T17:46:36.024039+07:00` |
| Finished time | `2026-08-31T17:46:41.997574+07:00` |
| Mode | `live` |
| Status | `PARTIAL` |
| Events detected | 80 |
| New events | 40 |
| Duplicate events suppressed | 40 |
| Notifications sent | 9 |
| Estimated API credits | 15/15 |
| Artifact name | `marketops-schedule-live-33383915122-1` |
| Workflow run URL | [33383915122](https://github.com/respramon/marketops-id/actions/runs/33383915122) |
| Screenshot | `[BLOCKED: include in submission/assets/actions-history.png]` |

Verification note: Artifact `marketops-schedule-live-33383915122-1` was downloaded and scanned on capture: zero webhook-URL matches from both the shared redaction scanner and an independent regex.

## Genuine Scheduled Run 3

| Field | Evidence |
|---|---|
| Run ID | `33472247776` |
| Trigger type | `schedule` (confirmed by GitHub event and run artifact) |
| Started time | `2026-09-01T12:05:28.849883+07:00` |
| Finished time | `2026-09-01T12:05:34.790718+07:00` |
| Mode | `live` |
| Status | `PARTIAL` |
| Events detected | 84 |
| New events | 54 |
| Duplicate events suppressed | 30 |
| Notifications sent | 16 |
| Estimated API credits | 15/15 |
| Artifact name | `marketops-schedule-live-33472247776-1` |
| Workflow run URL | [33472247776](https://github.com/respramon/marketops-id/actions/runs/33472247776) |
| Screenshot | `[BLOCKED: include in submission/assets/actions-history.png]` |

Verification note: Artifact `marketops-schedule-live-33472247776-1` was downloaded and scanned on capture: zero webhook-URL matches from both the shared redaction scanner and an independent regex.

## Non-Qualifying Local Replay Already Verified

The following is useful proof of deterministic end-to-end behavior, but it is
**not Track 2 unattended evidence**.

```text
SANITIZED HISTORICAL REPLAY - NOT LIVE MARKET DATA
Used for deterministic testing and demo.
```

| Metric | First replay | Identical second replay |
|---|---:|---:|
| Run ID | `run-20260827-095935-ff4937` | `run-20260827-095935-233846` |
| Trigger | `manual-demo` | `manual-demo` |
| Status | `OK` | `OK` |
| Started (WIB) | `2026-08-27T09:59:35+07:00` | `2026-08-27T09:59:35+07:00` |
| Finished (WIB) | `2026-08-27T09:59:35+07:00` | `2026-08-27T09:59:35+07:00` |
| Events detected | 16 | 16 |
| New events | 16 | 0 |
| Duplicate events suppressed | 0 | 16 |
| Candidates | 7 | 7 |
| Enriched tickers | 5 | 5 |
| Notification field | 5 dry-preview cards; 0 actual deliveries | 0 preview cards; 0 actual deliveries |
| Actual external deliveries | 0 | 0 |
| Equivalent live credits estimated | 15 | 15 |
| Actual Sectors credits consumed | 0 | 0 |

The first replay used dry-notify and wrote a payload preview. The second found
no new evidence, so the notifiable set was empty. This proves stateful replay
suppression without claiming a webhook delivery or a scheduled trigger.

## Non-Qualifying Public Hosted-Runner QA

These public GitHub Actions executions validate the production-shaped runner,
wheel installation, artifact upload, and state cache. Their event is
`workflow_dispatch`, so they are deliberately excluded from the three Track 2
qualification slots above.

| Field | Hosted run 1 | Identical hosted run 2 |
|---|---|---|
| Public workflow run | [`33036266340`](https://github.com/respramon/marketops-id/actions/runs/33036266340) | [`33036310666`](https://github.com/respramon/marketops-id/actions/runs/33036310666) |
| GitHub event / pipeline trigger | `workflow_dispatch` / `manual` | `workflow_dispatch` / `manual` |
| Mode / notify policy | `fixture` / dry preview | `fixture` / dry preview |
| Pipeline run ID | `run-20260827-102440-9b320b` | `run-20260827-102530-6eca07` |
| Started (WIB) | `2026-08-27T10:24:40+07:00` | `2026-08-27T10:25:30+07:00` |
| Status | `OK` | `OK` |
| Events / new / duplicates | 16 / 16 / 0 | 16 / 0 / 16 |
| Dry previews / actual deliveries | 5 / 0 | 0 / 0 |
| Estimated-equivalent credits | 15 | 15 |
| State evidence | Saved key ending `33036266340-1` | Restored the key ending `33036266340-1`, then saved a new key |
| Artifact | `marketops-manual-fixture-33036266340-1` | `marketops-manual-fixture-33036310666-1` |

The second artifact's `run-history.json` contains both pipeline runs in order.
This proves SQLite state survived a hosted-runner restart and that the duplicate
policy suppresses the full notifiable set. It does **not** prove schedule
triggering, live Sectors authentication, or webhook delivery.

## Non-Qualifying Manual Live and Delivery QA

Authenticated live Sectors ingestion and historical Discord delivery are
documented separately in [`manual-live-qa.md`](manual-live-qa.md). The delivery
run sent 16 research cards across three messages and its replay suppressed 77
duplicates, but affected artifacts were deleted after the webhook URL leak was
confirmed. Both were `workflow_dispatch`, neither fills a genuine scheduled
slot, and neither replaces a clean post-remediation delivery artifact.

## One Required Human Action

After the remediation is committed, pushed, and CI-verified, create and store a
new Discord webhook through the account owner. Inspect one controlled manual
delivery artifact, then re-enable the weekday schedule. After three genuine
`schedule` runs appear, copy each blocked field above directly from its JSON
artifact and public run page. Capture the Actions history and one run detail
without exposing any secret, and keep all manual runs outside the qualification
slots.

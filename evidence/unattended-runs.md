# Unattended Run Evidence

## Track 2 Qualification

**Status: `[BLOCKED: HUMAN ACTION REQUIRED]`**

As of 2026-08-27, no genuine scheduled run has been observed. The three entries
below are intentionally unfilled. They must be populated from real `schedule`
runs; manual or fixture executions must not be substituted. An authenticated
Sectors key and a real webhook destination are still required to produce live
delivery evidence.

## Genuine Scheduled Run 1

| Field | Evidence |
|---|---|
| Run ID | `[BLOCKED: waiting for first schedule execution]` |
| Trigger type | Must be `schedule` |
| Started time | `[BLOCKED: copy exact timestamp from run JSON]` |
| Finished time | `[BLOCKED: copy exact timestamp from run JSON]` |
| Mode | Must be `live` |
| Status | `[BLOCKED: actual OK/PARTIAL/FAILED result]` |
| Events detected | `[BLOCKED: actual counter]` |
| New events | `[BLOCKED: actual counter]` |
| Duplicate events suppressed | `[BLOCKED: actual counter]` |
| Notifications sent | `[BLOCKED: actual counter and delivery semantics]` |
| Estimated API credits | `[BLOCKED: actual value/budget]` |
| Artifact name | `[BLOCKED: exact GitHub artifact name]` |
| Workflow run URL | `[BLOCKED: public GitHub Actions URL]` |
| Screenshot | `[BLOCKED: submission/assets/scheduled-run.png]` |

Verification note: _pending._

## Genuine Scheduled Run 2

| Field | Evidence |
|---|---|
| Run ID | `[BLOCKED: waiting for second schedule execution]` |
| Trigger type | Must be `schedule` |
| Started time | `[BLOCKED: copy exact timestamp from run JSON]` |
| Finished time | `[BLOCKED: copy exact timestamp from run JSON]` |
| Mode | Must be `live` |
| Status | `[BLOCKED: actual OK/PARTIAL/FAILED result]` |
| Events detected | `[BLOCKED: actual counter]` |
| New events | `[BLOCKED: actual counter]` |
| Duplicate events suppressed | `[BLOCKED: actual counter]` |
| Notifications sent | `[BLOCKED: actual counter and delivery semantics]` |
| Estimated API credits | `[BLOCKED: actual value/budget]` |
| Artifact name | `[BLOCKED: exact GitHub artifact name]` |
| Workflow run URL | `[BLOCKED: public GitHub Actions URL]` |
| Screenshot | `[BLOCKED: include in submission/assets/actions-history.png]` |

Verification note: _pending._

## Genuine Scheduled Run 3

| Field | Evidence |
|---|---|
| Run ID | `[BLOCKED: waiting for third schedule execution]` |
| Trigger type | Must be `schedule` |
| Started time | `[BLOCKED: copy exact timestamp from run JSON]` |
| Finished time | `[BLOCKED: copy exact timestamp from run JSON]` |
| Mode | Must be `live` |
| Status | `[BLOCKED: actual OK/PARTIAL/FAILED result]` |
| Events detected | `[BLOCKED: actual counter]` |
| New events | `[BLOCKED: actual counter]` |
| Duplicate events suppressed | `[BLOCKED: actual counter]` |
| Notifications sent | `[BLOCKED: actual counter and delivery semantics]` |
| Estimated API credits | `[BLOCKED: actual value/budget]` |
| Artifact name | `[BLOCKED: exact GitHub artifact name]` |
| Workflow run URL | `[BLOCKED: public GitHub Actions URL]` |
| Screenshot | `[BLOCKED: include in submission/assets/actions-history.png]` |

Verification note: _pending._

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

## One Required Human Action

Add `SECTORS_API_KEY` and one webhook secret to the repository's GitHub Actions
Secrets, then leave the weekday schedule active until three runs appear; replace
all blocked fields above directly from their JSON artifacts and public run
pages. Never put either secret into this repository or an evidence artifact.

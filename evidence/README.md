# Automation Evidence Pack

This directory is the index for proof that MarketOps ID performs a recurring,
zero-click workflow. It deliberately separates deterministic local validation
from qualifying Track 2 evidence.

## Qualification Status

`[BLOCKED: HUMAN ACTION REQUIRED]`

The repository does not yet contain evidence of a genuine scheduled GitHub
Actions run. Manual runs, tests, dry-notify previews, and fixture replay are
valuable engineering evidence but do **not** prove unattended automation.

At this snapshot, the local repository has no commit history, configured
remote, API key, or webhook secret available for inspection. Therefore no
public GitHub run URL, authenticated Sectors execution, or real delivery may be
inferred from the local workflow files or artifacts.

The account owner must push the project to a public GitHub repository, configure
the required GitHub Secrets, enable Actions, and let at least three weekday
`schedule` executions complete before replacing this status.

## Evidence Standard

A qualifying run must have all of the following:

- GitHub Actions event/trigger is `schedule`, not `workflow_dispatch`.
- The workflow file and Actions UI show the weekday cron configuration.
- The log records a unique run ID plus start and finish timestamps.
- The run artifact contains JSON metadata, a standalone HTML report, Markdown
  summary, run history, and logs.
- The metadata states `mode: live`; fixture output cannot be presented as live.
- Source health and estimated API credits are visible.
- The restored SQLite state predates the run and the updated state is persisted
  for the next run.
- Notification delivery is visible when there is new qualifying evidence, or a
  truthful zero-notification reason is shown.
- No screenshot, log, or artifact exposes an API key or webhook URL.

Three separate scheduler firings should be recorded in
[`unattended-runs.md`](unattended-runs.md). A single screenshot of Actions
history may establish the series, but each run still needs its own ID, timing,
counters, artifact name, and accessible run URL.

## Required Capture Set

| File | Must show | Truth requirement |
|---|---|---|
| `submission/assets/actions-history.png` | At least three completed runs whose event is `schedule` | Capture from the real public repository |
| `submission/assets/scheduled-run.png` | One scheduled run detail page with workflow name, status, timestamp, and event | Do not substitute a manual dispatch |
| `submission/assets/discord-result.png` | Real delivered research queue and timestamp | Redact the webhook URL; never mock this as delivered |
| `submission/assets/dashboard.png` | Latest **live** scheduled run, source health, and summary metrics | The visible mode/trigger must match the run artifact |
| `submission/assets/p1-card.png` | A real or clearly labeled fixture P1 explanation | If fixture-based, keep the replay banner in frame |
| `submission/assets/test-pass.png` | Required lint, type, tests, coverage output or green CI job | Coverage value must match the captured run |
| `submission/assets/architecture.png` | Architecture diagram | May be generated from repository documentation |

## Artifact Cross-Check

For every scheduled run, reviewers should be able to match the same `run_id`
in four places:

1. structured workflow logs;
2. `<run_id>.json` inside the uploaded artifact;
3. `<run_id>.html` or `<run_id>-summary.md`;
4. the dashboard or `/api/runs` history after restoring the same SQLite state.

The workflow run URL and artifact name should be recorded before artifacts
expire. Download the final three evidence artifacts into private archival
storage as well; do not commit a database containing secrets or unrelated data.

## Safe Capture Procedure

1. Confirm the run was triggered by `schedule` and used `mode: live`.
2. Open the JSON artifact and verify source states, timestamp timezone, credit
   estimate, and disclaimer.
3. Inspect logs for accidental credential output before recording or sharing.
4. Capture the Actions history, one run detail, the HTML report/dashboard, and
   any real webhook result.
5. Record the exact values in `unattended-runs.md`; never transcribe from memory.
6. Add permanent public video and repository links only after uploads succeed.

## Fixture Evidence Policy

Fixture runs must always display:

```text
SANITIZED HISTORICAL REPLAY - NOT LIVE MARKET DATA
Used for deterministic testing and demo.
```

In fixture mode, `estimated_api_credits` is the simulated cost of equivalent
live requests. Actual Sectors credit consumption is zero because no network
request occurs. A dry-notify count represents cards rendered for preview, not
messages delivered to an external channel.

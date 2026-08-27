# Video Assembly and Truth-Labeling Guide

This guide covers the 57-second teaser and the 2:48 judging video. It does not
authorize substituting a manual run, fixture replay, mock notification, or a
workflow configuration screen for live scheduled-run proof.

## Before Recording

1. Start from the matching script and captions in this directory.
2. Inspect every source screen for browser profiles, API keys, webhook URLs,
   private repositories, hidden tabs, and notification previews that could be
   mistaken for a real delivery.
3. For fixture media, keep this exact banner legible in the frame:

   ```text
   SANITIZED HISTORICAL REPLAY - NOT LIVE MARKET DATA
   Used for deterministic testing and demo.
   ```

4. For Track 2 qualification media, verify the evidence first against
   `evidence/unattended-runs.md`. The action event must be `schedule`, the mode
   must be `live`, and the run ID/timestamps/artifact name must agree.

## Required Labels

| Surface | Required label |
|---|---|
| Fixture dashboard, report, replay, or notification preview | `SANITIZED HISTORICAL REPLAY - NOT LIVE MARKET DATA` |
| Manual GitHub Actions dispatch | `Manual test — not scheduled-run proof` |
| Workflow YAML or architecture diagram before a real schedule run | `Configured locally — scheduled-run evidence pending` |
| Dry-notify preview | `Preview only — no external delivery` |
| Real schedule artifact | Show the actual `schedule` trigger, `live` mode, run ID, and timestamp; do not add an unsupported claim. |
| Real webhook result | `Delivered` only when the run artifact and destination visibly confirm it; otherwise state the actual failure/zero-delivery reason. |

## Assembly Sequence

1. Record clean source clips at 1080p. Keep critical UI text readable at the
   final export resolution.
2. Add narration according to the timestamped script, then import the matching
   `.srt` file without changing its timing unless the narration is re-recorded.
3. Use only simple cuts or short fades; do not obscure required labels with
   transitions, captions, or a presenter overlay.
4. Export the teaser at no more than 60 seconds and the judging video at no
   more than 3 minutes. Watch both exports end-to-end with audio and captions.
5. Re-verify the repository and every video link in a logged-out browser. The
   repository is already public; each unpublished video remains
   `[BLOCKED: HUMAN ACTION REQUIRED]`.

## Evidence Gates Before Publishing

- `SECTORS_API_KEY`: `[BLOCKED]` until supplied by the account owner through a
  local ignored environment file or GitHub Secret; never record or publish it.
- Webhook delivery: `[BLOCKED]` until a configured secret produces a real,
  reviewable delivery. A dry-notify card is not delivery evidence.
- Genuine GitHub Actions scheduled runs: `[BLOCKED]` until three real `schedule`
  events have been recorded in `evidence/unattended-runs.md`.
- Public repository: `[PASS]` at <https://github.com/respramon/marketops-id>,
  verified logged out on 2026-08-27.
- Public/unlisted video links: `[PENDING]` until uploaded and accessible without
  the owner's login.

If any gate is still blocked, retain the pending disclosure in the judging
video and do not claim completion of that external step.

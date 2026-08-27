# Demo Asset Provenance

Assets in this folder are intentionally separated by evidence type.

| Asset | Status | Provenance / permitted claim |
|---|---|---|
| `dashboard.png` | LOCAL FIXTURE CAPTURE | Captured from the running read-only dashboard after a sanitized historical replay. Its visible replay banner means it is not live market data or scheduled-run proof. |
| `p1-card.png` | LOCAL FIXTURE CAPTURE | Cropped P1 research card from the same fixture dashboard. Use only alongside the fixture disclosure. |
| `architecture.png` / `architecture.svg` | REPOSITORY DIAGRAM | Code-native architecture diagram. It says the schedule is configured, not proven. |
| `actions-history.png` | PENDING PLACEHOLDER | Must be replaced by a real public GitHub Actions history after three `schedule` runs. Do not use as proof. |
| `scheduled-run.png` | PENDING PLACEHOLDER | Must be replaced by a real detail page for a live schedule run. Do not use as proof. |
| `discord-result.png` | PENDING PLACEHOLDER | Must be replaced only by a real delivered notification; dry preview is not delivery. |
| `test-pass.png` / `test-pass.svg` | LOCAL QA CAPTURE | Captured 27 Aug 2026 WIB after Ruff, mypy, and pytest passed: 375 tests and 95.08% coverage. It visibly says it is not GitHub Actions CI. |

The visual-only MP4 files in `submission/` are intentionally named
`no-voice`. They are assembly timelines, not public submission videos. Add the
approved narration and the matching SRT files, then replace pending evidence
shots before uploading.

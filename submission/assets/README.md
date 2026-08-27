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
| `test-pass.png` | PUBLIC CI CAPTURE | Logged-out capture of successful public [GitHub Actions run `33036454974`](https://github.com/respramon/marketops-id/actions/runs/33036454974) for commit `841b55f`. The run passed Ruff, mypy, pytest/coverage, and installed-wheel smoke. It is push-triggered CI, not scheduled-run proof. |
| `test-pass.svg` | LOCAL QA SUMMARY | Code-native local summary captured 27 Aug 2026 WIB after Ruff, mypy, and pytest passed: 375 tests and 95.08% coverage. It is not GitHub Actions evidence. |
| `hosted-dedupe-qa.png` / `hosted-dedupe-qa.svg` | PUBLIC MANUAL QA SUMMARY | Derived only from the two public `workflow_dispatch` fixture artifacts. It shows state restoration and duplicate suppression, and visibly states that it is not scheduled-run proof. |

The visual-only MP4 files in `submission/` are intentionally named
`no-voice`. They are assembly timelines, not public submission videos. Add the
approved narration and the matching SRT files, then replace pending evidence
shots before uploading.

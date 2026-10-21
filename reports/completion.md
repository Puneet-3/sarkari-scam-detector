# Completion and verification report

Completed on 2026-10-21, using the project Python 3.13 virtual environment and locally installed Playwright/Chromium.

## Hindi implementation

- Enabled native Hindi inference instead of a blanket unsupported-script result.
- Added 210 documented synthetic Hindi development examples: 84 authored government-scheme scenarios and 126 selected examples from a pinned CC-BY-4.0 public corpus.
- Added Hindi urgency recognition, Devanagari digit/currency normalization, character features and category/script-balanced weighting.
- Retained uncertainty for short, unfamiliar, low-confidence and unsupported-script inputs.
- Development Hindi validation: 39/42 correct scam/legitimate predictions (92.86%); 28/42 correct categories (66.67%). This small synthetic split was inspected during development, so it does not establish real Hindi traffic accuracy.

See [data provenance](../data/README.md) and [model evaluation](../backend/artifacts/evaluation.json).

## Independent real-message evaluation

- Downloaded the UCI SMS Spam Collection with pinned checksums and attribution.
- Kept it out of model fitting, cross-validation and threshold selection.
- Evaluated the actual API policy on 5,129 normalized unique, nonempty historical real English messages; no development-corpus overlap.
- Coverage: 34.22%. Accuracy among classified messages: 78.63%. Spam detection recall, counting abstentions as undetected: 1.27%. Spam incorrectly labelled legitimate: 375/628.
- These labels describe spam, not verified fraud. The benchmark is outside the app's intended government-scheme domain and contains no real native-Hindi SMS. The result exposes weak transfer and does not justify deployment accuracy claims.

See the [external evaluation report](external_evaluation.md) and [full metrics/fingerprints](../backend/artifacts/external_evaluation.json). Model weights were not changed after observing this benchmark.

## Browser and regression checks

| Checks | Result |
| --- | --- |
| Python backend, storage, data separation and Hindi regressions | 25 passed |
| JavaScript rendering, uncertainty, exports and stale responses | 6 passed |
| Chromium desktop, 1440 x 1000 | 8 passed |
| Chromium mobile emulation, 390 x 844 | 8 passed |
| Total | 47 passed |

Browser checks cover Hindi legitimate/scam results, unknown-message abstention, mixed-language CSV upload/download, formula escaping, invalid uploads, literal rendering of hostile HTML, delayed-request clearing, all navigation panes, analytics privacy, viewport overflow and unavailable chart-CDN fallback. No uncaught page errors occurred. Disposable analytics keep browser tests away from the user's history.

Screenshots were inspected. Mobile navigation was changed to a fully visible two-column layout, and mobile batch rows now show the message, verdict, category and confidence together. The page identifies the model as a research prototype rather than claiming verification.

Representative screenshots:

- [Desktop Hindi checker](visual/desktop-chromium-hindi-scam.png)
- [Mobile Hindi checker](visual/mobile-chromium-hindi-scam.png)
- [Mobile batch results](visual/mobile-chromium-batch.png)
- [Desktop analytics](visual/desktop-chromium-analytics.png)
- [Mobile analytics](visual/mobile-chromium-analytics.png)
- [Awareness examples](visual/desktop-chromium-awareness.png)

The generated Playwright HTML report is at `playwright-report/index.html`. The test suite is in `tests/browser.spec.cjs` and can be repeated with `npm run test:browser`. Screenshots are rendered output, not pixel-difference baselines. Safari, Firefox and physical-device behavior were not certified.

## Reliability boundary

The three requested work items have implementations and reproducible evidence. They do not establish production reliability. Better independent, real, in-domain government-scam and Hindi data are still needed; the poor external result is preserved rather than replaced with synthetic accuracy claims.

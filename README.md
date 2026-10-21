# Sarkari Scam Detector

A local Flask dashboard for spotting suspicious government-scheme messages in Hindi, Hinglish and English. It includes single-message checks, CSV processing, privacy-preserving analytics, and illustrative scam-awareness examples.

## Run on Windows

From the project directory, use the existing environment:

```powershell
.\backend\.venv\Scripts\python.exe backend/app.py
```

Open **http://127.0.0.1:5000**. Flask serves both the dashboard and API; do not open `frontend/index.html` directly. Startup works from the project root, the backend directory, or another directory when using the script's full path.

For a new checkout, create an environment first (tested with Python 3.13):

```powershell
py -3.13 -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\backend\.venv\Scripts\python.exe backend/fetch_data.py
.\backend\.venv\Scripts\python.exe backend/train_model.py
.\backend\.venv\Scripts\python.exe backend/evaluate_external.py
.\backend\.venv\Scripts\python.exe backend/app.py
```

This is a local application, bound to loopback with debug mode disabled. It has no account system. The default origin policy permits the dashboard served by Flask; another frontend requires explicit, comma-separated origins in `SCAM_ALLOWED_ORIGINS` before starting the server. Never set this to a wildcard.

## Vercel preview deployment

Current preview: [Open Sarkari Scam Detector](https://sarkari-scam-detector-el04es4nd-puneet-s-projects46.vercel.app). Deployment status and the styled, interactive desktop/mobile page were verified on 2026-10-22. Vercel authentication protects this preview; sign in with an authorized account to open it. See `reports/vercel-deployment.md` for deployment evidence.

The project includes a Flask entrypoint (`index.py`), Python 3.13 runtime dependencies, and `vercel.json`. CSS/JavaScript source files live in `public/static/`; dataset attribution is in `public/data-sources.txt`. These files must exist before deployment so Vercel discovers their CDN routes. Local Flask serves the same assets. `scripts/build_vercel.py` validates the public files, their local response types, and model readiness. The same model artifacts and dependency versions are used locally and in the preview; Vercel does not retrain the model.

```powershell
vercel deploy --environment preview --scope puneet-s-projects46 -y --no-wait
```

`.vercelignore` excludes training datasets, local analytics, the private recovery backup, virtual environments, tests, and credential files. Check the complete upload manifest with `vercel deploy --dry --json` before deploying. No model reliability claim is added by deploying the research prototype.

On Vercel, analytics uses the writable temporary directory and retains up to the latest 1,000 records per instance. Statistics may reset or differ across instances; they are not durable global totals. The dashboard states this limitation. Local runs continue using `backend/analytics.json`. HTTPS origin checks account for Vercel's TLS proxy. Persistent shared analytics would require a separate durable store.

## Results and limitations

- `label: 1` means likely scam; `label: 0` means likely legitimate. These are model estimates, not official fact checks.
- `label: null`, `category: "uncertain"`, and `status: "uncertain"` mean **Needs verification**. Unknown vocabulary, fewer than three familiar words, confidence below 0.5, and unsupported scripts trigger this result. A potentially legitimate message containing an unverified URL also requires verification.
- `confidence` is the probability of the highest-scoring category. This replaces the old API's aggregate scam confidence. `scam_probability` is the sum of scam-category probabilities, or `null` for inconclusive results. These scores have not been independently calibrated.
- Hindi-script classification is enabled with 210 synthetic Hindi examples: 84 authored scheme scenarios and 126 native-Hindi examples selected from a licensed public synthetic corpus. Unicode marks, Hindi urgency cues, and Devanagari amounts are normalized without discarding the script. Hindi validation results are reported separately below; these data are not a substitute for native-speaker-reviewed real messages.
- The independent English real-SMS transfer test found weak generalization. The application is a research prototype; neither a legitimate verdict nor a high model score establishes authenticity.
- The awareness tab contains educational examples, with no fabricated official reference numbers or claim of a live PIB connection.

## API

| Endpoint | Request | Result |
| --- | --- | --- |
| `GET /health` | None | HTTP 200 when both artifacts are loaded; HTTP 503 otherwise |
| `POST /predict` | JSON object with a nonempty `message` string | Label, category, confidence, uncertainty reason, cues, and category probabilities |
| `POST /predict_batch` | Multipart `file` field containing a UTF-8 CSV | `total_processed` and predictions including the original messages |
| `GET /analytics` | None | Aggregate counts, uncertainty count, category distribution, and ten recent results without message text |

Input limits: **10,000 characters per message**, **1,000 CSV rows**, and **2 MB per request**. A CSV must have a `message`, `text`, or `msg` column (case-insensitive). Invalid rows reject the whole batch before inference or logging. Unknown columns are not silently classified. Invalid inputs return JSON errors with HTTP 400, oversized requests return 413, and an unavailable model returns 503.

Downloaded CSV cells are escaped against spreadsheet formula injection. A leading apostrophe is added to potentially executable text; the UTF-8 BOM preserves Hindi text in spreadsheet applications.

## Training and evaluation

```powershell
.\backend\.venv\Scripts\python.exe backend/train_model.py
```

Training reads the original synthetic `dataset_final.csv`, `data/hindi_scheme_seeds.json`, and the pinned Hindi supplement through `backend/training_data.py`. It normalizes and deduplicates messages, rejects conflicting normalized labels, and creates a reproducible 80/20 split stratified by category and script. Combined word and character TF-IDF is fitted inside each cross-validation fold. Category/script cells receive balanced weights to reduce script shortcuts. Regularization is selected by cross-validated log loss. A new `fake_other` category covers supplement scams outside the original taxonomy. The supplied `train.csv` and `test.csv` remain original data files and are no longer used for evaluation.

Artifacts are saved to `backend/artifacts/`: `model.pkl`, `vectorizer.pkl`, and `evaluation.json`. Startup validates dependency versions, preprocessing version, and feature dimensions; incompatible artifacts leave the service unready instead of producing predictions. Changing preprocessing requires retraining and restarting the server. Use only trusted local pickle artifacts.

Current development validation uses **904 training messages** and **227 validation messages**, with **zero normalized overlap**:

| Validation slice | Rows | Scam/legitimate accuracy | Eight-category accuracy |
| --- | --- | --- | --- |
| Latin-script | 185 | 100% | 100% |
| Native Hindi | 42 | 92.86% (39/42) | 66.67% (28/42) |
| Combined | 227 | 98.68% (224/227) | 93.83% (213/227) |

These are argmax model metrics before the API's uncertainty and URL guards. The split was inspected during refinement and is **development validation**, not an untouched independent test. Related templates may occur across the split, and the Hindi slice is small. Full metrics, script coverage, source counts and input hashes are in `backend/artifacts/evaluation.json`.

## Independent real-message evaluation

```powershell
.\backend\.venv\Scripts\python.exe backend/evaluate_external.py
```

This evaluates the unchanged API decision policy on the frozen [UCI SMS Spam Collection](https://archive.ics.uci.edu/dataset/228/sms+spam+collection), a separately collected real-English-SMS dataset. Its labels are **spam versus ham**, not verified fraud versus genuine government schemes. UCI examples never enter training, cross-validation, or threshold selection. The evaluator writes no analytics.

Of 5,574 raw messages, 5,129 normalized unique nonempty messages were evaluated, with no development-corpus overlap. Coverage was **34.22%**, accuracy on classified rows **78.63%**, spam detection recall including abstentions **1.27%**, and ham false alarms **0%**. **375/628 spam messages were called legitimate**, demonstrating that synthetic validation cannot establish general spam reliability. The model needs independently verified, in-domain real data before a deployment accuracy claim is justified. No real Hindi traffic was evaluated.

See `reports/external_evaluation.md` for the confusion matrix and `backend/artifacts/external_evaluation.json` for checksums, exclusions, intervals and the model fingerprint. Dataset provenance, licensing and label mappings are documented in `data/README.md`; `backend/fetch_data.py` can restore and verify the frozen downloads.

The historical artifacts under `backend/backend/artifacts/` are unused; the application only loads the canonical `backend/artifacts/` directory.

## Analytics and privacy

Analytics records timestamps, labels, categories, confidence, and classification status, without message text or extracted URLs. Existing message fields are stripped when legacy history is read or next rewritten. Updates use a thread lock, an operating-system file lock, and atomic replacement; batch results are appended in one transaction. A corrupt file is preserved and analytics reports an error rather than silently erasing history. Predictions remain available if analytics storage fails.

History lives in `backend/analytics.json` and is excluded from Git. Historical counts may include results from the earlier model and confidence semantics. The UI sends messages only to this Flask instance; chart and font resources are loaded from external CDNs. Core checks and analytics text still work when charts cannot load.

During refinement, the existing history was found truncated. An explicit offline recovery restored 4,751 complete records without message text; one damaged record could not be parsed. The original bytes remain in the ignored local file `backend/analytics.json.private-backup`. That recovery backup may contain old message text and is never served by Flask.

## Checks

```powershell
.\backend\.venv\Scripts\python.exe -m unittest discover -s backend -v
node --test frontend/js/app.test.cjs
node --check public/static/js/app.js
npm ci
npx playwright install chromium
npm run test:browser
```

Backend tests isolate analytics in temporary directories and cover validation, spoofed URLs, Hindi classification and normalization, abstention, model readiness, data separation, legacy privacy, atomic failure recovery, and concurrent threads/processes. Frontend checks use Node's built-in test runner for safe rendering, uncertainty counts, spreadsheet escaping, stale requests, and chart fallback.

Playwright runs Chromium at desktop (1440×1000) and mobile (390×844) sizes, with a Flask server backed by disposable analytics. It exercises Hindi predictions, CSV upload/download, malicious trigger rendering, delayed requests, navigation, analytics privacy and offline-chart fallback. Screenshots are saved under `reports/visual/`; the HTML test report is generated in `playwright-report/`. These checks do not certify Safari, Firefox, or physical phones.

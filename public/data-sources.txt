# Data sources and evaluation boundaries

All downloaded inputs are frozen in `sources.json` with checksums and are fetched by `backend/fetch_data.py`. Source text is data only: the app never visits message links or calls numbers appearing in these datasets.

## Hindi training supplement

- Creator: Ridham115, **Indian Scam SMS (synthetic, audited)**, produced for the AI Scam & Phishing Message Detector project.
- Source and attribution: https://huggingface.co/datasets/Ridham115/indian-scam-sms-synthetic-audited
- Frozen revision: `45e92c38ba20e973ef3ff5d1893a0a710f622018`.
- License: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The original card is retained as `external/indian_scam_dataset_card.md`.
- Modification: training selects only 126 rows marked `language=hi` and `generator=groq/openai/gpt-oss-120b`, then normalizes text and maps categories. Gemini-provider rows are excluded. KYC, lottery, and job labels map to the corresponding existing category; other non-government scam types map to `fake_other`. Safe rows map to `legit`.
- These are LLM-generated messages with mostly automated auditing and incomplete human review. They are not real received SMS or a real-world evaluation set. Labels may contain noise.

`hindi_scheme_seeds.json` adds 84 AI-authored synthetic Hindi scheme scenarios across the original seven categories, 12 per category. They were authored during this project refinement. They are development examples, have no claim of native-speaker validation, and are not official advisories or independently received messages.

## Independent real-message transfer benchmark

- Creators: Tiago A. Almeida and José María Gómez Hidalgo, **SMS Spam Collection** (2011), UCI Machine Learning Repository.
- Source: https://archive.ics.uci.edu/dataset/228/sms+spam+collection
- DOI: https://doi.org/10.24432/C5CC84
- UCI repository license: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The source's accompanying `readme` is retained as `external/uci_readme.txt`.
- The source collects historical real English SMS from public research collections and reported spam. It is used only by `backend/evaluate_external.py`; no UCI messages or labels enter training, tuning, or threshold selection.
- Evaluation removes normalized duplicates, conflicting labels, and any overlap with the entire development corpus. The unmodified archive and message file are retained locally for reproducibility.
- **Spam is not the same as fraud.** These labels are an out-of-domain proxy, and there are no native Hindi real messages in this benchmark. Results cannot establish government-scam, current Indian traffic, or real-world Hindi accuracy. Abstentions and false alarms must be considered alongside selective accuracy.

Native-speaker-reviewed Hindi data and independently verified, in-domain real scheme messages remain necessary for a production reliability claim. Adding actual evaluation and Hindi functionality does not remove those scientific limits.

# Independent real-message evaluation

This is a frozen **English SMS spam transfer test**. Spam is not equivalent to fraud; these results do not measure Indian government-scam or native-Hindi real-world accuracy.

Source: [UCI SMS Spam Collection](https://archive.ics.uci.edu/dataset/228/sms+spam+collection), Almeida and Hidalgo, DOI 10.24432/C5CC84, CC BY 4.0.

The benchmark is excluded from all training and hyperparameter selection. Evaluation uses the actual API decision policy, including uncertainty, without writing analytics.

| Metric | Result |
| --- | --- |
| Raw records | 5574 |
| Evaluated normalized unique records | 5129 |
| Training-overlap rows excluded | 0 |
| Coverage (a definite classification) | 34.22% |
| Accuracy on classified records | 78.63% |
| Correct classifications / all records | 26.91% |
| Spam detected / all spam, including abstentions | 1.27% |
| Spam incorrectly called legitimate | 59.71% |
| Ham incorrectly flagged | 0.00% |

| Actual label | Likely legitimate | Likely scam | Needs verification |
| --- | --- | --- | --- |
| ham | 1372 | 0 | 3129 |
| spam | 375 | 8 | 245 |

Full checksums, exclusions, uncertainty reasons, confidence intervals and model fingerprints are in `backend/artifacts/external_evaluation.json`. Real Indian government-scam messages with independently verified labels are still required before deployment accuracy can be established.

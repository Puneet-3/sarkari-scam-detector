"""Frozen, read-only real-English-SMS transfer evaluation. This script never fits a model."""
import hashlib
import json
import math
from pathlib import Path
from collections import Counter

import app as api
from preprocess import HinglishPreprocessor
from training_data import normalized_training_texts

ROOT = Path(__file__).resolve().parent.parent
EXTERNAL_FILE = ROOT / 'data/external/uci_SMSSpamCollection.txt'


def wilson(successes, total):
    if not total:
        return None
    z = 1.959963984540054
    rate = successes / total
    denominator = 1 + z*z / total
    middle = (rate + z*z / (2*total)) / denominator
    spread = z * math.sqrt(rate*(1-rate)/total + z*z/(4*total*total)) / denominator
    return [max(0, middle-spread), min(1, middle+spread)]


def load_external_rows(path=EXTERNAL_FILE):
    rows = []
    for line_number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        label, message = line.split('\t', 1)
        if label not in ('spam', 'ham'):
            raise ValueError(f'Invalid benchmark label on line {line_number}')
        rows.append({'id': line_number, 'label': int(label == 'spam'), 'message': message})
    return rows


def main():
    if api.model is None or api.vectorizer is None:
        raise RuntimeError('Train the model before evaluating it.')
    manifest = json.loads((ROOT / 'data/sources.json').read_text(encoding='utf-8'))
    expected = manifest['uci_uncompressed_sha256']
    observed = hashlib.sha256(EXTERNAL_FILE.read_bytes()).hexdigest()
    if observed != expected:
        raise ValueError('External benchmark changed; freeze and document a new benchmark first.')
    raw = load_external_rows()
    cleaner = HinglishPreprocessor()
    training = normalized_training_texts()
    normalized = {}
    conflicts = set()
    overlap = duplicates = empty = 0
    for row in raw:
        key = cleaner.preprocess_text(row['message'])
        if not key:
            empty += 1
            continue
        if key in training:
            overlap += 1
            continue
        if key in normalized:
            duplicates += 1
            if normalized[key]['label'] != row['label']:
                conflicts.add(key)
        else:
            normalized[key] = row
    rows = [row for key, row in normalized.items() if key not in conflicts and key]
    decisions = []
    for offset in range(0, len(rows), 256):
        decisions.extend(api.classify_messages([row['message'] for row in rows[offset:offset+256]]))
    matrix = {'ham': {'legit': 0, 'scam': 0, 'uncertain': 0},
              'spam': {'legit': 0, 'scam': 0, 'uncertain': 0}}
    for row, decision in zip(rows, decisions):
        truth = 'spam' if row['label'] else 'ham'
        predicted = {0: 'legit', 1: 'scam', None: 'uncertain'}[decision['label']]
        matrix[truth][predicted] += 1
    spam = sum(matrix['spam'].values())
    ham = sum(matrix['ham'].values())
    classified = sum(decision['label'] is not None for decision in decisions)
    correct = matrix['ham']['legit'] + matrix['spam']['scam']
    report = {
        'benchmark': 'UCI SMS Spam Collection: independent real-English-SMS spam transfer test',
        'source_url': 'https://archive.ics.uci.edu/dataset/228/sms+spam+collection',
        'doi': '10.24432/C5CC84', 'license': 'CC-BY-4.0',
        'benchmark_sha256': observed,
        'model_sha256': hashlib.sha256((api.ARTIFACTS_DIR/'model.pkl').read_bytes()).hexdigest(),
        'vectorizer_sha256': hashlib.sha256((api.ARTIFACTS_DIR/'vectorizer.pkl').read_bytes()).hexdigest(),
        'raw_rows': len(raw), 'evaluated_rows': len(rows), 'ham_rows': ham, 'spam_rows': spam,
        'excluded_training_overlap_rows': overlap, 'excluded_duplicate_rows': duplicates,
        'excluded_empty_normalized_rows': empty,
        'excluded_conflicting_normalized_groups': len(conflicts),
        'training_or_tuning_on_this_benchmark': False,
        'confusion_matrix': matrix,
        'coverage': classified / len(rows),
        'accuracy_on_classified_rows': correct / classified if classified else None,
        'correct_fraction_of_all_rows': correct / len(rows),
        'spam_detection_recall': matrix['spam']['scam'] / spam,
        'spam_detection_recall_wilson_95': wilson(matrix['spam']['scam'], spam),
        'spam_misclassified_legitimate_fraction': matrix['spam']['legit'] / spam,
        'ham_false_alarm_rate': matrix['ham']['scam'] / ham,
        'ham_false_alarm_wilson_95': wilson(matrix['ham']['scam'], ham),
        'uncertainty_reasons': dict(Counter(d['uncertainty_reason'] for d in decisions if d['label'] is None)),
        'limitations': [
            'UCI labels indicate spam versus ham, not confirmed fraud versus genuine government schemes.',
            'This is an out-of-domain transfer test on historical English SMS, not current Indian government-scam accuracy.',
            'There are no native Hindi real-message examples in this benchmark.',
            'Abstentions are shown explicitly and count as undetected spam when computing recall.',
            'Do not compare selective accuracy alone; coverage and false alarms are required context.',
        ],
    }
    (api.ARTIFACTS_DIR/'external_evaluation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    directory = ROOT/'reports'
    directory.mkdir(exist_ok=True)
    lines = [
        '# Independent real-message evaluation', '',
        'This is a frozen **English SMS spam transfer test**. Spam is not equivalent to fraud; '
        'these results do not measure Indian government-scam or native-Hindi real-world accuracy.', '',
        f'Source: [UCI SMS Spam Collection]({report["source_url"]}), Almeida and Hidalgo, DOI 10.24432/C5CC84, CC BY 4.0.', '',
        'The benchmark is excluded from all training and hyperparameter selection. Evaluation uses the actual '
        'API decision policy, including uncertainty, without writing analytics.', '',
        '| Metric | Result |', '| --- | --- |',
        f'| Raw records | {len(raw)} |', f'| Evaluated normalized unique records | {len(rows)} |',
        f'| Training-overlap rows excluded | {overlap} |',
        f'| Coverage (a definite classification) | {report["coverage"]:.2%} |',
        f'| Accuracy on classified records | {report["accuracy_on_classified_rows"]:.2%} |',
        f'| Correct classifications / all records | {report["correct_fraction_of_all_rows"]:.2%} |',
        f'| Spam detected / all spam, including abstentions | {report["spam_detection_recall"]:.2%} |',
        f'| Spam incorrectly called legitimate | {report["spam_misclassified_legitimate_fraction"]:.2%} |',
        f'| Ham incorrectly flagged | {report["ham_false_alarm_rate"]:.2%} |', '',
        '| Actual label | Likely legitimate | Likely scam | Needs verification |', '| --- | --- | --- | --- |',
        *[f'| {key} | {value["legit"]} | {value["scam"]} | {value["uncertain"]} |' for key,value in matrix.items()], '',
        'Full checksums, exclusions, uncertainty reasons, confidence intervals and model fingerprints are in '
        '`backend/artifacts/external_evaluation.json`. Real Indian government-scam messages with independently '
        'verified labels are still required before deployment accuracy can be established.',
    ]
    (directory/'external_evaluation.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()

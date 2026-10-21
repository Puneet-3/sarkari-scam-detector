"""Train a reproducible baseline with a disjoint normalized holdout."""
import json
from importlib.metadata import version
from pathlib import Path
import hashlib
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.pipeline import Pipeline, FeatureUnion
from preprocess import HinglishPreprocessor, PREPROCESS_VERSION
from training_data import load_training_data

BASE_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = BASE_DIR / 'artifacts'
MIN_CONFIDENCE = 0.5


def prepare_split(frame):
    frame = frame.dropna(subset=['message', 'category']).copy()
    frame['cleaned'] = HinglishPreprocessor().transform(frame.message.tolist())
    frame = frame[frame.cleaned.str.len() > 0]
    conflicts = frame.groupby('cleaned').category.nunique()
    if (conflicts > 1).any():
        raise ValueError('Conflicting categories for identical normalized messages.')
    unique = frame.drop_duplicates('cleaned').reset_index(drop=True)
    unique['script'] = unique.message.str.contains(r'[\u0900-\u097f]').map({True: 'devanagari', False: 'latin'})
    strata = unique.category + '/' + unique.script
    return train_test_split(unique, test_size=0.2, stratify=strata, random_state=42)


def main():
    frame = load_training_data()
    train, test = prepare_split(frame)
    print(f'Normalized unique split: {len(train)} train / {len(test)} test', flush=True)
    pipeline = Pipeline([
        ('vectorizer', FeatureUnion([
            ('word', TfidfVectorizer(token_pattern=r'\S+', ngram_range=(1, 2))),
            ('character', TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), min_df=2, max_features=20000)),
        ], transformer_weights={'word': 1.0, 'character': 0.5})),
        ('classifier', LogisticRegression(max_iter=1000, random_state=42)),
    ])
    search = GridSearchCV(pipeline, {'classifier__C': [0.1, 1.0, 5.0, 10.0, 20.0]},
                          cv=5, scoring='neg_log_loss', n_jobs=1)
    # Balance category/script cells so Hindi does not become a shortcut for the
    # one class (fake_other) that has no original Latin-script examples.
    cells = train.groupby(['category', 'script']).size()
    weights = [len(train) / (len(cells) * cells.loc[(category, script)])
               for category, script in zip(train.category, train.script)]
    search.fit(train.cleaned.tolist(), train.category.tolist(), classifier__sample_weight=weights)
    best = search.best_estimator_
    predicted = best.predict(test.cleaned.tolist())
    probabilities = best.predict_proba(test.cleaned.tolist())
    confident = probabilities.max(axis=1) >= MIN_CONFIDENCE
    correct = predicted == test.category.to_numpy()
    binary_correct = (predicted != 'legit') == (test.category.to_numpy() != 'legit')
    metrics = {
        'preprocess_version': PREPROCESS_VERSION,
        'source_rows': len(frame), 'train_rows': len(train), 'test_rows': len(test),
        'normalized_overlap': len(set(train.cleaned) & set(test.cleaned)),
        'random_state': 42, 'best_parameters': search.best_params_,
        'split_role': 'development validation; inspected during refinement, not an independent real-world test',
        'multiclass_accuracy': accuracy_score(test.category, predicted),
        'binary_accuracy': float(binary_correct.mean()),
        'classification_report': classification_report(test.category, predicted, output_dict=True),
        'confidence_threshold': MIN_CONFIDENCE, 'coverage': float(confident.mean()),
        'accuracy_on_confident_predictions': float(correct[confident].mean()) if confident.any() else None,
        'supported_scripts': ['latin', 'devanagari'],
        'training_source_counts': frame.source.value_counts().to_dict(),
        'per_script': {script: {
            'train_rows': int((train.script == script).sum()),
            'test_rows': int((test.script == script).sum()),
            'accuracy': float(correct[test.script.to_numpy() == script].mean()),
            'binary_accuracy': float(binary_correct[test.script.to_numpy() == script].mean()),
            'confidence_threshold_coverage': float(confident[test.script.to_numpy() == script].mean()),
        } for script in sorted(test.script.unique())},
        'limitations': 'Internal holdout uses synthetic data, including authored and LLM-generated Hindi. '
                       'This does not establish real-world government-scam accuracy. '
                       'Normalized duplicates removed; related templates may still occur in both splits. '
                       'Probabilities are model scores, not independently calibrated risk estimates. '
                       'See external_evaluation.json for a separate real-English-SMS spam transfer test.',
        'versions': {name: version(name) for name in ('scikit-learn', 'numpy', 'scipy', 'joblib')},
        'training_input_sha256': {str(path.relative_to(BASE_DIR.parent)): hashlib.sha256(path.read_bytes()).hexdigest()
                                 for path in (BASE_DIR.parent/'dataset_final.csv',
                                              BASE_DIR.parent/'data/hindi_scheme_seeds.json',
                                              BASE_DIR.parent/'data/external/indian_scam_synthetic.csv')},
    }
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(best.named_steps['vectorizer'], ARTIFACTS_DIR / 'vectorizer.pkl')
    joblib.dump(best.named_steps['classifier'], ARTIFACTS_DIR / 'model.pkl')
    (ARTIFACTS_DIR / 'evaluation.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
    print(classification_report(test.category, predicted), flush=True)
    print(f'Coverage at {MIN_CONFIDENCE:.0%} confidence: {metrics["coverage"]:.1%}', flush=True)
    print(f'Artifacts saved to {ARTIFACTS_DIR}', flush=True)


if __name__ == '__main__':
    main()

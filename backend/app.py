"""Local dashboard and inference API."""
from datetime import datetime, timezone
from importlib.metadata import version
import json
import os
from pathlib import Path
import re
import unicodedata
import tempfile
import joblib
import pandas as pd
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from analytics_store import append_entries, read_entries
from preprocess import (HinglishPreprocessor, PREPROCESS_VERSION, extract_urls,
                        is_government_url, MONEY_PREFIX, MONEY_SUFFIX, URGENCY_PATTERN)

BASE_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = BASE_DIR / 'artifacts'
IS_VERCEL = os.environ.get('VERCEL') == '1'
ANALYTICS_FILE = (Path(tempfile.gettempdir()) / 'sarkari-scam-detector' / 'analytics.json'
                  if IS_VERCEL else BASE_DIR / 'analytics.json')
ANALYTICS_MAX_ENTRIES = 1000 if IS_VERCEL else None
MAX_MESSAGE_LENGTH = 10_000
MAX_BATCH_ROWS = 1_000
ALLOWED_ORIGINS = {origin.strip().rstrip('/') for origin in
                   os.environ.get('SCAM_ALLOWED_ORIGINS', '').split(',') if origin.strip()}
app = Flask(__name__, static_folder=str(BASE_DIR.parent / 'public/static'), static_url_path='/static')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024
if IS_VERCEL:
    # Vercel terminates TLS at its proxy; preserve HTTPS for same-origin validation.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=0, x_proto=1)
if ALLOWED_ORIGINS:
    CORS(app, origins=sorted(ALLOWED_ORIGINS), methods=['GET', 'POST', 'OPTIONS'])
vectorizer = None
model = None
metadata = {}
preprocessor = HinglishPreprocessor()


def load_artifacts():
    global vectorizer, model, metadata
    vectorizer = model = None
    metadata = {}
    try:
        loaded_metadata = json.loads((ARTIFACTS_DIR / 'evaluation.json').read_text(encoding='utf-8'))
        if loaded_metadata.get('preprocess_version') != PREPROCESS_VERSION:
            raise ValueError('Preprocessing changed; retrain the model.')
        for package in ('scikit-learn', 'numpy', 'scipy', 'joblib'):
            if loaded_metadata.get('versions', {}).get(package) != version(package):
                raise ValueError(f'{package} version changed; install pinned dependencies or retrain.')
        loaded_vectorizer = joblib.load(ARTIFACTS_DIR / 'vectorizer.pkl')
        loaded_model = joblib.load(ARTIFACTS_DIR / 'model.pkl')
        if 'legit' not in loaded_model.classes_:
            raise ValueError('Model must contain a legit class.')
        if loaded_model.n_features_in_ != len(loaded_vectorizer.get_feature_names_out()):
            raise ValueError('Model and vectorizer do not match; retrain them together.')
        vectorizer, model, metadata = loaded_vectorizer, loaded_model, loaded_metadata
    except Exception:
        app.logger.exception('Model unavailable. Run backend/train_model.py to create compatible artifacts.')


load_artifacts()


@app.before_request
def restrict_origins():
    origin = request.headers.get('Origin')
    if origin and origin != request.host_url.rstrip('/') and origin not in ALLOWED_ORIGINS:
        return jsonify(error='This origin is not allowed to access the API.'), 403


@app.after_request
def response_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    if request.path != '/' and not request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'no-store'
    return response


@app.errorhandler(413)
def too_large(error):
    return jsonify(error='Upload exceeds the 2 MB limit.'), 413


@app.route('/')
def index():
    return send_from_directory(BASE_DIR.parent / 'frontend', 'index.html')


def extract_triggers(text):
    triggers = [f'Unverified URL: {url}' for url in extract_urls(text) if not is_government_url(url)]
    for pattern in (MONEY_PREFIX, MONEY_SUFFIX):
        triggers.extend(f'Financial claim: {match.group().strip()}' for match in pattern.finditer(text))
    triggers.extend(f"Urgency indicator: '{match.group()}'" for match in URGENCY_PATTERN.finditer(text))
    if '!!!' in text or '???' in text:
        triggers.append('Exaggerated punctuation')
    return list(dict.fromkeys(triggers))


def validate_message(message):
    if not isinstance(message, str) or not message.strip():
        raise ValueError('Each message must be a nonempty string.')
    if len(message) > MAX_MESSAGE_LENGTH:
        raise ValueError(f'Messages must contain at most {MAX_MESSAGE_LENGTH:,} characters.')
    return message.strip()


def classify_messages(messages):
    """Single and batch requests share the same prediction and abstention rules."""
    cleaned = preprocessor.transform(messages)
    vectors = vectorizer.transform(cleaned)
    word_vectorizer = dict(vectorizer.transformer_list)['word']
    probabilities = model.predict_proba(vectors)
    classes = model.classes_
    threshold = metadata.get('confidence_threshold', 0.5)
    results = []
    for index, (message, probs) in enumerate(zip(messages, probabilities)):
        best = int(probs.argmax())
        category = str(classes[best])
        confidence = float(probs[best])
        reason = None
        if re.search(r'[\u0900-\u097f]', message) and 'devanagari' not in metadata.get('supported_scripts', []):
            reason = 'Hindi-script training data is not available yet. Verify this message through an official source.'
        elif any(unicodedata.category(char).startswith('L')
                 and not any(name in unicodedata.name(char, '') for name in ('LATIN', 'DEVANAGARI'))
                 for char in message):
            reason = 'This writing system is not supported by the current model. Verify the message independently.'
        elif vectors[index].nnz == 0:
            reason = 'This message does not contain enough familiar language for a reliable prediction.'
        elif sum(token in word_vectorizer.vocabulary_ and not token.startswith('[')
                 for token in cleaned[index].split()) < 3:
            reason = 'The message is too short or unfamiliar for a reliable prediction.'
        elif confidence < threshold:
            reason = 'The model is uncertain. Verify the claim through an independently found official source.'
        triggers = extract_triggers(message)
        if category == 'legit' and any(not is_government_url(url) for url in extract_urls(message)):
            reason = reason or 'The message contains an unverified link. Confirm its destination independently.'
        probs_dict = {str(key): float(value) for key, value in zip(classes, probs)}
        results.append({
            'label': None if reason else (0 if category == 'legit' else 1),
            'category': 'uncertain' if reason else category,
            'status': 'uncertain' if reason else 'classified',
            'confidence': confidence,
            'scam_probability': None if reason else 1.0 - probs_dict['legit'],
            'uncertainty_reason': reason,
            'triggers_found': triggers,
            'all_probabilities': probs_dict,
        })
    return results


def record_results(results):
    timestamp = datetime.now(timezone.utc).isoformat()
    entries = [{'timestamp': timestamp, **{key: result[key] for key in
                ('label', 'category', 'confidence', 'status')}} for result in results]
    try:
        append_entries(ANALYTICS_FILE, entries, max_entries=ANALYTICS_MAX_ENTRIES)
    except (OSError, ValueError):
        # Keep inference available, but never overwrite corrupt history.
        app.logger.exception('Could not persist analytics.')


@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Provide a JSON object with a 'message' string."), 400
    try:
        message = validate_message(data.get('message'))
    except ValueError as error:
        return jsonify(error=str(error)), 400
    if model is None or vectorizer is None:
        return jsonify(error='The model is unavailable. Please try again after the server is ready.'), 503
    result = classify_messages([message])[0]
    record_results([result])
    return jsonify(result)


@app.route('/predict_batch', methods=['POST'])
def predict_batch():
    file = request.files.get('file')
    if file is None or not file.filename or not file.filename.lower().endswith('.csv'):
        return jsonify(error="Upload a CSV file using the 'file' field."), 400
    try:
        frame = pd.read_csv(file, nrows=MAX_BATCH_ROWS + 1, dtype=str, keep_default_na=False)
        if frame.empty:
            raise ValueError('The CSV must contain at least one message.')
        if len(frame) > MAX_BATCH_ROWS:
            raise ValueError(f'The CSV may contain at most {MAX_BATCH_ROWS:,} rows.')
        columns = {column.strip().lower(): column for column in frame.columns}
        column = next((columns[name] for name in ('message', 'text', 'msg') if name in columns), None)
        if column is None:
            raise ValueError("The CSV needs a 'message', 'text', or 'msg' column.")
        messages = []
        for row_number, message in enumerate(frame[column].tolist(), start=2):
            try:
                messages.append(validate_message(message))
            except ValueError as error:
                raise ValueError(f'CSV row {row_number}: {error}') from error
    except (ValueError, UnicodeError, pd.errors.ParserError) as error:
        return jsonify(error=f'Invalid CSV: {error}'), 400
    if model is None or vectorizer is None:
        return jsonify(error='The model is unavailable. Please try again after the server is ready.'), 503
    results = classify_messages(messages)
    record_results(results)
    return jsonify(total_processed=len(results), results=[
        {'message': message, **result} for message, result in zip(messages, results)
    ])


@app.route('/analytics')
def get_analytics():
    try:
        entries = read_entries(ANALYTICS_FILE)
    except (OSError, ValueError):
        app.logger.exception('Could not read analytics.')
        return jsonify(error='Analytics history is unavailable.'), 503
    scam_count = sum(row.get('label') == 1 for row in entries)
    legit_count = sum(row.get('label') == 0 for row in entries)
    uncertain_count = len(entries) - scam_count - legit_count
    category_counts = {}
    for row in entries:
        if row.get('label') == 1:
            category = row['category']
            category_counts[category] = category_counts.get(category, 0) + 1
    return jsonify(total_checks=len(entries), scam_count=scam_count, legit_count=legit_count,
                   uncertain_count=uncertain_count, scam_ratio=scam_count / len(entries) if entries else 0.0,
                   category_counts=category_counts, recent_checks=entries[-10:][::-1],
                   storage_mode='temporary' if IS_VERCEL else 'local', max_entries=ANALYTICS_MAX_ENTRIES)


@app.route('/health')
def health():
    ready = model is not None and vectorizer is not None
    return jsonify(status='healthy' if ready else 'unavailable', model_loaded=model is not None,
                   vectorizer_loaded=vectorizer is not None), 200 if ready else 503


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)

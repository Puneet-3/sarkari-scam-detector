"""API, privacy, storage and model regression tests. No real analytics are modified."""
from concurrent.futures import ThreadPoolExecutor
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import app as api
from analytics_store import append_entries, read_entries
from preprocess import HinglishPreprocessor, is_government_url
from train_model import prepare_split
import pandas as pd

LEGIT = ('PIB Fact Check: Swachh Bharat Abhiyan se judi kisi bhi third-party link par vishwas na karein. '
         'Sahi jaankari sirf pmkisan.gov.in par upalabdh hai.')
SCAM = ('CONGRATULATIONS Suresh! Aapne KBC/Sarkari Lucky Draw mein ₹5,00,000 jeeta hai. '
        'Claim karne ke liye gov-scheme-claim.xyz par registration fee bhejein.')
HINDI_SCAM = 'सरकारी विभाग में आपकी नौकरी पक्की है। बिना परीक्षा नियुक्ति पत्र लेने के लिए ₹2000 हमारे यूपीआई पर भेजें।'
HINDI_LEGIT = 'पीएम किसान की किस्त का भुगतान पात्र किसानों के पंजीकृत बैंक खाते में किया जाता है। स्थिति स्वयं pmkisan.gov.in पर देखें।'


class TestScamDetectorAPI(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'analytics.json'
        self.analytics = patch.object(api, 'ANALYTICS_FILE', self.path)
        self.analytics.start()
        self.addCleanup(self.analytics.stop)
        self.client = api.app.test_client()

    def upload(self, content, filename='messages.csv'):
        return self.client.post('/predict_batch', data={
            'file': (io.BytesIO(content.encode('utf-8')), filename)
        })

    def test_health(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json['model_loaded'])
        self.assertTrue(response.json['vectorizer_loaded'])

    def test_dashboard_and_assets_are_served(self):
        for path in ('/', '/static/js/app.js', '/static/css/styles.css'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                response.close()

    def test_health_and_prediction_report_missing_model(self):
        with patch.object(api, 'model', None):
            self.assertEqual(self.client.get('/health').status_code, 503)
            response = self.client.post('/predict', json={'message': LEGIT})
            self.assertEqual(response.status_code, 503)
            self.assertIn('error', response.json)

    def test_incompatible_artifacts_fail_readiness(self):
        original = {'model': api.model, 'vectorizer': api.vectorizer, 'metadata': api.metadata}
        with patch.multiple(api, **original), patch.object(api, 'version', return_value='incompatible'):
            with self.assertLogs(api.app.logger, level='ERROR'):
                api.load_artifacts()
            self.assertIsNone(api.model)
            self.assertEqual(self.client.get('/health').status_code, 503)

    def test_predict_legit(self):
        response = self.client.post('/predict', json={'message': LEGIT})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['label'], 0)
        self.assertEqual(response.json['category'], 'legit')
        self.assertGreaterEqual(response.json['confidence'], 0.5)
        self.assertLess(response.json['scam_probability'], 0.5)

    def test_predict_scam(self):
        response = self.client.post('/predict', json={'message': SCAM})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['label'], 1)
        self.assertEqual(response.json['category'], 'fake_lottery_prize')
        self.assertGreaterEqual(response.json['confidence'], 0.5)
        self.assertTrue(response.json['triggers_found'])

    def test_unfamiliar_and_unsupported_messages_abstain(self):
        for message in ('hello', 'xzqplw', 'योजना pmkisan.gov.in', 'தமிழ் pmkisan.gov.in'):
            with self.subTest(message=message):
                response = self.client.post('/predict', json={'message': message})
                self.assertEqual(response.status_code, 200)
                self.assertIsNone(response.json['label'])
                self.assertEqual(response.json['status'], 'uncertain')
                self.assertIsNone(response.json['scam_probability'])
                self.assertTrue(response.json['uncertainty_reason'])

    def test_hindi_scam_and_legitimate_messages_are_supported(self):
        self.assertIn('devanagari', api.metadata['supported_scripts'])
        for message, expected in ((HINDI_SCAM, 1), (HINDI_LEGIT, 0)):
            with self.subTest(expected=expected):
                response = self.client.post('/predict', json={'message': message})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json['label'], expected)
                self.assertIsNone(response.json['uncertainty_reason'])

    def test_low_confidence_abstains_even_with_known_features(self):
        import numpy as np
        probs = np.full((1, len(api.model.classes_)), 1 / len(api.model.classes_))
        with patch.object(api.model, 'predict_proba', return_value=probs):
            response = self.client.post('/predict', json={'message': LEGIT})
        self.assertIsNone(response.json['label'])

    def test_invalid_inputs_return_json_400_without_logging(self):
        for payload in (None, [], ['message'], 12, {}, {'message': None}, {'message': 123},
                        {'message': []}, {'message': ''}, {'message': '   '}, {'message': 'x' * 10001}):
            with self.subTest(payload_type=type(payload).__name__):
                response = self.client.post('/predict', data=json.dumps(payload), content_type='application/json')
                self.assertEqual(response.status_code, 400)
                self.assertIn('error', response.json)
        self.assertFalse(self.path.exists())

    def test_batch_matches_single_predictions_including_uncertainty(self):
        messages = [SCAM, LEGIT, 'hello']
        import csv
        content = io.StringIO()
        writer = csv.writer(content)
        writer.writerow(['message'])
        writer.writerows([message] for message in messages)
        response = self.upload(content.getvalue(), 'MESSAGES.CSV')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['total_processed'], 3)
        for message, batch in zip(messages, response.json['results']):
            single = self.client.post('/predict', json={'message': message}).json
            self.assertEqual(batch['message'], message)
            self.assertEqual({key: value for key, value in batch.items() if key != 'message'}, single)

    def test_bad_csv_is_rejected_before_logging(self):
        for content in ('', 'message\n', 'id\n12\n', 'message\n""\n',
                        'message\n' + 'text\n' * 1001, 'message\n"unterminated'):
            with self.subTest(content=content[:20]):
                response = self.upload(content)
                self.assertEqual(response.status_code, 400)
                self.assertIn('error', response.json)
        self.assertFalse(self.path.exists())

    def test_upload_size_is_limited(self):
        response = self.client.post('/predict', data='x' * (2 * 1024 * 1024 + 1), content_type='application/json')
        self.assertEqual(response.status_code, 413)
        self.assertIn('error', response.json)

    def test_untrusted_origins_cannot_read_or_write(self):
        for path, method in (('/analytics', 'GET'), ('/predict', 'POST'), ('/predict_batch', 'POST')):
            response = self.client.open(path, method=method, headers={'Origin': 'https://untrusted.example'})
            self.assertEqual(response.status_code, 403)
            self.assertIsNone(response.headers.get('Access-Control-Allow-Origin'))
        self.assertFalse(self.path.exists())
        self.assertEqual(self.client.get('/health', headers={'Origin': 'http://localhost'}).status_code, 200)

    def test_analytics_counts_uncertain_without_retaining_text(self):
        for message in (LEGIT, SCAM, 'hello'):
            self.assertEqual(self.client.post('/predict', json={'message': message}).status_code, 200)
        response = self.client.get('/analytics')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['total_checks'], 3)
        self.assertEqual(response.json['scam_count'], 1)
        self.assertEqual(response.json['legit_count'], 1)
        self.assertEqual(response.json['uncertain_count'], 1)
        self.assertAlmostEqual(response.json['scam_ratio'], 1 / 3)
        self.assertNotIn('message', self.path.read_text())
        self.assertNotIn('message', json.dumps(response.json))

    def test_legacy_history_never_exposes_messages(self):
        self.path.write_text(json.dumps([{'timestamp': '2026-01-01T00:00:00+00:00',
            'message': 'private OTP 1234', 'label': 0, 'category': 'legit', 'confidence': 0.9}]), encoding='utf-8')
        self.assertNotIn('private OTP', self.client.get('/analytics').get_data(as_text=True))
        self.client.post('/predict', json={'message': SCAM})
        self.assertNotIn('private OTP', self.path.read_text())
        self.assertEqual(len(read_entries(self.path)), 2)

    def test_corrupt_history_is_preserved(self):
        self.path.write_text('broken history', encoding='utf-8')
        with self.assertLogs(api.app.logger, level='ERROR'):
            response = self.client.post('/predict', json={'message': SCAM})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.client.get('/analytics').status_code, 503)
        self.assertEqual(self.path.read_text(), 'broken history')


class TestPreprocessing(unittest.TestCase):
    def test_preserves_hindi_and_structured_tokens(self):
        cleaner = HinglishPreprocessor()
        self.assertEqual(cleaner.preprocess_text('आपका आधार'), 'आपका आधार')
        result = cleaner.preprocess_text('Abhi ₹50,000 https://pmkisan.gov.in !!!')
        for token in ('[urgent_cue]', '[money_value]', '[govt_link]', '!!!'):
            self.assertIn(token, result)
        for value in ('Rs. 10000', '1,00,000 rs', '50 hazar'):
            self.assertEqual(cleaner.preprocess_text(value), '[money_value]')
        for value in ('₹५०,०००', '५० हजार', '500 रुपये'):
            self.assertEqual(cleaner.preprocess_text(value), '[money_value]')
        self.assertEqual(cleaner.preprocess_text('अभी तुरंत जल्दी आज ही'),
                         '[urgent_cue] [urgent_cue] [urgent_cue] [urgent_cue]')

    def test_url_hostnames_resist_spoofing(self):
        for url in ('https://pmkisan.gov.in', 'mygov.in', 'https://service.nic.in/path'):
            self.assertTrue(is_government_url(url), url)
            self.assertIn('[govt_link]', HinglishPreprocessor().preprocess_text(url))
        for url in ('https://pmkisan.gov.in.evil.com/claim', 'https://evil.com/pmkisan.gov.in',
                    'https://pmkisan.gov.in@evil.com/', 'https://notgov.in/', 'bit.ly/claim',
                    'pmkisan.gov.in.attacker.dev/path', 'pmkisan.gov.in@evil.com',
                    'https://evil.com\\foo.gov.in/'):
            self.assertFalse(is_government_url(url), url)
            self.assertIn('[url_link]', HinglishPreprocessor().preprocess_text(url))
            self.assertNotIn('[govt_link]', HinglishPreprocessor().preprocess_text(url))
            self.assertTrue(api.extract_triggers(url))

    def test_training_holdout_is_normalized_disjoint(self):
        from training_data import load_training_data
        frame = load_training_data()
        train, test = prepare_split(frame)
        self.assertFalse(set(train.cleaned) & set(test.cleaned))
        self.assertEqual(train.cleaned.nunique(), len(train))
        self.assertEqual(test.cleaned.nunique(), len(test))
        self.assertEqual(set(train.category), set(test.category))
        self.assertIn('devanagari', set(train.script))
        self.assertIn('devanagari', set(test.script))

    def test_external_evaluation_is_excluded_from_training(self):
        from training_data import load_training_data
        frame = load_training_data()
        self.assertEqual(set(frame.source), {'original_synthetic', 'authored_hindi_synthetic',
                                             'ridham115_hindi_synthetic'})
        import hashlib
        from evaluate_external import EXTERNAL_FILE
        manifest = json.loads((api.BASE_DIR.parent/'data/sources.json').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256(EXTERNAL_FILE.read_bytes()).hexdigest(), manifest['uci_uncompressed_sha256'])

    def test_conflicting_normalized_labels_are_rejected(self):
        frame = pd.DataFrame({'message': ['Rs. 100', 'Rs. 200'], 'category': ['legit', 'fake_job_offer']})
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            prepare_split(frame)


class TestAnalyticsStorage(unittest.TestCase):
    def test_cloud_history_is_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'analytics.json'
            append_entries(path, [{'timestamp': str(i), 'label': 1} for i in range(5)], max_entries=3)
            self.assertEqual([row['timestamp'] for row in read_entries(path)], ['2', '3', '4'])
            append_entries(path, [{'timestamp': '5', 'label': 0}], max_entries=3)
            self.assertEqual([row['timestamp'] for row in read_entries(path)], ['3', '4', '5'])

    def test_threads_do_not_lose_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'analytics.json'
            with ThreadPoolExecutor(max_workers=10) as pool:
                list(pool.map(lambda i: append_entries(path, [{'timestamp': str(i), 'label': 1,
                    'category': 'fake_job_offer', 'confidence': 0.9, 'status': 'classified'}]), range(100)))
            rows = read_entries(path)
            self.assertEqual(len(rows), 100)
            self.assertEqual(len({row['timestamp'] for row in rows}), 100)

    def test_processes_do_not_lose_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'analytics.json'
            code = ("import sys; from analytics_store import append_entries; "
                    "[append_entries(sys.argv[1], [{'timestamp':sys.argv[2]+str(i),'label':1,"
                    "'category':'fake_job_offer','confidence':0.9,'status':'classified'}]) for i in range(20)]")
            processes = [subprocess.Popen([sys.executable, '-c', code, str(path), str(i)],
                         cwd=api.BASE_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for i in range(3)]
            for process in processes:
                output, error = process.communicate(timeout=30)
                self.assertEqual(process.returncode, 0, error.decode())
            self.assertEqual(len(read_entries(path)), 60)

    def test_failed_replacement_preserves_history(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'analytics.json'
            path.write_text('[]', encoding='utf-8')
            with patch('analytics_store.os.replace', side_effect=OSError('simulated disk failure')):
                with self.assertRaises(OSError):
                    append_entries(path, [{'label': 1}])
            self.assertEqual(path.read_text(), '[]')
            self.assertFalse(list(Path(directory).glob('*.tmp')))


class TestVercelEntrypoint(unittest.TestCase):
    def test_https_proxy_and_temporary_analytics(self):
        code = '''
import json, tempfile
from pathlib import Path
from index import app
import backend.app as api
assert api.IS_VERCEL
assert api.ANALYTICS_FILE.parent == Path(tempfile.gettempdir()) / 'sarkari-scam-detector'
with tempfile.TemporaryDirectory() as directory:
    api.ANALYTICS_FILE = Path(directory) / 'analytics.json'
    client = app.test_client()
    assert client.get('/health').status_code == 200
    response = client.post('/predict', json={'message': 'hello'},
        base_url='http://demo.vercel.app',
        headers={'Origin': 'https://demo.vercel.app', 'X-Forwarded-Proto': 'https'})
    assert response.status_code == 200, response.get_data(as_text=True)
    stats = client.get('/analytics').get_json()
    assert stats['storage_mode'] == 'temporary'
    assert stats['max_entries'] == 1000 and stats['total_checks'] == 1
    assert all('message' not in row for row in stats['recent_checks'])
    denied = client.post('/predict', json={'message': 'hello'},
        headers={'Origin': 'https://untrusted.example', 'X-Forwarded-Proto': 'https'})
    assert denied.status_code == 403
print('Vercel WSGI entrypoint, HTTPS origin and temporary storage verified.')
'''
        environment = dict(os.environ, VERCEL='1')
        result = subprocess.run([sys.executable, '-X', 'utf8', '-c', code],
                                cwd=api.BASE_DIR.parent, env=environment,
                                capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == '__main__':
    unittest.main()

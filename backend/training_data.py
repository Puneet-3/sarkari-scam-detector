"""Auditable training inputs. External real-message evaluation is deliberately excluded."""
import hashlib
import json
from pathlib import Path
import pandas as pd
from preprocess import HinglishPreprocessor

ROOT = Path(__file__).resolve().parent.parent
SUPPLEMENT_SHA256 = '45bde5f156a1a42698bab209e32bcd41b3639013d772f644cc3208ed39fb61e2'
SCAM_TYPES = {'fake_kyc': 'fake_kyc_aadhaar', 'lottery': 'fake_lottery_prize', 'job_offer': 'fake_job_offer'}


def load_training_data():
    original = pd.read_csv(ROOT / 'dataset_final.csv')[['message', 'category']]
    original['source'] = 'original_synthetic'
    seed_path = ROOT / 'data/hindi_scheme_seeds.json'
    seeds = json.loads(seed_path.read_text(encoding='utf-8-sig'))
    authored = pd.DataFrame([{'message': text, 'category': category, 'source': 'authored_hindi_synthetic'}
                            for category, texts in seeds.items() for text in texts])
    path = ROOT / 'data/external/indian_scam_synthetic.csv'
    if hashlib.sha256(path.read_bytes()).hexdigest() != SUPPLEMENT_SHA256:
        raise ValueError('The downloaded training supplement does not match its frozen checksum.')
    extra = pd.read_csv(path)
    # Use native Hindi rows from one documented generator; preserve original labels in the source CSV.
    extra = extra[(extra.language == 'hi') & (extra.generator == 'groq/openai/gpt-oss-120b')].copy()
    extra['category'] = ['legit' if label == 'safe' else SCAM_TYPES.get(kind, 'fake_other')
                         for label, kind in zip(extra.label, extra.scam_type)]
    extra = extra.rename(columns={'text': 'message'})
    extra['source'] = 'ridham115_hindi_synthetic'
    frame = pd.concat([original, authored, extra[['message', 'category', 'source']]], ignore_index=True)
    frame['script'] = frame.message.str.contains(r'[\u0900-\u097f]').map({True: 'devanagari', False: 'latin'})
    return frame


def normalized_training_texts():
    return set(HinglishPreprocessor().transform(load_training_data().message.tolist()))

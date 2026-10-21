"""Shared text and URL normalization for training and inference."""
import re
import unicodedata
from urllib.parse import urlsplit
from sklearn.base import BaseEstimator, TransformerMixin

PREPROCESS_VERSION = 3
URL_PATTERN = re.compile(
    r"(?i)\b(?:https?://[^\s<>\"']+|"
    r"(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+"
    r"[a-z]{2,63}(?![a-z0-9.-])"
    r"(?::\d+)?(?:[/?#@][^\s<>\"']*)?)"
)
URGENCY_PATTERN = re.compile(
    r'(?i)(?<![\w\u0900-\u097f])(?:turant|aaj\s*hi|jaldi|abhi|last\s*date|urgent|expired?'
    r'|तुरंत|आज\s*ही|जल्दी|अभी|अंतिम\s*तिथि|आखिरी\s*तारीख)(?![\w\u0900-\u097f])'
)
MONEY_PREFIX = re.compile(
    r'(?i)(?:₹|\brs\.?|\brupees?|\binr|रु\.?|रुपये|रुपए)\s*\d+(?:,\d+)*'
    r'(?:\s*(?:hazar|lakh|crore|k|हजार|लाख|करोड़)(?![\w\u0900-\u097f]))?'
)
MONEY_SUFFIX = re.compile(
    r'(?i)\b\d+(?:,\d+)*\s*(?:rs\.?|rupees?|inr|hazar|lakh|crore|k|रुपये|रुपए|हजार|लाख|करोड़)'
    r'(?![\w\u0900-\u097f])'
)


def extract_urls(text):
    return [match.group().rstrip('.,;:!?)]}') for match in URL_PATTERN.finditer(text)]


def is_government_url(url):
    """Match complete hostnames; paths, credentials and lookalikes confer no trust."""
    try:
        if '\\' in url or any(ord(char) < 33 for char in url):
            return False
        parsed = urlsplit(url if '://' in url else 'https://' + url)
        # Accessing .port also validates malformed or out-of-range ports.
        parsed.port
        host = (parsed.hostname or '').lower().rstrip('.')
        return (parsed.scheme in ('https', 'http')
                and parsed.username is None and parsed.password is None
                and any(host == domain or host.endswith('.' + domain)
                        for domain in ('gov.in', 'nic.in', 'mygov.in')))
    except ValueError:
        return False


class HinglishPreprocessor(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        if isinstance(X, str):
            X = [X]
        return [self.preprocess_text(text) for text in X]

    def preprocess_text(self, text):
        if not isinstance(text, str):
            return ''
        text = unicodedata.normalize('NFKC', text)
        text = ''.join(str(unicodedata.decimal(char)) if char.isdecimal() else char for char in text)
        text = URL_PATTERN.sub(
            lambda match: '[GOVT_LINK]' if is_government_url(match.group()) else '[URL_LINK]', text)
        text = MONEY_PREFIX.sub('[MONEY_VALUE]', text)
        text = MONEY_SUFFIX.sub('[MONEY_VALUE]', text)
        text = URGENCY_PATTERN.sub('[URGENT_CUE]', text).lower()
        # Preserve Unicode letters, numbers, and combining marks such as Hindi matras.
        text = ''.join(char if unicodedata.category(char)[0] in 'LNM'
                       or char.isspace() or char in '_[]!?%₹' else ' ' for char in text)
        return re.sub(r'\s+', ' ', text).strip()

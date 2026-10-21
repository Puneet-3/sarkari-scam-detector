"""Disposable analytics for real browser tests; never opens the user's history."""
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
import app

if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as directory:
        app.ANALYTICS_FILE = Path(directory) / 'analytics.json'
        app.app.run(host='127.0.0.1', port=5088, debug=False)

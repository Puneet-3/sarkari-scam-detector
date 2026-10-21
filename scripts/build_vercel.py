"""Validate public source assets and reject incompatible model artifacts."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent


def main():
    # Vercel discovers public files before this command. Keep these assets in
    # source control rather than generating them after static route discovery.
    for relative in ('static/css/styles.css', 'static/js/app.js', 'data-sources.txt'):
        if not (ROOT / 'public' / relative).is_file():
            raise RuntimeError(f'Missing public source asset: {relative}')
    sys.path.insert(0, str(ROOT))
    from index import app
    with app.test_client() as client:
        response = client.get('/health')
        if response.status_code != 200:
            raise RuntimeError('Model readiness failed; refusing to publish an unavailable API.')
        page = client.get('/')
        if page.status_code != 200:
            raise RuntimeError('Dashboard index is missing.')
        page.close()
        for url, mimetype in (('/static/css/styles.css', 'text/css'),
                              ('/static/js/app.js', 'text/javascript')):
            with client.get(url) as asset:
                if asset.status_code != 200 or asset.mimetype != mimetype:
                    raise RuntimeError(f'Invalid dashboard asset: {url}')
    print('Public source assets, Flask entrypoint and model readiness verified.')


if __name__ == '__main__':
    main()

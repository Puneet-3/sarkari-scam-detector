"""Re-download frozen public inputs with checksum verification; never execute source content."""
import hashlib
import io
import json
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent


def main():
    manifest = json.loads((ROOT/'data/sources.json').read_text(encoding='utf-8'))
    folder = ROOT/'data/external'
    folder.mkdir(parents=True, exist_ok=True)
    for entry in manifest['downloads']:
        target = folder/entry['path']
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == entry['sha256']:
            content = target.read_bytes()
        else:
            with urllib.request.urlopen(entry['url'], timeout=60) as response:
                content = response.read()
            if hashlib.sha256(content).hexdigest() != entry['sha256']:
                raise ValueError('Source checksum changed; refusing to use an unreviewed replacement.')
            target.write_bytes(content)
        if entry['path'] == 'uci_sms_spam.zip':
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                for member in ('SMSSpamCollection', 'readme'):
                    (folder/f'uci_{member}.txt').write_bytes(archive.read(member))
        print('Verified', entry['path'])


if __name__ == '__main__':
    main()

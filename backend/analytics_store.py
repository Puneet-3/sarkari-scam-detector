"""Small JSON store with process/thread locking and atomic replacement."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile
import threading

_thread_lock = threading.Lock()
PUBLIC_FIELDS = ('timestamp', 'label', 'category', 'confidence', 'status')


@contextmanager
def _locked(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with _thread_lock, open(str(path) + '.lock', 'a+b') as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b'\0')
            handle.flush()
        handle.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def _read(path):
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
        raise ValueError('Analytics must be a JSON array of records.')
    # Strip historical message text as well as any other private fields.
    return [{key: row[key] for key in PUBLIC_FIELDS if key in row} for row in data]


def read_entries(filename):
    path = Path(filename)
    with _locked(path):
        return _read(path)


def append_entries(filename, entries, max_entries=None):
    if max_entries is not None and (not isinstance(max_entries, int) or max_entries < 1):
        raise ValueError('max_entries must be a positive integer or None.')
    path = Path(filename)
    with _locked(path):
        data = _read(path)
        data.extend({key: row[key] for key in PUBLIC_FIELDS if key in row} for row in entries)
        if max_entries is not None:
            data = data[-max_entries:]
        pending = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                             prefix=path.name + '.', suffix='.tmp', delete=False) as handle:
                pending = handle.name
                json.dump(data, handle, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(pending, path)
        finally:
            if pending and os.path.exists(pending):
                os.unlink(pending)

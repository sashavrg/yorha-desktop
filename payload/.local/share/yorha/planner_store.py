"""Atomic, owner-only local tasks with revision checks and no external service."""
import fcntl
import json
import os
import tempfile
from pathlib import Path

PATH = Path.home() / '.local/share/yorha/tasks.json'

class Conflict(Exception):
    def __init__(self, state):
        self.state = state
        super().__init__('Tasks changed; reload and retry')

def read():
    try:
        state = json.loads(PATH.read_text())
        if not isinstance(state.get('items'), list) or not isinstance(state.get('rev'), int):
            raise ValueError('Invalid task state')
        return state
    except FileNotFoundError:
        return {'rev': 0, 'items': []}

def write(state, revision):
    PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PATH.parent / 'tasks.lock', 'a', opener=lambda p, f: os.open(p, f, 0o600)) as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        current = read()
        if current['rev'] != revision:
            raise Conflict(current)
        state = dict(state, rev=revision + 1)
        fd, tmp = tempfile.mkstemp(dir=PATH.parent, prefix='.tasks-')
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(state, stream, indent=2)
                stream.write('\n')
            os.replace(tmp, PATH)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
        return state

"""Small transactional file installer, shared by wizard and recovery command."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

class InstallError(RuntimeError): pass

def fingerprint(path):
    if path.is_symlink(): return 'link:' + os.readlink(path)
    if path.is_file(): return 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest()
    if path.is_dir(): return 'directory'
    return 'absent'

def validate(home, relative):
    name = Path(relative)
    if name.is_absolute() or '..' in name.parts or not name.parts:
        raise InstallError('Unsafe managed path')
    target = home/name
    # Leaf symlinks are backed up and replaced; never follow them when writing.
    if not target.parent.resolve().is_relative_to(home.resolve()):
        raise InstallError('A parent symlink leaves the selected home: '+relative)
    return target

def atomic_json(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.yorha-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(content, stream, indent=2)
            stream.write('\n')
            stream.flush();os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

class Transaction:
    def __init__(self, home):
        self.home = Path(home).absolute()
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        self.backup = self.home/'.local/state/yorha/backups'/stamp
        self.backup.mkdir(parents=True, mode=0o700)
        self.backup.chmod(0o700)
        self.state = dict(version=1, home=str(self.home), status='installing', files=[])
        self.save()

    def save(self): atomic_json(self.backup/'manifest.json', self.state)

    def capture(self, relative, generated_dir=False):
        target = validate(self.home, relative)
        previous = next((f for f in self.state['files'] if f['path'] == relative), None)
        if previous: return previous
        kind = 'link' if target.is_symlink() else 'file' if target.is_file() else 'absent'
        if target.is_dir() and not target.is_symlink():
            raise InstallError('Refusing to replace an existing directory: '+relative)
        entry = dict(path=relative, before=kind, after='pending', generated_dir=generated_dir)
        if kind == 'link': entry['link'] = os.readlink(target)
        if kind == 'file':
            destination = self.backup/'files'/relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, destination)
        self.state['files'].append(entry)
        self.save()  # Recovery data exists durably before modifying the destination.
        return entry

    def put(self, relative, data, mode=0o644):
        entry = self.capture(relative)
        target = validate(self.home, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=target.parent, prefix='.yorha-install-')
        try:
            with os.fdopen(fd,'wb') as stream: stream.write(data)
            os.chmod(tmp, mode)
            os.replace(tmp,target)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
        entry['after'] = fingerprint(target)
        self.save()

    def delete(self, relative):
        target = validate(self.home, relative)
        if not target.exists() and not target.is_symlink(): return
        entry = self.capture(relative)
        target.unlink()
        entry['after'] = 'absent'
        self.save()

    def replace_directory(self, relative):
        """Back up a generated runtime before rebuilding it for a new interpreter."""
        target = validate(self.home, relative)
        if target.is_symlink() or not target.is_dir():
            raise InstallError('Expected an owned runtime directory: '+relative)
        if any(f['path'] == relative for f in self.state['files']):
            raise InstallError('Directory is already part of this transaction: '+relative)
        destination = self.backup/'directories'/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(target, destination, symlinks=True)
        self.state['files'].append(dict(path=relative, before='directory', after='directory', generated_dir=True))
        self.save()
        shutil.rmtree(target)

    def generated_dir(self, relative):
        entry = self.capture(relative, generated_dir=True)
        entry['after'] = 'directory'
        self.save()

    def finish(self):
        self.state['status'] = 'complete'
        self.save()

def restore(backup, home=None, force=False):
    backup = Path(backup).resolve()
    state = json.loads((backup/'manifest.json').read_text())
    if state.get('version') != 1: raise InstallError('Unsupported backup version')
    home = Path(home).absolute() if home else Path(state['home']).absolute()
    if str(home) != state['home']: raise InstallError('This backup belongs to a different home')
    checked = []
    for entry in state['files']:
        target = validate(home, entry['path'])
        if entry['before'] not in ['file','link','absent','directory']: raise InstallError('Invalid backup entry')
        if entry['before'] == 'file' and not (backup/'files'/entry['path']).is_file():
            raise InstallError('Incomplete backup: '+entry['path'])
        if entry['before'] == 'directory' and not (backup/'directories'/entry['path']).is_dir():
            raise InstallError('Incomplete runtime backup: '+entry['path'])
        if not force and entry['after'] != 'pending' and fingerprint(target) != entry['after']:
            raise InstallError('Edited after installation: '+entry['path']+' (save edits, then use --force)')
        checked.append((entry,target))
    # Validate every entry before changing anything.
    for entry, target in reversed(checked):
        if target.is_dir() and not target.is_symlink():
            if not entry.get('generated_dir'): raise InstallError('Unexpected directory at '+entry['path'])
            shutil.rmtree(target)
        else: target.unlink(missing_ok=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        if entry['before'] == 'file': shutil.copy2(backup/'files'/entry['path'],target)
        elif entry['before'] == 'link': target.symlink_to(entry['link'])
        elif entry['before'] == 'directory': shutil.copytree(backup/'directories'/entry['path'],target,symlinks=True)
    state['status'] = 'restored'
    atomic_json(backup/'manifest.json',state)
    return home

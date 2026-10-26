"""Local settings and bounded daily Shortcut collection."""
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.daybook-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class Runtime:
    def __init__(self, folder, loader, clock=None, runner=None):
        self.folder = Path(folder)
        self.loader = loader
        self.clock = clock or (lambda: datetime.now().astimezone())
        self.runner = runner or subprocess.run
        self.lock = threading.Lock()
        self.settings_lock = threading.Lock()
        self.auto = False

    def read(self, name, default):
        try:
            return json.loads((self.folder / name).read_text())
        except (OSError, ValueError):
            return default

    def preferences(self):
        return self.read('preferences.json', {'goal':'understand', 'labels':{}, 'feedback':{}})

    def status(self):
        return {**self.read('collection.json', {}), 'enabled':self.auto,
                'running':self.lock.locked(), 'reports_folder':str(self.folder / 'reports')}

    @staticmethod
    def due(now, state):
        if now.hour < 8 or state.get('success_target') == (now.date()-timedelta(days=1)).isoformat():
            return False
        if state.get('attempt_day') != now.date().isoformat():
            return True
        if state.get('attempts', 0) >= 3:
            return False
        try:
            previous = datetime.fromisoformat(state['last_attempt'])
            return (now.astimezone(timezone.utc)-previous.astimezone(timezone.utc)).total_seconds() >= 3600
        except (KeyError, ValueError):
            return True

    def collect(self, automatic=False):
        if not self.lock.acquire(False):
            return False, 'A collection is already running.'
        try:
            now = self.clock()
            state = self.read('collection.json', {})
            if automatic and not self.due(now, state):
                return False, 'Not due.'
            attempts = state.get('attempts', 0) if state.get('attempt_day') == now.date().isoformat() else 0
            state.update(last_attempt=now.isoformat(), attempt_day=now.date().isoformat(), attempts=attempts+1)
            write_json(self.folder / 'collection.json', state)
            try:
                result = self.runner(['/usr/bin/shortcuts', 'run', 'Screen Time Yesterday'], capture_output=True, text=True, timeout=90)
                if result.returncode:
                    raise ValueError(result.stderr.strip()[:400] or 'Shortcuts could not run. Open it to resolve any prompt.')
                data = self.loader()
                # A newly saved file can arrive after the process exits via iCloud. Retry on a later check.
                fresh = any(d['date']==data['yesterday'] and d['complete']
                            and datetime.fromisoformat(d['captured_at']) >= now
                            for d in data['days'])
                if not fresh:
                    raise ValueError('No fresh completed-day export yet. Check the Shortcut and iCloud sync; Daybook will retry.')
                state.update(success_target=data['yesterday'], last_success=now.isoformat(), error='')
                message = 'Yesterday’s export is saved.'
                ok = True
            except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                message = ('Shortcut timed out. Open Shortcuts to check for a permission prompt.'
                           if isinstance(exc, subprocess.TimeoutExpired) else str(exc))
                state['error'] = message
                ok = False
            write_json(self.folder / 'collection.json', state)
            return ok, message
        finally:
            self.lock.release()

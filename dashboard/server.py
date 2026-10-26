#!/usr/bin/env python3
"""Local Screen Time dashboard. Standard library only; no private Apple databases."""
import argparse
from collections import defaultdict
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import subprocess
import threading
from urllib.parse import urlsplit
import os
import time
from insights import review, markdown, DEFAULTS, CATEGORIES, GOALS
from runtime import Runtime, write_json

ROOT = Path(__file__).resolve().parent
SNAPSHOTS = Path.home() / 'Library/Mobile Documents/iCloud~is~workflow~my~workflows/Documents/ScreenTime/snapshots'
DATA_FOLDERS = None
DEMO = False
RUNTIME = None


def parse_activity(raw):
    """Parse observed English/Chinese duration strings, retaining unknown lines."""
    entries, unknown = [], []
    units = {'h':3600, 'hr':3600, 'hrs':3600, 'hour':3600, 'hours':3600,
             '小时':3600, '小時':3600, 'm':60, 'min':60, 'mins':60,
             'minute':60, 'minutes':60, '分钟':60, '分鐘':60,
             's':1, 'sec':1, 'secs':1, 'second':1, 'seconds':1, '秒':1}
    pattern = r'(\d+(?:\.\d+)?)\s*(' + '|'.join(sorted(units, key=len, reverse=True)) + r')'
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.fullmatch(r'(.+)\s*[（(]([^()（）]+)[）)]', line)
        if not match:
            unknown.append(line)
            continue
        name, duration = match.groups()
        parts = list(re.finditer(pattern, duration.lower()))
        remainder = re.sub(pattern, '', duration.lower()).strip(' ,，')
        if not parts or remainder:
            unknown.append(line)
            continue
        seconds = sum(float(p[1]) * units[p[2]] for p in parts)
        entries.append({'name':name.strip(), 'seconds':seconds, 'raw':line})
    return entries, unknown


def load_data(folders=None):
    groups = defaultdict(list)
    warnings = []
    for folder in (folders if folders is not None else DATA_FOLDERS or [SNAPSHOTS, ROOT / 'data']):
        for path in sorted(folder.glob('*')):
            if path.suffix not in ('.txt', '.json'):
                continue
            try:
                item = json.loads(path.read_text())
                if not isinstance(item, dict):
                    raise ValueError('export must be an object')
                day = date.fromisoformat(item['report_date'])
                stamp = datetime.fromisoformat(item['captured_at'])
                if stamp.utcoffset() is None:
                    raise ValueError('capture time has no timezone')
                scope = item['device_scope']
                if not isinstance(scope, str) or not scope:
                    raise ValueError('missing device scope')
                entries, unknown = parse_activity(item['raw_activity_text'])
                period = item.get('query_period', '')
                # A completed-day query must have been captured after that day.
                complete = period in ('yesterday', 'specifiedDay') and stamp.date() > day
                item.update(date=day.isoformat(), complete=complete,
                            entries=entries, unparsed=unknown, source=path.name,
                            total_seconds=sum(e['seconds'] for e in entries))
                groups[(day.isoformat(), scope)].append((stamp, item))
            except (ValueError, KeyError, TypeError, OSError, AttributeError) as exc:
                warnings.append({'file':path.name, 'reason':str(exc)})
    days = []
    for _, candidates in sorted(groups.items()):
        # Prefer a completed-day export over an intraday sample. Never add
        # cumulative snapshots together or merge different device scopes.
        _, selected = max(candidates, key=lambda pair: (pair[1]['complete'], pair[0]))
        selected['snapshot_count'] = len(candidates)
        days.append(selected)
    now = datetime.now().astimezone()
    if DEMO:
        now = datetime.fromisoformat("2026-10-26T10:00:00-04:00")
    return {'days':days, 'warnings':warnings, 'today':now.date().isoformat(),
            'yesterday':(now.date()-timedelta(days=1)).isoformat(),
            'updated_at':now.isoformat(), 'source_folder':('Synthetic examples only' if DEMO else str(DATA_FOLDERS[0] if DATA_FOLDERS else SNAPSHOTS))}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, status, body, content_type='application/json; charset=utf-8'):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def valid_host(self):
        return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')

    def do_GET(self):
        if not self.valid_host():
            return self.reply(403, {'error':'Local access only'})
        route = urlsplit(self.path).path
        if route == '/api/health':
            return self.reply(200, {'application':'daybook', 'version':'0.1.0-alpha', 'demo':DEMO})
        if route == '/api/data':
            return self.reply(200, payload())
        files = {'/':('index.html','text/html; charset=utf-8'),
                 '/app.js':('app.js','text/javascript; charset=utf-8'),
                 '/style.css':('style.css','text/css; charset=utf-8')}
        if route not in files:
            return self.reply(404, {'error':'Not found'})
        filename, mime = files[route]
        self.reply(200, (ROOT / 'static' / filename).read_bytes(), mime)

    def do_POST(self):
        expected_origin = 'http://' + self.headers.get('Host', '')
        if (not self.valid_host() or self.headers.get('Origin') != expected_origin
                or self.headers.get('X-Daybook-Action') != 'collect'):
            return self.reply(403, {'error':'Request must come from this local dashboard'})
        if self.path == '/api/preferences':
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 65536:
                    raise ValueError('Invalid settings size')
                value = json.loads(self.rfile.read(length))
                if not isinstance(value, dict) or value.get('goal') not in GOALS:
                    raise ValueError('Unknown goal')
                labels, feedback = value.get('labels', {}), value.get('feedback', {})
                if not isinstance(labels, dict) or not isinstance(feedback, dict):
                    raise ValueError('Invalid settings')
                if len(labels)>500 or len(feedback)>500:
                    raise ValueError('Too many settings')
                if any(not isinstance(k,str) or len(k)>300 or v not in CATEGORIES for k,v in labels.items()):
                    raise ValueError('Invalid category')
                if any(not isinstance(k,str) or len(k)>300 or v not in ('useful','hide') for k,v in feedback.items()):
                    raise ValueError('Invalid feedback')
                with RUNTIME.settings_lock:
                    write_json(RUNTIME.folder / 'preferences.json', {'goal':value['goal'], 'labels':labels, 'feedback':feedback})
                data = payload()
                save_reports(data)
                return self.reply(200, data)
            except (ValueError, TypeError, OSError) as exc:
                return self.reply(400, {'error':str(exc)})
        if self.path != '/api/collect':
            return self.reply(404, {'error':'Not found'})
        if DEMO:
            return self.reply(400, {'error':'Demo uses synthetic records; real collection is disabled.'})
        ok, message = RUNTIME.collect()
        if not ok:
            return self.reply(502, {'error':message})
        data = payload()
        save_reports(data)
        self.reply(200, data)


def payload():
    data = load_data()
    prefs = RUNTIME.preferences()
    end = date.fromisoformat(data['yesterday'])
    # A stable Monday–Sunday review, refreshed as late exports arrive.
    end -= timedelta(days=(end.weekday()+1)%7)
    scopes = sorted({d['device_scope'] for d in data['days']}) or ['all_devices']
    data.update(preferences=prefs, defaults=DEFAULTS, demo=DEMO, collection=RUNTIME.status(),
                reviews={scope:review(data['days'], end, scope, prefs) for scope in scopes})
    return data


def save_reports(data=None):
    data = payload() if data is None else data
    for scope, report in data['reviews'].items():
        # Stable safe scope digest avoids filenames derived from imported text.
        import hashlib
        suffix = hashlib.sha256(scope.encode()).hexdigest()[:10]
        folder = RUNTIME.folder / 'reports'
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / (report['end'] + '-' + suffix + '.md')
        content = markdown(report)
        if not path.exists() or path.read_text() != content:
            path.write_text(content)


def automatic_worker():
    while True:
        try:
            RUNTIME.collect(automatic=True)
            save_reports()
        except Exception as exc:
            # Keep the loop alive; surface failures rather than silently pretending collection worked.
            print(f'Daybook background check failed: {exc}', flush=True)
        time.sleep(900)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--open', action='store_true', help='Open the dashboard in your default browser')
    parser.add_argument('--no-auto', action='store_true', help='Disable automatic daily collection')
    parser.add_argument('--demo', action='store_true', help='Use synthetic examples only; never invoke Shortcuts')
    parser.add_argument('--state-dir', type=Path, default=Path.home() / 'Library/Application Support/Daybook')
    parser.add_argument('--data-dir', type=Path, help='Read exports only from this folder')
    args = parser.parse_args()
    DEMO = args.demo
    if DEMO:
        DATA_FOLDERS = [ROOT / 'examples']
    elif args.data_dir:
        DATA_FOLDERS = [args.data_dir]
    RUNTIME = Runtime(args.state_dir / 'demo' if DEMO else args.state_dir, load_data)
    RUNTIME.auto = not (args.no_auto or DEMO)

    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    url = f'http://127.0.0.1:{args.port}'
    print(f'Daybook: {url}\nReads: {SNAPSHOTS}\nPress Control-C to stop.', flush=True)
    if RUNTIME.auto:
        threading.Thread(target=automatic_worker, daemon=True).start()
    else:
        threading.Thread(target=save_reports, daemon=True).start()
    if args.open:
        import webbrowser
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

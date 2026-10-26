#!/usr/bin/env python3
"""Open the installed dashboard or start it; never requires generated code."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.request
import webbrowser


def probe(port, demo):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health', timeout=3) as response:
            info = json.load(response)
    except urllib.error.HTTPError:
        return 'occupied'
    except urllib.error.URLError:
        return 'stopped'
    except (TimeoutError, ValueError):
        return 'occupied'
    return 'running' if info.get('application') == 'daybook' and info.get('demo') == demo else 'occupied'


def main():
    if sys.version_info < (3, 9):
        raise SystemExit('Daybook requires Python 3.9 or newer. Install Python from https://www.python.org/downloads/macos/.')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true')
    args = parser.parse_args()
    port = 8766 if args.demo else 8765
    state = probe(port, args.demo)
    if state == 'running':
        webbrowser.open(f'http://127.0.0.1:{port}')
        print('Opened the running Daybook dashboard.')
        return
    if state == 'occupied':
        raise SystemExit(f'Port {port} is already in use. Stop the other server, or restart an older Daybook service using python3 dashboard/manage.py install.')
    command = [sys.executable, str(Path(__file__).with_name('server.py')), '--open', '--port', str(port)]
    if args.demo:
        command.append('--demo')
    raise SystemExit(subprocess.call(command))

if __name__ == '__main__':
    main()

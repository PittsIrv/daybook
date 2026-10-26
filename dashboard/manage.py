#!/usr/bin/env python3
"""Optional macOS start-at-login installation. Does not request Full Disk Access."""
import argparse
import os
from pathlib import Path
import plistlib
import subprocess
import sys

LABEL = 'io.daybook.local'

def specification(root, home, executable):
    logs = home / 'Library/Logs/Daybook'
    return {'Label':LABEL, 'ProgramArguments':[executable, str(root/'server.py')],
            'WorkingDirectory':str(root), 'RunAtLoad':True,
            'KeepAlive':{'SuccessfulExit':False}, 'ThrottleInterval':60,
            'StandardOutPath':str(logs/'service.log'), 'StandardErrorPath':str(logs/'service-error.log')}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['install','uninstall','print'])
    args = parser.parse_args()
    home = Path.home(); root = Path(__file__).resolve().parent
    config = specification(root, home, sys.executable)
    if args.action == 'print':
        print(plistlib.dumps(config).decode());return
    if sys.platform != 'darwin':
        parser.error('Start-at-login installation requires macOS.')
    target = home/'Library/LaunchAgents'/f'{LABEL}.plist'
    domain = f'gui/{os.getuid()}'
    if args.action == 'uninstall':
        subprocess.run(['launchctl','bootout',f'{domain}/{LABEL}'],capture_output=True)
        target.unlink(missing_ok=True)
        print('Daybook login service removed. Your data and settings are retained.');return
    installed = subprocess.run(['/usr/bin/shortcuts','list'],capture_output=True,text=True)
    if installed.returncode or 'Screen Time Yesterday' not in installed.stdout.splitlines():
        parser.error('Import and run Screen Time Yesterday once before installing the login service.')
    target.parent.mkdir(parents=True,exist_ok=True)
    (home/'Library/Logs/Daybook').mkdir(parents=True,exist_ok=True)
    subprocess.run(['launchctl','bootout',f'{domain}/{LABEL}'],capture_output=True)
    target.write_bytes(plistlib.dumps(config))
    result = subprocess.run(['launchctl','bootstrap',domain,str(target)],capture_output=True,text=True)
    if result.returncode:
        parser.exit(1,'Could not start service: '+result.stderr)
    print('Installed Daybook at login. Open http://127.0.0.1:8765. Keep this project folder in place.')
    print('Collection runs after 8 AM while your Mac is awake. Check the dashboard for successful collection.')

if __name__ == '__main__': main()

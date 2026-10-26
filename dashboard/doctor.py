#!/usr/bin/env python3
"""Check local prerequisites without collecting data or changing settings."""
import json
import platform
from pathlib import Path
import subprocess
import sys


def check():
    checks=[]
    def add(name, ok, detail):
        checks.append({'check':name,'ok':ok,'detail':detail})
    add('Python',sys.version_info >= (3,9),platform.python_version()+'; Python 3.9+ required')
    add('macOS',sys.platform=='darwin',platform.platform()+'; live collection requires macOS')
    action = Path('/System/Library/ExtensionKit/Extensions/IntelligencePlatformDataActionsAppIntentsExtension.appex/Contents/Resources/Metadata.appintents/extract.actionsdata')
    try:
        metadata=json.loads(action.read_text())
        available=any('CalculateAppUsageIntent' in key for key in metadata.get('actions',{}))
    except (OSError,ValueError,TypeError):
        available=False
    add('Screen Time action',available,'Get App & Website Activity metadata found' if available else 'Could not verify automatically. Search for Get App & Website Activity in Shortcuts; missing metadata alone is not proof of unavailability.')
    try:
        result=subprocess.run(['/usr/bin/shortcuts','list'],capture_output=True,text=True,timeout=15)
        installed=result.returncode==0 and 'Screen Time Yesterday' in result.stdout.splitlines()
    except (OSError,subprocess.TimeoutExpired):
        installed=False
    add('Daily Shortcut',installed,'Installed' if installed else 'Import Screen Time Yesterday.shortcut from the release, choose its device scope and run it once.')
    exports=Path.home()/'Library/Mobile Documents/iCloud~is~workflow~my~workflows/Documents/ScreenTime/snapshots'
    add('Export folder',exports.is_dir(),'Folder found; contents not read' if exports.is_dir() else 'Not found yet; run the daily Shortcut once and allow iCloud to sync.')
    return checks

if __name__ == '__main__':
    checks=check()
    for item in checks:
        print(f'{"OK" if item["ok"] else "CHECK"}  {item["check"]}: {item["detail"]}')
    print('These checks do not prove device coverage, background permissions or complete iCloud sync.')
    sys.exit(0 if all(item['ok'] for item in checks) else 1)

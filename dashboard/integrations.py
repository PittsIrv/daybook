"""Optional macOS calendar bridge. Permissions are requested only by an explicit click."""
from pathlib import Path
import plistlib
import subprocess
import sys
import os
import shutil
import json

BRIDGE = Path.home()/'Library/Application Support/Daybook/Daybook Calendar.app'


def install_exporter():
    executable = shutil.which('screentime') or str(Path.home()/'.local/bin/screentime')
    script = Path(executable).resolve()
    if not script.is_file():
        raise SystemExit('Install first: uv tool install git+https://github.com/nichtlegacy/screentime')
    folder = BRIDGE.parent
    folder.mkdir(parents=True,exist_ok=True)
    config = folder/'exporter.toml'
    config.write_text('db_path = '+json.dumps(str(folder/'screentime.db'))+'\n\n[lookup]\nenabled = false\n')
    config.chmod(0o600)
    logs = Path.home()/'Library/Logs/Daybook'
    logs.mkdir(parents=True,exist_ok=True)
    label = 'io.daybook.exporter'
    agent = Path.home()/'Library/LaunchAgents'/f'{label}.plist'
    agent.parent.mkdir(parents=True,exist_ok=True)
    spec = {'Label':label,'ProgramArguments':[str(script),'sync'],
            'EnvironmentVariables':{'SCREENTIME_CONFIG':str(config)},
            'StartInterval':900,'RunAtLoad':True,
            'StandardOutPath':str(logs/'exporter.log'),
            'StandardErrorPath':str(logs/'exporter-error.log')}
    domain = f'gui/{os.getuid()}'
    subprocess.run(['/bin/launchctl','bootout',f'{domain}/{label}'],capture_output=True)
    agent.write_bytes(plistlib.dumps(spec))
    result = subprocess.run(['/bin/launchctl','bootstrap',domain,str(agent)],capture_output=True,text=True)
    if result.returncode:
        raise SystemExit(result.stderr)
    shebang = script.read_text().splitlines()[0].removeprefix('#!')
    binary = str(Path(shebang).resolve())
    setup = folder/'exporter-setup.json'
    setup.write_text(json.dumps({'permission_binary':binary,'agent':label,'interval_seconds':900}))
    setup.chmod(0o600)
    print('Exporter sync agent installed: every 15 minutes while this Mac is awake.')
    print('App Store lookup is disabled; no external export destinations are configured.')
    print('Enable Full Disk Access for this resolved exporter interpreter, then restart the exporter agent:')
    print(binary)


def build_calendar_bridge():
    contents = BRIDGE/'Contents'
    (contents/'MacOS').mkdir(parents=True,exist_ok=True)
    (contents/'Info.plist').write_bytes(plistlib.dumps({
        'CFBundleIdentifier':'io.daybook.calendar','CFBundleName':'Daybook Calendar',
        'CFBundleDisplayName':'Daybook Calendar','CFBundleExecutable':'CalendarBridge',
        'CFBundlePackageType':'APPL','CFBundleVersion':'1','LSUIElement':True,
        'NSCalendarsFullAccessUsageDescription':'Daybook reads titles and times from calendars you choose to compare scheduled events with screen activity. It never modifies your events.',
        'NSCalendarsUsageDescription':'Daybook reads selected calendar events for your local timeline.'}))
    subprocess.run(['/usr/bin/xcrun','swiftc',str(Path(__file__).with_name('CalendarBridge.swift')),
                    '-o',str(contents/'MacOS/CalendarBridge'),'-framework','AppKit','-framework','EventKit'],check=True)
    subprocess.run(['/usr/bin/codesign','--force','--sign','-',str(BRIDGE)],check=True)


def calendar_sync(folder, connect=False):
    if folder.resolve() != BRIDGE.parent.resolve():
        return False,'Calendar sync is available only in the normal personal workspace.'
    if not BRIDGE.exists():
        return False,'Calendar helper is not installed. Run: python3 dashboard/integrations.py install-calendar'
    if not connect and not (folder/'calendar-selection.json').exists():
        return False,'Choose calendars first.'
    result = subprocess.run(['/usr/bin/open','-a',str(BRIDGE),'--args',* ([] if connect else ['--sync'])],
                            capture_output=True,text=True,timeout=10)
    return result.returncode == 0, result.stderr.strip() or 'Calendar helper opened. Save your calendar selection, then refresh Daybook.'


if __name__ == '__main__':
    if sys.argv[1:] == ['install-calendar']:
        build_calendar_bridge()
        print('Calendar helper installed. Click Connect calendars in Daybook to select calendars and grant access.')
    elif sys.argv[1:] == ['install-exporter']:
        install_exporter()
    else:
        raise SystemExit('Usage: python3 dashboard/integrations.py install-calendar | install-exporter')

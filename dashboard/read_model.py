"""Shared read-only view for the browser and local MCP. No collection side effects."""
import json
from classification import app_catalog, totals
from activity import prepare_day, comparisons
from sources import exporter_days, calendar_data, calendar_for_day
from integrations import BRIDGE


def build_data(data, runtime, demo=False):
    prefs = runtime.preferences()
    if demo:
        from demo_sessions import add_demo_sources
        calendar, exporter = add_demo_sources(data)
    else:
        detailed, exporter = exporter_days(runtime.folder/'screentime.db')
        data['days'].extend(detailed)
        try:
            exporter['permission_binary'] = json.loads((runtime.folder/'exporter-setup.json').read_text())['permission_binary']
        except (OSError, ValueError, KeyError):
            pass
        calendar = calendar_data(runtime.folder)
        calendar['helper_installed'] = BRIDGE.exists()
        error_file = runtime.folder/'calendar-error.txt'
        if error_file.exists():
            calendar['error'] = error_file.read_text()[:500]
    for day in data['days']:
        prepare_day(day)
    for day in data['days']:
        day['purpose_seconds'] = totals(day, prefs['labels'])
        day['comparisons'] = comparisons(day, data['days'], prefs['labels'])
        day['calendar_events'] = calendar_for_day(calendar, day['date'])
    data.update(preferences=prefs, demo=demo, collection=runtime.status(),
                app_catalog=app_catalog(data['days'], prefs['labels']), calendar=calendar, exporter=exporter)
    return data

"""Source-aware totals and comparisons. Missing history is never zero-filled."""
from datetime import date, timedelta
import re
from classification import totals

BROWSERS = {'chrome', 'google chrome', 'safari', 'firefox', 'arc', 'brave',
            'brave browser', 'microsoft edge', 'edge', 'opera', 'vivaldi', 'orion'}
COMMON_TLDS = {'com','org','net','edu','gov','io','ai','app','dev','co','uk','cn','jp',
               'tv','me','us','ca','info','xyz','site','live','gg','cc','hk','tw','de',
               'fr','au','in','kr','tech','cloud'}


def website_name(name):
    host = re.sub(r'^https?://','',name).split('/')[0].lower()
    parts = host.split('.')
    # Shortcut text can contain reverse-DNS app IDs as well as web hosts.
    # Ambiguous identifiers stay counted; never silently discard app usage.
    if len(parts) > 2 and parts[0] in {'com','org','net','io','edu','gov','app','dev','cn'}:
        return False
    return len(parts)>1 and parts[-1] in COMMON_TLDS and bool(re.fullmatch(r'[\w.-]+',host))


SYSTEM_HELPERS = {
    'com.apple.incallservice',
    'com.apple.quicklook.quicklookuiservice',
}


def system_helper(entry):
    return any(str(entry.get(key, '')).casefold() in SYSTEM_HELPERS
               for key in ('name', 'bundle_id'))


def prepare_day(day):
    # Explicit helper identities only: Apple apps and short real usage remain.
    # Raw source files are untouched; this is the shared dashboard/MCP view.
    day['entries'] = [e for e in day['entries'] if not system_helper(e)]
    if 'sessions' in day:
        day['sessions'] = [e for e in day['sessions'] if not system_helper(e)]
    for hour in day.get('hourly', []):
        hour['apps'] = [e for e in hour['apps'] if not system_helper(e)]

    # Shortcut descriptions lack browser attribution and timestamps. Keep sites
    # as drill-down detail whenever a browser exists, not extra measured time.
    has_browser = any(e['name'].casefold() in BROWSERS for e in day['entries'])
    for entry in day['entries']:
        is_site = entry.get('kind') == 'website'
        if 'kind' not in entry:
            is_site = website_name(entry['name'])
            # Reverse-DNS bundle identifiers from the exporter are explicitly apps.
            entry['kind'] = 'website' if is_site else 'app'
        entry['detail_only'] = bool(is_site and has_browser)
        entry['counted_seconds'] = 0 if entry['detail_only'] else entry['seconds']
    day['total_seconds'] = sum(e['counted_seconds'] for e in day['entries'])
    day['website_detail_seconds'] = sum(e['seconds'] for e in day['entries'] if e['detail_only'])
    return day


def comparisons(day, days, labels):
    current = date.fromisoformat(day['date'])
    lookup = {d['date']:d for d in days if d['device_scope'] == day['device_scope']}
    result = []
    for key, title, offsets in [('yesterday','Previous day',[1]),
                                ('three_days','Previous 3 days · average',[1,2,3]),
                                ('same_weekday','Same weekday last week',[7])]:
        dates = [(current-timedelta(days=n)).isoformat() for n in offsets]
        baseline = [lookup[d] for d in dates if d in lookup and lookup[d]['complete']]
        ready = len(baseline) == len(dates)
        metrics = None
        if ready:
            metrics = {'Total':sum(d['total_seconds'] for d in baseline)/len(baseline)}
            for purpose in ('Focus','Entertainment','Other','Untagged'):
                metrics[purpose] = sum(totals(d,labels)[purpose] for d in baseline)/len(baseline)
        result.append({'key':key,'title':title,'dates':dates,'available_days':len(baseline),
                       'required_days':len(dates),'baseline':metrics,
                       'comparable':bool(day['complete'] and ready)})
    return result

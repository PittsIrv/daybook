"""User-confirmed app purposes and quantitative daily totals. No inferred intent."""
from collections import defaultdict

PURPOSES = ('Focus', 'Entertainment', 'Other')
LEGACY = {'Gaming':'Entertainment', 'Social':'Entertainment', 'Video':'Entertainment',
          'Leisure':'Entertainment', 'Utility':'Other', 'Mixed':'Other'}
SUGGESTIONS = {
    'Brawl Stars':'Entertainment', 'Minecraft':'Entertainment', 'Roblox':'Entertainment',
    'Stardew Valley':'Entertainment', 'Balatro':'Entertainment', 'Instagram':'Entertainment',
    'TikTok':'Entertainment', 'rednote':'Entertainment', '小红书':'Entertainment',
    'Netflix':'Entertainment', 'Disney+':'Entertainment',
    'Xcode':'Focus', 'Visual Studio Code':'Focus', 'Code':'Focus',
}


def normalize_labels(labels):
    """Preserve explicit older choices; defaults never count as confirmation."""
    result = {}
    for name, label in labels.items():
        label = LEGACY.get(label, label)
        if label in PURPOSES:
            result[name] = label
    return result


def totals(day, labels):
    result = {name:0 for name in (*PURPOSES, 'Untagged')}
    for entry in day['entries']:
        result[labels.get(entry['name'], 'Untagged')] += entry.get('counted_seconds', entry['seconds'])
    return result


def app_catalog(days, labels):
    catalog = {}
    for day in days:
        for entry in day['entries']:
            name = entry['name']
            item = catalog.setdefault(name, {'name':name, 'first_seen':day['date'],
                                            'last_seen':day['date'], 'scopes':set()})
            item['first_seen'] = min(item['first_seen'], day['date'])
            item['last_seen'] = max(item['last_seen'], day['date'])
            item['scopes'].add(day['device_scope'])
    return [{**item, 'scopes':sorted(item['scopes']), 'category':labels.get(name),
             'suggested_category':SUGGESTIONS.get(name, 'Other')}
            for name,item in sorted(catalog.items(), key=lambda pair:pair[0].casefold())]


def daily_markdown(day, labels):
    def duration(seconds):
        minutes = int(seconds//60)
        return f'{minutes//60}h {minutes%60}m' if minutes else f'{round(seconds)}s'
    grouped = defaultdict(float)
    detail = set()
    for entry in day['entries']:
        grouped[entry['name']] += entry['seconds']
        if entry.get('detail_only'):
            detail.add(entry['name'])
    lines = [f'# Daybook daily totals: {day["date"]}', '', f'Scope: {day["device_scope"]}', '',
             'Completed-day query' if day['complete'] else 'Partial snapshot', '',
             f'Reported activity: {duration(day["total_seconds"])}', '']
    lines += [f'- {name}: {duration(value)}' for name,value in totals(day,labels).items()]
    lines += ['', '## Apps and websites', '']
    lines += [f'- {name}: {duration(value)} ({labels.get(name, "Untagged")})'
              + (' — website detail, excluded from totals' if name in detail else '')
              for name,value in sorted(grouped.items(),key=lambda pair:-pair[1])]
    lines += ['', 'Labels reflect your choices, not measured productivity. App, website and device activity can overlap; these totals are not unique elapsed time.']
    if day.get('unparsed'):
        lines += [f'{len(day["unparsed"])} unparsed row(s) excluded from these totals.']
    return '\n'.join(lines)+'\n'

"""Evidence-first, deterministic weekly reviews. No network or model dependency."""
from collections import defaultdict
from datetime import date, timedelta
from statistics import mean, median

CATEGORIES = ('Focus', 'Gaming', 'Social', 'Video', 'Leisure', 'Utility', 'Mixed', 'Unclassified')
ENTERTAINMENT = {'Gaming', 'Social', 'Video', 'Leisure'}
# Conservative app-name defaults only. Domains and general-purpose tools stay mixed.
DEFAULTS = {
    'Brawl Stars': 'Gaming', 'Minecraft': 'Gaming', 'Roblox': 'Gaming',
    'Stardew Valley': 'Gaming', 'Balatro': 'Gaming',
    'Instagram': 'Social', 'TikTok': 'Social', 'rednote': 'Social', '小红书': 'Social',
    'Netflix': 'Video', 'Disney+': 'Video',
    'Chrome': 'Mixed', 'Google Chrome': 'Mixed', 'Safari': 'Mixed', 'Firefox': 'Mixed',
    'YouTube': 'Mixed', 'ChatGPT': 'Mixed', 'Claude': 'Mixed', 'Discord': 'Mixed',
    'Finder': 'Utility', 'System Settings': 'Utility', 'Settings': 'Utility',
    'Calculator': 'Utility', 'Calendar': 'Utility',
}
GOALS = ('understand', 'less_entertainment', 'more_learning')


def category(name, labels):
    value = labels.get(name, DEFAULTS.get(name, 'Unclassified'))
    return value if value in CATEGORIES else 'Unclassified'


def metrics(day, labels):
    values = defaultdict(float)
    for row in day['entries']:
        values[category(row['name'], labels)] += row['seconds']
    values['Entertainment'] = sum(values[c] for c in ENTERTAINMENT)
    return values


def minutes(seconds):
    return f'{round(seconds / 60)} min'


def review(days, end, scope, preferences=None):
    """Fixed calendar windows; no partial days, scope mixing or missing-as-zero."""
    prefs = preferences or {}
    labels, goal = prefs.get('labels', {}), prefs.get('goal', 'understand')
    end = date.fromisoformat(end) if isinstance(end, str) else end
    start = end - timedelta(days=6)
    baseline_start = start - timedelta(days=28)
    eligible = {date.fromisoformat(d['date']): d for d in days
                if d['device_scope'] == scope and d['complete'] and not d.get('unparsed')
                and d.get('entries') and date.fromisoformat(d['date']) <= end}
    recent = [eligible[d] for d in (start + timedelta(days=i) for i in range(7)) if d in eligible]
    baseline = [d for day, d in eligible.items() if baseline_start <= day < start]
    base_by_weekday = defaultdict(list)
    for d in baseline:
        base_by_weekday[date.fromisoformat(d['date']).weekday()].append(metrics(d, labels))
    ready = len(recent) == 7 and all(len(base_by_weekday[w]) >= 3 for w in range(7))
    result = {'start': start.isoformat(), 'end': end.isoformat(), 'scope': scope,
              'recent_days': len(recent), 'baseline_days': len(baseline),
              'baseline_start': baseline_start.isoformat(), 'baseline_end': (start-timedelta(days=1)).isoformat(),
              'eligible_days': len(eligible), 'ready': ready, 'findings': [],
              'method': 'Seven complete recent days compared with the previous 28 days, matching weekdays; at least three observations per weekday. Descriptive patterns, not proof of productivity or causation.',
              'caveat': 'Reported app/site durations can overlap. Categories reflect defaults or your corrections; browser intent is not inferred.'}
    result['message'] = ('Your baseline is ready. Only substantial changes are shown.' if ready else
        f'Still learning: {len(recent)}/7 recent days and {len(baseline)}/28 baseline days available. '
        'Comparisons need a full recent week and at least three of each weekday in the baseline. '
        'Empty, partial, missing or unparsed exports are excluded.')
    candidates = []
    if ready:
        current = [metrics(d, labels) for d in recent]
        # Equal weekday weighting prevents uneven missing baseline dates changing the comparison.
        names = ('Gaming', 'Social', 'Video', 'Leisure', 'Entertainment', 'Focus')
        averages = {}
        for name in names:
            before = mean(mean(v[name] for v in base_by_weekday[w]) for w in range(7))
            after = mean(v[name] for v in current)
            averages[name] = (before, after)
            delta = after - before
            if before < 600 or abs(delta) < 900 or abs(delta) / before < .2:
                continue
            aligned = sum((v[name]-mean(b[name] for b in base_by_weekday[date.fromisoformat(d['date']).weekday()])) * delta > 0 for d,v in zip(recent,current))
            if aligned < 5:
                continue
            direction = 'down' if delta < 0 else 'up'
            target = 'Focus-labelled activity' if name == 'Focus' else name
            evidence = f'{minutes(after)}/day this week versus {minutes(before)}/day before ({abs(delta)/before:.0%} {"less" if delta < 0 else "more"}).'
            suggestion = None
            if goal == 'less_entertainment' and name == 'Entertainment':
                suggestion = ('This moves toward your chosen goal. Keep the approach that feels sustainable.' if delta < 0 else
                              'Try one combined entertainment allowance for the next week, then compare again.')
            elif goal == 'more_learning' and name == 'Focus':
                suggestion = 'These are app labels, not learning outcomes. Protect a small regular study period if that suits your goal.'
            candidates.append({'id': f'change:{name}:{direction}', 'kind': 'change', 'title': f'{target} is {direction}',
                               'detail': evidence, 'evidence': {'before_seconds_per_day': round(before), 'after_seconds_per_day': round(after),
                               'recent_days': 7, 'baseline_days': len(baseline), 'days_in_same_direction':aligned}, 'suggestion': suggestion,
                               'score': abs(delta) / 60 + (25 if suggestion else 0)})
        before_total, after_total = averages['Entertainment']
        down = [(n, b-a) for n,(b,a) in averages.items() if n in ENTERTAINMENT and b-a >= 900]
        up = [(n, a-b) for n,(b,a) in averages.items() if n in ENTERTAINMENT and a-b >= 900]
        if down and up and abs(after_total-before_total) <= max(600, before_total*.1):
            a, decrease = max(down, key=lambda x:x[1]); b, increase = max(up, key=lambda x:x[1])
            candidates.append({'id': f'substitution:{a}:{b}', 'kind': 'substitution', 'title': 'Entertainment shifted between categories',
                'detail': f'{a} fell by {minutes(decrease)}/day while {b} rose by {minutes(increase)}/day. Combined entertainment stayed within 10 minutes or 10% of its baseline.',
                'evidence': {'before_seconds_per_day': round(before_total), 'after_seconds_per_day': round(after_total), 'recent_days': 7, 'baseline_days': len(baseline)},
                'suggestion': 'A combined allowance may suit your goal better than limiting one app.' if goal == 'less_entertainment' else None, 'score': 120})
        # Weekday finding uses up to eight weeks. Require four samples of EVERY weekday.
        by_weekday = defaultdict(list)
        for d, item in eligible.items():
            if end-timedelta(days=55) <= d <= end:
                by_weekday[d.weekday()].append(metrics(item, labels)['Entertainment'])
        if all(len(by_weekday[w]) >= 4 for w in range(7)):
            medians = {w: median(by_weekday[w]) for w in range(7)}
            peak = max(medians, key=medians.get)
            other = median([v for w,v in medians.items() if w != peak])
            if medians[peak]-other >= 1800 and medians[peak] >= other*1.25:
                weekday = ('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday')[peak]
                candidates.append({'id': f'weekday:Entertainment:{peak}', 'kind': 'weekday', 'title': f'{weekday} tends to have more entertainment',
                    'detail': f'Median {minutes(medians[peak])}, compared with {minutes(other)} for the other weekday medians. Based on {len(by_weekday[peak])} {weekday}s; at least four observations of every weekday.',
                    'evidence': {'weekday_samples':len(by_weekday[peak]), 'window_days':56},
                    'suggestion': f'If you want a change, try a small allowance specifically on {weekday}s.' if goal == 'less_entertainment' else None, 'score':60})
    feedback = prefs.get('feedback', {})
    for finding in candidates:
        finding['score'] += 15 if feedback.get(finding['id']) == 'useful' else 0
    candidates = [f for f in candidates if feedback.get(f['id']) != 'hide']
    # One substitution explanation is more useful than two redundant category changes.
    if any(f['kind']=='substitution' for f in candidates):
        candidates = [f for f in candidates if f['kind']!='change' or f['id'].split(':')[1] not in ENTERTAINMENT]
    result['findings'] = sorted(candidates, key=lambda f:(-f['score'], f['id']))[:3]
    if ready and not result['findings']:
        result['message'] = 'No substantial new pattern to highlight. Your habits may be steady, or findings may be hidden. Collection continues quietly.'
    totals = defaultdict(float)
    for d in recent:
        for row in d['entries']:
            if category(row['name'], labels) == 'Unclassified':
                totals[row['name']] += row['seconds']
    result['classification_candidate'] = max(totals, key=totals.get) if totals and max(totals.values()) >= 3600 else None
    return result


def markdown(report):
    lines = [f'# Daybook weekly review: {report["start"]} – {report["end"]}', '',
             f'Scope: {report["scope"]}', '', report['message'], '']
    for finding in report['findings']:
        lines.extend([f'## {finding["title"]}', '', finding['detail'], ''])
        if finding.get('suggestion'):
            lines.extend([finding['suggestion'], ''])
    lines.extend(['## Evidence and limits', '', report['method'], '', report['caveat'], ''])
    return '\n'.join(lines)

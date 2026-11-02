"""Fictional timeline fixture, used only by the explicit --demo mode."""
from datetime import datetime, timedelta


def add_demo_sources(data):
    events = []
    for day in data['days']:
        start = datetime.fromisoformat(day['date']+'T08:00:00-04:00')
        sessions = []
        for entry in day['entries']:
            # Synthetic rows are laid out sequentially for the preview only.
            end = start+timedelta(seconds=entry['seconds'])
            sessions.append({'name':entry['name'],'start':start.isoformat(),
                             'end':end.isoformat(),'seconds':entry['seconds']})
            start = end+timedelta(minutes=4)
        day['sessions'] = sessions
        day['timeline_synthetic'] = True
        events.append({'id':'demo-'+day['date'],'title':'Project check-in · fictional',
                       'start':day['date']+'T10:00:00-04:00','end':day['date']+'T10:30:00-04:00',
                       'calendar':'Demo calendar'})
    return ({'events':events,'mode':'demo','message':'Fictional calendar and session times.'},
            {'state':'demo','message':'Synthetic session preview. No personal database is read.'})

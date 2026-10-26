#!/usr/bin/env python3
"""Generate fictional examples. Never reads personal exports."""
from datetime import date, timedelta
import json
from pathlib import Path

folder = Path(__file__).resolve().parents[1] / 'dashboard/examples'
folder.mkdir(exist_ok=True)
end = date(2026,10,25)
for i in range(56):
    day = end-timedelta(days=55-i)
    recent = (end-day).days < 7
    gaming = 30 if recent else 60
    social = 50 if recent else 20
    if day.weekday()==0:
        social += 80
    rows = [f'Brawl Stars ({gaming}m)', f'Instagram ({social}m)',
            'Google Chrome (2h 15m)', 'ChatGPT (40m)', 'Calendar (10m)']
    payload = {'schema_version':'1', 'report_date':day.isoformat(),
               'captured_at':(day+timedelta(days=1)).isoformat()+'T10:00:00-04:00',
               'query_period':'yesterday', 'device_scope':'all_devices',
               'collector_device':'Synthetic demo', 'measurement':'cumulative_daily_usage',
               'raw_activity_text':'\n'.join(rows), 'synthetic':True}
    (folder/(day.isoformat()+'.json')).write_text(json.dumps(payload, indent=2)+'\n')
print('Generated 56 fictional days in dashboard/examples')

"""Read the exporter's own SQLite store and Daybook's calendar cache, never Apple DBs."""
from collections import defaultdict
from contextlib import closing
from datetime import datetime, timedelta, timezone, time
import json
import math
import os
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo

EXPORTER_DB = Path.home()/'Library/Application Support/Daybook/screentime.db'


def local_zone():
    try:
        name = os.environ.get('TZ') or os.readlink('/etc/localtime').split('zoneinfo/')[-1]
        return ZoneInfo(name)
    except (OSError, ValueError, KeyError):
        return ZoneInfo('UTC')


def timestamp(value):
    dt = datetime.fromisoformat(value.replace('Z','+00:00'))
    if dt.utcoffset() is None:
        raise ValueError('Timestamp needs a timezone')
    return dt


def union(intervals):
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end,merged[-1][1]))
        else:
            merged.append((start,end))
    return merged


def exporter_days(path=EXPORTER_DB, now=None, zone=None):
    now = now or datetime.now(timezone.utc)
    zone = zone or local_zone()
    status = {'name':'Screen Time Exporter','state':'missing','path':str(path),
              'message':'Waiting for the exporter database. Enable its Full Disk Access, then sync.'}
    if not path.is_file():
        return [], status
    grouped = defaultdict(list)
    try:
        with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
            db.row_factory = sqlite3.Row
            run = db.execute('SELECT status,finished_at,error FROM runs ORDER BY id DESC LIMIT 1').fetchone()
            successful = db.execute("SELECT finished_at FROM runs WHERE status='success' ORDER BY id DESC LIMIT 1").fetchone()
            if run:
                status.update(state=run['status'],last_sync=run['finished_at'],message=run['error'] or run['status'])
            # SQL datetime comparisons avoid lexical Z versus +00:00 differences.
            rows = db.execute('''SELECT e.*, d.name AS device_name FROM screen_events e
                LEFT JOIN devices d ON d.device_id=e.device_id
                WHERE julianday(started_at_utc)+duration_s/86400 > julianday(?)
                AND julianday(started_at_utc) < julianday(?)''',
                ((now-timedelta(days=45)).isoformat(),now.isoformat())).fetchall()
        for row in rows:
            start = timestamp(row['started_at_utc']).astimezone(timezone.utc)
            seconds = float(row['duration_s'])
            if not math.isfinite(seconds) or not 0 < seconds <= 7*86400:
                continue
            end = min(start+timedelta(seconds=seconds), now)
            key = (row['device_id'],row['device_name'] or row['device_id'],
                   row['bundle_id'],row['title'] or row['bundle_id'])
            grouped[key].append((start,end))
        days = {}
        last_success = timestamp(successful['finished_at']) if successful and successful['finished_at'] else None
        for (device_id, device_name, bundle_id, name), intervals in grouped.items():
            for start, end in union(intervals):
                cursor = start
                while cursor < end:
                    local = cursor.astimezone(zone)
                    next_midnight = datetime.combine(local.date()+timedelta(days=1),time(),zone).astimezone(timezone.utc)
                    stop = min(end,next_midnight)
                    day = days.setdefault((local.date().isoformat(),device_id), {
                        'date':local.date().isoformat(),'device_scope':f'Exporter · {device_name} [{device_id[:8]}]',
                        'complete':bool(last_success and last_success >= next_midnight),
                        'captured_at':(last_success or now).isoformat(),'source':'Screen Time Exporter',
                        'snapshot_count':1,'entries':[],'sessions':[],'hourly':[],
                        'unparsed':[],'raw_activity_text':'Session records from the exporter’s local database.',
                        'timezone':str(zone),'source_kind':'exporter'})
                    day['sessions'].append({'name':name,'bundle_id':bundle_id,'start':cursor.isoformat(),
                                            'end':stop.isoformat(),'seconds':(stop-cursor).total_seconds()})
                    cursor = stop
        for day in days.values():
            apps = defaultdict(float)
            hours = defaultdict(lambda: defaultdict(float))
            for session in day['sessions']:
                apps[session['name']] += session['seconds']
                cursor, end = timestamp(session['start']), timestamp(session['end'])
                while cursor < end:
                    # Advance in UTC so the repeated autumn hour keeps its offset.
                    local = cursor.astimezone(zone)
                    hour_start = local.replace(minute=0,second=0,microsecond=0).astimezone(timezone.utc)
                    stop = min(end,hour_start+timedelta(hours=1))
                    hours[hour_start.isoformat()][session['name']] += (stop-cursor).total_seconds()
                    cursor = stop
            day['entries'] = [{'name':name,'seconds':seconds,'kind':'app'} for name,seconds in apps.items()]
            day['total_seconds'] = sum(apps.values())
            day['sessions'].sort(key=lambda s:s['start'])
            day['hourly'] = [{'start':start,'label':timestamp(start).astimezone(zone).strftime('%H:%M %Z'),
                             'apps':[{'name':name,'seconds':seconds} for name,seconds in values.items()]}
                            for start, values in sorted(hours.items())]
        status['event_count'] = len(rows)
        if not rows:
            status['message'] = 'No sessions available yet. Check exporter permissions and Share Across Devices.'
        return sorted(days.values(),key=lambda d:(d['date'],d['device_scope'])), status
    except (OSError,sqlite3.Error,ValueError,OverflowError) as exc:
        status.update(state='error',message=str(exc))
        return [], status


def calendar_data(folder):
    path = folder/'calendar.json'
    if not path.exists():
        path = folder/'calendar-snapshot.json'
    try:
        data = json.loads(path.read_text())
        events = []
        for event in data.get('events',[]):
            if event.get('all_day') or event.get('status') == 'cancelled' or event.get('response') == 'declined':
                continue
            start,end = timestamp(event['start']),timestamp(event['end'])
            if end <= start:
                continue
            events.append({k:event[k] for k in ('id','title','start','end','calendar') if k in event})
        return {**data,'events':events}
    except FileNotFoundError:
        return {'events':[],'mode':'disconnected','message':'Connect calendars to see scheduled events alongside activity.'}
    except (OSError,ValueError,KeyError,TypeError) as exc:
        return {'events':[],'mode':'error','message':str(exc)}


def calendar_for_day(data, date_string, zone=None):
    zone = zone or local_zone()
    start = datetime.fromisoformat(date_string).replace(tzinfo=zone).astimezone(timezone.utc)
    end = datetime.combine(start.astimezone(zone).date()+timedelta(days=1),time(),zone).astimezone(timezone.utc)
    return [e for e in data['events'] if timestamp(e['start']) < end and timestamp(e['end']) > start]

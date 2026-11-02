from datetime import datetime, timezone
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from zoneinfo import ZoneInfo

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from activity import prepare_day, comparisons
from classification import totals
from sources import exporter_days, calendar_data, calendar_for_day
from runtime import write_json


def day(date='2026-10-26',complete=True,seconds=600,scope='phone'):
    return prepare_day({'date':date,'device_scope':scope,'complete':complete,
                        'entries':[{'name':'Code','seconds':seconds}]})


class ActivityTests(unittest.TestCase):
    def test_browser_detail_does_not_inflate_time_or_purposes(self):
        d=prepare_day({'entries':[{'name':'Google Chrome','seconds':3600},
                                  {'name':'youtube.com','seconds':1800},
                                  {'name':'Code','seconds':600}]})
        self.assertEqual(d['total_seconds'],4200)
        self.assertTrue(d['entries'][1]['detail_only'])
        self.assertEqual(totals(d,{'Google Chrome':'Focus','youtube.com':'Entertainment','Code':'Other'}),
                         {'Focus':3600,'Entertainment':0,'Other':600,'Untagged':0})

    def test_explicit_app_identifier_is_never_a_website(self):
        d=prepare_day({'entries':[{'name':'Chrome','seconds':600},
                                  {'name':'com.example.app','seconds':900,'kind':'app'}]})
        self.assertEqual(d['total_seconds'],1500)

    def test_shortcut_reverse_dns_names_stay_apps(self):
        d=prepare_day({'entries':[{'name':'Google Chrome','seconds':600},
                                  {'name':'com.example.social.Video','seconds':900},
                                  {'name':'com.apple.weather','seconds':120},
                                  {'name':'docs.example.com','seconds':300}]})
        self.assertEqual(d['total_seconds'],1620)
        self.assertEqual([e['detail_only'] for e in d['entries']],[False,False,False,True])

    def test_missing_baselines_are_not_zero_and_scopes_stay_separate(self):
        selected=day()
        days=[selected,day('2026-10-25',seconds=1200),day('2026-10-24'),
              day('2026-10-23',scope='mac'),day('2026-10-19',seconds=1800)]
        result=comparisons(selected,days,{'Code':'Focus'})
        self.assertEqual(result[0]['baseline']['Focus'],1200)
        self.assertIsNone(result[1]['baseline'])
        self.assertEqual(result[1]['available_days'],2)
        self.assertEqual(result[2]['baseline']['Total'],1800)
        self.assertTrue(result[2]['comparable'])

    def test_three_day_mean_and_partial_comparison(self):
        selected=day(complete=False)
        days=[selected,day('2026-10-25',seconds=600),day('2026-10-24',seconds=1200),
              day('2026-10-23',seconds=1800)]
        result=comparisons(selected,days,{})
        self.assertEqual(result[1]['baseline']['Total'],1200)
        self.assertFalse(result[1]['comparable'])

    def test_calendar_is_separate_and_excludes_cancelled_declined_all_day(self):
        with tempfile.TemporaryDirectory() as folder:
            event={'id':'one','title':'Meeting','start':'2026-10-26T23:30:00-04:00',
                   'end':'2026-10-27T00:30:00-04:00'}
            write_json(Path(folder)/'calendar.json',{'events':[event,{**event,'status':'cancelled'},
                       {**event,'response':'declined'},{**event,'all_day':True}]})
            calendar=calendar_data(Path(folder))
            self.assertEqual(len(calendar['events']),1)
            for date in ('2026-10-26','2026-10-27'):
                self.assertEqual(len(calendar_for_day(calendar,date,ZoneInfo('America/New_York'))),1)


class ExporterTests(unittest.TestCase):
    def create_db(self,path,rows):
        with closing(sqlite3.connect(path)) as db, db:
            db.executescript('''CREATE TABLE devices(device_id TEXT,name TEXT);
                CREATE TABLE runs(id INTEGER,status TEXT,finished_at TEXT,error TEXT);
                CREATE TABLE screen_events(device_id TEXT,started_at_utc TEXT,duration_s REAL,bundle_id TEXT,title TEXT);
                INSERT INTO devices VALUES ('one','Phone');
                INSERT INTO runs VALUES (1,'success','2026-11-03T12:00:00Z',NULL);''')
            db.executemany('INSERT INTO screen_events VALUES (?,?,?,?,?)',rows)

    def test_overlap_midnight_and_readonly_import(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.db'
            self.create_db(path,[('one','2026-10-26T03:50:00Z',1200,'com.code','Code'),
                                 ('one','2026-10-26T03:55:00Z',1200,'com.code','Code')])
            before=path.read_bytes()
            days,status=exporter_days(path,datetime(2026,11,3,13,tzinfo=timezone.utc),ZoneInfo('America/New_York'))
            self.assertEqual([d['total_seconds'] for d in days],[600,900])
            self.assertEqual(sum(d['total_seconds'] for d in days),1500)
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual(status['state'],'success')

    def test_fall_dst_keeps_repeated_hour_offsets_and_real_duration(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.db'
            self.create_db(path,[('one','2026-11-01T05:30:00Z',7200,'com.code','Code')])
            days,_=exporter_days(path,datetime(2026,11,3,13,tzinfo=timezone.utc),ZoneInfo('America/New_York'))
            self.assertEqual(days[0]['total_seconds'],7200)
            self.assertEqual([h['label'] for h in days[0]['hourly']],['01:00 EDT','01:00 EST','02:00 EST'])
            self.assertEqual(sum(a['seconds'] for h in days[0]['hourly'] for a in h['apps']),7200)

    def test_failed_sync_is_visible_and_does_not_certify_completeness(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.db'
            self.create_db(path,[('one','2026-10-26T12:00:00Z',600,'com.code','Code')])
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("UPDATE runs SET status='partial',error='permission needed'")
            days,status=exporter_days(path,datetime(2026,11,3,13,tzinfo=timezone.utc),ZoneInfo('UTC'))
            self.assertFalse(days[0]['complete'])
            self.assertEqual(status['message'],'permission needed')

if __name__=='__main__':unittest.main()

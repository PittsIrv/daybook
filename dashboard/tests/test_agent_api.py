import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from agent_api import DaybookReader
from activity import prepare_day, comparisons
from classification import totals, app_catalog


def fixture():
    labels = {'Chrome':'Focus','youtube.com':'Entertainment','Transit':'Other'}
    days=[]
    for date in ('2026-10-19','2026-10-25','2026-10-26'):
        d=prepare_day({'date':date,'device_scope':'phone','complete':True,
                       'captured_at':'2026-10-27T09:00:00-04:00','unparsed':[],
                       'entries':[{'name':'Chrome','seconds':3600},{'name':'youtube.com','seconds':1800},
                                  {'name':'Transit','seconds':300},{'name':'New app','seconds':301}]})
        d['purpose_seconds']=totals(d,labels)
        days.append(d)
    for d in days:
        d['comparisons']=comparisons(d,days,labels)
    return {'today':'2026-10-27','updated_at':'2026-10-27T09:00:00-04:00',
            'days':days,'preferences':{'labels':labels},'app_catalog':app_catalog(days,labels),
            'exporter':{'state':'partial','event_count':0},
            'calendar':{'mode':'snapshot','captured_at':'2026-10-20T12:00:00Z','events':[
                {'title':'PRIVATE CALENDAR TITLE','start':'2026-10-26T10:00:00-04:00','end':'2026-10-26T11:00:00-04:00'}]},
            'collection':{},'warnings':[]}


class AgentQueries(unittest.TestCase):
    def setUp(self):
        self.data=fixture()
        self.reader=DaybookReader(loader=lambda:copy.deepcopy(self.data))

    def test_calendar_is_not_exposed_by_any_default_query(self):
        outputs=[self.reader.status(),self.reader.days(),self.reader.day('2026-10-26'),
                 self.reader.compare('2026-10-26'),self.reader.timeline('2026-10-26'),
                 self.reader.labels(),self.reader.calendar('2026-10-26')]
        self.assertNotIn('PRIVATE CALENDAR TITLE',json.dumps(outputs))
        self.reader.include_calendar=True
        self.assertEqual(self.reader.calendar('2026-10-26')['events'][0]['title'],'PRIVATE CALENDAR TITLE')

    def test_threshold_pagination_totals_and_web_detail(self):
        result=self.reader.day('2026-10-26',limit=2)
        self.assertEqual(result['total_seconds'],4201)
        self.assertEqual(result['apps']['matching_count'],3)
        self.assertEqual(result['apps']['next_offset'],2)
        site=next(x for x in result['apps']['items'] if x['name']=='youtube.com')
        self.assertEqual(site['counted_seconds'],0)
        self.assertTrue(site['detail_only'])
        next_page=self.reader.day('2026-10-26',offset=2,limit=2)
        self.assertEqual(next_page['apps']['items'][0]['name'],'New app')
        self.assertEqual(result['purpose_seconds']['Other'],300)

    def test_missing_days_and_missing_hourly_are_not_zero(self):
        self.assertFalse(self.reader.day('2026-10-24')['available'])
        self.assertNotIn('total_seconds',self.reader.day('2026-10-24'))
        self.assertFalse(self.reader.timeline('2026-10-26')['available'])
        result=self.reader.days('2026-10-24','2026-10-26')['scopes'][0]
        self.assertEqual(result['missing_dates'],['2026-10-24'])
        self.assertEqual(len(result['days']),2)
        self.assertIsNone(self.reader.compare('2026-10-26')['comparisons'][1]['baseline'])

    def test_multiple_scopes_require_an_explicit_selection(self):
        self.data['days'].append({**copy.deepcopy(self.data['days'][-1]),'device_scope':'mac'})
        with self.assertRaisesRegex(ValueError,'Choose one exact scope'):
            self.reader.day('2026-10-26')
        self.assertEqual(self.reader.day('2026-10-26','mac')['total_seconds'],4201)
        with self.assertRaises(ValueError):
            self.reader.day('2026-10-26','not a device')

    def test_query_bounds(self):
        for kwargs in ({'limit':501},{'offset':-1},{'minimum_seconds':-1}):
            with self.assertRaises(ValueError):
                self.reader.day('2026-10-26',**kwargs)
        with self.assertRaises(ValueError):
            self.reader.days('2026-01-01','2026-10-26')
        with self.assertRaises(ValueError):
            self.reader.day('20261026')

    def test_shared_reader_needs_no_web_server_or_collection(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); state=root/'state'; data=root/'input'
            state.mkdir();data.mkdir()
            path=data/'example.txt'
            path.write_text(json.dumps({'report_date':'2026-10-26','captured_at':'2026-10-27T08:00:00-04:00',
                                       'device_scope':'phone','query_period':'yesterday','raw_activity_text':'Code (12m)'}))
            before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
            with patch('subprocess.run',side_effect=AssertionError('Read tools must not run collectors')):
                reader=DaybookReader(state,data)
                self.assertEqual(reader.day('2026-10-26')['total_seconds'],720)
                self.assertFalse(reader.timeline('2026-10-26')['available'])
            after={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
            self.assertEqual(before,after)


if __name__=='__main__':unittest.main()

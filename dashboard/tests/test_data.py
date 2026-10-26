import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import load_data, parse_activity


class DataTests(unittest.TestCase):
    def test_duration_names_and_unknown_formats(self):
        rows, unknown = parse_activity('Tool (work) (1h 2m 3s)\n应用（4分钟 5秒）\nApp (12:34)\nApp (5m unexpected)')
        self.assertEqual([(r['name'], r['seconds']) for r in rows], [('Tool (work)', 3723), ('应用',245)])
        self.assertEqual(unknown, ['App (12:34)', 'App (5m unexpected)'])

    def test_snapshots_are_not_added_and_scopes_are_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)
            base = {'report_date':'2026-10-24','device_scope':'all_devices', 'query_period':'today',
                    'captured_at':'2026-10-24T09:00:00-04:00','raw_activity_text':'A (10m)'}
            variants = [base, dict(base, captured_at='2026-10-24T15:00:00-04:00', raw_activity_text='A (20m)'),
                        dict(base, captured_at='2026-10-25T09:00:00-04:00', query_period='yesterday',raw_activity_text='A (30m)\nA (2m)'),
                        dict(base, device_scope='iphone',raw_activity_text='A (3m)'),
                        dict(base,report_date='')]
            for i,x in enumerate(variants): (p/f'{i}.txt').write_text(json.dumps(x))
            result=load_data([p]);self.assertEqual(len(result['days']),2)
            all_devices=next(d for d in result['days'] if d['device_scope']=='all_devices')
            self.assertEqual(all_devices['total_seconds'],1920)
            self.assertEqual(all_devices['snapshot_count'],3)
            self.assertTrue(all_devices['complete'])
            self.assertEqual(len(all_devices['entries']),2) # preserve ambiguous duplicate names
            self.assertEqual(len(result['warnings']),1)

    def test_intraday_is_partial_even_when_viewed_later(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'sample.json'
            p.write_text(json.dumps({'report_date':'2026-10-22','captured_at':'2026-10-22T12:00:00-04:00',
                                     'device_scope':'all_devices','query_period':'today','raw_activity_text':'A (1m)'}))
            self.assertFalse(load_data([p.parent])['days'][0]['complete'])


if __name__=='__main__': unittest.main()

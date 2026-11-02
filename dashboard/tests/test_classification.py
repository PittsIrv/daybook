import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from classification import normalize_labels, totals, app_catalog, daily_markdown
from runtime import Runtime, write_json


def day(date='2026-10-25', scope='phone'):
    return {'date':date, 'device_scope':scope, 'complete':True, 'unparsed':[],
            'total_seconds':7800, 'entries':[
                {'name':'Code','seconds':3600}, {'name':'Brawl Stars','seconds':1800},
                {'name':'Chrome','seconds':2400}]}


class ClassificationTests(unittest.TestCase):
    def test_defaults_are_suggestions_not_confirmed_purposes(self):
        catalog=app_catalog([day()],{})
        self.assertTrue(all(item['category'] is None for item in catalog))
        self.assertEqual(next(a for a in catalog if a['name']=='Code')['suggested_category'],'Focus')
        self.assertEqual(totals(day(),{}),{'Focus':0,'Entertainment':0,'Other':0,'Untagged':7800})

    def test_saved_labels_apply_to_future_days_and_new_app_waits(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'preferences.json'
            labels={'Code':'Focus','Chrome':'Other','Brawl Stars':'Entertainment'}
            write_json(path,{'labels':labels})
            runtime=Runtime(Path(folder),lambda:{})
            later=day('2026-10-26')
            later['entries'].append({'name':'New app','seconds':60})
            catalog=app_catalog([day(),later],runtime.preferences()['labels'])
            self.assertEqual([a['name'] for a in catalog if a['category'] is None],['New app'])
            actual=totals(later,runtime.preferences()['labels'])
            self.assertEqual(actual,{'Focus':3600,'Entertainment':1800,'Other':2400,'Untagged':60})
            self.assertEqual(sum(actual.values()),sum(e['seconds'] for e in later['entries']))

    def test_legacy_explicit_choices_are_preserved_without_default_assignment(self):
        labels=normalize_labels({'game':'Gaming','social':'Social','settings':'Utility',
                                 'browser':'Mixed','editor':'Focus','unknown':'Unclassified'})
        self.assertEqual(labels,{'game':'Entertainment','social':'Entertainment','settings':'Other',
                                 'browser':'Other','editor':'Focus'})

    def test_catalog_groups_names_without_adding_device_times(self):
        catalog=app_catalog([day(),day('2026-10-24','mac')],{'Code':'Focus'})
        self.assertEqual(len(catalog),3)
        code=next(a for a in catalog if a['name']=='Code')
        self.assertEqual(code['scopes'],['mac','phone'])
        self.assertEqual(code['first_seen'],'2026-10-24')
        self.assertEqual(code['last_seen'],'2026-10-25')

    def test_daily_report_has_quantities_without_experiments(self):
        text=daily_markdown(day(),{'Code':'Focus'})
        self.assertIn('Focus: 1h 0m',text)
        self.assertIn('Untagged: 1h 10m',text)
        self.assertIn('Chrome: 0h 40m (Untagged)',text)
        self.assertNotIn('trial',text)
        self.assertIn('not unique elapsed time',text)

if __name__=='__main__':unittest.main()

import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from datetime import datetime, timedelta
from types import SimpleNamespace
import tempfile
import unittest
from runtime import Runtime

class RuntimeTests(unittest.TestCase):
    def test_schedule_bounds(self):
        now=datetime.fromisoformat('2026-10-26T09:00:00-04:00')
        self.assertTrue(Runtime.due(now,{}))
        self.assertFalse(Runtime.due(now.replace(hour=7),{}))
        self.assertFalse(Runtime.due(now,{'success_target':'2026-10-25'}))
        state={'attempt_day':'2026-10-26','last_attempt':now.isoformat(),'attempts':1}
        self.assertFalse(Runtime.due(now+timedelta(minutes=59),state))
        self.assertTrue(Runtime.due(now+timedelta(hours=1),state))
        state['attempts']=3
        self.assertFalse(Runtime.due(now+timedelta(hours=5),state))
        self.assertTrue(Runtime.due(now+timedelta(days=1),state))

    def test_success_requires_fresh_dated_file_and_prevents_repeat(self):
        now=datetime.fromisoformat('2026-10-26T09:00:00-04:00')
        dataset={'yesterday':'2026-10-25','days':[{'date':'2026-10-25','complete':True,'captured_at':now.isoformat()}]}
        calls=[]
        def run(*args,**kwargs):calls.append(args);return SimpleNamespace(returncode=0,stderr='')
        with tempfile.TemporaryDirectory() as folder:
            rt=Runtime(folder,lambda:dataset,lambda:now,run)
            self.assertTrue(rt.collect(automatic=True)[0])
            self.assertFalse(rt.collect(automatic=True)[0])
            self.assertEqual(len(calls),1)
            self.assertEqual(rt.status()['success_target'],'2026-10-25')

    def test_failed_export_is_visible_not_success(self):
        now=datetime.fromisoformat('2026-10-26T09:00:00-04:00')
        with tempfile.TemporaryDirectory() as folder:
            rt=Runtime(folder,lambda:{'yesterday':'2026-10-25','days':[]},lambda:now,
                       lambda *a,**k:SimpleNamespace(returncode=0,stderr=''))
            self.assertFalse(rt.collect()[0])
            self.assertIn('No fresh',rt.status()['error'])
            self.assertNotIn('last_success',rt.status())

if __name__=='__main__':unittest.main()

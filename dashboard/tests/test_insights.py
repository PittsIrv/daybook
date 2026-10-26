import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from datetime import date, timedelta
import unittest
from insights import review, category

END=date(2026,10,25)
def history():
    days=[]
    for i in range(56):
        day=END-timedelta(days=55-i)
        recent=(END-day).days<7
        days.append({'date':day.isoformat(),'device_scope':'all_devices','complete':True,'unparsed':[],
                     'entries':[{'name':'Brawl Stars','seconds':1800 if recent else 3600},
                                {'name':'Instagram','seconds':3000 if recent else 1200},
                                {'name':'Chrome','seconds':7200}]})
    return days

class InsightsTests(unittest.TestCase):
    def test_substitution_and_goal_sensitive_advice(self):
        report=review(history(),END,'all_devices')
        self.assertTrue(report['ready'])
        found=next(f for f in report['findings'] if f['kind']=='substitution')
        self.assertIsNone(found['suggestion'])
        goal=review(history(),END,'all_devices',{'goal':'less_entertainment'})
        self.assertTrue(next(f for f in goal['findings'] if f['kind']=='substitution')['suggestion'])
        self.assertEqual(found['evidence']['before_seconds_per_day'],found['evidence']['after_seconds_per_day'])

    def test_missing_partial_and_unparsed_days_never_become_zero(self):
        for mutation in ('missing','partial','unparsed','empty'):
            days=history()
            if mutation=='missing':days.pop()
            elif mutation=='partial':days[-1]['complete']=False
            elif mutation=='unparsed':days[-1]['unparsed']=['unrecognized']
            else:days[-1]['entries']=[]
            report=review(days,END,'all_devices')
            self.assertFalse(report['ready'],mutation)
            self.assertEqual(report['recent_days'],6)
            self.assertFalse(report['findings'])

    def test_scope_isolation_and_personal_labels(self):
        days=history()
        for d in history():
            d['device_scope']='another_device';d['entries'][0]['seconds']=99999;days.append(d)
        self.assertEqual(review(days,END,'all_devices'),review(history(),END,'all_devices'))
        self.assertEqual(category('Chrome',{}),'Mixed')
        r=review(history(),END,'all_devices',{'labels':{'Brawl Stars':'Mixed','Instagram':'Mixed'}})
        self.assertFalse(r['findings'])

    def test_feedback_suppresses_pattern(self):
        r=review(history(),END,'all_devices',{'feedback':{'substitution:Gaming:Social':'hide','change:Gaming:down':'hide','change:Social:up':'hide'}})
        self.assertFalse(r['findings'])

    def test_weekday_matching_does_not_create_false_change(self):
        days=history()
        for d in days:
            seconds=7200 if date.fromisoformat(d['date']).weekday()>=5 else 1800
            d['entries']=[{'name':'Brawl Stars','seconds':seconds}]
        # Remove one baseline Saturday; matched weekday weighting remains identical.
        days=[d for d in days if d['date']!=(END-timedelta(days=15)).isoformat()]
        r=review(days,END,'all_devices')
        self.assertTrue(r['ready'])
        self.assertFalse(any(f['kind']=='change' for f in r['findings']))

    def test_single_outlier_is_not_a_sustained_change(self):
        days=history()
        for d in days:d['entries']=[{'name':'Brawl Stars','seconds':1800}]
        days[-1]['entries'][0]['seconds']=36000
        r=review(days,END,'all_devices')
        self.assertFalse(r['findings'])

    def test_weekday_pattern_needs_four_of_every_weekday(self):
        days=history()
        for d in days:
            d['entries']=[{'name':'Brawl Stars','seconds':7200 if date.fromisoformat(d['date']).weekday()==0 else 1800}]
        r=review(days,END,'all_devices')
        self.assertEqual(next(f for f in r['findings'] if f['kind']=='weekday')['title'],'Monday tends to have more entertainment')
        r=review(days[-21:],END,'all_devices')
        self.assertFalse(r['findings'])

if __name__=='__main__':unittest.main()

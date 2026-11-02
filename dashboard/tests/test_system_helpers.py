import unittest
from activity import prepare_day
from classification import app_catalog

class SystemHelpersTest(unittest.TestCase):
    def test_helpers_excluded_but_real_apple_and_short_apps_remain(self):
        day = {'date':'2026-10-31', 'device_scope':'all_devices',
               'entries':[{'name':name,'seconds':seconds} for name,seconds in [
                   ('com.apple.InCallService',900),
                   ('com.apple.quicklook.QuickLookUIService',600),
                   ('com.apple.MobileSafari',120),('Code',30)]],
               'sessions':[{'name':'Quick Look','bundle_id':'com.apple.quicklook.QuickLookUIService'}],
               'hourly':[{'apps':[{'name':'com.apple.InCallService','seconds':900}]}]}
        prepare_day(day)
        self.assertEqual(day['total_seconds'],150)
        self.assertEqual(day['sessions'],[])
        self.assertEqual(day['hourly'][0]['apps'],[])
        self.assertEqual({e['name'] for e in app_catalog([day],{})},
                         {'com.apple.MobileSafari','Code'})

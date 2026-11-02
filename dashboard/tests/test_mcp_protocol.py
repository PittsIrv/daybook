"""Optional protocol tests: run using an environment with mcp==2.3.0 installed."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
HAS_MCP=importlib.util.find_spec('mcp') is not None


@unittest.skipUnless(HAS_MCP,'Optional MCP SDK is not installed')
class MCPProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_discovery_and_tool_calls_without_dashboard(self):
        from mcp import Client, StdioServerParameters
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);state=root/'state';data=root/'exports'
            state.mkdir();data.mkdir()
            (data/'day.txt').write_text(json.dumps({'report_date':'2026-10-26','captured_at':'2026-10-27T08:00:00-04:00',
                'device_scope':'phone','query_period':'yesterday','raw_activity_text':'Code (12m)\nCalendar (5m)'}))
            program=str(Path(__file__).resolve().parents[1]/'mcp_server.py')
            parameters=StdioServerParameters(command=sys.executable,args=[program,'--state-dir',str(state),'--data-dir',str(data)])
            async with Client(parameters) as client:
                tools=(await client.list_tools()).tools
                names={t.name for t in tools}
                self.assertEqual(names,{'get_status','list_days','get_day','compare_day','get_timeline','list_app_labels'})
                self.assertTrue(all(t.annotations.read_only_hint and not t.annotations.destructive_hint for t in tools))
                day=await client.call_tool('get_day',{'date':'2026-10-26'})
                self.assertFalse(day.is_error)
                self.assertEqual(day.structured_content['total_seconds'],1020)
                self.assertEqual(len(day.structured_content['apps']['items']),1)
                timeline=await client.call_tool('get_timeline',{'date':'2026-10-26'})
                self.assertFalse(timeline.structured_content['available'])
                missing=await client.call_tool('get_day',{'date':'2026-10-24'})
                self.assertFalse(missing.structured_content['available'])
                bad=await client.call_tool('get_day',{'date':'nonsense'})
                self.assertTrue(bad.is_error)
            # Opt-in changes the registered tool set, without changing any data.
            parameters.args.append('--include-calendar')
            async with Client(parameters) as client:
                self.assertIn('get_calendar',{t.name for t in (await client.list_tools()).tools})
            self.assertEqual(list(state.iterdir()),[])


if __name__=='__main__':unittest.main()

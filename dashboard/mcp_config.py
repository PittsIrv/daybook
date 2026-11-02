"""Print a local MCP client entry. Does not edit or connect any agent configuration."""
import argparse
import json
from pathlib import Path
import shutil


def configuration(include_calendar=False):
    fallback = Path.home()/'.local/bin/uv'
    command = shutil.which('uv') or (str(fallback) if fallback.is_file() else 'uv')
    args = ['run','--script',str(Path(__file__).with_name('mcp_server.py').resolve())]
    if include_calendar:
        args.append('--include-calendar')
    return {'mcpServers':{'daybook':{'command':command,'args':args}}}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-calendar',action='store_true')
    args=parser.parse_args()
    print(json.dumps(configuration(args.include_calendar),indent=2))

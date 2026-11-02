# Daybook for agents

Daybook can be queried by a local MCP-capable agent without opening the dashboard or running its HTTP server. The MCP reader uses the same labels, overlap handling and comparisons as the dashboard. It does not start collectors or request Apple permissions.

## Connect once

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if it is missing. Keep this source folder in a permanent location. Generate the client entry from the project folder:

```bash
python3 dashboard/mcp_config.py
```

This prints the actual `command` and `args` for this checkout in the `mcpServers` JSON format used by several desktop clients. Add the entry to your chosen agent's MCP settings; clients using another configuration format accept the same command and argument list. No existing client settings are changed by this command.

The command runs `uv run --script /absolute/path/to/daybook/dashboard/mcp_server.py`. Inline script metadata pins the official MCP SDK to `mcp==2.3.0` and requests Python 3.11+. uv manages the environment; the first launch needs network access to download dependencies and possibly Python. Subsequent launches reuse its cache. The MCP process is launched and stopped by the agent, using stdio. It opens no network port.

Calendar event titles are not exposed by default. To opt in:

```bash
python3 dashboard/mcp_config.py --include-calendar
```

For isolated tests or nondefault storage, the server also accepts `--state-dir /path/to/state` and `--data-dir /path/to/shortcut/exports`. State includes preferences, the exported `screentime.db` and calendar caches. These paths are launch-time configuration, not arguments an agent can change through a tool.

## Tools

| Tool | Returns |
|---|---|
| `get_status` | Freshness, source scopes, hourly availability and calendar mode |
| `list_days` | Daily totals with explicit missing dates, up to 90 days |
| `get_day` | Purpose totals and paginated app/site breakdown |
| `compare_day` | Previous day, previous three-day average and same weekday last week |
| `get_timeline` | Hourly records and paginated sessions, when available |
| `list_app_labels` | Saved labels and unconfirmed suggestions |
| `get_calendar` | Opt-in scheduled event titles and times for one day |

Tools are read-only and return structured JSON. They do not edit labels, create events, launch Shortcuts, change permissions or send messages. Dates use `YYYY-MM-DD`. If multiple device/source scopes exist, a single-day query requires one exact scope from `get_status`; combining sources can double-count usage. App and session filters default to strictly more than 300 seconds, while daily totals retain shorter activity.

Example requests to an agent:

- “Check Daybook's data freshness, then compare yesterday with the same weekday last week.”
- “Show my phone activity by hour yesterday, if session data is available.”
- “Has entertainment time increased, or did I simply have more recorded activity? Separate missing data from real changes.”
- “Compare my calendar plans with recorded activity. Don't assume a scheduled meeting actually happened.”

The deterministic code calculates time and comparisons; the user's existing agent explains them. Daybook needs no separate model service or model API key. The agent may send tool results to its own model provider according to that client's settings. Local storage does not imply that the agent's analysis is offline.

## Collection and sleep

Recording and importing are separate. Apple's iPhone Screen Time can record phone activity while the Mac sleeps. Once the Mac wakes, Apple can sync retained records, and the exporter can import their original timestamps. The importer runs every 15 minutes while the Mac is awake; this interval does not restrict historical records to 15-minute precision. Delivery is subject to Apple's sync delays, retention and Full Disk Access. Recovery of sleep-period phone data has not yet been verified on this installation because the exporter is still permission-blocked.

A sleeping Mac has no active local app use to record. No Daybook collector or local MCP process runs while the Mac sleeps, and a remote agent cannot query that sleeping Mac through this stdio connection.

Screen Time Exporter's launch agent runs independently of the web dashboard. The original Shortcut collector and automatic calendar refresh currently run in Daybook's background web service; keep that service running if you rely on those paths, even if you never open its page. Closing the browser does not stop that service. The MCP only reads their saved results. It does not schedule daily agent reviews; scheduling belongs to the agent host.

## What already exists

[Screen Time Exporter has its own MCP server](https://github.com/nichtlegacy/screentime/blob/main/docs/mcp.md), suitable for raw exporter reports. Daybook's adapter adds the Shortcut fallback, saved Focus/Entertainment/Other labels, conservative browser overlap handling, same-scope comparisons, and optional calendar context. There is no need to run both MCPs unless those additional raw exporter queries are useful.

## Distribution state

The current implementation is in the source checkout. The old public alpha release does not contain it. A public installer should eventually handle the background importer, OS permission setup and agent registration together; this source version still needs one-time setup. Neither a hosted dashboard nor an MCP server bypasses Apple's local permissions.

## Verify locally

The core tests do not require MCP. For the protocol test, install the pinned SDK in a development environment, then run:

```bash
python3 -m unittest discover -s dashboard/tests
```

The protocol test starts an actual stdio subprocess against fictional data, checks tool discovery, structured responses, strict five-minute filtering, missing-hourly states, invalid input and calendar opt-in. It skips when the optional SDK is absent.

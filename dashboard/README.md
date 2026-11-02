# Daybook local dashboard

See the [project README](../README.md) for setup, automation, privacy and one-time app labels.

- `server.py`: loopback HTTP API, snapshot selection, daily collection loop, report files.
- `read_model.py`: shared read-only data view for the web UI and agents.
- `agent_api.py`, `mcp_server.py`, `mcp_config.py`: optional stdio MCP queries and client-entry generator.
- `runtime.py`: durable settings/status, bounded collection retries.
- `classification.py`: saved purposes, app setup catalog and daily report totals.
- `sources.py`: read-only exporter database adapter, timezone-aware hourly records, calendar cache.
- `activity.py`: conservative website deduplication and same-scope day comparisons.
- `integrations.py` / `CalendarBridge.swift`: optional exporter agent and local read-only calendar bridge.
- `insights.py`: legacy weekly engine; not invoked by the current dashboard.
- `manage.py`: optional macOS login service installation/removal.
- `static/`: buildless dashboard, daily totals and one-time labels.
- `examples/`: fictional data, isolated from personal imports by `--demo`.
- `tests/`: parsing, selection, classification and scheduling tests.

Run `python3 server.py --demo --open` to preview without reading personal data. Real collection uses the installed **Screen Time Yesterday** Shortcut and may need its existing permissions resolved once. `--no-auto` prevents automatic collection. `--state-dir` isolates settings and reports. Reports and preferences normally live under `~/Library/Application Support/Daybook/`; daily input normally lives in iCloud Drive → Shortcuts → ScreenTime → snapshots.

The legacy personal collector uses scope `all_devices`; the portable release uses `configured_device` because its device selection is not embedded. These scopes remain separate. Do not relabel and mix scopes unless you have verified they measure the same devices.

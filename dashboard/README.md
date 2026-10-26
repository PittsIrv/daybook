# Daybook local dashboard

See the [project README](../README.md) for setup, automation, privacy and statistical thresholds.

- `server.py`: loopback HTTP API, snapshot selection, daily collection loop, report files.
- `runtime.py`: durable settings/status, bounded collection retries.
- `insights.py`: deterministic weekly comparisons and suggestions.
- `manage.py`: optional macOS login service installation/removal.
- `static/`: buildless dashboard, corrections and feedback.
- `examples/`: fictional data, isolated from personal imports by `--demo`.
- `tests/`: parsing, selection, statistical and scheduling tests.

Run `python3 server.py --demo --open` to preview without reading personal data. Real collection uses the installed **Screen Time Yesterday** Shortcut and may need its existing permissions resolved once. `--no-auto` prevents automatic collection. `--state-dir` isolates settings and reports. Reports and preferences normally live under `~/Library/Application Support/Daybook/`; daily input normally lives in iCloud Drive → Shortcuts → ScreenTime → snapshots.

The legacy personal collector uses scope `all_devices`; the portable release uses `configured_device` because its device selection is not embedded. These scopes remain separate. Do not relabel and mix scopes unless you have verified they measure the same devices.

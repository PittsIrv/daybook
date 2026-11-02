# Verification — v0.1.0-alpha

## Current source: daily totals and one-time labels

The active dashboard now centers daily quantities, with Focus, Entertainment and Other. New names remain untagged until explicitly assigned. New classification tests cover suggestion/confirmation separation, saved labels across future days, new-app detection, legacy explicit-label migration, name grouping across scopes and quantitative daily reports. The earlier insight engine remains as legacy source and tests but is not invoked by the dashboard.

Browser verification with isolated fictional data checks individual labeling, optional bulk suggestions, persistence after reload and correct daily totals. No personal labels are assigned during this check. The public v0.1.0-alpha ZIP has not been replaced.

## Current source: integrations and comparisons

36 local tests pass. New coverage checks browser/site suppression, explicit and Shortcut reverse-DNS app identifiers, same-scope comparisons with missing days, three-day averages, partial-day comparisons, calendar cancellation/decline handling, cross-midnight sessions, overlap union, repeated DST hours and read-only database import. Browser checks confirmed saved labels, day selection, same-weekday comparisons and the session/calendar layout using fictional data, with no JavaScript errors. The live dashboard showed missing-baseline and permission-blocked states correctly. The EventKit helper compiled successfully on the development Mac.

The local exporter agent is installed with a dedicated Python runtime, local-only sync and App Store lookup disabled. Its first runs were permission-blocked, so live session history is not yet verified. A primary Google Calendar snapshot was imported privately; it is explicitly labelled static. The calendar helper still needs user permission and calendar selection before automatic sync can be verified. Personal data is excluded from packaging. The public alpha ZIP is unchanged.

## Local MCP source verification

43 tests pass with the optional official MCP SDK 2.3.0, including a real stdio client/server handshake, tool discovery, structured output, strict five-minute filtering, pagination, missing data, source ambiguity, invalid arguments and calendar opt-in. The Python 3.9 core run passes 42 tests and skips the optional protocol test. A local MCP client also read the latest saved personal daily record without opening an HTTP connection or running collection; no calendar titles were exposed by default.

The dashboard and MCP now share `read_model.py`. Query tests verify no writes to activity/settings storage and no collector subprocess calls. Read-only SQLite connections close after each query. This establishes the local interface, not agent coaching quality or compatibility with every desktop client. Agent configuration has not been edited, and the public release is unchanged.

## Published alpha verification (historical)

## Automated

The local test suite passes under Python 3.9.6 and Python 3.13.5 on the development Mac. These results cover Python compatibility, not other hardware or Apple permissions.

- Parser and selection tests: English/Chinese durations, unknown lines, partial days, latest completed export, duplicate cumulative snapshots and separate scopes.
- Insight tests: missing/partial/empty/unparsed days, substitution, goal-dependent advice, scope isolation, remembered labels, hidden patterns, weekday matching, single-outlier suppression and repeated weekday patterns.
- Runtime tests: after-8-AM collection, success deduplication, one-hour retry separation, three-attempt daily ceiling, fresh-export validation and visible failure status.
- Launcher tests: reuse only a matching Daybook instance and distinguish demo mode, unrelated services and stopped servers.
- JavaScript syntax check with Node (development check only; Node is not a runtime requirement).

## Interactive

The login service was installed and its first automatic collection produced a fresh completed-day export and a saved weekly Markdown report on the development Mac. The real dashboard showed the last successful collection and a truthful insufficient-history state. This does not establish reliability across later sleep/login cycles.

The synthetic demo is isolated from personal exports. Goal selection, persistent settings, hiding/resetting findings and category corrections are checked in a browser. Report evidence and limitations are visible in the UI.

A sanitized portable Shortcut without an embedded device selector was signed, imported and run on the development Mac. Its non-saving verification variant returned a dated previous-day JSON result with nonempty activity. Default device scope was not established; first-run scope verification remains required. The existing personal daily Shortcut's save-to-iCloud and dashboard import path were previously verified on this Mac.

## Still requires validation

- Fresh setup and device selection on a second Mac and other supported OS versions.
- End-to-end unattended collection across logout/login, sleep, restart and iCloud delays.
- iPhone locked-screen collection.
- Advice usefulness over several weeks with real users. Thresholds are product heuristics, not a validated model of productivity.

Daily data does not establish session-level focus, activity timing or causal effects. The alpha does not reconstruct missed historical days or send native/email notifications.

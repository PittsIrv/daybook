# Verification — v0.1.0-alpha

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

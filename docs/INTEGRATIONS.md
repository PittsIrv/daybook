# Optional hourly activity and calendars

The daily Shortcut route still works without Full Disk Access. These integrations are optional and remain separate from its totals.

## Screen Time Exporter

Daybook supports [nichtlegacy/screentime](https://github.com/nichtlegacy/screentime), tested against version 2.0.0, commit `c25696a3ddac32058ae809f63c04e2bfc0c8dc0f`. Its app sessions come from Apple's synced Biome stream and the Mac knowledgeC store. These are unofficial Apple stores; availability, retention and sync delays vary. Its current adapter provides app sessions, not website-session detail.

Install with [uv](https://docs.astral.sh/uv/getting-started/installation/). A dedicated runtime is recommended because the interpreter itself needs Full Disk Access:

```bash
uv python install 3.13 --no-bin --install-dir "$HOME/Library/Application Support/Daybook/python"
```

Use the actual installed `bin/python3.13` path from that folder in the next command (the patch version in its folder name can change):

```bash
uv tool install --python /path/to/dedicated/bin/python3.13 'git+https://github.com/nichtlegacy/screentime@c25696a3ddac32058ae809f63c04e2bfc0c8dc0f'
python3 dashboard/integrations.py install-exporter
```

The installer prints the resolved interpreter path. Open **System Settings → Privacy & Security → Full Disk Access → +**, press **Command–Shift–G**, enter that path and enable it. Granting access to an interpreter also covers other code run using that same interpreter, hence the dedicated runtime. The dashboard itself does not need this permission. Then click **Exporter setup & retry → Retry exporter sync** in Daybook.

The `io.daybook.exporter` login agent runs `screentime sync` every 15 minutes while the Mac is awake. Its private config disables App Store lookups and does not configure any cloud export sinks. It writes `~/Library/Application Support/Daybook/screentime.db`. Daybook opens this database read-only, merges overlapping same-app intervals per device, and splits sessions at local midnight and hour boundaries, including daylight-saving changes. Different devices and Shortcut exports are never added together.

On iPhone and Mac enable **Screen Time → Share Across Devices** under the same Apple account. Imported phone history can arrive after the Mac wakes; no hourly iPhone automation is necessary for this route. It cannot recover records Apple has already discarded, and a successful sync does not prove every remote device has finished syncing.

An empty or permission-blocked import is shown as such; no synthetic sessions are substituted into personal data. To stop this optional agent:

```bash
launchctl bootout "gui/$(id -u)/io.daybook.exporter"
```

Remove its `~/Library/LaunchAgents/io.daybook.exporter.plist` if you also want to prevent future login starts. This does not delete your recorded history.

## Google Calendar through Apple Calendar

1. Add your Google account in **Calendar → Add Account → Google**, and enable the calendars you want to sync. This uses Apple's account connection, not a Google API key in Daybook.
2. Install the helper from the project folder (requires Apple's Swift command-line tools and macOS 14+):

   ```bash
   python3 dashboard/integrations.py install-calendar
   ```

3. Click **Connect calendars** in Daybook. Approve the macOS calendar prompt, choose calendars in the helper, and click **Save and sync**. No calendars are preselected on first setup.
4. Refresh Daybook. Its existing background loop asks the helper to refresh every 15 minutes while running. Use **Choose calendars** to adjust the selection later.

The helper stores only identifiers, titles, start/end times and calendar names in `calendar.json` under Daybook's private state folder. It does not save attendees, descriptions, meeting links or locations. It ignores all-day, cancelled and personally declined events and reads a rolling window of 45 days back and 14 days forward. It uses no event modification APIs. macOS calls the EventKit read permission “Full Access”; the app's behavior remains read-only.

A connector-imported `calendar-snapshot.json`, if supplied, is only a fallback snapshot. It is explicitly labelled as static and is not evidence of an ongoing Google connection. Native calendar data takes precedence after setup. Rebuilding the unsigned local helper may require macOS permission again. The helper is not notarized or bundled in the old public alpha release.

Calendar events are scheduled time. They appear beside measured activity and never increase Focus, Entertainment, Other or total activity.

## Interpretation

- The app table shows daily app/site totals **strictly greater than 300 seconds**. Hourly rows show app totals above that threshold within the hour; the expanded session log uses the threshold per session. Shorter usage remains in daily totals and CSV.
- A website in a Shortcut export is detail-only when a recognized browser is also present. Its time and label do not add to the browser's time or purpose totals. The export does not identify the parent browser, so Daybook does not invent a browser allocation. Recognized browser names are listed in `dashboard/activity.py`.
- Each app/name has one saved purpose: Focus, Entertainment or Other. Other means travel, food and other life activities. It never contributes to Focus or Entertainment. Old Mixed and Utility choices migrate to Other.
- Day comparisons stay in the selected device/source scope. The three-day mean requires all three previous calendar days; absent days are not zeros. Partial-day comparisons display reference totals without claiming an increase or decrease.
- “Completed-day query” means a query or successful sync occurred after the day ended. It is not a guarantee of complete Apple synchronization. Reported activity is not necessarily unique elapsed time across different apps.

## Validation boundary

Database parsing, interval union, midnight and daylight-saving splits, scope isolation, browser-detail suppression, calendar exclusion and comparison baselines are covered by local tests. The native calendar helper compiles on the development Mac. Live exporter history and automatic calendar sync remain unverified until the user grants the corresponding OS permissions and selects calendars.

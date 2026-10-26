# Releasing Daybook

GitHub is for the public code, issues and downloadable releases. Run personal collection locally. GitHub Pages can host a synthetic static demo or documentation; it cannot run the Python server or your Mac's Shortcuts. The repository is https://github.com/PittsIrv/daybook. Local build scripts prepare artifacts; publication is a separate explicit step.

## Prepare a release

1. Run tests: `python3 -m unittest discover -s dashboard/tests -v`.
2. Generate a sanitized collector: `python3 shortcuts/build_shortcuts.py --portable`.
3. On macOS, sign the yesterday collector:

   ```bash
   shortcuts sign --mode anyone --input 'shortcuts/release/Screen Time Yesterday.unsigned.shortcut' --output 'shortcuts/release/Screen Time Yesterday.shortcut'
   ```

   Apple's signing process can send a copy to Apple for validation. The portable source has no personal device identifier or usage data. Signing is not a runtime compatibility test.

4. Run `python3 scripts/package_release.py`. It creates an explicit allowlist-based ZIP, a manifest with SHA-256 hashes, and `release-source/` for initializing the public repository. It never copies the entire working folder.
5. Review the manifest and release directory. Publish **only `release-source/`** as the GitHub repository. Attach the ZIP and manifest to a versioned GitHub release. Do not upload personal exports, local state, old diagnostic shortcuts or personal screenshots.
6. Verify first-run setup with someone on a second Mac before calling the release generally compatible. Preserve the alpha label until that succeeds.

Use `--source-only` on non-Mac systems; it omits the signed Shortcut and works without Apple signing. The source repository includes the portable generator and instructions. Never publish the original shared Shortcut from the development workspace.

## Suggested first release

Title: **Daybook v0.1.0-alpha — private weekly Screen Time reviews**

A local Python dashboard with Shortcuts-based daily collection, an optional macOS login service, and deterministic weekly patterns. No API key or Full Disk Access. Includes a reproducible synthetic demo. Daily totals only; unattended execution and OS compatibility still need broader testing. No email or native notification delivery in this alpha.

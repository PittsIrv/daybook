# Daily collector

The release ZIP contains a signed **Screen Time Yesterday.shortcut**. Import it into Apple's Shortcuts, expand **Get App & Website Activity**, and choose the device scope you want, such as All Devices. Keep that scope unchanged across runs. Run once before enabling automatic collection and resolve any native permission prompts.

Output: iCloud Drive → Shortcuts → ScreenTime → snapshots → timestamped `.txt` files containing JSON. This is one daily query per invocation; there is no long Wait loop and the Shortcut does not schedule itself. Daybook's optional Mac login service calls it automatically.

The portable collector has no embedded device identifier. Its output says `device_scope: configured_device`. A default selection returned activity on the development Mac, but that is not proof of which devices are included on another Mac. Verify the scope in the editor and compare the first result with Screen Time settings. Changing the selector without changing the dataset can invalidate historical comparisons.

## Build from source

```bash
python3 shortcuts/build_shortcuts.py --portable
shortcuts sign --mode anyone --input 'shortcuts/release/Screen Time Yesterday.unsigned.shortcut' --output 'shortcuts/release/Screen Time Yesterday.shortcut'
```

Signing requires macOS and may send the sanitized Shortcut to Apple for validation. It does not verify runtime behavior. Portable builds need no original export; the generator contains the native action definition and the complete workflow. The optional private development source is never packaged.

The action is present in the tested macOS 27 installation; its installed metadata lists introduction in OS 26, but feature availability and permissions may vary. If it is unavailable, this alpha cannot collect on that device. iPhone scheduling and locked-phone execution remain unverified. No developer account, API key or Full Disk Access is requested by this collector.

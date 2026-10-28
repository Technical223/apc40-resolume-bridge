# APC40 Bridge — macOS preview

Experimental tester build, separate from Windows. It reuses the shared MIDI engine for Hue pads, Colorize feedback, utility lighting and reconnects. A native dialog menu provides preparation, a three-minute test, stop and diagnostic export. This is not yet a full macOS dashboard or production release.

[Tester instructions](TESTER.md) · [Main project](https://github.com/Technical223/apc40-resolume-bridge)

## Requirements and launch

A Mac, Arena 7, APC40 mkII over USB and Python 3.9+ are required. Python 3.11/3.12 from [python.org](https://www.python.org/downloads/macos/) is recommended. Python is not bundled. No Homebrew, Xcode or sudo is needed. **Prepare dependencies** downloads pinned MIDI wheels into a private environment. Missing compatible wheels produce an error report instead of compiling native code.

1. Extract the ZIP into a permanent local folder.
2. Open **APC40 Bridge macOS Preview.app**. This bundle is unsigned and unnotarized. If macOS blocks it, send the exact warning; keep system protections enabled. **Open Preview.command** is an optional Terminal launcher for debugging.
3. Choose **Prepare dependencies** and wait for completion.
4. Configure IAC and Arena below. Use a disposable test composition.
5. Choose **Start 3-minute test**. It initializes LEDs and may resend physical fader/knob positions to Arena. The test can also run with Arena closed for hardware-only diagnostics; process detection is recorded, not used as a start gate.
6. The test ends automatically and creates **APC40-macOS-debug-…zip** on the Desktop. **Stop test** ends it early. **Export diagnostics** stops an active test and creates another ZIP. **Quit** stops the test and releases ports.

If Python is missing, the launcher still attempts a small ZIP with the macOS version, architecture and missing-Python error. It does not invoke the system Python/Xcode installer shim.

## Native MIDI setup

Open **Audio MIDI Setup → Window → Show MIDI Studio → IAC Driver**, enable **Device is online**, and add two buses:

- **APC VIRT A**: bridge → Arena.
- **APC VIRT B**: Arena → bridge.

Full names may be prefixed, e.g. IAC Driver APC VIRT A. The adapter accepts one unique matching name and refuses missing or ambiguous matches; it never opens a default port. With multiple APC devices, set the exact physical port name through **Open settings file**.

In **Arena → Preferences → MIDI**, enable **input only** on A and **output only** on B. Disable physical APC40 input/output in Arena for this test. Keep clock off on both IAC buses. Do not route feedback into the same bus. Leave unrelated devices unchanged.

The preview does not edit Arena preferences, create IAC buses, install login items or set autostart. Stop it before re-enabling physical APC input/output for direct use.

The example preset is inside the app at Contents/Resources/resolume/APC40 BRIDGE EXAMPLE.xml (Finder → Show Package Contents). Copy it manually into ~/Documents/Resolume Arena/Shortcuts/MIDI if needed; do not overwrite your own preset. Or use an existing compatible preset. Set **Any device**, Hue maximum **0.63871**, notes 32–39 and CCs 48–55 on channel 1 (zero-based 0). Colorize feedback is **5 = active, 3 = bypass**. Seven-bit feedback has the same limits as Windows.

## Tester checklist

1. Move each Hue knob and compare the pad and Arena layer.
2. Toggle each Colorize pad; check white for bypass and restored Hue when active.
3. Change Hue/Colorize with the mouse in Arena and check APC feedback.
4. Try a fader, clip pad and utility button; note incorrect behavior.
5. Optionally unplug/reconnect USB during the test; check recovery.
6. Stop or wait for expiry. Check that another MIDI app can use the APC afterward.

Send the ZIP with which steps worked, Arena version and approximate failure times. A completed timer does not prove MIDI works: check connections and traffic. **no_connection** means the bridge never opened all required ports.

## Diagnostics and local data

Data is separate from Windows: ~/Library/Application Support/APC40 Bridge macOS Preview.

- config.json and state.json: local settings and state; edits apply on the next test.
- venv: private MIDI dependencies.
- app.log, test.log, setup.log, bootstrap.log: errors, setup and message counts.
- last-test.json: latest test summary and up to 300 recent Hue/Colorize input events, retained in later exports.
- reports: fallback export location if Desktop access fails.

Exports include only known diagnostics, selected settings, versions, MIDI port names, counts and bounded Hue/Colorize events. Home directory paths are redacted. No compositions, screenshots, arbitrary files, SysEx payloads, serial numbers, environment dumps or full process lists are collected. Custom MIDI names may identify devices; review before sharing. There is no upload or telemetry.

## Build and validation

From the repository root:

    python macos/package_macos.py --output dist/APC40-Bridge-macOS-Preview.zip
    python -m unittest discover -s tests -v

The packager copies the unchanged shared engine into the app and preserves Unix executable permissions in the ZIP. Windows scripts and local runtime data are excluded. The macOS CI workflow checks shell syntax, AppleScript compilation and a CoreMIDI virtual-port roundtrip. Finder launch, real IAC routing and physical APC/Arena operation still need a Mac tester.

Sources: [Apple IAC setup](https://support.apple.com/en-ie/guide/audio-midi-setup/ams1013/mac), [Mido RtMidi](https://mido.readthedocs.io/en/stable/backends/rtmidi.html), [Resolume MIDI preferences](https://resolume.com/support/en/7/preferences).

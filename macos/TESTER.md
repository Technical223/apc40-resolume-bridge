# macOS Preview — Tester Instructions

Thank you for testing APC40 Bridge on a Mac. This is an experimental build, separate from the Windows version. Real APC40/Arena compatibility is still being tested.

## Before you start

You need Resolume Arena 7, an Akai APC40 mkII connected by USB, and Python 3.9 or newer. Python 3.11 or 3.12 from https://www.python.org/downloads/macos/ is recommended. Python is not included in the ZIP.

Use a disposable test composition: starting the bridge may send the physical fader and knob positions to Arena.

## Setup

1. Extract the ZIP into a permanent folder.
2. Open **APC40 Bridge macOS Preview.app**. The app is unsigned and unnotarized. If macOS blocks it, send Jakub the exact warning; keep system protections enabled. **Open Preview.command** is an optional debugging launcher that opens Terminal.
3. Choose **Prepare dependencies** and wait. This downloads MIDI libraries into a private environment without changing your system Python.
4. Choose **Open Audio MIDI Setup**. Open **Window → Show MIDI Studio → IAC Driver**, enable **Device is online**, and create two buses named **APC VIRT A** and **APC VIRT B**.
5. In **Arena → Preferences → MIDI**, enable **input only** for A and **output only** for B. Disable direct APC40 input/output in Arena. Leave clock disabled on both IAC buses and leave unrelated devices unchanged.
6. Use a compatible MIDI preset set to **Any device**, with Hue maximum **0.63871**. The example preset is inside the app: Finder → Show Package Contents → Contents/Resources/resolume. Copy it manually into ~/Documents/Resolume Arena/Shortcuts/MIDI if needed; do not overwrite your own preset.

No loopMIDI is needed on macOS. The preview uses the built-in IAC Driver.

## Run the test

Choose **Start 3-minute test**, then:

- Move all eight Hue knobs; compare pad colors with the corresponding Arena layers.
- Toggle Colorize using each top-row pad. Bypass should show white; enabling it should restore the remembered hue.
- Change Hue and Colorize with the mouse in Arena. Check whether the APC updates.
- Try faders, clip pads and utility buttons.
- Optionally unplug and reconnect USB; check whether the bridge recovers.

Write down what works, what fails, and the approximate time of each problem.

The test stops automatically after three minutes. **Stop test** ends it sooner. **Quit** stops the test and releases its ports. Afterward, confirm another MIDI app can use the APC.

## Send back the results

A file named **APC40-macOS-debug-…zip** should appear on your Desktop. **Export diagnostics** stops an active test and creates another ZIP, including the latest test summary.

If Desktop access fails, choose **Open logs folder** and look in **reports**.

Send Jakub:

- The diagnostic ZIP.
- Your Arena version.
- Which checklist items worked or failed.
- Any startup warning or error message.

Nothing is uploaded automatically. The ZIP contains versions, MIDI port names, errors, message counts and up to 300 recent Hue/Colorize events. It excludes compositions and screenshots, and home directory paths are redacted. Review custom MIDI port names before sharing.

If Python is missing, the launcher still attempts to create a small bootstrap diagnostic ZIP. If setup or MIDI connection fails, try **Export diagnostics**.

A completed timer alone does not mean MIDI worked. Zero connections means the bridge never opened all required ports together.

## After testing

The preview has no autostart and does not rewrite Arena preferences. If you want to use the APC directly again, stop the preview and manually re-enable physical APC40 input/output in Arena.

Full technical instructions are in README.md.

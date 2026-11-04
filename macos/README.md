# APC40 Bridge — macOS test build

A native macOS window using the system WebKit, with the same main navigation as Windows: **Overview, Controller Studio, Settings, Logs & diagnostics**, plus the shared browser visualizer and output editor. It uses the same MIDI engine, profile format and 145 calibrated controller hotspots. This is an unsigned, unnotarized test build, not a production macOS release.

## Start here

1. Download the [macOS test ZIP](https://github.com/Technical223/apc40-resolume-bridge/releases/tag/macos-v0.2.0-preview), extract it and open **APC40 Bridge macOS Preview.app**. The compiled package supports Apple Silicon and Intel Macs on macOS 11 or newer.
2. Install Python 3.12 from [python.org](https://www.python.org/downloads/macos/) if needed. Python is not bundled. No Homebrew or Xcode is required for the downloaded app. If macOS blocks the app, send the exact warning and keep system protections enabled.
3. Click **Install / repair**. Pinned MIDI libraries are downloaded into the app's private environment. No sudo or global Python changes are used.
4. Open **Audio MIDI Setup > Window > Show MIDI Studio > IAC Driver**. Enable Device is online and add **APC VIRT A** and **APC VIRT B**.
5. In Arena, enable input on A and output on B; keep clock off. For this Mac test, disable the physical APC input/output in Arena so the bridge owns the route. Leave unrelated devices unchanged. Windows uses its own documented routing.
6. Use a test composition, then click **Start bridge**. Starting initializes LEDs and may resend physical knob/fader positions. Keep MIDI learning off.

Closing the window keeps the app running; click its Dock icon to reopen it. **Quit APC40 Bridge** stops the bridge and releases ports. Sign-in autostart is not enabled by this test build.

## Controller Studio and visualizer

Click a control on the APC image, choose its behavior, color, source or reset action. Source values can be simulated without sending MIDI. Lighting changes save automatically and update a running bridge. Live feedback reads the bridge's output snapshot; it does not open a second physical MIDI connection. Controller profiles import/export in the same format as Windows.

The **Visualizer** button opens the same preview and output editor in your browser. Save your Advanced Output preset in Arena first. On a Mac, select **Capture window / screen** or a compatible virtual camera and grant macOS/browser capture permission. **SpoutCam is Windows-only**; direct Syphon capture is not implemented. See the [short visualizer guide](../docs/visualizer.md).

## Feedback and local diagnostics

**Nothing is uploaded automatically.** There is no telemetry or automatic feedback submission. **Export diagnostics** creates a ZIP locally and reveals it in Finder. Review it, then share it manually with your feedback if you choose. The three-minute diagnostic test also creates a local ZIP when it ends.

The ZIP includes installation/app errors, OS/CPU/Python and dependency versions, MIDI port names and route status, message counts, and at most 300 recent Hue/Colorize events. Home paths are redacted. It excludes compositions, media, screenshots, unrelated files, environment dumps, full process lists and SysEx payloads. Custom MIDI names can identify devices: review before sharing.

Please report your Mac model/architecture, macOS and Arena versions, what worked, what failed and roughly when. Attach the diagnostic ZIP manually. [Tester checklist](TESTER.md) · [Send feedback](https://github.com/Technical223/apc40-resolume-bridge/issues/new?template=macos-preview.yml).

Local data: `~/Library/Application Support/APC40 Bridge macOS Preview`. Reports fall back to its `reports` folder if Desktop access is unavailable.

## Validation and building

The Mac CI compiles an Apple Silicon + Intel native window, checks app permissions/plist, tests a CoreMIDI virtual-port roundtrip and diagnostic export, and runs portable regression tests. Finder launch, macOS permissions and real APC/Arena feedback still require testers.

Build on a Mac with Xcode command-line tools: `python macos/package_macos.py --require-native`. Source packaging on Windows omits the compiled native window and is not the downloadable tester app. `--legacy-menu` retains the earlier diagnostic menu for troubleshooting.

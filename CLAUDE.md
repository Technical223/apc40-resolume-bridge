# Project context for Claude and future contributors

Updated 2026-10-28. Repository: Technical223/apc40-resolume-bridge.
Original reviewed commit: `3855d08223d5c55350fa9edb5b9d6da87de64f6e`.

## User decisions

Keep the bridge simple and stable. Use existing MIDI feedback for Hue/Colorize changes made outside the APC; do not require a webserver, REST/OSC, or new dependencies. This request superseded an earlier decision to ignore top-row feedback.

English is the default for the app, messages, primary README, documentation, and diagrams. `README.cs.md` and `docs/*.cs.md` are optional Czech versions. Keep their instructions consistent with the actual English button labels. Maintain both README versions when changing the landing page. Preserve the original Czech batch filenames for compatibility alongside the new English entry points. Do not rename user clip names, MIDI ports, preset identifiers, configuration keys, or the existing `midi.xml.pred-bridge.bak` backup filename merely to translate them.

## MIDI feedback

`sync_resolume_feedback` is true in the supplied configuration, but defaults to false if the key is absent. Hue uses CCs 48–55, Colorize notes 32–39, channel 0 (Arena channel 1), and `hue_max: 0.63871`.

The existing Arena installation was tested with an external MIDI source: CC54=50 produced feedback CC54=49 (7-bit rounding), and returning to zero produced zero. Note38 toggling produced velocity 3 for bypass and 5 for an active effect, matching NamedValues in the JKB APC40 PRO preset. Never treat all nonzero velocities as active. The tested layer was restored to Hue 0 and active Colorize.

The feedback handler stores Hue and redraws the pad. Colorize feedback sets state idempotently, then draws white or the remembered hue. CC passthrough to the APC remains; feedback is not sent back into Arena. Unknown velocities and Note Off are ignored. Physical APC controls still work without feedback.

Limitations: 7-bit resolution, shortcut range and routing, no full-value API read, active polling, or saturation/brightness tracking. Colors outside the mapped range are not guaranteed. Composition synchronization depends on matching mappings and actual feedback from Arena. Direct mouse input was not conclusively tested in the original live validation; external MIDI and real Arena feedback were verified.

## Reliability fixes

1. The Bridge constructor records each opened port and closes partially initialized ports if any later open or initialization fails, then raises the original error.
2. Exceptions in `on_apc`, `on_resolume`, or blinking set the `failed` event. `alive()` returns false even if device names are still enumerated. The main loop closes the failed bridge and reconnects.
3. Stop and restart share `stop_bridge.ps1`. It verifies Python/Pythonw, the exact absolute script path as the first argument, `--watch`/`--run`, and process creation time. Termination holds a handle to the exact process instance rather than looking up a recycled PID. Unrelated processes remain alive; unverifiable identity safely prevents restart.
4. Documentation covers optional feedback and the original APC-only mode.

## Windows control panel

`bridge/ui/BridgeManager.cs` implements the native WinForms dashboard using .NET Framework. `build-ui.ps1` uses the system compiler. `APC40 Bridge.vbs` bootstraps source ZIPs; distribution ZIPs include the EXE. `START.bat` opens the dashboard. Backend actions live in `manage.ps1` and `runtime.ps1`; see [technical notes](docs/windows-app.md).

Normal start is idempotent and does not reinstall anything. `setup.ps1 -NoPopup -PrepareOnly` prepares dependencies and settings without restarting the watcher, with explicit instructions for missing virtual ports or Arena preferences. The status check only enumerates ports and reads MIDI preferences; it does not claim ports or prove MIDI message delivery.

Settings preserve unknown configuration keys and save atomically with a backup. Closing the dashboard leaves the watcher running. Only one dashboard instance is allowed per installation. Mutating actions use a path-specific mutex.

Autostart targets `APC40 Bridge.exe --autostart`, which starts the watcher without a dashboard or setup. Preserve existing configuration, state, runtime path, and user shortcuts when updating. Restarting the watcher can resend physical fader/knob positions into the composition.

MIDI restore requires Arena closed and a real backup before stopping the watcher or disabling autostart. No backup means no destructive change.

## Validation

- `py -3 -m unittest discover -s tests -v`: 27 tests covering port initialization failures, errors in both directions and blinking, reconnect behavior, normal passthrough, all eight Hue/pad mappings, feedback state, disabled synchronization, channels/velocities, no feedback loop, read-only port/preferences status, and Windows management with a fake watcher.
- `py -3 tests/test_stop_process.py`: real disposable child processes, unrelated Python and other run modes preserved, malformed/stale PID handling, correct child termination, paths with spaces/apostrophes, Windows PowerShell syntax.
- Tests do not require actual MIDI hardware or change Arena settings. The idempotent management test is skipped unless loopMIDI is already running; tests never launch it.
- Original live preparation succeeded without changing the watcher PID. The dashboard, settings, and logs were visually inspected. Actual USB unplug/replug and pristine Windows installation remain unverified.
- `.github/workflows/windows.yml` runs Windows tests and builds the package. Read CI results separately from local validation.
- English UI update: system compiler build succeeded; 26 tests passed and one loopMIDI-dependent test was skipped. Safe-process-stop checks passed. The Python MIDI engine and default configuration were not changed.

## Deployment

The local installation is `C:\Users\jakub\AppData\Local\Programs\APC40 Bridge`, with backend files directly inside it rather than a Git checkout. The previous Documents installation was archived under its `backups` folder. English UI update backup: `backups/before-english-ui-20261028`. Preserve `config.json`, `state.json`, `bridge.pid`, `runtime.json`, and existing log history during translation updates; no watcher restart is needed for UI text changes.

Manual reliability updates must include `stop_bridge.ps1`, `apc_bridge.py`, `setup.ps1`, and the stop launcher. Feedback updates require merging the synchronization and velocity keys into existing configuration without overwriting custom ports or mappings. A running Python process keeps its old code until restarted. This file alone does not guarantee any branch has been merged.

## README media

`docs/media/app-showcase.gif` is an animated tour of real dashboard, settings, and log screenshots, not an installation recording. Matching stills are `docs/img/app-dashboard.png`, `app-settings.png`, and `app-logs.png`. Capture actual app windows without modifying user configuration or watcher state; publish no private paths from logs. Refresh these screenshots when changing the interface language.

The synchronized real demo uses `docs/media/controller-screen-sync.gif` and `.mp4`. Camera source: IMG_0533.MP4 (768×550, about 29.997 fps). Screen source: Záznam 2026-10-26 232815.mp4 (2560×1380, 30 fps). Camera starts at 0 s, screen at 72.300 s, aligned visually using Hue changes near camera 3.1 / screen 75.4 s and later transitions. This is approximate visual synchronization, not a MIDI latency measurement.

Output: 36 s, 1920×720, H.264/yuv420p, 30 fps, silent, faststart. Three panels: full camera at left; Colorize crop x=1340, y=680, w=426, h=390 in the middle; Composition Monitor image crop x=2138, y=906, w=422, h=238 on the right. The composition black background is preserved. GIF: 1200 px, 10 fps, looped. Static endings and large source files are excluded. Original demo.gif/demo.mp4 remain in a collapsible section. No bridge behavior changes were made for media editing.

## macOS preview (2026-10-28)

The user requested a separate Mac tester build with shareable diagnostics. Sources are in macos/, packaged independently by macos/package_macos.py as an unsigned .app ZIP. Windows source, setup and installed runtime are not changed for this preview. The shared bridge/apc_bridge.py is copied unchanged into the Mac bundle. mac_bridge.py imports it as a separate module, overrides its state path and port resolver only in that process, and uses mido RtMidi/MACOSX_CORE with two manually configured IAC buses.

The native osascript menu offers preparation, Audio MIDI Setup, settings, a bounded three-minute test, stop, export and logs. Python 3.9+ is external; MIDI dependencies are pinned and installed from wheels into a private venv. No sudo, global pip, login items, automatic Arena preferences edits or security changes. Missing Python has a bootstrap-only report. The preview intentionally has no automatic Arena watch/autostart or full WinForms-equivalent dashboard yet.

Runtime data is under ~/Library/Application Support/APC40 Bridge macOS Preview. Tests can run without Arena; process presence is diagnostic only. The worker owns its ports and OS file lock, handles SIGTERM/SIGINT, closes on expiry/stop and exports a Desktop ZIP with a reports fallback. Stop uses only the owned child process, never a PID file. Port matches must be unique; missing names never fall back to default ports.

Reports use a file whitelist, redact home paths, retain the last test summary and cap recent Hue/Colorize events at 300. No upload, compositions, screenshots, environment dumps, SysEx bodies or full process lists. A completed timer is not a passing device test: inspect connections and traffic. Real Mac hardware validation remains pending. The macOS package, filenames, tester instructions and all future macOS-specific material must be English-only, as explicitly requested by the user. README.md and TESTER.md are included in the ZIP.

New portable tests cover isolation, ambiguous/missing ports, config routing, missing dependencies, bounded events, diagnostic export and cleanup, plus ZIP permissions/contents. .github/workflows/macos.yml adds macOS-native shell/AppleScript syntax, CoreMIDI virtual-port loopback and no-hardware report generation. CI outcomes must be checked separately from local Windows tests and cannot establish physical APC/Arena compatibility.

macOS validation: GitHub Actions run https://github.com/Technical223/apc40-resolume-bridge/actions/runs/40779973125 succeeded on source a05d943: pinned wheel installation, portable tests, AppleScript compilation, native CoreMIDI virtual-port roundtrip, no-hardware test diagnostic generation, packaging, executable ZIP permissions and plist validation. A subsequent small change guarantees a parent-side diagnostic export after Stop and adds CI timeouts; physical hardware and Finder launch remain untested. Local Windows run: 35 tests, 34 passed, one existing loopMIDI-dependent management test skipped.

## Speed-ring animation (2026-10-29)

## Animated group-speed rings

With `speed_ring_animation: true`, device knobs 5–8 show a single dot bouncing across their 15 ring LEDs (first → last → first). Faster group speed means a faster loop. After manual takeover, CCs 20–23 on MIDI channel 1 (zero-based 0) pass unchanged to Arena; takeover/settling messages are consumed locally. The supplied configuration enables this feature; a missing key or `false` preserves the previous behavior.

Arena must send the matching speed CC feedback to **APC VIRT B** (IAC bus B on macOS). With `sync_resolume_feedback: true`, mouse edits update the stored speed and animation. Incoming ring positions/styles are suppressed for animated knobs, preventing a fight with the animator. With sync disabled, Arena speed feedback is ignored for these rings; physical knob movement still changes their speed.

| Setting | Default | Meaning |
|---|---|---|
| `speed_ring_animation` | true in supplied config; false if absent | Enable animated rings |
| `speed_ring_ccs` | [20, 21, 22, 23] | Device-knob CCs; configurable subset of 16–23 |
| `speed_ring_channel` | 0 | Zero-based MIDI channel |
| `speed_ring_slowest_seconds` | 2.0 | Full out-and-back period at CC value 0 |
| `speed_ring_fastest_seconds` | 0.25 | Full out-and-back period at CC value 127 |
| `speed_ring_update_hz` | 120 | Scheduler rate; MIDI is sent only when the LED index changes |

Period interpolates linearly between the configured endpoints. The animation is a relative speed indicator, not a beat clock or exact display of a percentage. The JKB preset maps these knobs to group speeds of approximately 25–100%. At the fastest default setting, traffic is at most about 112 CCs/s per ring (448 CCs/s total). A low update rate can skip intermediate LEDs.

Last speed values are stored in `state.json` under `speed`, keyed by channel and CC (e.g. `0:20`). Old state files remain compatible. Until movement or feedback arrives, a missing value starts at the slowest period. Changing speed preserves animation phase. The animation thread stops and joins before ports close; send failures mark the connection unhealthy and trigger normal reconnection.

Protocol: [Akai APC40 mkII Communications Protocol v1.2](https://cdn.inmusicbrands.com/akai/attachments/apc40II/APC40Mk2_Communications_Protocol_v1.2.pdf), pages 24–27. Device ring-style CC = knob CC + 8 (28–31 for knobs 5–8); value 1 selects Single. Fifteen values are selected from single-LED ranges, avoiding the intervening two-LED patterns. Mode 66 (Alternate Ableton) is required so the host owns the LEDs.

Validation: hardware-free tests cover periods, protocol messages, passthrough, mouse-style feedback, sync disabled, old configuration/state, persistence, thread shutdown and animation send failures. Real LED appearance and direct mouse changes in Arena have **not yet been verified on hardware**. No API polling is added: mouse changes require actual matching Arena MIDI feedback and are subject to its mapping/range and 7-bit resolution.

Restart the bridge after changing configuration. To revert, set `speed_ring_animation: false` and restart.

The shared engine also reaches macOS when its preview is rebuilt. Existing release v1.2.0 assets are not replaced. Do not claim physical LED or mouse validation without a real Arena/APC test. Preserve custom configuration on updates.

## Speed-ring motion correction (2026-10-29)

The user clarified the desired motion is bounce/ping-pong, not a wraparound loop. The 15-LED sequence is 0..14..1, repeated; reverse direction at each end. The configured period is a full out-and-back cycle. Keep speed feedback unchanged. The regression test verifies every LED and both endpoints; real LED appearance still requires user confirmation.

## Hardware regression: animated rings vs encoder values

User reports speed values jumping like relative input while rotating the animated device knobs. Akai documents device CCs as absolute. Suspected cause is shared encoder/ring value state, not yet independently captured. Immediately disabled animation in the installed configuration and restarted the live bridge. Repository default is now false. Keep animation experimental/disabled; do not claim the issue fixed or re-enable it without hardware validation. The original requirement for unchanged absolute passthrough may be incompatible with independent ring animation on this firmware. Normal passthrough and Arena feedback remain active with the feature off.

## Idle-only speed-ring animation and manual takeover

In **Settings → Speed rings**, enable **Animate speed rings while idle (experimental)**, save and restart the bridge. The default remains off.

The ring bounces only while its knob is idle. The first physical movement pauses animation and re-anchors the encoder to the stored actual speed; that first message is **not sent to Arena**. Messages during the short settling window are also ignored. Subsequent manual values pass unchanged. Animation stays paused until one second after the last movement, then resumes. This is per knob: other rings can continue animating.

Mouse feedback updates stored speed. While manual control is active, normal absolute feedback is also sent to the knob to keep its baseline aligned; while animating, feedback does not overwrite the dot. Keep sync_resolume_feedback enabled for mouse changes.

Advanced configuration: speed_ring_idle_seconds (default 1.0, range 0.2–10) and speed_ring_settle_seconds (default 0.05, range 0.02–0.5, no longer than idle).

Tradeoff: the first small turn after idle takes control rather than changing speed. The brief settling period may discard a little further movement. This avoids blindly forwarding an absolute value derived from the animated ring. It is a software workaround, not an independently addressable LED channel. Queuing and encoder firmware behavior still require real-hardware validation; do not claim the interference fixed solely from simulated tests. Leave the option off if jumps persist.

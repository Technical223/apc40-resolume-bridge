# APC40 mkII ⇄ Resolume Arena bridge

**English** | [Česky](README.cs.md)

![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D6)
![Resolume](https://img.shields.io/badge/Resolume%20Arena-7.x-8A2BE2)
![License](https://img.shields.io/badge/license-MIT-green)

Color pads beneath the Hue knobs, buttons you can see in the dark, and **one window for setup, launch, and management**.

- Each pad shows its knob’s hue; press it to toggle Colorize.
- Optional MIDI feedback follows changes from Arena and other controllers.
- The bridge activates with Arena and releases the controller when Arena closes.
- The app shows controller, Arena, MIDI port, and setup status. No terminal window needed.

<p align="center">
  <a href="docs/media/app-showcase.gif"><img src="docs/media/app-showcase.gif" width="1000" alt="APC40 Bridge animated tour: connection status, settings, and live logs"></a>
</p>
<p align="center"><sub>Actual Windows app screenshots · status, settings, and logs in one window</sub></p>

## App screenshots

<table>
  <tr>
    <td width="33%" align="center"><a href="docs/img/app-dashboard.png"><img src="docs/img/app-dashboard.png" alt="APC40 Bridge dashboard with controller, Arena, port, and setup status"></a></td>
    <td width="33%" align="center"><a href="docs/img/app-settings.png"><img src="docs/img/app-settings.png" alt="MIDI port, Hue, feedback, and lighting settings"></a></td>
    <td width="33%" align="center"><a href="docs/img/app-logs.png"><img src="docs/img/app-logs.png" alt="APC40 Bridge log viewer"></a></td>
  </tr>
  <tr>
    <td align="center"><b>Connection status</b></td>
    <td align="center"><b>Settings</b></td>
    <td align="center"><b>Live logs</b></td>
  </tr>
</table>

Click a screenshot to view it at full size.

## macOS preview — testers wanted

A separate [experimental macOS build](https://github.com/Technical223/apc40-resolume-bridge/tree/main/macos) uses native CoreMIDI/IAC buses, a small dialog-based control panel, a three-minute test and a local diagnostic ZIP. It is unsigned and requires Python plus manual MIDI setup. Real APC/Arena testing on a Mac is still needed; this is not a production release. The Windows app remains separate.

## Get started — Windows

1. Extract **APC40-Bridge-Windows.zip** into the folder where you want to keep it. Close Arena before the initial setup.
2. Open **APC40 Bridge.exe**.
3. Click **Prepare and start**. Setup finds or installs the required components.
4. If virtual MIDI ports are missing, click **Open loopMIDI**, create **APC VIRT A** and **APC VIRT B**, then run setup again.
5. In Arena, set the MIDI preset to **Any device** and Hue **Range Max to 0.63871** (displayed rounded to 0.64).

For everyday use, open the app and click **Start bridge**. **Start automatically when signing in to Windows** runs the bridge without opening the dashboard.

The app interface, setup messages, and primary documentation are in English.

**Using GitHub’s source ZIP:** open **APC40 Bridge.vbs** in the `bridge` folder. It builds the app from the included sources and opens the same dashboard. Building the dashboard uses Windows’ .NET Framework and requires no Python or additional developer tools; bridge dependencies are handled during setup.

## Everything in one place

| Control | What it does |
|---|---|
| Start bridge | Starts watching for Arena; repeated launches do not create duplicate processes |
| Stop / Restart | Safely releases the controller or reloads settings |
| Install / repair | Prepares dependencies and MIDI settings without unnecessarily restarting a running bridge |
| Settings | Ports, Hue, feedback, and lighting; preserves other values and saves a backup |
| View logs | Runtime, setup, and management logs inside the app |
| Desktop shortcut | Adds an app shortcut to your desktop |
| Restore Arena MIDI | With Arena closed, restores its MIDI settings backup, stops the bridge, and disables autostart |

Closing the dashboard **does not stop** the bridge: it runs independently in the background. Restarting may resend the physical fader and knob positions to Arena.

## Bridge in action

<p align="center">
  <a href="docs/media/controller-screen-sync.mp4"><img src="docs/media/controller-screen-sync.gif" width="1200" alt="Three synchronized views side by side: APC40 mkII, Colorize controls, and Composition Monitor"></a>
</p>
<p align="center"><sub>The same moment from three perspectives · APC40 mkII + Colorize + Composition Monitor · <a href="docs/media/controller-screen-sync.mp4">Watch the full-quality 36-second video (MP4)</a></sub></p>

The recordings are aligned using Hue changes. The physical controller is on the left, the Colorize panel and Hue value in the middle, and the Composition Monitor on the right. The silent video demonstrates hue changes and Colorize toggling.

<details>
<summary>Original short controller demo</summary>

<p align="center">
  <a href="docs/media/demo.mp4"><img src="docs/media/demo.gif" width="340" alt="Physical APC40 demo: the Hue knob changes the pad color and Resolume output"></a>
</p>
<p align="center"><sub><a href="docs/media/demo.mp4">Watch the original APC40 demo at full quality</a></sub></p>

</details>

## Speed indication and reset

Optional blinking buttons beneath device knobs 5–8 indicate group speed. Press a button to reset its group to 1x (100% with the supplied mapping). Knobs retain normal absolute feedback, including mouse changes. This replaces the buttons’ original preset actions while enabled. [Configuration and validation](docs/navod.md#speed-buttons-blink-rate-and-1x-reset). Legacy ring animation remains experimental and is disabled by the new Settings option.

## LED feedback

Set `sync_resolume_feedback: true` in `config.json` to enable MIDI feedback. Hue CCs 48–55 update the hue; notes 32–39 update the Colorize state. Arena must send these messages to `APC VIRT B`. The current preset uses velocity **5 = effect active, 3 = bypass**.

Feedback uses 7-bit MIDI values within the preset’s mapped range, rather than full-precision API readings. Correct hues outside `0–hue_max` are not guaranteed. Disable it under **Settings → Feedback**. No webserver or extra library is required.

👉 **[Detailed setup and troubleshooting guide](docs/navod.md)**

For development: [project context and validation](CLAUDE.md), [app technical notes](docs/windows-app.md).

Legacy batch files remain available for compatibility; `START.bat` now opens the dashboard.

MIT · [Technical223](https://github.com/Technical223)

**Known hardware issue (2026-10-29):** Animated ring CC values appear to interfere with the absolute device-knob values on the user’s APC40 mkII, causing speed jumps during rotation. The precise firmware interaction has not been independently measured. Keep `speed_ring_animation: false` for normal control and standard Arena feedback. Do not treat unchanged-message unit tests as proof that host-driven ring animation is independent of encoder state.

### Speed-button range correction

The supplied Arena shortcut range is 1–10 (normalized parameter bounds approximately 0.2502–1); these normalized bounds are not speed multipliers. MIDI CC 0 selects the lower bound (1x), and CC 127 the upper bound (10x). Button reset sends CC 0 to both Arena and the encoder, restarting the pulse phase. Pulse rate increases from 1 to 3 Hz across the full MIDI range (speed 1x–10x). The display rate is compressed by speed_button_max_blink_hz, default 3; it is an indication of speed, not a 10 Hz strobe. Intermediate pulse rates are a linear indication of the shortcut position, not an exact measurement of Arena’s nonlinear speed curve. Physical knob input and mouse MIDI feedback remain unchanged. Replaces earlier descriptions of CC-127 reset and the 0.25–1 pulse range.

### Arena reset and MIDI routing

If a speed-reset button updates the APC ring/pulse but the Arena speed number stays unchanged, check that Arena is receiving APC VIRT A. Reopen that MIDI Input (off/on) in Arena preferences if a virtual port was recreated after Arena started. Disable direct APC40 MIDI Input and Output so all traffic passes through the bridge. The speed shortcuts must use Any Device or APC VIRT A for input and All Devices or APC VIRT B for output. Keep MIDI learning off during bridge restarts, which can cause the controller to resend controls. A CC reset changes the actual parameter and its displayed number together when the virtual input is connected.

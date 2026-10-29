# Setup and troubleshooting guide

[English](navod.md) | [Česky](navod.cs.md) · [Home](../README.md)

![How it works](img/architecture.svg)

![What the bridge does on the APC40](img/apc-overview.svg)

## Contents

1. [Requirements](#1-requirements)
2. [Installation and launch](#2-installation-and-launch)
3. [Resolume setup](#3-resolume-setup)
4. [Everyday use](#4-everyday-use)
5. [Bridge configuration](#5-bridge-configuration-configjson)
6. [Troubleshooting](#6-troubleshooting)
7. [Fallback mode and removal](#7-fallback-mode-and-removal)

## 1. Requirements

| Component | Version | Notes |
|---|---|---|
| Windows | 10 / 11 | 64-bit |
| Resolume Arena | 7.x | Tested with 7.25 |
| Akai APC40 mkII | — | Connected via USB |
| Python | 3.9+ | Setup installs 3.12 if missing |
| [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html) | — | Setup attempts installation via winget; see the publisher’s license for your use case |
| Internet | — | Needed during initial setup |

## 2. Installation and launch

1. Extract the Windows package into a permanent folder. Close Arena before initial setup.
2. Open **APC40 Bridge.exe**. If using the source ZIP, open **bridge/APC40 Bridge.vbs** to build and open the same dashboard.
3. Click **Prepare and start**. Setup finds or installs Python, MIDI libraries, and loopMIDI.
4. If virtual ports are missing, click **Open loopMIDI**, add **APC VIRT A** and **APC VIRT B**, then repeat setup. Keep loopMIDI autostart enabled.
5. Setup updates Arena MIDI inputs/outputs, saves a backup, and copies the example preset if not already installed.
6. In Arena, use **Any device** for the preset and match the Hue range below.

![loopMIDI ports](img/loopmidi.svg)

| Port | Direction |
|---|---|
| APC VIRT A | Bridge → Resolume |
| APC VIRT B | Resolume → bridge |

For normal use, click **Start bridge**. Repeated launches do not create another process. **Start automatically when signing in to Windows** launches the watcher without opening the dashboard or running setup again. After moving the installation folder, turn this option off and on to update its shortcut.

**Install / repair** can be used again; preparation alone does not restart a running bridge. If Arena is running and its MIDI settings need changing, setup asks you to close Arena. Restarting the bridge may send the physical fader and knob positions to the composition.

Setup backs up the original MIDI settings as `midi.xml.pred-bridge.bak`. With Arena closed, **Restore Arena MIDI** restores that backup, stops the bridge, and disables its autostart. Open **View logs** for runtime and installation logs.

## 3. Resolume setup

![Resolume MIDI settings](img/resolume-midi.svg)

![Resolume MIDI preset](img/resolume-preset.svg)

- **The MIDI preset must use Any device.** A preset bound to APC40 mkII does not respond through the virtual port, because Resolume now receives input from `APC VIRT A`.
- Setup copies **APC40 BRIDGE EXAMPLE** into `Documents\Resolume Arena\Shortcuts\MIDI`. See the expected [composition layout](layout.md).
- **Custom mapping:** relearn shortcuts in *Shortcuts → Edit MIDI*. Input from `APC VIRT A` is expected.
- **Top grid row, notes 32–39:** toggles layer Colorize. The bridge owns the pad colors and can update them from optional MIDI feedback.
- **Track knobs, CCs 48–55:** control Colorize Hue over 0–0.63871 (red → green → blue).
- **Save the composition.** It remembers the selected MIDI preset.

### Hue range: match the knob and pad

![Hue range](img/hue-range.svg)

Colorize Hue wraps around: 0 is red and 1 is **red again**. Mapping a knob to the full range gives the same color at both ends, with blue somewhere in the middle. The example preset therefore limits the knobs to **0–0.63871**, ending at blue.

The bridge derives pad colors from MIDI values rather than reading the full effect value through an API. **The upper limit in Resolume must match `hue_max` in `config.json`**, otherwise the pad and layer colors can differ.

![Hue knob range in Resolume](img/resolume-hue-range.png)

1. Open *Shortcuts → Edit MIDI*.
2. Click the mapped layer Colorize **Hue** parameter (for example, `1/CC48`).
3. Select the `… Video Effects Colorize Effect Color Hue` entry in **Shortcuts**. Check **Input: Any device**.
4. Under **Range**, set the right handle to **0.64** (rounded display; the example preset stores exactly 0.63871). Leave the left handle at 0.
5. Repeat for all eight Hue knobs, then save the composition.

The difference between 0.64 and 0.63871 is less than half a degree of hue and does not change the pad palette color.

| Desired range | Resolume maximum | `hue_max` |
|---|---|---|
| **A (default):** red → blue, distinct endpoints | `0.63871` | `0.63871` |
| **B:** full circle, including purple and pink | `1` | `1.0` |
| Custom limit | Your value | The same value |

Click **Restart** after changing bridge settings. Mode B also shows purple and pink. Both modes select the closest color in the APC `palette`.

## 4. Everyday use

| Situation | Action |
|---|---|
| Autostart enabled | Open Arena; the APC lights up within a few seconds |
| Autostart disabled | Open the dashboard → Start bridge, then Arena |
| Use the APC in another program | Close Arena to release the APC, or click Stop |
| Something is wrong | View logs; if needed, Install / repair |

**When the bridge starts**, the APC sends all fader and knob positions, and Resolume applies them immediately. A fader physically at the bottom sets its layer opacity to zero.

### LED meanings

| Button | Steady | Blinking |
|---|---|---|
| Top grid row | Hue of the knob above it; white means Colorize is off | — |
| Single-color utility buttons | Function available | Function active: flash held, effect enabled, clip playing, etc. |
| Mute buttons (`lit_invert`) | Normal state | Muted |
| Clip grid | Determined by your Resolume preset | — |

### Top-row feedback

`sync_resolume_feedback: true` enables simple synchronization using existing MIDI feedback. Arena must send Hue and Colorize feedback to `APC VIRT B`. The bridge receives CCs 48–55 on channel 0 (channel 1 in Arena), stores Hue, and updates the pad color. Mouse edits and other controllers can update the same indicator when Arena sends the corresponding messages. `hue_max` must still match the preset range.

Do not interpret Colorize as `velocity > 0`: this preset sends **5 for an active effect** and **3 for bypass**. These values are configured by `color_on_feedback_velocity` and `color_off_feedback_velocity`. White indicates bypass. Re-enabling Colorize restores the remembered hue instead of the plain red from the preset. Unexpected velocities and Note Off are ignored. These feedback messages are not returned to Arena, preventing a MIDI loop.

Limitations: MIDI has 128 steps, may round values, and is limited by shortcut range and routing. This is not a direct REST/OSC read of the full effect value; there is no active polling. Only messages actually sent by Arena update the bridge. Colors outside the mapped range may differ. Composition changes synchronize only if the new composition uses matching mappings and sends feedback. Saturation, brightness, and opacity are not tracked; the pad still displays a fully saturated hue.

For another preset, match the CCs/notes, channel, range, and Colorize feedback values. Set `sync_resolume_feedback: false` and restart to return to APC-only indication. In this mode, physical knobs/pads alone determine the top row; mouse edits do not update it.

### MIDI error recovery

If a port fails to open, the bridge closes previously opened ports and retries. Send errors in either direction or in the blink thread mark the connection as failed; the main loop closes it and reconnects, even if the port names remain listed. Actual USB disconnect behavior should still be checked with the specific device and driver.

Stop and restart share `stop_bridge.ps1`. Before terminating a process, it checks Python, the exact script path, run mode, and process creation time. A stale `bridge.pid` alone cannot terminate an unrelated program.

## 5. Bridge configuration (`config.json`)

| Key | Default | Meaning |
|---|---|---|
| `to_resolume_port` / `from_resolume_port` | `APC VIRT A` / `APC VIRT B` | loopMIDI port names |
| `apc_port_match` | `APC40` | Substring of the physical APC port name in Windows |
| `arena_process` | `Arena.exe` | Process watched by the bridge |
| `knob_ccs` | 48–55 | Track knobs supplying Hue |
| `color_notes` | 32–39 | Pads displaying Hue |
| `hue_max` | 0.63871 | Upper Hue limit; **must match the Resolume knob maximum**; `1.0` = full circle ([Hue range](#hue-range-match-the-knob-and-pad)) |
| `palette` | 14 colors | Hue angle → APC palette number (red → blue → purple → pink) |
| `white_velocity` | 3 | Pad color with Colorize off |
| `sync_resolume_feedback` | `true` in the supplied config, otherwise `false` | Follow Arena Hue/Colorize feedback |
| `color_on_feedback_velocity` / `color_off_feedback_velocity` | 5 / 3 | Feedback values for active Colorize / bypass in this preset |
| `always_lit` | `true` | Keep single-color utility buttons lit |
| `lit_track_notes` / `lit_global_notes` | See file | Buttons to illuminate |
| `lit_invert` | Mute buttons | Steady = normal; blinking = muted |
| `blink_hz` | 3 | Blink rate |
| `apc_mode` | 66 | APC mode (0x42 Alternate Ableton); try 65 if controls do not respond |

Click **Restart** after changing settings.

## 6. Troubleshooting

| Symptom | Cause | Solution |
|---|---|---|
| Setup reports missing ports | Missing or differently named loopMIDI ports | Create exactly `APC VIRT A` and `APC VIRT B` |
| APC stays dark | Bridge or Arena is not running | Check `bridge.log`, click Start bridge, open Arena |
| Log says “Waiting for ports” | APC disconnected or held by another program | Connect USB; disable physical APC40 mkII in Resolume; close Ableton or other MIDI apps |
| Knobs/pads do nothing in Resolume | Preset bound to APC40 mkII | Use Any device (section 3) |
| Resolume cannot see APC VIRT A | loopMIDI is not running | Start loopMIDI and enable its autostart |
| Setup says Arena is running | MIDI preferences cannot be changed while Arena is open | Close Arena, then use Install / repair again |
| Another controller triggers the same actions | Any device preset hears all enabled inputs | Disable that controller in *Preferences → MIDI* if unwanted |
| Pad and layer colors differ | Missing feedback, disabled sync, or mismatched range | Check `sync_resolume_feedback`, shortcut output to APC VIRT B, and matching `hue_max` ([Hue range](#hue-range-match-the-knob-and-pad)) |
| Knob turns red again at its far end | Knob mapped to the full 0–1 range | Set Resolume maximum to 0.63871, or use `hue_max: 1.0` for the full circle |

Logs are available inside the app: **View logs → Bridge runtime / Setup / App management**.

## 7. Fallback mode and removal

**Fallback mode during a show:**

1. Click **Stop** or run `STOP.bat`.
2. In Arena → *Preferences → MIDI*, enable physical **APC40 mkII** input and output.
3. An Any device preset keeps working directly, without the bridge color pads and utility-button lighting.

**Removal:**

1. Disable autostart in the app and click **Stop**.
2. With Arena closed, use **Restore Arena MIDI** to restore the original MIDI settings.
3. Delete the installation folder and any desktop/Start Menu shortcuts you created. Uninstall Python and loopMIDI through Windows if no longer needed.

## Animated group-speed rings

With `speed_ring_animation: true`, device knobs 5–8 show a single dot bouncing across their 15 ring LEDs (first → last → first). Faster group speed means a faster loop. After manual takeover, CCs 20–23 on MIDI channel 1 (zero-based 0) pass unchanged to Arena; takeover/settling messages are consumed locally. The supplied configuration disables this experimental feature; a missing key or `false` preserves the previous behavior.

Arena must send the matching speed CC feedback to **APC VIRT B** (IAC bus B on macOS). With `sync_resolume_feedback: true`, mouse edits update the stored speed and animation. Incoming ring positions/styles are suppressed for animated knobs, preventing a fight with the animator. With sync disabled, Arena speed feedback is ignored for these rings; physical knob movement still changes their speed.

| Setting | Default | Meaning |
|---|---|---|
| `speed_ring_animation` | false | Experimental animated rings; known encoder interference |
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

**Known hardware issue (2026-10-29):** Animated ring CC values appear to interfere with the absolute device-knob values on the user’s APC40 mkII, causing speed jumps during rotation. The precise firmware interaction has not been independently measured. Keep `speed_ring_animation: false` for normal control and standard Arena feedback. Do not treat unchanged-message unit tests as proof that host-driven ring animation is independent of encoder state.

## Idle-only speed-ring animation and manual takeover

In **Settings → Speed rings**, enable **Animate speed rings while idle (experimental)**, save and restart the bridge. The default remains off.

The ring bounces only while its knob is idle. The first physical movement pauses animation and re-anchors the encoder to the stored actual speed; that first message is **not sent to Arena**. Messages during the short settling window are also ignored. Subsequent manual values pass unchanged. Animation stays paused until one second after the last movement, then resumes. This is per knob: other rings can continue animating.

Mouse feedback updates stored speed. While manual control is active, normal absolute feedback is also sent to the knob to keep its baseline aligned; while animating, feedback does not overwrite the dot. Keep sync_resolume_feedback enabled for mouse changes.

Advanced configuration: speed_ring_idle_seconds (default 1.0, range 0.2–10) and speed_ring_settle_seconds (default 0.05, range 0.02–0.5, no longer than idle).

Tradeoff: the first small turn after idle takes control rather than changing speed. The brief settling period may discard a little further movement. This avoids blindly forwarding an absolute value derived from the animated ring. It is a software workaround, not an independently addressable LED channel. Queuing and encoder firmware behavior still require real-hardware validation; do not claim the interference fixed solely from simulated tests. Leave the option off if jumps persist.

## Speed buttons: blink rate and 1x reset

The preferred speed indication is now **Settings → Speed buttons → Blink speed buttons; press to reset to 1x**. Save and restart to apply. The repository default is off for compatibility; enabling this option replaces the original actions of the four device buttons beneath knobs 5–8.

This mode uses notes **58, 59, 60, 61** on MIDI channel 1 (zero-based 0), paired with speed CCs **20, 21, 22, 23**. The physical controller protocol identifies these as Device Left, Device Right, Bank Left and Bank Right (the upper of the two button rows). These buttons retain their original preset actions only when the speed-button option is off. Both press and release are consumed locally, so the old preset action does not reach Arena. Turning the option off restores the original mapping.

Buttons blink on/off at a rate proportional to the mapped group-speed multiplier. These are single-color on/off LEDs; velocity does not provide smooth brightness fading. Default mapping is approximately 0.25x–1x: one cycle takes 2 seconds at minimum speed and 0.5 seconds at 1x. LED messages are sent only at on/off transitions and never to Arena.

Knob rings use normal absolute feedback again. The first knob movement passes to Arena unchanged; there is no takeover gesture or animation write to an encoder. Mouse feedback updates stored speed and the pulse rate when sync_resolume_feedback is enabled, and passes through to the knob normally.

Pressing a button sends its paired speed CC with value **127** to Arena and the APC. For the current 25–100% preset this resets speed to **1x (100%)**, restores the correct encoder/ring position and restarts that button pulse at the beginning. It does not reset clip playback. Custom preset ranges may require a different speed_button_reset_value.

Configuration: speed_button_pulse (false if absent), speed_button_notes ([58,59,60,61]), speed_button_base_seconds (0.5), speed_button_min_multiplier (0.25), speed_button_max_multiplier (1.0), speed_button_reset_value (127). The existing speed_ring_ccs/channel define the paired knob mapping. Legacy ring animation and button pulsing cannot run together; saving Settings disables legacy ring animation.

Validation: tests cover LED-only animation traffic, unchanged first knob movement, normal mouse-style feedback, reset on press only, consumption of releases and duplicate presses, ownership of button LEDs against old preset feedback/general blinking, compatibility when disabled, and configuration conflicts. Physical button timing and real mouse edits still require user confirmation. No Arena preset files are modified.

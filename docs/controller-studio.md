# Controller Studio

[Home](../README.md) · [Setup guide](navod.md)

Controller Studio is the Windows app's visual editor for bridge lighting and button resets. It has an offline simulation and a read-only live view. Editing and the preview slider never open MIDI ports or send MIDI messages.

## Build a lighting profile

1. Open **APC40 Bridge → Controller Studio**.
2. Click a grid pad or utility button in the controller diagram.
3. Choose its **Lighting** behavior.
4. Choose an **Input source**, or click **Pick source on controller** and then click a knob or fader in the diagram.
5. Set its color or blink rate. RGB pads support palette colors; utility buttons retain their hardware's single-color LED.
6. Keep **Button press → Keep original Arena action**, or explicitly choose **Reset source value**.
7. Move the **Preview** slider to simulate the source position.
8. Name your profile and click **Save changes**. Restart the bridge from the dashboard to apply it. If you opened Studio directly from setup, close it and open **APC40 Bridge** from the desktop to reach the dashboard.

![Controller Studio](img/controller-studio.png)

The editor uses the supplied top-view APC40 mkII photograph with clickable regions over the actual controls: clip/scene pads, track/device buttons, sixteen main knobs, Cue level, track/master faders, crossfader and supported global buttons. Standard encoder ring feedback remains unchanged.

## Live view

Enable **Live bridge feedback** to display the LED Note values and source CC positions observed by the running bridge. This reads a small local snapshot file; the editor never opens another MIDI connection. The view reflects bridge output, not optical measurement of physical LEDs. Custom palette colors are approximated on screen.

The bridge must be running and connected. If it stops or the snapshot becomes stale, Studio shows an offline/waiting state instead of presenting simulated values as live. Turn Live off to return to the preview slider. Unsaved edits affect simulation only; live view continues to show the running configuration.

Snapshots update at up to 10 Hz only while the editor requests Live view, with unchanged frames deduplicated and a one-second heartbeat. Closing Live view lets a short lease expire, so the engine stops writing snapshots when the monitor is unused. This is a visual monitor, not a sample-accurate representation of blinking at high rates. The snapshot worker stops and marks the view disconnected when the bridge closes.

## Behaviors

| Lighting | Result |
|---|---|
| Default bridge | Preserve existing bridge behavior, including Hue/Colorize and enabled speed buttons |
| LED off | Hold this LED off without removing its original Arena button action |
| Solid light | Hold a palette color on an RGB pad, or light a utility button |
| Follow Hue | Map a knob/fader value to the existing Hue palette; RGB pads only |
| Follow level (on / off) | Light when the source CC is above zero |
| Blink | Blink at the configured slow rate |
| Speed indicator | Increase blink rate between Slow and Fast as the source moves from left to right |

Blink rates are limited to 0.2–5 Hz, with a default 1–3 Hz range. Speed indication follows the MIDI shortcut position; it is not an exact measurement of Arena's nonlinear playback-speed curve.

**Follow Hue** uses the bridge's existing Hue upper limit and palette. Mouse changes follow when **Settings → Sync changes from Arena** is on and Arena sends the matching source CC feedback to the bridge.

Custom lighting takes ownership of only the selected LED. Incoming Arena colors and the older bridge blinkers cannot overwrite it. Unchanged LED frames are not resent. Lighting animation uses Note messages; it never writes animated values into knob CCs.

## Button resets

**Reset source value** consumes the selected button's press and release and sends one absolute CC value to its linked source. Holding the button does not repeat the reset. The original Arena action is replaced only when this reset action is explicitly selected.

Reset position is the source's MIDI position: **0** is its left endpoint, **127** its right endpoint. With the supplied speed mapping, **0 selects 1x** and **127 selects 10x**. This is not universal: another mapping can use different endpoints. Physical faders are not motorized and do not move when reset.

## Save and share

**Save changes** updates only the lighting rules and profile name, preserves unrelated configuration, and makes a timestamped backup. It disables legacy ring animation to prevent encoder interference. If another process changes the configuration while Studio is open, saving stops and asks you to reopen it.

**Export profile** saves a named, versioned JSON profile. **Import profile** loads it into the preview; it does not apply anything until you save and restart. Profiles contain custom lighting rules, not MIDI port settings, Arena shortcuts, or the global legacy bridge settings.

Two examples are included in the app's **profiles** folder:

- **Default bridge.json** clears the custom overrides and returns every control to its existing bridge behavior.
- **Fader colors.json** links the top eight RGB pads to the eight track faders without changing their Arena actions.

Choose **Use default behavior** to remove only the selected control's override. Closing without saving leaves the installed configuration unchanged.

## Validation

The shared Python engine validates profiles before opening ports. Tests cover fader-driven color, mouse CC feedback, one LED owner, deduplicated animation, reset press/release handling, coexistence with speed buttons, compatibility without a profile, and worker shutdown.

The Windows UI is built with the same bundled .NET Framework compiler as the dashboard; it adds no browser runtime, background service, or graphics dependency. This visual editor is Windows-only; the separate macOS preview has no Studio UI yet.

The MIDI mapping is based on the [Akai APC40 mkII communications protocol](https://cdn.inmusicbrands.com/akai/attachments/apc40II/APC40Mk2_Communications_Protocol_v1.2.pdf). New custom hardware bindings still need to be checked on a connected controller.

## Installation and performance

Use the [Windows setup guide](windows-installation.md) for the ready-to-run EXE, automatic loopMIDI download, local offline dependency option, and automatic port preparation. The controller photograph is scaled once per resize and reused. Studio stops preview painting when minimized; the dashboard skips background status checks while its editor is open. Static lighting rules do not start an animation worker, unrelated/unchanged source CCs do not redraw their LEDs, and speed-button timing uses 30 updates per second instead of the legacy 120. These reduce work without claiming measured zero latency in Arena.

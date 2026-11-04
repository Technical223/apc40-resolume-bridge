# Mac tester checklist

Use a test composition. Follow [first-time setup](README.md) before connecting the bridge.

1. Open the app and check Overview, Settings and Controller Studio stay in the same window.
2. Run Install / repair, configure IAC and check the port status. Note any installation errors.
3. Start the bridge; move Hue knobs, toggle Colorize and edit Hue/Colorize with the mouse in Arena. Check controller feedback.
4. Try faders, clip pads and utility buttons. Change a lighting rule in Studio and check live updates. Test a profile export/import between Windows and Mac if possible.
5. Open Visualizer, choose a screen-capture or virtual-camera source, and try selecting fixtures in Edit output mapping.
6. Optionally unplug/reconnect USB. Stop the bridge and confirm another MIDI app can use the APC afterward.
7. Click Export diagnostics in Logs & diagnostics, review the ZIP and attach it manually to your feedback.

**Nothing is uploaded automatically. You decide whether to share the file.** It contains bounded technical logs, dependency/OS versions, MIDI names and related errors, not your composition or media. Home paths are redacted; review custom MIDI names.

Tell us your Mac architecture, macOS/Arena/Python versions, steps that worked, steps that failed and approximate failure times. A running bridge or completed timer does not prove hardware feedback works. If the app is blocked, send the exact macOS warning; do not disable system protections.

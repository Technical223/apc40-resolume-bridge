# Accessibility

APC40 Bridge is a small hobby project for live visual performers. We want the app to be usable by as many people as possible and welcome reports about barriers.

## Current status

The app has **not been formally audited** against WCAG or tested with screen readers. This statement describes what is known today, not a compliance claim.

## Supported environments

| Part | Environment |
|:---|:---|
| Windows dashboard and Controller Studio | Windows 10/11 x64, native WinForms (.NET Framework) |
| LED visualizer | Desktop Chromium-based browser with WebGL; uses the GPU |
| macOS preview (experimental) | macOS with Python 3.9+, native AppleScript menu and dashboard preview |
| Hardware | Akai APC40 mkII with Resolume Arena 7.x |

## What works

- The dashboard uses standard Windows controls and the system Segoe UI font at 10 pt or larger.
- Settings sliders can be focused with the keyboard and adjusted with **Left/Right**, **Home** and **End**.
- Some controls in Controller Studio and the visualizer provide accessible names or form labels.
- Closing the dashboard does not stop the bridge, so the controller keeps working without the window open.

## Known limitations

- **Color is central to the product.** Pad colors on the APC40 mirror Arena's Hue/Colorize values, and Controller Studio rules are edited mainly by color and blink speed. Some states can be hard to tell apart with color vision deficiency.
- **Blinking LEDs.** Utility buttons blink at 3 Hz by default; **Settings → Utility blink speed** adjusts this between 0.5 and 10 Hz. Optional speed buttons blink at up to 3 Hz and can be turned off in **Settings → Speed buttons**.
- **Mouse-first editors.** Controller Studio selects controls by clicking a photo of the APC40, and the visualizer's output editor relies on pointer selection. Full keyboard-only use has not been verified.
- **Screen readers** (Narrator, NVDA, VoiceOver) have not been tested. Custom-drawn controls may not announce their values.
- **Dark theme only.** Windows high-contrast mode and custom scaling above 100 % have not been verified.
- **The LED preview** is a visual tool by nature and shows bright, flashing content from your Arena composition. It can be closed at any time and is optional.
- Interface text is in English; Czech documentation is available, but the app itself is not localized.

## Report a barrier

Open an issue at <https://github.com/Technical223/apc40-resolume-bridge/issues> and describe:

- what you tried to do and where it failed,
- your operating system, display scaling and any assistive technology you use.

Please do not include personal information you do not want to be public. Barriers will be considered in future releases; there is no guaranteed timeline.

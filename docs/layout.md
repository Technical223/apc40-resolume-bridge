# Example layout (`APC40 BRIDGE EXAMPLE` preset)

[English](layout.md) | [Česky](layout.cs.md) · [Home](../README.md)

The preset expects a composition with **four groups of three layers**, optionally with two global layers above them:

| Layer | Content |
|---|---|
| 1, 4, 7, 10 | Base group generator (Alpha blend) |
| 2, 5, 8, 11 | Complementary generator (Lighten blend) |
| 3, 6, 9, 12 | FLASH: clip 1 WHITE, 2 STROBE, 3 SCISSORS, 4 BLACK (Piano trigger style, Ignore Column Trigger) |
| 13 | GLOBAL (all LEDs) |
| 14 | GLOBAL FLASH: WHITE, STROBE, SCISSORS, BLACK |

Groups have Strobe, Trails, Mirror, and Invert effects, initially disabled. Transform places each group into its own canvas area, matching its LED slices in Advanced Output. Slices take their input from the composition, so global layers reach every LED.

## APC40 mkII

| Control | Function |
|---|---|
| Grid rows 1–4, from the bottom | Clips 1–4; each column controls the layer above its fader (1, 2, 4, 5, 7, 8, 10, 11) |
| Top grid row | **COLOR**: the hue of the knob above it; press to toggle layer Colorize via the bridge |
| Track knobs 1–8 | Layer Hue (0–0.63871; see the [Hue range guide](navod.md#hue-range-match-the-knob-and-pad)) |
| Faders 1–8 | Layer opacity |
| Activator 1–8 | Clip 5 |
| A\|B 1–8 | Clear layer |
| Clip Stop, pairs per group | Group WHITE / STROBE flash |
| Track Select, pairs | Group SCISSORS / mute |
| S / ●, four per group | Group Strobe FX, Trails, Mirror, Invert |
| Scene launch 1–4 | ALL WHITE, STROBE, SCISSORS, BLACK (GLOBAL FLASH) |
| Scene launch 5 / Stop All | Tap tempo / resync |
| Device knobs 1–4 / 5–8 | Group flash hue / group speed |
| Device buttons 1–4 / 5–8 | Flash color on/off / clear group |
| Pan, Sends, User, Play | Decks 1–4 |
| Bank select ▲▼ / ◀▶ | Deck / column |
| Master button, Nudge −/+, Session | GLOBAL on/off, previous/next clip, clear |
| Record | Turn everything off |
| Master fader / crossfader | Master / GLOBAL opacity |
| Cue knob | Strobe FX speed, relative |
| Tempo knob | BPM |

SCISSORS refers to the clip named “NŮŽKY” in the original composition; existing clip and preset names do not need to be changed.

The preset uses **Any device**, so it works through the bridge as well as with the APC connected directly.

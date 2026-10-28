# Ukázkové rozložení (preset `APC40 BRIDGE EXAMPLE`)

[English](layout.cs.md) | **Česky** · [Hlavní stránka](../README.cs.md)

Preset počítá s kompozicí se **4 grupami po 3 vrstvách** (+ volitelně 2 globální vrstvy nahoře):

| Vrstva | Obsah |
|---|---|
| 1, 4, 7, 10 | základní generátor grupy (blend Alpha) |
| 2, 5, 8, 11 | „opačný“ generátor (blend Lighten) |
| 3, 6, 9, 12 | FLASH: klip 1 WHITE, 2 STROBE, 3 NŮŽKY, 4 BLACK (trigger style Piano, Ignore Column Trigger) |
| 13 | GLOBAL (přes všechny LED) |
| 14 | GLOBAL FLASH: WHITE, STROBE, NŮŽKY, BLACK |

Grupy mají efekty Strobe, Trails, Mirror, Invert (vypnuté). Každá grupa je přes Transform posazená do své oblasti plátna, kde leží slicy jejích LED v Advanced Outputu. Slicy berou vstup z kompozice, takže globální vrstvy svítí na všech LED.

## APC40 mkII
| Ovladač | Funkce |
|---|---|
| Grid, řady 1–4 (zdola) | klipy 1–4, sloupec = vrstva nad faderem (1, 2, 4, 5, 7, 8, 10, 11) |
| Grid, horní řada | **BARVA**: odstín z knobu nad ní, stisk = colorize zap/vyp (bridge) |
| Track knoby 1–8 | hue vrstvy (0–0,63871, viz README „Rozsah hue“) |
| Fadery 1–8 | opacity vrstvy |
| Activator 1–8 | klip 5 |
| A\|B 1–8 | clear vrstvy |
| Clip Stop (dvojice na grupu) | WHITE / STROBE flash grupy |
| Track Select (dvojice) | NŮŽKY / mute grupy |
| S / ● (čtveřice na grupu) | strobe FX, trails, mirror, invert grupy |
| Scene launch 1–4 | ALL WHITE, STROBE, NŮŽKY, BLACK (GLOBAL FLASH) |
| Scene launch 5 / Stop All | tap tempo / resync |
| Device knoby 1–4 / 5–8 | hue flashe grupy / rychlost grupy |
| Device tlačítka 1–4 / 5–8 | barva flashe zap/vyp / clear grupy |
| Pan, Sends, User, Play | deck 1–4 |
| Bank select ▲▼ / ◀▶ | deck / sloupec |
| Master tlačítko, Nudge −/+, Session | GLOBAL zap/vyp, předchozí/další klip, clear |
| Record | vypnout vše |
| Master fader / crossfader | master / opacity GLOBAL |
| Cue knob | rychlost strobe FX (relativně) |
| Tempo knob | BPM |

Preset je nastavený na **libovolné zařízení**, funguje přes bridge i s APC zapojeným napřímo.

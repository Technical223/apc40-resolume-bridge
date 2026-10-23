# APC40 mkII ⇄ Resolume Arena bridge

Malý MIDI „prostředník“ mezi **Akai APC40 mkII** a **Resolume Arena 7**, který dělá to, co Resolume sám neumí:

- **Barevné pady pod hue knoby.** Horní řada gridu svítí odstínem, který zrovna dává track knob nad ní (červená → zelená → modrá). Stisk padu zapne/vypne colorize, vypnuto = pad svítí bíle.
- **Tlačítka svítí pořád.** Jednobarevná tlačítka (Clip Stop, Track Select, Activator, S, ●, A|B, device tlačítka, scene launch…) svítí trvale, aby šla najít ve tmě, a **blikají, když je jejich funkce aktivní**.
- **Hlídá Arenu.** Běží na pozadí bez okna, APC převezme, když spustíš Arenu, a pustí ho, když ji zavřeš. Po vytažení kabelu se sám znovu připojí.
- **Instalace jedním kliknutím.** `START.bat` doinstaluje Python, knihovny i loopMIDI a nastaví Resolume.

Všechno ostatní (fadery, knoby, grid, LED klipů) prochází beze změny, takže funguje s jakýmkoliv MIDI mappingem v Resolume.

```
APC40 mkII ⇄ apc_bridge.py ⇄ loopMIDI „APC VIRT A“ → Resolume (vstup)
                           ⇠ loopMIDI „APC VIRT B“ ← Resolume (výstup / LED)
```

## Požadavky
- Windows 10 / 11
- Resolume Arena 7 (testováno 7.25)
- Akai APC40 mkII
- [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html) (instalátor ho zkusí nainstalovat přes winget; zdarma pro nekomerční použití)
- Python 3.9+ (instalátor nainstaluje 3.12, když chybí)

## Instalace
1. Stáhni repo (Code → Download ZIP) a rozbal kamkoliv. Složku můžeš později přesunout.
2. **Zavři Resolume Arenu.**
3. Spusť `bridge\START.bat`.
4. V okně loopMIDI vytvoř dva porty: **`APC VIRT A`** a **`APC VIRT B`** (název do *New port-name*, tlačítko **+**) a zaškrtni v loopMIDI *Autostart*. Instalátor počká, až porty uvidí.
5. Instalátor přepne MIDI v Resolume: vypne přímé APC40 mkII, zapne `APC VIRT A` jako vstup a `APC VIRT B` jako výstup. Záloha: `Preferences\midi.xml.pred-bridge.bak`.
6. Volitelně `AUTOSTART_ZAPNOUT.bat`, bridge pak čeká od přihlášení do Windows.
7. V Areně vyber MIDI preset (Shortcuts → Edit MIDI). **Preset musí být nastavený na libovolné zařízení**, ne na „APC40 mkII“, jinak přes virtuální port nereaguje. Ukázkový preset `APC40 BRIDGE EXAMPLE` se nakopíruje automaticky.

## Soubory v `bridge\`
| Soubor | Co dělá |
|---|---|
| `START.bat` | instalace (poprvé) + spuštění na pozadí |
| `STOP.bat` | zastaví bridge, APC se uvolní |
| `LADENI.bat` | běh v okně s výpisem portů a chyb |
| `AUTOSTART_ZAPNOUT.bat` / `AUTOSTART_VYPNOUT.bat` | start po přihlášení do Windows |
| `VRATIT_RESOLUME.bat` | vrátí MIDI nastavení Resolume (APC napřímo) |
| `config.json` | porty, rozsah hue, paleta, která tlačítka svítí |
| `bridge.log`, `setup.log` | záznam běhu (vznikne při běhu) |

## Nastavení (`config.json`)
| Klíč | Výchozí | Význam |
|---|---|---|
| `to_resolume_port` / `from_resolume_port` | `APC VIRT A` / `APC VIRT B` | názvy loopMIDI portů |
| `knob_ccs` | 48–55 | track knoby, ze kterých se bere odstín |
| `color_notes` | 32–39 | pady, které ukazují odstín (horní řada gridu) |
| `hue_max` | 0.6387 | horní mez hue v Resolume (stejná jako ValueRange knobu) |
| `palette` | 11 barev | úhel odstínu → číslo barvy APC |
| `always_lit` | `true` | jednobarevná tlačítka svítí trvale |
| `lit_invert` | mute tlačítka | tlačítka, kde „svítí“ znamená normální stav; blikají, když zhasnou |
| `blink_hz` | 3 | rychlost blikání aktivních tlačítek |
| `apc_mode` | 66 | režim APC (0x42 Alternate Ableton); zkus 65, kdyby něco nereagovalo |

## Nouzový režim
Kdyby bridge na akci nejel: `STOP.bat`, v Areně *Preferences → MIDI* zapni **APC40 mkII** (vstup i výstup). Preset nastavený na libovolné zařízení funguje dál, jen bez barevné horní řady a trvale svítících tlačítek.

## Známá omezení
- Pad ukazuje **polohu knobu**, ne hodnotu v Resolume. Když měníš hue myší, pad to neví. Poslední polohy si bridge pamatuje (`state.json`).
- Po startu bridge APC pošle aktuální polohy faderů a knobů, Resolume je hned převezme.
- Když je zapojený i jiný kontroler se stejnými notami (např. APC20), reagoval by na preset „libovolné zařízení“ taky. V Resolume ho vypni.
- Barvy jsou z palety APC40 mk2 (stejná jako Launchpad), na každém kusu můžou vypadat trochu jinak.

Ukázkový mapping a rozložení kompozice: [`docs/layout.md`](docs/layout.md).

---

### English summary
A small MIDI bridge between an Akai APC40 mkII and Resolume Arena 7 (Windows). The top grid row shows the current hue of the track knob above it (press = colorize on/off), single-colour buttons stay lit and blink while active, the bridge starts/stops itself with Arena, and `START.bat` installs everything it needs (Python, mido/python-rtmidi, loopMIDI). Your Resolume MIDI preset must be set to *any device*. See `config.json` for options.

License: MIT

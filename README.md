# APC40 mkII ⇄ Resolume Arena bridge

![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D6)
![Resolume](https://img.shields.io/badge/Resolume%20Arena-7.x-8A2BE2)
![License](https://img.shields.io/badge/license-MIT-green)

Barevné pady pod Hue knoby, tlačítka viditelná ve tmě a **jedno okno pro instalaci, spuštění a správu**.

- Pad ukazuje odstín knobu; stisk přepíná Colorize.
- Volitelná MIDI zpětná vazba přijímá změny z Areny i jiných ovladačů.
- Bridge se aktivuje s Arenou a uvolní kontroler po jejím zavření.
- Aplikace ukazuje stav kontroleru, Areny, portů a instalace. Bez terminálového okna.

<p align="center">
  <a href="docs/media/app-showcase.gif"><img src="docs/media/app-showcase.gif" width="1000" alt="Animovaná prohlídka APC40 Bridge: přehled připojení, nastavení a provozní logy"></a>
</p>
<p align="center"><sub>Skutečné snímky Windows aplikace · přehled, nastavení a logy v jednom okně</sub></p>

## Ukázky aplikace

<table>
  <tr>
    <td width="33%" align="center"><a href="docs/img/app-dashboard.png"><img src="docs/img/app-dashboard.png" alt="Hlavní okno APC40 Bridge se stavem kontroleru, Areny, portů a instalace"></a></td>
    <td width="33%" align="center"><a href="docs/img/app-settings.png"><img src="docs/img/app-settings.png" alt="Nastavení MIDI portů, Hue, zpětné vazby a osvětlení"></a></td>
    <td width="33%" align="center"><a href="docs/img/app-logs.png"><img src="docs/img/app-logs.png" alt="Prohlížeč provozních logů APC40 Bridge"></a></td>
  </tr>
  <tr>
    <td align="center"><b>Přehled připojení</b></td>
    <td align="center"><b>Nastavení</b></td>
    <td align="center"><b>Provozní logy</b></td>
  </tr>
</table>

Kliknutím otevřeš snímek v plné velikosti.

## Začni tady — Windows

1. Rozbal balíček **APC40-Bridge-Windows.zip** do složky, kde má zůstat. Při prvním nastavení zavři Arenu.
2. Otevři **APC40 Bridge.exe**.
3. Klikni **Připravit a spustit**. Příprava najde nebo nainstaluje potřebné součásti.
4. Pokud chybí virtuální porty, klikni **Otevřít loopMIDI**, vytvoř **APC VIRT A** a **APC VIRT B** a přípravu zopakuj.
5. V Areně vyber MIDI preset na **Any device** a nastav Hue **Range Max 0,63871** (zobrazuje se zaokrouhleně 0,64).

Pro další použití stačí aplikace a tlačítko **Spustit bridge**. Volba **Spouštět automaticky po přihlášení do Windows** spustí bridge bez otevírání správce.

**Stažený zdrojový ZIP z GitHubu:** ve složce `bridge` otevři **APC40 Bridge.vbs**. Ten připraví aplikaci z přiložených zdrojů a otevře stejné okno. Není k tomu potřeba Python ani další vývojové nástroje; sestavení používá .NET Framework ve Windows.

## Vše na jednom místě

| Ovládání | Co dělá |
|---|---|
| Spustit bridge | Spustí hlídání Areny; při opakovaném spuštění nevytváří další proces |
| Zastavit / Restartovat | Bezpečně uvolní kontroler nebo načte nové nastavení |
| Instalace / oprava | Připraví závislosti a MIDI nastavení; běžící bridge zbytečně nerestartuje |
| Nastavení | Porty, Hue, zpětná vazba a osvětlení; zachová ostatní hodnoty a uloží zálohu |
| Zobrazit logy | Provoz, příprava i správa přímo v aplikaci |
| Zástupce na plochu | Přidá běžnou ikonu aplikace na plochu |
| Obnovit MIDI Areny | Při zavřené Areně vrátí zálohu MIDI nastavení, zastaví bridge a vypne autostart |

Zavření správce **nezastaví** bridge. Běží samostatně na pozadí. Restart může do Areny znovu přenést fyzické polohy faderů/knobů.

## Bridge v akci

<p align="center">
  <a href="docs/media/demo.mp4"><img src="docs/media/demo.gif" width="340" alt="Ukázka fyzického APC40: Hue knob mění barvu padu i výstupu v Resolume"></a>
</p>
<p align="center"><sub><a href="docs/media/demo.mp4">Přehrát původní ukázku APC40 v plné kvalitě</a></sub></p>

## Zpětná vazba LED

`sync_resolume_feedback: true` v `config.json` zapíná stávající MIDI zpětnou vazbu. Hue CC 48–55 aktualizují odstín, noty 32–39 stav Colorize. Arena je musí odesílat do `APC VIRT B`; pro aktuální preset platí velocity **5 = aktivní efekt, 3 = bypass**.

Jde o 7bitovou MIDI hodnotu v rozsahu nastaveného presetu, nikoli plně přesné čtení přes API. Mimo rozsah `0–hue_max` není správný odstín zaručen. Režim lze vypnout v **Nastavení → Zpětná vazba**. Webserver ani další knihovna nejsou potřeba.

👉 **[Podrobný návod, nastavení a řešení problémů](docs/navod.md)**

Pro další vývoj: [kontext a ověření změn](CLAUDE.md), [technický popis aplikace](docs/windows-app.md).

Původní dávkové soubory zůstávají pro kompatibilitu; `START.bat` nyní otevře správce.

<details>
<summary>English</summary>

A Windows control panel and MIDI bridge for Akai APC40 mkII and Resolume Arena 7. Extract the Windows package and open **APC40 Bridge.exe**. Installation, start/stop, autostart, settings, logs and recovery are available in one window. A source ZIP can bootstrap the same app using **bridge/APC40 Bridge.vbs**.

Create loopMIDI ports APC VIRT A/B, set the Resolume MIDI preset to Any device, and keep the Hue range aligned with hue_max (0.63871 by default). MIDI feedback is optional and limited to the shortcut's 7-bit range. Closing the control panel leaves the background bridge running.
</details>

MIT · [Technical223](https://github.com/Technical223)

# Windows aplikace

[English](windows-app.md) | **Česky** · [Hlavní stránka](../README.cs.md)

## Soubory

- `bridge/ui/BridgeManager.cs`: nativní WinForms správce (.NET Framework); nepotřebuje Python pro své vlastní spuštění.
- `bridge/build-ui.ps1`: sestavení pomocí systémového C# kompilátoru. EXE je výstup sestavení a není uložené v Gitu.
- `bridge/APC40 Bridge.vbs`: vstup pro zdrojový ZIP; skrytě sestaví chybějící EXE a otevře správce.
- `bridge/manage.ps1`: sdílené akce status/start/stop/autostart/shortcut/restore.
- `bridge/runtime.ps1`: hledání Pythonu a lokální cache cesty `runtime.json`.
- `bridge/setup.ps1 -NoPopup -PrepareOnly`: příprava součástí a konfigurace bez spouštění/restartu watcheru.
- `bridge/package-release.ps1`: přenosný ZIP s aplikací, výchozím configem, presetem a návodem.
- `.github/workflows/windows.yml`: Windows testy, sestavení a ZIP jako GitHub Actions artefakt.

## Chování

Správce spouští PowerShell bez konzolového okna. Stav se kontroluje asynchronně každých 5 s. `--status-json` v Pythonu pouze vypisuje dostupné porty; nikdy je neotevírá ani nebere běžícímu bridge. Připravenost zahrnuje i read-only kontrolu MIDI nastavení Areny a dostupnost virtuálních portů. Stav „Bridge spuštěný“ znamená ověřený proces watcheru, nikoli potvrzení každé MIDI zprávy.

Start je idempotentní: pokud watcher této složky běží, ponechá ho beze změny. Start/stop a další mutace se serializují pojmenovaným mutexem podle cesty instalace. Platí ověření identity procesu ze stop_bridge.ps1. Samotný dashboard má také jednu instanci na instalaci.

Zavření okna nemění běh bridge. Přepínač autostartu vytváří zástupce v uživatelské složce Po spuštění s cílem `APC40 Bridge.exe --autostart`. Tento režim spustí pouze watcher a skončí; nespouští instalaci ani nezobrazuje dashboard.

Nastavení zachovává neznámé klíče configu, kontroluje porty a číselné rozsahy a ukládá atomicky přes File.Replace se zálohou. Hodnoty načte až restart watcheru. Logy jsou čteny sdíleně, pouze z posledních 64 KB. Obnova MIDI je výslovná akce s potvrzením; odmítne běžící Arenu a bez nalezené zálohy nic nezastaví.

Příprava používá původní instalační postup Python/mido/python-rtmidi/loopMIDI. Vytvoření virtuálních portů zůstává ruční krok v loopMIDI. Při jejich absenci se vrátí konkrétní pokyn, místo neviditelného pětiminutového čekání. Kompletní instalace na čistém Windows nebyla při této změně testována.

## Sestavení

Z kořene repa:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File bridge/build-ui.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File bridge/package-release.ps1
py -3 -m unittest discover -s tests -v
py -3 tests/test_stop_process.py
```

Výchozí výstup balíčku je `dist/APC40-Bridge-Windows.zip`. Pro další sestavení použij jiný výstupní adresář nebo původní ZIP nejprve přesuň. Balíček obsahuje čistý výchozí config z repozitáře, nikoli lokální stav, PID, logy nebo cache. Při aktualizaci existující instalace zachovej vlastní config.json a state.json.

# Kontext projektu pro Clauda

Aktualizováno 26. 10. 2026. Repo: Technical223/apc40-resolume-bridge.
Výchozí prověřený commit: 3855d08223d5c55350fa9edb5b9d6da87de64f6e.

## Výslovné rozhodnutí uživatele

NESYNCHRONIZOVAT horní barevnou řadu podle stavu Resolume. Uživatel při živém testu potvrdil, že vypnutí Colorize myší nezmění barevný pad na bílý, a výslovně požaduje toto chování ponechat. Jde o známé, přijatelné omezení. Horní řada odráží místní stav knobů/padů; příchozí noty 32–39 na MIDI kanálu 0 se dál zahazují. Změny myší a přepnutí kompozice mohou indikaci rozcházet. Platí i původní hue_max = 0.63871 a vazba na stejný rozsah v presetu.

## Provedené opravy

1. Konstruktor Bridge eviduje každý otevřený port. Při selhání dalšího otevření nebo inicializace zavře dosud otevřené porty a znovu vyvolá původní chybu.
2. Výjimka v on_apc, on_resolume nebo blikání nastaví threading.Event failed. alive() tak vrátí False i tehdy, když se názvy portů nezměnily. Hlavní smyčka zavře starý bridge a opakuje vytvoření.
3. STOP.bat a setup.ps1 používají společný stop_bridge.ps1. Číslo v bridge.pid se ověřuje proti procesu Python/Pythonw, přesné absolutní cestě skriptu jako prvnímu argumentu, režimu --watch/--run a času vzniku procesu. Ukončení používá držený handle konkrétního procesu, nikoli znovu vyhledaný PID. Cizí proces zůstane běžet; neověřitelná identita zastaví restart bezpečně.
4. README a návod výslovně uvádějí záměrné omezení Colorize i Hue.

## Ověření

- tests/test_bridge.py: 9 testů, včetně všech čtyř bodů selhání otevírání portů, chyby inicializačního odesílání, chyb obou směrů a blikání, opětovného vytvoření bridge, normálního průchodu MIDI a zachování ignorované zpětné vazby horní řady.
- tests/test_stop_process.py: skutečné dočasné procesy, ověření že cizí Python a jiný režim téhož skriptu zůstávají běžet, neplatný/starý PID, zastavení správného procesu, cesta s mezerou a apostrofem a syntaktická kontrola Windows PowerShellu 5.1.
- Testy nevyžadují připojené MIDI zařízení a nemění nastavení Resolume.
- Skutečné odpojení a opětovné připojení USB nebylo testováno; simulované chyby nejsou důkazem chování konkrétního ovladače.

Spuštění testů z kořene repa:
    py -3 tests/test_bridge.py -v
    py -3 tests/test_stop_process.py

## Nasazení

Živá místní instalace má soubory z bridge/ přímo v jedné složce (není to Git checkout).
Při kopírování opravy je nutné zahrnout nový stop_bridge.ps1 spolu s apc_bridge.py, setup.ps1 a STOP.bat.
Běžící Python drží starý kód až do restartu. Restart může znovu odeslat fyzické polohy faderů/knobů do kompozice, jak již uvádí návod.
GitHubové změny jsou předávány přes pull request; tento soubor nezaručuje jeho sloučení.

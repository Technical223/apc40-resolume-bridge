# Kontext projektu pro Clauda

Aktualizováno 26. 10. 2026. Repo: Technical223/apc40-resolume-bridge.
Výchozí prověřený commit: 3855d08223d5c55350fa9edb5b9d6da87de64f6e.

## Aktuální rozhodnutí uživatele: jednoduchá MIDI synchronizace

Uživatel původně schválil ignorování zpětné vazby horní řady. Následně výslovně požádal doplnit reakci na změny Hue/Colorize myší a jinými zdroji, ale hlavně nic nekomplikovat a zachovat stabilitu. Toto novější přání nahrazuje předchozí zákaz synchronizace.

Použita je pouze stávající MIDI zpětná vazba; Webserver nebyl zapnut, nejsou přidané závislosti ani REST/OSC. `sync_resolume_feedback` je v configu true, bezpečný výchozí stav bez klíče je false. Jednou volbou lze obnovit původní chování. Mapování CC 48–55 / noty 32–39, kanál 0, hue_max 0.63871 zůstává.

Živým testem stávající Areny bylo ověřeno: odeslání CC54=50 přes jiný MIDI výstup vyvolá zpětnou vazbu CC54=49 (MIDI zaokrouhlení), návrat na 0 vrátí 0. Přepnutí Colorize na notě 38 vrátí velocity 3 pro bypass a 5 pro zapnutý efekt. Stejné hodnoty jsou v NamedValues aktuálního JKB APC40 PRO presetu. Nelze používat prosté velocity>0. Testovaná vrstva byla po testu vrácena na Hue 0 a aktivní Colorize.

Nový handler uloží příchozí Hue a překreslí LED. Colorize feedback nastavuje stav idempotentně (nepřepíná ho znovu) a vykreslí bílou nebo aktuální odstín. CC průchod do APC zůstává, zprávy se neposílají zpět do Areny. Neznámé velocity a Note Off se ignorují. Bez feedbacku zůstává původní ovládání APC funkční.

Omezení: 7bitové MIDI, rozsah a směrování shortcutu; nejde o přesné čtení plného Hue přes API, aktivní dotazování ani sledování saturace/jasu. Mimo rozsah shortcutu není věrný odstín zaručen. Automatické resynchronizování kompozice závisí na tom, zda Arena pošle stejné mapování. Změny přímo myší nebyly v závěrečném testu ověřené; ověřen byl externí MIDI zdroj a skutečná zpětná vazba Areny.

Testy: `py -3 -m unittest discover -s tests -v` (19 testů; 9 původních + 10 nových). Nové testy pokrývají všech 8 knobů/padů, bypass, opětovné zapnutí se správným odstínem, vypnutí nové volby, chybné velocity/kanály a nevytváření zpětné smyčky. Integrační test s běžící Arenou potvrdil změny uloženého stavu Hue a Colorize z reálného feedbacku. Testy STOP zůstávají stejné.

## Provedené opravy

1. Konstruktor Bridge eviduje každý otevřený port. Při selhání dalšího otevření nebo inicializace zavře dosud otevřené porty a znovu vyvolá původní chybu.
2. Výjimka v on_apc, on_resolume nebo blikání nastaví threading.Event failed. alive() tak vrátí False i tehdy, když se názvy portů nezměnily. Hlavní smyčka zavře starý bridge a opakuje vytvoření.
3. STOP.bat a setup.ps1 používají společný stop_bridge.ps1. Číslo v bridge.pid se ověřuje proti procesu Python/Pythonw, přesné absolutní cestě skriptu jako prvnímu argumentu, režimu --watch/--run a času vzniku procesu. Ukončení používá držený handle konkrétního procesu, nikoli znovu vyhledaný PID. Cizí proces zůstane běžet; neověřitelná identita zastaví restart bezpečně.
4. README a návod popisují novou volitelnou MIDI synchronizaci i původní režim bez ní.

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

Nová synchronizace navíc vyžaduje nové klíče config.json (sync_resolume_feedback a dvě velocity). Při ruční aktualizaci sluč config s vlastním nastavením; nepřepisuj uživatelské porty ani mapování.

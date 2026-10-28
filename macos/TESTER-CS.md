# Testovací macOS verze

První experimentální verze, oddělená od Windows. Zatím není ověřená s fyzickým APC na Macu. Obsahuje jednoduché nativní menu, tříminutový test a export diagnostiky.

1. Nainstaluj Python z python.org (doporučeno 3.11/3.12), pokud jej nemáš. Není součástí balíčku.
2. Rozbal ZIP do stálé složky a otevři **APC40 Bridge macOS Preview.app**. Aplikace není podepsaná ani notarizovaná. Pokud macOS spuštění blokuje, pošli přesné znění hlášky; nevypínej ochrany. **Open Preview.command** je alternativní ladicí spouštěč přes Terminál.
3. Vyber **Prepare dependencies** a počkej. MIDI knihovny se instalují do samostatného prostředí aplikace.
4. Přes **Open Audio MIDI Setup** otevři MIDI Studio → IAC Driver, zapni **Device is online**, přidej **APC VIRT A** a **APC VIRT B**. loopMIDI není potřeba.
5. V Areně v Preferences → MIDI zapni u A pouze vstup a u B pouze výstup. Vypni přímý vstup/výstup APC40, clock u IAC portů nech vypnutý. Ostatní zařízení neměň.
6. Použij kompatibilní MIDI preset na **Any device**, Hue Max **0.63871**. Přiložený preset najdeš uvnitř .app přes Show Package Contents → Contents/Resources/resolume. Použij testovací kompozici; start může přenést fyzické polohy faderů/knobů do Areny.
7. Vyber **Start 3-minute test**. Vyzkoušej Hue knoby, Colorize pady, změny myší v Areně, fadery a další tlačítka. Volitelně odpoj/připoj USB. Poznamenej si, co fungovalo a co ne.
8. Po třech minutách test skončí a vytvoří **APC40-macOS-debug-…zip** na ploše. **Stop test** jej ukončí dříve. **Export diagnostics** zastaví aktivní test a vytvoří nový ZIP včetně posledního výsledku. Pokud plocha není dostupná, hledej přes **Open logs folder → reports**.
9. Pošli ZIP Jakubovi a připiš verzi Areny a popis problémů. Nic se neodesílá automaticky.

Když chybí Python, spouštěč se i tak pokusí vytvořit malý ZIP s verzí macOS, architekturou a chybou. Při chybě instalace nebo MIDI spojení lze použít Export diagnostics.

Log obsahuje verze, názvy MIDI portů, chyby, počty zpráv a nejvýše 300 posledních změn Hue/Colorize. Neobsahuje kompozice ani snímky; domovské cesty se anonymizují. Vlastní názvy MIDI portů si před odesláním zkontroluj.

Aplikace nemá autostart a nepřepisuje nastavení Areny. **Quit** test ukončí a uvolní porty. Pro použití APC napřímo potom ručně znovu zapni jeho vstup/výstup v Areně.

Úspěšně dokončený časovač sám nepotvrzuje funkčnost MIDI. Nulový počet connections znamená, že se nepodařilo otevřít všechny potřebné porty.

@echo off
rem Vrati MIDI nastaveni Resolume do stavu pred bridge (Arena musi byt zavrena)
cd /d "%~dp0"
py -3 apc_bridge.py --restore-resolume
pause

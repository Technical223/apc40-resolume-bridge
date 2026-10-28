@echo off
rem Restore Arena MIDI settings from before bridge setup (Arena must be closed)
cd /d "%~dp0"
py -3 apc_bridge.py --restore-resolume
pause

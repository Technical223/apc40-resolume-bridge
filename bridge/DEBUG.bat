@echo off
rem Run the bridge in a console (stop the background bridge with STOP.bat first)
cd /d "%~dp0"
py -3 apc_bridge.py --list-ports
py -3 apc_bridge.py --run
pause

@echo off
rem Spusti bridge v okne s vypisem (nejdriv zastav ten na pozadi pres STOP.bat)
cd /d "%~dp0"
py -3 apc_bridge.py --list-ports
py -3 apc_bridge.py --run
pause

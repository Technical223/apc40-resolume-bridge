@echo off
rem Stop only the bridge in this folder
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_bridge.ps1"
pause

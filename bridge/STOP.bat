@echo off
rem Zastavi pouze bridge z teto slozky
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_bridge.ps1"
pause

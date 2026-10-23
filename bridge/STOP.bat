@echo off
rem Zastavi bridge (APC40 se uvolni)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=Join-Path '%~dp0' 'bridge.pid'; if(Test-Path $p){Stop-Process -Id (Get-Content $p) -Force -ErrorAction SilentlyContinue; Remove-Item $p}; Write-Host Zastaveno."
pause

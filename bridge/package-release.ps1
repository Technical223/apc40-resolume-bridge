param([string]$OutputDirectory=(Join-Path (Split-Path $PSScriptRoot -Parent) 'dist'), [string]$WorkDirectory=$env:TEMP)
$ErrorActionPreference='Stop'
$Repo=Split-Path $PSScriptRoot -Parent
& (Join-Path $PSScriptRoot 'build-ui.ps1') | Out-Null
$stage=Join-Path $WorkDirectory ('apc40-package-' + [guid]::NewGuid().ToString('N'))
$app=Join-Path $stage 'APC40 Bridge'
New-Item -ItemType Directory -Path $app -Force | Out-Null
$files=@('APC40 Bridge.exe','APC40 Bridge.vbs','apc_bridge.py','config.json','setup.ps1','runtime.ps1','manage.ps1','stop_bridge.ps1','build-ui.ps1','package-release.ps1','START.bat','STOP.bat','AUTOSTART_ON.bat','AUTOSTART_OFF.bat','DEBUG.bat','RESTORE_RESOLUME.bat','AUTOSTART_ZAPNOUT.bat','AUTOSTART_VYPNOUT.bat','LADENI.bat','VRATIT_RESOLUME.bat')
foreach ($name in $files) { Copy-Item -LiteralPath (Join-Path $PSScriptRoot $name) -Destination (Join-Path $app $name) }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'ui') -Destination (Join-Path $app 'ui') -Recurse
foreach ($folder in @('docs','resolume')) { Copy-Item -LiteralPath (Join-Path $Repo $folder) -Destination (Join-Path $app $folder) -Recurse }
foreach ($name in @('README.md','README.cs.md','LICENSE','CLAUDE.md')) { Copy-Item -LiteralPath (Join-Path $Repo $name) -Destination (Join-Path $app $name) }
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$zip=Join-Path $OutputDirectory 'APC40-Bridge-Windows.zip'
if (Test-Path -LiteralPath $zip) { throw ('Package already exists: ' + $zip + '. Choose another output directory.') }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[IO.Compression.ZipFile]::CreateFromDirectory($stage,$zip,[IO.Compression.CompressionLevel]::Optimal,$false)
Write-Output $zip

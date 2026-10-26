param([string]$OutputDirectory=$PSScriptRoot)
$ErrorActionPreference='Stop'
$compiler=Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path -LiteralPath $compiler)) { $compiler=Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe' }
if (-not (Test-Path -LiteralPath $compiler)) { throw 'Je potreba .NET Framework 4.8 (soucast Windows 10/11).' }
if (-not (Test-Path -LiteralPath $OutputDirectory)) { New-Item -ItemType Directory -Path $OutputDirectory | Out-Null }
$destination=Join-Path $OutputDirectory 'APC40 Bridge.exe'
& $compiler /nologo /target:winexe /platform:anycpu /optimize+ /utf8output ("/out:" + $destination) ("/win32icon:" + (Join-Path $PSScriptRoot 'ui\bridge.ico')) /reference:System.dll /reference:System.Core.dll /reference:System.Drawing.dll /reference:System.Windows.Forms.dll /reference:System.Web.Extensions.dll (Join-Path $PSScriptRoot 'ui\BridgeManager.cs')
if ($LASTEXITCODE -ne 0) { throw 'Sestaveni aplikace se nepodarilo.' }
Write-Output $destination

param([string]$OutputDirectory=$PSScriptRoot, [string]$DependencyCache=(Join-Path $env:LOCALAPPDATA 'APC40 Bridge/build-cache'))
$ErrorActionPreference='Stop'
$compiler=Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
if (-not (Test-Path -LiteralPath $compiler)) { $compiler=Join-Path $env:WINDIR 'Microsoft.NET/Framework/v4.0.30319/csc.exe' }
if (-not (Test-Path -LiteralPath $compiler)) { throw '.NET Framework 4.8 is required (included with Windows 10/11).' }
New-Item -ItemType Directory -Path $OutputDirectory,$DependencyCache -Force | Out-Null
$OutputDirectory=(Get-Item -LiteralPath $OutputDirectory).FullName
$DependencyCache=(Get-Item -LiteralPath $DependencyCache).FullName
$lock=(Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'offline-dependencies.lock.json') | ConvertFrom-Json).webview2_sdk
$package=Join-Path $DependencyCache $lock.file
if (-not (Test-Path -LiteralPath $package)) {
    $partial=$package+'.download'
    try { [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri $lock.url -OutFile $partial; Move-Item -LiteralPath $partial -Destination $package }
    finally { if (Test-Path -LiteralPath $partial) { Remove-Item -LiteralPath $partial } }
}
if ((Get-FileHash -LiteralPath $package -Algorithm SHA256).Hash.ToLowerInvariant() -ne $lock.sha256) { throw 'WebView2 SDK checksum mismatch.' }
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip=[IO.Compression.ZipFile]::OpenRead($package)
try {
    $files=@{'lib/net462/Microsoft.Web.WebView2.Core.dll'='Microsoft.Web.WebView2.Core.dll';'lib/net462/Microsoft.Web.WebView2.WinForms.dll'='Microsoft.Web.WebView2.WinForms.dll';'runtimes/win-x64/native/WebView2Loader.dll'='WebView2Loader.dll';'LICENSE.txt'='WebView2-SDK-LICENSE.txt'}
    foreach ($name in $files.Keys) { $entry=$zip.GetEntry($name); if (-not $entry) { throw ('Missing SDK file: '+$name) }; [IO.Compression.ZipFileExtensions]::ExtractToFile($entry,(Join-Path $OutputDirectory $files[$name]),$true) }
} finally { $zip.Dispose() }
$destination=Join-Path $OutputDirectory 'APC40 Bridge.exe'
$arguments=@('/nologo','/target:winexe','/platform:x64','/optimize+','/utf8output',('/out:'+$destination),('/win32icon:'+(Join-Path $PSScriptRoot 'ui/bridge.ico')),('/resource:'+(Join-Path $PSScriptRoot 'ui/apc40-top.jpg')+',ApcBridge.ControllerTop.jpg'))
foreach ($name in @('System','System.Core','System.Drawing','System.Windows.Forms','System.Web.Extensions','System.IO.Compression','System.IO.Compression.FileSystem')) { $arguments+=('/reference:'+$name+'.dll') }
foreach ($name in @('Microsoft.Web.WebView2.Core.dll','Microsoft.Web.WebView2.WinForms.dll')) { $arguments+=('/reference:'+(Join-Path $OutputDirectory $name)) }
foreach ($name in @('BridgeManager.cs','ControllerEditor.cs','VisualizerPage.cs')) { $arguments+=(Join-Path $PSScriptRoot ('ui/'+$name)) }
& $compiler $arguments
if ($LASTEXITCODE -ne 0) { throw 'Could not build the app.' }
Write-Output $destination

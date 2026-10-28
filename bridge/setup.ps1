param([switch]$Silent, [ValidateSet('','on','off')][string]$Autostart='', [switch]$NoPopup, [switch]$PrepareOnly)
$OutputEncoding = [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
# APC40 Bridge - setup and launch. Open APC40 Bridge.exe.
$ErrorActionPreference = 'Continue'   # Avoid treating Python/winget stderr as fatal in PS 5.1
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Log  = Join-Path $Here 'setup.log'
function Say([string]$t) { if (-not $Silent) { Write-Host $t }; Add-Content -Path $Log -Value ("{0} {1}" -f (Get-Date -Format s), $t) -Encoding UTF8 }
function Popup([string]$t) { if ($NoPopup) { Say $t; return }; Add-Type -AssemblyName PresentationFramework; [void][System.Windows.MessageBox]::Show($t, 'APC40 Bridge') }
function Fail([string]$t) { Say "ERROR: $t"; Popup "ERROR: $t"; exit 1 }

# ---------- autostart (same backend as the control panel)
if ($Autostart -ne '') {
    $result = & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $Here 'manage.ps1') -Action ('autostart-' + $Autostart)
    if ($LASTEXITCODE -ne 0) { Fail ($result -join ' ') }
    Popup ('Autostart ' + $Autostart)
    exit 0
}

# ---------- 1) Python
. (Join-Path $Here 'runtime.ps1')
$Py = Find-BridgePython
if (-not $Py) {
    Say 'Python not found. Installing Python 3.12 for your user account...'
    $done = $false
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        & winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements | Out-Null
        $Py = Find-BridgePython; $done = [bool]$Py
    }
    if (-not $done) {
        $inst = Join-Path $env:TEMP 'python-3.12.7-amd64.exe'
        Say 'Downloading the installer from python.org...'
        Invoke-WebRequest -UseBasicParsing 'https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe' -OutFile $inst
        Start-Process -FilePath $inst -ArgumentList '/quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0' -WindowStyle Hidden -Wait
        $Py = Find-BridgePython
    }
    if (-not $Py) { Fail 'Could not install Python. Install it manually from python.org, then run setup again.' }
}
Save-BridgePython $Py
Say "Python: $Py"
$PyW = Join-Path (Split-Path $Py) 'pythonw.exe'
if (-not (Test-Path $PyW)) { $PyW = $Py }

# ---------- 2) libraries
& $Py -c "import mido, rtmidi" 2>$null
if ($LASTEXITCODE -ne 0) {
    Say 'Installing mido and python-rtmidi...'
    & $Py -m ensurepip --user 2>$null | Out-Null
    & $Py -m pip install --user --disable-pip-version-check --quiet mido python-rtmidi
    & $Py -c "import mido, rtmidi" 2>$null
    if ($LASTEXITCODE -ne 0) { Fail 'Could not install mido / python-rtmidi. Check your internet connection.' }
}

# ---------- 3) loopMIDI
$LoopExe = @("${env:ProgramFiles(x86)}\Tobias Erichsen\loopMIDI\loopMIDI.exe", "$env:ProgramFiles\Tobias Erichsen\loopMIDI\loopMIDI.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $LoopExe) {
    Say 'loopMIDI not found. Installing...'
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        & winget install -e --id TobiasErichsen.loopMIDI --silent --accept-package-agreements --accept-source-agreements | Out-Null
    }
    $LoopExe = @("${env:ProgramFiles(x86)}\Tobias Erichsen\loopMIDI\loopMIDI.exe", "$env:ProgramFiles\Tobias Erichsen\loopMIDI\loopMIDI.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $LoopExe) {
        Start-Process 'https://www.tobias-erichsen.de/software/loopmidi.html'
        Fail 'Install loopMIDI from the page that just opened, then run setup again.'
    }
}
if (-not (Get-Process loopMIDI -ErrorAction SilentlyContinue)) { Start-Process $LoopExe -WindowStyle Hidden; Start-Sleep -Seconds 3 }

# ---------- 4) virtual ports
Set-Location $Here
$r = & $Py apc_bridge.py --check-ports
if ($r -ne 'PORTS_OK') {
    if ($NoPopup) { Fail 'Create APC VIRT A and APC VIRT B in loopMIDI, then run setup again.' }
    if (-not $Silent) {
        Popup "Create 2 ports in loopMIDI (enter each name in 'New port-name' and click +):`n`n   APC VIRT A`n   APC VIRT B`n`nEnable 'Autostart' in loopMIDI. Then click OK; setup will wait for the ports to appear."
    }
    $deadline = (Get-Date).AddMinutes(5)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 3
        $r = & $Py apc_bridge.py --check-ports
        if ($r -eq 'PORTS_OK') { break }
    }
    if ($r -ne 'PORTS_OK') { Fail "loopMIDI ports are missing ($r)." }
}
Say 'loopMIDI ports OK.'

# ---------- 5) Resolume: APC40 via virtual ports
$r = & $Py apc_bridge.py --patch-resolume
$patchExit = $LASTEXITCODE
if (($patchExit -notin @(0,1,2)) -or ($patchExit -eq 1 -and $r -notmatch 'RESOLUME_PREFS_NOT_FOUND') -or ($patchExit -eq 2 -and $r -notmatch 'RESOLUME_RUNNING')) { Fail 'Could not read Resolume settings. Check the Setup log.' }
Say "Resolume: $r"
if ($r -match 'RESOLUME_RUNNING') {
    Popup "Resolume Arena is running. Close Arena, then run setup again to update its MIDI settings.`n`n(Arena would overwrite these changes when closing.)"
    if ($NoPopup) { exit 2 }; exit 0
}
if ($r -match 'RESOLUME_PREFS_NOT_FOUND' -and $NoPopup) { Fail 'Launch and close Arena once to create its settings, then run setup again.' }
if ($r -match 'RESOLUME_PREFS_NOT_FOUND') { Say 'Resolume settings not found. In Arena > Preferences > MIDI, enable APC VIRT A input and APC VIRT B output, and disable APC40 mkII.' }

# ---------- 5b) sample Resolume MIDI preset (only if missing)
$PresetSrc = Join-Path $Here 'resolume'
if (-not (Test-Path -LiteralPath $PresetSrc)) { $PresetSrc = Join-Path (Split-Path $Here -Parent) 'resolume' }
$PresetDst = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Resolume Arena\Shortcuts\MIDI'
if ((Test-Path $PresetSrc) -and (Test-Path $PresetDst)) {
    Get-ChildItem $PresetSrc -Filter *.xml | ForEach-Object {
        $t = Join-Path $PresetDst $_.Name
        if (-not (Test-Path $t)) { Copy-Item $_.FullName $t; Say "MIDI preset copied: $($_.Name)" }
    }
}

if ($PrepareOnly) { Say 'Setup complete.'; exit 0 }

# ---------- 6) start watching Arena (in the background, without a window)
$result = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Here 'manage.ps1') -Action start
if ($LASTEXITCODE -ne 0) { Fail ($result -join ' ') }
Say 'The bridge is running in the background and will activate with Resolume Arena.'
if (-not $Silent) { Popup "Done. The bridge is running in the background and will activate with Resolume Arena.`n`nIn Arena, select the 'APC40 BRIDGE EXAMPLE' MIDI preset (or your own preset set to Any device).`nLog: bridge.log in this folder." }

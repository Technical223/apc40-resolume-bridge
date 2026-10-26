param([switch]$Silent, [ValidateSet('','on','off')][string]$Autostart='', [switch]$NoPopup, [switch]$PrepareOnly)
$OutputEncoding = [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
# APC40 Bridge - instalace a spusteni. Pousti START.bat.
$ErrorActionPreference = 'Continue'   # PS 5.1 by jinak padal na stderr z pythonu/wingetu
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Log  = Join-Path $Here 'setup.log'
function Say([string]$t) { if (-not $Silent) { Write-Host $t }; Add-Content -Path $Log -Value ("{0} {1}" -f (Get-Date -Format s), $t) -Encoding UTF8 }
function Popup([string]$t) { if ($NoPopup) { Say $t; return }; Add-Type -AssemblyName PresentationFramework; [void][System.Windows.MessageBox]::Show($t, 'APC40 Bridge') }
function Fail([string]$t) { Say "CHYBA: $t"; Popup "CHYBA: $t"; exit 1 }

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
    Say 'Python nenalezen, instaluji Python 3.12 (jen pro tvého uživatele)...'
    $done = $false
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        & winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements | Out-Null
        $Py = Find-BridgePython; $done = [bool]$Py
    }
    if (-not $done) {
        $inst = Join-Path $env:TEMP 'python-3.12.7-amd64.exe'
        Say 'Stahuji instalátor z python.org...'
        Invoke-WebRequest -UseBasicParsing 'https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe' -OutFile $inst
        Start-Process -FilePath $inst -ArgumentList '/quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0' -WindowStyle Hidden -Wait
        $Py = Find-BridgePython
    }
    if (-not $Py) { Fail 'Python se nepodařilo nainstalovat. Nainstaluj ho ručně z python.org a spusť START znovu.' }
}
Save-BridgePython $Py
Say "Python: $Py"
$PyW = Join-Path (Split-Path $Py) 'pythonw.exe'
if (-not (Test-Path $PyW)) { $PyW = $Py }

# ---------- 2) knihovny
& $Py -c "import mido, rtmidi" 2>$null
if ($LASTEXITCODE -ne 0) {
    Say 'Instaluji knihovny mido a python-rtmidi...'
    & $Py -m ensurepip --user 2>$null | Out-Null
    & $Py -m pip install --user --disable-pip-version-check --quiet mido python-rtmidi
    & $Py -c "import mido, rtmidi" 2>$null
    if ($LASTEXITCODE -ne 0) { Fail 'Knihovny mido / python-rtmidi se nenainstalovaly (je připojený internet?).' }
}

# ---------- 3) loopMIDI
$LoopExe = @("${env:ProgramFiles(x86)}\Tobias Erichsen\loopMIDI\loopMIDI.exe", "$env:ProgramFiles\Tobias Erichsen\loopMIDI\loopMIDI.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $LoopExe) {
    Say 'loopMIDI nenalezen, instaluji...'
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        & winget install -e --id TobiasErichsen.loopMIDI --silent --accept-package-agreements --accept-source-agreements | Out-Null
    }
    $LoopExe = @("${env:ProgramFiles(x86)}\Tobias Erichsen\loopMIDI\loopMIDI.exe", "$env:ProgramFiles\Tobias Erichsen\loopMIDI\loopMIDI.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $LoopExe) {
        Start-Process 'https://www.tobias-erichsen.de/software/loopmidi.html'
        Fail 'Nainstaluj loopMIDI (otevřel jsem stránku) a spusť START znovu.'
    }
}
if (-not (Get-Process loopMIDI -ErrorAction SilentlyContinue)) { Start-Process $LoopExe -WindowStyle Hidden; Start-Sleep -Seconds 3 }

# ---------- 4) virtuální porty
Set-Location $Here
$r = & $Py apc_bridge.py --check-ports
if ($r -ne 'PORTS_OK') {
    if ($NoPopup) { Fail 'V loopMIDI vytvor porty APC VIRT A a APC VIRT B, potom zopakuj pripravu.' }
    if (-not $Silent) {
        Popup "V okně loopMIDI vytvoř 2 porty (napiš název do 'New port-name' a klikni +):`n`n   APC VIRT A`n   APC VIRT B`n`nV loopMIDI zaškrtni 'Autostart'. Pak klikni OK, počkám, až se porty objeví."
    }
    $deadline = (Get-Date).AddMinutes(5)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 3
        $r = & $Py apc_bridge.py --check-ports
        if ($r -eq 'PORTS_OK') { break }
    }
    if ($r -ne 'PORTS_OK') { Fail "Porty v loopMIDI chybí ($r)." }
}
Say 'loopMIDI porty OK.'

# ---------- 5) Resolume: APC40 přes virtuální porty
$r = & $Py apc_bridge.py --patch-resolume
$patchExit = $LASTEXITCODE
if (($patchExit -notin @(0,1,2)) -or ($patchExit -eq 1 -and $r -notmatch 'RESOLUME_PREFS_NOT_FOUND') -or ($patchExit -eq 2 -and $r -notmatch 'RESOLUME_RUNNING')) { Fail 'Nastaveni Resolume se nepodarilo precist. Podivej se do logu pripravy.' }
Say "Resolume: $r"
if ($r -match 'RESOLUME_RUNNING') {
    Popup "Resolume Arena běží. Nastavení MIDI v Resolume upravím, až ji zavřeš:`nzavři Arenu a spusť START znovu.`n`n(Arena by změnu při zavření přepsala.)"
    if ($NoPopup) { exit 2 }; exit 0
}
if ($r -match 'RESOLUME_PREFS_NOT_FOUND' -and $NoPopup) { Fail 'Nejdrive jednou spust a zavri Arenu, aby vzniklo jeji nastaveni. Pak zopakuj pripravu.' }
if ($r -match 'RESOLUME_PREFS_NOT_FOUND') { Say 'Nastavení Resolume nenalezeno - v Arena > Preferences > MIDI zapni vstup APC VIRT A a výstup APC VIRT B, APC40 mkII vypni.' }

# ---------- 5b) ukázkový MIDI preset do Resolume (jen když tam ještě není)
$PresetSrc = Join-Path $Here 'resolume'
if (-not (Test-Path -LiteralPath $PresetSrc)) { $PresetSrc = Join-Path (Split-Path $Here -Parent) 'resolume' }
$PresetDst = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Resolume Arena\Shortcuts\MIDI'
if ((Test-Path $PresetSrc) -and (Test-Path $PresetDst)) {
    Get-ChildItem $PresetSrc -Filter *.xml | ForEach-Object {
        $t = Join-Path $PresetDst $_.Name
        if (-not (Test-Path $t)) { Copy-Item $_.FullName $t; Say "MIDI preset nakopírován: $($_.Name)" }
    }
}

if ($PrepareOnly) { Say 'Priprava dokoncena.'; exit 0 }

# ---------- 6) spustit hlídání Areny (na pozadí, bez okna)
$result = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Here 'manage.ps1') -Action start
if ($LASTEXITCODE -ne 0) { Fail ($result -join ' ') }
Say 'Bridge běží na pozadí a zapne se, jakmile poběží Resolume Arena.'
if (-not $Silent) { Popup "Hotovo. Bridge běží na pozadí a zapne se s Resolume Arena.`n`nV Areně vyber MIDI preset 'APC40 BRIDGE EXAMPLE' (nebo svůj, nastavený na libovolné zařízení).`nLog: bridge.log v této složce." }

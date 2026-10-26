param([ValidateSet('status','start','stop','autostart-on','autostart-off','shortcut','restore')][string]$Action='status')
$OutputEncoding = [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$ErrorActionPreference = 'Stop'
$Here = $PSScriptRoot
. (Join-Path $Here 'runtime.ps1')
. (Join-Path $Here 'stop_bridge.ps1')
$StartupLink = Join-Path ([Environment]::GetFolderPath('Startup')) 'APC40 Bridge.lnk'
function Find-RunningBridge {
    $file = Join-Path $Here 'bridge.pid'
    if (-not (Test-Path -LiteralPath $file)) { return $null }
    $bridgeProcessId = 0
    if (-not [int]::TryParse([IO.File]::ReadAllText($file).Trim(), [ref]$bridgeProcessId)) { return $null }
    if ($bridgeProcessId -le 0) { return $null }
    $p = Get-CimInstance Win32_Process -Filter ("ProcessId = {0}" -f $bridgeProcessId)
    if ($p -and $p.Name -in @('python.exe','pythonw.exe') -and
        (Test-BridgeCommandLine -CommandLine $p.CommandLine -ScriptPath (Join-Path $Here 'apc_bridge.py'))) { return $p }
    return $null
}
function New-BridgeShortcut([string]$Path, [string]$Arguments) {
    $exe = Join-Path $Here 'APC40 Bridge.exe'
    if (-not (Test-Path -LiteralPath $exe)) { throw 'Aplikace chybi. Spust nejdrive build-ui.ps1.' }
    $shell = New-Object -ComObject WScript.Shell
    $link = $shell.CreateShortcut($Path)
    $link.TargetPath = $exe
    $link.Arguments = $Arguments
    $link.WorkingDirectory = $Here
    $link.IconLocation = "$exe,0"
    $link.Description = 'APC40 Bridge - ovladani a sprava'
    $link.Save()
}
$guard = $null
$ownsGuard = $false
try {
    if ($Action -ne 'status') {
        $sha = [Security.Cryptography.SHA256]::Create()
        try { $hash = [BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($Here.ToLowerInvariant()))).Replace('-','') }
        finally { $sha.Dispose() }
        $guard = New-Object Threading.Mutex($false, ("Local\APC40BridgeManager_" + $hash))
        try { $ownsGuard = $guard.WaitOne(10000) } catch [Threading.AbandonedMutexException] { $ownsGuard = $true }
        if (-not $ownsGuard) { throw 'Prave probiha jina operace. Zkus to za chvili.' }
    }
    switch ($Action) {
        'status' {
            $py = Find-BridgePython
            $cfg = Get-Content -Raw -LiteralPath (Join-Path $Here 'config.json') | ConvertFrom-Json
            $ports = @{dependencies_ready=$false; apc_ready=$false; virtual_ready=$false; error='Python neni pripraveny.'}
            if ($py) {
                try {
                    $raw = & $py (Join-Path $Here 'apc_bridge.py') --status-json 2>$null
                    if ($LASTEXITCODE -eq 0) { $ports = $raw | ConvertFrom-Json }
                } catch { $ports.error = $_.Exception.Message }
            }
            $arenaName = [IO.Path]::GetFileNameWithoutExtension($cfg.arena_process)
            $running = Find-RunningBridge
            @{
                ok=$true; bridge_running=[bool]$running; arena_running=[bool](Get-Process -Name $arenaName -ErrorAction SilentlyContinue)
                loopmidi_running=[bool](Get-Process loopMIDI -ErrorAction SilentlyContinue)
                python_ready=[bool]$py; dependencies_ready=[bool]$ports.dependencies_ready
                apc_ready=[bool]$ports.apc_ready; virtual_ready=[bool]$ports.virtual_ready
                autostart=(Test-Path -LiteralPath $StartupLink); port_error=$ports.error
                preferences_ready=[bool]$ports.preferences_ready
                pid=$(if ($running) { $running.ProcessId } else { 0 })
            } | ConvertTo-Json -Compress
        }
        'start' {
            if (Find-RunningBridge) { @{ok=$true; message='Bridge uz bezi.'} | ConvertTo-Json -Compress; break }
            $py = Find-BridgePython
            if (-not $py) { throw 'Nejdrive klikni na Pripravit instalaci.' }
            & $py -c "import mido,rtmidi" 2>$null
            if ($LASTEXITCODE -ne 0) { throw 'Chybi MIDI knihovny. Klikni na Pripravit instalaci.' }
            Save-BridgePython $py
            $loop = @("${env:ProgramFiles(x86)}\Tobias Erichsen\loopMIDI\loopMIDI.exe", "$env:ProgramFiles\Tobias Erichsen\loopMIDI\loopMIDI.exe") | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
            if (-not (Get-Process loopMIDI -ErrorAction SilentlyContinue)) {
                if (-not $loop) { throw 'Chybi loopMIDI. Klikni na Pripravit instalaci.' }
                Start-Process -FilePath $loop -WindowStyle Hidden | Out-Null
            }
            Stop-BridgeProcess -Directory $Here
            $pyw = Join-Path (Split-Path $py) 'pythonw.exe'
            if (-not (Test-Path -LiteralPath $pyw)) { $pyw = $py }
            $child = Start-Process -FilePath $pyw -ArgumentList ("`"" + (Join-Path $Here 'apc_bridge.py') + "`" --watch") -WorkingDirectory $Here -WindowStyle Hidden -PassThru
            Start-Sleep -Milliseconds 1200
            if ($child.HasExited -or -not (Find-RunningBridge)) { throw 'Bridge se nespustil. Podivej se do provozniho logu.' }
            @{ok=$true; message='Bridge spusten. Aktivuje se s Arenou.'} | ConvertTo-Json -Compress
        }
        'stop' { Stop-BridgeProcess -Directory $Here; @{ok=$true; message='Bridge zastaven.'} | ConvertTo-Json -Compress }
        'autostart-on' { New-BridgeShortcut $StartupLink '--autostart'; @{ok=$true; message='Automaticke spousteni zapnuto.'} | ConvertTo-Json -Compress }
        'autostart-off' { if (Test-Path -LiteralPath $StartupLink) { Remove-Item -LiteralPath $StartupLink }; @{ok=$true; message='Automaticke spousteni vypnuto.'} | ConvertTo-Json -Compress }
        'shortcut' { New-BridgeShortcut (Join-Path ([Environment]::GetFolderPath('Desktop')) 'APC40 Bridge.lnk') ''; @{ok=$true; message='Zastupce byl pridan na plochu.'} | ConvertTo-Json -Compress }
        'restore' {
            $py = Find-BridgePython
            if (-not $py) { throw 'Python neni pripraveny.' }
            $result = & $py (Join-Path $Here 'apc_bridge.py') --restore-resolume 2>&1
            if ($LASTEXITCODE -ne 0) { throw ('Obnoveni nastaveni neni mozne: ' + ($result -join ' ')) }
            if (-not ($result -match 'RESTORED')) { throw 'Zaloha puvodniho nastaveni nebyla nalezena.' }
            Stop-BridgeProcess -Directory $Here
            if (Test-Path -LiteralPath $StartupLink) { Remove-Item -LiteralPath $StartupLink }
            @{ok=$true; message='Puvodni MIDI nastaveni obnoveno. Bridge a autostart jsou vypnute.'} | ConvertTo-Json -Compress
        }
    }
} catch {
    $message = $_.Exception.Message
    try { Add-Content -LiteralPath (Join-Path $Here 'management.log') -Encoding UTF8 -Value ((Get-Date -Format s) + ' ERROR ' + $message) } catch {}
    @{ok=$false; message=$message} | ConvertTo-Json -Compress
    exit 1
} finally {
    if ($guard) { if ($ownsGuard) { $guard.ReleaseMutex() }; $guard.Dispose() }
}

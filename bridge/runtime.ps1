# Shared runtime discovery. Do not install anything while checking status.
function Find-BridgePython {
    $bundled = Join-Path $PSScriptRoot 'runtime\python.exe'
    if (Test-Path -LiteralPath $bundled) { return $bundled }
    $cache = Join-Path $PSScriptRoot 'runtime.json'
    if (Test-Path -LiteralPath $cache) {
        try {
            $cached = (Get-Content -Raw -LiteralPath $cache | ConvertFrom-Json).python
            if ($cached -and (Test-Path -LiteralPath $cached)) { return [string]$cached }
        } catch {}
    }
    $candidates = @()
    try { $p = & py -3 -c "import sys;print(sys.executable)" 2>$null; if ($LASTEXITCODE -eq 0 -and $p) { $candidates += $p.Trim() } } catch {}
    try { $g = Get-Command python -ErrorAction Stop; if ($g.Source -notmatch 'WindowsApps') { $candidates += $g.Source } } catch {}
    $candidates += Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe" -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | ForEach-Object FullName
    $candidates += Get-ChildItem "$env:ProgramFiles\Python3*\python.exe" -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | ForEach-Object FullName
    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (-not (Test-Path -LiteralPath $candidate)) { continue }
        try {
            $ok = & $candidate -c "import sys;print(int(sys.version_info>=(3,9)))" 2>$null
            if ($LASTEXITCODE -eq 0 -and $ok -eq '1') { return $candidate }
        } catch {}
    }
    return $null
}
function Save-BridgePython([string]$Python) {
    @{python=$Python} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'runtime.json') -Encoding UTF8
}

# loopMIDI reads these per-user port names at startup. Only add missing names.
function Initialize-BridgeMidiPorts {
    $cfg = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'config.json') | ConvertFrom-Json
    $toPort = if ($cfg.to_resolume_port) { [string]$cfg.to_resolume_port } else { 'APC VIRT A' }
    $fromPort = if ($cfg.from_resolume_port) { [string]$cfg.from_resolume_port } else { 'APC VIRT B' }
    $names = @($toPort, $fromPort)
    if (($names | Where-Object { [string]::IsNullOrWhiteSpace($_) }).Count -or $names[0] -eq $names[1]) { throw 'Choose two different MIDI port names in Settings.' }
    $key = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey('Software\Tobias Erichsen\loopMIDI\Ports')
    try {
        foreach ($name in $names) {
            if ($null -eq $key.GetValue($name, $null)) {
                $key.SetValue($name, 1, [Microsoft.Win32.RegistryValueKind]::DWord)
                Write-Output $name
            }
        }
    } finally { $key.Dispose() }
}

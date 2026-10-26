# Shared runtime discovery. Do not install anything while checking status.
function Find-BridgePython {
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

# Shared by setup.ps1 and STOP.bat. Compatible with Windows PowerShell 5.1.
function Test-BridgeCommandLine {
    param([string]$CommandLine, [string]$ScriptPath)
    # Only the exact script in this directory, as the first Python argument.
    $scriptArg = '(?:"' + [regex]::Escape($ScriptPath) + '"|' + [regex]::Escape($ScriptPath) + ')'
    $pattern = '^(?:"[^"]+"|\S+)\s+' + $scriptArg + '\s+--(?:watch|run)\s*$'
    return $CommandLine -match $pattern
}

function Stop-BridgeProcess {
    param([Parameter(Mandatory=$true)][string]$Directory)
    $pidFile = Join-Path $Directory 'bridge.pid'
    if (-not (Test-Path -LiteralPath $pidFile)) { return }
    $original = [System.IO.File]::ReadAllText($pidFile).Trim()
    $bridgeProcessId = 0
    if ([int]::TryParse($original, [ref]$bridgeProcessId) -and $bridgeProcessId -gt 0) {
        $process = Get-Process -Id $bridgeProcessId -ErrorAction SilentlyContinue
        if ($process) {
            try {
                # Keep a handle to this process instance; do not kill by a recycled PID.
                $null = $process.Handle
                $info = Get-CimInstance Win32_Process -Filter ("ProcessId = {0}" -f $bridgeProcessId) -ErrorAction Stop
                $scriptPath = [System.IO.Path]::GetFullPath((Join-Path $Directory 'apc_bridge.py'))
                $sameStart = $info -and [math]::Abs(($info.CreationDate.ToUniversalTime() - $process.StartTime.ToUniversalTime()).TotalMilliseconds) -lt 1
                if ($sameStart -and $process.ProcessName -in @('python','pythonw') -and
                    (Test-BridgeCommandLine -CommandLine $info.CommandLine -ScriptPath $scriptPath)) {
                    $process.Kill()
                    if (-not $process.WaitForExit(5000)) { throw 'Bridge did not stop within 5 seconds.' }
                } else {
                    Write-Warning 'The stale PID does not belong to this bridge; the process was left unchanged.'
                }
            } catch {
                # Do not start a second bridge when identity/access cannot be verified.
                throw
            } finally {
                $process.Dispose()
            }
        }
    }
    # A concurrently started bridge may have replaced the PID file.
    if ((Test-Path -LiteralPath $pidFile) -and
        [System.IO.File]::ReadAllText($pidFile).Trim() -eq $original) {
        Remove-Item -LiteralPath $pidFile -ErrorAction Stop
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    try { Stop-BridgeProcess -Directory $PSScriptRoot; Write-Host 'Stopped.' }
    catch { Write-Error $_; exit 1 }
}

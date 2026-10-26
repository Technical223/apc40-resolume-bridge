"""Integration tests: only disposable child processes are used."""
import base64
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HELPER = Path(__file__).resolve().parents[1] / "bridge" / "stop_bridge.ps1"
if not HELPER.exists():
    HELPER = Path(__file__).with_name("stop_bridge.ps1")
def quote(value):
    return "'" + str(value).replace("'", "''") + "'"
def run_ps(code):
    encoded = base64.b64encode(code.encode("utf-16-le")).decode("ascii")
    return subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive",
                           "-EncodedCommand", encoded], capture_output=True, text=True, check=True)
def stop(folder):
    return run_ps("$ErrorActionPreference='Stop'; . " + quote(HELPER) +
                  "; Stop-BridgeProcess -Directory " + quote(folder))

def main():
    with tempfile.TemporaryDirectory(prefix="bridge test ' ", dir=Path(__file__).parent) as tmp:
        folder = Path(tmp)
        script = folder / "apc_bridge.py"
        script.write_text("import time; time.sleep(120)", encoding="utf-8")
        pidfile = folder / "bridge.pid"
        foreign = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
        own = subprocess.Popen([sys.executable, str(script), "--watch"])
        other = subprocess.Popen([sys.executable, str(script), "--list-ports"])
        try:
            pidfile.write_text(str(foreign.pid))
            stop(folder)
            assert foreign.poll() is None, "Unrelated Python was killed"
            print("PASS: stale PID of unrelated Python process left alive")
            pidfile.write_text(str(other.pid))
            stop(folder)
            assert other.poll() is None, "Non-runtime script mode was killed"
            print("PASS: same script with a non-runtime argument left alive")
            pidfile.write_text("invalid PID")
            stop(folder)
            assert not pidfile.exists()
            print("PASS: malformed PID file safely cleared")
            pidfile.write_text(str(own.pid))
            stop(folder)
            own.wait(timeout=5)
            assert not pidfile.exists()
            assert foreign.poll() is None and other.poll() is None
            print("PASS: exact bridge child stopped, paths with spaces/apostrophe work")
            pidfile.write_text(str(own.pid))
            stop(folder)
            assert not pidfile.exists()
            print("PASS: exited process PID safely cleared")
        finally:
            for child in (foreign, own, other):
                if child.poll() is None: child.kill()
                child.wait(timeout=5)
    # Parse all PowerShell sources using Windows PowerShell 5.1.
    for name in ("setup.ps1", "stop_bridge.ps1"):
        result = run_ps("$tokens=$null; $errors=$null; [void][System.Management.Automation.Language.Parser]::ParseFile(" +
                        quote(HELPER.with_name(name)) + ",[ref]$tokens,[ref]$errors); if($errors.Count){throw ($errors | Out-String)}")
    print("PASS: Windows PowerShell parser accepts both scripts")

if __name__ == "__main__": main()

"""Native-only smoke checks. Creates temporary virtual MIDI ports, never physical APC ports."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch
import uuid
import zipfile

import mac_bridge as mac

if sys.platform != "darwin":
    raise SystemExit("Run this smoke check on macOS")

subprocess.run(["/bin/sh", "-n", str(mac.HERE / "launcher.sh")], check=True)
with tempfile.TemporaryDirectory() as temp:
    scripts = []
    def capture(args, **kwargs):
        scripts.append(args[2])
        return subprocess.CompletedProcess(args, 0, stdout="Quit\n")
    with patch.object(mac.subprocess, "run", side_effect=capture):
        mac.dialog("CI syntax check")
        assert mac.menu("CI syntax check") == "Quit"
    for i, script in enumerate(scripts):
        subprocess.run(["/usr/bin/osacompile", "-o", str(Path(temp) / f"dialog-{i}.scpt"), "-e", script], check=True)

import mido
mido.set_backend(mac.BACKEND, load=True)
name = "APC40-preview-CI-" + uuid.uuid4().hex
with mido.open_input(name, virtual=True) as receiver:
    output_name = mac.select_port(mido.get_output_names(), name)
    with mido.open_output(output_name) as sender:
        message = mido.Message("control_change", channel=0, control=48, value=63)
        sender.send(message)
        received = None
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            received = receiver.poll()
            if received is not None:
                break
            time.sleep(0.02)
        assert received == message, (received, message)
print("CoreMIDI virtual-port roundtrip and AppleScript compilation passed")

# No physical device is attached in CI: verify the failure report still exists.
result = subprocess.run([sys.executable, str(mac.HERE / "mac_bridge.py"), "--test", "--seconds", "1"],
                        capture_output=True, text=True, timeout=30)
assert result.returncode == 0, result.stdout + result.stderr
last = mac.DATA / "last-test.json"
details = json.loads(last.read_text())
assert details["test"]["outcome"] == "no_connection", details
assert details["test"]["connections"] == 0
exports = list((Path.home() / "Desktop").glob("APC40-macOS-debug-*.zip"))
exports += list((mac.DATA / "reports").glob("APC40-macOS-debug-*.zip"))
assert exports, "No diagnostic ZIP was created"
with zipfile.ZipFile(max(exports, key=lambda p: p.stat().st_mtime)) as archive:
    assert "report.json" in archive.namelist()
    assert "last-test.json" in archive.namelist()
print("No-hardware test produced a diagnostic ZIP successfully")

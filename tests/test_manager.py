"""Windows integration tests use a fake watcher, never the real APC."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
@unittest.skipUnless(os.name == "nt", "Windows management scripts")
class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="APC manager ' ")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        for name in ("manage.ps1", "runtime.ps1", "stop_bridge.ps1"):
            shutil.copy2(ROOT / "bridge" / name, self.home / name)
        (self.home / "runtime.json").write_text(json.dumps({"python":sys.executable}),encoding="utf-8")
        (self.home / "config.json").write_text(json.dumps({"arena_process":"NonexistentAPCTest.exe"}),encoding="utf-8")
        (self.home / "apc_bridge.py").write_text(
            'import sys,json,os,time\nfrom pathlib import Path\n'
            'if "--status-json" in sys.argv:\n'
            ' print(json.dumps(dict(dependencies_ready=True,apc_ready=False,virtual_ready=False,error="")))\n'
            'elif "--watch" in sys.argv:\n'
            ' Path(__file__).with_name("bridge.pid").write_text(str(os.getpid()))\n'
            ' time.sleep(90)\n', encoding="utf-8")
        self.addCleanup(lambda: self.call("stop", check=False))
    def call(self, action, check=True):
        result=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-ExecutionPolicy","Bypass",
                               "-File",str(self.home/"manage.ps1"),"-Action",action],
                              capture_output=True, encoding="utf-8",timeout=30)
        if check: self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        return result
    def test_status_does_not_start_watcher(self):
        status=json.loads(self.call("status").stdout)
        self.assertFalse(status["bridge_running"])
        self.assertFalse(status["apc_ready"])
        self.assertFalse((self.home/"bridge.pid").exists())
    def test_start_is_idempotent_then_stop_releases_process(self):
        try: __import__("mido"); __import__("rtmidi")
        except ImportError: self.skipTest("Live dependency check needs prepared Python")
        if not subprocess.run(["tasklist","/FI","IMAGENAME eq loopMIDI.exe","/NH"],
                              capture_output=True,text=True).stdout.lower().count("loopmidi.exe"):
            self.skipTest("Requires loopMIDI already running; tests never launch it")
        self.call("start")
        first=(self.home/"bridge.pid").read_text()
        self.call("start")
        self.assertEqual((self.home/"bridge.pid").read_text(),first)
        self.assertTrue(json.loads(self.call("status").stdout)["bridge_running"])
        self.call("stop")
        self.assertFalse((self.home/"bridge.pid").exists())
    def test_invalid_config_returns_error_without_installing(self):
        (self.home/"config.json").write_text("{broken",encoding="utf-8")
        result=self.call("status",check=False)
        self.assertNotEqual(result.returncode,0)
        self.assertFalse(json.loads(result.stdout)["ok"])
        self.assertFalse((self.home/"bridge.pid").exists())

if __name__=="__main__": unittest.main()

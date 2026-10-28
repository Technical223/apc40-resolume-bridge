"""Portable macOS adapter tests: no hardware, system changes or network."""
import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

mac = module("mac_preview_test", "macos/mac_bridge.py")
package = module("mac_package_test", "macos/package_macos.py")

class MacTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name) / "runtime"
        self.data.mkdir()
        self.override = patch.object(mac, "DATA", self.data)
        self.override.start()
        self.addCleanup(self.override.stop)
        mac.EVENTS.clear()
        self.core = mac.load_core()
        self.cfg = mac.load_config(self.core)

    def test_separate_state_and_config_do_not_change_windows_defaults(self):
        self.assertEqual(self.cfg["arena_process"], "Arena")
        self.assertEqual(self.core.STATE_PATH, str(self.data / "state.json"))
        self.assertEqual(json.loads((ROOT / "bridge/config.json").read_text())["arena_process"], "Arena.exe")
        self.assertNotEqual(str(self.data / "config.json"), self.core.CFG_PATH)

    def test_exact_port_preferred_and_ambiguous_ports_refused(self):
        self.assertEqual(mac.select_port(["APC VIRT A", "Other APC VIRT A"], "APC VIRT A"), "APC VIRT A")
        self.assertEqual(mac.select_port(["IAC Driver APC VIRT A"], "APC VIRT A"), "IAC Driver APC VIRT A")
        for names in ([], ["IAC APC VIRT A", "Other APC VIRT A"]):
            with self.assertRaises(RuntimeError):
                mac.select_port(names, "APC VIRT A")
        with self.assertRaises(RuntimeError):
            mac.select_port(["APC40 VIRT"], "APC40", "VIRT")

    def test_duplicate_routes_rejected(self):
        self.cfg["from_resolume_port"] = self.cfg["to_resolume_port"]
        (self.data / "config.json").write_text(json.dumps(self.cfg))
        with self.assertRaises(ValueError):
            mac.load_config(self.core)

    def test_diagnostics_can_export_when_dependency_unavailable(self):
        with patch.object(mac, "configure_midi", side_effect=ImportError("missing MIDI backend")), patch.object(mac, "arena_running", return_value=False):
            info = mac.snapshot(self.core, self.cfg)
        self.assertFalse(info["ports_ready"])
        self.assertIn("missing MIDI backend", info["port_error"])
        self.assertNotIn("environment", info)
        self.assertNotIn("processes", info)

    def test_report_only_known_files_redacts_paths_and_preserves_last_test(self):
        (self.data / "app.log").write_text(str(Path.home()) + "/private/test /Users/other/person")
        (self.data / "secret-composition.avc").write_text("DO NOT EXPORT")
        (self.data / "last-test.json").write_text('{"test":{"connections":1}}')
        path = mac.report({"error": str(Path.home()) + "/bad"}, self.data / "exports")
        with zipfile.ZipFile(path) as archive:
            self.assertEqual(set(archive.namelist()), {"report.json", "app.log", "last-test.json", "README.txt"})
            text = archive.read("app.log").decode()
            self.assertNotIn(str(Path.home()), text)
            self.assertNotIn("/Users/other", text)
            self.assertEqual(json.loads(archive.read("last-test.json"))["test"]["connections"], 1)

    def test_event_capture_is_bounded_and_excludes_sysex(self):
        for i in range(400):
            mac.record_event("APC -> Arena", types.SimpleNamespace(type="control_change",channel=0,control=48,value=i%128), self.cfg)
        mac.record_event("APC -> Arena", types.SimpleNamespace(type="sysex", data=[1,2,3]), self.cfg)
        self.assertEqual(len(mac.event_snapshot()), 300)
        self.assertTrue(all(x["kind"] == "Hue" for x in mac.event_snapshot()))

    def test_test_closes_ports_and_reports_counts_on_stop(self):
        class Stop:
            stopped = False
            def is_set(self): return self.stopped
            def wait(self, seconds): self.stopped = True
        closed = []
        class State:
            def save(self): pass
        class Bridge:
            def __init__(self, cfg):
                self.state = State()
                self.count = {"apc>res": 3, "res>apc": 2, "dropped": 1}
            def alive(self): return True
            def close(self): closed.append(True)
        core = types.SimpleNamespace(Bridge=Bridge)
        with patch.object(mac, "configure_midi"), patch.object(mac, "routes", return_value={}):
            result = mac.run_test(core, self.cfg, 3, Stop())
        self.assertEqual(closed, [True])
        self.assertEqual(result["traffic"]["res>apc"], 2)
        self.assertEqual(result["connections"], 1)
        self.assertEqual(result["outcome"], "stopped")

    def test_package_isolated_and_executable_modes_preserved(self):
        output = package.build(self.data / "mac.zip")
        with zipfile.ZipFile(output) as archive:
            names = archive.namelist()
            self.assertFalse(any(name.endswith((".exe", ".ps1", ".bat")) for name in names))
            launcher = next(n for n in names if n.endswith("MacOS/launcher"))
            self.assertTrue(archive.getinfo(launcher).external_attr >> 16 & stat.S_IXUSR)
            core = next(n for n in names if n.endswith("core/apc_bridge.py"))
            self.assertEqual(archive.read(core), (ROOT / "bridge/apc_bridge.py").read_bytes())
            self.assertFalse(any(n.endswith(("state.json", "runtime.json", ".log")) for n in names))
        with self.assertRaises(FileExistsError):
            package.build(output)

if __name__ == "__main__": unittest.main()

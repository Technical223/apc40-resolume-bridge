import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
import threading

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bridge_under_test", ROOT / "bridge" / "apc_bridge.py")
if not spec.origin or not Path(spec.origin).exists():
    spec = importlib.util.spec_from_file_location("bridge_under_test", Path(__file__).with_name("apc_bridge.py"))
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

class FakeState:
    def __init__(self, n):
        self.hue = [0] * n
        self.color_on = [True] * n
        self.dirty = False
    def save(self): pass

class Port:
    def __init__(self, name):
        self.name = name
        self.closed = False
        self.messages = []
        self.fail = False
    def send(self, message):
        if self.fail: raise OSError("MIDI disconnected")
        self.messages.append(message)
    def close(self): self.closed = True

class Backend:
    def __init__(self, fail_open=None, fail_send=False):
        self.ports = []
        self.fail_open = fail_open
        self.fail_send = fail_send
    def open(self, name):
        if len(self.ports) + 1 == self.fail_open: raise OSError("Port busy")
        port = Port(name)
        port.fail = self.fail_send
        self.ports.append(port)
        return port
    open_input = open
    open_output = open
    @staticmethod
    def Message(kind, **values): return types.SimpleNamespace(type=kind, **values)

class StopLoop(BaseException): pass

class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.cfg = dict(b.DEFAULT_CFG, always_lit=False)
        self.backend = Backend()
        self.patches = [
            patch.dict(sys.modules, {"mido": self.backend}),
            patch.object(b, "State", FakeState),
            patch.object(b, "find_port", side_effect=lambda kind, match, exclude=None: match),
            patch.object(b, "ports_ready", return_value=True),
        ]
        for p in self.patches: p.start(); self.addCleanup(p.stop)
        self.addCleanup(lambda: None)
    def make(self):
        x = b.Bridge(self.cfg)
        self.addCleanup(x.close)
        return x
    def test_every_partial_open_failure_closes_previously_opened_ports(self):
        for number in range(1, 5):
            with self.subTest(number=number):
                self.backend.ports = []
                self.backend.fail_open = number
                with self.assertRaises(OSError): b.Bridge(self.cfg)
                self.assertTrue(all(p.closed for p in self.backend.ports))
    def test_initial_led_send_failure_closes_all_ports(self):
        self.backend.fail_send = True
        with self.assertRaises(OSError): b.Bridge(self.cfg)
        self.assertEqual(len(self.backend.ports), 4)
        self.assertTrue(all(p.closed for p in self.backend.ports))
    def test_apc_send_failure_marks_bridge_unhealthy(self):
        x = self.make()
        x.res_out.fail = True
        with self.assertLogs(level="ERROR"):
            x.on_apc(Backend.Message("control_change", channel=0, control=48, value=30))
        self.assertFalse(x.alive())
    def test_feedback_send_failure_marks_bridge_unhealthy(self):
        x = self.make()
        x.apc_out.fail = True
        with self.assertLogs(level="ERROR"):
            x.on_resolume(Backend.Message("control_change", channel=0, control=10, value=30))
        self.assertFalse(x.alive())
    def test_blink_send_failure_marks_bridge_unhealthy(self):
        x = self.make()
        x.lit[(48, 0)] = True
        x.apc_out.fail = True
        with patch.object(b.time, "sleep"), self.assertLogs(level="ERROR"):
            x._blinker()
        self.assertFalse(x.alive())
    def test_normal_messages_still_pass_both_directions(self):
        x = self.make()
        message = Backend.Message("control_change", channel=0, control=10, value=30)
        x.on_apc(message)
        x.on_resolume(message)
        self.assertIs(x.res_out.messages[-1], message)
        self.assertIs(x.apc_out.messages[-1], message)
        self.assertTrue(x.alive())
    def test_colorize_feedback_stays_intentionally_ignored(self):
        x = self.make()
        before = len(x.apc_out.messages)
        for kind, velocity in (("note_on", 0), ("note_off", 64), ("note_on", 127)):
            x.on_resolume(Backend.Message(kind, channel=0, note=32, velocity=velocity))
        self.assertEqual(x.state.color_on, [True] * 8)
        self.assertEqual(len(x.apc_out.messages), before)
        self.assertEqual(x.count["dropped"], 3)
    def test_close_is_idempotent(self):
        x = self.make()
        x.close()
        x.close()
        self.assertTrue(all(p.closed for p in self.backend.ports))
    def test_failed_bridge_is_closed_and_recreated_by_watch_loop(self):
        first = types.SimpleNamespace(
            alive=lambda: False, close=unittest.mock.Mock(),
            state=FakeState(8), count={})
        second = types.SimpleNamespace(
            alive=lambda: True, close=unittest.mock.Mock(),
            state=FakeState(8), count={})
        with patch.object(b, "Bridge", side_effect=[first, second]) as create:
            with patch.object(b.time, "sleep", side_effect=[None, None, StopLoop]):
                with self.assertRaises(StopLoop): b.run_loop(self.cfg, watch=False)
        first.close.assert_called_once()
        self.assertEqual(create.call_count, 2)

if __name__ == "__main__": unittest.main()

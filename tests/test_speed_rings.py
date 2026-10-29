import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import test_bridge as baseline

b = baseline.b
Backend = baseline.Backend
RealState = b.State
RealAnimator = b.Bridge._speed_animator

class SpeedTests(unittest.TestCase):
    make = baseline.BridgeTests.make
    def setUp(self):
        baseline.BridgeTests.setUp(self)
        self.cfg.update(speed_ring_animation=True, sync_resolume_feedback=True)
        self.no_thread = patch.object(b.Bridge, "_speed_animator")
        self.no_thread.start()
        self.addCleanup(self.no_thread.stop)

    def test_period_endpoints_and_monotonic_mapping(self):
        self.assertEqual(b.speed_ring_period(0, self.cfg), 2)
        self.assertEqual(b.speed_ring_period(127, self.cfg), .25)
        self.assertGreater(b.speed_ring_period(30,self.cfg), b.speed_ring_period(90,self.cfg))

    def test_single_mode_protocol_and_changed_dot_only(self):
        x=self.make()
        style=[m for m in x.apc_out.messages if m.type=="control_change" and m.control in range(28,32)]
        self.assertEqual([(m.control,m.value) for m in style],[(28,1),(29,1),(30,1),(31,1)])
        before=len(x.apc_out.messages)
        x._speed_tick(0)
        self.assertEqual(len(x.apc_out.messages),before)
        x._speed_tick(2/15+.00001)
        self.assertEqual(len(x.apc_out.messages),before+4)
        self.assertEqual(x.apc_out.messages[-1].value,10)
        self.assertEqual(x.res_out.messages,[])

    def test_bounce_visits_every_led_and_reverses_at_endpoints(self):
        x = self.make()
        observed = [0]
        for unused in range(28):
            x._speed_tick(2 / 28 + 1e-8)
            observed.append(x.speed_last[0])
        self.assertEqual(observed, list(range(15)) + list(range(13, -1, -1)))
        self.assertEqual(x.res_out.messages, [])

    def test_takeover_discards_animated_baseline_then_passes_manual_values(self):
        x=self.make()
        x.state.speed["0:20"]=60
        with patch.object(b.time,"monotonic",return_value=100):
            x.on_apc(Backend.Message("control_change",channel=0,control=20,value=126))
        self.assertEqual(x.res_out.messages,[])
        self.assertEqual(x.state.speed["0:20"],60)
        self.assertEqual(x.apc_out.messages[-1].value,60)
        with patch.object(b.time,"monotonic",return_value=100.01):
            x.on_apc(Backend.Message("control_change",channel=0,control=20,value=120))
        self.assertEqual(x.res_out.messages,[])
        msg=Backend.Message("control_change",channel=0,control=20,value=61)
        with patch.object(b.time,"monotonic",return_value=100.1): x.on_apc(msg)
        self.assertIs(x.res_out.messages[-1],msg)
        self.assertEqual(x.state.speed["0:20"],61)
        target=lambda: [m for m in x.apc_out.messages if m.type=="control_change" and m.control==20]
        before=len(target())
        with patch.object(b.time,"monotonic",return_value=100.2): x._speed_tick(.1)
        self.assertEqual(len(target()),before)
        feedback=Backend.Message("control_change",channel=0,control=20,value=70)
        with patch.object(b.time,"monotonic",return_value=100.3): x.on_resolume(feedback)
        self.assertEqual(x.state.speed["0:20"],70)
        self.assertIs(x.apc_out.messages[-1],feedback)
        self.assertEqual(len(x.res_out.messages),1)
        with patch.object(b.time,"monotonic",return_value=102): x._speed_tick(.1)
        self.assertGreater(len(target()),before+1)
        with patch.object(b.time,"monotonic",return_value=102.1):
            x.on_apc(Backend.Message("control_change",channel=0,control=20,value=100))
        self.assertEqual(x.apc_out.messages[-1].value,70)
        self.assertEqual(len(x.res_out.messages),1)

    def test_idle_feedback_updates_speed_without_writing_encoder(self):
        x=self.make(); before=len(x.apc_out.messages)
        x.on_resolume(Backend.Message("control_change",channel=0,control=20,value=55))
        self.assertEqual(x.state.speed["0:20"],55)
        self.assertEqual(len(x.apc_out.messages),before)
        self.assertEqual(x.res_out.messages,[])

    def test_sync_disabled_ignores_feedback_but_owns_ring(self):
        self.cfg["sync_resolume_feedback"]=False
        x=self.make(); before=len(x.apc_out.messages)
        x.on_resolume(Backend.Message("control_change",channel=0,control=20,value=100))
        self.assertEqual(x.state.speed,{})
        self.assertEqual(len(x.apc_out.messages),before)

    def test_option_absent_leaves_passthrough_and_no_thread(self):
        self.cfg.pop("speed_ring_animation")
        x=self.make();before=len(x.apc_out.messages)
        msg=Backend.Message("control_change",channel=0,control=20,value=100)
        x.on_resolume(msg)
        self.assertEqual(len(x.apc_out.messages),before+1)
        self.assertIs(x.apc_out.messages[-1],msg)
        self.assertIsNone(x.speed_thread)

    def test_other_channel_passthrough(self):
        x=self.make()
        msg=Backend.Message("control_change",channel=1,control=20,value=99)
        x.on_resolume(msg)
        self.assertIs(x.apc_out.messages[-1],msg)
        self.assertEqual(x.state.speed,{})

    def test_custom_ccs_channel_and_invalid_config(self):
        self.cfg.update(speed_ring_ccs=[18],speed_ring_channel=2)
        x=self.make()
        self.assertEqual(x.speed_ccs,[18])
        x.on_resolume(Backend.Message("control_change",channel=2,control=18,value=80))
        self.assertEqual(x.state.speed["2:18"],80)
        for changes in [dict(speed_ring_ccs=[20,20]),dict(speed_ring_channel=16),dict(speed_ring_fastest_seconds=0),dict(speed_ring_update_hz=float("nan")),dict(apc_mode=65)]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                b.validate_speed_rings(dict(self.cfg,**changes))

    def test_save_restore_and_old_state(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(b,"State",RealState), patch.object(b,"STATE_PATH",str(Path(temp)/"state.json")):
            state=b.State(8)
            state.speed={"0:20":77};state.dirty=True;state.save()
            self.assertEqual(b.State(8).speed,{"0:20":77})
            with patch.object(b,"State",wraps=b.State):
                x=self.make()
                self.assertEqual(x.state.speed["0:20"],77)
            x.close()
            Path(b.STATE_PATH).write_text('{"hue":[20],"color_on":[false]}')
            self.assertEqual(b.State(8).speed,{})

    def test_real_thread_joins_before_ports_close(self):
        self.no_thread.stop()
        x=self.make()
        self.assertTrue(x.speed_thread.is_alive())
        x.close()
        self.assertFalse(x.speed_thread.is_alive())
        self.assertTrue(all(p.closed for p in self.backend.ports))

    def test_animation_failure_marks_connection_unhealthy(self):
        x=self.make()
        x.apc_out.fail=True
        x.speed_last=[None]*4
        with patch.object(x.speed_stop,"wait",return_value=False),self.assertLogs(level="ERROR"):
            RealAnimator(x)
        self.assertTrue(x.failed.is_set())

if __name__=="__main__": unittest.main()

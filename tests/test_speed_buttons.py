import unittest
from unittest.mock import patch
import test_bridge as baseline
b=baseline.b
Backend=baseline.Backend

class SpeedButtonTests(unittest.TestCase):
    make=baseline.BridgeTests.make
    def setUp(self):
        baseline.BridgeTests.setUp(self)
        self.cfg.update(speed_ring_animation=False,speed_button_pulse=True,sync_resolume_feedback=True)
        self.mock_thread=patch.object(b.Bridge,"_speed_animator")
        self.mock_thread.start()
        self.addCleanup(self.mock_thread.stop)

    def test_pulse_period_matches_multiplier(self):
        self.assertEqual(b.speed_button_period(0,self.cfg),1)
        self.assertEqual(b.speed_button_period(127,self.cfg),1/3)

    def test_custom_cap_compresses_the_whole_travel(self):
        self.cfg["speed_button_max_blink_hz"]=2
        self.assertEqual(b.speed_button_period(0,self.cfg),1)
        self.assertEqual(b.speed_button_period(127,self.cfg),.5)
        self.assertGreater(b.speed_button_period(100,self.cfg),b.speed_button_period(127,self.cfg))

    def test_pulse_accelerates_monotonically_and_mouse_feedback_controls_it(self):
        periods = [b.speed_button_period(v,self.cfg) for v in range(128)]
        self.assertTrue(all(a > z for a,z in zip(periods,periods[1:])))
        x=self.make()
        x.on_resolume(Backend.Message("control_change",channel=0,control=20,value=127))
        x.speed_phase[0]=0
        x.speed_last[0]=True
        before=len(x.apc_out.messages)
        x._speed_tick(.17)
        self.assertTrue(any(m.type=="note_on" and m.note==58 and m.velocity==0 for m in x.apc_out.messages[before:]))
        x.on_apc(Backend.Message("note_on",channel=0,note=58,velocity=127))
        self.assertEqual(x.state.speed["0:20"],0)
        self.assertEqual(x.speed_phase[0],0)
        x._speed_tick(.1)
        self.assertTrue(x.speed_last[0])

    def test_animation_only_writes_button_notes_and_no_repeated_frames(self):
        x=self.make()
        before=len(x.apc_out.messages)
        x._speed_tick(0)
        self.assertEqual(len(x.apc_out.messages),before)
        x._speed_tick(.51)
        frames=x.apc_out.messages[before:]
        self.assertEqual(len(frames),4)
        self.assertTrue(all(m.type=="note_on" and m.note in [58,59,60,61] and m.velocity==0 for m in frames))
        self.assertEqual(x.res_out.messages,[])
        self.assertFalse(any(m.type=="control_change" for m in x.apc_out.messages))

    def test_first_knob_move_unchanged_and_mouse_feedback_preserved(self):
        x=self.make()
        msg=Backend.Message("control_change",channel=0,control=20,value=55)
        x.on_apc(msg)
        self.assertIs(x.res_out.messages[-1],msg)
        self.assertEqual(x.state.speed["0:20"],55)
        feedback=Backend.Message("control_change",channel=0,control=20,value=99)
        x.on_resolume(feedback)
        self.assertIs(x.apc_out.messages[-1],feedback)
        self.assertEqual(x.state.speed["0:20"],99)
        self.assertEqual(len(x.res_out.messages),1)

    def test_reset_sends_one_minimum_cc_and_consumes_press_release(self):
        x=self.make()
        for i,note in enumerate([58,59,60,61]):
            x.on_apc(Backend.Message("note_on",channel=0,note=note,velocity=127))
            x.on_apc(Backend.Message("note_on",channel=0,note=note,velocity=127))
            self.assertEqual(x.res_out.messages[-1].control,20+i)
            self.assertEqual(x.res_out.messages[-1].value,0)
            self.assertEqual(x.state.speed["0:"+str(20+i)],0)
            x.on_apc(Backend.Message("note_off",channel=0,note=note,velocity=0))
        self.assertEqual(len(x.res_out.messages),4)
        self.assertTrue(all(m.type=="control_change" for m in x.res_out.messages))
        x.on_apc(Backend.Message("note_on",channel=0,note=58,velocity=127))
        x.on_apc(Backend.Message("note_on",channel=0,note=58,velocity=0))
        self.assertEqual(len(x.res_out.messages),5)

    def test_buttons_not_owned_by_general_blinker_or_old_feedback(self):
        self.cfg["always_lit"]=True
        with patch.object(b.Bridge,"_blinker"):
            x=self.make()
        for note in [58,59,60,61]:
            self.assertNotIn((note,0),x.lit)
        before=len(x.apc_out.messages)
        x.on_resolume(Backend.Message("note_on",channel=0,note=58,velocity=127))
        self.assertEqual(len(x.apc_out.messages),before)

    def test_lower_button_row_keeps_original_actions(self):
        x=self.make()
        for note in [62,63,64,65]:
            msg=Backend.Message("note_on",channel=0,note=note,velocity=127)
            x.on_apc(msg)
            self.assertIs(x.res_out.messages[-1],msg)
        self.assertEqual(len(x.res_out.messages),4)

    def test_disabled_preserves_original_button_actions(self):
        self.cfg["speed_button_pulse"]=False
        x=self.make()
        msg=Backend.Message("note_on",channel=0,note=58,velocity=127)
        x.on_apc(msg)
        self.assertIs(x.res_out.messages[-1],msg)

    def test_sync_off_preserves_static_feedback_but_not_pulse_state(self):
        self.cfg["sync_resolume_feedback"]=False
        x=self.make()
        msg=Backend.Message("control_change",channel=0,control=20,value=30)
        x.on_resolume(msg)
        self.assertIs(x.apc_out.messages[-1],msg)
        self.assertEqual(x.state.speed,{})

    def test_config_conflicts_and_notes_validated(self):
        for changes in [dict(speed_ring_animation=True),dict(speed_button_notes=[58]*4),dict(speed_button_reset_value=128),dict(speed_button_min_multiplier=0),dict(speed_button_max_blink_hz=10)]:
            self.cfg.update(changes)
            with self.assertRaises(ValueError): b.Bridge(self.cfg)
            for k in changes:self.cfg.pop(k,None)

if __name__=="__main__":unittest.main()

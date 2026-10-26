import unittest
import test_bridge as baseline
Backend = baseline.Backend
b = baseline.b

class FeedbackTests(unittest.TestCase):
    make = baseline.BridgeTests.make
    def setUp(self):
        baseline.BridgeTests.setUp(self)
        self.cfg["sync_resolume_feedback"] = True
    def test_external_hue_updates_state_pad_and_preserves_cc_through(self):
        x = self.make()
        msg = Backend.Message("control_change", channel=0, control=48, value=100)
        x.on_resolume(msg)
        self.assertEqual(x.state.hue[0], 100)
        self.assertTrue(x.state.dirty)
        self.assertIs(x.apc_out.messages[-2], msg)
        self.assertEqual(x.apc_out.messages[-1].velocity, b.hue_to_velocity(100, x.cfg))
        self.assertEqual(x.res_out.messages, [])  # No feedback loop to Arena.
    def test_mouse_colorize_off_is_velocity_three_not_zero(self):
        x = self.make()
        x.on_resolume(Backend.Message("note_on", channel=0, note=32, velocity=3))
        self.assertFalse(x.state.color_on[0])
        self.assertEqual(x.apc_out.messages[-1].velocity, 3)
        self.assertEqual(x.res_out.messages, [])
    def test_colorize_on_redraws_actual_hue_instead_of_red_feedback_colour(self):
        x = self.make()
        x.state.hue[0] = 100
        x.state.color_on[0] = False
        x.on_resolume(Backend.Message("note_on", channel=0, note=32, velocity=5))
        self.assertTrue(x.state.color_on[0])
        self.assertEqual(x.apc_out.messages[-1].velocity, b.hue_to_velocity(100, x.cfg))
        self.assertNotEqual(x.apc_out.messages[-1].velocity, 5)
    def test_hue_while_bypassed_stays_white_and_is_remembered(self):
        x = self.make()
        x.state.color_on[0] = False
        x.on_resolume(Backend.Message("control_change", channel=0, control=48, value=120))
        self.assertEqual(x.apc_out.messages[-1].velocity, 3)
        x.on_resolume(Backend.Message("note_on", channel=0, note=32, velocity=5))
        self.assertEqual(x.apc_out.messages[-1].velocity, b.hue_to_velocity(120, x.cfg))
    def test_unknown_velocities_and_note_off_do_not_toggle_state(self):
        x = self.make()
        before = len(x.apc_out.messages)
        for kind, value in (("note_on", 0), ("note_on", 127), ("note_off", 3)):
            x.on_resolume(Backend.Message(kind, channel=0, note=32, velocity=value))
        self.assertTrue(x.state.color_on[0])
        self.assertEqual(len(x.apc_out.messages), before)
    def test_all_eight_knobs_and_pads_are_independent(self):
        x = self.make()
        for i, cc in enumerate(x.knobs):
            x.on_resolume(Backend.Message("control_change", channel=0, control=cc, value=i*10))
            x.on_resolume(Backend.Message("note_on", channel=0, note=x.notes[i], velocity=3 if i%2 else 5))
        self.assertEqual(x.state.hue, list(range(0,80,10)))
        self.assertEqual(x.state.color_on, [True,False]*4)
    def test_other_channels_do_not_change_local_state(self):
        x = self.make()
        x.on_resolume(Backend.Message("control_change", channel=1, control=48, value=100))
        x.on_resolume(Backend.Message("note_on", channel=1, note=32, velocity=3))
        self.assertEqual(x.state.hue, [0]*8)
        self.assertEqual(x.state.color_on, [True]*8)
    def test_switch_off_restores_original_behaviour(self):
        x = self.make()
        x.cfg["sync_resolume_feedback"] = False
        x.on_resolume(Backend.Message("control_change", channel=0, control=48, value=100))
        x.on_resolume(Backend.Message("note_on", channel=0, note=32, velocity=3))
        self.assertEqual(x.state.hue, [0]*8)
        self.assertEqual(x.state.color_on, [True]*8)
    def test_equal_on_off_mapping_does_not_guess_state(self):
        x = self.make()
        x.cfg["color_on_feedback_velocity"] = 3
        x.on_resolume(Backend.Message("note_on", channel=0, note=32, velocity=3))
        self.assertTrue(x.state.color_on[0])
    def test_physical_pad_then_duplicate_feedback_does_not_double_toggle(self):
        x = self.make()
        x.on_apc(Backend.Message("note_on", channel=0, note=32, velocity=127))
        for _ in range(2):
            x.on_resolume(Backend.Message("note_on", channel=0, note=32, velocity=3))
        self.assertFalse(x.state.color_on[0])
        self.assertEqual(len(x.res_out.messages), 1)

if __name__ == "__main__": unittest.main()

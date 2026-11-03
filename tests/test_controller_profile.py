import unittest
import json
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch, Mock
import test_bridge as baseline
b=baseline.b
Message=baseline.Backend.Message
PROFILE_WORKER=b.Bridge._profile_worker

class ControllerProfileTests(unittest.TestCase):
    make=baseline.BridgeTests.make
    def setUp(self):
        baseline.BridgeTests.setUp(self)
        self.cfg["sync_resolume_feedback"]=True
        self.worker=patch.object(b.Bridge,"_profile_worker")
        self.worker.start()
        self.addCleanup(self.worker.stop)

    def rule(self, **values):
        rule=dict(channel=0,note=32,mode="hue",source_channel=0,source_cc=48,color=5,press="passthrough",reset_value=0,rate_min=1,rate_max=3)
        rule.update(values)
        self.cfg["control_rules"]=[rule]
        return rule

    def test_absent_profile_keeps_existing_midi_and_no_profile_worker(self):
        x=self.make()
        self.assertIsNone(x.profile_thread)
        self.assertEqual(x.profile_rules,{})

    def test_fader_drives_rgb_without_changing_original_message(self):
        self.rule(source_channel=2,source_cc=7)
        x=self.make()
        msg=Message("control_change",channel=2,control=7,value=127)
        x.on_apc(msg)
        self.assertIs(x.res_out.messages[-1],msg)
        led=[m for m in x.apc_out.messages if m.type=="note_on" and m.note==32][-1]
        self.assertEqual(led.velocity,b.hue_to_velocity(127,self.cfg))
        self.assertFalse(any(m.type=="control_change" for m in x.apc_out.messages))

    def test_mouse_feedback_updates_source_but_does_not_echo_to_arena(self):
        self.rule(source_cc=20)
        x=self.make()
        x.on_resolume(Message("control_change",channel=0,control=20,value=127))
        self.assertEqual(x.profile_values[(0,20)],127)
        self.assertEqual(x.res_out.messages,[])
        self.assertEqual(x.apc_out.messages[-1].value,127)

    def test_owned_led_rejects_arena_palette_and_legacy_draw(self):
        self.rule(mode="solid",color=45)
        x=self.make()
        before=len(x.apc_out.messages)
        x.draw(0)
        x.on_resolume(Message("note_on",channel=0,note=32,velocity=5))
        self.assertEqual(len(x.apc_out.messages),before)

    def test_static_frames_are_deduplicated_and_no_controller_cc_animation(self):
        self.rule(mode="solid")
        x=self.make()
        before=len(x.apc_out.messages)
        x._profile_tick(.25)
        self.assertEqual(len(x.apc_out.messages),before)
        self.assertTrue(all(m.type!="control_change" for m in x.apc_out.messages))

    def test_blink_has_one_owner_and_changes_only_led_notes(self):
        self.rule(mode="blink",note=58)
        self.cfg["always_lit"]=True
        with patch.object(b.Bridge,"_blinker"):
            x=self.make()
        before=len(x.apc_out.messages)
        x.draw_lit((58,0))
        self.assertEqual(len(x.apc_out.messages),before)
        before=len(x.apc_out.messages)
        x._profile_tick(.51)
        self.assertEqual(x.apc_out.messages[-1].note,58)
        self.assertEqual(x.apc_out.messages[-1].velocity,0)
        self.assertEqual(len(x.apc_out.messages),before+1)

    def test_reset_consumes_hold_and_release_once_and_sends_true_value(self):
        self.rule(note=58,mode="speed",source_cc=20,press="reset")
        x=self.make()
        for _ in range(2):x.on_apc(Message("note_on",channel=0,note=58,velocity=127))
        x.on_apc(Message("note_off",channel=0,note=58,velocity=0))
        self.assertEqual(len(x.res_out.messages),1)
        self.assertEqual(x.res_out.messages[0].control,20)
        self.assertEqual(x.res_out.messages[0].value,0)
        self.assertNotIn((0,58),x.profile_held)
        self.assertEqual(x.profile_phase[(0,58)],0)

    def test_profile_overrides_legacy_speed_button_without_double_reset(self):
        self.rule(note=58,mode="solid",source_cc=21,press="reset",reset_value=20)
        self.cfg["speed_button_pulse"]=True
        with patch.object(b.Bridge,"_speed_animator"):
            x=self.make()
        x.on_apc(Message("note_on",channel=0,note=58,velocity=127))
        self.assertEqual(len(x.res_out.messages),1)
        self.assertEqual(x.res_out.messages[0].control,21)
        self.assertEqual(x.res_out.messages[0].value,20)
        before=len(x.apc_out.messages)
        x._speed_tick(0)
        self.assertFalse(any(m.type=="note_on" and m.note==58 for m in x.apc_out.messages[before:]))

    def test_lighting_keeps_speed_reset_and_updates_linked_led(self):
        self.rule(note=58,mode="speed",source_cc=20)
        self.cfg["speed_button_pulse"]=True
        with patch.object(b.Bridge,"_speed_animator"):
            x=self.make()
        x.on_apc(Message("control_change",channel=0,control=20,value=127))
        x.res_out.messages.clear()
        x._profile_tick(.2)
        for _ in range(2):
            x.on_apc(Message("note_on",channel=0,note=58,velocity=127))
        x.on_apc(Message("note_off",channel=0,note=58,velocity=0))
        self.assertEqual(len(x.res_out.messages),1)
        self.assertEqual((x.res_out.messages[0].control,x.res_out.messages[0].value),(20,0))
        self.assertEqual(x.profile_values[(0,20)],0)
        self.assertEqual(x.profile_phase[(0,58)],0)
        self.assertNotIn(58,x.speed_reset_held)

    def test_speed_profile_rate_tracks_knob_and_mouse_feedback(self):
        self.rule(note=58,mode="speed",source_cc=20,rate_min=.5,rate_max=4)
        x=self.make()
        for source, value, phase in ((x.on_apc,0,.05),(x.on_apc,127,.4),(x.on_resolume,0,.05)):
            source(Message("control_change",channel=0,control=20,value=value))
            x.profile_phase[(0,58)]=0
            x._profile_tick(.1)
            self.assertAlmostEqual(x.profile_phase[(0,58)],phase)

    def test_profile_lighting_preserves_original_colorize_press(self):
        self.rule(mode="solid")
        x=self.make()
        msg=Message("note_on",channel=0,note=32,velocity=127)
        x.on_apc(msg)
        self.assertIs(x.res_out.messages[-1],msg)
        self.assertFalse(x.state.color_on[0])

    def test_sync_off_does_not_update_preview_source(self):
        self.rule()
        self.cfg["sync_resolume_feedback"]=False
        x=self.make()
        x.on_resolume(Message("control_change",channel=0,control=48,value=127))
        self.assertEqual(x.profile_values,{})

    def test_reload_applies_and_removes_lighting_without_reopening_ports(self):
        self.rule(mode="solid",color=45)
        x=self.make()
        ports=list(self.backend.ports)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"config.json"
            with patch.object(b,"CFG_PATH",str(path)):
                path.write_text(json.dumps({"control_rules":[dict(self.cfg["control_rules"][0],color=5)]}))
                x._reload_profile()
                self.assertEqual(x.apc_out.messages[-1].velocity,5)
                path.write_text(json.dumps({"control_rules":[]}))
                x.profile_config_stamp=None
                x._reload_profile()
                self.assertEqual(x.profile_rules,{})
                self.assertEqual(x.res_out.messages,[])
                self.assertEqual(self.backend.ports,ports)
                self.assertFalse(any(p.closed for p in ports))

    def test_invalid_reload_keeps_last_valid_profile(self):
        self.rule(mode="solid",color=45)
        x=self.make()
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"config.json";path.write_text('{"control_rules":[{"mode":"bad"}]}')
            with patch.object(b,"CFG_PATH",str(path)),self.assertLogs(level="WARNING"):
                x._reload_profile()
        self.assertEqual(x.profile_rules[(0,32)]["color"],45)
        self.assertFalse(x.failed.is_set())

    def test_invalid_profile_fails_before_opening_any_port(self):
        changes=[dict(mode="bad"),dict(mode="hue",note=58),dict(source_cc=127),dict(rate_max=10),dict(reset_value=-1),dict(note=90),dict(channel=True)]
        for change in changes:
            self.rule(**change)
            with self.assertRaises(ValueError):b.Bridge(self.cfg)
        self.assertEqual(self.backend.ports,[])

    def test_worker_failure_marks_connection_for_recovery_and_close_stops_it(self):
        self.rule()
        x=self.make()
        x.apc_out.fail=True
        with self.assertLogs(level="ERROR"):
            with patch.object(x.profile_stop,"wait",return_value=False):
                with patch.object(x,"_profile_tick",side_effect=OSError("gone")):
                    PROFILE_WORKER(x)
        self.assertTrue(x.failed.is_set())
        x.close()
        self.assertTrue(x.profile_stop.is_set())
        self.assertTrue(all(p.closed for p in self.backend.ports))

class InstallerFeedbackTests(unittest.TestCase):
    def test_repair_preserves_physical_ports_and_mode(self):
        xml='<midiController><inputDevices><device name="APC40 mkII"/></inputDevices><outputDevices><device name="APC40 mkII"/></outputDevices><controlSurfaces><device port="APC40 mkII" option="3"/></controlSurfaces></midiController>'
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"midi.xml";p.write_text(xml)
            self.assertTrue(b.patch_midi_xml(p,b.DEFAULT_CFG))
            tree=b.ET.parse(p)
            self.assertEqual([x.get("name") for x in tree.findall("inputDevices/device")],["APC40 mkII","APC VIRT A"])
            self.assertEqual([x.get("name") for x in tree.findall("outputDevices/device")],["APC40 mkII","APC VIRT B"])
            self.assertEqual(tree.find("controlSurfaces/device").get("option"),"3")
            self.assertFalse(b.patch_midi_xml(p,b.DEFAULT_CFG,dry=True))

    def test_dry_check_never_edits_file_and_missing_physical_is_enabled(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"midi.xml";p.write_text("<midiController/>")
            before=p.read_bytes()
            self.assertTrue(b.patch_midi_xml(p,b.DEFAULT_CFG,dry=True))
            self.assertEqual(p.read_bytes(),before)
            b.patch_midi_xml(p,b.DEFAULT_CFG)
            self.assertTrue(any(x.get("name")=="APC40 mkII" for x in b.ET.parse(p).findall("inputDevices/device")))

class LiveSnapshotTests(unittest.TestCase):
    def test_snapshot_worker_is_dormant_without_an_editor_request(self):
        x=b.Bridge.__new__(b.Bridge)
        x.live_stop=Mock()
        x.live_stop.wait.side_effect=[False,False,True]
        x._live_publish=Mock()
        with patch("builtins.open",side_effect=OSError("no lease")),patch.object(b.time,"time",return_value=100):
            b.Bridge._live_worker(x)
        x._live_publish.assert_not_called()

    def test_snapshot_worker_activates_only_with_a_short_lease(self):
        from io import StringIO
        x=b.Bridge.__new__(b.Bridge)
        x.live_stop=Mock()
        x.live_stop.wait.side_effect=[False,False,True]
        x._live_publish=Mock()
        with patch("builtins.open",return_value=StringIO('{"expires":105}')),patch.object(b.time,"time",return_value=100):
            b.Bridge._live_worker(x)
        self.assertEqual(x._live_publish.call_count,2)
        self.assertEqual(x.live_stop.wait.call_args_list[1].args,(.1,))

    def test_snapshot_is_read_only_and_marks_disconnect(self):
        x=b.Bridge.__new__(b.Bridge)
        x.live_lock=threading.Lock()
        x.live_leds={"0:32":45}
        x.live_controls={"0:48":127}
        x.live_warned=False
        x.live_previous=None
        x.live_written=0
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"controller-live.json"
            with patch.object(b,"LIVE_PATH",str(p)):
                x._live_publish()
                data=json.loads(p.read_text())
                self.assertTrue(data["connected"])
                self.assertEqual(data["leds"],{"0:32":45})
                before=p.stat().st_mtime_ns
                x._live_publish()
                self.assertEqual(p.stat().st_mtime_ns,before)
                x._live_publish(False)
                self.assertFalse(json.loads(p.read_text())["connected"])
                self.assertFalse(p.with_suffix(".json.tmp").exists())

    def test_snapshot_write_failure_does_not_stop_midi(self):
        x=b.Bridge.__new__(b.Bridge)
        x.live_lock=threading.Lock()
        x.live_leds={}
        x.live_controls={}
        x.live_warned=False
        x.live_previous=None
        x.live_written=0
        with patch("builtins.open",side_effect=OSError("read only")),self.assertLogs(level="WARNING"):
            x._live_publish()
        self.assertTrue(x.live_warned)

if __name__=="__main__":unittest.main()

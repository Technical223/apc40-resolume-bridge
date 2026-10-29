"""APC40 mkII <-> Resolume Arena MIDI bridge.

APC40 (USB)  <->  this script  <->  loopMIDI "APC VIRT A" (to Resolume)
                                   loopMIDI "APC VIRT B" (from Resolume)

* Passes every message through in both directions.
* Track knobs 1-8 (CC 48-55): the top grid row (notes 32-39) shows the hue
  the knob currently gives (palette colour), white when colorize is off.
* Optional MIDI feedback updates hue and Colorize state; bridge still owns pad colours.
* Single-colour buttons stay lit all the time and blink while active
  (easier to find in the dark).
* --watch: runs the bridge only while Resolume Arena is running.

Usage:  python apc_bridge.py --watch | --run | --list-ports | --patch-resolume | --restore-resolume
"""
import argparse
import colorsys
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET

BASE = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(BASE, "config.json")
STATE_PATH = os.path.join(BASE, "state.json")
LOG_PATH = os.path.join(BASE, "bridge.log")
PID_PATH = os.path.join(BASE, "bridge.pid")

DEFAULT_CFG = {
    "apc_port_match": "APC40",
    "to_resolume_port": "APC VIRT A",
    "from_resolume_port": "APC VIRT B",
    "arena_process": "Arena.exe",
    "apc_mode": 66,                      # 0x42 Alternate Ableton Live mode (host owns all LEDs)
    "hue_max": 0.63871,                  # = Max of the hue knob range in Resolume (1.0 = full hue circle)
    "knob_ccs": [48, 49, 50, 51, 52, 53, 54, 55],
    "color_notes": [32, 33, 34, 35, 36, 37, 38, 39],
    "white_velocity": 3,
    # Match NamedValues in the Resolume preset: bypass Off=5, On=3.
    "sync_resolume_feedback": False,
    "color_on_feedback_velocity": 5,
    "color_off_feedback_velocity": 3,
    "palette": [[0, 5], [20, 9], [55, 13], [90, 17], [120, 21], [145, 25],
                [165, 29], [180, 33], [200, 37], [220, 41], [240, 45],
                [260, 49], [300, 53], [335, 57]],
    "poll_seconds": 2.0,
    "speed_ring_animation": False,  # Missing key preserves original ring behavior.
    "speed_ring_ccs": [20, 21, 22, 23],
    "speed_ring_channel": 0,  # MIDI channel 1 in Arena.
    "speed_ring_slowest_seconds": 2.0,
    "speed_ring_fastest_seconds": 0.25,
    "speed_ring_update_hz": 120.0,
    # single-colour buttons: lit all the time, blinking while active
    "always_lit": True,
    "lit_track_notes": [48, 49, 50, 51, 52, 66],          # rec arm, solo, activator, track select, clip stop, A|B (ch 1-8)
    "lit_global_notes": [58, 59, 60, 61, 62, 63, 64, 65,  # device buttons
                         80, 81, 82, 83, 84, 85, 86,      # master, stop all, scene launch
                         87, 88, 89, 90, 91, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103],
    # [note, channel 0-15] whose Resolume LED means "normal" (e.g. mute buttons): blink when it goes dark
    "lit_invert": [[51, 1], [51, 3], [51, 5], [51, 7], [80, 0]],
    "idle_velocity": 1,
    "blink_hz": 3.0,
}


def load_cfg():
    cfg = dict(DEFAULT_CFG)
    try:
        with open(CFG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except FileNotFoundError:
        pass
    return cfg


def setup_logging(console):
    handlers = [logging.FileHandler(LOG_PATH, encoding="utf-8")]
    if console:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(level=logging.INFO, handlers=handlers,
                        format="%(asctime)s %(levelname)s %(message)s")


# ---------------------------------------------------------------- colour logic
def hue_to_velocity(cc_value, cfg):
    """Knob value 0-127 -> APC palette velocity of the nearest fully saturated colour."""
    angle = (cc_value / 127.0) * cfg["hue_max"] * 360.0
    best = min(cfg["palette"], key=lambda p: min(abs(p[0] - angle), 360 - abs(p[0] - angle)))
    return best[1]


def hue_to_rgb_hex(cc_value, cfg):
    r, g, b = colorsys.hsv_to_rgb((cc_value / 127.0) * cfg["hue_max"], 1, 1)
    return "#%02X%02X%02X" % (int(r * 255), int(g * 255), int(b * 255))


# Akai APC40 mkII protocol v1.2, pp.24-27: Single mode, 15 LEDs.
# These values avoid intermediate two-LED patterns in the Single table.
SPEED_RING_DOTS = (1, 10, 19, 28, 36, 45, 54, 63, 71, 80, 89, 98, 106, 115, 125)


def speed_ring_period(value, cfg):
    slow = cfg.get("speed_ring_slowest_seconds", 2.0)
    fast = cfg.get("speed_ring_fastest_seconds", 0.25)
    return slow + (fast - slow) * max(0, min(127, value)) / 127.0


def validate_speed_rings(cfg):
    ccs = cfg.get("speed_ring_ccs", [20, 21, 22, 23])
    if not isinstance(ccs, list) or not ccs or any(type(c) is not int or c not in range(16, 24) for c in ccs) or len(set(ccs)) != len(ccs):
        raise ValueError("speed_ring_ccs must be unique device-knob CCs 16-23")
    channel = cfg.get("speed_ring_channel", 0)
    if type(channel) is not int or channel not in range(16):
        raise ValueError("speed_ring_channel must be 0-15")
    slow = cfg.get("speed_ring_slowest_seconds", 2.0)
    fast = cfg.get("speed_ring_fastest_seconds", 0.25)
    hz = cfg.get("speed_ring_update_hz", 120.0)
    import math
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in (slow, fast, hz)) or not 0.05 <= fast <= slow <= 60 or not 1 <= hz <= 240:
        raise ValueError("Speed ring periods must satisfy 0.05 <= fastest <= slowest <= 60; update rate 1-240 Hz")
    if cfg.get("apc_mode", 66) != 66:
        raise ValueError("Speed ring animation requires APC Alternate Ableton mode 66")
    return ccs, channel


class State:
    def __init__(self, n):
        self.hue = [0] * n
        self.color_on = [True] * n
        self.dirty = False
        self.speed = {}
        self._persist_lock = threading.RLock()
        try:
            with open(STATE_PATH, encoding="utf-8") as f:
                d = json.load(f)
            raw_speed = d.get("speed", {})
            if isinstance(raw_speed, dict):
                self.speed = {k: v for k, v in raw_speed.items() if isinstance(k, str) and type(v) is int and 0 <= v <= 127}
            self.hue = (d.get("hue", self.hue) + [0] * n)[:n]
            self.color_on = (d.get("color_on", self.color_on) + [True] * n)[:n]
        except (FileNotFoundError, ValueError):
            pass

    def save(self):
        with self._persist_lock:
            self._save()

    def _save(self):
        if not self.dirty:
            return
        tmp = STATE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"hue": self.hue, "color_on": self.color_on, "speed": self.speed}, f)
        os.replace(tmp, STATE_PATH)
        self.dirty = False


# ---------------------------------------------------------------- ports
def _names(kind):
    import mido
    return mido.get_input_names() if kind == "in" else mido.get_output_names()


def find_port(kind, match, exclude=None):
    for name in _names(kind):
        if match.lower() in name.lower() and not (exclude and exclude.lower() in name.lower()):
            return name
    return None


def ports_ready(cfg):
    return all([
        find_port("in", cfg["apc_port_match"], "VIRT"),
        find_port("out", cfg["apc_port_match"], "VIRT"),
        find_port("out", cfg["to_resolume_port"]),
        find_port("in", cfg["from_resolume_port"]),
    ])


def port_status(cfg):
    """Read-only availability check. Never open/claim MIDI ports."""
    try:
        ins, outs = _names("in"), _names("out")
        def contains(names, match, exclude=None):
            return any(match.lower() in n.lower() and
                       not (exclude and exclude.lower() in n.lower()) for n in names)
        return {"dependencies_ready": True,
                "apc_ready": contains(ins, cfg["apc_port_match"], "VIRT") and contains(outs, cfg["apc_port_match"], "VIRT"),
                "virtual_ready": contains(outs, cfg["to_resolume_port"]) and contains(ins, cfg["from_resolume_port"]),
                "error": ""}
    except Exception as exc:
        return {"dependencies_ready": False, "apc_ready": False,
                "virtual_ready": False, "error": str(exc)}


def preference_status(cfg):
    """Verify MIDI preferences without editing them, even while Arena runs."""
    try:
        dirs = resolume_pref_dirs()
        ready = bool(dirs) and all(not patch_midi_xml(os.path.join(d, "midi.xml"), cfg, dry=True) for d in dirs)
        return {"preferences_ready": ready, "preferences_error": ""}
    except Exception as exc:
        return {"preferences_ready": False, "preferences_error": str(exc)}


# ---------------------------------------------------------------- bridge
class Bridge:
    def __init__(self, cfg):
        import mido
        self.mido = mido
        self.cfg = cfg
        self.knobs = cfg["knob_ccs"]
        self.notes = cfg["color_notes"]
        self.state = State(len(self.knobs))
        self.speed_enabled = bool(cfg.get("speed_ring_animation", False))
        self.speed_ccs, self.speed_channel = validate_speed_rings(cfg) if self.speed_enabled else ([], 0)
        self.speed_stop = threading.Event()
        self.speed_thread = None
        self.speed_lock = getattr(self.state, "_persist_lock", threading.RLock())
        self.speed_phase = [0.0] * len(self.speed_ccs)
        self.speed_last = [None] * len(self.speed_ccs)
        self.lock = threading.Lock()
        self.count = {"apc>res": 0, "res>apc": 0, "dropped": 0}
        self.lit = {}
        if cfg.get("always_lit", True):
            for n in cfg["lit_track_notes"]:
                for ch in range(8):
                    self.lit[(n, ch)] = False
            for n in cfg["lit_global_notes"]:
                self.lit[(n, 0)] = False
        self.invert = {tuple(k) for k in cfg.get("lit_invert", [])}
        self.blink_on = True
        self.running = True
        self.failed = threading.Event()
        try:
            self.apc_in = mido.open_input(find_port("in", cfg["apc_port_match"], "VIRT"))
            self.apc_out = mido.open_output(find_port("out", cfg["apc_port_match"], "VIRT"))
            self.res_out = mido.open_output(find_port("out", cfg["to_resolume_port"]))
            self.res_in = mido.open_input(find_port("in", cfg["from_resolume_port"]))
            logging.info("Ports: APC in=%s out=%s | Resolume in=%s out=%s",
                         self.apc_in.name, self.apc_out.name, self.res_out.name, self.res_in.name)
            self._to_apc(mido.Message("sysex", data=[0x47, 0x7F, 0x29, 0x60, 0x00, 0x04,
                                                     cfg["apc_mode"], 0x01, 0x00, 0x00]))
            for i in range(len(self.notes)):
                self.draw(i)
            for k in self.lit:
                self.draw_lit(k)
            if self.speed_enabled:
                for cc in self.speed_ccs:
                    self._to_apc(mido.Message("control_change", channel=self.speed_channel, control=cc + 8, value=1))
                self._speed_tick(0)
            self.apc_in.callback = self.on_apc
            self.res_in.callback = self.on_resolume
            if self.speed_enabled:
                self.speed_thread = threading.Thread(target=self._speed_animator, name="APC-speed-rings", daemon=True)
                self.speed_thread.start()
            if self.lit:
                threading.Thread(target=self._blinker, daemon=True).start()
        except Exception:
            self.running = False
            self._stop_speed_animation()
            self._close_ports()
            raise

    def _speed_key(self, cc):
        return "%d:%d" % (self.speed_channel, cc)

    def _store_speed(self, msg):
        with self.speed_lock:
            self.state.speed[self._speed_key(msg.control)] = msg.value
            self.state.dirty = True

    def _speed_tick(self, elapsed):
        with self.speed_lock:
            for i, cc in enumerate(self.speed_ccs):
                value = self.state.speed.get(self._speed_key(cc), 0)
                self.speed_phase[i] = (self.speed_phase[i] + elapsed / speed_ring_period(value, self.cfg)) % 1.0
                dot = int(self.speed_phase[i] * len(SPEED_RING_DOTS))
                if dot != self.speed_last[i]:
                    self._to_apc(self.mido.Message("control_change", channel=self.speed_channel, control=cc, value=SPEED_RING_DOTS[dot]))
                    self.speed_last[i] = dot

    def _speed_animator(self):
        last = time.monotonic()
        try:
            while not self.speed_stop.wait(1.0 / self.cfg.get("speed_ring_update_hz", 120.0)):
                now = time.monotonic()
                self._speed_tick(now - last)
                last = now
        except Exception:
            logging.exception("Speed ring animation")
            self.failed.set()

    def _stop_speed_animation(self):
        self.speed_stop.set()
        if self.speed_thread is not None and self.speed_thread.ident is not None:
            self.speed_thread.join()

    def draw_lit(self, key):
        on = (not self.lit[key]) or self.blink_on
        self._to_apc(self.mido.Message("note_on", channel=key[1], note=key[0],
                                       velocity=self.cfg["idle_velocity"] if on else 0))

    def _blinker(self):
        half = 0.5 / max(0.5, float(self.cfg.get("blink_hz", 3.0)))
        while self.running:
            time.sleep(half)
            self.blink_on = not self.blink_on
            try:
                for k, active in list(self.lit.items()):
                    if active:
                        self.draw_lit(k)
            except Exception:
                logging.exception("blink")
                self.failed.set()
                return

    def _to_apc(self, msg):
        with self.lock:
            self.apc_out.send(msg)

    def draw(self, i):
        if self.state.color_on[i]:
            vel = hue_to_velocity(self.state.hue[i], self.cfg)
        else:
            vel = self.cfg["white_velocity"]
        self._to_apc(self.mido.Message("note_on", channel=0, note=self.notes[i], velocity=vel))

    def on_apc(self, msg):
        self.count["apc>res"] += 1
        try:
            if self.speed_enabled and msg.type == "control_change" and msg.channel == self.speed_channel and msg.control in self.speed_ccs:
                self._store_speed(msg)
                self.res_out.send(msg)
                return
            if msg.type == "control_change" and msg.channel == 0 and msg.control in self.knobs:
                i = self.knobs.index(msg.control)
                self.state.hue[i] = msg.value
                self.state.dirty = True
                self.res_out.send(msg)
                self.draw(i)
                return
            if msg.type == "note_on" and msg.channel == 0 and msg.note in self.notes and msg.velocity > 0:
                i = self.notes.index(msg.note)
                self.state.color_on[i] = not self.state.color_on[i]
                self.state.dirty = True
                self.res_out.send(msg)
                self.draw(i)
                return
            self.res_out.send(msg)
        except Exception:  # never let a callback die silently
            logging.exception("APC -> Resolume")
            self.failed.set()

    def on_resolume(self, msg):
        self.count["res>apc"] += 1
        try:
            if self.speed_enabled and msg.type == "control_change" and msg.channel == self.speed_channel:
                if msg.control in self.speed_ccs:
                    if self.cfg.get("sync_resolume_feedback", False):
                        self._store_speed(msg)
                    return  # Ring values belong exclusively to the animator.
                if msg.control in [cc + 8 for cc in self.speed_ccs]:
                    return  # Prevent incoming ring-style feedback fighting Single mode.
            if (self.cfg.get("sync_resolume_feedback", False)
                    and msg.type == "control_change" and msg.channel == 0
                    and msg.control in self.knobs):
                i = self.knobs.index(msg.control)
                self.state.hue[i] = msg.value
                self.state.dirty = True
                self._to_apc(msg)  # Preserve existing MIDI-through (including knob feedback).
                self.draw(i)
                return
            if msg.type in ("note_on", "note_off") and msg.channel == 0 and msg.note in self.notes:
                self.count["dropped"] += 1
                if self.cfg.get("sync_resolume_feedback", False) and msg.type == "note_on":
                    # Both preset values are positive: generic velocity>0 would be wrong.
                    on = self.cfg["color_on_feedback_velocity"]
                    off = self.cfg["color_off_feedback_velocity"]
                    if on != off and msg.velocity in (on, off):
                        i = self.notes.index(msg.note)
                        self.state.color_on[i] = msg.velocity == on
                        self.state.dirty = True
                        self.draw(i)
                return  # Never forward Resolume palette colours over our own pad colours.
            if msg.type in ("note_on", "note_off") and (msg.note, msg.channel) in self.lit:
                key = (msg.note, msg.channel)
                lit = msg.type == "note_on" and msg.velocity > 0
                self.lit[key] = (not lit) if key in self.invert else lit
                self.draw_lit(key)
                return
            self._to_apc(msg)
        except Exception:
            logging.exception("Resolume -> APC")
            self.failed.set()

    def alive(self):
        return not self.failed.is_set() and ports_ready(self.cfg)

    def _close_ports(self):
        # Stop incoming callbacks before closing their output ports.
        for name in ("apc_in", "res_in", "apc_out", "res_out"):
            p = getattr(self, name, None)
            if p is None:
                continue
            try:
                p.close()
            except Exception:
                logging.exception("Closing MIDI port")
            finally:
                setattr(self, name, None)

    def close(self):
        self.running = False
        self._stop_speed_animation()
        self._close_ports()
        self.state.save()


# ---------------------------------------------------------------- Arena watch
def arena_running(proc_name):
    flags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
    try:
        out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {proc_name}", "/NH"],
                             capture_output=True, text=True, creationflags=flags, timeout=10).stdout
    except Exception:
        return False
    return proc_name.lower() in out.lower()


def run_loop(cfg, watch):
    bridge = None
    waiting_logged = False
    last_count = None
    while True:
        try:
            want = arena_running(cfg["arena_process"]) if watch else True
            if want and bridge is None:
                if ports_ready(cfg):
                    bridge = Bridge(cfg)
                    logging.info("Bridge running")
                    waiting_logged = False
                elif not waiting_logged:
                    logging.warning("Waiting for ports (APC40 connected? loopMIDI running with %s and %s?)",
                                    cfg["to_resolume_port"], cfg["from_resolume_port"])
                    waiting_logged = True
            elif bridge is not None and (not want or not bridge.alive()):
                logging.info("Bridge stopped (%s)", "Arena closed" if not want else "port lost or MIDI error")
                bridge.close()
                bridge = None
            if bridge is not None:
                bridge.state.save()
                c = dict(bridge.count)
                if c != last_count:
                    logging.info("MIDI traffic %s", c)
                    last_count = c
        except Exception:
            logging.exception("Bridge error, restarting in 3 s")
            if bridge is not None:
                bridge.close()
                bridge = None
            time.sleep(3)
        time.sleep(cfg["poll_seconds"])


# ---------------------------------------------------------------- Resolume prefs
def resolume_pref_dirs():
    home = os.path.expanduser("~")
    cands = []
    if os.name == "nt":
        try:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
            docs = os.path.expandvars(winreg.QueryValueEx(k, "Personal")[0])
            cands.append(docs)
        except OSError:
            pass
    cands += [os.path.join(home, "Documents"), os.path.join(home, "OneDrive", "Documents"),
              os.path.join(home, "OneDrive", "Dokumenty")]
    out = []
    for d in cands:
        p = os.path.join(d, "Resolume Arena", "Preferences")
        if os.path.isfile(os.path.join(p, "midi.xml")) and p not in out:
            out.append(p)
    return out


def patch_midi_xml(path, cfg, dry=False):
    """Resolume: physical APC40 off, loopMIDI ports on. Returns True when a change is (or was) needed."""
    tree = ET.parse(path)
    root = tree.getroot()
    changed = False
    to_res, from_res, match = cfg["to_resolume_port"], cfg["from_resolume_port"], cfg["apc_port_match"]
    for section, keep in (("inputDevices", to_res), ("outputDevices", from_res)):
        sec = root.find(section)
        if sec is None:
            sec = ET.SubElement(root, section)
        for d in list(sec):
            n = d.get("name", "")
            if match.lower() in n.lower() and n != keep:
                sec.remove(d)
                changed = True
        if not any(d.get("name") == keep for d in sec):
            ET.SubElement(sec, "device", {"name": keep})
            changed = True
    cs = root.find("controlSurfaces")
    if cs is not None:
        for d in list(cs):
            if match.lower() in d.get("port", "").lower():
                cs.remove(d)
                changed = True
    if changed and not dry:
        bak = path + ".pred-bridge.bak"
        if not os.path.exists(bak):
            shutil.copy2(path, bak)
        ET.indent(tree, "\t")
        with open(path, "w", encoding="utf-8", newline="\r\n") as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n")
    return changed


def cmd_patch(cfg, restore=False):
    dirs = resolume_pref_dirs()
    if not dirs:
        print("RESOLUME_PREFS_NOT_FOUND")
        return 1
    if arena_running(cfg["arena_process"]):
        # Resolume rewrites its prefs on exit, so never edit them while it runs
        needs = restore or any(patch_midi_xml(os.path.join(d, "midi.xml"), cfg, dry=True) for d in dirs)
        print("RESOLUME_RUNNING" if needs else "OK")
        return 2 if needs else 0
    for d in dirs:
        p = os.path.join(d, "midi.xml")
        if restore:
            bak = p + ".pred-bridge.bak"
            if os.path.exists(bak):
                shutil.copy2(bak, p)
                print("RESTORED " + p)
        else:
            print(("PATCHED " if patch_midi_xml(p, cfg) else "OK ") + p)
    return 0


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--watch", action="store_true", help="run while Resolume Arena runs")
    g.add_argument("--run", action="store_true", help="run now (debug, with console log)")
    g.add_argument("--list-ports", action="store_true")
    g.add_argument("--status-json", action="store_true")
    g.add_argument("--check-ports", action="store_true")
    g.add_argument("--patch-resolume", action="store_true")
    g.add_argument("--restore-resolume", action="store_true")
    a = ap.parse_args()
    cfg = load_cfg()
    if a.status_json:
        status = port_status(cfg)
        status.update(preference_status(cfg))
        print(json.dumps(status))
        return 0
    if a.list_ports:
        print("IN :", _names("in"))
        print("OUT:", _names("out"))
        return 0
    if a.check_ports:
        missing = [n for n, k in ((cfg["to_resolume_port"], "out"), (cfg["from_resolume_port"], "in"))
                   if not find_port(k, n)]
        print("MISSING " + ";".join(missing) if missing else "PORTS_OK")
        return 1 if missing else 0
    if a.patch_resolume or a.restore_resolume:
        return cmd_patch(cfg, restore=a.restore_resolume)
    setup_logging(console=a.run)
    with open(PID_PATH, "w") as f:
        f.write(str(os.getpid()))
    logging.info("Start (%s)", "watch Arena" if a.watch else "run")
    try:
        run_loop(cfg, watch=a.watch)
    finally:
        try:
            os.remove(PID_PATH)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())

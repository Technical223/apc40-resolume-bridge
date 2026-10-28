"""Experimental macOS host for the unchanged shared MIDI engine."""
import argparse
from collections import deque
from datetime import datetime, timezone
import importlib.metadata
import importlib.util
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
import threading
import time
import traceback
import uuid
import zipfile

VERSION = "0.1.0-preview"
HERE = Path(__file__).resolve().parent
DATA = Path.home() / "Library/Application Support/APC40 Bridge macOS Preview"
BACKEND = "mido.backends.rtmidi/MACOSX_CORE"
EVENTS = deque(maxlen=300)
EVENT_LOCK = threading.Lock()


def event_snapshot():
    with EVENT_LOCK:
        return list(EVENTS)


def load_core():
    path = HERE / "core/apc_bridge.py"
    if not path.exists():
        path = HERE.parent / "bridge/apc_bridge.py"
    spec = importlib.util.spec_from_file_location("apc_macos_core", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.STATE_PATH = str(DATA / "state.json")
    return module


def load_config(core):
    source = HERE / "core/config.json"
    if not source.exists():
        source = HERE.parent / "bridge/config.json"
    cfg = dict(core.DEFAULT_CFG)
    cfg.update(json.loads(source.read_text(encoding="utf-8-sig")))
    cfg["arena_process"] = "Arena"
    override = DATA / "config.json"
    if override.exists():
        cfg.update(json.loads(override.read_text(encoding="utf-8-sig")))
    else:
        override.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    for key in ("apc_port_match", "to_resolume_port", "from_resolume_port", "arena_process"):
        if not isinstance(cfg[key], str) or not cfg[key].strip():
            raise ValueError("Empty or invalid setting: " + key)
    if cfg["to_resolume_port"].casefold() == cfg["from_resolume_port"].casefold():
        raise ValueError("Use two different IAC buses for the two directions.")
    for key in ("knob_ccs", "color_notes"):
        values = cfg[key]
        if (not isinstance(values, list) or len(values) != 8 or
                any(type(x) is not int or not 0 <= x <= 127 for x in values) or len(set(values)) != 8):
            raise ValueError(key + " must contain eight distinct MIDI numbers.")
    if not 0 < float(cfg["hue_max"]) <= 1 or not 0.5 <= float(cfg["blink_hz"]) <= 10:
        raise ValueError("Hue limit or blink rate outside supported range.")
    return cfg


def select_port(names, match, exclude=None):
    """Never choose an arbitrary device or open the default port."""
    names = [n for n in names if not exclude or exclude.casefold() not in n.casefold()]
    exact = [n for n in names if n.casefold() == match.casefold()]
    found = exact or [n for n in names if match.casefold() in n.casefold()]
    if len(found) != 1:
        raise RuntimeError("Expected one port matching %r; found %s" % (match, found))
    return found[0]


def configure_midi(core):
    import mido
    mido.set_backend(BACKEND, load=True)
    def find(kind, match, exclude=None):
        return select_port(core._names(kind), match, exclude)
    core.find_port = find  # macOS-only module instance; shared source unchanged.
    return mido


def routes(core, cfg):
    return {
        "apc_input": select_port(core._names("in"), cfg["apc_port_match"], "VIRT"),
        "apc_output": select_port(core._names("out"), cfg["apc_port_match"], "VIRT"),
        "arena_input_bus": select_port(core._names("out"), cfg["to_resolume_port"]),
        "arena_feedback_bus": select_port(core._names("in"), cfg["from_resolume_port"]),
    }


def arena_running(name):
    try:
        result = subprocess.run(["/bin/ps", "-axo", "comm="], capture_output=True,
                                text=True, timeout=5, check=True)
        return any(Path(line.strip()).name == name for line in result.stdout.splitlines())
    except (OSError, subprocess.SubprocessError):
        return None


def snapshot(core=None, cfg=None):
    result = {"schema": 1, "preview_version": VERSION,
              "utc": datetime.now(timezone.utc).isoformat(),
              "system": {"os": platform.system(), "macos": platform.mac_ver()[0],
                         "architecture": platform.machine(), "python": platform.python_version()},
              "backend": BACKEND, "dependencies": {}, "events": event_snapshot()}
    manifest = HERE / "build.json"
    if manifest.exists():
        result["build"] = json.loads(manifest.read_text(encoding="utf-8"))
    for name in ("mido", "python-rtmidi"):
        try:
            result["dependencies"][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result["dependencies"][name] = "not installed"
    if cfg:
        keys = ("apc_port_match", "to_resolume_port", "from_resolume_port", "arena_process",
                "apc_mode", "hue_max", "knob_ccs", "color_notes", "sync_resolume_feedback",
                "color_on_feedback_velocity", "color_off_feedback_velocity", "blink_hz")
        result["config"] = {k: cfg[k] for k in keys}
        result["arena_running"] = arena_running(cfg["arena_process"])
    try:
        if core is None or cfg is None:
            raise RuntimeError("Configuration or engine unavailable; see error details.")
        configure_midi(core)
        result["midi_inputs"] = core._names("in")
        result["midi_outputs"] = core._names("out")
        result["selected_routes"] = routes(core, cfg)
        result["ports_ready"] = True
    except Exception as exc:
        result["ports_ready"] = False
        result["port_error"] = str(exc)
    return result


def redact(text):
    text = text.replace(str(Path.home()), "<HOME>")
    return re.sub(r"/Users/[^/\s\"']+", "<HOME>", text)


def report(details, destination=None):
    """Export known diagnostics only; never whole folders or compositions."""
    root = Path(destination) if destination else Path.home() / "Desktop"
    filename = "APC40-macOS-debug-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6] + ".zip"
    try:
        root.mkdir(parents=True, exist_ok=True)
        handle = (root / filename).open("xb")
    except OSError:
        root = DATA / "reports"
        root.mkdir(parents=True, exist_ok=True)
        handle = (root / filename).open("xb")
    with handle, zipfile.ZipFile(handle, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("report.json", redact(json.dumps(details, indent=2, default=str)))
        for name in ("app.log", "test.log", "setup.log", "bootstrap.log", "last-test.json"):
            path = DATA / name
            if path.is_file():
                with path.open("rb") as stream:
                    stream.seek(max(0, path.stat().st_size - 256000))
                    text = stream.read(256000).decode("utf-8", errors="replace")
                archive.writestr(name, redact(text))
        archive.writestr("README.txt", "Local export. Nothing was uploaded.\n"
                         "Contains OS/CPU/Python versions, MIDI port names, route errors, logs,\n"
                         "message counts and up to 300 recent Hue/Colorize input events.\n"
                         "No compositions, screenshots, serial numbers, environment dump or full process list.\n"
                         "Home paths are redacted. Review custom MIDI names before sharing.\n")
    return root / filename


def logging_setup(name):
    DATA.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(DATA / name, maxBytes=1000000, backupCount=2, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True,
                        format="%(asctime)s %(levelname)s %(message)s")


def record_event(direction, msg, cfg):
    if getattr(msg, "channel", None) != 0:
        return
    if msg.type == "control_change" and msg.control in cfg["knob_ccs"]:
        event = {"kind": "Hue", "cc": msg.control, "value": msg.value}
    elif msg.type == "note_on" and msg.note in cfg["color_notes"]:
        event = {"kind": "Colorize", "note": msg.note, "velocity": msg.velocity}
    else:
        return
    event.update(direction=direction, monotonic=round(time.monotonic(), 3))
    with EVENT_LOCK:
        EVENTS.append(event)


def run_test(core, cfg, seconds, stop):
    configure_midi(core)
    bridge = None
    totals = {"apc>res": 0, "res>apc": 0, "dropped": 0}
    connections = 0
    last = None
    deadline = time.monotonic() + seconds
    try:
        while not stop.is_set() and time.monotonic() < deadline:
            try:
                if bridge is None:
                    logging.info("Selected routes: %s", routes(core, cfg))
                    class DebugBridge(core.Bridge):
                        def on_apc(self, msg):
                            record_event("APC -> Arena", msg, cfg)
                            super().on_apc(msg)
                        def on_resolume(self, msg):
                            record_event("Arena -> APC", msg, cfg)
                            super().on_resolume(msg)
                    bridge = DebugBridge(cfg)
                    connections += 1
                    logging.info("Bridge connected; remaining test time %.0f seconds", deadline - time.monotonic())
                if not bridge.alive():
                    raise RuntimeError("MIDI device disappeared or a send failed")
                bridge.state.save()
                if bridge.count != last:
                    last = dict(bridge.count)
                    logging.info("MIDI traffic %s", last)
                stop.wait(min(1, max(0, deadline - time.monotonic())))
            except Exception:
                logging.exception("Connection unavailable; retrying in 2 seconds")
                if bridge:
                    for key in totals:
                        totals[key] += bridge.count[key]
                    old, bridge = bridge, None
                    old.close()
                stop.wait(2)
    finally:
        if bridge:
            for key in totals:
                totals[key] += bridge.count[key]
            bridge.close()
    return {"connections": connections, "traffic": totals,
            "outcome": "no_connection" if not connections else "stopped" if stop.is_set() else "finished"}


def dialog(message):
    script = 'on run argv\n display dialog (item 1 of argv) with title "APC40 Bridge macOS Preview" buttons {"OK"} default button "OK"\nend run'
    subprocess.run(["/usr/bin/osascript", "-e", script, message], check=False)


def menu(message):
    script = '''on run argv
set choices to {"Prepare dependencies", "Open Audio MIDI Setup", "Open settings file", "Start 3-minute test", "Stop test", "Export diagnostics", "Open logs folder", "Quit"}
set picked to choose from list choices with title "APC40 Bridge macOS Preview" with prompt (item 1 of argv) default items {"Export diagnostics"}
if picked is false then return "Quit"
return item 1 of picked
end run'''
    result = subprocess.run(["/usr/bin/osascript", "-e", script, message],
                            capture_output=True, text=True, check=True)
    return result.stdout.strip()


def stop_child(child):
    if child is None or child.poll() is not None:
        return
    child.send_signal(signal.SIGTERM)
    try:
        child.wait(timeout=15)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait(timeout=5)
        logging.error("Test did not stop gracefully; export diagnostics manually")


def prepare():
    import venv
    target = DATA / "venv"
    with (DATA / "setup.log").open("w", encoding="utf-8") as output:
        venv.EnvBuilder(with_pip=True).create(target)
        subprocess.run([str(target / "bin/python3"), "-m", "pip", "install", "--only-binary=:all:",
                        "--disable-pip-version-check", "-r", str(HERE / "requirements.txt")],
                       stdout=output, stderr=subprocess.STDOUT, check=True, timeout=300)


def gui(core, cfg):
    import fcntl
    with (DATA / "dashboard.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            dialog("The preview control panel is already open.")
            return
        child = None
        try:
            while True:
                active = child is not None and child.poll() is None
                choice = menu("Experimental build " + VERSION + "\nTest: " + ("running" if active else "stopped")
                              + "\nUse two IAC buses. Arena preferences are never edited.\n"
                              "After testing, send the debug ZIP from your Desktop to Jakub.")
                try:
                    if choice == "Quit":
                        break
                    if choice == "Prepare dependencies":
                        if active:
                            dialog("Stop the test before preparing dependencies.")
                            continue
                        dialog("The next step downloads MIDI libraries from PyPI into a private environment. This may take several minutes. No sudo or global Python changes are used.")
                        prepare()
                        dialog("Dependencies ready. Configure IAC buses and Arena as described in README, then start the test.")
                    elif choice == "Open Audio MIDI Setup":
                        subprocess.run(["/usr/bin/open", "-a", "Audio MIDI Setup"], check=True)
                    elif choice == "Open settings file":
                        subprocess.run(["/usr/bin/open", "-a", "TextEdit", str(DATA / "config.json")], check=True)
                    elif choice == "Start 3-minute test":
                        if active:
                            dialog("A test is already running.")
                            continue
                        python = DATA / "venv/bin/python3"
                        if not python.exists():
                            dialog("Choose Prepare dependencies first.")
                            continue
                        dialog("The test runs for 3 minutes. It initializes APC LEDs and may resend fader/knob positions to Arena. Use a test composition. Move Hue knobs, toggle Colorize, then try mouse edits. A debug ZIP is created when the test ends.")
                        child = subprocess.Popen([str(python), str(HERE / "mac_bridge.py"), "--test", "--seconds", "180"],
                                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    elif choice == "Stop test":
                        stop_child(child)
                        exported = report(snapshot(core, cfg))
                        dialog("Test stopped. Diagnostics saved to:\n" + str(exported))
                    elif choice == "Export diagnostics":
                        if active:
                            stop_child(child)
                        python = DATA / "venv/bin/python3"
                        if not python.exists():
                            python = Path(sys.executable)
                        result = subprocess.run([str(python), str(HERE / "mac_bridge.py"), "--collect"],
                                                capture_output=True, text=True, timeout=30, check=True)
                        dialog(result.stdout.strip() + "\nReview the ZIP, then send it to Jakub. Nothing was uploaded.")
                    elif choice == "Open logs folder":
                        subprocess.run(["/usr/bin/open", str(DATA)], check=True)
                except Exception:
                    logging.exception("Preview action failed")
                    exported = report({**snapshot(core, cfg), "error": traceback.format_exc()})
                    dialog("The action failed. Diagnostics saved to:\n" + str(exported))
        finally:
            stop_child(child)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--collect", action="store_true")
    parser.add_argument("--seconds", type=int, default=180)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 600:
        parser.error("Test duration must be between 1 and 600 seconds")
    logging_setup("test.log" if args.test else "app.log")
    core = cfg = None
    try:
        core = load_core()
        cfg = load_config(core)
        if args.collect:
            print(report(snapshot(core, cfg)))
            return 0
        if sys.platform != "darwin":
            raise RuntimeError("This preview runs on macOS only. The Windows build is separate.")
        if args.test:
            import fcntl
            with (DATA / "test.lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                stop = threading.Event()
                signal.signal(signal.SIGTERM, lambda *_: stop.set())
                signal.signal(signal.SIGINT, lambda *_: stop.set())
                test = run_test(core, cfg, args.seconds, stop)
                details = {**snapshot(core, cfg), "test": test}
                details["events"] = event_snapshot()
                (DATA / "last-test.json").write_text(redact(json.dumps(details, indent=2)), encoding="utf-8")
                exported = report(details)
                logging.info("Report saved: %s", exported)
                return 0
        gui(core, cfg)
        return 0
    except Exception:
        logging.exception("Preview error")
        details = {**snapshot(core, cfg), "error": traceback.format_exc()}
        if args.test:
            (DATA / "last-test.json").write_text(redact(json.dumps(details, indent=2)), encoding="utf-8")
        exported = report(details)
        if not args.test and not args.collect and sys.platform == "darwin":
            dialog("The preview could not start. Diagnostics saved to:\n" + str(exported))
        else:
            print(exported)
        return 1


if __name__ == "__main__":
    sys.exit(main())

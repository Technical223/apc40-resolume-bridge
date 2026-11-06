"""Private loopback viewer. No network dependencies and no background work when closed."""
import hashlib
import json
import os
import secrets
import threading
import subprocess
import sys
import time
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

HOME = Path(__file__).resolve().parent
sys.path.insert(0, str(HOME))
STATE = HOME / "viewer-session.json"
FILES = {"workspace.js": "text/javascript", "preview.html": "text/html; charset=utf-8", "active-layout.js": "text/javascript",
         "room-current.glb": "model/gltf-binary",
         "editor.html": "text/html; charset=utf-8", "editor.js": "text/javascript",
         "wiring.js": "text/javascript", "editor-project.js": "text/javascript", "editor-model.js": "text/javascript"}
for _file in (HOME / "editor-vendor").glob("*.js"):
    FILES["editor-vendor/" + _file.name] = "text/javascript"
CONVERT_LOCK = threading.Lock()

def space_layout(query):
    """Generated layout file of the space named by ?space=, else the first space."""
    from prepare import layout_file, spaces
    items = spaces()
    wanted = parse_qs(query).get("space", [""])[0]
    return layout_file(next((s["id"] for s in items if s["id"] == wanted), items[0]["id"]), items)

def served_files():
    from prepare import spaces
    return {**FILES, **{space["model"]: "model/gltf-binary" for space in spaces()}}

def render_folder():
    """Pictures/APC40 Bridge (the user's real Pictures folder on Windows)."""
    pictures = Path.home() / "Pictures"
    if os.name == "nt":
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as key:
            pictures = Path(os.path.expandvars(winreg.QueryValueEx(key, "My Pictures")[0]))
    return pictures / "APC40 Bridge"

def layout_version(query=""):
    return hashlib.sha256(space_layout(query).read_bytes()).hexdigest()

def serve(idle_timeout=90, token=None, port=18741):
    from prepare import prepare
    prepare()
    token = token or secrets.token_urlsafe(24)
    if not all(c.isalnum() or c in "-_" for c in token) or not 20 <= len(token) <= 64:
        raise ValueError("Invalid local viewer session token")
    last_seen = time.monotonic()
    last_check = time.monotonic()
    from prepare import source_signature
    signature = source_signature()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            nonlocal last_seen, last_check, signature
            prefix = "/" + token + "/"
            path, _, query = self.path.partition("?")
            if not path.startswith(prefix):
                self.send_error(404)
                return
            name = path[len(prefix):]
            if name == "session":
                self.reply(json.dumps({"pid": os.getpid()}).encode(), "application/json")
                return
            if name == "heartbeat":
                last_seen = time.monotonic()
                try:
                    # Saved presets only; unchanged output never reloads the browser.
                    if time.monotonic() - last_check > 5:
                        updated = source_signature()
                        if updated != signature:
                            prepare()
                            signature = updated
                        last_check = time.monotonic()
                    payload = {"version": layout_version(query)}
                except Exception as error:
                    payload = {"error": str(error)}
                self.reply(json.dumps(payload).encode(), "application/json")
                return
            if name == "layout":
                text = space_layout(query).read_text(encoding="utf-8")
                layout = json.loads(text[len("window.APC40Layout="):-1])
                self.reply(json.dumps({key:layout[key] for key in ("comp","preset","outputFixtures")}).encode(), "application/json")
                return
            files = served_files()
            if name not in files:
                self.send_error(404)
                return
            file = space_layout(query) if name == "active-layout.js" else HOME / name
            if not file.is_file():
                self.send_error(404)
                return
            last_seen = time.monotonic()
            self.send_response(200)
            self.send_header("Content-Type", files[name])
            self.send_header("Content-Length", str(file.stat().st_size))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            try:
                with file.open("rb") as stream:
                    while chunk := stream.read(256 * 1024):
                        self.wfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_POST(self):
            if self.path == "/" + token + "/convert-model":
                origin = "http://127.0.0.1:" + str(self.server.server_port)
                if self.headers.get("Origin") != origin or self.headers.get("X-Conversion-Consent") != "yes":
                    self.send_error(403)
                    return
                from model_convert import convert_model, MAX_MODEL
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= MAX_MODEL:
                        self.send_error(413)
                        return
                    if not CONVERT_LOCK.acquire(blocking=False):
                        self.send_error(409, "A model is already converting")
                        return
                    try:
                        body = self.rfile.read(length)
                        if len(body) != length:
                            raise ValueError("Incomplete model upload")
                        result = convert_model(body, self.headers.get("X-Model-Extension", ""))
                    finally:
                        CONVERT_LOCK.release()
                    self.reply(result, "model/gltf-binary")
                except (ValueError, RuntimeError, OSError) as error:
                    self.reply(json.dumps({"error": str(error)}).encode(), "application/json")
                return
            # Save render: a PNG from this page, written under a server-chosen name.
            if self.path != "/" + token + "/render" or self.headers.get("Origin", "") not in ("", "http://127.0.0.1:" + str(self.server.server_port)):
                self.send_error(403)
                return
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if 0 < length <= 60 * 1024 * 1024 else b""
            if not body.startswith(b"\x89PNG\r\n\x1a\n"):
                self.send_error(400)
                return
            try:
                folder = render_folder()
                folder.mkdir(parents=True, exist_ok=True)
                target = folder / ("APC40-render-" + time.strftime("%Y%m%d-%H%M%S") + ".png")
                target.write_bytes(body)
            except OSError as error:
                # e.g. Windows Controlled Folder Access blocks the bundled Python in Pictures; the page then downloads it.
                self.send_error(507, "Could not write to " + str(render_folder()) + ": " + type(error).__name__)
                return
            self.reply(json.dumps({"path": str(target)}).encode(), "application/json")

        def reply(self, body, content_type):
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.timeout = 2
    url = "http://127.0.0.1:" + str(server.server_port) + "/" + token + "/"
    session = {"url": url, "pid": os.getpid()}
    STATE.write_text(json.dumps(session), encoding="utf-8")
    try:
        # shortcut: background tabs may be suspended; reopen from Bridge if the viewer expires.
        while time.monotonic() - last_seen < idle_timeout or CONVERT_LOCK.locked():
            server.handle_request()
    finally:
        server.server_close()
        try:
            if json.loads(STATE.read_text())["pid"] == os.getpid():
                STATE.unlink()
        except (OSError, ValueError, KeyError):
            pass

def current_url():
    try:
        session = json.loads(STATE.read_text(encoding="utf-8"))
        url = session["url"]
        from urllib.parse import urlsplit
        parsed = urlsplit(url)
        if parsed.scheme != "http" or parsed.hostname != "127.0.0.1":
            return None
        with urllib.request.urlopen(url + "session", timeout=1) as reply:
            if json.load(reply).get("pid") == session["pid"]:
                return url
    except (OSError, ValueError, KeyError):
        pass
    return None

def ensure_preview():
    from prepare import prepare
    prepare()
    url = current_url()
    if not url:
        executable = Path(sys.executable)
        windowless = executable.with_name("pythonw.exe")
        if windowless.is_file():
            executable = windowless
        process = subprocess.Popen([str(executable), str(HOME / "launcher.py")],
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        for attempt in range(40):
            time.sleep(.1)
            url = current_url()
            if url:
                break
            if process.poll() is not None:
                break
        if not url:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
            raise RuntimeError("The local visualizer could not start.")
    return url

def open_preview():
    app = HOME.parent / "APC40 Bridge.exe"
    if os.name == "nt" and app.is_file():
        subprocess.Popen([str(app), "--visualizer"], cwd=app.parent)
    else:
        webbrowser.open(ensure_preview() + "preview.html")

if __name__ == "__main__":
    if sys.argv[1:] == ["--url"]:
        import contextlib
        with contextlib.redirect_stdout(sys.stderr):
            url = ensure_preview()
        print(json.dumps({"url": url}))
    else:
        serve(token=sys.argv[1] if len(sys.argv) == 2 else None)

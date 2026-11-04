"""Build the Windows app, private runtime, portable ZIP and native setup EXE."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "bridge/offline-dependencies.lock.json").read_text(encoding="utf-8"))
VERSION = "1.5.3"

def download(item, cache):
    path = cache / item["file"]
    if not path.exists():
        request = urllib.request.Request(item["url"], headers={"User-Agent": "APC40-Bridge-build"})
        with urllib.request.urlopen(request, timeout=60) as response, path.open("wb") as out:
            shutil.copyfileobj(response, out)
    with path.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != item["sha256"]:
        raise ValueError("Dependency checksum mismatch: " + item["file"])
    return path

def extract_safe(archive, target):
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            path = (target / item.filename).resolve()
            if not path.is_relative_to(target.resolve()):
                raise ValueError("Invalid archive path")
        z.extractall(target)

def run(cmd, **kwargs):
    result = subprocess.run([str(x) for x in cmd], timeout=180, **kwargs)
    result.check_returncode()

def compiler():
    for name in ("Framework64", "Framework"):
        path = Path(os.environ["WINDIR"]) / "Microsoft.NET" / name / "v4.0.30319/csc.exe"
        if path.exists():
            return path
    raise RuntimeError(".NET Framework compiler is missing")

def compile_setup(output, payload=None):
    cmd = [compiler(), "/nologo", "/target:winexe", "/platform:anycpu", "/optimize+", "/out:" + str(output),
           "/win32icon:" + str(ROOT / "bridge/ui/bridge.ico")]
    for ref in ("System", "System.Core", "System.Drawing", "System.Windows.Forms", "System.Web.Extensions",
                "System.IO.Compression", "System.IO.Compression.FileSystem", "Microsoft.CSharp"):
        cmd.append("/reference:" + ref + ".dll")
    if payload:
        cmd.append("/resource:" + str(payload) + ",ApcBridge.Payload.zip")
    cmd.append(ROOT / "bridge/installer/Setup.cs")
    run(cmd)

def build(output, cache, visualizer=None):
    output.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    names = ("APC40-Bridge-Setup.exe", "APC40-Bridge-Portable.zip")
    if any((output / name).exists() for name in names):
        raise FileExistsError("Choose an empty output directory")
    run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ROOT / "bridge/build-ui.ps1"])
    with tempfile.TemporaryDirectory(prefix="APC40-build-") as tmp:
        stage = Path(tmp) / "app"
        stage.mkdir()
        files = ["APC40 Bridge.exe", "APC40 Bridge.vbs", "apc_bridge.py", "config.json", "setup.ps1",
                 "runtime.ps1", "manage.ps1", "stop_bridge.ps1", "build-ui.ps1", "START.bat", "STOP.bat",
                 "AUTOSTART_ON.bat", "AUTOSTART_OFF.bat", "DEBUG.bat", "RESTORE_RESOLUME.bat"]
        for name in files:
            shutil.copy2(ROOT / "bridge" / name, stage / name)
        for name in ("ui", "profiles"):
            shutil.copytree(ROOT / "bridge" / name, stage / name)
        shutil.copytree(ROOT / "resolume", stage / "resolume")
        # Keep installed help small; full showcase media stays on GitHub.
        shutil.copytree(ROOT / "docs", stage / "docs", ignore=shutil.ignore_patterns("media"))
        for name in ("README.md", "README.cs.md", "LICENSE", "CLAUDE.md"):
            shutil.copy2(ROOT / name, stage / name)
        viewer = visualizer or ROOT / "bridge/visualizer"
        if viewer.is_dir():
            excluded = ["__pycache__", "*.pyc", "active-layout*.js", "viewer-session.json", "*.download"]
            if visualizer is None:
                excluded.append("SpoutCam64.ax")
            shutil.copytree(viewer, stage / "visualizer", ignore=shutil.ignore_patterns(*excluded))
        runtime = stage / "runtime"
        runtime.mkdir()
        extract_safe(download(LOCK["python"], cache), runtime)
        site = runtime / "site-packages"
        site.mkdir()
        for wheel in LOCK["wheels"]:
            extract_safe(download(wheel, cache), site)
        pth = next(runtime.glob("python*._pth"))
        pth.write_text("python312.zip\n.\nsite-packages\n..\nimport site\n", encoding="utf-8")
        (stage / "runtime-manifest.json").write_text(json.dumps(LOCK, indent=2), encoding="utf-8")
        run([runtime / "python.exe", "-I", "-c",
             "import mido,rtmidi,packaging,ssl; print('Bundled MIDI runtime OK')"])
        compile_setup(stage / "Uninstall.exe")
        manifest = {"version": VERSION, "files": []}
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                with path.open("rb") as stream:
                    digest = hashlib.file_digest(stream, "sha256").hexdigest()
                manifest["files"].append({"path": path.relative_to(stage).as_posix(), "sha256": digest})
        (stage / "package-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        payload = Path(tmp) / "payload.zip"
        with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for path in sorted(stage.rglob("*")):
                if path.is_file():
                    z.write(path, path.relative_to(stage).as_posix())
        shutil.copy2(payload, output / names[1])
        compile_setup(output / names[0], payload)
        # Verify extraction and runtime in an isolated directory, without installation.
        extracted = Path(tmp) / "verify"
        run([output / names[0], "--extract", extracted])
        run([extracted / "runtime/python.exe", "-I", "-c", "import mido,rtmidi; print('Extracted offline runtime OK')"])
        run([extracted / "runtime/python.exe", extracted / "apc_bridge.py", "--status-json"])
    sums = []
    for name in names:
        with (output / name).open("rb") as stream:
            sums.append(hashlib.file_digest(stream, "sha256").hexdigest() + "  " + name)
    (output / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")
    print("Ready:", output)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist/offline")
    parser.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "APC40-build-cache")
    parser.add_argument("--visualizer", type=Path, help="Private offline visualizer assets")
    args = parser.parse_args()
    build(args.output.resolve(), args.cache.resolve(), args.visualizer)

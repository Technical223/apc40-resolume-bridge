"""Build a separate, unsigned macOS test app ZIP on any OS."""
import argparse
import json
from pathlib import Path
import plistlib
import stat
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
APP = "APC40 Bridge macOS Preview.app/Contents/"

def build(destination, require_native=False):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(destination)
    files = {
        APP + "MacOS/launcher": ROOT / "macos/launcher.sh",
        APP + "Resources/mac_bridge.py": ROOT / "macos/mac_bridge.py",
        APP + "Resources/desktop.py": ROOT / "macos/desktop.py",
        APP + "Resources/desktop.html": ROOT / "macos/desktop.html",
        APP + "Resources/surface.json": ROOT / "macos/surface.json",
        APP + "Resources/controller.jpg": ROOT / "bridge/ui/apc40-top.jpg",
        APP + "Resources/requirements.txt": ROOT / "macos/requirements.txt",
        APP + "Resources/core/apc_bridge.py": ROOT / "bridge/apc_bridge.py",
        APP + "Resources/core/config.json": ROOT / "bridge/config.json",
        APP + "Resources/resolume/APC40 BRIDGE EXAMPLE.xml": ROOT / "resolume/APC40 BRIDGE EXAMPLE.xml",
        "README.md": ROOT / "macos/README.md",
        "TESTER.md": ROOT / "macos/TESTER.md",
        "LICENSE": ROOT / "LICENSE",
    }
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    plist = dict(CFBundleName="APC40 Bridge macOS Preview", CFBundleDisplayName="APC40 Bridge macOS Preview",
                 CFBundleIdentifier="com.technical223.apc40bridge.preview", CFBundleExecutable="launcher",
                 CFBundlePackageType="APPL", CFBundleShortVersionString="0.2.0", CFBundleVersion="2",
                 LSUIElement=False, NSHighResolutionCapable=True,
                 NSAppTransportSecurity={"NSAllowsLocalNetworking":True})
    payloads = {name: path.read_bytes() for name, path in files.items()}
    for name in ("preview.html","prepare.py","launcher.py","physical-layout.json","room-current.glb","THIRD-PARTY-NOTICES.txt"):
        payloads[APP+"Resources/visualizer/"+name]=(ROOT/"bridge/visualizer"/name).read_bytes()
    native=False
    if sys.platform=="darwin":
        with tempfile.TemporaryDirectory(prefix="APC40-native-") as temp:
            outputs=[]
            for arch in ("arm64","x86_64"):
                output=Path(temp)/arch
                subprocess.run(["/usr/bin/xcrun","swiftc","-O","-target",arch+"-apple-macos11.0",str(ROOT/"macos/BridgeWindow.swift"),"-o",str(output)],check=True)
                outputs.append(str(output))
            output=Path(temp)/"BridgeWindow"
            subprocess.run(["/usr/bin/lipo","-create",*outputs,"-output",str(output)],check=True)
            subprocess.run(["/usr/bin/codesign","--force","--sign","-",str(output)],check=True)
            payloads[APP+"MacOS/BridgeWindow"]=output.read_bytes();native=True
    elif require_native:
        raise RuntimeError("The native macOS app must be built on macOS.")
    payloads[APP + "Info.plist"] = plistlib.dumps(plist)
    payloads[APP + "Resources/build.json"] = json.dumps({"source_commit": revision, "signed": False,
        "kind": "native-webkit-preview" if native else "source-only-preview", "version": "0.2.0-preview", "native_window":native}, indent=2).encode()
    payloads["Open Preview.command"] = b'#!/bin/sh\ncd "$(dirname "$0")" || exit 1\nexec "./APC40 Bridge macOS Preview.app/Contents/MacOS/launcher"\n'
    with zipfile.ZipFile(destination, "x", zipfile.ZIP_DEFLATED) as archive:
        for name, data in payloads.items():
            info = zipfile.ZipInfo("APC40-Bridge-macOS-Preview/" + name)
            info.create_system = 3
            mode = 0o755 if name.endswith(("/launcher", "/BridgeWindow", ".command")) else 0o644
            info.external_attr = (stat.S_IFREG | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    return destination

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(ROOT / "dist/APC40-Bridge-macOS-Preview.zip"))
    parser.add_argument("--require-native",action="store_true")
    args=parser.parse_args()
    print(build(args.output,args.require_native))

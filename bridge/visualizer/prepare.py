"""Build preview UVs from the saved active Arena output, preserving physical LED positions."""
import json
import math
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HOME = Path(__file__).resolve().parent
sys.path.insert(0, str(HOME))

def source_paths():
    documents = Path.home() / "Documents"
    if os.name == "nt":
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as key:
            documents = Path(os.path.expandvars(winreg.QueryValueEx(key, "Personal")[0]))
    arena = documents / "Resolume Arena"
    preferences = arena / "Preferences/AdvancedOutput.xml"
    name = ET.parse(preferences).getroot().get("presetFile", "")
    if not name or Path(name).name != name:
        raise ValueError("Save an Advanced Output preset in Arena first.")
    preset = arena / "Presets/Advanced Output" / (name + ".xml")
    return preferences, preset, name

def source_signature():
    preferences, preset, name = source_paths()
    return (name, preferences.stat().st_mtime_ns, preset.stat().st_mtime_ns,
            (HOME / "physical-layout.json").stat().st_mtime_ns)

def prepare():
    preferences, preset, name = source_paths()
    tree = ET.parse(preset)
    layout = json.loads((HOME / "physical-layout.json").read_text(encoding="utf-8"))
    size = tree.find(".//CurrentCompositionTextureSize")
    width, height = float(size.get("width")), float(size.get("height"))
    if not all(math.isfinite(x) and x > 0 for x in (width,height)):
        raise ValueError("Invalid composition dimensions")
    slices = {item.get("uniqueId"): item for item in tree.findall(".//DmxSlice")}
    missing = []
    mapped = set()
    for fixture in layout["fixtures"]:
        item = slices.get(fixture["sliceUid"])
        if item is None:
            missing.append(fixture["object"])
            continue
        points = [(float(point.get("x")), float(point.get("y")))
                  for point in item.findall("InputRect/v")]
        if len(points) != 4:
            continue
        pixel_params = item.find(".//ParamFixturePixels")
        if pixel_params is None:
            continue
        w = int(float(pixel_params.find("ParamRange[@name='Width']").get("value")))
        h = int(float(pixel_params.find("ParamRange[@name='Height']").get("value")))
        if w != 1 and h != 1:
            continue
        count = max(w, h)
        old = fixture["pos"]
        fixture["pos"] = []
        fixture["uv"] = []
        for index in range(count):
            t = (index + .5) / count
            u, v = (.5, t) if h >= w else (t, .5)
            x = (1-u)*(1-v)*points[0][0] + u*(1-v)*points[1][0] + u*v*points[2][0] + (1-u)*v*points[3][0]
            y = (1-u)*(1-v)*points[0][1] + u*(1-v)*points[1][1] + u*v*points[2][1] + (1-u)*v*points[3][1]
            fixture["uv"].append([x / width, 1 - y / height])
            position = index * (len(old)-1) / max(1, count-1)
            lower = int(position)
            upper = min(lower+1, len(old)-1)
            fixture["pos"].append([old[lower][axis] + (old[upper][axis]-old[lower][axis])*(position-lower) for axis in range(3)])
        fixture["pixels"] = count
        mapped.add(fixture["sliceUid"])
    layout["fixtures"] = [f for f in layout["fixtures"] if f["sliceUid"] in mapped]
    layout["comp"] = [int(width), int(height)]
    layout["preset"] = name
    modeled = {fixture["sliceUid"] for fixture in layout["fixtures"]}
    layout["outputFixtures"] = []
    for screen in tree.findall(".//screens/*"):
        screen_label = screen.find("Params/Param[@name='Name']")
        screen_name = screen_label.get("value", screen.get("name", "")) if screen_label is not None else screen.get("name", "")
        for item in screen.iter():
            if not item.tag.endswith("Slice") or item.find("InputRect") is None:
                continue
            points = [(float(p.get("x")), float(p.get("y"))) for p in item.findall("InputRect/v")]
            if len(points) < 3:
                raise ValueError("Unsupported output rectangle")
            params = item.find(".//ParamFixturePixels")
            w = int(float(params.find("ParamRange[@name='Width']").get("value"))) if params is not None else 0
            h = int(float(params.find("ParamRange[@name='Height']").get("value"))) if params is not None else 0
            uv = [[x/width,1-y/height] for x,y in points]
            label = item.find("Params/Param[@name='Name']")
            layout["outputFixtures"].append({"screen":screen_name,"screenUid":screen.get("uniqueId", ""),
                "lumiverse":screen.get("LumiverseId", ""),"slice":label.get("value", "") if label is not None else item.get("name", ""),
                "sliceUid":item.get("uniqueId"),"uv":uv,"width":w,"height":h,"pixels":w*h,"modeled":item.get("uniqueId") in modeled})
    target = HOME / "active-layout.js"
    temp = target.with_suffix(".tmp")
    temp.write_text("window.APC40Layout=" + json.dumps(layout, ensure_ascii=True) + ";", encoding="utf-8")
    os.replace(temp, target)
    print("Prepared", len(layout["fixtures"]), "physical fixtures from", name)

if __name__ == "__main__":
    if "--open" in sys.argv:
        import launcher
        launcher.open_preview()
    else:
        prepare()

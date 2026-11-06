"""Local model conversion; never execute scripts embedded in a Blender file."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

SUPPORTED = {".blend"}
MAX_MODEL = 256 * 1024 * 1024

def blender_path():
    found = shutil.which("blender")
    if found:
        return found
    roots = [Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Blender Foundation",
             Path("/Applications")]
    candidates = []
    for root in roots:
        if root.is_dir():
            candidates += list(root.glob("Blender [0-9]*/blender.exe"))
            candidates += list(root.glob("Blender*.app/Contents/MacOS/Blender"))
    return str(sorted(candidates)[-1]) if candidates else None

def convert_model(data, extension, executable=None):
    extension = extension.lower()
    if extension not in SUPPORTED:
        raise ValueError("Only BLEND uses the optional converter. GLB, OBJ and FBX import without Blender.")
    if not data or len(data) > MAX_MODEL:
        raise ValueError("Model must be nonempty and at most 256 MiB.")
    executable = executable or blender_path()
    if not executable:
        raise RuntimeError("Install Blender from blender.org, then reopen the visualizer. Conversion stays local; no model is uploaded online.")
    with tempfile.TemporaryDirectory(prefix="apc40-model-") as folder:
        folder = Path(folder)
        source, target = folder / ("source" + extension), folder / "model.glb"
        source.write_bytes(data)
        script = folder / "convert.py"
        script.write_text("""import bpy, sys
from pathlib import Path
source, target = map(Path, sys.argv[sys.argv.index('--')+1:])
if source.suffix == '.blend':
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
elif source.suffix == '.obj':
    bpy.ops.wm.obj_import(filepath=str(source))
elif source.suffix == '.fbx':
    bpy.ops.import_scene.fbx(filepath=str(source))
# Keep hidden objects so the editor can reveal them; source file is never saved.
bpy.ops.export_scene.gltf(filepath=str(target), export_format='GLB', use_visible=False,
                          use_renderable=False, export_extras=True, export_animations=False)
""", encoding="utf-8")
        command = [executable, "--background", "--factory-startup", "--disable-autoexec",
                   "--threads", "2", "--python-exit-code", "1", "--python", str(script),
                   "--", str(source), str(target)]
        try:
            result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
                                    timeout=180, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("Conversion exceeded three minutes and was stopped. Try a smaller model.") from error
        if result.returncode or not target.is_file():
            raise RuntimeError("Blender could not convert this model. Pack external textures into BLEND first; OBJ/FBX sidecar textures are not included.")
        if target.stat().st_size > MAX_MODEL:
            raise ValueError("Converted GLB exceeds 256 MiB. Simplify the source model.")
        output = target.read_bytes()
        if output[:4] != b"glTF":
            raise RuntimeError("Converter did not produce a valid GLB.")
        return output

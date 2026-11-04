# LED preview and output editor

[Home](../README.md)

Open **Visualizer** from the dashboard. It runs locally in your browser and is
optional. Keep automatic opening disabled unless you want the preview at startup.

## Input and mapping

1. Save the Advanced Output preset in Arena.
2. Enable Arena's composition Spout output.
3. On first use, enable the visualizer in **Settings** and choose camera setup.
   SpoutCam is downloaded directly from its publisher, checked against a pinned
   checksum, then registered through the Windows administrator prompt. Public
   installers do not redistribute the camera binary. Browser camera permission
   also needs your confirmation. OBS is not required.
4. Open Visualizer and choose SpoutCam. The input should match Arena's composition.

The bottom-right inset follows the saved preset's input rectangles, names,
fixture counts and composition aspect. Saved changes are checked every ten
seconds. The inset updates without reconnecting the camera or reloading the room.
Unsaved Arena edits are not read. An empty or renamed output is supported.

## Choose the fixtures used in the preview

Click **Edit output mapping**. The inset expands into an editor in the same page.

- Search by output, fixture name or Lumiverse ID. Names and raw Lumiverse IDs
  are read from Advanced Output; the editor does not rename anything in Arena.
- Toggle an entire output or an individual fixture with its checkbox.
- Click an outline to select it; click the selected outline again to toggle it.
- Select a fixture and choose **Edit selected fixture pixels** to toggle pixels
  directly in the inset. Pixel editing supports fixtures up to 4096 pixels.
- **Enable all** and **Disable all** operate on the current preset.
- **Done** returns to the normal preview. Changes save automatically in this
  browser, separately for each preset, using fixture IDs. Newly added fixtures
  start enabled. Export/import transfers a selection for the same preset.

Selection affects the preview only. It sends no MIDI, REST edits or DMX output.
The composition image remains visible behind its selected slice outlines.

## Space presets

Switch between several rooms in the same preview with **Space preset**. Each
space has its own room model, physical LED layout and, optionally, its own saved
Advanced Output preset. A space with a fixed preset previews your composition on
another rig without changing what Arena outputs. The choice is remembered in the
browser and can also be opened directly with `preview.html?space=<id>`.

Add `spaces.json` next to `preview.html`. The first space is the default; paths
must stay inside the visualizer folder. Without `output`, a space follows the
preset that is active in Arena. `mode` is `led` (default) or `projection`.

```json
{
  "spaces": [
    {"id": "led", "name": "Stage - LED", "model": "room-current.glb", "layout": "physical-layout.json"},
    {"id": "projection", "name": "Stage - projection", "model": "room-current.glb",
     "layout": "physical-layout.json", "mode": "projection"},
    {"id": "festival", "name": "Festival stage", "model": "spaces/festival/room.glb",
     "layout": "spaces/festival/physical-layout.json", "output": "spaces/festival/Festival.xml"}
  ]
}
```

Without `spaces.json` the preview behaves as before, with one room and no picker.
Fixture and pixel selections are saved per preset, so each space keeps its own.

## Projection spaces

An LED space shows LEDs only. A **projection** space shows no LEDs; instead each
steel-mesh shell in the room (material name containing `pletiv`, `mesh` or
`fence`) becomes a solid flat board with the same outline, and diffusers
(`difuz`, `diffus`) are hidden. The boards carry the composition source. In
**Projection boards** choose **Projector from audience** (one virtual projector at
the layout camera) or **Whole input on each board**, and set the brightness. Use
**Input crop** to show only part of the source. Projection is preview-only.

## Room and performance

The public package includes a small generic open-front room. **Import room model**
can display a local GLB model for the current session. Private show models and
compositions are not part of the public package. A room model alone does not
define physical LED positions: 3D LEDs require a `physical-layout.json` with
fixture IDs, pixel positions and camera settings matching the saved preset.
The inset and output editor work without any 3D fixture positions.

Room materials, ambient light, light spill and bloom are preview settings and are
stored in the browser. Model emission is disabled so static Blender materials do
not glow independently of video. Missing input is black; Test pattern is explicit.

Preview rendering and video capture are capped at 30 FPS. Rendering pauses in a
hidden tab. The loopback helper serves only viewer assets at `127.0.0.1:18741` and
exits about 90 seconds after its last tab heartbeat. A browser-suspended tab may
also expire; reopen Visualizer from Bridge. Large imported models still use GPU
memory, so close the preview if Arena needs those resources.

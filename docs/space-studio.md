# Space Studio — experimental scene editor

Open **APC40 Bridge → Visualizer → 3D Editor**. **Preview** returns to the same visualizer; no second application or installation is required. Both views load from the same `visualizer` folder. The editor stays in the same browser tab and uses the same local server and port. Switching views changes only the page path, not the IP address or application. The layout and 3D canvas resize with the browser window; no fullscreen mode is required.
It edits a local preview project, never Arena, Advanced Output or DMX.

## Build a space

1. **Import model**: GLB, OBJ and FBX open with libraries included in the app. No Blender, Python package download or internet connection is needed for these imports. Imported objects are added to the current collection. OBJ/FBX sidecar material and texture files are not imported; use embedded textures in GLB for reliable materials.
2. Add **Projection**, **LED panel**, **LED strip** or a **Box**. Select objects in the collection or by clicking the viewport. Rename them and set position, rotation, scale, video input slice and pixel counts. Dimensions use meters; a strip runs along local X. At most 4096 pixels are supported per object.
3. Use **Front / Back / Left / Right / Top / Bottom** for orthographic views, or **Perspective**. Middle-drag orbits, Shift + middle-drag pans, the wheel zooms, and **Frame** centers the selection. **G / R / S** chooses the move/rotate/scale gizmo; drag its handles. **1 / 3 / 7** switches axes, **5** toggles perspective, **F** frames. This is an object editor, not Blender's vertex/sculpt/animation toolset.
4. **Center pivot** puts a pivot at the geometry bounds center without moving the object in the scene. It uses a pivot parent in the collection, preserves UVs/children and supports Undo. The **eye** controls editor visibility. **Power / Include in preview** controls the final preview independently. Switching off a parent also excludes its children. An object can stay visible while editing yet be excluded from the preview.
5. Click **Preview** to inspect video on surfaces and pixels. Choose **Open video** for a local, muted looping video (H.264 MP4 or WebM recommended), **Camera** / **Capture screen** for live input, or explicitly choose **Test pattern**. Files are not uploaded; DXV clips need conversion to a browser-compatible format first. No input means black; the test pattern is generated content, not proof of Arena output. **Stop** releases input.
6. **Apply to visualizer** stores the project in this browser and returns to the visualizer. The next editor session reopens it. **Save project · GLB** downloads a portable copy with geometry and object settings; import it to continue on another machine. Browser data can be cleared, so keep a GLB backup.

Projects are kept per space ID in this browser. No upload or automatic sharing occurs. Selecting a saved slice controls the preview input; it does not create or rename output slices in Arena. Existing configured physical fixtures remain separate from objects added in the editor. Match the plane's proportions to the slice to avoid stretching.

## Optional native Blender files

Selecting **.blend** opens an explanation before any conversion. **Open official Blender download** goes to [blender.org](https://www.blender.org/download/). Install the standard app, return to the editor and choose **Convert locally**. On Linux, Blender must be on PATH. You may instead continue without Blender and import GLB/OBJ/FBX.

The optional converter runs Blender in the background only after consent, with embedded scripts disabled, two CPU threads and a three-minute timeout. It writes to a temporary folder, cleans up and never saves over the source. Pack external assets into the BLEND first. Blender is a separate large download; it is neither bundled nor silently installed. Conversion is not guaranteed for every Blender version, plug-in material or unsupported format.

## Performance and test status

Rendering is capped at 30 FPS and pauses in hidden tabs. A static editor redraws only when needed. Undo stores object states rather than serializing full geometry on every edit and retains up to 30 actions. Large imports and video still consume GPU/RAM; close the preview when Arena needs those resources.

This branch is experimental. Browser checks cover exact dimensions, row duplication, slice assignment, automatic recovery, and switching Preview ↔ 3D Editor with selection, orthographic view, snap and a local video loop preserved. OBJ/FBX import and GLB roundtrips have automated checks. Live Arena capture, optional Blender conversion on a clean computer, Mac hardware, compressed GLB extensions and arbitrary production models still need validation. The stable installed application is not changed by checking out this branch.

## Dimensions and arrays

**Dimensions · meters** sets the physical size along the object's local axes, including inherited scale. A plane has no thickness; its zero dimension is disabled. Geometry and UVs are preserved by changing scale.

**Duplicate into a row** creates 2–32 total objects, including the original. Choose the object's X/Y/Z axis and center-to-center spacing in meters. Rotation and parent scale are taken into account. The whole row is one Undo action. Copies share geometry/material resources to avoid multiplying GPU memory; object settings and transforms remain independent.

## View state, recovery and diagnostics

Camera position/orientation, orthographic framing, selection and snap settings are remembered in this browser session per space. Returning to Preview carries the camera orientation and the selected input. A local video of up to **128 MiB** is retained in browser storage and resumes as a muted loop at the previous playback position. Larger files must be selected again. Screen sharing needs another user confirmation; camera/screen input may need reconnecting in the editor. Capture permissions are never bypassed.

**Snap transforms** enables the chosen grid step (local transform units), 15° rotations and 0.1 scale increments. Inherited non-unit parent scales affect the physical distance of local snapping; use Dimensions for exact meters.

Edits automatically keep a local recovery after approximately two seconds of inactivity. Geometry is exported only when the object/geometry structure changes; transform/name/visibility edits save a small state record against that baseline. Recovery reopens automatically in this browser and space. It is not a substitute for a downloaded GLB: browser cleanup or storage limits can remove it. Storage failures show a message; no file folders or uploads are created.

The slice diagram highlights the selected object's source. Click an outline to select its first assigned object, or use **Video source slice** to assign a source. The label reports the saved output/slice and object count. Missing sources show a warning and are excluded from the editor preview instead of silently using the whole composition. This never edits Arena's mapping.

The input readout distinguishes decoded **source FPS** from **render FPS**, displays source dimensions and reports a static scene instead of pretending to render continuously. Browser support determines whether source-frame counts are available. Rendering pauses in hidden tabs.

The browser workflow was checked with a small model and a local H.264 loop. Missing slices show a warning; Stop returns the input to black. Large production models, live camera permissions and storage pressure still need validation before a public release.

## Wiring view and physical groups

**Output mapping** keeps each strip inside its physical output group. Groups explicitly named **OUTPUT 1** through **OUTPUT 16** are recognized automatically; Lumiverse IDs are never used as socket numbers. A physical output selector, including Unassigned, belongs to the whole group. Individual pieces show their inherited output and retain editable order and IN / OUT direction.

The 16-output profile has outputs 1–5 with ten 1 m strips each, 6–11 with five 2 m strips, and 12–16 with four 5 m neons. Actual pixel counts come from the saved mapping, including shorter pieces. DMX outputs are separate. Piece checkboxes specify what is used today: disabling five pieces in a ten-piece group leaves **5 / 10 in use**, without changing physical output ownership or Arena addresses.

Select multiple pieces with a **drag rectangle** over the output diagram, **Ctrl-click** to add/remove, or **Shift-click** for a range in the list. **Use selected / Do not use selected** changes the entire selection. Selection and enabled state are separate; selecting a piece never disables it.

Turn on **Wiring view** for a gray room with colored chains and IN / OUT labels. In the normal Visualizer, **double-click a modeled strip** to highlight it, show green IN / red OUT, and open **Reverse direction** beside it. Double-click empty 3D space or press **Escape** to dismiss it; the saved direction stays unchanged. Reversing updates the arrows and the video sampling along that strip in the preview. It does not reverse Arena's hardware output. Order and direction share the same saved settings as the mapper.

Assignments and direction save locally per preset and space, and are included in selection export/import. Existing direction settings are retained when fixed groups are recognized. Unknown group names can be assigned at group level; missing 3D positions are never invented. Export a selection to transfer or back it up. Original model geometry, actual pixel counts and Arena/DMX addressing are unchanged.

## Selecting objects and pixels

The **Scene collections** outliner is on the right, with object properties below it. Search by name or material, or open Environment, LEDs, Surfaces, Objects and Helpers. These are display collections: original object names, parenting and geometry stay intact. Recognized room parts are labeled Wall, Floor or Ceiling. Eye toggles editor visibility; power toggles inclusion in the result.

Above the viewport, **Select → LEDs** prevents room geometry from intercepting LED selection. Environment and Surfaces work the same way. Selected objects have an orange outline/bounds, an orange outliner row and a named status label. **H** hides the selected object; **Alt+H** reveals objects in the current selection scope. Undo restores visibility changes. Room walls are pickable from either side. Fog volumes and camera/reference helpers are hidden by default; enable **Show helper volumes / cameras** when needed.

**Solid** is the default editing view: neutral double-sided shading without imported textures or emission. **Materials** shows the model's original materials; Scene preview shows the mapped video. Solid shading does not rewrite UVs, materials or mesh geometry in the exported project. For dense meshes, selection uses an orange bounds box instead of generating expensive edges.

In Output mapping, thin fixtures have a small screen-space hit tolerance, and selecting an outline never disables it. Enable/disable uses the fixture checkbox. For exact pixels, select a fixture and choose **Edit selected fixture pixels**: the magnified numbered grid makes pixel 1 and the last pixel individually clickable. Use the range selector for long strips. Orange marks the selected fixture/pixel; changes save automatically.

## Pause the visualizer input

Use **Pause / Resume** beside the settings panel to hold the current input image while inspecting fixtures or editing the mapping. Camera movement, selection and mapping controls remain available. The output inset and LED/projection sampling use the same frozen frame; Arena and hardware output continue unchanged. Resume returns to live input, or continues the local video. Changing the input while paused keeps the frozen image until Resume.

A single snapshot is limited to 1280×720 to bound memory use. Its canvas and GPU texture are released on Resume. The pause is local to the current Visualizer page; opening the 3D Editor does not pause its separate preview input.

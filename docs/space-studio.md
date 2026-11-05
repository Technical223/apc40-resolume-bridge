# Space Studio — experimental scene editor

Open **Visualizer → Open Space Studio**. The editor stays in the same browser tab.
It edits a local preview project, never Arena, Advanced Output or DMX.

## Build a space

1. **Import model**: GLB, OBJ and FBX open with libraries included in the app. No Blender, Python package download or internet connection is needed for these imports. Imported objects are added to the current collection. OBJ/FBX sidecar material and texture files are not imported; use embedded textures in GLB for reliable materials.
2. Add **Projection**, **LED panel**, **LED strip** or a **Box**. Select objects in the collection or by clicking the viewport. Rename them and set position, rotation, scale, video input slice and pixel counts. Dimensions use meters; a strip runs along local X. At most 4096 pixels are supported per object.
3. Use **Front / Back / Left / Right / Top / Bottom** for orthographic views, or **Perspective**. Middle-drag orbits, Shift + middle-drag pans, the wheel zooms, and **Frame** centers the selection. **G / R / S** chooses the move/rotate/scale gizmo; drag its handles. **1 / 3 / 7** switches axes, **5** toggles perspective, **F** frames. This is an object editor, not Blender's vertex/sculpt/animation toolset.
4. The **eye** controls editor visibility. **Power / Include in preview** controls the final preview independently. Switching off a parent also excludes its children. An object can stay visible while editing yet be excluded from the preview.
5. Click **Preview** to inspect video on surfaces and pixels. Connect **Camera** or **Capture screen**, or explicitly choose **Test pattern**. No input means black; the test pattern is generated content, not proof of Arena output. **Stop** releases input.
6. **Apply to visualizer** stores the project in this browser and returns to the visualizer. The next editor session reopens it. **Save project · GLB** downloads a portable copy with geometry and object settings; import it to continue on another machine. Browser data can be cleared, so keep a GLB backup.

Projects are kept per space ID in this browser. No upload or automatic sharing occurs. Selecting a saved slice controls the preview input; it does not create or rename output slices in Arena. Existing configured physical fixtures remain separate from objects added in the editor. Match the plane's proportions to the slice to avoid stretching.

## Optional native Blender files

Selecting **.blend** opens an explanation before any conversion. **Open official Blender download** goes to [blender.org](https://www.blender.org/download/). Install the standard app, return to the editor and choose **Convert locally**. On Linux, Blender must be on PATH. You may instead continue without Blender and import GLB/OBJ/FBX.

The optional converter runs Blender in the background only after consent, with embedded scripts disabled, two CPU threads and a three-minute timeout. It writes to a temporary folder, cleans up and never saves over the source. Pack external assets into the BLEND first. Blender is a separate large download; it is neither bundled nor silently installed. Conversion is not guaranteed for every Blender version, plug-in material or unsupported format.

## Performance and test status

Rendering is capped at 30 FPS and pauses in hidden tabs. A static editor redraws only when needed. Undo stores object states rather than serializing full geometry on every edit and retains up to 30 actions. Large imports and video still consume GPU/RAM; close the preview when Arena needs those resources.

This branch is experimental. Basic browser editing and GLB export have been checked; OBJ/FBX import and GLB roundtrips have automated checks. Live Arena capture, optional Blender conversion on a clean computer, Mac hardware, compressed GLB extensions and arbitrary production models still need validation. The stable installed application is not changed by checking out this branch.

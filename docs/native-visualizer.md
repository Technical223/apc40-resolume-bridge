# Visualizer inside Bridge · development preview

[Home](../README.md) · [Scene editor](space-studio.md)

On Windows, choose **APC40 Bridge → Visualizer**. **Visualizer**, **Output mapping** and **3D Editor** share one embedded workspace, one local server and one asset folder. Chrome is not opened. The renderer is created only while this page is open and disposed when you leave it; closing the dashboard does not stop the MIDI bridge.

This branch is a development preview. The stable release has not been replaced. macOS keeps its existing browser preview; WebView2 is Windows-only.

## First use and existing projects

1. Microsoft **WebView2 Runtime** is required for the optional view. The bundled-runtime builder includes Microsoft's full x64 installer in `dependencies/MicrosoftEdgeWebView2RuntimeInstallerX64.exe`. On a machine missing the Runtime, run that installer manually, then use **Retry**. The source ZIP does not bundle it; use [Microsoft's download](https://developer.microsoft.com/microsoft-edge/webview2/). No Runtime installation is needed for MIDI-only use.
2. Camera permission belongs to Bridge, separately from Chrome. Confirm it yourself and select SpoutCam. OBS is not required. Existing SpoutCam setup and Arena Spout output requirements still apply. Screen capture requires a new system source selection.
3. To bring existing browser work across, open the original preview in that browser, choose **Workspace → Export workspace**, then **Workspace → Import workspace** inside Bridge. Save a GLB first if you want a separate scene backup. The original browser storage is never deleted.

Bridge uses a persistent WebView2 profile under `%LOCALAPPDATA%/APC40 Bridge/WebView2`, independent of the installation folder. Changing browser or clearing this profile does not preserve browser-local projects automatically.

A `.apcworkspace` file contains saved projects, local recovery, mapping, appearance and cached video across space IDs. It stays local and may contain private show material: review it before sharing. Imports replace matching keys; other projects remain. Invalid files are rejected before canonical projects are replaced. Limit: 512 MiB total, 256 MiB per record; this is not a media-library archive. Save GLB for a portable single scene.

Before native navigation, Retry or closing Bridge, the host asks the editor to flush local recovery. If saving fails, it stays open unless you explicitly choose to leave without recovery. Downloads use a native Save dialog. A renderer failure exposes Retry instead of silently discarding/reloading an open project.

## Runtime and privacy

Only the current token-protected `127.0.0.1` visualizer pages load inside the host. External links explicitly opened by the user go to the default browser. The host exposes no general filesystem or command-execution bridge to JavaScript. Microphone capture is denied. Workspace transfer does not upload anything; WebView2 itself follows Microsoft's Runtime update and service behavior.

The app uses the same WebGL renderer and input path as the browser version. This integration removes browser tabs, not rendering cost. Close the view when Arena needs the GPU. Direct Spout GPU reception and a native renderer are **not implemented** by this change. Live Arena/Spout performance, clean-PC Runtime installation and macOS parity require separate testing.

## Build and checks

`bridge/build-ui.ps1` fetches the pinned Microsoft WebView2 SDK, checks SHA-256 and copies the two managed DLLs, x64 loader and SDK license beside the EXE. `-DependencyCache` reuses downloads. The offline builder includes the pinned standalone Runtime installer; a changed vendor download fails checksum validation rather than silently accepting a new binary. The Runtime is installed manually if missing. [Microsoft's distribution guide](https://learn.microsoft.com/microsoft-edge/webview2/concepts/distribution) explains the dependency.

Run `python -m unittest discover -s tests -v`, `python tests/test_stop_process.py` and the Windows build. Test workspace export/import, failed-import preservation, scene recovery after leaving/reopening, same-window navigation, camera selection and WebView process release. Test the latter with Arena on target hardware before calling it show-ready.

## Next renderer

1. **Measure the existing path.** Repeat the same composition/model/input on target hardware, record Arena FPS, preview FPS, GPU load, RAM and capture latency. Keep an idle/closed-view baseline.
2. **Prototype direct Spout input separately.** Compare GPU copies and latency with SpoutCam. Keep the current path available until restart, device loss and source selection are reliable.
3. **Try a native renderer behind the same project data.** Retain GLB, scene metadata, mapping and saved projects. Compare one representative room before rewriting editor tools. Choose an engine based on measured results and redistribution/maintenance requirements.
4. **Bring macOS to parity.** Reuse project formats and UI where practical; assess a platform host and Syphon/capture independently. Collect local, manually shared diagnostics. Never imply a Windows build proves Mac support.
5. **Release only after migration and show tests pass.** Preserve MIDI isolation and user files, document supported versions, provide rollback. Consider professional features/support with contributors while retaining existing MIT rights.

Help with any one of these steps is welcome: [contributing](../CONTRIBUTING.md#build-the-next-version-together).

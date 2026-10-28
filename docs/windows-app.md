# Windows application

[English](windows-app.md) | [Česky](windows-app.cs.md) · [Home](../README.md)

## Files

- `bridge/ui/BridgeManager.cs`: native WinForms dashboard (.NET Framework); the dashboard itself does not need Python.
- `bridge/build-ui.ps1`: builds with the system C# compiler. The generated EXE is not tracked in Git.
- `bridge/APC40 Bridge.vbs`: source ZIP entry point; silently builds a missing EXE, then opens the dashboard.
- `bridge/manage.ps1`: shared status/start/stop/autostart/shortcut/restore actions.
- `bridge/runtime.ps1`: Python discovery and the local `runtime.json` path cache.
- `bridge/setup.ps1 -NoPopup -PrepareOnly`: prepares dependencies and configuration without starting or restarting the watcher.
- `bridge/package-release.ps1`: portable ZIP with the app, default configuration, preset, and documentation.
- `.github/workflows/windows.yml`: Windows tests, build, and a ZIP artifact in GitHub Actions.

## Behavior

The dashboard runs PowerShell without a console window and checks status asynchronously every five seconds. Python’s `--status-json` only lists available MIDI ports; it never opens them or takes them away from a running bridge. Readiness includes a read-only check of Arena’s MIDI settings and virtual port availability. “Bridge running” confirms the watcher process, not delivery of every MIDI message.

Start is idempotent: an existing watcher for this folder is left running. Start/stop and other mutations use a named mutex based on the installation path. Process identity is checked by `stop_bridge.ps1`. The dashboard also allows only one instance per installation.

Closing the window leaves the bridge running. Autostart creates a shortcut in the current user’s Startup folder targeting `APC40 Bridge.exe --autostart`. This mode starts only the watcher and exits; it does not run setup or display the dashboard.

Settings preserve unknown configuration keys, validate ports and numeric ranges, and save atomically using `File.Replace` with a backup. Restart the watcher to apply changes. Logs are read with shared access, limited to the last 64 KB. MIDI restore requires explicit confirmation, refuses to run while Arena is open, and does not stop anything if no backup exists.

Setup uses Python/mido/python-rtmidi/loopMIDI. Creating the virtual ports remains a manual loopMIDI step. Missing ports produce a specific instruction instead of a hidden five-minute wait. A complete installation on a pristine Windows machine has not been tested.

The app, setup messages, and primary documentation use English. Legacy Czech launcher filenames remain for compatibility; new launchers are `AUTOSTART_ON.bat`, `AUTOSTART_OFF.bat`, `DEBUG.bat`, and `RESTORE_RESOLUME.bat`.

## Build

From the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File bridge/build-ui.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File bridge/package-release.ps1
py -3 -m unittest discover -s tests -v
py -3 tests/test_stop_process.py
```

The default package output is `dist/APC40-Bridge-Windows.zip`. For another build, select a different output directory or move the previous ZIP first. Packages include the repository’s clean default configuration, not local state, PIDs, logs, or runtime caches. Preserve your own `config.json` and `state.json` when updating an existing installation.

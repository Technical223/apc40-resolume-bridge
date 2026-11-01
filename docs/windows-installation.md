# Windows installation

[Home](../README.md) · [Arena MIDI setup](navod.md#arena-midi-preferences) · [Controller Studio](controller-studio.md)

## Setup EXE

1. Download **[APC40-Bridge-Setup.exe](https://github.com/Technical223/apc40-resolume-bridge/releases/latest)**. Close Arena for first setup and close the bridge dashboard/editor before updating.
2. Run it and click **Install**. If loopMIDI is missing, complete its license and Windows permission prompts.
3. Open **APC40 Bridge → Start bridge**. Use **Controller Studio** to edit lighting.
4. Check [Arena MIDI preferences](navod.md#arena-midi-preferences), including physical APC input/output **on** and **Alternate Ableton Live Mode**.

Requires Windows 10/11 x64 and Windows .NET Framework. Python and MIDI libraries are bundled; no separate Python, pip or developer tools are needed. The app installs for the current user. The loopMIDI driver may need administrator permission. The installer is not code-signed.

## Internet and offline use

Setup needs internet only if loopMIDI is missing. It downloads the installer directly from the publisher and checks its SHA-256 digest.

For offline installation, place the unmodified publisher installer at **dependencies/loopMIDISetup.exe** beside the bridge setup EXE. The same checksum is checked. loopMIDI is not included in public assets because redistribution requires its author's prior permission; its own license applies.

## MIDI ports

Setup prepares **APC VIRT A** and **APC VIRT B**, or your existing configured names. Other ports are preserved. If loopMIDI was already running without these ports, close and reopen it once. Setup does not terminate an existing loopMIDI session.

## Updates and removal

Updates preserve configuration and existing profiles and back up configuration and core app files. Close the GUI before updating. If Arena is open and its preferences need changing, close Arena and run **Install / repair**.

Remove the app through **Windows Installed Apps**. Configuration, state, profiles, backups, logs and the small uninstaller remain. loopMIDI stays installed for other applications. To restore pre-bridge Arena settings, close Arena and use **Restore Arena MIDI** before uninstalling.

## Portable and source versions

**APC40-Bridge-Portable.zip** includes the app and runtime. Extract it into a permanent folder and open **APC40 Bridge.exe**. It still needs loopMIDI and the named ports; use the setup EXE for automatic dependency installation.

From a source ZIP, open **bridge/APC40 Bridge.vbs** to build the dashboard. Source setup may download dependencies; it is separate from the bundled-runtime release.

For developers, **bridge/build-offline.py** builds and verifies the setup EXE, portable ZIP and checksums on Windows with Python 3.12+. Dependencies and hashes are recorded in **bridge/offline-dependencies.lock.json**. Runtime checks do not replace testing Arena with your composition and hardware.

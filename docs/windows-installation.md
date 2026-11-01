# Windows installation

[Home](../README.md) · [Controller Studio](controller-studio.md)

## Recommended: setup EXE

1. Download **APC40-Bridge-Setup.exe** from the latest Windows release.
2. Close the bridge dashboard/editor before updating. Close Arena for the first setup so its MIDI preferences can be prepared.
3. Run the setup EXE and click **Install**.
4. If loopMIDI is missing, setup downloads the publisher's installer and checks its SHA-256 digest before running it. Complete the loopMIDI license and Windows permission prompts.
5. Setup creates the required per-user MIDI port names, copies the app and its private runtime, and adds Desktop/Start Menu shortcuts.
6. Use **APC40 Bridge** for the dashboard, or open **Controller Studio** to configure lighting. Check Arena's **Alternate Ableton Live Mode** as shown in the [MIDI guide](navod.md#arena-midi-preferences).

No separate Python, pip, developer tools, or visible command window is required. The app installs for the current user. The MIDI driver installer may require administrator permission. Windows 10/11 x64 and the included Windows .NET Framework are required.

The current package pins CPython 3.12.10, mido 1.3.3, python-rtmidi 1.5.8 and packaging 25.0. CPython 3.12 matches the available native MIDI wheel. Dependencies are downloaded at build time and checksum-verified; they are already present inside the setup EXE.

## Internet and offline use

The app runtime and Python MIDI libraries are bundled. A first install needs internet only when **loopMIDI is missing and no local installer is supplied**. If loopMIDI is already installed, setup does not download it.

For offline installation on your own machine, put the unmodified publisher installer at **dependencies/loopMIDISetup.exe** beside the setup EXE. Setup verifies the same pinned checksum and opens it locally.

The repository owner's **APC40-Bridge-Offline-Local.zip** contains this arrangement for local use. It is not a public GitHub asset: loopMIDI's license prohibits redistribution without the author's prior written permission. The public installer downloads it directly from the publisher instead. The publisher's own license remains applicable.

## Automatic ports

Setup prepares **APC VIRT A** and **APC VIRT B** in loopMIDI's per-user settings before starting it. Existing port names and unrelated settings are preserved. Custom bridge port names are read from the existing configuration during an update.

If loopMIDI was already running without the required ports, close and reopen loopMIDI once to load them. Setup does not terminate an existing loopMIDI session, because other applications may be using its ports.

## Updating and removal

Updates preserve config.json and existing profiles and create a timestamped backup of configuration and core app files. If the GUI is open, setup asks you to close it before copying files. Preparation never turns off the physical APC MIDI input/output required by the user-tested configuration.

The app appears in Windows Installed Apps. Its uninstaller stops this installation's watcher and removes package files and its own shortcuts. User configuration, state, profiles, backups and logs are retained, along with the small uninstaller. loopMIDI remains installed because other programs may use it.

## Portable ZIP

**APC40-Bridge-Portable.zip** contains the same app and private runtime. Extract it into a permanent folder and open **APC40 Bridge.exe**. First-time MIDI preparation still needs loopMIDI and the two named ports. Bundled setup mode does not download Python or install pip packages.

## Building and verifying

Run **bridge/build-offline.py** on Windows with Python 3.12 or newer. The build produces a setup EXE, a portable ZIP and checksums. It verifies embedded extraction and imports the MIDI libraries using the extracted private runtime. Source ZIP users can still use the original dashboard bootstrap/build scripts.

The installer is not code-signed. No Arena-latency guarantee is made: the runtime, GUI and integration tests do not replace testing a real composition with its normal effects and devices.

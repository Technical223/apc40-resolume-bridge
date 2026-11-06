# Contributing to APC40 Bridge

Thanks for helping. This project bridges an **Akai APC40 mkII** and **Resolume Arena** with MIDI feedback, a visual controller editor and an optional LED preview. The goal is a simple, stable bridge, so small and well-tested changes are preferred over new features.

By taking part you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Ways to help

- **Test on real hardware.** Reports from a physical APC40 mkII with Arena are the most valuable feedback, because CI cannot verify LEDs, encoders or Arena's MIDI feedback.
- **Mac testers:** use the [macOS test build feedback](https://github.com/Technical223/apc40-resolume-bridge/issues/new/choose) issue form and follow [macos/README.md](macos/README.md).
- **Bugs and ideas:** open an issue with your Windows/macOS version, Arena version, the steps you took, and what happened.
- **Security problems:** do not open a public issue. See [SECURITY.md](SECURITY.md).

## Build the next version together

I'm looking for people who want to help turn this into a reliable tool for real shows: graphics/rendering, direct Spout input, C#/WebView2 integration, macOS parity, UI and hardware testing. AI-assisted development is welcome; explain your changes, review the generated code and include reproducible checks.

Start with a small bug or propose an approach in an [issue](https://github.com/Technical223/apc40-resolume-bridge/issues/new/choose). Include what you would like to work on. No private show files are needed. The [renderer roadmap](docs/native-visualizer.md#next-renderer) describes the next steps and their validation gates.

The current project remains MIT licensed. A future professional package, support or paid additions are possibilities to discuss with collaborators, not a change to existing users' rights or a promised commercial release.

## Before you open a pull request

1. Open an issue first for anything larger than a small fix, so we can agree on the approach.
2. Keep the bridge simple. Keep MIDI routing independent of the optional local visualizer and its WebView2 host. Discuss additional services, REST/OSC control or runtime dependencies before adding them.
3. Do not change the user-verified Arena MIDI routing (physical APC40 Input **and** Output on, APC VIRT A input, APC VIRT B output, Alternate Ableton Live Mode). See [docs/navod.md](docs/navod.md).
4. Preserve user data on updates: `config.json`, `state.json`, custom ports, mappings and controller profiles. Unknown config keys must survive a save.
5. Do not rename MIDI ports, preset identifiers, configuration keys or the original Czech batch filenames.

## Development setup

- Python 3.12 is used in CI (Windows). The macOS preview needs Python 3.9+.
- Install test dependencies:

  ```
  python -m pip install mido python-rtmidi
  ```

- Run the tests (no MIDI hardware needed; they do not change Arena settings):

  ```
  python -m unittest discover -s tests -v
  python tests/test_stop_process.py
  ```

  One management test is skipped unless loopMIDI is already running.

- Windows dashboard and installer build notes: [docs/windows-app.md](docs/windows-app.md) and [docs/windows-installation.md](docs/windows-installation.md).

GitHub Actions runs the Windows tests and builds the package for pull requests that touch `bridge/` or `tests/`. The macOS workflow covers the `macos/` preview.

## Language and documentation

- English is the default for the app, messages, `README.md`, documentation and diagrams.
- `README.cs.md` and `docs/*.cs.md` are optional Czech versions. If you change the landing page or instructions, keep both versions consistent and use the real English button labels.
- macOS-specific material is English-only.
- Do not publish private paths, usernames or show media in screenshots or logs.

## Honest validation

State exactly what you tested. Simulated tests do not prove behavior on a physical APC40 or in Arena. Write "not verified on hardware" rather than claiming a fix that was only tested in software.

## Contributors

- **[Technical223](https://github.com/Technical223)** – author and maintainer; design, hardware testing and releases.
- **Anthropic Claude** – AI-assisted development and documentation.
- **OpenAI ChatGPT / Codex** – AI-assisted development.

All contributions are released under the project's [MIT License](LICENSE).

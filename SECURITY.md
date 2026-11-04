# Security Policy

## Supported versions

Only the [latest release](https://github.com/Technical223/apc40-resolume-bridge/releases/latest) receives fixes. Please update before reporting.

| Version | Supported |
|:---|:---:|
| Latest release (Windows) | Yes |
| Older releases | No |
| macOS test builds (experimental) | Best effort |

## Reporting a vulnerability

**Please do not report security issues in public issues, discussions or pull requests.**

Report privately through GitHub: open the repository's **Security** tab and choose **Report a vulnerability**, or go directly to <https://github.com/Technical223/apc40-resolume-bridge/security/advisories/new>.

Include, if you can:

- the affected version and operating system,
- what an attacker could do and the steps to reproduce,
- any proof of concept or relevant log lines (remove personal paths and usernames first).

This is a one-person hobby project, so there is no guaranteed response time. You will get a reply as soon as possible, and confirmed issues will be fixed in a new release and credited if you wish.

## Scope

In scope:

- the bridge engine, Windows dashboard, Controller Studio, installer and setup scripts in this repository,
- the local LED visualizer server and page,
- the macOS preview and its diagnostic export.

Out of scope (report to their publishers): Resolume Arena, loopMIDI, SpoutCam, Python and third-party libraries.

## Notes for users

- The Windows installer is **unsigned**. Download it only from this repository's Releases page.
- Setup downloads loopMIDI and the optional SpoutCam from their publishers and verifies their checksums.
- Diagnostics stay on your computer; nothing is uploaded automatically. Review a diagnostic ZIP before sharing it.

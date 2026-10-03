# Third-party notices - Imperial Radio Directorate v3

## CCP Games

© 2014 CCP hf. All rights reserved. 'EVE', 'EVE Online', 'CCP', and all related logos and images are trademarks or registered trademarks of CCP hf.

EVE Online and the EVE logo are the registered trademarks of CCP hf. All rights are reserved worldwide. EVE Online, the EVE logo, EVE and all associated logos and designs are the intellectual property of CCP hf. All artwork, screenshots, characters, vehicles, storylines, world facts or other recognizable features of the intellectual property relating to these trademarks are likewise the intellectual property of CCP hf.

This is an unofficial fan-made tool, not made, endorsed or supported by CCP.

Where this app uses CCP's Game Data, ESI or EVE SSO, it does so under CCP's
Developer License Agreement: https://developers.eveonline.com/license-agreement

## Data and services this app uses

- This app uses no CCP Game Data, ESI, SDE or EVE SSO.

## Python libraries (direct dependencies)

| Library | License |
| --- | --- |
| FastAPI | MIT |
| Starlette (via FastAPI) | BSD-3-Clause |
| uvicorn[standard] | BSD-3-Clause |
| Pydantic | MIT |
| mutagen (audio tag / duration reading) | GPL-2.0-or-later |

Each of these pulls in further packages of its own (for example `certifi`,
`urllib3`, `idna`, `websockets`); see each package's own metadata for their
licenses. This list covers direct dependencies only.

Optional / build-time, not part of a plain source install:

- PySide6 (the `desktop` extra, used by the Windows desktop shell): LGPL-3.0-only
  OR GPL-2.0-only OR GPL-3.0-only. Shipping it inside an installer carries LGPL
  conditions that the installer project must meet.
- PyInstaller (builds the Windows installer): GPL-2.0-or-later with a special
  exception that allows building and distributing programs under any license.
- pytest, httpx, ruff (the `dev` extra): development only, never shipped.

**mutagen is GPL-2.0-or-later (a copyleft license).** If this app is ever
distributed to others, that distribution has to satisfy the GPL's terms, which
constrains which license this project's own code can be released under. This is
the one dependency in the v3 suite with that effect - the other apps do not use it.

## This project's own license

Not yet chosen. Until a license file is added, all rights in this project's own
code are reserved by its author.

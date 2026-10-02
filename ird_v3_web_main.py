#!/usr/bin/env python3
"""Entry point: launches IRD v3's real web server.

Named `ird_v3_web_main.py` — the `<prefix>_web_main.py` convention every
Imperial app uses, hand-matched from the sibling v3 apps' own entry
points. No `_supervisor`/self-restart-after-update wiring yet (a later,
cross-app TODO item, not scoped into this build).

Single uvicorn worker — this app has no shared in-memory state to worry
about (no caching at all, confirmed directly with the owner: every
request re-scans the filesystem fresh), but matching the sibling apps'
own single-worker convention costs nothing and avoids ever having to
reconsider it later.

No `sys.frozen` packaged-build handling yet — IRD v3 has no PyInstaller
packaging story at all yet. This is a plain dev-checkout entry point
until that lands.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import uvicorn  # noqa: E402

from config import Config  # noqa: E402
from web.app import create_app_from_config  # noqa: E402

if __name__ == "__main__":
    config = Config.load()
    app = create_app_from_config(config)
    uvicorn.run(app, host=config.web_host, port=config.web_port, reload=False)

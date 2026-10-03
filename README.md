# Imperial Radio Directorate v3

Clean-room rewrite of IRD — an EVE Online-themed local media player
(music + serialized stories, with in-universe ad breaks). Fourth of the
four Imperial Apps to get the v3 treatment, following
`ImperialIndustryDirectorate-v3`, `ImperialLogisticDirectorate-v3`, and
`ImperialSkillDirectorate-v3`. Unlike those three, IRD has zero EVE
ESI/SDE dependency.

Legacy IRD (`../ImperialRadioDirectorate/`) remains the reference
implementation until v3 replaces it. See `CLAUDE.md` for the architecture
pattern and non-negotiables, and `docs/PART_INVENTORY.md` for the current
build phase.

## Running the test suite

```
pytest
```

`src/` is on the import path automatically (`pyproject.toml`'s
`pythonpath = ["src"]`) — no install step needed.

## Running the app

```
python ird_v3_web_main.py
```

Serves the Phase 6 functional-skeleton frontend (plain, un-styled HTML/JS
— real visual design is a separate later pass) at the configured
`IRD_WEB_PORT` (default 8060). For local dev/preview with isolated
synthetic test content instead of your real `music/`/`stories/` folders,
use the root-level `ird-v3-test` launcher (`../.claude/test_launchers/ird_v3_test_main.py`,
port 18061).

## Legal and third-party notices

© 2014 CCP hf. All rights reserved. 'EVE', 'EVE Online', 'CCP', and all related logos and images are trademarks or registered trademarks of CCP hf.

EVE Online and the EVE logo are the registered trademarks of CCP hf. All rights are reserved worldwide. EVE Online, the EVE logo, EVE and all associated logos and designs are the intellectual property of CCP hf. All artwork, screenshots, characters, vehicles, storylines, world facts or other recognizable features of the intellectual property relating to these trademarks are likewise the intellectual property of CCP hf.

This is an unofficial fan-made tool, not made, endorsed or supported by CCP.

This project uses no CCP Game Data, ESI, SDE or EVE SSO; the notice above
covers its use of EVE-related names and theming.

Third-party libraries and data sources are credited in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). This project's own license has
not been chosen yet.

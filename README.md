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

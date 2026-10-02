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

Not yet available — Phase 5 (the web app) has not shipped.

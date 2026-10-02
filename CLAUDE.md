# CLAUDE.md — IRD v3.0

Clean-room rewrite of Imperial Radio Directorate. 100% fresh code.

## What this is

A jukebox/tuning device, themed around EVE Online — a deliberate "vanity
project" (the owner's own framing), not a functional gap-filler like
IID/ISD/ILD. **Zero EVE ESI dependency, zero SDE dependency** — a pure
local media player with no EVE Online API dependency at all.

## Read these first

| Before you… | Read |
|---|---|
| touch anything | this file, non-negotiables below |
| reason about *what IRD v3 does*, or the full resolved design | `C:\Users\vasea\.claude\plans\misty-cuddling-moler.md` — the approved architecture/scope plan, including how it diverges from a conflicting pasted draft spec |
| plan a phase / roadmap | `docs/PART_INVENTORY.md` |
| see history / rulings | `docs/ROADMAP_HISTORY.md` |
| see open gaps | `../TODO.md`'s "IRD" heading |

## Non-negotiables

- **Clean-room:** legacy IRD (`../ImperialRadioDirectorate/`) is a
  blueprint to read, never to paste. Verified technical facts (Starlette's
  built-in Range-request support, the `.mp4`/`.m4a` MIME equivalence,
  `mutagen`'s tag-reading behavior) may carry over as *facts*, re-verified
  fresh, never as copied code.
- **Decomposition (C3):** distinct responsibility → its own file
  (50-150 LOC expected); a coherent algorithm (the ad scheduler, the
  story-sequencing walk) stays whole.
- **Invariants:** invalid states unconstructible types, not runtime
  assertions (e.g. `StoryPartNumber` can't be < 1, `D100Roll` can't be
  outside [1, 100]).
- **Persistence:** typed JSON + atomic temp-swap + integer `schema_version`.
  No SQLAlchemy/ORM — and unlike the sibling v3 apps, no sqlite3 either;
  IRD v3 has no SDE to read, so there's no exception to carve out.
- **Testing:** fresh native `pytest`. Iron Gate green first-pass.
- **Build once, cry once. No time constraints, ever.**
- **This gaming PC is a test environment only** — process and data. The Pi
  is the only production server; never touch it.
- **Git & Workflow:** commit and push after each distinct, working build
  step; never stockpile changes. Master branch only — branch only when the
  owner explicitly asks. Never touch a version string/CHANGELOG unless
  asked.
- **No ESI/SDE dependency, same as legacy** — stays a pure local media
  player, themed around EVE.
- **Legal grounding carries over unchanged:** never extract/scrape audio
  from the installed EVE client (CCP ToS ban, actively enforced). Safe
  sources only: AI-generated original audio, or the owner's own
  legitimately-owned files.
- **Dual-shell (Phase 7, not yet built):** Windows-native desktop shell
  spawning a local web instance by default, `--remote-url` override for
  Pi/shared access — same shape as the other three v3 apps' shells,
  hand-matched not shared.
- **Do not start frontend (Phase 6) work without the owner** — standing
  instruction, owner's own words, 2026-10-01.

## What changed vs. legacy IRD (resolved 2026-10-01, see the plan file for full detail)

- The legacy car-radio/tuning-dial **visual design is out** — the
  interaction model (tune between channels, no track list) stays, restyled
  to fit EVE's own visual language. Real visual design deferred to a live
  session after Phase 6's functional skeleton exists.
- Two tunable channel kinds: **Music** (folder-per-station, same as
  legacy) and **Stories** (exactly one channel, series play in order,
  parts within a series always sequential, position persists across
  restarts).
- Two distinct ad/snippet roll mechanisms: Music keeps a **plain 25%
  check** (no dice framing — owner's explicit call); Stories uses an
  **explicit d100 roll, 1-50 triggers**. Both pick from the same shared
  `commercials_and_snippets/` pool.

## Layout

- `src/config.py` — frozen config (env + overrides), fail-fast validation.
  No ESI/SDE fields at all.
- `src/primitives/` — `TrackId`, `StationName`, `StorySeriesId`,
  `StoryPartNumber`, `D100Roll`, `DomainRuleViolation`.
- `src/schema/` — `PlaybackResumeState` (the one real persisted document).
- `src/storage/` — atomic typed-JSON persistence (`json_store.py`).
- `src/adapters/library/` — music/commercials scanning (`scanner.py`) and
  story-series scanning (`story_scanner.py`).
- `src/solvers/` — `ad_scheduler.py` (music's plain 25% check, Stories'
  d100 roll) and `story_sequence.py` (the pure story-sequencing walk) —
  no I/O, no `adapters/` import at all (DAG-enforced).
- `src/services/` — `playback_service.py` (the two channel services +
  shared interlude/track lookup) and `resume_state_store.py` (typed
  persistence + the throttled-checkpoint policy).
- `src/web/` — FastAPI app factory (`app.py`), routers (`music.py`,
  `stories.py`, `tracks.py`), `security.py` (CSRF), `errors.py` (domain
  exception → HTTP mapping), `serializers.py`. **No frontend/static assets
  yet** — Phase 6 does not start without the owner.
- `ird_v3_web_main.py` — the real entry point.
- `desktop_shell/` — (Phase 7, not yet built) thin PySide6 wrapper.
- `music/`, `stories/`, `commercials_and_snippets/` — the three content
  folders (each has its own explanatory `README.md`). Only
  `commercials_and_snippets/` is meant to ship real committed content;
  `music/`/`stories/` stay personal and gitignored.
- `tests/` — unit tests and the Iron Gate structural audit
  (`test_iron_gate.py`).

## Layer DAG & Rules

`config < primitives < schema < {storage, adapters} < solvers < services <
web` — no `resolvers` layer (no dogma-graph concept in this domain, same
narrower DAG shape as ILD v3).

- `src` is on the path via `pyproject.toml` (`pythonpath = ["src"]`). Run
  the suite with `pytest`.
- Detailed history and architectural rulings live strictly in
  `docs/ROADMAP_HISTORY.md`.
- Active gap list lives strictly in `../TODO.md`.

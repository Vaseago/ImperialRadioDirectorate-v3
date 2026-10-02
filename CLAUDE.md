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
  asked. **`../GIT_WORKFLOW.md`'s `release`-tag policy applies here too**
  (it's a cross-app standing doc) — a live app-update check compares
  against `refs/tags/release`, never `master`'s raw tip; moving that tag
  is the owner's call alone, never Claude's own confidence. **Verified
  fact (2026-10-02):** `release` is an ANNOTATED tag (`git tag -a`) — any
  code resolving it with `git rev-parse` MUST peel with `^{commit}`
  (`web/app_update.py`'s own `_resolve_release_tag`), or it silently
  resolves to the tag object's own hash instead of the commit, which can
  never compare equal to `HEAD` — a real bug found live against this
  app's own tag, not caught by mocked tests.
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
- **Phase 6 functional skeleton shipped 2026-10-01** — plain, un-styled
  HTML/JS wired to the real endpoints (`src/web/static/`). Real visual
  design is a separate later live session — a draft spec from the owner
  is filed at `docs/design_spec_draft/FRONTEND_VISUAL_DESIGN_DRAFT.md`,
  not yet applied.

## What changed vs. legacy IRD (resolved 2026-10-01, see the plan file for full detail)

- The legacy car-radio/tuning-dial **visual design is out** — the
  interaction model (tune between channels, no track list) stays, restyled
  to fit EVE's own visual language. Real visual design deferred to a live
  session after Phase 6's functional skeleton exists (now shipped —
  `docs/design_spec_draft/` holds the draft to work from).
- Two tunable channel kinds: **Music** (folder-per-station, same as
  legacy) and **Stories** — **re-architected 2026-10-01** to tune
  per-series, exactly like Music's stations (the owner picks which story
  to hear), not one combined channel that auto-cycles through every
  series. Each series remembers its own resume position and a `listened`
  flag independently; finishing one auto-advances to the next unlistened
  series, stopping (not resetting/looping) once every series has been
  heard at least once. See `docs/ROADMAP_HISTORY.md`'s own dated entry
  for the full resolution.
- Two distinct ad/snippet roll mechanisms: Music keeps a **plain 25%
  check** (no dice framing — owner's explicit call); Stories uses an
  **explicit d100 roll, 1-50 triggers**, still rolled once per part end
  regardless of the per-series rework above. Both pick from the same
  shared `commercials_and_snippets/` pool.

## Layout

- `src/config.py` — frozen config (env + overrides), fail-fast validation.
  No ESI/SDE fields at all.
- `src/primitives/` — `TrackId`, `StationName`, `StorySeriesId`,
  `StoryPartNumber`, `D100Roll`, `DomainRuleViolation`.
- `src/schema/` — `PlaybackResumeState` (the one real persisted document
  this app needs — a tuple of per-series `SeriesResumeState`, keyed by
  `series_id`, each with its own part/elapsed/listened state).
- `src/storage/` — atomic typed-JSON persistence (`json_store.py`).
- `src/adapters/library/` — music/commercials scanning (`scanner.py`) and
  story-series scanning (`story_scanner.py`).
- `src/solvers/` — `ad_scheduler.py` (music's plain 25% check, Stories'
  d100 roll) and `story_sequence.py` (`resume_part_for_series`,
  `next_part_in_series`, `pick_next_unlistened_series` — the pure
  per-series resume/advance logic) — no I/O, no `adapters/` import at all
  (DAG-enforced).
- `src/services/` — `playback_service.py` (the two channel services +
  shared interlude/track lookup) and `resume_state_store.py` (typed
  persistence + the per-series throttled-checkpoint policy +
  `mark_listened`).
- `src/web/` — FastAPI app factory (`app.py`), routers (`music.py`,
  `stories.py`, `tracks.py`, `app_update.py`), `security.py` (CSRF),
  `errors.py` (domain exception → HTTP mapping), `serializers.py`,
  `app_update.py` (git check/pull), `supervised_restart.py` (the
  self-restart gate), `poller/app_update_poll.py` (periodic check, no
  WebSocket — IRD v3 has no hub, unlike the sibling v3 apps; the frontend
  just polls `GET /api/app-update/status`), `static/` (Phase 6's
  functional-skeleton frontend — plain HTML/JS, mounted last so the API
  routers always take precedence).
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

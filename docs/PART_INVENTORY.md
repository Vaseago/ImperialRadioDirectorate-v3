# IRD v3 — Part / Phase Inventory

Approved architecture/scope plan: `C:\Users\vasea\.claude\plans\misty-cuddling-moler.md`.

## Phase 1 — Foundation

- [x] `src/config.py` — frozen `Config` snapshot (music/stories/interludes
  dirs, data dir, web port), env + `config_overrides.json` resolution,
  fail-fast on an uncreatable data dir. Zero ESI/SDE surface, unlike the
  sibling v3 apps' own `config.py`.
- [x] `src/primitives/errors.py` — `DomainRuleViolation`.
- [x] `src/primitives/ids.py` — `TrackId`, `StationName`, `StorySeriesId`,
  `StoryPartNumber`, `D100Roll` (each invariant enforced at construction).
- [x] `src/schema/_coerce.py` — per-field `from_dict` coercion helpers.
- [x] `src/schema/playback_resume_state.py` — `PlaybackResumeState`, the
  one real persisted document this app needs (Stories-channel resume
  position).
- [x] `src/storage/json_store.py` — atomic typed-JSON envelope persistence,
  hand-matched from ISD v3's own copy.
- [x] `music/`, `stories/`, `commercials_and_snippets/` — the three
  top-level content folders, each with an explanatory `README.md`.
- [x] `tests/unit/test_iron_gate.py` — structural audit (no SQL/ORM
  anywhere, frozen+slotted dataclasses, layer DAG, Manager Isolation Law
  stub, ruff-clean). 42/42 tests green, Iron Gate clean first-pass.

## Phase 2 — Library adapters

- [x] `src/adapters/library/models.py` — `Track` (wraps `TrackId`/
  `StationName`, re-derived from legacy IRD's own `library/models.py`).
- [x] `src/adapters/library/scanner.py` — music + commercials scanning
  (`mutagen` tag read, filename fallback, folder-per-station derivation).
  Verified real Gemini-sourced suggestion against the actual `mutagen`/
  stdlib behavior 2026-10-01: nothing changed here (extensions/fallback
  already matched), but it surfaced a real Phase 5 MIME-mapping gap — see
  that phase's own bullet below.
- [x] `src/adapters/library/story_scanner.py` — walks `stories/<series>/`,
  derives part order from the filename's trailing digit run (numeric sort,
  not string sort — `alien_invasion10` sorts after `alien_invasion2`). A
  file with no trailing digits is skipped, not guessed at.

## Phase 3 — Solvers

- [x] `src/solvers/ad_scheduler.py` — music's plain 25% check
  (`should_play_interlude_after_music_track`), Stories' explicit d100 roll
  (`should_play_interlude_after_story_part`, 1-50 triggers). Both take an
  injected `random.Random` for deterministic tests.
- [x] `src/solvers/story_sequence.py` — `resolve_next_story_position`, pure
  "given current series+part, what's next" walk. Deliberately operates on
  plain `StorySeriesId`/`StoryPartNumber` tuples, never the real
  `adapters.library.StorySeries` — the layer DAG forbids `solvers/` from
  importing `adapters/` at all.

## Phase 4 — Services

- [x] `src/services/playback_service.py` — `MusicChannelService`
  (list stations, pick a track avoiding immediate repeat),
  `StoriesChannelService` (resume-aware current position, advance,
  per-position track lookup), shared `pick_interlude()` (same pool for
  both channels).
- [x] `src/services/resume_state_store.py` — `PlaybackResumeStateStore`
  (typed persistence) + `ResumeCheckpointManager` (throttled-write
  policy: once per `min_interval_seconds` unless `force=True`).

## Phase 5 — Web

- [x] `src/web/app.py` — `create_app(config)` factory (DI — tests build an
  app against an isolated `Config`, never the real filesystem), stores the
  two channel services + the `ResumeCheckpointManager` on `app.state`.
  **No caching anywhere** — confirmed directly with the owner, 2026-10-01:
  every request re-scans fresh, so there's no rescan endpoint at all
  (legacy IRD's own cached-`app.state` + explicit `/rescan` model doesn't
  carry forward).
- [x] `src/web/routers/music.py` — `GET /api/music/stations`,
  `GET /api/music/stations/{station}/next` (returns a 1-or-2-item
  `items` list: an interlude first if the 25% roll triggers, then the
  picked track — all scheduling stays server-side).
- [x] `src/web/routers/stories.py` — `GET /api/stories/current` (resume
  position, never rolls the interlude dice), `POST /api/stories/advance`
  (same `items`-list shape as music, using the 50% d100 roll),
  `POST /api/stories/checkpoint` (the one real state-changing write,
  CSRF-guarded).
- [x] `src/web/routers/tracks.py` — `GET /api/tracks/{id}/stream`,
  cross-pool lookup via `services.find_track_by_id` (a small Phase 4
  extension). Explicit extension→MIME override table (`.mp4`→`audio/mp4`,
  `.aac`→`audio/aac`, `.flac`→`audio/flac`) — verified live 2026-10-01 that
  stdlib `mimetypes` gets all three wrong for an `<audio>` element,
  resolving the gap flagged during Phase 2's Gemini-note review.
- [x] `src/web/security.py` — `require_same_origin_header`
  (`X-IRD-Request`), re-derived from legacy IRD's own.
- [x] `src/web/errors.py` — `register_exception_handlers`, hand-matched
  from ISD v3's own (`DomainRuleViolation`→400, `ValueError`→400,
  `FileNotFoundError`→404, `StorageError`→500) — no router needs a bare
  `try`/`except`.
- [x] `ird_v3_web_main.py` — the real entry point, hand-matched from the
  sibling apps' own `*_web_main.py`.

All 5 backend phases are now complete (112/112 tests passing, Iron Gate
clean first-pass).

**Mid-build revision, 2026-10-01**: Stories re-architected to tune
per-series (like Music's stations) instead of one combined auto-cycling
channel — see `docs/ROADMAP_HISTORY.md`'s own dated entry for the full
resolution. Touches Phase 1's schema, Phase 3's solver, Phase 4's
service, and Phase 5's `stories.py` router; all re-shipped the same
session, 139/139 tests passing.

## Phase 6 — Frontend (functional skeleton)

- [x] Station/channel tuning UI wired to the real endpoints — functional
  only, un-styled placeholder (`src/web/static/`). Real visual design is
  a separate later live session — draft spec filed at
  `docs/design_spec_draft/FRONTEND_VISUAL_DESIGN_DRAFT.md`, not yet
  applied. Verified live via the `ird-v3-test` root-level launcher
  (142/142 tests passing, Iron Gate clean first-pass).

**Added outside the phase plan, 2026-10-02**: the "Check for App Update"
feature (git-pull self-update, clean-room from IID v3's own), including a
real bug fix (annotated `release`-tag peeling) found live — see
`docs/ROADMAP_HISTORY.md`'s own dated entry. 175/175 tests passing, Iron
Gate clean first-pass. Shipped but not yet marked `release` — pending the
owner's sign-off.

## Phase 7 — Desktop shell

- [ ] Dual-shell pattern (own port, spawns local web instance by default,
  `--remote-url` override), hand-matched from the sibling v3 apps' shells.

See `docs/ROADMAP_HISTORY.md` for build rulings and history as each phase
lands.

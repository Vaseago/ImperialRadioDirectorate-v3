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

- [ ] `src/adapters/library/scanner.py` — music + commercials scanning
  (`mutagen` tag read, filename fallback, folder-per-station derivation).
- [ ] `src/adapters/library/story_scanner.py` — walks `stories/<series>/`,
  derives part order from filename numeric suffix.

## Phase 3 — Solvers

- [ ] `src/solvers/ad_scheduler.py` — music's plain 25% check, Stories'
  explicit d100 roll (1-50 triggers).
- [ ] `src/solvers/story_sequence.py` — pure "given current series+part,
  what's next" walk.

## Phase 4 — Services

- [ ] `src/services/playback_service.py` — orchestrates scanner +
  scheduler + resume-state store.
- [ ] `src/services/resume_state_store.py` — periodic checkpoint writer.

## Phase 5 — Web

- [ ] FastAPI app + routers (library listing, stream endpoint, resume-state
  read/write, rescan), CSRF guard (`X-IRD-Request`).
- [ ] Explicit extension→MIME override table for the stream endpoint
  (not relying on stdlib `mimetypes` alone) — verified live 2026-10-01
  that `.mp4` guesses as `video/mp4` (legacy's own known issue), `.aac`
  guesses as the non-standard `audio/vnd.dlna.adts`, and `.flac` guesses
  as the older `audio/x-flac`; override all three to standard audio MIME
  types for maximum browser compatibility.

## Phase 6 — Frontend (functional skeleton) — NOT started without the owner

- [ ] Station/channel tuning UI wired to the real endpoints — functional
  only, real visual design is a separate later live session.

## Phase 7 — Desktop shell

- [ ] Dual-shell pattern (own port, spawns local web instance by default,
  `--remote-url` override), hand-matched from the sibling v3 apps' shells.

See `docs/ROADMAP_HISTORY.md` for build rulings and history as each phase
lands.

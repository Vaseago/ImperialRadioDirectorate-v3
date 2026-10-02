# IRD v3 — Roadmap History

## 2026-10-01 — Phase 1: config/primitives/schema/storage foundation

Scope confirmed with the owner across several rounds of questions after a
pasted draft spec conflicted with legacy IRD's own already-shipped,
test-verified design decisions (the tuning-dial UI with no track list, the
per-track dice-roll ad scheduler, a shared ad/snippet pool) — see the
approved plan file for the full resolution. Key confirmed decisions this
phase's types encode:

- Two tunable channel kinds: **Music** (folder-per-station, same as legacy)
  and **Stories** (exactly one channel, cycles every series in order,
  parts within a series always sequential).
- Two distinct ad/snippet roll mechanisms, deliberately NOT unified:
  **Music** keeps legacy's plain 25% check (no dice framing, owner's own
  call after being asked directly). **Stories** uses an explicit d100 roll,
  1-50 triggers, 51-100 doesn't — the owner's own D&D-dice framing,
  confirmed literally ("roll it 1-50 and 51-100").
- Stories' playback position persists across restarts ("as close as
  possible" to where it was left off) — Music stays ephemeral, no
  persisted position (legacy's own "tune and get a random pick" behavior,
  unchanged).

Shipped: `config.py` (`Config.load`, frozen snapshot, zero ESI/SDE surface
— this app has none, matching legacy's own smaller `config.py`),
`primitives/errors.py` (`DomainRuleViolation`), `primitives/ids.py`
(`TrackId`, `StationName`, `StorySeriesId`, `StoryPartNumber` — each
>= 1 enforced at construction, not a runtime assertion — and `D100Roll`,
range-checked [1,100] with a `.triggers(threshold)` method so the exact
d100 mechanic stays visible and testable), `schema/_coerce.py` +
`schema/playback_resume_state.py` (`PlaybackResumeState`, the one real
persisted document this app needs), `storage/json_store.py` (atomic
typed-JSON envelope, hand-matched from ISD v3's own copy — generic infra,
not domain logic). The three top-level content folders (`music/`,
`stories/`, `commercials_and_snippets/`) created with explanatory
`README.md`s per the owner's own ask ("I want it to be clear as to what is
going into the folder").

42/42 tests passing, Iron Gate clean first-pass (no SQL/ORM anywhere in
`src/` — unlike the sibling v3 apps, IRD v3 has no SDE to read, so there's
no sqlite3 exception at all; frozen+slotted dataclasses; layer DAG
`config < primitives < schema < {storage, adapters} < solvers < services <
web`, no `resolvers` layer — same narrower DAG shape as ILD v3, no
dogma-graph concept here; Manager Isolation Law check stubbed with an
empty allowlist, no Store/Manager pair exists yet; `ruff check` clean).

**Left in Phase 1**: nothing — Phase 1 is complete. Phase 2 (library
adapters: music/commercials scanning, story-series scanning) is next.

## 2026-10-01 — Phase 2: adapters/library/ (scanner, story_scanner)

Shipped: `adapters/library/models.py` (`Track`, re-derived from legacy
IRD's own `library/models.py` — wraps `TrackId`/`StationName` instead of
bare strings), `adapters/library/scanner.py` (`scan_library_dirs` — real
verified facts carried forward from legacy: `sha1(relative_path)[:16]`
track-id scheme, `mutagen.File(path, easy=True)` tag read with a
cleaned-filename fallback, folder-per-station derivation with a "General"
catch-all — used for both `music/` and `commercials_and_snippets/`),
`adapters/library/story_scanner.py` (`scan_story_dirs` — new: each
`stories/` subfolder is a series, parts ordered by the trailing digit run
in the filename via regex, NOT a string sort, so `alien_invasion10` sorts
after `alien_invasion2`; a file with no trailing digits is skipped rather
than guessed at; series themselves sort alphabetically by folder name).

The owner passed along a Gemini-drafted note mid-phase ("Universal Audio
Support" for Phase 2/5) asking to confirm broad format support, filename
fallback, and dynamic MIME mapping. Verified directly against this repo's
own `config.SUPPORTED_AUDIO_EXTENSIONS` and a live `mimetypes.guess_type()`
check rather than taking it at face value: the extension list and
filename-fallback behavior were already exactly what it asked for (no
change needed), but the MIME-mapping point was real and new — confirmed
`.mp4` guesses as `video/mp4`, `.aac` as the non-standard
`audio/vnd.dlna.adts`, `.flac` as the older `audio/x-flac`. Folded into
Phase 5's own scope (see `PART_INVENTORY.md`) rather than acted on here,
since Phase 2 has no HTTP/MIME layer at all.

Tests use real synthetic silent `.wav` files generated on the fly (the
`wave` stdlib module, same real-file-not-mocked technique legacy IRD
verified), not mocks — 54/54 tests passing, Iron Gate clean first-pass
(ruff-clean over the new `adapters/` layer too).

**Left in Phase 2**: nothing — Phase 2 is complete. Phase 3 (solvers: the
ad-roll scheduler, story-sequencing walk) is next.

## 2026-10-01 — Phase 3: solvers/ (ad_scheduler, story_sequence)

Shipped: `solvers/ad_scheduler.py` (`should_play_interlude_after_music_track`
— a plain 25% check, no dice framing; `should_play_interlude_after_story_part`
— an explicit d100 roll via `roll_d100()`, 1-50 triggers via
`D100Roll.triggers()` from Phase 1 — both take an injected `random.Random`
so tests assert the exact boundary condition rather than a long-run
statistical rate) and `solvers/story_sequence.py`
(`resolve_next_story_position` — the pure "what plays next" walk: starts
at the first series' first part when nothing has played yet, advances
within a series, moves to the next series once one finishes, wraps around
to the first series after the last one finishes so the Stories channel
loops rather than stopping, and degrades gracefully — not a crash — if a
stored resume position references a series/part that no longer exists).

A real DAG decision made while building this: `story_sequence.py`
deliberately takes only `StorySeriesId`/`StoryPartNumber` tuples, never
the real `adapters.library.StorySeries`/`StoryPart` from Phase 2 — the
layer DAG (`config < primitives < schema < {storage, adapters} < solvers
< services < web`) forbids `solvers/` from importing `adapters/` at all.
`services/` (Phase 4) will build the plain id-tuple structure this solver
consumes from a real scan, call the solver, then map its answer back to
the real `Track` for playback.

75/75 tests passing, Iron Gate clean first-pass.

**Left in Phase 3**: nothing — Phase 3 is complete. Phase 4 (services:
orchestration + the resume-state checkpoint writer) is next.

## 2026-10-01 — Phase 4: services/ (playback_service, resume_state_store)

Shipped: `services/resume_state_store.py` (`PlaybackResumeStateStore` —
typed `JsonStore` wrapper, the Manager Isolation Law's real
persisted-document Store; `ResumeCheckpointManager` — the throttled-write
policy on top of it, once per `min_interval_seconds` (default 15s) unless
`force=True`, "as close as possible," not continuous — the owner's own
words) and `services/playback_service.py` (`MusicChannelService` —
station listing + random-track-pick avoiding immediate repeat, a verified
UX fact carried forward from legacy; `StoriesChannelService` —
resume-aware `current_position()` that validates a saved checkpoint
still points at real content before trusting it, falling back to the very
first position if a series/part was deleted since; `advance()` wraps
Phase 3's pure solver; shared `pick_interlude()` used by both channels
from the one `commercials_and_snippets/` pool, confirmed directly with
the owner there's no separate story/music interlude distinction).

95/95 tests passing (real synthetic WAV files on disk, same technique as
Phase 2's scanner tests — not mocks), Iron Gate clean first-pass.

**Left in Phase 4**: nothing — Phase 4 is complete. Phase 5 (the FastAPI
web app + routers, including the explicit MIME-mapping gap flagged during
Phase 2) is next.

## 2026-10-01 — Phase 5: web/ (app factory, routers, security, errors)

A real architecture question surfaced before building this phase and was
confirmed directly with the owner: Phase 4's services re-scan the
filesystem fresh on every call with no caching, which makes legacy IRD's
"scan once at startup, cache in `app.state`, explicit rescan action"
model meaningless here — nothing is ever cached to invalidate. Owner's
call: keep it that way (always fresh, no rescan endpoint at all), rather
than retrofitting caching into Phase 4 to match legacy's model.

Shipped: `web/app.py` (`create_app(config)` factory, DI-friendly — tests
build an app against an isolated `Config`; stores the two Phase 4
services + a `ResumeCheckpointManager` on `app.state`), `web/errors.py`
(hand-matched from ISD v3's own — `DomainRuleViolation`→400 with the
`rule` field surfaced, `ValueError`→400, `FileNotFoundError`→404,
`StorageError`→500, so a bad request like `part_number: 0` comes back as
a clean 400, not a raw 500), `web/security.py` (`require_same_origin_header`,
re-derived from legacy IRD's own `X-IRD-Request` CSRF mitigation),
`web/serializers.py` (shared track/position JSON shapes), and three
routers:

- `routers/music.py` — stations list + `next` (1-or-2-item `items`
  response: interlude first if the 25% roll triggers, then the picked
  track).
- `routers/stories.py` — `current` (never rolls the interlude dice —
  resuming shouldn't surprise the listener with an ad before anything's
  even playing again), `advance` (same `items` shape as music, using the
  50% d100 roll), `checkpoint` (the one real state-changing write, the
  only CSRF-guarded route — matches legacy's own precedent of guarding
  only the actual state-mutating endpoint, not every POST).
- `routers/tracks.py` — the shared cross-pool stream endpoint
  (`services.find_track_by_id`, a small Phase 4 extension — searches
  music, interludes, and every story part for one id, since a single
  stream URL serves any pool). Carries the explicit MIME-override table
  flagged during Phase 2's Gemini-note review: `.mp4`→`audio/mp4` (legacy's
  own known issue), `.aac`→`audio/aac` (stdlib guesses the non-standard
  `audio/vnd.dlna.adts`), `.flac`→`audio/flac` (stdlib guesses the older
  `audio/x-flac`).

`ird_v3_web_main.py` (the real entry point) hand-matched from the sibling
apps' own `*_web_main.py`.

112/112 tests passing — real `TestClient` requests against the real ASGI
app (not mocks), including a genuine `Range: bytes=0-99` request
confirmed returning `206`/`Content-Range`, a 403 on a missing CSRF header,
and a 400 (not a 500) on an out-of-range `part_number`. Iron Gate clean
first-pass (one new `_FORBIDDEN_STORE_IMPORTS` entry —
`PlaybackResumeStateStore` — added now that `web/` actually exists; one
new ruff per-file-ignore for `web/errors.py`'s docstring table, same
exception ISD v3 carries for the identical shape).

**Left in Phase 5**: nothing — Phase 5 is complete, and with it, every
backend phase (1-5) of this build. **All 112 tests passing. Standing
instruction from the owner, 2026-10-01: Phase 6 (the frontend) does not
start without the owner.**

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

## 2026-10-01 — Stories re-architected: tuned per-series, not one combined channel

The owner pasted a visual design spec + two reference images for Phase 6
mid-session (filed as a draft for the later design pass —
`docs/design_spec_draft/`) and, discussing Screen A's channel selector,
raised a real functional requirement that conflicts with the shipped
Phase 1/3/4/5 design: Stories should be tuned **per series**, like
Music's stations (pick exactly which story to hear), not one combined
channel that auto-cycles through every series in a fixed order. Resolved
directly with the owner across two rounds of questions:

- Each story series now remembers its **own** resume position
  independently (`schema.SeriesResumeState`, replacing the old singleton
  `PlaybackResumeState`) — switching between stories never clobbers
  another story's progress. Schema version bumped 1→2 (clean break, no
  real persisted data on this gaming-PC test environment to migrate).
- Each series also tracks a `listened` flag, set once it's been heard
  through to its end. Finishing a series auto-advances into the next
  series that hasn't been heard yet (`solvers.story_sequence.
  pick_next_unlistened_series` — forward search from just after the
  finished series, wrapping around once) — **owner's own words**: "it
  will start the next story that hasn't been listened to yet."
- Re-tuning into an already-`listened` series restarts fresh at part 1,
  not at its old end-of-story position (`resume_part_for_series`).
- Once every series has been heard at least once, auto-advance **stops**
  — owner's explicit call, not a reset-and-loop of the whole library and
  not an infinite repeat of the last series. The listener must manually
  tune into a story to keep going.
- Marking a series `listened` is always an immediate, unthrottled write
  (`ResumeCheckpointManager.mark_listened`) — a completion milestone, not
  a periodic position tick; losing it to a crash before the next
  throttled checkpoint would wrongly un-complete an already-heard story.
  Each series' own periodic position checkpoint is now throttled
  independently (a `dict[str, float]` of last-write times, not one global
  clock), so tuning between two stories within one's throttle window
  never blocks the other's write.

Shipped: `schema/playback_resume_state.py` rewritten (`SeriesResumeState`
+ `PlaybackResumeState` as an immutable tuple of per-series entries, with
`for_series`/`listened_series_ids`/`with_series` helpers),
`solvers/story_sequence.py` rewritten (`resume_part_for_series`,
`next_part_in_series`, `pick_next_unlistened_series` — replacing the old
single global `resolve_next_story_position` walk),
`services/resume_state_store.py` (`ResumeCheckpointManager.checkpoint`
now throttles per-series; new `mark_listened`),
`services/playback_service.py` (`StoriesChannelService` rewritten:
`list_series`/`tune_in`/`advance` replacing `current_position`/
`current_elapsed_seconds`/`advance`'s old signature; new
`StorySeriesSummary`/`StoriesAdvanceResult` result types),
`web/routers/stories.py` rewritten (`GET /series`, `GET /series/{id}`
replacing `GET /current`; `POST /advance` response now carries
`series_completed`).

All Stories-touching tests rewritten to match (`test_playback_resume_state.py`,
`test_story_sequence.py`, `test_resume_state_store.py`,
`test_playback_service.py`, `test_stories_router.py`) — 139/139 tests
passing, Iron Gate clean first-pass.

## 2026-10-01 — Phase 6: frontend functional skeleton

Shipped with the owner live, after the Stories re-architecture above:
plain, un-styled HTML/JS wired to the real endpoints
(`src/web/static/index.html`, `js/api.js`, `js/musicChannel.js`,
`js/storiesChannel.js`, `js/app.js`), mounted in `web/app.py` via
`StaticFiles` (a `_NoCacheStaticFiles` subclass forcing
`Cache-Control: no-cache` so a rebuild's JS isn't served stale from
browser heuristic caching — hand-matched fact from ISD v3's own
`web/app.py`, a real bug it hit during its own desktop-shell packaging).
Station and story-series lists are always re-fetched from the server,
never hardcoded — a new `music/`/`stories/` subfolder (or an
`extra_*_dirs` override) shows up with no frontend change, confirmed live
(added a folder while the server was running, reloaded, it appeared).
Explicitly a placeholder per the standing plan — real visual design
(`docs/design_spec_draft/`) is a separate later pass.

Verified live via a new `ird-v3-test` root-level test launcher
(`.claude/test_launchers/ird_v3_test_main.py`, port 18061 — seeds
isolated synthetic silent-WAV music/stories/interlude content, never
touching the real gitignored `music/`/`stories/` folders): music
tune-in/auto-advance, Stories per-series tune-in, mid-series resume,
auto-advance to the next unlistened series on completion, the
already-listened restart-at-part-1 behavior, and the full-library
"every story heard, stop" state — all confirmed against the real running
app in a browser, not just unit tests.

142/142 tests passing, Iron Gate clean first-pass.

**Left in Phase 6**: nothing functional — the real visual design pass
(`docs/design_spec_draft/FRONTEND_VISUAL_DESIGN_DRAFT.md`) is still
ahead, and Phase 7 (the desktop shell) hasn't started.

## 2026-10-02 — App-update feature (git-pull self-update), clean-room from IID v3

Owner's ask: bring IRD v3 the same "Check for App Update" capability IID
v3 already has live on the Pi (self-restart-after-pull, confirmed working
2026-08-29). Clean-room re-derived from IID v3's own `web/app_update.py`
/ `web/supervised_restart.py` / `web/poller/app_update_poll.py` /
`web/routers/app_update.py` (read as a blueprint, not copied) — same
"check and ask" two-step flow (`GET /status`, `POST /check`, `POST
/pull`), same `../GIT_WORKFLOW.md` `release`-tag policy, same
`SUPERVISED_RESTART_OK` gate (set only by `_supervisor/supervisor.py`'s
`_start()` — a self-restart is only ever attempted on a
supervisor-managed process; everywhere else, including this repo's own
`ird-v3-test` launcher and a bare `python ird_v3_web_main.py` run, a pull
installs but leaves the restart to the operator).

**One deliberate simplification vs. IID v3**: no WebSocket hub. IID v3's
poller broadcasts `app_update.pending_changed` over a `ConnectionHub` it
already has for other reasons; IRD v3 has no WebSocket infrastructure at
all and nothing else that would justify building one just for this
admin-adjacent feature. The frontend instead just polls `GET
/api/app-update/status` once on load — the same posture the legacy
(pre-v3) ISD/ILD apps took, per IID v3's own `SHARED_ARCHITECTURE.md`.

**A real bug found live, not by the mocked unit tests** (testing against
this app's own freshly-pushed `release` tag, 2026-10-02): `release` was
created as an ANNOTATED tag (`git tag -a`, the normal `-m`-message form),
and a bare `git rev-parse refs/tags/release` resolves to that tag
OBJECT's own hash, not the commit it points to — the two can never be
equal, so `check_for_update` would have reported "update pending" forever,
even the instant after a real pull landed exactly on the tagged commit.
Fixed with `^{commit}` peeling syntax (`refs/tags/release^{commit}`),
which is also a safe no-op for a lightweight tag. Locked in with a real
(non-mocked) git-repo integration test, since every mocked test just
hands back whatever fake hash it's told to and physically cannot exercise
real git ref-resolution semantics going wrong — worth checking whether
IID v3's own `release` tag is lightweight or annotated, since an
annotated tag there would carry the identical latent bug.

Shipped: `web/app_update.py` (pure git check/pull, the annotated-tag fix
above), `web/supervised_restart.py` (the gate + `trigger_self_restart`),
`web/poller/app_update_poll.py` (periodic check, no broadcast),
`web/routers/app_update.py` (the three routes), `web/app.py` (lifespan
wiring — the poller's `run_forever()` task starts/cancels with the app;
unconditionally constructed, not config-gated, since git operations don't
touch `Config`), and a minimal frontend panel (`static/js/appUpdate.js` +
an `#app-update-panel` section in `index.html`) — Check/Pull buttons, a
confirm dialog before pulling, no visual design (matches Phase 6's own
placeholder posture).

A real `release` tag now exists on this repo's own GitHub remote,
pointing at the Phase 6 commit (`a5dd504`) — **owner's own explicit
request**, 2026-10-01 ("commit, push, and tag so it can be updated
through the git"), the first real exercise of `../GIT_WORKFLOW.md`'s
policy for this app. This app-update feature's own commit sits on
`master`, verified (175/175 tests passing, Iron Gate clean, live-checked
against the real tag in a browser) but **not yet marked `release`** —
moving that tag is the owner's call alone, flagged here per the policy's
own "proactively flag it, every time" rule.

175/175 tests passing, Iron Gate clean first-pass.

## 2026-10-02 — CCP trademark notice and third-party notices (IRD)

IRD uses no CCP Game Data, ESI, SDE or EVE SSO, so the Developer License's
section 7.1 notice is not strictly required here; the README and new
`THIRD_PARTY_NOTICES.md` carry CCP's trademark statement plus an "unofficial
fan-made tool" line anyway, since the app is EVE-themed. No in-app footer (the
frontend is still the un-styled skeleton; revisit when the visual design lands).

**Real finding: `mutagen` is GPL-2.0-or-later.** It is IRD's audio-tag dependency
and the only copyleft dependency in the v3 suite. If IRD is ever distributed to
others, that distribution must satisfy the GPL, which constrains which license
IRD's own code can use. Flagged in `THIRD_PARTY_NOTICES.md`; the license choice
itself is the owner's (root `TODO.md`, public-release checklist).

Guard: `test_ccp_notice.py` fails if the notices disappear or the GPL flag is
dropped. Full suite 177 passing, Iron Gate clean.

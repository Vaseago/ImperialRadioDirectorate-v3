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

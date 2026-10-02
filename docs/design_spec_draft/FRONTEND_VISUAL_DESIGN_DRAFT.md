# Frontend visual design — draft, not yet applied

Filed 2026-10-01. The owner pasted this spec + two reference images (now
alongside this file) mid-session, ahead of Phase 6's functional skeleton —
the standing plan (`CLAUDE.md`, `docs/PART_INVENTORY.md`) says real visual
design is a separate later pass, after the functional skeleton exists.
Owner's call once asked directly: build the functional skeleton first
(shipped this same session — plain HTML/JS in `src/web/static/`, wired to
the real endpoints), apply this design after. **Not yet applied — this
file is the brief to work from when that later design pass happens.**

The owner also clarified live: the two screens are a *design idea*, not a
literal spec — folder/content names in the mockups don't need to match
this app's real `music/`/`stories/`/`commercials_and_snippets/` naming.

## Screen A — Master Channel Selector (overview state)

- Heavy dark-metal casing, gold inlay, deep crimson backing — classified
  imperial-security feel.
- Vertical rotating cylindrical selector for the main content categories
  (this app's real categories: Music stations and the Stories series
  picker — see `docs/ROADMAP_HISTORY.md`'s 2026-10-01 entry for why
  Stories became a per-series tunable "station" model rather than one
  combined channel).
- Side telemetry panel: active channel status (e.g. "SECURE BROADCAST —
  RELAY KX-9") and an encryption/clearance readout (e.g. "ENCRYPTION:
  ACTIVE — LEVEL RED") — flavor text, not real security.

See `screen_a_channel_selector.jpg`.

## Screen B — Active Playback & Frequency State (unified stream view)

- Top: a glowing gold Amarr Imperial Seal (the eagle), anchor of the
  layout.
- Center: a permanent, live horizontal frequency waveform pulsing with
  the audio stream, with a central tuning cursor.
- Bottom: monospaced metadata — "NOW PLAYING", elapsed/total time, and a
  "SIGNAL STATUS: SECURE BROADCAST — LOCKED" readout.
- Replaces a static logo during playback with constant live visual
  feedback.

See `screen_b_playback.jpg`.

## Known gaps to resolve when this is actually built

- Real frontend functional behavior now exists to design against:
  `GET /api/music/stations` / `GET /api/music/stations/{station}/next`,
  `GET /api/stories/series` / `GET /api/stories/series/{id}` /
  `POST /api/stories/advance` / `POST /api/stories/checkpoint` — see
  `src/web/routers/` for the exact shapes.
- The waveform in Screen B needs a real data source — the raw audio
  buffer isn't exposed anywhere yet (no Web Audio API analyser node in
  the Phase 6 skeleton); this is new scope for the design pass, not
  something already wired up.
- Reconcile the "rotating cylindrical selector" interaction (Screen A)
  with Stories needing to show per-series metadata (listened flag, part
  count) — the mockup doesn't address a picker with that much per-item
  state.

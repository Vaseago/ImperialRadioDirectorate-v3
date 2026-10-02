# commercials_and_snippets/

One shared pool for everything that isn't a music track or a story part:
commercials/ad jingles AND any future in-universe radio-news snippets both
go here, mixed together — they're treated identically by the scheduler, so
there's deliberately no separate folder for each kind.

This pool is what gets played as a "break":

- **Music**: after each track ends, there's a plain 25% chance the next
  thing played is a random item from this folder instead of another track.
- **Stories**: after each part ends, there's a 50% chance (a 1d100 roll,
  1-50 triggers) a random item from this folder plays before the next part.

Flat folder, no subfolders needed — anything dropped in here is eligible to
be picked for either kind of break.

This folder's real content IS committed to git (same as legacy IRD's own
`music_library_commercials/`) — once real audio exists, it ships with every
install, unlike `music/`/`stories/` which stay personal and uncommitted.

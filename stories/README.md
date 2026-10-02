# stories/

Serialized story content goes here. Each **subfolder is one story series**
— e.g. `stories/alien_invasion/`. Inside a series folder, name each part so
it sorts in the order it should play: `alien_invasion1.mp3`,
`alien_invasion2.mp3`, `alien_invasion3.mp3`, etc. Parts always play in
that order, never shuffled.

There is exactly one "Stories" channel, which plays every series in order
(all of one series' parts before moving to the next series). Your place in
the current story is remembered across app restarts.

Supported formats: same as `music/` — `.mp3`, `.ogg`, `.oga`, `.flac`,
`.wav`, `.m4a`, `.mp4`, `.aac`.

This folder is never committed to git (large personal binaries) — only
this README and `.gitkeep` are tracked.

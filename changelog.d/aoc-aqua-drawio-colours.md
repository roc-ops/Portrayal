### Changed
- **One-way: recolours existing drawings. An AOC with no colour stated is
  drawn aqua, and a draw.io export strokes each cable in the colour the
  Rack Builder draws it in** (#1028, `kit/rack/cable-geometry.js`,
  `kit/drawio.js`). `COLORS.aoc` is the teal `#08788a`, of the multimode aqua
  family but not OM3's and OM4's `#2bb3c8`, where it was dark grey `#3a3f45`; no
  other `COLORS` entry changes. The draw.io writer no longer keeps a palette of its own: a cable's
  stroke is what `mediaColor` gives it (copper by its purpose), after the
  cable's own `color` and a caller's `cableStyle` map, which still win.
  `CABLE_COLOURS` is still exported, now derived from `COLORS`. Its colours
  change: dac `#4D4D4D` to `#15171a`; aoc `#2F80C0` to `#08788a`; cu, mm, sm,
  om1, om2, os1, os2, cat5e and `default` to the OS2 yellow `#e8c547` (the
  kit has no colour of its own for the media it does not list, and draws
  them so); om3 and om4 `#16A5A5` to `#2bb3c8`; om5 `#7DB343` to `#9acd32`;
  cat6 and cat6a `#7A5C99` to `#5aa7ff`. A cable of media `unset`, `power`,
  `ground` or copper, which the writer drew in the grey `default`, is now
  `#9aa3ad`, `#1c1c1c`, `#3f9b4b` and, by purpose, `#5aa7ff` or `#9aa3ad`.
  Saved drawings, sheets, 3D files and draw.io exports of a rack with an AOC
  change colour the next time they are drawn; a rack file is unchanged. No kit
  version is bumped here.

### Added
- `@portrayal/kit` 0.6.0: parts beside the rack and parts on one rail are the
  rack kit's (#926; `docs/vertical-cable-managers-design.md` section 8). A
  zero-U part (`mount: rack-side`, a vertical cable manager today and a zero-U
  PDU next) is an entry of `rack.zeroU`, `{id, ref, cfg, label, at, offsetMm,
  between?}`, placed, moved and removed by `zerou.place`, `zerou.update` and
  `zerou.remove`, and fitted by the rack units it states, not its drawn height.
  A narrow rack-face part (under the 450 mm opening) goes on one rail with
  `side.place` and changes rail, or goes across both, with `side.set`. A new
  module, `@portrayal/kit/rack/zero-u`, says where each part stands; `describe`
  and `inspect` list them, and the export data says where each stands
  (`zeroUNotes`, `zeroUImportItems`, `rackNotes(rack, {zeroU: false,
  chassisOf})`). A cable lane runs through a duct beside its upright
  (`laneXAt`), and `fill` and `capacityOver` count the cables through it.
- `rack.schema.json` describes the `zeroU` entry and `side` on an item, and no
  longer calls `zeroU` reserved. Both keys are optional and unconstrained, so
  every file that validated still does; the rack file stays `version` 2
  (`docs/format-stability.md`).

### Changed
- **Routed lengths change beside a duct**: a lane waypoint at a unit a zero-U
  duct spans is measured at the duct's centre line, about 49 mm further out at
  each end beside a 138.8 mm duct. Stored `routed` lengths are re-measured the
  next time a page measures them.
- `parseDoc` keeps `side` on an item, and gives a `zeroU` entry with no id, or
  a repeated one, an id of its own.
- A rack-face part is judged on every unit it spans, not only its bottom one,
  and within the rack's height. `place` of a zero-U part is refused, naming
  `zerou.place`; `remove` and `move` given a zero-U id name the command that
  takes it. A `frame` change moves the parts beside the rack to their side of
  the new frame, or down to fit, and removes one that no longer fits, saying
  so. `fitsZeroU` takes `ru` as well as `offsetMm`, and refuses a part that is
  not a zero-U part.
- `describe`'s totals line counts the parts beside the rack when there are
  any, and a window takes `section: 'zeroU'`; `inspect` of an item carries
  `side`.

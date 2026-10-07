### Added
- **Cable managers, pieces 2 to 4: brushes, pass-throughs, guides and lab
  placement** (`docs/cable-managers-design.md` sections 5 to 7).
  A `brush` panel-decor pattern with `bristle: vertical | horizontal` paints
  itself as a solid field, needs no backing rect and is never an air aperture
  (`data-kind="brush-field"`, `data-bristle`). On a sheet body a sunk decor now
  builds a plate at that depth with no walls, as a well does, which is how a
  brush is an opaque slab in 3D.
  `passes:` on a view declares where cables cross the face, each
  `{id, at, size, shape: rect | obround, cover: open | brush}`, compiled to
  invisible `data-class="pass"` outlines in a `--passes` group. Lint L136: a
  pass lies inside its face and overlaps no component but a well that holds it
  whole. Lint L137: a pass covered by a brush has a brush drawn over it, and a
  brush over a pass belongs to one whose cover is `brush`.
  `guide: {kind: ring, aperture: {w, h}, run}` on a component contract, and
  `guides:` (`kind: duct`, with `finger-pitch` and `finger-gap`) on a device
  view, compile to `data-guide*` attributes and an unpainted
  `data-class="guide"` rect; `components.json` carries a contract's `guide`.
  Lint L138: a ring's opening fits inside its part, seen along its run, and a
  duct lies inside its view with a gap less than its pitch.
  Nothing consumes passes or guides yet, and the DCIM exports ignore both; the
  device lock fingerprints them only where they are declared.
  `attrs.performance.cable-capacity` and `cable-capacity-basis` hold the
  vendor's one capacity figure per manager with its cable and fill basis
  (decision 9).
  A lab placement of a `rack-face` device takes `face` (`front` or `rear`)
  and is placed `on` a host placement at its `unit` (from 1 at the host's
  bottom unit), or at a rack unit by `ru`. Labs have a schema,
  `spec/schemas/lab.schema.json` (published as
  `https://portrayal.dev/schemas/v1/lab.schema.json`), checked by lint (L1)
  and by the build, and five rules: L139 (refs, ids and `on` resolve), L140
  (`face`/`on`/`unit` only on a rack-face part, placed by `on` or `ru` and
  not both), L141 (the host is a rack device and `unit` is within it), L142
  (everything fits the rack, no two rack devices share a unit, no two
  rack-face parts claim one unit on one face), all errors, and L143, a
  warning naming the host behind a rack-face part placed by `ru`.
  `labs_index.py` will not write a lab that fails L1 or L139-L142.
  `roadm-ring-demo` passes all of them. Every `labs.json` placement keeps its
  keys and gains its resolved `ru`, `face`, `mount`, `host` and `unit`; new
  fields only, `contract` stays at 2, and a site that reads none of them still
  draws a rack-face part on its unit.
  Two devices: `fs/cmh-4drb1u`, the FS CMH-4DRB1U (#68690), a 1U sheet tray
  with four steel D-rings and a brush strip behind five windows, from the
  vendor's dimensioned front and side views, with `fs/cmh-4drb1u-panel@1`,
  `-ring@1`, `-end@1` and `-flange@1`; and `fs/cmh-sfd1u`, the FS CMH-SFD1U
  (#29038), a 1U ABS finger duct built hollow as a sheet body: the base
  plate as the well (`fs/cmh-sfd1u-base@1`), two rows of thirteen fingers
  standing in it (`fs/cmh-sfd1u-finger@1`, `-finger-end@1`) with twelve
  gaps a side at 34.1 mm, and the cover across their tips
  (`fs/cmh-sfd1u-cover@1`), which comes off to open the channel; the channel
  and its ends are open, and a `duct` guide declares it.

### Changed
- **A lab is validated** (`docs/cable-managers-design.md` section 6):
  `labs_index.py` used to pass any `lab.yaml` through. The lab schema is
  strict on the top level and on placements (`id`, `ref`, `cfg`, `label`,
  `ru`, `face`, `on`, `unit`, `turned`), so a lab carrying a key it does not
  know now fails the build. A lab `ref` is a device's bare `name`.
- `fs/d-ring-snap-in@1` 1.1.0 declares its ring guide, a 32.0 x 29.5 mm
  opening run along the tray. `fs/fhd-cmp5dr` 1.0.1 for that, and for stating
  its capacity of 30 as `cable-capacity` rather than in its description; its
  drawings gain only the guide attributes, and its DCIM exports change in
  their description and version only.
- Lint L127 reads a `chassis.thickness` that is not a number as a finding
  rather than raising.
- Lint L44 counts a view's declared pass-throughs as openings in the part
  that holds them, so a brush seen through a well's windows is not called
  buried; `fs/cmh-4drb1u` needs no waiver.

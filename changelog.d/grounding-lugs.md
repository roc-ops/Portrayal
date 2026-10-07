### Added
- A two-hole lug across a pair of studs (#828). Three connector interfaces,
  `stud-pair-5-8`, `stud-pair-3-4` and `stud-pair-1`, each spanning two
  `terminal-stud` seats at the pitch in its name (15.875, 19.05, 25.4), and a
  lug for each, `generic/two-hole-lug-5-8@1`, `-3-4@1` and `-1@1`, drawn
  across with the wire leaving along the pair. Pair hosts compose two studs at
  the pitch and present the pair at their midpoint, at the top of the studs:
  `juniper/mx-ground-stud-pair-5-8@1`, `juniper/mx-ground-stud-pair-3-4@1`,
  `common/ground-stud-pair-5-8-m6@1`, `-5-8-1-4@1`, `-3-4-1-4@1` and
  `-1-1-4@1`. A pair and its two studs are one level or the other (L115); each
  stud still takes the ring lug alone. docs/connectors-dc-terminal-design.md
  section 13.7.
- Sized ground screws (#830): `common/ground-screw-m6@1` (ISO 7045 pan head)
  and `common/ground-screw-1-4@1` (ASME B18.6.3 pan head), used only inside the
  pair hosts. `common/ground-lug@1` stays the nominal, unsized ground screw.

### Changed
- The Juniper MX ground studs are pairs a two-hole lug spans (#828), each
  device a major. `juniper/mx80` 2.0.0, `mx240` 2.0.0 and `mx480` 2.0.0 (a
  vertical pair, was 14.0 / 13.2 / 13.2 apart) and `mx104` 3.0.0 (was 16.0)
  place one `juniper/mx-ground-stud-pair-5-8@1` at the 0.625 in. their guides
  state; `mx150` 2.0.0 places `juniper/mx-ground-stud-pair-3-4@1` at 3/4 in.,
  inferred from the lug its guide names (was 13.0). The placements
  `ground-stud-0` and `ground-stud-1` are gone: the pair is `ground-studs`, its
  studs `ground-studs/1` and `/2`. `mx204` 4.0.0 seats
  `juniper/mx204-ground-plate@2`, two 10-32 screws on the guide's 0.75 in.
  (@1 drew 16.0, and is removed); the plate is the pair, its screws
  `ground-plate/1` and `/2`. `mx304` 4.0.0 seats
  `juniper/mx304-ground-plate@2`, two M6 screws one above the other on 5/8 in.,
  the guide's "0.63-in. (16-mm) centers" (@1 drew 16.0, and is removed); its
  screws are `ground-plate/1` and `/2`.
- ESD jacks on the MX80, MX150, MX204, MX240, MX304 and MX480 are in a group of
  their own, `esd` (Point, furniture), not `grounding` (#414). The MX204's laser label moved from `grounding` to a new
  `furniture` group. A placement moving group is breaking for anything that
  addressed it by group.
- L116's depth arm reads where a spanned part PRESENTS, its placed `lift` plus
  its own seat out, rather than its `lift` alone. Nothing the library placed
  before changes: an LC bore presents at its own face. A stud presents at its
  top, which is where a lug across a pair lies (#828).

### Removed
- `juniper/mx204-ground-plate@1`, replaced by `juniper/mx204-ground-plate@2`
  (two 10-32 screws on the guide's 0.75 in. centres, presenting a
  `stud-pair-3-4`; @1 drew the holes 16.0 apart) (#828, #830).
- `juniper/mx304-ground-plate@1`, replaced by `juniper/mx304-ground-plate@2`
  (two M6 screws on 5/8 in. centres, presenting a `stud-pair-5-8`) (#828,
  #830).

### Fixed
- `devicelock` no longer calls a change minor because it added an id while
  something already there moved: the added placements are taken back out and
  the rest must still hash to the old shape, or the change is a major (#828).

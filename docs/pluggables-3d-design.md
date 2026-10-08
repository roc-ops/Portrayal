# Pluggables D: standing proud in 3D

Status: design agreed 2026-09-18. Part of [pluggables-design.md](pluggables-design.md).
Depends on A and B. Written now so it survives; refined when they land.

## Goal

Every pluggable stands out of its cage by the amount its MSA says, its latch or tab
reads as a latch or tab, and a plug with its boot stands off the module face by the
amount the connector drawings say - so a populated device looks like the hardware
from any angle, and a cable landing on B's `cable` point starts where the boot ends.

## The rule this holds to

Umbrella decision 9: EVERY pluggable protrudes. Not the QSFP alone - the SFP, the
QSFP-DD, the OSFP, the XFP, the CFP and CFP2 all stand proud of the bezel by design,
because the latch has to be reachable. So A ships each generic with its
`relief.features` from the start, and D is where the figures are checked against the
hardware and where the parts of the picture that are not a box are decided.

## Protrusion, per family

The protrusion is the module's overall length less the cage's bezel-to-connector
depth - a subtraction of two sourced numbers, the shape `common/sfp-lc-duplex`
already documents ("55.4 module length less the ~41.5 bezel-to-connector measured on
the TE 2007562-6 cage, so ~13.9 stands proud"). D replaces both inputs with the MSA
figures where they exist:

| family | module length | cage depth | status |
|---|---|---|---|
| SFP | SFF-8432 Table 4-3 | `std/sfp` registry depth 41.0 (`measured`) | both held |
| QSFP | SFF-8661 Fig 5-1 | SFF-8663 Fig 4-1, 37 REF (registry `verified`) | both held |
| QSFP-DD | QSFP-DD HW 6.3 Fig 47 | its own cage figure | held |
| OSFP | OSFP MSA | OSFP MSA | fetch |
| XFP, CFP, CFP2 | INF-8077i, CFP MSA | registry depths | second batch |

The tab or bail is a second feature with its own reach where the MSA gives one
(SFF-8661 dimensions the pull-tab reach; SFF-8432 Fig 4-2 the latch post), and
`estimated` with a sentence where it does not. A tab that vendors colour-code takes
its colour from the same `latch-color` field the 2D uses, so the 3D never disagrees
with the 2D about which bail is blue.

## What is not a box

`common/qsfp-transceiver` carried six `body-*.svg` skins - top, bottom, left, right,
rear - produced by a study page, since removed from the repository, whose 3D loft
of the pull tab was verified against photographs.
The README used to say the viewer textures a box from them; nothing in `relief.js`
or `viewer3d.js` ever read them, and D1 (2026-09-21) deleted the five
`body-*.svg` files rather than wire them in - task 2 of this spec carried that out.

Decision to make here, with the parts in hand: either

- **wire them in** - `relief.js` reads `body-*.svg` for a part that has them and
  textures the extruded box's five hidden faces, which gives heatsink ribs on top and
  the label underneath for every generic that draws them; or
- **delete them** - the extruded box with the face skin is what every other module
  in the library gets, and the study's fidelity was for a study.

The recommendation is delete unless a consumer asks: the library's 3D is
"interpolated for a realistic view, not a claim about the hardware" (the
library's stated rule, quoted in `cisco/a99-rp-f`), and five textured faces per generic is a
maintenance surface nothing has asked for. Either way the README stops claiming what
the code does not do; A already corrects the sentence.

## Plugs and boots

A plug stands off the module face by its body length from the connector drawing; the
boot by `boot-length` behind that. Both are ordinary `relief.features` with `out`,
lifted by the chain they sit in (cage -> transceiver -> plug -> boot), which B's
render change 1 makes the occupant path carry. The RJ45 plug's latch is a feature of
its own; its clip is whatever the cabling side draws.

## Verification

Not "renders flat" reasoned about - compiled and counted, per the modelling skill's
own warning. For each generic: compile through `instance_group`, count `data-z-out`
and `data-z-lift` on the output, and read the numbers back against the MSA. Then the
composited 3D screenshot (`viewer-3d-verification`: composited, not buffer readbacks)
of one populated port from three-quarter and side, beside a photograph of the same
module in the same kind of cage.

## Order of work

1. Confirm every A generic's `out` against the MSA figures; fix any that A estimated.
2. Tabs and bails as features; colour from the field.
3. The body-skin decision, and the code or the deletion that follows it.
4. Plug and boot standoff once B lands.
5. XFP/CFP/CFP2 when their generics exist.

## Decisions taken in D (2026-09-21)

- **D1 - delete the body skins**: `common/qsfp-transceiver`'s five
  `body-*.svg` skins are deleted, not wired in. The part is retired
  (`superseded-by: generic/qsfp-lc@1`) and nothing reads them.
- **D2 - SFF-8432 Rev 5.2a was fetched**, held locally in the maintainer's
  gitignored corpus. Table 4-3 designator A is "10.00 Recommended Maximum",
  with other lengths "application specific"; Figure 4-2
  is the cage latch-retention post, not the bail, so SFF-8432 does not
  dimension the bail's forward reach. Note 13 codes an exposed feature's
  colour "blue" for single mode. The held SFF-8661 Rev 2.5 gives no pull-tab
  reach either - its bail-travel note is Note 6, "3.4 MAX".
- **D3 - seating depth by naming the feature**: a connection point may carry
  `on: <relief node>`; a boot seated there lifts by that feature's `out`
  (`interface-at`, `on:`, L106). A `cyl` feature has no `out`, and its rear is
  its far end, `lift + cyl`, so a cable point on a round stub lands there.
- **D4 - out of scope**: 2D side views showing a seated module's protrusion
  (see Open questions below); XFP/CFP/CFP2 (no generics exist); the OSFP MSA
  fetch (no OSFP generic exists); changing the generics' default latch
  colour (see below - since settled).

SETTLED 2026-09-21 - the latch colour default is a neutral grey. The item D
carried open: SFF-8432 Note 13 makes an exposed SFP colour a mode claim
(blue = single mode), and both SFP generics defaulted `latch-color` to
`#2f5fa8` (blue), so every generic SFP drawn with its default claimed single
mode - a per-SKU fact L99 keeps off generics. All four generics now default
`latch-color` to `#6f6f6f`, because SFF-8432 Rev 5.2a codes blue, black and
beige and QSFP-DD HW Rev 6.3 section 6.3 codes beige, blue and white, and an
achromatic grey is in neither table; a vendor wrapper sets the colour its
mode or wavelength calls for. D's 3D wiring is unchanged - the grey reaches
3D the same way any `latch-color` does.

## Stacked cages: one orientation (2026-09-21)

Since C2 a seated optic takes its host cage's `rotate`, so a cage's turn IS the
optic's orientation, and the library drew its belly-to-belly stacks five ways.
Each entry says whose it is: a MAINTAINER DECISION, or an IMPLEMENTATION RULING
taken while applying those decisions across the library. All are dated 2026-09-21.

- **S1 - which side the lip is on** (maintainer decision): in a belly-to-belly SFP/QSFP/QSFP-DD
  stack the cage's latch tab (the `cage-lip` in a std skin) sits on the
  MODULE'S BELLY side, opposite the bail. In a real stack both tabs hang into
  the band between the rows and both bails - the release levers - face
  OUTWARD, where a thumb reaches them.
- **S2 - what `rotate: 0` means on a pluggable cage** (maintainer decision): the module seats
  upright, bail / pull tab at the top, belly and latch at the bottom. Every
  generic transceiver already drew its bail at the top; the std cage skins drew
  their `cage-lip` near the TOP, on the bail's side, which is why sessions that
  matched a photograph turned the UPPER cage to put its lip in the middle band -
  and since C2 seated that upper optic upside down. The six skins with a lip
  (`std/sfp`, `std/sfp-ganged`, `std/qsfp28`, `std/qsfp56`, `std/qsfp-ganged`,
  `std/qsfp-dd`) now draw it at the BOTTOM of the opening; a skin redrawn, a
  patch bump each, nothing addressable moved.
- **S3 - the convention** (maintainer decision for row pairs; implementation ruling
  for column pairs and mixed stacks): a row pair is upper 0 over lower 180. A column pair,
  on a card drawn on its side, is LEFT 270 beside RIGHT 90: `rotate: 90` turns
  an upright cage's bail from the top to the right (SVG turns clockwise) and
  270 to the left, so outward is left and right. A column pair is the two
  cages whose bellies face each other ACROSS the stack, never two cages down a
  column; cages side by side for any other reason are not forced into a pair.
  QSFP over QSFP-DD is a pair - one face family, one bezel opening.
- **S4 - the evidence order** (maintainer decision, including the flip rule where
  there is no evidence; applying it to component cards is an implementation
  ruling), for device faces and component cards alike: a
  recorded photo or drawing reading of the stack first (a reading that the
  tabs point into the middle band IS belly-to-belly; only a reading that the
  two cages are built the same way round keeps them the same), then the port
  lamps (`common/led-arrow*` `for:` each port - up over down is belly-to-belly),
  then the rule, with a note saying the orientation is the rule and not an
  observation, so a later photograph can overturn it.
- **S5 - the exception is declared by the pair** (maintainer decision that exceptions
  are declared; the key's shape is an implementation ruling): `stack-exceptions:` - a
  top-level list in a device manifest (or its layout.yaml) and in a component
  contract, each entry `pair: [a, b]` or `pairs: [[a, b], ...]` with the
  `reason:` that overturns the convention. Lint L108 holds every other pair to
  S3; an entry that names no pair is a finding, and so is one on a pair that already
  follows the convention, because an exception says the stack is built otherwise. The pairing is one module,
  `spec/tools/portrayal/stacks.py`, read by the rule and by its tests.
- **S6 - a component that turns an internal cage is a MINOR bump** (implementation
  ruling): the card's
  box, ids and everything a device places are unchanged, so a device that
  placed the card is not wrong. A device that turns a placed cage takes the
  device rule as written - geometry, a major. A part that MOVES an opening or a
  connection point inside its box is a major by the component rule, not this one:
  `common/qsfp-cage` went to v3 for its flange.
- **S7 - OSFP stacks the same way up** (maintainer decision, 2026-10-07, #799,
  replacing the 2026-09-21 ruling that set OSFP aside; accepting 180 over 180 and
  the column turns is an implementation ruling): a stacked OSFP cage is
  one connector seating both modules heat sink up - the OSFP MSA rev 5.22 draws
  its stacked 2x1 cages so (section 7.1, Figures 7-1 and 7-2), and its Table 7-1
  puts the 19.9 mm pitch's riding heat sink "on the top side of bottom port". So
  L108 holds an OSFP pair to cages turned alike: 0 over 0, 180 over 180 where the
  whole 2x1 cage sits on the underside of the board (the MSA's belly-to-belly
  application, section 7.6, is cages on both faces of one board), 90/90 or
  270/270 on a card drawn on its side. A pair turned 0 over 180 is two single
  cages either side of a board, which the MSA allows but which is not a stacked
  cage, so it takes a reading in `stack-exceptions:`. `std/osfp@1` keeps its
  skin. Applying it, the drawings disagreed with the first proposal (every lower
  row to 0) on four of six faces: the 1RU Celestica faces are single cages either
  side of a board, and the 2RU and 3RU faces draw their lower bank as the upper
  turned over; those devices keep their turn under a per-pair exception and a
  gap until the reading is decided.
- **S8 - three-high faces** (implementation ruling): six devices carry a two-high stack with a separate
  single row under it. The pairing takes stacks from the top, which each
  device's provenance confirms, even where the separate row sits closer to the
  stack than the stack's rows sit to each other - nearest-gap pairing was
  tried and is wrong on all of them. `test_stack_orientation.py` lists them.

- **S9 - what counts as a recorded reading** (implementation ruling): only a
  reading of which way the cages face - their tabs, lip, gasket or cavity - taken
  off a named figure or photograph, as a measurement or an observed crop, with its
  confidence in provenance. A gap, a hint, an analogy with a sibling, symmetric art
  or a claim about construction (two separate shells) is not one: those stacks take
  the rule, and the note says the question is open. Only a reading can make an
  exception, and each device's `stack-orientation` note names, block by block,
  whether the lamps, a reading or the rule decided it.

## Open questions

- Whether a seated module's protrusion should be visible in the 2D SIDE views the
  library renders for every device (left/right faces). It would be correct and it is
  cheap once `out` is right; it is also the first time a face would show an occupant
  of another face, which is the `plan:` mechanism's territory.

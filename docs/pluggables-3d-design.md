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
rear - produced by a study page (`library/demo/part.html`, since removed) whose 3D
loft of the pull tab was verified against photographs (the maintainer's notes, not in this repository).
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
"interpolated for a realistic view, not a claim about the hardware" (the owner's own
ruling, quoted in `cisco/a99-rp-f`), and five textured faces per generic is a
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
  (`interface-at`, `on:`, L106).
- **D4 - out of scope**: 2D side views showing a seated module's protrusion
  (see Open questions below); XFP/CFP/CFP2 (no generics exist); the OSFP MSA
  fetch (no OSFP generic exists); changing the generics' default latch
  colour (see below - since settled).

SETTLED 2026-09-21 - the latch colour default is a neutral grey. The item D
carried open: SFF-8432 Note 13 makes an exposed SFP colour a mode claim
(blue = single mode), and both SFP generics defaulted `latch-color` to
`#2f5fa8` (blue), so every generic SFP drawn with its default claimed single
mode - a per-SKU fact L99 keeps off generics. All four generics now default
`latch-color` to `#6b6f73`, because SFF-8432 Rev 5.2a codes blue, black and
beige and QSFP-DD HW Rev 6.3 section 6.3 codes beige, blue and white, and an
achromatic grey is in neither table; a vendor wrapper sets the colour its
mode or wavelength calls for. D's 3D wiring is unchanged - the grey reaches
3D the same way any `latch-color` does.

## Open questions

- Whether a seated module's protrusion should be visible in the 2D SIDE views the
  library renders for every device (left/right faces). It would be correct and it is
  cheap once `out` is right; it is also the first time a face would show an occupant
  of another face, which is the `plan:` mechanism's territory.

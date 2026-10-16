# Connectors: GPU power and NVLink

Status: implemented, 2026-10-14. Task P-0028. Builds on
[connectors-power-design.md](connectors-power-design.md), which does the same for
AC inlets: a registry entry per interface, a part that presents it, a cable plug
that mates it.

## 1. What was missing

A GPU card could not seat a power cable. The A100's CPU 8-pin connector and its
three NVLink connectors were boxes in a card's 3D body, and nothing could mate
them. The H100 PCIe, L40S and H200 NVL take a 16-pin connector the library had
no part for. A NVLink bridge, which spans two cards, had no representation.

## 2. The interfaces

`spec/schemas/connectors.yaml` gains five. The key names the board connector, as
`iec-c14` names the inlet and not the cord that enters it.

| interface | presented by | mated by |
|---|---|---|
| `eps12v-8pin` | `std/eps12v-header@1` | `generic/eps12v-8pin-plug@1` |
| `pcie-8pin` | `std/pcie-8pin-header@1` | `generic/pcie-8pin-plug@1` |
| `pcie-12vhpwr` | `std/12vhpwr-header@1` | `generic/pcie-16pin-plug@1` |
| `pcie-12v-2x6` | `std/12v-2x6-header@1` | `generic/pcie-16pin-plug@1` |
| `nvlink-a100-pcie` | `nvidia/nvlink-a100-connector@1` | `nvidia/nvlink-bridge-a100-2slot@1` |

Decisions:

- **The two 8-pin connectors are two interfaces over one size.** The housings are
  the same Mini-Fit size, and Molex's catalogue lists the PCIe housing's
  polarisation as its own ("for PCI Express applications only"). A PCIe plug is
  not offered to an EPS12V header and an EPS12V plug is not offered to a PCIe
  header. NVIDIA's table 7 says the same thing the other way: the A100's CPU
  8-pin takes a CPU 8-pin cable, or an adapter from the PCIe 8-pin.
- **12VHPWR and 12V-2x6 are two interfaces, one plug.** 12V-2x6 recesses the
  sense contacts of the board and supply sockets; the cable plug is unchanged. So
  there are two header parts, one plug, and the plug's `mates` lists both.
- **The 6-pin PCIe connector is not registered.** A 6+2 plug also enters it, and
  nothing here needs it. A later task adds `pcie-6pin` and puts it in the 6+2
  plug's `mates`.
- **The NVLink interface is the A100's.** The A30, A40, H100 PCIe, H100 NVL and
  H200 NVL take bridges of their own part numbers. No source held says the
  connectors intermate, so none of them is offered this bridge.

## 3. The figures

Every figure is a transcription. Nothing is copied from a datasheet or a photograph.

| part | figure | source | confidence |
|---|---|---|---|
| `mini-fit-8-header`, `-plug` (EPS12V and PCIe 8-pin) | 12.6 across | NVIDIA A100 80GB PCIe brief PB-10577-001 v03, figure 7 | drawing (the registry entry as a whole is estimated, for the length) |
| | 18.0 long | four 4.20 pitches and a wall; a distributor lists the Molex 39-01-2085 at 18 mm | estimated |
| | 21.1 long (not used) | figure 7, the same housing; 3.1 more than 18.0, not reconciled | |
| | 4.20 pitch, 9.0 A, 600 V | Molex Mini-Fit Jr. catalogue MX10 pp. E-57 to E-63 | datasheet |
| | plug body 20.1, nose 9.9 | figure 7 | drawing; which is which is read from the picture |
| | header cavity 9.9 | taken from the plug's nose | estimated |
| | pins: EPS 4 x 12 V + 4 ground; PCIe 3 + 5 | figure 7's pin table | drawing |
| `pcie-16pin-plug` | 20.85 wide, 14.00 deep | Molex customer drawing 2191140001-SD rev A (2024-03-11), part 2191140161, marked "H++" | drawing |
| | 11.7 high | read between the drawing's 11.70 (on the depth's axis) and 11.63 (the end view's width) | estimated |
| | 12 power on 3.00 pitch, 4 sense on 2.00 | same | drawing |
| `pcie-16pin-header` | opening 20.85 x 11.70 | the plug's own outline; no header drawing was readable | estimated |
| | depth 9.0 | a guess, bounded by the plug's 14.00 | estimated |
| | 600 W; 9.5 A a contact | PCIe CEM 5.0 as Wikipedia reports it; Amphenol GS-12-1706 as Mouser quotes it | datasheet (secondary) |
| `nvlink-a100-connector` | 6.6 x 49.5 | PNY's public top-edge render, measured in the A100 pilot; NVIDIA's figure 5 has no dimensions | estimated |
| | 2.5 above the edge | PB-10577: clearance above the north edge "should meet or exceed 2.5 mm" | estimated (an upper bound) |
| `nvlink-bridge-a100-2slot` | part 900-53651-0000-000, three a pair, 20.5 g | PB-10577 "NVLink Bridge", figure 4 and table 1 | datasheet |
| | 47.24 x 49.5 | two CEM slot pitches (2 x 20.32) plus the connector's 6.6; the connector's length | estimated |

What could not be read: PCI-SIG CEM 5.0 and 5.1 are not held, Molex's own header
pages and the Amphenol 12VHPWR specification (GS-12-1706) refused the download,
and NVIDIA publishes no drawing of the bridge. The 12V-2x6 sense-contact recess
is stated four ways by four secondary sources (1.5 mm, 1.25 mm, 0.1 mm, a
4 mm to 2.75 mm change) and is not drawn.

## 4. How a plug seats

As an AC cord end does (connectors-power-design.md section 5): each plug's nose
sits on the floor of the cavity its header models, and the plug's relief runs from
the header's face. An 8-pin plug stands 20.1 in front of the header and a 16-pin
plug 5.0 (the 14.00 housing less the 9.0 cavity), then a 30 mm stub of the wire
bundle, whose diameter is the `cable-od` field. The bundle diameters (9.0 and
10.0) are estimates; no source states one.

## 5. The bridge spans two cards

A bridge is one part with two ends. It declares `mate` for the end that seats on
the first card and `mate-b` for the second, 40.64 apart (two slot pitches). The
library seats a part at its `mate` point only, so the second end is stated and
nothing seats it. A later task that seats a bridge across two bays reads
`mate-b`; the bridge has `unplaced` until then.

## 6. The exports

A header is `class: inlet`, so a card that composes one exports a **power port**.
NetBox's `PowerPortTypeChoices` has Molex Micro-Fit 1x2, 2x2, 2x3 and 2x4 (a
3.0 mm pitch family) and nothing for Mini-Fit Jr., PCIe or 16-pin; Nautobot's
list has no Molex entry. So each exports as type `other` with the connector as its
`label` (`dcim_export.PART_POWER` and `POWER_LABEL`), as an outlet with no upstream
type does. Plugs, the NVLink connector and the bridge export nothing: a cord end
is not a port of the device it is drawn on, and neither DCIM has an NVLink port.

## 7. What the A100 and the other cards need

The A100 (`nvidia/a100-pcie-80gb@1`, PR #1070, revised by P-0024) is not changed
here. To use these parts it needs:

1. **A place for parts off the bracket face.** A card's `parts:` are placed in the
   bracket face's frame. The CPU 8-pin is on the card's east end and the three
   NVLink connectors are on its top edge, so neither fits `at:` on the face. The
   two ways that exist: a `faces.rear` component for the east end and a
   `faces.plan` component for the top edge, each composing its connector; or a
   part allowed to say which face it is on. The DCIM export reads power ports
   from the card contract's own `parts:` and not from a face component
   (`dcim_export.contract_view`), so the first way also needs the exporter to read
   the face components' inlets before the power port appears. Decide this first.
2. **The CPU 8-pin:** replace the `body-power-connector` box in `body.boxes` with
   `std/eps12v-header@1`, id `aux-power`. Keep the box's position; its size is
   estimated there from figure 6's proportions and this part's 12.6 x 18.0 is
   estimated the same way, so re-check which agrees with the render.
3. **NVLink:** replace the three cap boxes in `body-nvlink` with three
   `nvidia/nvlink-a100-connector@1` at the A100's measured starts (13.5, 70.7 and
   126.1 behind the bracket's outer face), ids `nvlink-1` to `nvlink-3`. The caps
   (0.5 proud, estimated) stay as boxes or become a later part.
4. **Its attrs:** `power-input` already names the connector; add nothing else.
   `nvlink` already says three bridges.
5. **The bridge:** nothing on the A100. The bridge is an accessory listed in the
   brief ("three per pair"); a lab or device that pairs two cards places three of
   `nvidia/nvlink-bridge-a100-2slot@1`, which needs the two-bay seating in
   section 5.

The other cards:

| card | connector | part to use |
|---|---|---|
| A100 40GB PCIe, A30, A40, A16 | CPU 8-pin, per the staging notes of the A100 pilot; unchecked | `std/eps12v-header@1` |
| A10 | PCIe 8-pin, same source; unchecked | `std/pcie-8pin-header@1` |
| H100 PCIe, L40S, L40, H200 NVL, RTX PRO 6000 and 4500 Blackwell SE | 16-pin | `std/12vhpwr-header@1` or `std/12v-2x6-header@1`, by the card's brief |
| A100 40GB PCIe | NVLink, 3 bridges | `nvidia/nvlink-a100-connector@1`, if the 40GB connectors match the 80GB's; unchecked |
| A30, A40, H100 PCIe, H100 NVL, H200 NVL | NVLink | not these: each has its own bridge and no source says the connectors intermate |

Which of 12VHPWR and 12V-2x6 each card has is not in the briefs held here for any
of them (the briefs say "16-pin"). Read each brief's figure; a card built to CEM
5.1 or later has 12V-2x6. Only the A100 brief was read for this change, so every
other card's connector in the table is unchecked and is to be read from that
card's NVIDIA brief before it is wired in.

## 8. The 3D form (P-0031)

Each part was a box with its skin painted on one face: a header's cells were grey
squares on a black face and the bridge a plain slab. They are built now with the
relief keys the library already has, none of them new (library/components/README.md,
docs/modelling-pitfalls.md "Relief and 3D"). The same keys do it for an IEC inlet
(`std/c14-inlet@1`: a `cavity` and pins as `top` features) and a D-sub
(`std/db9@1`: a `shape` outline that is a tube).

| part | how it is built |
|---|---|
| header | `relief.cavity` names one path of one subpath a cell, so the kit punches the housing top in each cell's shape and walls each one down to `size.d`; the housing between cells stays solid. A contact is a `top` feature standing on the cell floor. The latch ramp is an `out` wedge with a `profile`. The 16-pin headers' four sense cells are 1.6 square against the power cells' 2.4 |
| plug | `body` is a `shape` outline with a hole a cell, so it builds as a tube open at the mating face; `back` is a `shape` plate from `lift` to the body's `out`, closing it. The latch arm and hook are `out` boxes with a `lift`. Each wire is a `cyl` with a `lift`, a `comb` plate gathers them, and the stub starts after it |
| NVLink connector | the well is the cavity; `rim` is a `shape` ring standing proud round it; two contact `top` rows stand in it |
| bridge | four `shape` steps from the plate up to a raised centre, and three ridges |

**No capability was added.** `out` is the absolute top and `lift` the base of a
feature (relief.js builds `out - lift`), which is what makes the plug's rear wall
possible without a new key.

What is estimated, all of it low confidence, each in the contract's `provenance`:
the cell sizes (the pitches are sourced, the cells are proportional); the contact
heights (tips 2.4 behind the face; the 12V-2x6 sense contacts 1.5 shorter, one of
four secondary readings); the latch ramps, arms and hooks; the rear wall, comb and
wire lengths; the rim and contact rows of the NVLink connector; and the whole of
the bridge's cover. NVIDIA publishes no drawing of the bridge, and no photograph or
vendor figure was traced or copied: its steps are what a bridge with two connector
ends and a cover between them has to be, and their heights are guesses.

Known gap: the plug's cells are open at the header's mouth, where its modelled
nose begins, because the nose inside the header is not built
(docs/connectors-power-design.md section 5), so the open cells are seen only on a
plug that is not seated.

### Cleanup (P-0034)

A browser scan (each box in a flat colour, the camera nudged 0.05 mm, pixels
whose box changes counted) found four things, and each has its fix and its check:

- **Coplanar joints flickered.** A plug's rear wall had the housing's outline and
  stopped on the housing's rear face, its wires and stub started on the face of
  what they leave, and the bridge's ends and steps stood on the plate's underside
  and edge. Two faces on one plane are drawn by whichever the depth buffer prefers
  pixel by pixel, so the housing's side showed streaks of the wall's darker
  colour. Every piece now starts or ends inside its neighbour or 0.05 short of
  its face. `test_no_two_pieces_of_a_connector_share_a_plane` compares the faces
  of all nine parts in pairs (the lint rule for it, L71 on PR #1070, is not on
  this branch).
- **A sliver at the cell walls.** The face is a raster; its cell openings are
  punched at 4 px/mm (more as the camera nears) and land up to a pixel off the
  exact walls. Measured on the 12V-2x6 header at the base density the cut ran
  0.22 past a wall on some edges, so the dark behind showed. Each header carries
  a `plate`, an exact skin 0.05 proud of the face whose cells are cut 0.03
  smaller than the cells, which covers the walls' top edges.
- **The latch ramp** is now a wedge on the outside of the wall, sloping along the
  mating axis, from 0.3 out of the wall at the mouth to 1.4 at its far end over
  the 8.0 (6.8 on the 16-pin headers) the earlier version spread across the face.
  The numbers are the same guesses. It starts behind the face, which the schema
  allowed only for a facet: a feature that declares `profile` or `profile-y` may
  now have a negative `lift`. The renderer already built it. The ramp's node
  stands outside the skin's viewBox on all four headers (x -1.4 on the EPS12V
  and PCIe 8-pin, y -1.4 on the 12VHPWR and 12V-2x6), so the 2D drawing no longer
  shows it; it is 3D only, like the plug's latch arm.

## 9. Not done

- The 6-pin PCIe connector, and the 6+2 plug's split.
- Polarisation as geometry beyond one chamfered cell a housing; the chamfers are
  schematic. The latches are drawn (section 8) but not their travel.
- Right-angle, vertical and edge-mount board forms: the header presents its
  mating face and says nothing of how it sits on the board.
- The wire bundle's bend, and the adapter cable with an EPS plug at one end and
  two PCIe plugs at the other (NVIDIA figure 7): a cable type is not modelled.
- The NVLink connectors of AMD Infinity Fabric Link and Intel Xe Link bridges.

## Decisions taken

- 2026-10-14: five connector interfaces; two 8-pin interfaces over one size; one
  16-pin plug mating both 16-pin interfaces.
- 2026-10-14: headers export as `other` power ports labelled with the connector.
- 2026-10-14: the bridge is one part with a `mate` and a `mate-b`.
- 2026-10-14: the 3D form uses the existing relief keys and adds none; a header
  keeps its `size.d` cavity (so a plug still seats on its floor) and a plug keeps
  its 30 mm stub.

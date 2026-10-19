# Rack file version 4: one version for everything held back

Status: **decided 2026-10-11**; all eleven parts of section 9 are built, on
one held branch. The exports were tried on NetBox 4.7.2 and Nautobot 3.2.6
(section 13, item 47). What
the build read more narrowly than this note says, or had to choose where it
was silent, is in section 13, and waits for a person to confirm. The kit
release that carries it is a minor one, kit 0.22.0 after 0.21.0. Issues #935 (the scope, decided 2026-10-10), #970,
#949 (step 4), #934, #939, #972, with #983, #986, #1007, #966 and #908 read
beside them. The thirteen questions it raised were each decided as it
recommended and are recorded in section 10, with the options not taken.
Follow-up issues: #1009 (tie points on rings and ducts), #1010 (the ear plan
for a body under one unit) and #1011 (drawing and placing the spare).

Builds on the rack file as it stands (`kit/rack/model.js`, `VERSION` 3,
`spec/schemas/rack.schema.json` under `/schemas/v2/`), and on four notes that
each left keys waiting for this version:
[rack-products-design.md](rack-products-design.md) section 9,
[cable-lay-design.md](cable-lay-design.md) sections 5 and 7,
[pdu-model-design.md](pdu-model-design.md) sections 3 and 6, and
[adjustable-positions-design.md](adjustable-positions-design.md) section 8.
[format-stability.md](format-stability.md) has the rules a version follows.

Three words are used one way throughout. **Read** means read in a file of this
repository or in an upstream file at a named commit. **Measured** means run or
computed for this note. **Inferred** means reasoned from those, and not checked
against hardware.

## 1. What version 4 is, and is not

Decided 2026-10-10: rack file version 4 is **one version, from one design pass
and one build pull request**, not a bump per feature. A rack file version is a
one-way door (an older page refuses the file), so every key that needs the
door goes through it together.

**It is** the keys below, a schema published under `/schemas/v3/` (the next
unused label; a label is never reused), an identity migration from 3, and a
reader that acts on each key or holds it safely.

**It is not** a new document shape. A version-3 file is a valid version-4
file apart from the number. Rows of racks, a room, and anything that needs a
second rack in one drawing stay out (section 12).

**Adjustable positions (#950) need no rack key.** A position is a field value,
and a rack item already carries `fields`. Version 4 only gives a zero-U entry
its own `fields` (section 4), which lets an adjustable zero-U part be set the
same way.

### 1.1 Every key of version 4

| key | on | from | what the first version-4 reader does with it |
|---|---|---|---|
| `ru` in steps of 0.5 | item | section 2 | read, fitted, drawn, exported |
| `roll` (`90`, `180`, `270`) | item | section 6 | read, fitted by the rolled box; `180` drawn and routed; quarter turns drawn as an outline until #550 |
| `states`, `readings` | item, zero-U entry | section 4 | read, checked against the catalogue, applied, exported |
| `swaps`, `fields` | zero-U entry | section 4 | read and applied, as on an item |
| `heldBy` `{parts}` | zero-U entry | section 5 | read, fitted, exported |
| `slack` | cable | section 3 | read, checked, measured, listed and exported; marked with a tag, and no coil drawn (decision 4) |
| `lay` | cable | section 3.9 | `face` is acted on; `position` is kept, and read when lay order is built |
| `straps` (`every`, `breakout`, `anchors`) | bundle | section 3.10 | read, placed, counted |
| `straps` (`anchors`) | cable | section 3.10 | read, placed, counted |
| `color` | cable | section 14, added in kit 0.31.0 with no new version | read, checked, drawn, exported |
| `setback` | frame, item | section 7 | read, fitted, used by routes |
| `startU`, `holes.style: round` | frame | section 7 | read, labelled, drawn, exported |
| `channel` | zero-U entry | section 7 | read; overlap judged per channel |
| `width`, `options` | frame | section 7 | read and kept; acted on only as section 7 states |
| `heldBy` `{item, at, x, z, turn}` | item | section 7 | read, and kept in step with its host; one that is no rack device is not checked, and fit refuses one whose host is gone or that is also `on` a device |

The last five rows are the rack products keys. **That they ride is settled by
the record,** and is not a question here: the decision of 2026-10-09 put them
in version 4, the setback record on #908 says they ship with it, and item 2
of the 2026-10-10 decision says any rack-format change the rack products note
needs goes into version 4. Section 7 says what each does on day one and why
the two that are only kept are safe to publish that way.

### 1.2 What the reader keeps

Read in `model.js`: `readItem` rebuilds an item from a fixed list of keys and
`normalizeFrame` does the same for the frame, so a key neither knows is
dropped on load and erased on the next save. `parseDoc` rebuilds each rack and
the document from fixed keys in the same way. `readCables`, `readZeroU` and
`readBundles` keep what they do not know. There have been two bumps (1 to 2,
2 to 3); the second, for `bundles`, was for exactly this erasure, and every
item or frame key of 1.1 would need one for the same reason.

**Version 4 keeps unknown keys at the four levels that drop them today, so
at all seven** (decision 9). A later optional key that is safe to ignore
then needs no bump, whichever level it sits at. A misspelt key is kept with
the rest and is not reported, by the reader or by the schema.
The validator (`kit/rack/validate.js`) gains the `multipleOf` keyword, since
the schema needs it for `ru`; that is settled here.

## 2. Half-U positions (#970)

### 2.1 What the Fibrain XCU10 is

Read, in `library/devices/fibrain/xcu/device.yaml` and the datasheet it names
(`DSH_XCU00_EN` rev 1.1, modified 05.07.2024, two pages):

- The datasheet title is "Fibrain extendable Patch panel HD 0.5U for 48
  splices". Its description says height 0.5U; its specification table gives
  height 0.5U, width 19 in, depth 284 mm, powder painted steel. Those four
  rows are the whole table.
- The manifest states `chassis.ru: 0.5` and `height: 22.2`, and its
  provenance says 22.2 is half of 44.45, the figure a sibling sheet prints
  beside its own 0.5U.
- The manifest states no `chassis.ears`, and its `handles-and-ears` gap says
  the ears are real and not drawn, because no held image is square to them.
- The NetBox exports state `u_height: 0.5`. The Nautobot exports state
  `u_height: 1.0`, on purpose: `for_target` in
  `spec/tools/portrayal/dcim_export.py` rounds a fractional height up for
  Nautobot and adds the comment line "Occupies 0.5U. Nautobot stores whole
  rack units, so this type states 1."

What the source does **not** say: how the panel bolts to the rail, how many
holes or slots an ear has and at what height, whether two panels may share a
unit, and whether anything goes between them. It publishes no drawing and no
installation guide.

Inferred, and marked as such wherever it is used:

- **It is a 0.5U unit on its own ears, not a 1U enclosure.** The vendor sells
  a separate 1U extendable sibling, the body is 22.2 mm high, and the three
  quarter renders show an integral ear tab the height of the body with one
  elongated slot a side. One slot and its direction are read off renders that
  are not square to the ear, so neither is a measurement.
- **Two stacked in one unit is the point of the product,** since half a unit
  of height has no other use on a rail. Nothing held says so in words.
- **Side by side is not possible:** the face is 19 in wide.

So the device is right as modelled, its height needs no fix, and the fault
reported in #970 is in the Rack Builder and the rack file.

### 2.2 What the kit does today

Measured, by running `fits` and `shrinkRack` from `kit/rack/fit.js` on a 42U
four-post frame:

| case | answer today | right answer |
|---|---|---|
| a 0.5U item at U20, then a second 0.5U item at U20 | refused, "Taken by" | allowed in the other half |
| a 1U item at U2, over a 1.5U item at U1 | allowed | refused: the 1.5U item fills half of U2 |
| a 1U item at U13, over a 3.5U item at U10 | allowed | refused |
| a 3.5U item at U10 and a 1U item at U20, shrunk to 12U | the 1U item is packed to `ru: 4.5`, and `parseDoc` then refuses the saved file ("Item 2 has no device or no U.") | the 1U item at U5 |

Read: every height in the kit is `Math.max(1, chassis.ru)` and every span is
the closed whole-unit range `[ru, ru + u - 1]` (`fit.js` `span`, `fits`,
`fitsRackFace`, `heightOf`, `shrinkRack`; `managers.js` `unitsOf`;
`export-data.js` `overlaps`, `uOfItem`, `drawioU`, `hardwareRows`). A 0.5U
device is therefore a 1U device, and a 1.5U device has a top of `ru + 0.5`,
which a closed whole-unit test never meets. Three catalogue devices state a
height that is not a whole number: the XCU10 (0.5), the BATM TM-7124S (1.5)
and the Juniper MX104 (3.5). The last three rows of the table are faults in
version-3 racks today, and version 4 fixes them with the first.

Read: the loader refuses a file whose item `ru` is not an integer
(`readItem`), the schema says `integer`, and the commands take an integer
(`RU` in `commands.js`).

Read: where a body shorter than its span is drawn is said three ways.
`kit/rack/solids.js` stands a box on the bottom of its unit
(`y0: (it.ru - 1) * RU`). `docs/cable-bundles-design.md` section 6 says the
face is drawn centred in the item span, and gives the formula the routing
context uses for a port. `route.js` `pointOf` and the fallback in `portPoint`
use the middle of the bottom unit. The report on #970 is those three meeting:
the 2D elevation centred the 22.2 mm face in a 44.45 mm span, and 3D stood it
on the bottom.

### 2.3 The position format

Three formats were weighed.

| | (a) `ru` in steps of 0.5 | (b) integer `ru` plus `half: lower \| upper` | (c) a millimetre offset |
|---|---|---|---|
| a 0.5U device in the upper half of U12 | `ru: 12.5` | `ru: 12, half: upper` | `ru: 12, offsetMm: 22.225` |
| a 1.5U device above it | `ru: 13` | `ru: 13` | `ru: 13` |
| a 1.5U device starting on a half | `ru: 12.5` | `ru: 12, half: upper` | as (a) with an offset |
| NetBox `position` | the same number on a bottom-up frame | computed from two keys | computed, and rounded |
| a reader that forgets the new part | cannot: there is one number | reads `ru` alone and overlaps two devices silently | the same |
| what an item carries | one key, as now | two keys that must agree | two keys, one in other units |
| `Number.isInteger(ru)` in old code | fails loudly | still passes | still passes |
| positions that meet no hole | steps of half a unit only | the same | any millimetre, most of them impossible |

**Against the DCIMs.** Read at netbox-community/netbox commit `84e19368`:
`netbox/dcim/models/devices.py` declares `DeviceType.u_height` and
`Device.position` as `DecimalField(max_digits=4, decimal_places=1)`, and both
`clean` methods refuse a value that is not a multiple of 0.5 ("U height must
be in increments of 0.5 rack units.", "Position must be in increments of 0.5
rack units."); `netbox/dcim/models/racks.py` builds a rack as a range of
half units (`drange(..., 0.5)` in `units`, `get_rack_units` and
`get_available_units`). So NetBox holds exactly format (a). Read at
nautobot/nautobot commit `c77e4255`: `nautobot/dcim/models/devices.py`
declares both `DeviceType.u_height` and `Device.position` as
`PositiveSmallIntegerField`, and `nautobot/dcim/models/racks.py` walks whole
units (`range(1, self.u_height + 1)`). Nautobot takes neither a fractional
height nor a fractional position, whatever the format here.

**Against the kit.** Every consumer needs a span and a box, not a key: fit and
collision, the elevation rows, the routing anchors and the exports all ask
"which half units does it fill" and "where is its body in millimetres". Under
(a) those come from one number and the device height. Under (b) every one of
them must remember a second key, and the one that forgets is the fault of
section 2.2 again, silently.

**Against a height that is not 0.5.** A 1.5U device at U13 needs no new
position under any format; what it needs is a span that ends at 14.5 and not
at 13.5. That is a change to how spans are computed, and it is the same change
under (a), (b) and (c). Only (a) then lets the half unit above it be named
with the same key the device below uses.

**Format (c)** is what zero-U parts use and is right for them, since a duct
bracket bolts wherever the upright has a hole. For a rail item it says more
than the hardware allows: an item meets holes only at whole or half units
(2.5), and both DCIMs want units.

**Decided: (a)** (decision 1). `ru` stays the bottom of the item,
counted bottom-up from 1, and may be any multiple of 0.5 from 1. The schema
says `{"type": "number", "minimum": 1, "multipleOf": 0.5}`. It is the NetBox
field, it is the unit the library already writes heights in, and it is the
only one of the three that a careless reader cannot half read. Format (b) is
the smaller diff and keeps `ru` an integer for a consumer that only labels by
it; that is its one advantage, and the version gate already keeps such a
consumer away from a file it would misread.

```json
{"id": "i8", "ref": "xcu", "cfg": "XCU10-21IC", "label": "ODF A", "ru": 12,
 "face": "front", "turned": false, "swaps": {}, "fields": {}},
{"id": "i9", "ref": "xcu", "cfg": "XCU10-21IC", "label": "ODF B", "ru": 12.5,
 "face": "front", "turned": false, "swaps": {}, "fields": {}}
```

What stays whole:

- the frame `heightRU`;
- a lane waypoint `{lane, ru}`: a lane point is the middle of a unit;
- **a rack-face part.** Its own `ru` is a whole unit, and a half is refused.
  Its host is the rack device on its face that fills more of that unit than
  any other, the lower one when two fill it equally. Its `unit` counts whole
  units from the one the bottom of the host is in:
  `unit = ru - floor(host.ru) + 1`, from 1 to
  `ceil(host.ru + units) - floor(host.ru)`. `settleManagers` and `moveItem`
  put it back at `floor(host.ru) + unit - 1`. For a host on a whole unit that
  is the rule of today.

A zero-U part is not on the rails and keeps `offsetMm`. The commands write a
whole number of units for one placed by hand, as today; a part hung on
brackets takes the offset its brackets give it, which is not a whole unit
(section 5), and zero-U fit is judged in millimetres from version 4
(decision 12).

### 2.4 Spans, and the one function that says where a body is

**Settled here.** Three functions in `kit/rack/fit.js` own the answers, and no
other file computes them:

- **`unitsOf(chassis)`** is the height in units: the stated `ru` rounded up to
  the next half, and never less than 0.5. A device with no `ru` is 1, as now.
- **`spanOf(item, chassisOf)`** is the half-open range `[ru, ru + units)`.
  Two spans overlap when each starts below the end of the other. `span` (the
  closed whole-unit pair) is removed; `heightOf`, `itemsWithU`, `shrinkRack`,
  `availableDepth`, `hostAt` and the export `overlaps` are rebuilt on it. With
  `roll: 90` or `270` the units are the rolled ones (section 6).
- **`itemBox(rack, item, chassisOf)`** is the body as mounted:
  `{y0, y1, h, lo, hi}`, millimetres above the bottom of the rails. `lo` and
  `hi` are the span edges, `(ru - 1) * RU` and `(ru - 1 + units) * RU`.

With `unitsOf` right, a half-unit body fills its half-unit span either way
(22.2 mm in 22.225), and the fault of #970 is gone whichever rule `itemBox`
uses for a body that is not as tall as its span. That rule was a separate
choice (decision 2), and it is: centred.

**Bottom or centred.** What decides it on a real rack is the ear: the ear
bolts to the holes, and the body hangs where the ear puts it. Read in
`kit/rack/rails.js`: the three holes of a unit are symmetric about its middle
(6.35 and 38.1 are each 15.875 from 22.225). Read in
`spec/tools/portrayal/ears.py` and `kit/relief.js`: the generic ear lays its
slots symmetrically over its own height, and is the height of the body unless
the device says otherwise. So the ear the library draws puts the middle of
the body on the middle of its units. Standing a body on the bottom of its
span puts those slots below the holes they bolt to, by half the difference.

A formula that reads the stated ear box (`chassis.ears.y` and `h`) was
considered and is **not** proposed: the catalogue does not carry the ear box
until #908, and an ear that spans fewer units than the body (10U ears on a
13U chassis) need not sit on the middle of the span, so the formula would be
wrong for the cases it was written for. It is left for the device that needs
it.

Measured over the 230 rack devices that state both `ru` and `height` (a 231st,
the Celestica DS6001, states a height of 94 mm and no `ru`; the rack index
gives it 2U, so `rack.json` lists 231 and its body overhangs its span by
2.55 mm at each edge, a fifth body that drops by more than a millimetre):
the gap between span and body has a median of 0.65 mm. Sixteen bodies are more than
2 mm short of their span, the most the FS DINRAIL4U at 12.7 mm. Fourteen are
taller than their span: four finger ducts by 4.6 to 13.35 mm, and the other
ten, a fifth duct among them, by 0.55 mm or less.

**Decided: centred, always** (decision 2). `y0 = lo + (hi - lo - h) /
2`, for a body shorter than its span and for one taller, which then overhangs
both edges equally. What moves:

- **The 2D elevation does not move**: it centres today. That holds for the
  formula the kit documents; for the fourteen bodies taller than their span
  it depends on the site elevation not clamping a face to its span, which
  is to be confirmed on the site in the build.
- **3D and the kit solids move** by half the gap: 210 of 230 bodies by a
  millimetre or less, twenty by more. Sixteen rise, by up to 6.35 mm; four
  ducts drop, the FS CMH-DFDS1U by 6.7 mm.
- **Routed lengths move a little where a route touches a body that moved.**
  A tray top and a ring sill come from the solids, so a cable resting on one
  moves with it, and a detour round a body follows the body. For 210 bodies
  that is a millimetre or less at each touch.

Readers of a height, and what each does:

- `solids.js`: `y0` from `itemBox`.
- The routing context `portY`, and a guide box: the face `y` is measured down
  from `y1`, which for a centred body is the formula of today.
- `route.js` `pointOf`, and the `portPoint` fallback: `lo + RU / 2` for an
  item of one unit or more, which is the figure of today; the middle of the
  box for an item under one unit, where the figure of today is the top edge
  of the box.
- The strap extents of the bundle note, and the two site drawings.

A test asserts that nothing under `kit/rack/` outside `fit.js` computes a
height from `ru` (section 9).

### 2.5 The rack holes

Read in `kit/rack/rails.js`: the holes of a unit are 6.35, 22.22 and 38.10 mm
above its bottom (`HOLE_DY`), so the spacing up a rail is 15.875, 15.875,
12.7, repeating. Measured from that:

- A half unit does **not** repeat the pattern. The lower half of a unit holds
  one usable hole, 6.35 mm above its own bottom. The upper half holds one,
  15.875 mm above its own bottom (38.1 less 22.225). The middle hole sits on
  the line between the two halves, and no ear 22.2 mm high can use it.
- So **one half-unit ear cannot serve both halves with a round hole**: it
  needs its hole 6.35 mm from the bottom in the lower half and 6.35 mm from
  the top in the upper half. A slot elongated up and down by 9.5 mm about the
  middle of the ear serves both, and so does turning the panel over
  (`roll: 180`, section 6). Which the XCU10 does is not known (2.1).
- A device of a **whole** number of units shifted by half a unit meets no
  hole: its ear holes land 28.575, 44.45 and 60.325 mm above the unit bottom,
  and the rail has holes at 22.225, 38.1, 50.8 and 66.675.
- A device 1.5 or 3.5 units high meets a different set of holes on a whole
  start than on a half start, so an ear made for one start fits only that one
  unless it is slotted.

**For fit:**

1. A position is a multiple of 0.5. Anything else is refused by the schema
   and the commands.
2. **A device whose height is a whole number of units is refused at a half
   position** (decision 3), with a sentence: "QFX5120-48Y is 1U; its ears
   meet the rail holes only at a whole unit, and U12.5 is a half unit."
3. **A device whose height is not a whole number may start on a whole unit or
   on a half.** Whether its ears meet the holes there is checked only when the
   catalogue states its ear slot heights. No catalogue row does today, so in
   version 4 the check is silent and `inspect` says so once for such a device:
   "The ear holes of XCU10 are not stated, so its holes at U12.5 are not
   checked." When a slot height is stated and misses, it is a warning and not
   a refusal, since the slot length is rarely stated with it.
4. The top of the rack: `ru + units - 1 <= heightRU` becomes
   `ru + units <= heightRU + 1`.

**For the drawn ears.** Read: `ears.py` plans a generic ear with
`units = max(1, floor(h / U + 0.5))` and spaces three slots across each unit,
and `kit/relief.js` does the same in 3D. For a 22.2 mm body that is one unit
squeezed to 22.2 mm with three slots 7.9 mm apart, which no rail takes.
**Settled here:** the slot heights of a generic ear come from the rail
pattern through one helper, `holesIn(lo, hi)` in `kit/rack/rails.js` (every hole
centre at least 3 mm inside the range), mirrored in `ears.py`. A half-unit
ear then has one slot, 6.35 mm up when the device is drawn alone and wherever
its half puts it when it is in a rack. This is a drawing change in library
tooling, not a rack-file change, so it is a follow-up (#1010) beside the
version-4 pull request and not part of it; the Rack Builder draws the ears of
an item through `holesIn` from the start. Only the three devices of 2.2 are
affected, and the XCU10 draws no ears until its gap closes.

### 2.6 Labels, queries and packing

- **Labels.** With `startU` (section 7, absent is 1) the label of a whole
  unit `u` is `startU - 1 + u` on a bottom-up frame and
  `startU - 1 + heightRU - u + 1` on a top-down one.
- **`positionOf(frame, ru, units)`** is the lowest-numbered half unit the
  item fills, as NetBox defines a position: `startU - 1 + ru` bottom-up, and
  `startU - 1 + heightRU + 2 - ru - units` top-down. That is the present
  formula with a fractional height. On a 42U top-down frame a 0.5U item
  stored at `ru: 12` is at 31.5 and one stored at 12.5 is at 31, the order in
  which the NetBox `units` property lists a descending rack (read at the
  commit above, and confirmed on NetBox 4.7.2: on a 45U top-down rack the
  lower panel is stored at 34.5 and the upper at 34).
- **`uText(frame, ru, units)`** names a position through `positionOf`: "U12",
  "U12.5". It takes the height because a top-down label of a half depends on
  it. `uLabel` stays for whole units (lanes, managers, the rail numbers).
- `fitsAt` and `freeUs` take and return half positions. `freeUs` lists whole
  positions for a whole-unit device and both for any other.
- `describe` and `inspect` print a span in words (`spanText`; provisional,
  section 13): whole units on a whole unit as before ("U13", "U13-U14"), and
  anything that starts or ends on a half with the half named, lower and upper
  as the item hangs ("the lower half of U7", "U13 to the lower half of U14").
  No two placements print the same text.
- The commands that place and move (`place`, `move`) take `ru` as a number in
  steps of 0.5. `patch` takes no `ru` and never did: `move` is the command.
  `side.place` and a rack-face part are still refused a half.
- **Three refusals the build worded,** since agents match them. A rack-face
  part at a half: "FHD-CMP5DR bolts to the rail face at a whole unit, and
  U12.5 is a half unit." A position that is no step of 0.5, which the command
  schema refuses first and `fits` refuses for a caller that skips it: "A
  position is a whole unit or a half unit, counted from 1." A command argument
  off the step: "place needs ru, a number in steps of 0.5 from 1."
- **A position below 1** is refused by the schema and by fit ("Below U1."),
  and is still loaded: a version-3 reader loaded any whole number, a
  hand-edited file may hold one, and refusing it on load would refuse the
  whole file. The item is kept where the file says and fit refuses it. The
  exports write its position as the file has it, which a DCIM import then
  refuses; a shrink that has to pack moves it up from the bottom with its
  cluster, and one that has nothing to pack leaves it.
- **`shrinkRack`.** Clusters are formed by `spanOf` overlap, and a cluster
  height is its top edge less its bottom edge, in half units. Each cluster
  moves by one shift, so every item in it keeps its parity. **The shift is a
  whole number of units for a cluster that holds any item of a whole-unit
  height or any rack-face part, and a multiple of 0.5 otherwise.** The cursor
  that packs clusters upward is therefore rounded up to the next position of
  the parity such a cluster already has. In the fourth row of 2.2 the 1U
  item lands at U5 and half a unit stays free under it.
- **What is dropped is judged by the packed top, not by the heights added
  up.** Read: today `shrinkRack` drops clusters from the bottom while the sum
  of their heights is over the new height. With a rounded cursor the packed
  rack can be taller than that sum: clusters of 3.5U, 1U, 3.5U and 1U add up
  to 9U and pack to 10U (1 to 4.5, 5 to 6, 6 to 9.5, 10 to 11). So the loop
  packs the survivors, reads the top edge of the last one, and drops the
  lowest cluster while that top is above the new height. Shrunk to 10U all
  four stay; shrunk to 9U the lowest goes and the other three pack to 6U.
  A device never lands on a half it would be refused at by rule 2 of 2.5.
- **The neighbours a route looks to for a manager** (`neighbours` in
  `fit.js`; before, the 1U device in the unit above and then the one below).
  They are the devices of a unit or less just above an item and just below
  it, above first and nearest first. Above an item of a unit or more: one
  that starts on its top edge. Above an item under a unit: one that starts
  anywhere from its top edge to the next whole unit, so a half-unit panel in
  the lower half of a unit still finds the 1U device over that unit, as it
  did when it counted as a unit. Below: one whose top edge is the bottom of
  the item, and one in the whole unit under the unit its bottom is in, when
  the item starts on a whole unit or is under a unit itself. So a half-unit
  panel directly on the top edge of a 1.5U device is its neighbour, and a 1U
  device half a unit over that edge is not, as it was not before. Every
  answer for a rack of whole positions is the answer of version 3.

### 2.7 What the exports write

For two XCU10 panels at `ru: 12` and `ru: 12.5` on a bottom-up frame:

| export | lower panel | upper panel |
|---|---|---|
| NetBox device rows | `position: 12` | `position: 12.5` |
| NetBox device type | `u_height: 0.5` (already so) | the same |
| Nautobot device type | `u_height: 1.0` with its comment (already so) | the same |
| Nautobot device rows | `position: 12`, comment "Occupies the lower half of U12 (0.5U). Nautobot stores whole rack units." | no position and no face, comment "In the upper half of U12, above ODF A; no position, since Nautobot stores whole rack units." |
| cable schedule `a_u`, `b_u` | `12` | `12.5` |
| draw.io | a cell from `itemBox`, half a unit high | the same, in the upper half |
| BOM mounting hardware | 2 screws and 2 cage nuts | the same |

- **Nautobot** (decision 7). Each item has a whole-unit span there: from
  `floor(p)` to `ceil(p + units) - 1`, where `p` is its `positionOf`. Items
  are taken in order of their stored `ru`, lowest first, and in the order the
  rack lists them where two share a `ru`. An item whose whole-unit span meets,
  on its face, that of one already written with a position is kept in the
  rack with no position and no face, as a held item is (rack products, 7.4),
  and its comment says where it is. The others are written at `floor(p)` with
  a comment saying which part of the span they fill. On the top-down frame of
  2.6 both panels have `floor(p)` 31; the one stored at `ru: 12` is written
  there. That Nautobot refuses two devices in one unit on one face was
  inferred from its whole-unit walk and is confirmed on Nautobot 3.2.6, which
  also refuses a position of 7.5 ("A valid integer is required."). **It
  refuses a front and rear pair in one unit too, while either type is full
  depth,** as NetBox does (`Device.clean`, `nautobot/dcim/models/devices.py`
  lines 804 to 818, with `Rack.get_available_units`, `racks.py` lines 302
  and 349), and one refused row rolls its whole file back. So the whole-unit
  rule looks across both faces where a type is full depth: the later device
  is kept in the rack with no position and a comment. The kit on main wrote
  such a pair to the Nautobot file, on the belief that Nautobot took it.
- **Mounting hardware** (decision 11) is `4 * units` an item, with no floor
  of 1: 2 for a half-unit panel, which has one slot an ear, and the counts
  of today for every other device.
- **draw.io** `drawioU` is whole units from the top. It becomes the top of the
  box in units from the top, in steps of 0.5.

## 3. Slack, stock length and lay (#949 step 4)

### 3.1 What is there today

Read in `kit/rack/route.js`: a routed length is the path, plus an end
allowance from a sourced table (`END_ALLOWANCE_BY_MEDIA`), plus a
`DRESSING_ALLOWANCE` of 0.1 m an end that has no source and is marked
temporary until this step. The table holds two things added together: what
is inside the port, and for copper and DAC a constant 25 mm an end for how
short the maker lets a cord be (copper: 9.5 inside and 25 short, 34.5 in
all; a cable with no media takes the copper figure). `stockLength` then takes
the next size in `STOCK_M`, with a tolerance of one nanometre. Only the path
is drawn.

Measured on the reference rack of #949: one cord has a 397 mm path, a
measured length of 0.62 m (397 plus two ends of 113.1 mm) and a 1 m stock
size. About 0.58 m of the cable bought is neither drawn nor placed, and a
0.5 m cord beside it looks the same.

`inspect` already returns `slack: {metres}` for an entered length. The tray
contract of the FS FHD-CMP5DR already states `slack: {kind: area}` and
`rack.json` already carries it (`solids.js` passes `slack` through). Nothing
reads it.

### 3.2 The lengths, named

**Settled here.** Each word is one number:

- **path**: the routed points, port face to port face.
- **need**: the path, plus what is inside the two ports, plus the short
  tolerance of the maker. It is what the cord must at least be.
- **stock**: the length bought. Pinned by the user, or chosen by the kit.
- **spare**: stock less need. It is real cable, and it is somewhere.
- **end play**: the part of the spare that stays at the two ends, in the
  curves into the ports, and is never coiled. `END_PLAY_M` is 0.1 m an end.
- **to store**: the spare less the end play, never below zero.

`DRESSING_ALLOWANCE` goes, as its comment says it will. `END_PLAY_M` is the
same 0.1 m an end under the name of what it is, moved out of the need and
into the spare. **No stock size on a saved rack changes because of the
move.**

- **The chosen stock** is the smallest size `s` in `STOCK_M` with
  `s + BREAK_TOL_M >= need + 2 * END_PLAY_M`, and where the slack entries
  state values, with their sum in place of nothing: `need + 2 * END_PLAY_M +
  values`.
- **`BREAK_TOL_M`** settles #983 (decision 5): 0.01 m.
- **The short tolerance, with its floor.** For copper (`cat6`, `cat6a`) and
  for a cable with no media or a media the table does not know, it is
  **the greater of 50 mm and 1 per cent of the stock length**, half at each
  end. Up to 5 m that is the 25 mm an end of today, exactly, so no need and
  no stock size moves there; at 7 m it is 70 mm, at 30 m 300 mm where the
  constant gave 50. It is solved with the stock size, taking sizes in order.
  DAC keeps its stated 50 mm at every length (its source covers lengths to
  5 m). Fibre and AOC have none: their makers state plus tolerances only.
  The floor is why the note on #949 (2026-10-10) is met without shortening
  any cord: a bare 1 per cent would be 10 mm at 1 m, 40 mm less than today.
- **The table** keeps its name, `END_ALLOWANCE_BY_MEDIA`, and becomes the
  inside part alone: 13.1 mm for LC fibre, 9.5 for copper and for no media,
  0 for DAC, 52.4 for AOC. `shortTolerance(cable, stock)` is the other part.
- **What stock sizes change on a saved rack:** a cord within 10 mm over a
  break drops a size (decision 5), and a copper cord of 7 m or more may rise
  one. Nothing else. The test of section 9 names each on the reference rack.
- **Centring can move a stock size at a break.** Decision 2 moves a body by
  half its gap, a routed length that touches it by under a millimetre, and
  so the stock size of a cord that sat within that of a break. Measured on
  the routing fixture: the lacer rises 0.225 mm, thirteen of sixteen path
  lengths move by 0.1 to 0.6 mm, and one cord (c2) goes from 500.0 to
  499.8 mm, from a 1 m cord to a 0.5 m one. With `BREAK_TOL_M` of decision 5
  the same cord drops a size regardless, being within 10 mm over the break.
- **`length`** keeps its shape and its `source`: `routed` is a stock size the
  kit chose, `entered` a stock length the user pinned, which is never
  touched. No new key is needed to pin one. Beside a routed value the kit
  stores `need`, and no longer writes `measured`, which is dropped from a
  cable at its next measure (decision 6).
- **A pinned length shorter than the need** is a finding ("c7 is 0.5 m and
  needs 0.62 m."), as `inspect` already shows a negative slack.

For the reference cord: path 397 mm, need 423 mm (two LC ends of 13.1 mm),
stock 1 m (0.5 m would leave 77 mm, under the end play), **spare 577 mm:
200 mm of end play and 377 mm to store.**

### 3.3 What the file records

One cable key, a list, in the shape section 5.2 of the cable lay note gave it,
with one more kind of entry:

```json
{"id": "c2", "a": {"item": "i3", "path": "bay-2/module/p1", "view": "front"},
 "b": {"item": "i5", "path": "p14", "view": "front"}, "media": "os2",
 "length": {"value": 1, "unit": "m", "source": "routed", "need": 0.42},
 "route": [{"item": "i4", "via": "r3"}],
 "slack": [{"item": "i4", "via": "tray", "form": "coil"}]}
```

| entry | means |
|---|---|
| `{item, via, form?, value?, unit?}` | spare stored in a named tray or spool of a placed item or zero-U part, as a waypoint names a pathway |
| `{end: "a" \| "b", value?, unit?}` | spare left at that end of the cable, on nothing the library describes |

- **`form`** is `coil` (the default, decided 2026-10-09), `serpentine` or
  `spool`. It is recorded and listed; version 4 draws none of them (3.4).
- **`value` absent means the rest** of what is to store. At most one entry of
  a cable has no value; entries with a value take theirs first.
- **No `slack` key** means nothing has been said, and the spare reads "not
  placed" (decision 8). An empty list, `"slack": []`, means the user has
  said it is stored nowhere. The two are kept apart so that a later build
  that places spare on its own leaves the second alone.
- **Lay order on a shared tray** is the cable key `lay` (3.9).
- **The loader** (`readCables`, which `parseDoc` runs) normalises the list
  entry by entry, as section 4 does for `states`. An entry is kept when it
  is an object with `item` and `via` as non-empty strings, or with `end` as
  `a` or `b`; `form`, when present, is one of the three names; `value`, when
  present, is a number above 0 with a `unit` that is a non-empty string or
  absent (metres). A second entry with no value, after the first, is not
  usable, since only one can take the rest. If any entry is not usable, the
  usable ones stay in `slack` and the whole list as written moves to
  `slackAsWritten`, as a route with an unreadable waypoint moves to
  `routeAsWritten`; nothing is thrown away. A `slack` that is not a list
  moves there whole and the cable is read as having no `slack` key.
- **`inspect` tells the two apart:** its `slack` carries `said: false` for
  an absent key and `said: true` for a list, empty or not.

An older reader keeps `slack` and `lay` (a cable keeps keys `readCables` does
not know) and misreads `slack`: it measures without it and edits a tray off
the route under it. The cable lay note wrote a guard for a version-4 reader
that held `slack` without acting on it. **That guard is not needed:** version
4 is one build, and its first reader acts on `slack`.

### 3.4 Is the spare drawn?

| | (1) stated, never drawn | (2) drawn as turns in the version-4 build | (3) a stylised hank | (4) recorded and stated in version 4, drawn in a later kit release |
|---|---|---|---|---|
| the file | `slack`, `need` | the same | the same | the same |
| the list and the exports | spare and where it is stored | the same | the same | the same |
| the picture | the path, and a tag | turns as long as what is stored | one solid a cable | the path and a tag now; turns when the geometry is right |
| from the library | nothing | a tray that states slack, and a way to lay a turn on it | the same | nothing now |
| what the picture can be trusted for | routes | the cable bought, where a coil can be drawn | that slack exists | routes now, and it says so |

**Decided: (4)** (decision 4). A draft of this note recommended (2). Checking its geometry against the one part that states
slack today, the FS FHD-CMP5DR tray, found four faults, and none is a detail:

1. **The cells are not even.** Read in the device manifest and the ring
   contract: the five rings stand 95.4, 110.4, 110.4 and 95.4 mm apart and
   each band is 6.8 mm along the run, so the floor strip (448.4 by 61.2 mm)
   is cut into cells of about 15.0, 88.6, 103.6, 103.6, 88.6 and 15.0 mm. A
   turn of 3 mm cord at its 25 mm installed radius needs 53 mm along the
   run, so the two end cells take none. Four cells take turns.
2. **A turn does not touch the line the cable lies on.** Read in `route.js`
   (the resting face of a tray): the cable crosses the tray at the rail side
   of the ring openings, 73.7 mm from the rail for a 3 mm cord (the ring at 66.4, its opening 5.8 in, the cord radius) on a floor that ends at 110. That line leaves room
   for an oval beside it only up to a radius of about 17.4 mm, under the
   25 mm the cord needs. A coil at a legal radius has to sit elsewhere on
   the floor, so the cable needs legs out to it and back, or the lay line
   has to move. Either changes the path, and so the need the spare is
   measured from. A draft of this note said there were no legs; that was wrong.
3. **A coil can be larger than a cell.** Three turns in a cell hold at most
   0.71 or 0.80 m of 3 mm cord. A cord that steps from a 2 m to a 3 m stock
   size stores more. Whether it splits across cells, is drawn in part, or is
   not placed is not settled, nor is a two-turn coil meeting a cell with one
   turn free.
4. **The tray holds little.** With turns stacked to the fill limit of the
   ring opening (29.5 mm at `FILL_LIMIT` 0.4 is three turns of 3 mm cord a
   cell, a bound this note invented: decision 13), a tray takes twelve turns,
   about 2.2 to 3 m of cord. The cable lay note gave 42 m for the same tray
   from floor area times height; no cord can fill that area at its bend
   radius. Worked for a rack of 48 OS2 duplex cords through three such
   lacers (1 m and 1.5 m stock, so 0 to 0.5 m each to store, one to three
   turns for most): each lacer is asked for about thirty turns and takes
   twelve. **On the only tray that holds slack today, a normal rack would
   show most of its spare as not placed**, and which cords got a place would
   turn on the order of their ids.

So drawing in the version-4 build would draw little, draw it in the wrong
place, and leave a rule undefined. Recording is not affected by any of the
four.

**The file needs nothing more for a later drawing.** Checked against the
key list: a drawing needs where the spare is (`slack` entries: the tray, the
form, a value), and the lengths (`length`, with `need`). The coil points
that `routePath` would return, the cell a coil is in, and the `stored` detail
of `inspect` are kit output, computed, not saved. If a later build wants a
user to pin a cell, that is one more optional key in a `slack` entry, which a
cable keeps. No version 5 is needed to draw.

**The later drawing is not free of consequence, though.** If it moves the lay
line or adds legs (fault 2), the path of every cable on a tray changes, the
need with it, and a stock size can move on a saved rack at its next measure.
That release carries the same one-way door every routed-length change has
carried, and its pull request must name it.

**What the later build has to bring**, so that it is not rediscovered: a lay
line and legs that fit a real tray (fault 2); a rule for a coil larger than
a cell (fault 3); a measured stack bound (decision 13); and a part that can
hold the spare of a rack, which a lacer tray cannot: a slack spool (the FHD
enclosures, cable lay note section 6) or a vertical manager that states
storage. Its test is a sum: path plus coiled plus
end play plus the inside ends plus the tolerance equals the stock length.

### 3.5 What version 4 does with `slack`

- **It computes the spare** of every cable with a path and a length (3.2),
  and what of it is to store.
- **It records where the user says the spare is.** `cable.slack` writes an
  entry. It is refused when the tray is not one the cable rests on ("mgr-2
  tray is not on the route of c7."); when the tray states no `slack`; when
  the cable lies on the held face there ("c7 lies on the held face of mgr-1
  tray; slack is stored on the resting face."); when the cable rides a
  bundle trunk through it ("c7 rides Bundle 2 through mgr-1 tray: store its
  spare after it leaves the bundle."); and when no turn of the cable can lie
  on the floor at all, twice its bend radius plus its diameter being more
  than the floor is deep (Cat6A, 67.5 mm against 61.2). That last test is
  necessary and not sufficient; nothing finer is judged in version 4. It is
  applied to `coil` and `serpentine`, which both turn the cable on the
  floor, and not to `spool`, which is refused instead on a tray that states
  no spool.
- **It records spare in a finger duct** (kit 0.35.0), as a technician
  stores a service loop: the duct of a horizontal manager, of a rack-face
  bracket, or of a vertical manager beside the rack, when the cable's route
  uses it (names it, or runs a lane through it). Which pathway kinds hold
  spare is one table, `SPARE_HOLDS` in `kit/rack/slack.js`: a tray and a
  duct do; a ring (a lacer bar's too) and a pass-through do not. A ring, a
  pass-through, a duct off the route and a name the part does not have are
  refused, and the refusal ends with where the cable's spare can go. A loop
  in a duct counts as one more cable for each length of the duct it takes,
  against the cable count the part states (`capacity`, on the basis
  `route.js capacityOver` uses), and is refused past it; a part that states
  no count accepts it with a finding (`spare-capacity-unstated`). No
  capacity is ever assumed; an estimated one is marked
  (`capacity.estimated`, cable-managers-design.md section 15) and said to be one.
- **It does not judge how much a tray holds,** and does not refuse or warn
  for a full one (decision 13).
- **It does not place spare on its own** (decision 8). A cable with no
  `slack` key reads "not placed".
- **A route edit that takes a named tray off the route** keeps the entry and
  says so, as a waypoint that no longer resolves is kept and reported.
- **It marks it.** In 2D and 3D a stored entry is a tag at the tray with the
  length (the marked loop decided 2026-10-09, without a shape), and an
  `{end}` entry a tag at that port. A duct entry is tagged where
  `spareMarks` puts it: a rack item's duct at its own point, a duct beside
  the rack at the middle of the cable's run inside it. Nothing else is drawn, and the legend
  says "Spare cable is listed, not drawn."
- **The finding.** A cable with more than 0.3 m to store and no `slack` key
  (`UNPLACED_WARN_M`) gives `spare-unplaced`: "c2 has 0.38 m to store and no
  place for it." A cable with `"slack": []` gives none. `inspect` of the
  cable carries the finding; `describe` and every export note carry one
  summary line for the rack and never a line a cable, since under decision 8
  it is most cords.

### 3.6 What the list says

`stored` is the text column of 3.8. Every cable with a path and a usable
length gets one of these:

| case | `stored` |
|---|---|
| an entry naming a tray | "mgr-1 tray, coil, 0.38 m; 0.2 m at the ends" |
| an `{end}` entry | "0.38 m at the A end; 0.2 m at the ends" |
| entries with values that add up to less than what is to store | the entries, then "0.1 m not placed" |
| entries with values that add up to more | the entries, and the finding "c7 stores 1.5 m in mgr-1 tray and has 0.6 m to store.", past the stock break tolerance of 10 mm |
| no `slack` key | "0.38 m not placed; 0.2 m at the ends" |
| `"slack": []` | "0.38 m not placed, by choice; 0.2 m at the ends" |
| nothing to store (the spare is all end play) | "0.15 m at the ends" |
| an entry on a tray the cable no longer rests on, or on its held face | the entry, then "not on its route" or "on the held face" |
| a member riding a bundle trunk through the tray | the entry, then "in Bundle 2" |
| a pinned stock length under the need | blank, and the finding of 3.2 |
| no length, a length kept as written, a loose end or no path | blank, and `spare` blank |

### 3.7 Direction (#986)

Read on #986: 38 of 1,803 sample cables measure differently when written end
for end, because of the path. Version 4 does not fix that. The spare follows
the need, so a cable whose path differs by direction differs in its spare by
the same amount; nothing here adds a dependence on direction, since nothing
is placed. The #986 sample must not gain a cable that differs (section 9).

### 3.8 The exports

- **Cable schedule.** Two columns **appended after the last**, so no column
  read by position moves: `spare` (metres, a number) and `stored` (text:
  one of the texts of 3.6). The cable lay note planned one text column named `slack`; two
  serve a spreadsheet better, since the length can be summed. Its `straps`
  column follows them. **This is a download format change**: a reader that
  takes columns by header is unaffected, one that checks the column count is
  not.
- **BOM.** The cable lines keep their shape; the length bought is the stock
  length, as now. One note line totals the spare and counts the cords with no
  place for it ("Spare cable: 14.2 m of 31 m bought; 41 cords have spare
  that is not placed."). The cords are named in the `stored` column of the
  schedule, not in the notes.
- **DCIM.** Nothing new: both targets import the stock length.
- **draw.io.** The edge label of a cable gains its spare where it has a
  length ("1 m, 0.58 m spare").
- **Bend findings (#1007)** join the same pass: one note line a cable in the
  schedule and BOM notes, `bends` on a cable in `inspect`, a count and the
  worst in `describe`, and one finding a corner where two share a point.
  They need no rack key.

### 3.9 `lay`

`lay` is in the schema as the cable lay note fixed it, each entry
`{item, via, position?, face?}`. `face` is acted on from the first build (the
held face exists since step 3 of that note). `position` is kept and not
acted on until lay order is built; ignoring it moves a cable across its
pathway by millimetres and is harmless, as that note argues.

The gap behind a tray (#966) needs no key in version 4. If it becomes a
pathway a user can pin, it is one more value in a `lay` entry, an additive
schema change.

### 3.10 Straps

Wanted from use, and added to the scope of this note: (1) a strap every
12 in along a bundle; (2) at least one strap before each point where a cable
leaves a bundle; (3) a bundle strapped to a cable manager it passes; (4) a
single cable strapped to a manager too.

Read: `straps()` in `kit/rack/bundles.js` places `ceil(L / every)` straps
evenly along each run and moves one off a ring. A run is a stretch where two
or more members ride, **merged across any point where two or more still ride
on both sides**, so a cable leaving a bundle of four does not end a run. Each
member carries where it joins and leaves the trunk (`ji`, `li` in
`layoutOf`). A bundle carries `straps: {every}`; `readBundles` drops a
`straps` whose `every` is not valid, and the command schema (`STRAPS` in
`commands.js`) requires `every` and allows nothing else. The tray contract
states `ties`, the tie slots. The cable lay note counts one strap a tie slot
used on the held face of a tray and none on the resting face, and draws
neither (its decision 3, 2026-10-09).

**Breakout straps (want 2).** Settled here, as geometry:

- **A peel point** is a place along the trunk where at least one member
  joins or leaves it. The two ends of the trunk are peel points when members
  fan out there.
- **Which side.** A strap goes on each side of a peel point on which two or
  more members ride, counting the member that peels there on the side it
  rides. For a cable leaving a bundle of four that is both sides: four ride
  before it and three after. For the last two members parting it is the one
  side. The rule names sides by who rides, not by direction, so it is the
  same when the bundle is written end for end.
- **How far.** The strap centre is 25 mm from the peel point
  (`BREAKOUT_MM`).
- **Where one fits** (decision 14). Peel points are grouped only where no
  strap fits between them: closer than 22 mm (`BREAKOUT_GROUP_MM`), the
  narrowest strap and its clearance of 5 mm each side. The grouping chains.
  Between two groups, where two or more ride: a gap of 75 mm or more
  (`BREAKOUT_TWO_MM`) takes a strap 25 mm in from each end; a shorter gap
  takes one, 25 mm from the end at which a riding member peels, or in the
  middle of the gap when members peel at both ends or when that would leave
  the strap less than its clearance. A spacing strap already in a short gap
  serves, and in a long gap one within 50 mm of where a breakout strap would
  go serves as it (`BREAKOUT_MERGE_MM`). The gap at either end of the trunk,
  where the members fan out to their ports, is a gap like any other: it
  takes a strap wherever one of some stock width fits with its clearance.
  So at a pitch of one unit every cable has a strap before it leaves, and
  at two units and over there is one each side of each peel point.
  A strap that would fall on a ring moves to its nearer edge, as now.
- **How wide** (decision 15). A strap is cut from one of a few stock widths,
  `STRAP_WIDTHS_MM`: 12, 19 and 25 mm. Each strap carries `width_mm`: 19,
  or 25 where the pack it goes round is 25 mm across or more, and the
  narrowest that fits where a gap is too tight for that. **An anchor goes
  through its tie slot, so it is no wider than the slot is long:** the
  widest stock width that is. The FHD-CMP5DR slots are 22.5 mm, so a pack
  that would take 25 mm is tied there with 19. Where even 12 mm does not
  go through, no strap is counted at the slot and the bundle note says so.
  The widths and the clearance are estimates, with no maker's sheet held.
- Each strap that `straps()` returns gains `kind`: `spacing`, `breakout` or
  `anchor`. The count is the three together.

**Anchor straps (wants 3 and 4).** An anchor ties what passes to the part it
passes, and needs a place on the part to tie to. The only such place the
library states is a tray tie slot.

- **A bundle:** one anchor at each tray with `ties` that its trunk lies on,
  at the tie slot nearest the middle of its stretch there (the lower slot
  index on a tie). On either face.
- **A single cable on the held face:** one strap a tie slot used, as the
  cable lay note already counts.
- **A single cable on the resting face:** one strap at the tie slot nearest
  the middle of its stretch on a tray that states tie slots (decision 10).
  This reverses one clause of decision 3 of the cable lay note, that straps
  on the resting face are neither drawn nor counted; they are now counted,
  and drawn as a band at the slot.
- One strap at a slot serves every cable and bundle that passes it; the count
  is by slot, never by cable.
- **A ring states no tie point,** so nothing anchors to a ring or to a
  vertical manager yet. That needs a library key, `guide.ties`
  (the tray shape, `[{at, size}]`, on a ring or duct contract), and the parts
  that would state it: `fs/d-ring-snap-in` (the FHD-CMP5DR rings) first, then
  the `fs/cmh-*-ring` parts and the FS CMV vertical managers. That is #1009.

**The keys.** `straps` on a bundle becomes
`{every?, breakout?: boolean, anchors?: boolean}`, and on a cable
`{anchors?: boolean}`.

- `every` absent is the default 12 in, and `null` is no spacing straps, as
  now.
- **A bundle saved with no straps stays with none.** Read: `every: null`
  means no straps at all today (`straps()` returns none). So `breakout` and
  `anchors`, when absent, are **on where `every` is absent or a spacing, and
  off where `every` is `null`**. The migration stays the identity and adds
  no strap to a bundle that was saved without any. `{every: null, breakout:
  true}` is how a user asks for breakout straps alone.
- **The schema** (`straps` in `rack.schema.json`, and `STRAPS` in
  `commands.js`) drops `required: [every]` and lists the three keys;
  `readBundles` keeps a `straps` that has any valid key.
- **`bundle.update` merges.** A key given replaces that key and a key left
  out stays as it was; `straps: null` removes the object, which is the
  defaults. Today it replaces the whole object, which is the same thing
  while the object has one key. A note for the builder: `bundleUpdate` in
  `commands.js` builds its sentence from `nb.straps.every`, which throws on
  `straps: null`; it has to read the spacing through `strapSpacing`.

**Does it need the bump? Yes, for the bundle key.** A version-3 reader drops
a `straps` with no valid `every`, so `{breakout: false}` alone is erased on
its next save; with an `every` beside it the object is kept whole and the new
keys ignored. Erasure is the bump case, and version 4 is the bump. The cable
key alone would not need one (a cable keeps unknown keys).

**Whether positions need a key: no.** Every strap position above is computed
from what a version-3 file already holds and the `ties` of the library. The
keys only turn a rule off.

### 3.11 What the kit gains

- `rack/route`: `needOf(path, cable, stock)`, `shortTolerance(cable, stock)`,
  `spareOf(rack, cable, ctx)` returning
  `{need_m, stock_m, spare_m, end_play_m, to_store_m, pinned}` (null without
  a path: it never reads a saved number); `END_PLAY_M`, `BREAK_TOL_M`,
  `UNPLACED_WARN_M`; `stockLength(need, {values})`.
- `rack/slack` (a new subpath): `slackOf(rack, cable, ctx)` returning the
  entries as resolved, `{item, via, form, metres, ok, why}` or
  `{end, metres}`, with `at_ends_m` and `unplaced_m`; `storedText(...)`, the
  text of 3.6; `slackFindings(rack, ctx, nameOf)`. It returns no geometry.
- `rack/bundles`: `straps()` entries gain `kind`; `BREAKOUT_MM`,
  `BREAKOUT_MERGE_MM`, `BREAKOUT_GROUP_MM`; `anchorsOf(rack, ctx)` for the
  slots used by bundles and single cables.
- Commands: `cable.slack {id, at: {item, via} | {end}, value?, unit?, form?}`
  and `cable.slack.clear {id, at?}`; `cable.lay` as the cable lay note has
  it; `bundle.update` and `cable.update` take the `straps` keys.
- `inspect` of a cable: `slack` becomes
  `{metres, at_ends_m, said, stored: [...], unplaced_m}`, and `length` gains
  `need`. `describe` gains one line ("Spare: 14.2 m; 41 cords not placed.").

## 4. Outlet states and readings (#934)

Decided 2026-10-08, and not reopened: the device declares what an outlet can
be (`states: [on, off]`), the rack entry sets it, and readings go in the rack
file first. This section gives the keys their exact shape.

```json
{"id": "z2", "ref": "evma8365x", "cfg": "", "label": "PDU A", "at": "left-rear",
 "offsetMm": 133.35,
 "swaps": {}, "fields": {"section-a-label": "Row 4 A"},
 "states": {"outlet-a1": "on", "outlet-a2": "off"},
 "readings": {"source": "SNMP poll of the PDU network module",
              "at": "2026-10-08T14:05:00Z",
              "values": {"outlet-a1": {"current-a": 1.8, "power-w": 372},
                         "breaker-a": {"current-a": 11.2},
                         "input": {"current-a": 19.6}}}}
```

| key | on | type | default |
|---|---|---|---|
| `states` | item, zero-U entry | map of part path to state name, both strings | absent: no state set, lamps unlit |
| `readings` | item, zero-U entry | `{source, at, values}`; `source` a string, `at` an RFC 3339 time, `values` a map of part path to `{current-a?, power-w?, energy-kwh?}`, each a number from 0 | absent |
| `swaps`, `fields` | zero-U entry | as on an item | absent, read as `{}` |

- **Units** are in the names: amperes, watts, kilowatt hours.
- **The loader** normalises `states` entry by entry: an own key that is a
  string, with a string value, is kept; anything else is dropped with a
  notice. `readings` is kept only whole: without a `source` or a readable
  `at` it moves to `readingsAsWritten`, as an unusable length moves to
  `lengthAsWritten`, and nothing draws it. The schema requires the same two
  keys, `source` and `at`, and no other: a `readings` with no `values` is
  usable and shows nothing.
- **The catalogue check** is a settle step, as managers have, since
  `parseDoc` has no catalogue. A state a part does not declare is kept and
  not applied: "outlet-a1 on PDU A cannot be standby: it can be on or off." A
  reading where the PDU meters nothing is kept and not shown: "EVMI2130X
  meters its input and its branches, so there is no reading for outlet-a1."
- **Where the facts come from.** Read: `rack.json` carries neither the PDU
  class nor mount points, and `rack_index.py` reads the default
  configuration only. `<name>.configs.json` carries `pdu-class` for the
  device and `mount-points` for each configuration (`render.py`), and the
  kit already fetches that file for a placed device (`catalog.js`
  `loadSlots`). So the check reads it there:
  - **the metering scope** from `pdu-class`, whose eight names each state
    it: `basic` and `switched` meter nothing; `metered-input` and
    `switched-metered-input` the input; `metered-branch` and
    `switched-metered-branch` the branches too; `metered-outlet` and
    `managed`, its switched form, each outlet. The EVMI2130X is
    `metered-branch`. No new key. A note for the builder: `loadSlots` in
    `kit/rack/catalog.js` keeps `bays`, `cages`, `configs` and `default`
    from that file and drops the top-level `pdu-class`, so it has to keep
    it too;
  - **the state vocabulary** from a new key of each configuration,
    `states: {<path>: [names]}`, the parts that declare one. Additive,
    written by `render.py` beside `mount-points` (section 9, part 4).
- **Older readers.** A version-3 reader drops both keys from an item and
  erases them on save; it keeps them on a zero-U entry and ignores them.
- **Applying them.** `statesFor(entry, facts)` in a new `rack/states` subpath
  returns the map to hand a drawing, expanded from each outlet to the lamps
  bound to it by `for:`, through the one expansion the PDU note requires for
  2D and 3D alike (its section 3.2). `readingsFor(entry, facts)` returns the
  badges with the source and the time.
- **Commands.** `state.set {id, path, state | null}` and
  `readings.set {id, readings | null}`, on an item or a zero-U entry, each
  refused with the sentences above. `patch` and `zerou.update` take `swaps`
  and `fields` on a zero-U entry.
- **Exports.**
  - **NetBox.** Decided 2026-10-08: `on` is `enabled` and `off` is
    `disabled`. Read at netbox-community/netbox commit `84e19368`,
    `netbox/dcim/choices.py`: `PowerOutletStatusChoices` is `enabled`,
    `disabled`, `faulty`. **How the kit delivers it is not verified.** The
    outlets exist once the device is created from its type, and a NetBox CSV
    import creates rows unless each carries an `id`, which the kit cannot
    know; a `power-outlets.csv` of `device`, `name`, `status` would most
    likely be refused as duplicates. So the first choice is a step in the
    import script the kit already ships for cables (`KIT_SCRIPT`), which
    finds each outlet by device and name and sets its status. The
    running-instance test of section 9 tries the CSV first and the script
    second; **if neither works, the states go in the device comment**, one
    line, as for Nautobot.
    **As built:** the CSV is ruled out by the form. At the same commit,
    `netbox/dcim/forms/bulk_import.py` lines 973 to 976,
    `PowerOutletImportForm.Meta.fields` lists no `status`, so a file with
    that column is refused; NetBox 4.7.2 answers "Unrecognized header:
    status" (the header check is `utilities/forms/forms.py` lines 134 to
    139). The model, the REST serializer, the edit form and the bulk-edit
    form of NetBox all take `status` (enabled, disabled, faulty), so a later
    step of the import script could set it through the API. No such step
    exists, so none was tried: the states go in the device comment in both
    files (section 13, item 44).
  - **Nautobot:** the device comment, one line ("Outlets off: A2, A7."),
    each outlet by the name the device-type export gives it. Read
    at nautobot/nautobot commit `c77e4255`,
    `nautobot/dcim/models/device_components.py`: a `PowerOutlet` has `type`,
    `power_port` and `feed_leg`, and no status.
  - **Readings** are in no DCIM file. The sheets, the BOM notes and draw.io
    that show one state its source and time (decided 2026-10-08).

## 5. PDU brackets (#939)

A zero-U PDU on a frame with no zero-U channel hangs on two brackets bolted to
an upright. The bracket is a library device (FS-PDUBK, to be modelled with
#939 as a `mount: rack-side` part); its keyholes are placements whose part
carries `interface: pdu-button`; the PDU mount points carry
`mates: pdu-button` (PDU note, 6.2; rack products, 3).

**How the hosting is written.** Each bracket is a zero-U entry of its own, so
the parts list counts it and it is drawn where it is. The PDU entry names
them:

```json
{"id": "z3", "ref": "fs-pdubk", "cfg": "front", "label": "Bracket", "at": "left-rear", "offsetMm": 133.35},
{"id": "z4", "ref": "fs-pdubk", "cfg": "front", "label": "Bracket", "at": "left-rear", "offsetMm": 1689.1},
{"id": "z2", "ref": "evmi2130x", "cfg": "", "label": "PDU A", "at": "left-rear", "offsetMm": 120.65,
 "heldBy": {"parts": ["z3", "z4"]}}
```

- **`heldBy: {parts: [id, ...]}`** on a zero-U entry: the ids of the zero-U
  entries that hold it, one or more, each an entry of this rack. It is the
  same word an item uses for a shelf (rack products, 7.2), and the shape
  differs with where it is written: an item is on one host at a place, a PDU
  hangs on several parts and its place follows from them.
- **The bracket option** (the quick start guide gives two: on the front of
  the post, or on its rear side) is the bracket configuration, `cfg`.
- **How the position behaves.** Decided 2026-10-09: a hosted item keeps `ru`,
  written by the kit and kept in step with its host, and `heldBy` is what
  decides. A zero-U entry has no `ru`; its position is `at` and `offsetMm`,
  and the same rule is applied to them. **The kit writes both for a held
  PDU:** `at` is the `at` of its brackets, and `offsetMm` is the height of
  the lowest bracket slot less the height of the lowest PDU mount point. When
  a bracket moves the PDU moves with it, as a manager moves with its host.
  Every reader that sorts or labels a zero-U part by where it is goes on
  working, and `zeroUBottom` still names the unit.
- **Off the whole unit.** A held PDU has an `offsetMm` that is not a whole
  number of units (120.65 above). Read: `fitsZeroU` and `settleZeroU` judge
  in whole units today (`zeroUBottom` rounds the offset). From version 4 overlap is
  judged in millimetres (decision 12), and **a part does not overlap the
  parts that hold it**.
- **Fit**, in order, each a sentence:
  1. every id in `parts` is a zero-U entry of the rack whose part offers a
     slot with the interface the PDU mates: "z9 is not a bracket in this
     rack.";
  2. the parts are on one attachment point (or in one `channel`): "z3 is at
     left-rear and z4 at right-rear; a PDU hangs on one upright.";
  3. each PDU mount point lands on a slot, within the tolerance the interface
     states in the connectors registry, 1 mm where it states none: "PDU A has
     mount points 1555.8 mm apart; brackets z3 and z4 are 1511.3 mm apart.
     Move z4 up 1U." The Eaton G4 pitch is 35 units to 0.05 mm (1555.75), so
     brackets at whole units meet it.
- **A bracket removed** leaves the PDU where it was, with `heldBy` naming a
  part that is gone, refused by fit and said in a note until it is hung
  again or freed. Nothing is deleted.
- **A channel.** A PDU in a cabinet channel (rack products, 3) carries
  `channel` and no `heldBy`: the channel is part of the frame. The fit check
  is the same comparison against the channel slots.
- **An older reader** keeps `heldBy` on a zero-U entry and ignores it: it
  draws the PDU where `offsetMm` says, which is right, and lets a bracket be
  moved from under it, which is wrong. That is the bump case.
- **Commands.** `zerou.hang {id, on: [ids]}` and `zerou.hang {id, on: null}`.
  `zerou.update` of a bracket carries its PDU. A query,
  `bracketPositions(rack, {ref, cfg, ru}, ctx)`, returns the offsets the
  brackets need for a PDU, from the unit of the lowest, so a page or an
  agent can place them first.
- **Exports.** The brackets are lines of the BOM. The PDU comment in both
  DCIMs names what it hangs on ("0U, on 2 FS-PDUBK brackets at left-rear,
  from U4; NetBox has no field for that."), and each bracket is a zero-U
  device row with its own comment, as a duct is today.
- **The catalogue.** A PDU already publishes `mount-points: [{mates, at}]`
  for each configuration in `<name>.configs.json`. A part that offers slots
  gains the other side there, `slots: [{interface, at}]` for each
  configuration, millimetres above the bottom of its view, derived from its
  placements in the same way and written by `render.py` beside
  `mount-points` (section 9, part 4). The fit check reads both for the
  configuration each entry names (`cfg`), so a bracket whose two mounting
  options differ is judged by the one chosen. FS-PDUBK is built with #939
  as a plain device first, and this pull request tests against a fixture
  part.

## 6. Roll

Decided in the cable lay note (7.1) and the rack products note (10), and
kept: one item key, `roll`, `90`, `180` or `270`, degrees clockwise as the
item is seen in the elevation of the face it is on, applied after `face` and
`turned`. Absent is upright and `0` is never written.

```json
{"id": "i6", "ref": "fhd-cmp5dr", "cfg": "", "label": "Lacer, inverted", "ru": 21,
 "face": "front", "turned": false, "swaps": {}, "fields": {}, "roll": 180}
```

| | `180` | `90`, `270` |
|---|---|---|
| units | unchanged | the width over 44.45 mm, rounded up to a whole unit |
| box | the same box, from `itemBox` | height and width swapped, centred across the opening until #550 says otherwise |
| ears | a whole-unit ear meets the same holes; see below for a half unit | the ears do not meet the rails; the mount kit of #550 does |
| ports and guides | every face point turned about the centre of the box | the same |
| routing | resting and lay in the frame as mounted (cable lay, 3.1) | routed as an outline only, and said so, until #550 |
| version 4 builds | fit, drawing data, routing | fit and the outline |

- **Ears at a half unit.** Measured from the hole pattern (2.5): turning a
  half-unit panel over moves a hole that is 6.35 mm above its bottom to
  6.35 mm below its top, which is the hole the other half of the unit needs.
  So `roll: 180` is the one way a half-unit ear with a round hole can go in
  the other half. The kit allows it and does not require it, since the slot
  of the XCU10 is not measured.
- **Ports.** `facePoint(rack, item, {x, y}, chassisOf)` in `kit/rack/fit.js`
  turns a point of the face as drawn into the rack, through `face`, `turned`
  and `roll`, on the box `itemBox` gives. A drawing goes through it. `pointOf`
  and `portPoint` are handed rack points by the routing context, not face
  points, so they go through `rollPoint`, the turn `facePoint` itself ends
  with; the solids are turned by their placer. A port on a rolled item is
  where it is drawn. Labels printed on the item are turned with it and are not
  redrawn upright.
- **A rack-face part hosted on a rolled item** keeps `on` and `unit`; `unit`
  counts from the bottom of the host as mounted.
- **Exports.** The notes of the cable lay note: "Mounted upside down.",
  "Mounted rotated 90 degrees clockwise, as seen from its face.", or the same
  with anticlockwise, in the BOM notes and both DCIM comments.
- **An older reader** drops `roll` and fits a quarter-turned item upright,
  into units it does not fill. That is the bump case.
- **Commands.** `patch` takes `roll: 90 | 180 | 270 | null`, refused where
  the rolled box does not fit.

## 7. The rack products keys, and DIN devices on a shelf rail (#972)

A fair question of these keys: this note rejects publishing `slack` as a
key that is read and kept before anything acts on it, so why may `heldBy`,
`width` and `options` be published that way?

**The difference is who can write the key.** `slack` is written by a command
any user can run on any rack, and a reader that ignores it writes a wrong
length into the file. `width`, `options`, `channel` and item `heldBy` can be
written only by choosing a product frame or a host from the catalogue, and
the catalogue has neither yet (read: there is no `library/racks/`, and
`spec/schemas/device.schema.json` defines no `hosts`). The kit release that
first offers a product frame or a host is the release that acts on its keys.
A file edited by hand to carry one is kept whole and said to be unjudged; no
number in it is rewritten.

What each does in the first version-4 reader:

| key | acts on day one | what a hand-written value gets |
|---|---|---|
| `setback` (frame, item) | **fully**, as rack products section 8 has it: the order (item, device default ear position, frame, flush), fit against `usableDepth` and the other face, routed port and guide depth; the 30 mm showcase default goes (no export note is written: section 13) | the same: any user may set it |
| `startU` (frame) | **fully**: an integer from 1, absent is 1; labels and `positionOf` (2.6). **Neither DCIM import takes it:** the NetBox model has `starting_unit` and its rack import form does not, and Nautobot has no such field. So both device files count positions from 1, each device comment gives the label on the rack, and the NetBox rack row says it in `comments` (below) | the same |
| `holes.style: round` | **fully**: kept by `normalizeFrame`, drawn round, and the mounting hardware rows read as for square holes with the note "Round holes: check what fixing your rail takes." | the same |
| `channel` (zero-U entry) | overlap is judged per channel when the frame `ref` names a product whose row lists that channel | with no such row: the part stands outside at its point, as today, and a notice says the channel is not known |
| `width` (frame) | 19 is drawn and fitted as today; the NetBox rack row writes the value when it is one its import takes (10, 19, 21, 23) | another width is kept, the rack is drawn as 19 in, and a notice says so; a width NetBox does not take is written as 19 with a comment |
| `options` (frame) | kept, and listed in `describe` | the same; nothing reads an option until a product row defines one |
| `heldBy` (item) | kept, and kept in step with its host as 7.1 sets out; fit says "i7 is held by i4, and DINRAIL2U states no rail to hold a device, so it is not checked."; exported in the rack with no position and a comment (rack products, 7.4) | the same; **placing a new one is refused** until the catalogue describes hosts |

**Every DCIM column is checked against the import form, not the model.** A
NetBox CSV import refuses a file whose header names a field its import form
does not list, so a field of the model is no evidence. Read at
netbox-community/netbox commit `84e19368`, `netbox/dcim/forms/bulk_import.py`:

| file | columns this kit writes | where the form lists them |
|---|---|---|
| NetBox racks | `site`, `name`, `status`, `width`, `u_height`, `desc_units`, and `comments` only for a rack that has something to say | `RackImportForm` (line 271), `Meta.fields` lines 359 to 364. `width` is a choice field (lines 322 to 327) of `RackWidthChoices`, 10, 19, 21 or 23 (`netbox/dcim/choices.py` lines 87 to 99). **`starting_unit` is not in the list**; only `RackTypeImportForm` (line 218) has it |
| NetBox devices | `position` in steps of 0.5, `face`, `comments` (and the columns of before) | `DeviceImportForm` (line 698), `Meta.fields` lines 760 to 765; the half step is the model rule section 2.3 cites |
| Nautobot devices | `position` whole or blank, `face`, `comments` (and the columns of before); no column is added | read at nautobot/nautobot commit `c77e4255`, `nautobot/dcim/api/serializers.py`: `DeviceSerializer` (line 559) takes every model field (`fields = "__all__"`, line 565), and the model position is the whole number section 2.3 cites |

A rack that numbers from 1 and is 19 in wide exports the six rack columns it
always did, to the byte. The one column this version adds to any DCIM file
is the rack `comments`, written only for a frame with `startU` other than 1
or a width NetBox does not take.

`setback`, `startU` and round holes can be set by a user on a generic frame,
so they are built in full and have tests (section 9, part 3). The other four
wait for catalogue data, and each has the one safe behaviour above and a test
that it survives a round trip and is never rewritten.

### 7.1 A held item in the first reader

A later kit of version 4 will write held items, and the first version-4
reader will open those files. It cannot judge the host (the catalogue says
nothing of hosts yet), but it must not let the two drift apart. It needs
only `chassisOf`, which it has:

- **The host is moved.** A held item that is not `mount: rack` takes the
  face of the host and `floor(host.ru)` as its `ru`, in the same step, as a
  manager moves with its host; its `heldBy` is unchanged. A held item that
  is `mount: rack` keeps its own `ru` and is fitted as any rack device is.
- **The host is removed.** Its held items stay where they were with
  `heldBy` naming an item that is gone, a note says so, and fit refuses
  them until they are placed again. Nothing is deleted with the host.
- **The rack is shrunk.** A held item that is not `mount: rack` is not a
  cluster of its own: it takes the shift of its host. If the host is
  dropped, the held item is kept as for a removed host. A `mount: rack`
  held item is clustered as any rack device.
- **Fit.** A held item that is not `mount: rack` claims no unit in the first
  reader, since nothing says how tall the space on its host is; `describe`
  lists it under its host as not checked.
- **The held item is moved by hand.** A `move` of it (its `ru` or `face`;
  `patch` takes neither) is refused while it is held ("i7 is held by i4: move
  i4, or free it first."); `patch {heldBy: null}` frees it.

### 7.2 DIN devices on a shelf rail (#972)

**The rack-file part is in version 4. The feature is not built with it, and
needs no version 5.**

What #972 needs from the rack file is one statement: this item is on that
rail of that item, so far along it. That is `heldBy: {item, at, x}`, with
`at` the id of a host of `kind: rail`. The depth of the rail follows the
shelf adjustment through `fields` (#950, decided 2026-10-10), so it needs no
key either. The DCIM answer is written (rack products, 7.4).

What is **not** ready, and why the build waits:

- The library has no `hosts:` key, and the DINRAIL2U and DINRAIL4U manifests
  state no rail, profile or usable span. The profile has to be read from the
  FS source, not assumed.
- A `mount: din-rail` device does not yet state the rail profiles it clips to
  in a form fit can compare (#734).
- Whether a DIN device on a shelf should be a child device in either DCIM
  instead of an unpositioned one was asked in #972 and not checked upstream.

When the library gains `hosts:`, placing starts to work on files version 4
already reads.

## 8. Migration, and what each reader does

- **3 to 4** is the identity: `d => ({...d, version: 4})`. Nothing in a
  version-3 file changes shape or meaning on load. The bump is so that a
  version-3 page refuses a file it would erase keys from (`states`,
  `readings`, `roll`, item `heldBy` and `setback`, the frame keys, a bundle
  `straps` without `every`), misplace (`ru: 12.5` it refuses outright;
  `channel`, zero-U `heldBy`) or measure wrongly (`slack`).
- **A version-3 reader given a version-4 file** refuses it whole, with the
  sentence it has today: "This rack file is version 4; this reader supports
  up to version 3." Nothing is read in part.
- **A version-4 reader given a version-3 file** migrates it on load and saves
  it as version 4. `parseDoc` measures nothing, as today.

**What then changes in the file, and when.** Only routed lengths, and only
when a page measures them, which it does through `lengths.routed` exactly as
today (`withRoutedLengths`: a cable with no length or a routed one; never an
entered one). On that first measure each routed cable has its length object
rewritten: the stock value where a size moved (3.2), and the stored figure
beside it (decision 6). **The spare is never computed from a saved figure:**
`spareOf` measures the path it is given and returns null without one, so a
file that has not been re-measured shows no spare and not a wrong one.

**What changes on the page, with nothing changed in the file:**

1. **Overlaps the old fit allowed.** A 1.5U or 3.5U item with another in the
   unit its top half fills (2.2) now overlaps. Both are kept where they are,
   as fit keeps an item it would no longer accept, and a notice names them:
   "TM-7124S at U1 is 1.5U and reaches into U2, where QFX5120 is." The
   sentences are `overlapNotices` in `fit.js`, by item label, and the editor
   gives each as a finding when a document is loaded (`loadDoc`).
2. **Bodies in 3D and the kit solids** move by half the gap between body and
   span under decision 2: a millimetre or less for 210 of 230 rack devices,
   up to 6.7 mm for the other twenty. Routed lengths move by about as much
   where a cable rests on or goes round one of them.
3. **The slack that `inspect` reports for an entered length rises by 0.2 m,**
   since the need no longer holds the dressing allowance. The cable is the
   same; the 0.2 m is now reported as end play.
4. **Faceplates move** with the setback order: the 30 mm showcase default
   goes (rack products, 8).
5. **Strap counts rise** by the breakout and anchor straps (3.10), on
   bundles that have spacing straps; a bundle saved with none stays so.

**The schema** is `spec/schemas/rack.schema.json` with `version` const 4 and
`$id` `https://portrayal.dev/schemas/v3/rack.schema.json`. The file under
`/v2/` stays as published, and the site must serve the new path beside the
old one before a version-4 file is written anywhere, since a saved file may
name its schema. `docs/format-stability.md` gains the version-4 section in
the build.

## 9. Build order inside the one pull request

One branch, one commit a part, in this order. Each part lands with its tests,
and the kit suite runs at the end of each.

| | part | tests it needs |
|---|---|---|
| 1 | **The format.** `VERSION` 4, the migration, the schema under `/v3/`, `multipleOf` in the validator, the reader keeping what decision 9 says, every key of 1.1 read and round-tripped. | A version-3 fixture opens and saves as version 4 with nothing else changed. Each key of 1.1 survives parse and serialise. A version-3 `parseDoc`, kept as a fixture, refuses a version-4 file with its sentence. The schema accepts `ru: 12.5` and refuses `12.25`. A file with an unknown key at each level decision 9 names keeps it. |
| 2 | **Spans and boxes.** `unitsOf`, `spanOf`, `itemBox`, `holesIn`, `uText`, `positionOf`; every site of `Math.max(1, ru)` moved to them; `freeUs`, `shrinkRack`, the manager host rule, the commands. | The four rows of 2.2, each asserting the right answer, the shrink row also asserting that the result parses. Clusters of 3.5U, 1U, 3.5U and 1U shrunk to 10U all stay, with a packed top edge of 11; shrunk to 9U the lowest is dropped. Two 0.5U items in one unit, no overlap, boxes that tile the unit. A 1U item refused at a half with its sentence. `positionOf` and `uText` on a top-down frame for both halves (31 and 31.5). A manager on a host that starts on a half. A source scan that fails when `kit/rack/` computes a height from `ru` outside `fit.js`. A check that `pointOf` gives the figure of today for every item of one unit or more on the routing fixtures. |
| 3 | **The frame and setback.** `startU`, round holes, `width` and `options` kept, `setback` on frame and item with its order, `channel` read. | Labels and exported positions with `startU: 5`, both directions. A setback fitted against `usableDepth` and the other face; a decrease never refused. A routed length that follows a setback. A hand-written `width: 23`, `options` and item `heldBy` each surviving a round trip unchanged, with its notice. Placing a held item refused with its sentence. A file with a held item: moving its host moves it, removing its host keeps it with a note, shrinking carries it, and moving it by hand is refused. |
| 4 | **The catalogue.** `render.py` writes `slots` and `states` for each configuration into `<name>.configs.json`, beside `mount-points`; the kit reads them, and `pdu-class`, from the file `loadSlots` already fetches; the configs section of `format-stability.md`. | The EVMA8365X configuration lists its switchable outlet paths under `states`; the EVMI2130X lists no outlet and is read as metering its branches; a fixture part with keyholes gets `slots`, and its second configuration gets its own. The build gate for the two PDUs, with `devicelock.py` run against the lock on main first. |
| 5 | **Roll.** `facePoint`, the rolled box, `roll: 180` through solids, resting and routes. | Fixture 3 of the cable lay note (two managers back to back, the lower with `roll: 180`). A port on a rolled item at the mirrored point. A quarter-turned item taking its rolled units and refusing a neighbour. |
| 6 | **Zero-U: `swaps`, `fields`, `states`, `readings`, `heldBy`.** Overlap as decision 12 says; `zerou.hang`; `bracketPositions`; the state and reading settle step and commands. | A PDU hung on two brackets 35U apart fits; 34U apart is refused with the sentence and the distance. Moving a bracket moves the PDU. A state the part does not declare is kept, not applied, and named. A reading with no `source` moves to `readingsAsWritten`. An outlet state reaches its lamp path in the map handed to a drawing. |
| 7 | **Lengths and the slack record.** `readCables` normalising `slack` (3.3), `needOf`, `shortTolerance`, `spareOf`, `END_PLAY_M`, `BREAK_TOL_M`, `slackOf`, `storedText`, `cable.slack` and its refusals, `spare-unplaced`. No geometry. | On the reference rack of #949: every stock size before and after, with only the cords within 10 mm over a break changing, each named. A copper cord at each stock size: need unchanged to 5 m, 20 mm more at 7 m. For every cable, need plus spare equals stock, and end play plus what is to store equals spare. Each row of the table of 3.6 has a case asserting its text. Each refusal of 3.5 has a case. A bad `form`, a negative `value`, two entries with no value, an unknown `end` and a `slack` that is no list each load with the usable part kept and `slackAsWritten` holding what was written, and save unchanged. `inspect` gives `said: false` for no key and `said: true` for `[]`. `routePath` returns the same points with and without a `slack` entry. The #986 sample script reports no more cables differing by direction than before (38). |
| 8 | **Straps.** `kind` on each strap, breakout and anchor straps, the `straps` keys on bundle and cable, `readBundles` and the `STRAPS` schema. | A bundle of four with one cable leaving mid-trunk: a breakout strap 25 mm each side of the peel, and the same set when the bundle is written end for end. Two peels 60 mm apart share the outer straps. A spacing strap 40 mm from a peel serves and none is added. A trunk over the FHD-CMP5DR tray gets one anchor at the nearest tie slot. Peels at 0, 60 and 130 mm are one group from either end. `{breakout: false}` alone survives a round trip and turns breakouts off. A version-3 bundle with `every: null` has no strap of any kind after migration. `bundle.update` with one key leaves the others. The BOM count equals the three kinds summed. |
| 9 | **Exports.** Positions in halves, the Nautobot rule, the hardware count, `spare` and `stored`, outlet states, the comments for roll, brackets and held items, the bend lines of #1007. **Owed from part 5:** until this part a quarter-turned item is exported at the position its rolled box starts at, with no comment saying it is rolled. | Golden files for both DCIM kits with two half-unit items in one unit, on a bottom-up and a top-down frame. The schedule header ends `..., status, notes, spare, stored, straps`. **On running instances:** both device files import whole with two half-unit devices in one unit; NetBox shows the upper at 12.5; the outlet states arrive by CSV or, failing that, by the script, and the test records which. **Tried on NetBox 4.7.2 and Nautobot 3.2.6** (section 13, item 47): the first two hold, and the outlet CSV is refused. |
| 10 | **Queries and agent output.** `describe`, `inspect`, `fitsAt`, the command table, and `cable.lay` with its `face` acted on by the routes (3.9, decision 17). | The agent command schema validates each new argument. `inspect` of a cable shows `stored`, `at_ends_m` and `unplaced_m`. |
| 11 | **Docs and release.** `format-stability.md`, the four notes of the header amended to point here (the 42 m figure of the cable lay note among them), the kit minor version, the changelog fragment naming each one-way item. | Preflight and the docs tests. |

The site follows in portrayal-site once the kit is published: it serves the
schema under `/v3/` beside `/v2/`; the 2D and 3D drawings read `itemBox` and
`facePoint`, draw the spare tags and the three kinds of strap, and draw
bracket-hung PDUs. Its browser check asserts, for two half-unit items in one
unit, that neither drawn box overlaps the other in 2D or in 3D, and that the
legend says spare cable is listed and not drawn.

**Not in the pull request, and no format change when they come:** lay order
by `position` (cable lay step 5), the quarter turns of #550, placing a new
held item (7.1), the gap behind a tray (#966), the direction faults of #986,
the generic ear slots in `ears.py` (2.5, #1010), drawing and placing spare
(3.4, #1011), and ring anchors (3.10, #1009).

## 10. Decisions (decided 2026-10-11)

Thirteen questions, each decided as this note recommended. Each entry gives
the choice, its reason, what was considered and not taken, and what is
one-way.

1. **The half-U position format: `ru` in steps of 0.5.** It is the NetBox
   field, it is one number, and a reader cannot read half of it (2.3).
   Considered: an integer `ru` with `half: lower | upper`; a millimetre
   offset. One-way: a saved key and a published schema.

2. **A body that is not as tall as its span is centred, always.** The holes
   of a unit are symmetric about its middle, and the ear the library draws
   is symmetric about the body (2.4). The 2D elevation does not move; 3D and
   the kit solids do: 210 of 230 rack devices by a millimetre or less,
   sixteen up by as much as 6.35 mm, four ducts down by as much as 6.7 mm,
   and routed lengths by about as much where a cable touches one.
   Considered: on the bottom of the span, as 3D did, which would move every
   2D face instead. Two-way in the file; one-way in that every published
   picture follows it.

3. **A whole-unit device at a half position is refused.** Its ears meet no
   hole there (2.5). Considered: allowed with a warning, as NetBox allows
   it. Two-way: it is a kit rule, nothing saved depends on it, and loosening
   it later breaks no file. Agents match its sentence.

4. **The spare is recorded and listed in version 4, and drawn in a later kit
   release** (#1011), once the geometry fits a real part and a part exists
   that can hold the spare of a rack. The geometry of drawing it now failed
   on the one tray that holds slack: a turn cannot touch the lay line at a
   legal radius, a coil can outgrow a cell, and the tray takes about a third
   of what a normal rack would ask of it (3.4). Considered: never drawn;
   drawn as turns in the version-4 build; a stylised hank. One-way: the
   `slack` keys, `need`, and the `spare` and `stored` columns of the cable
   schedule, a download format change. The picture is two-way and needs no
   key the record lacks; but the release that draws it may move paths on a
   tray, and so the need and the stock size of saved cables, which is
   one-way when it comes.

5. **The stock break (#983): `BREAK_TOL_M` is 0.01 m.** A cord up to 10 mm
   short of full end play is still chosen. It is one twentieth of the end
   play and covers the spread of the LC plug depth estimate at two ends
   (1.8 mm each). The 10 mm figure was confirmed 2026-10-18. Considered: no tolerance; another figure. One-way: on a
   saved rack, each cord within 10 mm over a break drops a stock size at its
   next measure. The end play itself (0.2 m) and the copper floor (50 mm)
   keep the figures of before and move nothing.

6. **Beside a routed length the kit writes `need`, and stops writing
   `measured`,** which is dropped from a cable at its next measure. No saved
   number then changes meaning under its old name. Considered: keeping the
   name `measured` with a new meaning; keeping it with its old meaning.
   One-way: a saved-format field.

7. **Nautobot, two half-unit devices in one unit: the lower stored `ru` is
   positioned, the other is kept in the rack with no position and a
   comment** (2.7). It imports, loses no device, and states no position that
   is false. Considered: leaving the other out of the file; giving each a
   whole unit of its own. One-way: an imported device keeps where it was
   put.

8. **The kit does not place spare on its own in version 4.** A cable with no
   `slack` key reads "not placed". With nothing drawn, an automatic place
   would be a line in a list that nobody chose and that the tray may not be
   able to honour (3.4). It comes back with the drawing (#1011). Considered:
   placing it on a tray the cable already rests on. Two-way: nothing is
   saved either way.

9. **Unknown keys are kept at all seven levels of the file** (item, frame,
   rack and document, which dropped them, as well as cable, zero-U entry and
   bundle, which kept them). A later optional key that is safe to ignore
   then needs no bump, as `side` did not. The cost is that a misspelt key is
   kept and not reported, by the reader or by the schema: no level of the
   schema refuses a key it does not describe. Considered: items and the frame only; leaving it. One-way in
   practice: later keys will rely on it.

10. **Straps on day one: all four of what was asked, on every part that
    states tie slots.**

    | wanted | delivered in version 4 |
    |---|---|
    | every 12 in along a bundle | yes, as before |
    | a strap before each point where a cable leaves a bundle | yes |
    | a bundle strapped to a manager it passes | yes, at a tray that states tie slots (the FHD-CMP5DR today); not at a ring or a vertical manager |
    | a single cable strapped to a manager | yes, on either face of a tray that states tie slots: one strap at the tie slot nearest its stretch, shared by every cable at that slot |

    This reverses one clause of decision 3 of the cable lay note
    (2026-10-09), that straps on the resting face are neither drawn nor
    counted: they are counted, and drawn as a band at the slot, as a bundle
    strap is. The cost is in the BOM: up to one strap a tie slot a tray,
    sixteen on an FHD-CMP5DR, and fewer in practice since cords in one cell
    share a slot. Deferred: anything strapped to a ring or to a vertical
    manager, until those parts state a tie point (`guide.ties`, #1009). A
    bundle saved with no straps stays with none (3.10). Considered: single
    cables strapped on the held face only; leaving straps as they were.
    One-way: the BOM strap count, and the `kind` of a strap in the kit
    output.

11. **The mounting hardware count is `4 * units`, with no floor of 1.** The
    XCU10 goes from 4 to 2, and nothing else changes (the TM-7124S stays 6,
    the MX104 14). It fixes the one count the hole pattern shows to be wrong
    and moves no other. Considered: by whole units, which would move the
    MX104 from 14 to 12 and the TM-7124S from 6 to 4; leaving it. One-way: a
    BOM line.

12. **Zero-U overlap is judged in millimetres,** from `offsetMm` to
    `offsetMm` plus the stated units times 44.45. A part the kit wrote at a
    whole unit, which is every part the kit has written into a version-3
    file, overlaps exactly as before, and a PDU hung at 120.65 mm is judged
    where it is. A hand-written offset between units is judged where it
    says, where before it was rounded. Considered: whole units as before,
    with only the rule that a part does not overlap its holders added.
    Two-way in the file; one-way in that fit answers follow it.

13. **How much a tray holds is not judged in version 4.** An entry is
    recorded, and no tray is ever called full. No source gives a stack
    bound, the two candidates differ three times over, and the figure
    decides how many cords of a rack read as not placed; it is to be
    measured on a lacer before it is a rule, and it is needed only once
    coils are drawn or placed (#1011). Considered: turns stacked to
    `FILL_LIMIT` of the stack height (twelve turns a tray on the
    FHD-CMP5DR, about 2.2 to 3 m); turns stacked to the whole ring opening
    (thirty-six, about 6.6 to 9 m). Two-way.

14. **Breakout straps at close pitch (decided 2026-10-11): a strap before
    each leaving point.** The first build grouped every peel point within
    75 mm of the one before, so a trunk whose cables join a unit apart was
    one group and had no breakout strap at all. Peel points are grouped
    only where no strap fits between them with its clearance (3.10). On
    eleven cables down one lane a unit apart that is ten straps where
    there were two, the spacing straps: a strap in each of the ten gaps
    where two or more ride, eight of them breakout straps. Considered:
    the chained 75 mm of the first build. One-way: the strap count, and
    where a drawn strap is.

15. **A strap has a width, from a short list (decided 2026-10-11).**
    Narrower and wider hook-and-loop strap exists and may be used: each
    strap carries `width_mm`, one of 12, 19 and 25, and the BOM line counts
    each width. The list and the rule that picks one are provisional
    (section 13, item 43). Considered: the one 20 mm figure of before.
    One-way: the shape of a strap entry, and the text of the BOM line.

16. **Single-cable tie straps are kept as built (decided 2026-10-11):** one
    strap at each tray tie slot a lone cord rests at, shared by every cord
    at that slot (section 13, item 38, for how the slot is found).

17. **The face a file pins is read before a page's own pin (to be
    confirmed).** A cable with a `lay` entry for a tray lies on the face the
    entry names, whatever `ctx.trayFaceOf` of the page says, so a saved rack
    routes the same on every page and for an agent. The page's pin is read
    only where the file says nothing. Chosen in the build, since 3.9 has
    `face` acted on and does not say which wins. Considered: the page
    first, which lets a page override a file it did not write; reading the
    file only. One-way: where a cable with a pinned face is routed.

## 11. One-way items

**That follow from a decision of section 10:**

| item | follows from |
|---|---|
| `ru` as a multiple of 0.5; `positionOf` and `uText` in halves; the half positions in every export | 1 |
| `itemBox` and where 3D bodies and solids stand | 2 |
| the texts of 3.6, `spare` and `stored` in the schedule, the BOM spare lines, the draw.io label, `spare-unplaced` and `UNPLACED_WARN_M` | 4 |
| `BREAK_TOL_M` and the stock sizes it moves | 5 |
| `length.need`, and `measured` no longer written | 6 |
| the Nautobot order and its two comment lines | 7 |
| the reader keeping unknown keys | 9 |
| breakout and anchor straps, their distances, `kind`, the strap count | 10 |
| the hardware row and its text | 11 |
| zero-U spans in millimetres | 12 |

**That the build added, and the note had not decided:**

| item | where | what moves |
|---|---|---|
| the BOM strap line counts each kind of strap and each width, and ends "length to suit" | BOM | every rack with a bundle or a cord on a tray; before, it gave one count and one spacing |
| `kinds` and `widths` in what `straps()` returns, `strap_kinds`, `strap_widths` and `anchor_widths` on a bundle in `bundleExports`, `kinds` in `inspect` of a bundle | kit output | `count` is all kinds together; the spacing straps alone are `kinds.spacing` |
| `width_mm` on each strap, and on each slot of `anchorsOf` | kit output | decision 15 |
| `spare-unplaced`, `spare-short`, `spare-over`, `spare-off-route` as finding kinds of one cable, and `spareLine` as the one line for a rack | kit output | agents match the kinds |
| `END_ALLOWANCE_BY_MEDIA` and `endAllowance` are what is inside the port alone | kit API | a page that took the dressing as `endAllowance` less the table gets 0: the end play is `END_PLAY_M`, and the lengths of a cable are `spareOf` |
| `strapBomRows(bundles)` counts single cables only when handed `{anchors: anchorsOf(rack, ctx)}` | kit API | a page that does not pass them leaves their straps out |
| the comment line of what is set off, in both device files, naming each outlet as the device-type export does | DCIM exports | section 13, item 44 |
| `configs[].names` in `<device>.configs.json` | published build | additive; the kit reads it as `configFacts().names` |
| an anchor strap capped by the long side of its tie slot, and `notes` in what `straps()` returns | kit output, BOM | the widths of the BOM strap line |
| the comment of a PDU on brackets and the note of one, worded by `hungText` | DCIM exports, BOM notes | a reader that matches "beside the rack at" for every part beside it |
| the `straps` column of the cable schedule, after `stored` | download format | the schedule has 20 columns where main has 17; a reader that checks the count |
| `cable.lay`, and the face the file pins read before a page's own pin | kit command, routes | agent sessions call it by name; a rack with a `lay` face routes by it on every page |
| `notes` on `inspect` of an item, `lay` on `inspect` of a cable | kit output | agents read them |

**That the scope fixed before any of those decisions:**

| item | where | why it is one-way |
|---|---|---|
| rack file version 4 under `/schemas/v3/`, with every key of 1.1 | rack file, schemas | an older page refuses a version-4 file; a label is never reused |
| `unitsOf`, `spanOf` (half-open), `facePoint`, `holesIn` | kit API | pages place and route by them |
| `END_PLAY_M` (0.1 m an end, the 0.2 m a cable has today, renamed), `shortTolerance` with its 50 mm floor, `END_ALLOWANCE_BY_MEDIA` as the inside part alone | kit API | a page reads them by name; copper cords of 7 m and over may rise a stock size |
| `slack` entries `{item, via, form, value, unit}` and `{end, value, unit}`; absent against empty | rack file | saved files carry them |
| `states`, `readings`, and `swaps` and `fields` on a zero-U entry | rack file | saved files carry them |
| how outlet states reach NetBox (CSV, script or comment, as the test finds), and the Nautobot comment line | DCIM export | an import kit file or step |
| zero-U `heldBy: {parts}`, and the kit writing `at` and `offsetMm` of a held part | rack file, kit | saved files carry it |
| `straps` keys on a bundle and a cable, and `every: null` meaning no strap of any kind unless a kind is turned on | rack file | saved files carry them |
| `startU`, `setback`, round holes, and the kept keys of section 7 | rack file | saved files carry them |
| `slots` and `states` per configuration in `<name>.configs.json` | the build | the kit reads them; additive |
| `zerou.hang`, `state.set`, `readings.set`, `cable.slack`, `cable.slack.clear`, `roll` on `patch` | kit commands | agent sessions call them by name |

## 12. Left for version 5, or later with no version

**Needs a later version:**

- **Rows of racks** (`rows` on the document), baying checked between two
  products, and `between: true` resolved to two racks (rack products, 10).
- **A room**: rows in plan, aisles, anchors.
- **Slack across racks**, which needs rows first.
- **A stored position for a channel that slides** (`moves`, rack products 3),
  if a product needs one.

**Needs no version, only a build:**

- Lay order by `position`, and the gap behind a tray (#966).
- The quarter turns of `roll` and the mount kit facts of #550.
- Placing a device on a shelf, in a drawer or on a DIN rail (#972), once the
  library has `hosts:`; and acting on `width` and `options`, once a product
  frame defines them.
- **Drawing the spare, and placing it without being asked** (3.4, #1011): the lay
  line and legs, a coil larger than a cell, a measured stack bound, and a
  part that can hold the spare of a rack. With it: a shape for `serpentine`
  and `spool`, slack in a vertical duct, and a bundle storing its spare as
  one hank.
- An anchor strap at a ring or a vertical manager, which waits for
  `guide.ties` (#1009).
- Readings in the marks format, a later decision of its own (PDU note, 3.4).
- The ear slot heights of a device in the catalogue, which turn on the hole
  check of 2.5.
- The direction faults of #986.

## 13. Provisional

Readings the build took where this note was silent or could not be followed
as written. Each is built, and each waits for a person to confirm it. The
numbers are kept: a later reading takes the next one.

1. **Span text** (2.6). A draft of 2.6 printed "U13-U14.5", which follows from
  no rule that also keeps "U13-U14" for a 2U item. Built: whole units on a
  whole unit read as before; anything on a half names the half ("U13 to the
  lower half of U14", "the lower half of U7", "the upper half of U7"). A
  position alone is still a number (`uText`: "U12.5"), which is what the
  commands say and NetBox stores.
2. **The Nautobot comment for a height other than 0.5U** (2.7) uses the same
  words: "Occupies U1 to the lower half of U2 (1.5U). Nautobot stores whole
  rack units." An item kept with no position beside one at the same stored
  `ru` reads "with" in place of "above". A device of whole units on a whole
  unit gets no such comment.
3. **The three refusal sentences** of 2.6.
4. **The manager neighbours** of 2.6, which keep every version-3 answer.
5. **A stock size can move with centring** (3.2).
6. **A position below 1 is loaded** and refused by fit (2.6).
7. **Zero-U keys in the schema.** A zero-U entry is described and not
  constrained, so that any entry is kept as written; `states`, `readings`,
  `swaps`, `fields` and `heldBy` on it are typed as section 4 and 5 give them,
  and nothing else of an entry is.
8. **`width` is in inches** in the schema (19, 23), as the NetBox rack row
  takes it. `options` and the `turn` of an item `heldBy` have no type until a
  product or a host defines one.
9. **`startU` in the DCIM files** (section 7). Neither import takes a starting
  unit. Built: both device files keep the position counted from 1, and every
  device comment says how the rack is numbered ("U16 on the rack. The rack
  numbers its units from 5, and a unit named here is its label; the NetBox
  import counts from 1."), so a unit a comment names is never taken for a
  position. The NetBox rack row says it in `comments`, and says what to do:
  leave the starting unit of the rack at 1, or set it in the one order
  NetBox 4.7.2 allows. It refuses a starting unit above a device
  (`netbox/dcim/models/racks.py` lines 459 to 464) and a position past the
  top (`devices.py` lines 906 to 912), so the devices below the new start
  are raised first, then the start is set, then the rest are raised. A
  rack CSV with a `starting_unit` column is refused ("Unrecognized
  header").
10. **The sentences of fit under `startU`** name a unit counted from the
  bottom, from the number of the first unit ("Below U5.", "1U free from U46
  to the top."). On a top-down frame they still count from the bottom, as
  they did before, since "past the top" has no label there.
11. **Setback.** It applies to a rack device only: a part on the rail face or
  beside the rack has none, `patch` refuses it one ("CM bolts to the rail
  face, so it has no setback."), and one written by hand is ignored. A
  refusal names it after the depth ("700 mm deep, set back 301 mm; this rack
  allows 1000 mm."), and a proud one reads "set forward 25 mm". **A larger
  setback is REFUSED, on depth alone** (`fitsDepth`): never for an overlap in
  height the rack already held, and also when the same command shrinks the
  rack. Whether a larger rack default should refuse or only warn is for a
  person: a smaller `usableDepth` is accepted silently today and leaves the
  same devices past it, so the consistent choices are to check both or to
  warn on both. A proud faceplate is not checked against a door, since no
  frame states a door clearance yet. **No export note is written for a
  setback:** rack products section 8 names none, so that step is not built.
12. **The setback order is untested on real data at its second step.** No
  catalogue row carries `ears.default` (`rack_index.py` writes no ears until
  #908), so the default ear position of a device is exercised on a fixture
  only.
13. **The 30 mm showcase default** lives on the site. The kit is flush where
  nothing is stated; the site has to drop its default in the release that
  takes this kit, or every faceplate it draws stands 30 mm from where the
  kit fits and routes it.
14. **The sentences of a held item** beyond the two section 7.1 gives: placing
  one ("The catalogue describes no host yet, so a device cannot be put on
  one; heldBy takes only null, which frees it."); a host that is gone ("i7 is held by i4, which is not in this
  rack: place it again, or free it."); removing a host ("DIN switch was held
  by it and stays where it was, held by nothing."); a shrink that drops a
  host ("DIN switch was held by a removed device and stays in the rack, held
  by nothing."), after which an item left above the new top stands in the
  top unit; and the DCIM comment ("On Shelf, which holds it; NetBox has no
  field for that."). An item with both `on` and `heldBy` is kept on load,
  named in a notice and refused by fit until one is removed (rack products
  7.2): "i2 is on i1 and held by i1: a part is bolted over a device or held
  by one, not both, so remove one."
15. **The notices for kept keys** (`frameNotices` in `fit.js`): "This rack
  states 23 in rails; it is drawn and fitted as 19 in." and "PDU A names the
  channel rear-left, which is not known for this frame, so it stands at
  left-rear."
16. **Which parts `configs[].states` lists** (section 4). Built: what a part
  ITSELF can be set to. A placement with an id is listed when its own
  `states`, else its group, else its part declares a list of names, and it
  is not a lamp (`class: led`). Lamps are left out because a state is
  addressed by the outlet and follows `for:` to the lamp, whose own
  vocabulary is already on the drawing; the mapping form
  (`{led-a: [...]}`, on 230 placements) is left out because its keys are the
  lamps inside a part and not state names. On the EVMA8365X that is its 42
  outlets. Across the library the key then holds 99 parts on 10 devices and
  under 4 KB (the three Eaton and Tripp Lite switched PDUs with 82 outlets;
  the power supplies of three Smartoptics DCP shelves and the fans of the
  three Edgecore EPS and the Juniper MX150, 17 parts whose part declares
  `ok`, `fail` or `absent`), where listing every lamp held some 329 KB. A breaker is not
  listed: its rocker declares its states on an element of the part.
17. **What counts as a slot** (section 5). Built: a placement of a
  `class: mount` part that declares `interface` and a `mate` point, the
  mirror of a mount point. No part in the library is one yet, so every
  device publishes an empty list until the bracket of #939 is modelled.
18. **Roll and the routing context** (section 6). `facePoint` is built as the
  note has it. The context a page hands the routes (`portX`, `portY`,
  `guidesOf`) gives rack points, not face points, and is left as it is: it
  gives each where the upright item would hold it, and the kit turns it
  (`rollPoint`). A page that rolls its own points would turn them twice, so
  this is a rule the site has to follow.
19. **A quarter turn.** A part on the rail face is refused one ("Bracket bolts
  to the rail face, so it cannot be rolled a quarter turn."). Its units are
  its width over 44.45 mm, rounded up, and never under one. It is refused where its height does not pass between the
  rails ("WIDE-13 is 577 mm high; rolled a quarter turn that is across the
  opening, which is 451 mm."). It is one solid, with no tray, ring or guide,
  centred across the opening, and a page is told so on load. A port on it is
  turned with it about the centre of its box.
20. **`describe` and `inspect`** say a roll only where an item has one
  ("rolled 90"; `roll: 90`). The export notes of a rolled item are part 9
  and are not written yet.
21. **Readings and the metering scope** (section 4). A PDU that meters nothing
  shows no reading and is named ("BASIC-PDU measures nothing, so there is no
  reading for outlet-a1, input."). **The check for a PDU that meters its
  input or its branches is not built:** it has to know that `outlet-a1` is
  an outlet and `breaker-a` a branch, and nothing the kit loads says what
  kind of part a path is. It needs a key in `configs.json` that this note
  does not give, so readings on such a PDU are kept and shown as given.
22. **The other sentences of states and readings.** A part that declares no
  state ("breaker-a on PDU A cannot be set: it declares no state."); the
  three loader notices (a state that is no name, states that are no map,
  readings kept as written); and a refused `readings.set`. With no parts
  lists loaded a state is stored unchecked, as a configuration is.
23. **`readings` is usable** with a `source`, a time `at` that can be read,
  and `values` absent or a map of part to an object. `readings: null` is no
  key at all. The notice gives the reason that applies: no source or time,
  or values that are no map. The numbers inside a
  value are not checked on load; the schema states them.
24. **Hanging** (section 5). The tolerance is 1 mm, since the connectors
  registry states none for any mounting interface. A refusal that is not two
  mount points on two brackets reads "A mount point of PDU A 1555.8 mm above
  its lowest meets no slot of z3, z4."; a move of under a unit is given in
  mm. A bracket of two cannot be moved alone, since the pitch would no
  longer be met: the part is taken off first. A held part moved by hand is
  refused ("PDU A hangs on z1, z2: move a bracket, or take it off them with
  zerou.hang."). `zerou.hang` needs the parts lists loaded. A frame change
  that would move or remove a hung part, or a bracket it hangs on, is
  REFUSED, naming the part and its brackets ("PDU A hangs on z1, z2, and
  this frame would move it: take it off its brackets first with
  zerou.hang."): a hung part is never moved silently, since the kit writes
  where it stands. `hangNotices` says a part a file holds out of place is
  not where its brackets hold it.
25. **`bracketPositions(rack, {ref, cfg, ru}, ctx)`** takes the part and the
  unit of the lowest bracket, and answers one bracket a mount point, each a
  whole number of units above the lowest, with `exact` saying the points
  then land. It takes each bracket to offer its slot at one height, since
  it is asked before a bracket is chosen.
26. **`swaps` and `fields` beside the rack** are taken by `zerou.update` and
  kept; `patch` still takes a device only. Nothing in the kit draws them.
27. **The export comments of a hung PDU and of states** are written by
  part 9 (item 44 for the states).
28. **Three things of the kit API the note did not decide.** `stateRefusal` is
  the kit's own and not for a page, which reads `stateNotices`. `shrinkRack`
  answers `orphaned` beside `moved` and `removed`: the held items a dropped
  host left behind. A quarter-turned item is exported at the position its
  rolled box starts at, and since part 9 its comment says it is turned.
29. **`measured` in the kit, though no longer in the file** (3.2). `pathLength`
  still answers `measured`, the need and the end play at both ends, since
  two lays of one cable are compared by it and it is the figure a routed
  length was. It is never saved: a file holds `need`.
30. **Units of a slack value.** Only metres and feet convert, as for a cable
  length; `cable.slack` takes `m` or `ft`. A value in another unit is kept
  and reads "a length in a unit that does not convert".
31. **The sentences of slack beyond those section 3.5 gives:** a tray that
  states no place ("CM-01 tray states no place for spare cable."), no
  spool ("CM-01 tray states no spool."), a turn that cannot lie on the
  floor ("A turn of c1 is 67.5 mm across, and the floor of CM-01 tray is
  61.2 mm deep."), a second entry for the rest, and spare left at an end
  given a form. The finding of values past what there is to store compares
  them with what is to store and names it ("has 0.44 m to store"), and is
  raised only past the stock break tolerance, 10 mm. An entry kept on a
  tray the cable cannot store in is a finding of its own kind,
  `spare-off-route`. `spare-unplaced` is a finding of one cable, which
  `inspect` of that cable carries; the rack has one summary line
  (`spareLine`) and never a line a cable. A cable with no length has no
  spare, no finding and no part in that line.
32. **No command writes an empty list.** `cable.slack.clear` with a place
  takes that entry off, and the key with the last; with none it takes the
  key off, so nothing is said again. "Stored nowhere, by choice" can be
  written in a file and is read, and no command yet says it.
33. **With no routes known `cable.slack` records the place as given,** as a
  bundle is made without being measured.
34. **The exports take what the routes know from their caller.** The
  schedule fills `spare` and `stored` when it is handed
  `spareExports(rack, ctx)` and `straps` when it is handed
  `strapTexts(rack, ctx)`; the BOM notes and the draw.io cables take the
  same `spare`. Without them the columns are there and blank, and no line
  is written.
35. **`cable.lay`, as part 10 built it** (decision 17 for which pin wins).
  With the routes known it is refused for a pathway the device does not
  have, for a face on a ring or a duct, for a held face on a tray that
  states no tie slots, and for a face the cable does not come to lie on:
  a tray that is not on its route. The cable lay note also lets a ring on
  the held face offer it, which no part yet has. With no routes known the
  entry is recorded as given, as a place for spare is. Unpinning is never
  refused. An entry whose part or tray is gone is kept and passed over.
  `inspect` of a cable shows `lay` where it has one, and `inspect` of a
  device of a fractional height carries the ear-hole sentence of 2.5 under
  `notes`.
36. **`inspect` of a cable** gains `spare_findings` where it has any, and
  `describe` gives the spare a line of its own after the findings.
37. **Found on main and fixed here:** a cable whose media is named like
  something every object has (`constructor`) got a path with a point that
  is no number, no length, and `value: null` in a saved file. Every table
  the kit reads by a media name is now read by its own keys only.
38. **Where a cable lies on a tray, for its anchor** (3.10). A single cable is
  tied at a tray its path rests on. Its stretch there is the part of its
  path within 12 mm over a floor of the tray (on the floor, or on the sill
  of a ring that stands on it), and the slot is the one whose middle is
  nearest the middle of that stretch along the run, the lower index where
  two are as near. A member of a drawn bundle is not counted again at a
  tray its trunk lies on. For a trunk the stretch is what lies over the
  floors of the way from the waypoint before to the one after.
39. **A side of a peel point** is measured to the end of the run of two or
  more riding, and a spacing strap serves only from its own side of the
  peel.
40. **The words of the strap count.** The BOM line says how many of each kind
  ("3 along 1 bundle, one every 12 in; 4 where a cable joins or leaves a
  bundle", then the slots and its closing words as before), and a bundle
  note gives its kinds where it has more than spacing straps ("7 straps (3
  every 12 in, 4 where a cable leaves)"). `strapBomRows` counts single
  cables only when it is handed `anchorsOf` for the rack.
41. **The kit draws no strap.** An anchor is an entry with its tray and slot;
  the band at the slot is the page's to draw.
42. **Measured.** On the generated sample (78 racks, 364 lacer trays, 2,320
  cables, no bundle): 1,220 anchor straps where there were none, 3.4 a
  tray; 1,699 cables rest on a tray. On the eight bundles the tests hold:
  the trunk along five rings (5 straps, unchanged: a spacing strap serves
  each end), the trunk of 30 in through ducts (3 to 5), the fan-out up the
  lane (2 to 4), the three-member bundle of the exports test (4 to 6), the
  two drawn bundles of its three (4 to 6 each), the eleven cables down one
  lane a unit apart (2 to 10 under decision 14: the 2 spacing straps and 8
  breakout straps, all 19 mm) and the two jumpers of that rack (1,
  unchanged). Every strap of the sample is 19 mm.
43. **The strap widths and the rule that picks one** (decision 15). The
  list is 12, 19 and 25 mm: the common inch sizes of hook-and-loop strap
  (1/2, 3/4 and 1 in) to a whole millimetre, an estimate with no maker's
  sheet held. A strap is 19 mm; 25 mm where the pack at it is 25 mm across
  or more (`WIDE_PACK_MM`, a figure of this build); and in a gap too tight
  for that, the widest of the list that leaves 5 mm clear each side
  (`STRAP_CLEAR_MM`, an estimate). The 20 mm that keeps a strap off a ring
  (`STRAP_W`) is unchanged, so no strap of before moves. An anchor is
  capped by the long side of its tie slot, read from the `ties` of the
  tray; that a strap needs no room beyond its own width in the slot is an
  assumption.
44. **Outlet states in the DCIM files** (section 4). The NetBox outlet
  import refuses a `status` column (tried on 4.7.2; file and lines in
  section 4), and no import-script step exists to try, so both
  device files carry one comment line ("Outlets off: A2, A7."). An outlet
  is named as the device-type export names it: `<device>.configs.json`
  gains `names` on each configuration, `{<path>: <name>}`, read from the
  `interfaces:` of the device by the function that names the exported
  outlets, so the two cannot disagree. It is additive, and the kit reads it
  as `configFacts().names`. A part with no name there is named by its
  path, and a part that is no outlet is in a line of its own ("Off:
  psu-1."). Only `off` is written, and only for a part that declares the
  state. The kit writes the line when its caller hands `deviceImportRows`
  a `statesOf`, and uses the names when it is handed a `namesOf`.
45. **The `straps` column** names a single cable's own slots, on either face
  ("CM-01 tray, resting face (top), tie 11"), by slot number from 1; slots
  that are no one run are each named ("ties 5, 6, 9 and 10"). A member of a
  drawn bundle is blank at a tray its trunk lies on, as it is not counted
  there. The BOM note a tray of the cable lay note (5.5) is not written:
  the strap line of the BOM counts the slots.
46. **Readings in the exports.** No export of the kit shows a reading, so
  none states a source and a time; `readingsFor` gives both to a page that
  shows one. A test holds that neither device file carries any.
47. **Running instances.** The exports were tried on NetBox 4.7.2 and
  Nautobot 3.2.6, from the files the kit writes.
  **Held as this note says:** a whole-unit rack; two half-unit panels in
  one unit (NetBox stores 7.0 and 7.5; Nautobot takes the lower at 7 and
  keeps the other in the rack with no position, no face and its comment);
  a top-down rack (the lower stored at 34.5, the upper at 34, the labels
  as `uText` gives them); 1.5U and 3.5U items with a half-unit panel
  above; a rack row with `comments`; widths 10, 19, 21 and 23, and 24
  written as 19 with a comment; a held item, a hung PDU and its brackets
  with no position or face; the roll comments. An outlet CSV with `status`
  and a rack CSV with `starting_unit` are each refused as an unrecognised
  header. Nothing was stored differently from the file, and neither
  platform limits the length of a comment.
  **Found wrong, and fixed:** a front and rear pair in one unit in the
  Nautobot file while a type is full depth (2.7; a fault of the export on
  main too); the order of steps in the `startU` rack comment (item 9); a
  quarter-turned item, which is a row of its 1U type, so both platforms
  show the other units free: its comment now says which units it fills
  ("Turned, it occupies U30-U34 on the rack; the device type is 1U.");
  the outlet names (item 44); and the limits table, where the device name
  of Nautobot is 255 characters and of NetBox 64, and the rack name of
  NetBox is 100, which the rack row now screens.
  **Still not tried:** Nautobot cables, whose import needs an API token;
  NetBox cable bundles, since the kit writes none; an outlet-state step of
  the import script, since none exists; and a real PDU bracket or shelf
  host, since the catalogue has none: the bracket was a hand-made 0U type
  and the sizes nominal.

## 14. A cable's own colour (#1028), added after version 4 shipped

Built in kit 0.31.0, with no new rack file version: section 1.2 has a reader
keep a cable key it does not know, so a kit before 0.31.0 opens a file that
carries the key, keeps it, writes it back, and draws the cable by its media.

### 14.1 What was there

A drawn cable's colour was its media's and nothing else
(`kit/rack/cable-geometry.js`, `COLORS` and `colorOf`). `cablePlan` handed a
drawing the media and the purpose. A seated cable end's `jacket-color` field
coloured its drawn stub and not the cable. The rack file had no colour for a
cable, and the cable types table had none for a type. So an AOC was dark
grey whatever was said of it, and on a dark stage nearly invisible.

### 14.2 The order

**Decided 2026-10-18:** this order, and `color` as the new saved key on a
cable. Nothing else in this section is decided by that (see 14.3 and 14.7).

A cable is drawn in the first of these that says something:

1. **its own colour**, `color` on the cable in the rack file;
2. **its ends'**: the jacket colour its two seated ends state, when both
   state one and the two agree;
3. **its type's**: the `jacket` of the cable type it names in `type`;
4. **its media's**, from `COLORS`, as before.

Every view and export asks the kit: `cableColor(link)` gives `{color, from}`
and `colorOf(link)` the colour, for a link of `cablePlan` or `cablePlan3d`,
which carry what decides it (`color`, `jackets`, `typeColor`).

![Four AOC cables on one rack: one with its own colour, one whose two ends agree, one whose ends differ, one with nothing stated](img/cable-colour-order.svg)

The figure is a sketch drawn from the kit's own answers for one rack
(`cablePlan` with the readers, then `colorOf` of each link), not a page's
drawing. The last two cables are the media's dark grey, as every AOC was.

### 14.3 What was decided in the build

Each is built, and each waits for a person to confirm it, as section 13's do.
The order of 14.2 and the `color` key were decided 2026-10-18; no item below
is marked decided by that. Items 3 ("both ends, or neither") and 5 (a type's
colour for a named type only) are how items 2 and 3 of 14.2 read, and are decided only as far as the order says so. Their further
wording here, and every other item, still waits.

1. **A colour is hex.** `#` and three or six hex digits, either case, stored
   as `#rrggbb` in lower case. That is how `jacket-color` is written on
   every cable end of the library (four values, all hex) and what
   `fields.js strokeShade` reads. A colour name is not taken: `red` would
   need a table of names nobody has agreed, and a draw.io file, NetBox and
   Nautobot each take hex only. A value that is no colour is refused by the
   commands with a sentence ("A cable color is # and three or six hex
   digits, such as #2bb3c8, or empty for none of its own."), moved to
   `colorAsWritten` by the reader, and never drawn: nothing here turns an
   unreadable colour into black.
2. **A default is not a statement.** The generic cable ends declare
   `jacket-color` with a default, `#1c1c1c` on most. If a default counted,
   every cable between two generic ends would turn black, which is the
   opposite of what was asked. So an end states a jacket colour only when
   the rack sets the field for the part seated in that port (`fields` of
   the item; the default's own colour, set on purpose, counts) or when the
   part's own contract gives its jacket one (a maker's part that composes
   the generic end: `siemon/qsfp28-aoc@1` states its aqua so). That is the
   library's own usage: a maker's part sets `jacket-color` on the generic
   end it composes only where its document states the colour ("it is set
   here because this document states it"), and leaves it out where the
   document is silent ("NOT STATED ... the generic's default stands"). A
   field value that is no hex colour states nothing, and does not fall back
   to the part's own: the rack said something else of that end.
3. **Both ends, or neither.** One stated end and one bare end is no
   agreement, and nor are two ends that differ. The type then decides,
   else the media. No colour is mixed or averaged.
4. **The kit reads the ends from the parts lists** (`ports.js seatedJacket`,
   over what `loadSlots` returns), so an agent with no drawing gets the same
   answer as a page. A page that reads an end off its drawing passes a
   `jacket` key on that end's entry of its cable facts, and where the key is
   there it stands. A plug a page seats for a cable is in no rack file, so
   only the page can speak for it.
5. **A type's colour is read for a named type only.** A cable is drawn in a
   type's `jacket` when its own `type` names that type. The bare type of
   its media is never asked, and the cable types build refuses a `jacket`
   on a bare media type, so that `COLORS` stays the one table of defaults.
6. **A bundle's band.** Where a view draws one thing for a whole bundle, it
   is the members' colour when they are all one, and no colour at all when
   they differ (`bundleColor`: `color: null`, `mixed: true`). Any one
   member's colour would say the others are that colour too. In the 2D
   elevation and the 3D pack each member is drawn on its own and keeps its
   own colour either way.
7. **draw.io** draws a cable in its colour when rule 1, 2 or 3 gives one. A
   cable coloured by its media alone is filed under its media as before,
   and takes the entry of the draw.io writer's own palette.
8. **NetBox and Nautobot** get the cable's own colour and nothing else, in
   the `color` column both files already had and left blank: six lower-case
   hex digits with no `#`. Both store a cable's colour so (NetBox v4.7.2
   251458b8, `netbox/dcim/models/cables.py` `Cable.color`, a `ColorField`
   whose `ColorValidator` in `netbox/utilities/validators.py` is
   `^[0-9a-f]{6}$`, and `color` in the fields of `CableImportForm`,
   `netbox/dcim/forms/bulk_import.py`; Nautobot v3.2.6 3dc554b4,
   `nautobot/dcim/models/cables.py` `Cable.color`, the same field and
   validator in `nautobot/core/models/fields.py`). A colour worked out from
   the ends, the type or the media is how the kit draws the cable, not a
   fact someone recorded of it, so it is not written. **Not tried on a
   running instance.**
9. **The cable schedule and the BOM gain no column.** `describe` and
   `inspect` show a cable's own colour when it states one.
10. **A colour is no part of a lay.** Nothing in `route.js` reads it, so a
    colour set or cleared lays no cable again, and `ctx.checkKept` has
    nothing to find.

### 14.4 One-way items

| item | where | what moves |
|---|---|---|
| `color` and `colorAsWritten` on a cable | rack file | saved files carry them; a `color` that is no colour, which a kit before 0.31.0 kept as an unknown key, now moves to `colorAsWritten` |
| the two keys in `rack.schema.json`, `color` with a `pattern` | published schema, `/schemas/v3/` | the first `pattern` in that schema; a validator that does not know the keyword passes any text |
| `color` on `cable.add` and `cable.update` | kit commands | agent sessions call them by name |
| `color`, `jackets`, `typeColor` on a link of `cablePlan` and `cablePlan3d`, each only when it says something; their second argument | kit output | a reader that compares a link key for key sees them on a cable that states a colour |
| `colorOf` reads those keys before the media | kit API | a caller that put a `color` on a link for its own use is now drawn in it |
| `color` on a row of `drawioCables`, and the draw.io writer drawing it | draw.io export | only a cable whose colour is said |
| the `color` cell of both DCIM cables files | DCIM export | only a cable with its own colour; blank before |
| `color` in `inspect` of a cable, and after the media in `describe` | kit output | only a cable with its own colour |
| `validate` knows `pattern` | kit API | a command argument or schema with a `pattern` is now held to it; none had one |
| `jacket` on a cable type, table version 1.1.0, and the type `aoc-siemon-q1q28f` | `cable-types.json` | additive; no rack names the type |
| `typeColorOf` in what `loadCableTypes` returns | kit output | additive |

**What does not move:** the colour of every media, so every drawing, sheet
and 3D file of a rack that states no colour; the four values of `JACKETS`;
every recorded answer of `spec/tests/js/speed-goldens.json`; the columns of
every export.

**What does move, by design:** a rack that already seats two cable ends
that state the same jacket colour is drawn in that colour once a page passes
the readers. That is rule 2 doing what it was asked to. Four parts of the
library state one today, and no device or lab sets the field:

| both ends | states | on | the cable goes from | to |
|---|---|---|---|---|
| `siemon/qsfp28-aoc@1` | `#49eaf8` | counted on the sheet's photograph | `#3a3f45` (aoc) | `#49eaf8` |
| `volex/qsfp-dd-passive-dac@1` | `#1c1c1c` | the datasheet's "Cable Colour Black" | `#15171a` (dac) | `#1c1c1c` |
| `amphenol/qsfp56-linear-active@1` | `#1c1c1c` | the drawing's "PVC BLACK" | `#15171a` (dac) | `#1c1c1c` |
| `credo/hiwire-shift-qsfp-dd@1` | `#6b3fa0` | the brief's word "purple"; **the shade is an estimate, not a reading** | its media's | `#6b3fa0` |

The two blacks differ from the DAC default by seven steps a channel and
read the same. The purple is the one colour here that nothing counted: its
contract says so, and a cable between two such ends takes it.

### 14.5 Open: three tables name a colour for an AOC, and they disagree

Not settled here. No colour was changed to settle it.

- `COLORS.aoc` in `kit/rack/cable-geometry.js` is `#3a3f45`, dark grey. It
  decides what the Rack Builder draws: the elevation, the sheet and 3D.
- `JACKETS` in the same file has no entry for an AOC. Its comment said
  multimode fibre and AOCs are aqua, and the front-page hero draws an AOC
  with the `mm` jacket, `#2bb3c8`. `JACKETS` now names entries of `COLORS`
  and holds no colour of its own, so the two tables cannot drift; what the
  hero passes for an AOC is the hero's choice, and is as it was.
- `CABLE_COLOURS.aoc` in `kit/drawio.js` is `#2F80C0`, blue. That table is
  the draw.io writer's own palette for a white page, and differs from
  `COLORS` for every media, not only this one.

The one source the library holds is Siemon's 100G QSFP28 AOC, aqua on its
maker's photograph (`#49eaf8`, counted). It is now the `jacket` of the named
type `aoc-siemon-q1q28f` and was already the stated jacket of
`siemon/qsfp28-aoc@1`, so a cable between two of those ends is aqua by rule
2. No source is held for a 400G QSFP-DD AOC.

**The question:** should `COLORS.aoc` become aqua? One maker's 100G cable is
not every AOC, and a changed default recolours every drawing, sheet and 3D
file with an AOC in it. If it should, the change is one line in `COLORS`,
with a test that says so (`rack-cable-colour.mjs` holds every default to
what it was). Whether the draw.io palette should follow `COLORS` is the
same kind of question for every media.

### 14.6 Not built

- A command that sets a cable's `type` (#897). A type's colour reaches a
  cable whose file names the type; nothing in the kit writes that key yet.
- A colour for a bundle, a strap, or a plug.
- A jacket colour for any type but the one with a source.

### 14.7 Still open

- **The AOC default** (`COLORS.aoc`, 14.5): whether it becomes aqua. One-way:
  it recolours every existing drawing, sheet and 3D file with an AOC.
- **The draw.io palette** (`CABLE_COLOURS` in `kit/drawio.js`): whether it
  follows `COLORS`. One-way for the same reason.
- **The Rack Builder page's half**, which is not in this repository: the
  cable form's colour input, and passing the readers to `cablePlan` and
  `cablePlan3d`. Until it does, no page shows a colour from the ends or a
  type.
- **Named cable types with sourced jacket colours** (#897): each type needs a
  source for its colour; the table holds one today.
- The rulings of 14.3 other than the order, as noted there.

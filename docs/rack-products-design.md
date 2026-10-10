# Rack and cabinet products: the library format

Status: proposed 2026-10-09, nothing built. Issue #935. Each section's
decision is a recommendation; the five questions the note left open were
decided as it recommended on 2026-10-09, and are listed at the end of section
11.
Two decisions are already taken and are not reopened here: doors are drawn
OPEN by default, and a drawer is a real cavity that items can go inside.

Builds on the rack file and the kit's rack core (`kit/rack/`, rack file
`version` 3, `spec/schemas/rack.schema.json` under `/schemas/v2/`), on
[vertical-cable-managers-design.md](vertical-cable-managers-design.md) section 8
(zero-U parts and attachment points in the kit, #926), on
[pdu-model-design.md](pdu-model-design.md) section 6 (mount point, slot,
`pdu-button`, pitch and `mount-points`), on rail kits and ears (#904, #905,
#906, #907, #908, #909) and on [format-stability.md](format-stability.md). It
is read with #936 (reseller listings), #939 (PDU brackets) and #550 (vertical
mounting).

The goal: racks and cabinets become library products, shown in the Rack Builder
beside the customisable generic frames, which stay; and the accessories that go
in them (blanks, shelves, drawers, DIN rail brackets, fans, PDU brackets) become
building blocks first, with shelves, drawers and DIN rail able to hold things.

## What exists

- **The frame** is the rack file's own record:
  `{kind: four-post | two-post, heightRU, numbering: bottom-up | top-down,
  holes: {style: square | tapped, thread: 12-24 | 10-32 | M6 | null},
  railDepth, usableDepth, ref}`. `ref` is described as the catalogue rack the
  frame was taken from and is always `null` today: the key was kept for this
  note. `normalizeFrame` rebuilds the frame from these keys only, so a frame
  key it does not know is dropped on load and erased on the next save.
- **Positions** are stored bottom-up whatever the labels say. `uLabel` and
  `positionOf` turn them into labels; no frame starts anywhere but U1.
- **Zero-U parts** (#926) stand at an attachment point of the frame: `left` and
  `right` on a two-post, `left-front`, `right-front`, `left-rear` and
  `right-rear` on a four-post. The point also names the cable lane beside that
  upright. Two parts on one point never overlap in height; on two points they
  never meet. Section 8 of the vertical managers note left three things for
  this note: a named channel, so a PDU inside a cabinet's channel and a duct
  outside the upright do not meet; the mounting interface a channel takes; and
  the fit check of a part's mount points against it.
- **The mounting vocabulary** is set (PDU note, section 6.2): a mount point on
  the hanging part (a button) carries `mates: pdu-button`; the slot that takes
  it (a keyhole in a bracket or a channel) carries `interface: pdu-button`; the
  pitch is derived from the placements and published per configuration as
  `mount-points: [{mates, at}]`.
- **Rail kits and ears** (#905, #906): `kind: kit` beside `component` and
  `module`, published in `kits.json`; `chassis.kits` and `chassis.ears` on a
  device, with named ear positions and their `at`. `rack.json` does not yet
  carry a device's default ear position (#908, open).
- **The faceplate setback** is 30 mm for every device in the Rack Builder, its
  3D scene's showcase default. A per-item and per-frame `setback` was built in
  the site and paused unmerged (portrayal-site#139, part 3).
- **`rack.json`** (`format: 1`) is the one-fetch catalogue of placeable devices.
  It has no racks in it.
- **The DCIMs.** NetBox has a rack type (`RackType`, manufacturer, model and
  slug) whose fields are `form_factor`, `width`, `u_height`, `starting_unit`,
  `desc_units`, `outer_width`, `outer_height`, `outer_depth`, `outer_unit`,
  `mounting_depth`, `weight`, `max_weight` and `weight_unit`, and
  `cooling_capability` and `cooling_capacity`. Its form factors are
  `2-post-frame`, `4-post-frame`, `4-post-cabinet`, `wall-frame`,
  `wall-frame-vertical`, `wall-cabinet` and `wall-cabinet-vertical`, and its
  widths 10, 19, 21 and 23 in (`dcim/choices.py` `RackFormFactorChoices` and
  `RackWidthChoices`, `dcim/models/racks.py` `RackBase`, at netbox-community
  commit 84e19368). Nautobot has no rack type: the same seven slugs plus
  `other` are the `type` of a rack itself, beside `width`, `u_height`,
  `desc_units`, `outer_width`, `outer_depth` and `outer_unit`, and it has no
  field for a starting unit, an outer height, a mounting depth, a weight or a
  load (`dcim/choices.py` `RackTypeChoices`, `dcim/models/racks.py`, at
  nautobot commit c77e4255).

## What the sources say

The sources are FS's datasheets, quick start guides and compatibility matrices,
and the APC and Schneider installation manuals and submittal drawings, for 10
open-frame racks, 16 cabinet SKUs and 29 accessories. What each breaks in a
simpler model:

| source | what it showed |
|---|---|
| APC AR203A (FS datasheet, APC manual) | four-post, 44U, square 9.5 mm holes for M6 cage nuts, a FIXED 740 mm rail depth from its side brackets; static load only; numbered every third hole at mid-U, and one manual figure that may show labels both ways |
| APC AR201 (FS datasheet, Schneider installation sheet 990-6040B) | two-post, 45U, #12-24 tapped holes, devices centre-mounted to 1048 mm deep; tool-less blanks do not fit it (FS blanking matrix) |
| FS-OR4P-45U (FS datasheet and QSG, discontinued) | an ADJUSTABLE rail depth, 22 to 40 in in 1 in steps, set by index pairs; casters and levelling feet but no rolling rating |
| FS-OR2P-45U (FS datasheet, discontinued) | keyhole slots on the side of each upright at 311 mm pitch, the pitch the 42U FS vertical duct's brackets use |
| APC NetShelter SV, SX Gen2, SX Advanced (installation manuals, submittal drawings) | rail depth adjustable in steps (10 mm SV, 6 mm SX Gen2, 13 mm SX Advanced) about a factory setting; front door-to-rail wiring clearance (14.0, 60.96 and 101.8 to 103.6 mm); front door single and perforated, rear door split; side panels one or two per side; roof cable openings; zero-U accessory channels for tool-less PDUs, two or four, movable; casters and levelling feet; static AND rolling loads (SX Gen2 1818 and 1020 kg); joining brackets at 600 mm centres |
| FS GR600 and GR800 (FS datasheets and QSGs) | full-height PDU brackets on the cabinet's rails, separate parts; GR800 also takes two vertical managers screwed to the frame beside the rails, GR600 none but fixed shelves; rail depth in 12.7 mm steps |
| FS-WMNR-D2P6U, FS-HWM-4U, FS-SVWM-1U and -4U, FS-DR-8U | a wall box with front rails only, a hinged wall bracket, two vertical wall brackets where the equipment hangs face down, and a desktop rack whose posts lean back 9 degrees |
| FS shelves, drawers, DIN rail brackets (datasheets, QSGs, three compatibility matrices) | cantilever shelves on the front rails only, rated 10 to 60 kg; a sliding shelf on four posts with telescopic rails 650 to 950 mm; drawers that slide out of a fixed 412 mm box; DIN rail on an adjustable panel 360 mm deep |
| FS blanks and fans | screw-on, tool-less steel with clips, tool-less ABS: the clip types decide which hole styles a blank fits; one mains-powered fan panel and two fan trays |

Three things follow. A rack product is mostly numbers the Rack Builder already
uses; the new parts are channels, enclosure, base and load. Hole style is a fit
fact, not decoration, because a tool-less part refuses a tapped rail. And the
cabinets FS sells are made by APC, so they are modelled once under their maker
and listed under FS (#936).

## 1. Kind, identity, versioning and lock

**Recommendation: a new manifest kind, `kind: rack`,** at
`library/racks/<vendor>/<name>/rack.yaml`, format 1, with its own lock,
`rack.lock.json`, beside it.

It is not a device with a new `mount: floor`, although that reuses the most.
Against it:

- **A rack is not placed in a rack.** `rack.json`, `devices.json`, the census
  tests and every device rule read a device as something with a U height that
  goes on rails. A floor rack would be an exception in each of them.
- **`ru` would mean the opposite.** A device's `ru` is units it takes; a
  rack's is units it offers.
- **The DCIM record is different.** NetBox imports a rack as a rack type, not a
  device type, and Nautobot has no type at all, only fields of a rack.
- **The vocabulary is new either way.** Channels, doors, panels, base, load and
  baying belong to no device; on a device they would be a large section that
  every other device must not state.

What a rack reuses unchanged is the identity and the version rules, the way
`kind: kit` reused the component rules (#905):

- **Identity**: `<vendor>/<name>`, namespaced by the maker, with `manufacturer`,
  `model`, `part-numbers`, `aliases`, `description`, `maturity`, `provenance`,
  `references` and `gaps` as a device writes them. A rack's `name` is unique
  within its vendor across racks AND devices, so a ref never needs the kind to
  resolve.
- **Versioning**: semantic, as DESIGN section 9 states it. A rack is referenced
  by major, `<vendor>/<name>@<major>`, as a component is.
- **The lock** (`devicelock.py`, which already locks devices and listings):
  - **major**, the numbers a saved rack file copies or positions things
    against: height, numbering and start, posts, rail positions and the rail
    depth range, holes, width, the channels' ids and slot positions, the
    outside attachment points;
  - **minor**, additions: a new channel, a new door option, a load rating
    stated where there was none;
  - **patch**, statements nothing positions against: door perforation, colour,
    provenance, a corrected load figure.
- **Views are optional.** A product frame is drawn from its numbers (section 9),
  so an open frame needs no drawing to be useful. Door and panel art, when it is
  drawn, uses the device `views` machinery and its lint.
- **The schema** is a new file, `spec/schemas/rack-product.schema.json`,
  published under `/schemas/v1/` as format 1: a new kind is additive, as
  `kind: kit` was. It is NOT called `rack.schema.json`, which is the Rack
  Builder's file. The two are easy to confuse, and the docs name them "the rack
  file" and "a rack product" throughout.
- **Reseller listings** (#936) list a rack as they list a device: the APC
  cabinet under its maker, listed under FS with FS's part number.

Accessories are not racks. Blanks, shelves, drawers, DIN rail brackets, fan
panels and PDU brackets are devices (`mount: rack`, or `rack-face` and
`rack-side` where they bolt there), and what lets some of them hold things is a
device key (section 7).

## 2. The frame

```yaml
format: 1
kind: rack
name: ar203a
version: 1.0.0
manufacturer: APC
model: AR203A
form: 4-post-frame             # the NetBox and Nautobot slug (below)
ru: 44
numbering: {direction: bottom-up, start: 1}
width: 19                      # nominal rail width, in: 10 | 19 | 21 | 23
holes: {style: square, size: 9.5, fixing: M6}
rails:
  - {id: front}
  - {id: rear, depth: {fixed: 740}}   # mm, front rail to rear rail
max-device-depth: 740
outer: {w: 600, h: 2130, d: 747}
weight-kg: 40.32                    # the frame's own weight (section 5)
```

The figures are AR203A's from its FS datasheet and APC manual. Its hole
centres and opening are not printed, so the example leaves `hole-centres` and
`opening` out. The examples in later sections show the shape of a key, and
their figures are illustrative unless a product is named beside them.

- **`form`** takes the seven slugs NetBox and Nautobot share
  (`2-post-frame`, `4-post-frame`, `4-post-cabinet`, `wall-frame`,
  `wall-frame-vertical`, `wall-cabinet`, `wall-cabinet-vertical`), plus
  `desktop-frame`, which neither has: it exports as `2-post-frame` to both,
  with a comment line saying it is a desktop rack, since a two-post frame is
  what it is and both DCIMs have that slug. The form also says how the rack stands,
  so a rack has no `mount` key.
- **`ru` and `numbering`.** `direction` is `bottom-up` or `top-down`, the
  frame's existing values; `start` is the label of the first unit, 1 unless the
  source says otherwise (NetBox `starting_unit`). Positions in the rack file
  stay bottom-up from 1 whatever the labels say. A rail that prints labels both
  ways (the AR203A manual figure may) is art, stated in provenance, and
  numbered by the direction the maker's text gives.
- **Posts and rails.** Posts follow from `form`. `rails` lists the rail planes,
  `front` and, on a four-post, `rear`. `at` places the front rail behind the
  front of the frame (on a cabinet, behind the front door's plane, which is
  what the door clearance in section 4 is measured from). It is written only
  when a source gives it, as an ear position's `at` is.
- **Rail depth, fixed or a range.** `depth` is `{fixed: mm}` or
  `{min, max, step?, factory?}`: the FS-OR4P-45U is 559 to 1016 in 25.4 steps,
  the SX Gen2 1070 deep is up to 921 in 6 mm steps from a factory 737. A range
  can depend on fitted options (SX Gen2's channels lower its maximum to 781);
  that is a second range under `with: [<option>]`, read with the options in
  section 4. The rack file holds the depth chosen (section 9).
- **Holes.** `style` is `square`, `round` or `tapped`; `thread` is `12-24`,
  `10-32` or `M6` on tapped holes; `size` and `fixing` say what a square or
  round hole takes. The style is a fit fact: a part that clips into holes says
  which styles it fits (section 7), so a tool-less blank is refused on AR201's
  tapped rail as FS's matrix refuses it.
- **Width.** 19 in nominal everywhere in the intake; 23 in is an SX Gen2
  option and the reason the FS-EB extender brackets exist. `hole-centres` (mm,
  left hole line to right) and `opening` (mm clear between the rails) are
  written only where a source prints them. Every source that prints them gives
  hole centres 465: AR201's installation sheet (990-6040B) with opening 450,
  the FS-OR2P-45U datasheet with opening 452, the FS-OR4P-45U datasheet with
  opening 450, the FS-DR-8U datasheet with opening 451, and the FS-HWM-4U and
  FS-SVWM-4U datasheets with opening 450. The FS-WMNR-D2P6U datasheet prints
  only an opening, 452, and no hole centres. Where none does, the EIA-310
  figures are assumed and the product says so in `gaps`.
- **`max-device-depth`** is the maker's usable depth, the rack file's
  `usableDepth`. On a cabinet it is what the doors allow, not the rails.
- A post's profile (AR201's 76 mm channel, the FS-OR2P's 120 mm extrusion) is
  drawing data, under `posts: {profile, w, d}`, and nothing fits against it.

## 3. Zero-U channels and attachment points

**Recommendation: a product names its channels, each tied to an attachment
point, each offering slots with an interface; the rack file names the channel a
zero-U part stands in; overlap is judged per channel.**

```yaml
points: []                        # a cabinet: nothing stands OUTSIDE its side panels
channels:
  - id: left-rear
    point: left-rear              # the kit attachment point it belongs to
    where: inside                 # inside the side panel, between the posts
    ru: 42
    slots: {interface: pdu-button, first: 210, pitch: 1555.8, count: 2}   # illustrative
    moves: {front-back: true, up-down: true}
```

- **`point`** is one of the kit's attachment point names, so everything #926
  built (lanes, `fitsZeroU`, `settleZeroU`, describe and export) finds the
  channel. A channel's own `id` is free, so a cabinet with two channels a side
  names them (`left-front`, `left-rear`, or `left-rear-1`, `left-rear-2`).
- **`where`** is `inside` (between the front and rear posts, inside the side
  panel: the SX and SV channels) or `outside` (against the upright's outer
  face, as a duct stands today).
- **`points`** lists the attachment points where a part may stand OUTSIDE the
  frame. An open frame lists all of its own; a cabinet with side panels lists
  none, which is what FS's vertical manager matrix says (no full-height duct
  fits any cabinet). Absent, every point of the form is allowed, as on a
  generic frame.
- **`slots`** is a channel's slot column: `interface` from the connectors
  registry (`pdu-button` today), and the positions as `first` and `pitch` and
  `count`, or a list `at: [mm, ...]`, in mm above the bottom of the rails. It
  is stated because a rack product is drawn from its numbers and has no
  placements to derive it from. A part's `mount-points: [{mates, at}]` (PDU
  note, 6.2) are checked against it: every mount point lands on a slot of the
  interface it mates, within the interface's tolerance, or the placement is
  refused with a sentence naming the point that misses.
- **A bracket is not a channel.** A PDU bracket (FS-PDUBK, #939) is a device,
  and its keyholes are component placements whose part carries `interface:
  pdu-button` and a `mate` point (L11), as the PDU note sets out. Its slot
  positions are derived from those placements, as a PDU's mount points are,
  and no pitch is stated. The fit check is the same comparison, against the
  channel's `slots` or against the bracket's derived positions; the published
  shape of the bracket's side, and the rack-file key for a PDU hung on
  brackets, come with #939.
- **Upright keyholes.** The FS-OR2P-45U's 311 mm keyholes and the 42U duct's
  311 mm brackets are the first pair a check could hold. The interface is
  named (`vcm-keyhole` is proposed) only when a rack product and a duct in the
  library both have a source for it; until then the duct is placed at a point
  without a slot check, as today.
- **`moves`** records a channel that slides front to back or up and down (SX
  Gen2). The first build places a part at the factory position; a stored
  position is a later key.

In the rack file a zero-U entry gains `channel`, the id of a channel of the
product frame. With it, the part stands in that channel, is drawn there, and
claims height in that channel only, so a PDU inside and a duct outside on one
attachment point do not meet. Without it, the entry stands outside at its
point, exactly as today. On a generic frame there are no channels and nothing
changes.

## 4. Doors, side panels, roof and cable entry

**Recommendation: the enclosure is data first and drawing second; doors are
drawn open; a cable entry is a pass-through the router can later use.**

```yaml
enclosure:
  doors:
    - {face: front, leaves: 1, kind: perforated, open-area: 80, hinge: left,
       reversible: true, swing: 180, clearance: 60.96, lock: key}
    - {face: rear, leaves: 2, kind: perforated, open-area: 80}
  panels: {per-side: 2, split: top-bottom, removable: true, lock: key}
  roof: {removable: true}
  entries:
    - {where: roof, kind: brush, box: {x: 100, z: 120, w: 200, d: 80}}
    - {where: floor, kind: open}
options:
  - {id: rails-23in, width: 23}
```

- **Doors** are drawn OPEN by default. In 3D an open door swings to its
  `swing` (or 110 degrees where none is stated) about its hinge side; in the 2D
  elevation an open door is not drawn over the rails, and its hinge side is
  marked. A view may close them; the file stores nothing until it does.
  `kind` is `perforated`, `solid`, `glass` or `mesh`; `leaves` 1 or 2 (split);
  `open-area` is the perforation percentage the manual states.
- **`clearance`** is the door-to-rail wiring space at that face, written only
  where a source gives it: the APC manuals give the front only (SV 14.0 mm, SX
  Gen2 60.96, SX Advanced 101.8 to 103.6). It is the one door fact fit uses: a device whose
  front stands proud of the rail by more than the clearance (its setback,
  section 8, plus any handles the drawing has) is warned about, since the door
  would not close. A warning and not a refusal, because the door is drawn open
  and the user may mean it to stay open.
- **Side panels and roof** are drawn and counted; they decide `points` above.
- **Cable entries** (`brush`, `knockout`, `cutout`, `open`) are boxes in the
  roof, floor or a side, in the product's own frame of reference. They are
  pass-throughs in the sense of the cable managers note: nothing routes through
  them in the first build, and a later route can end at one.
- **`options`** are the sold variations that change a number (23 in rails, a
  rail depth with channels fitted). A rack file names the options it takes
  (section 9); a product with none states none.

## 5. Base and load

```yaml
# NetShelter SX Gen2: the SX Gen2 manual's loads and the AR3380B2 bottom view
base:
  casters: 4
  levellers: 4
  anchors: {holes: 4, dia: 18, rows: 905}   # mm between the front and rear rows
load: {static-kg: 1818, rolling-kg: 1020}
```

- **`weight-kg`** is the rack's own weight, as a device's `chassis.weight-kg`
  is a device's, written only where a source gives it (AR203A 40.32 kg in its
  APC manual, as section 2's example writes it; FS-WMNR-D2P6U 10.95). It is
  what the DCIM export writes as the rack's `weight` (decision 5), and it is
  not counted against `load`, which is what the rack carries.

- **`load`** is the maker's static and rolling rating. A rating not stated is
  not written (the FS-OR4P-45U has casters and no rolling figure), and the
  catalogue says "not stated", never zero.
- **The check is a warning.** The kit sums the placed items' `chassis.weight-kg`
  and compares the sum with `static-kg`; items with no weight are counted and
  named ("12 of 19 items state a weight"). Over the rating is a sentence in
  `describe` and the export notes, never a refusal: weights are often missing,
  and a refusal on a sum of guesses misleads. Rolling load is shown beside it
  and checked only when a later view says the rack is being moved.
- **Casters, levellers and anchors** are drawn in 3D and listed in the parts
  count. Anchor positions are data for a later room view.

## 6. Baying

**Recommendation: describe it on the product now, build it with rows later.**

```yaml
baying: {centres: 600, brackets: apc/ar-joining-bracket@1, trim: apc/ar7600@1}
```

Two cabinets are joined side by side with brackets, at 600 mm centres as
shipped, and with a trim for a wider gap. That is a fact about two racks, so it
is checked only when a document holds a row (section 10). A rack file today
holds one rack, and `between: true` on a zero-U entry already says a part
serves this rack and the next. Nothing in the rack file changes for baying in
this note.

## 7. Hosting: shelves, drawers and DIN rail

**Recommendation: a device declares what it hosts under a new top-level
`hosts:` key; the rack file places an item on a host with a new `heldBy` key; fit
judges the footprint, the height and the load; describe and export say where it
is.**

### 7.1 What a host declares

```yaml
hosts:
  - id: tray
    kind: surface              # surface | cavity | rail
    box: {x: 14, y: 3, z: 0, w: 430, d: 250}    # mm in the device's own frame
    support: cantilever        # cantilever | four-post
    load-kg: 10
  - id: drawer
    kind: cavity
    box: {x: 20, y: 5, z: 10, w: 420, d: 390, h: 78}
    opens: {motion: sliding, travel: 380}
    load-kg: 20
  - id: rail
    kind: rail
    rail: ts35-7.5             # IEC 60715 top-hat, 35 x 7.5
    box: {x: 20, y: 40, z: 120, w: 440}
    set-back: {min: 60, max: 300}
    load-kg: 15
```

- **The frame of reference** is the device's own: `x` from its left, `y` up
  from its bottom, `z` back from its front, as the plan views and the 3D build
  already use. `box` is where the host's usable space starts and how far it
  goes.
- **`surface`** is a shelf floor: `w` by `d`, open above. Its headroom is not
  the shelf's to say; the rack decides it (7.3). `support` is how the shelf
  hangs, and it is not checked against the rack on its own: the shelf's ear
  positions and kits already restrict it (a sliding shelf lists a sliding kit
  whose configurations name `4-post`, #906), and `support` is what describe
  says.
- **`cavity`** is a closed space with an inside height: the drawer. Items
  inside it are hidden in 2D and drawn in 3D when the drawer is open. `opens`
  reuses the kit vocabulary of motion and travel.
- **`rail`** is a DIN rail: its profile (`ts35-7.5`, `ts35-15`, and others
  only when a device needs them), its length `w`, and the range it can be set
  back (DINRAIL2U and DINRAIL4U adjust it;
  [adjustable-positions-design.md](adjustable-positions-design.md), #950,
  decided 2026-10-10: the host follows an adjustment and does not restate
  the range). A
  `mount: din-rail` device is the only thing it takes. The AurCore switches are
  the first such devices.
- **`load-kg`** is the maker's rating for the host, warned about as the rack's
  load is (section 5).
- **Compiled** as invisible `data-class="host"` rects on the top view, as
  guides and pass-throughs are, so the 3D build and the Rack Builder find the
  space without a second statement.
- **In the lock** a host's `id` is addressing (renaming or removing one is a
  major, since a saved rack names it), its box is geometry (a major), and its
  load figure a statement.
- **Hole styles** are the other accessory fact fit needs: a part that clips
  into rail holes states the styles it fits as `chassis.ears.holes:
  [square, round]` (absent, any), so the FHU-BPSTL blanks are refused on a
  tapped rail.

### 7.2 What the rack file says

An item on a host is an ordinary entry of `items`, so its ports, cables,
bundles, swaps and fields work as every item's do:

```json
{"id": "i7", "ref": "ais2002p", "cfg": "", "label": "Edge switch",
 "ru": 12, "face": "front", "turned": false, "swaps": {}, "fields": {},
 "heldBy": {"item": "i4", "at": "rail", "x": 35}}
```

- **`heldBy`** is `{item, at, x, z?, turn?}`: the host item's id, the host's
  `id` on it, and where on it in mm: `x` across from the host's left (along a
  rail), `z` back from its front edge (not on a rail), and `turn` 0, 90, 180
  or 270 degrees about the vertical, for a box set down sideways.
- **Why `heldBy` and not `host`.** The rack file already has a host: a
  rack-face manager's `on` and `unit` name the device it bolts over, and the
  kit calls that its host. A second key named `host` with another meaning
  would be read as the first. The two never meet on one item: `on` is only for
  a `rack-face` part, and a `rack-face` part is never held (7.3). An item that
  carries both is kept as written, never repaired, and refused by fit until one
  is removed.
- **`ru` is kept.** A held item that is not `mount: rack` (a DIN rail
  switch, a desktop box, something in a drawer) has its host's bottom U as its
  `ru`: the kit writes it and keeps it in step when the host moves, as managers
  on a host are settled today, so every reader that sorts or labels by U goes
  on working, and `heldBy` is what decides. A `mount: rack` device standing on
  a shelf keeps its own U and claims its units (7.3).
- **`face`** is the host's face.
- **A host removed** leaves its items where they were, unhosted and refused by
  fit until they are placed again, said with a note; it never deletes them, as
  a cable is never deleted.

### 7.3 Fit

- **Footprint.** The item's width and depth (turned) lie inside the host's box
  and do not overlap another item on the same host. On a rail, only `x` and the
  width along the rail count.
- **Height.** A `cavity` gives its own `h`. A `surface` gives headroom up to
  the underside of the next thing above it on that face; a hosted item claims
  the rack units its top reaches, so a rack device is refused there with a
  sentence naming the item on the shelf. A `rail` gives the bracket's clear
  height.
- **Kind.** A rail takes `mount: din-rail` of a matching profile; a surface
  and a cavity take any device that is not `rack-side` or `rack-face`. A `mount: rack` device
  standing on a shelf (a 2U box on a cantilever shelf) is placed at its own U
  as any rack device is, and names the shelf in `heldBy` only to say what holds
  it; it claims its units as it always did.
- **Load** is a warning (section 5).

### 7.4 Describe and export

- `describe` and `inspect` say "on the DIN rail of DINRAIL2U (i4) at U12,
  35 mm from the left"; the parts list counts hosted items with the rest.
- **DCIM.** A hosted device is a device in the rack with no position and no
  face (NetBox and Nautobot both allow a non-racked device in a rack), and a
  comment line saying what it is on. Neither DCIM models a shelf's contents;
  the comment is the record.

## 8. Setback

**Recommendation: adopt the paused site design's keys into the kit's rack
format, and settle the order in which a setback is found.**

- **`setback`** on an item: millimetres the faceplate stands behind its rail's
  plane, measured into the rack from the face it is on; negative is proud. On
  the frame, `setback` is the rack's default. Both are optional and absent until
  set, the shape the paused site branch already wrote.
- **The order**: the item's own `setback`; else the device's default ear
  position from `rack.json` (#908 adds `ears: {default: {name, at}}`), whose
  setback is `-at`; else the frame's `setback`; else 0, flush. A default
  position with no `at` is used only when its name settles it: `flush` is 0;
  any other name without `at` (`recessed`, `proud`, `mid`, `rear`) falls
  through to the frame's `setback`, since the name alone gives no distance. A device that
  states its ears knows better than a rack-wide default; the default is for the
  many devices that state nothing.
- **Fit** uses setback plus depth against `usableDepth` and the depth the
  other face leaves, and the door clearance (section 4) for a proud front.
  Increasing a setback is checked; reducing one is never refused.
- **#908 lands unchanged**: `rack.json` carries each device's default position
  and its default kit's motion and depth range, `format: 1`.
- The 30 mm showcase default goes: with no statement anywhere a faceplate is
  flush.

## 9. The Rack Builder: product frames and the rack file

**Recommendation: product frames are a catalogue in `rack.json`; choosing one
copies its numbers into the frame and sets `frame.ref`; the frame keys the
products need beyond today's are added in one rack file version, 4.**

- **The catalogue.** `rack.json` gains `frames`, keyed by ref, each row every
  key the Rack Builder needs: identity and listings (so a search by an FS part
  number finds the APC product), `form`, `ru`, `numbering`, `width`,
  `hole-centres`, `opening`, `holes`, `rails`, `max-device-depth`, `outer`,
  `weight-kg`, `points`, `channels`, `enclosure`, `options`, `base` and
  `load`. A new key; `rack.json` stays `format: 1`.
- **The generic frames stay.** A frame with `ref: null` is edited and fitted
  exactly as today.
- **Choosing a product** writes `ref: "<vendor>/<name>@<major>"` and copies the
  product's numbers into the frame: `kind` from `form`, `heightRU`,
  `numbering` (and `startU` from version 4), `holes` (`style` and `thread`),
  `railDepth` (the factory or fixed depth), `usableDepth`
  (`max-device-depth`), and from version 4 `width` and the `options` the rack
  takes. The file still stands alone, so a page without the catalogue draws
  the same frame. Product-only data (channels, doors, points, load, weight, and
  a hole's `size` and `fixing`) is read from the catalogue by `ref`.
- **While `ref` is set**, a number the product fixes is not edited; the rail
  depth is edited within the product's range and step. Customising a product
  sets `ref` to `null` and keeps the numbers: it becomes a generic frame.
- **A product that changed.** Frame numbers are in the product's major bucket,
  so the same major always copies the same numbers. A ref the catalogue does not
  have, or whose numbers no longer match, is drawn from the file's own numbers
  with a note, and the page offers to apply the product again.

**What fits rack file version 3, and what does not.** `frame.ref` is an
existing key, so a product whose numbers today's frame can hold needs no format
change: AR203A (four-post, square, fixed 740) and AR201 (two-post, tapped
12-24) are such products. Seven keys do not fit version 3, and an older reader
mishandles each. Five it drops (frame keys through `normalizeFrame`, item keys
through `readItem`) and erases on its next save, which is the case #921 bumped
for. One it rewrites: `normalizeFrame` turns `holes.style: round` into
`square`, and saves that. The seventh, `channel`, it keeps, since `readZeroU` keeps a zero-U entry
whole, but it misreads it: it stands the part outside at its point, as the 1 to
2 bump was for a manager an older page would misdraw:

| key | where | why |
|---|---|---|
| `width` (10, 19, 21, 23) | frame | a 23 in rail; absent is 19 |
| `numbering.start`, as `startU` | frame | a frame not starting at 1; absent is 1 |
| `holes.style: round` | frame | today's reader turns it into `square` |
| `setback` | frame and item | section 8 |
| `heldBy` | item | section 7 |
| `channel` | zero-U entry | section 3; kept by an older reader, which then stands the part outside and overlaps it with a duct there |
| `options` | frame | the product options a rack takes (section 4) |

**They go in together, as rack file version 4,** published under
`/schemas/v3/` (the next unused label), with an identity migration from 3, so
every version-3 file is a valid version-4 file and an older page refuses a
version-4 file rather than erase or misread what it cannot read. One bump, not seven: each
key alone would need it, and a rack file version is a one-way door.

**Proposed for the same version** by
[cable-lay-design.md](cable-lay-design.md) section 7 (#949): the rack entry
`states` and `readings` of the PDU note (#934), the PDU bracket key of #939,
the cable keys `slack` and `lay` (each `lay` entry `{item, via, position?,
face?}`, with `position` and `face` each optional), and the item key `roll`
with `90`, `180` and `270` (section 10 reserves the name for #550; the cable
lay note adds `180`, a manager mounted upside down, and fixes the convention:
clockwise as seen in the elevation of the face, applied after `face` and
`turned`), so that none of them needs a version 5.
The version-4 step reserves `slack` and `lay` even before anything acts on
them, fits an item with `roll` by its rolled box, and its reader must not
misread `slack`: for a cable that carries it,
the stored routed length and stock size are kept as written and not
re-measured, and a route edit that takes off a tray the slack names is
refused.

## 10. Later: designed for, not built

- **Wall-mount.** `wall-frame` and `wall-cabinet` products (FS-WMNR-D2P6U,
  the hinged FS-HWM-4U) are frames with front rails only, which today's
  `two-post` kind already fits with a `usableDepth` of the box's depth. Their
  wall fixings (keyholes at 406.4 mm stud spacing) are `base`-like data for a
  room view. Nothing new is needed until a wall is drawn.
- **Vertical mounting (#550).** Two cases. A device turned 90 degrees in an
  ordinary rack (the 7360 ISAM FX-8 on its kit) is an item key, `roll: 90 |
  270`, whose U footprint is its width over 44.45 mm, plus a kit configuration
  for the baffles and the facts that differ (lug size, cable exit). A
  `wall-frame-vertical` product (FS-SVWM-1U and -4U) hangs every device face
  down; the frame states it and the elevation is drawn from above. `roll` is
  reserved by this note; the cable lay note proposes it for version 4 with a
  third value, `180`, for a manager mounted upside down (its section 7.1),
  and the quarter turns are built with #550.
- **The tilted desktop rack.** `desktop-frame` with `tilt: 9` (degrees back
  from vertical, FS-DR-8U's 81 degrees to its base). The 3D scene leans the
  rail plane; the 2D elevation is face on and unchanged.
- **Rows.** A document already holds an array of racks. A row is a later
  document key, `rows: [{id, racks: [ids], gaps: [mm]}]`, with baying checked
  against the products' `baying`, and `between: true` resolved to two racks.
  That key will be its own rack file version.
- **A room.** Rows placed in plan with aisles, and anchors and wall fixings
  drawn: after rows.

## 11. Build order

The order follows the agreed sequence: easy wins, then hosting, sliding,
cabinets, wall and vertical, and desktop.

1. **This note.**
2. **Easy wins, no format change.** As plain devices: the blanks (screw-on,
   tool-less steel, tool-less ABS), the fan panel FANP3U3F (a mains input and a
   switch), the cantilever shelves FS-CFS-1U, IWEP1U350 and IWEP1U550, the
   drawers FS-LRD-2U, -3U and -4U, the DIN rail brackets DINRAIL2U and
   DINRAIL4U, and FS-PDUBK with #939. Then `kind: rack`: the schema, the lock,
   lint, `rack.json` `frames`, the rack type export (decision 5), and the open frames
   AR203A and AR201, which fit rack file version 3 through `frame.ref`. The
   Rack Builder's frame picker follows in the site.
3. **Hosting.** `hosts:` on devices, `chassis.ears.holes`, and rack file
   version 4 with all of section 9's keys at once; setback (#908 and the
   paused site design) lands in the same version. Fit, describe, inspect and
   export learn hosted items. The shelves, drawers and DIN brackets of step 2
   take a minor each for their hosts.
4. **Sliding.** The sliding shelf FS-1USSH (a sliding kit, four-post, 650 to
   950 mm), the drawers' travel, and the site sliding a host out with what is on
   it.
5. **Cabinets.** NetShelter SX Gen2 first (manual, drawings and the richest
   CAD), then SV and SX Advanced, under their maker with FS listings (#936):
   enclosure, base, load, channels with `pdu-button` slots, and the PDU fit
   check (PDU note step 8, #939's FS-GR42U-PDUBK).
6. **Wall and vertical.** FS-WMNR-D2P6U, FS-HWM-4U, FS-SVWM-1U and -4U, and
   the quarter turns of `roll` with #550 (`roll` itself enters at version 4,
   section 9).
7. **Desktop.** FS-DR-8U and `tilt`.

Rows and the room come after, each with its own note.

### Decisions taken 2026-10-09

The five questions this note left open were each decided as it recommended:

1. **The kind.** A rack product is `kind: rack`, in `library/racks/` with its
   own schema (`rack-product.schema.json`) and its own lock, not a device with
   `mount: floor` (section 1).
2. **The maker's namespace for APC racks** is `apc`, since the products, part
   numbers and manuals all say APC. The open frames AR203A and AR201 and the
   NetShelter cabinets go under it, and FS lists them through #936.
3. **The setback order** is the item's own `setback`, then the device's
   default ear position, then the rack's default, then 0, flush (section 8).
4. **A hosted item keeps `ru`.** One that is not `mount: rack` has its host's
   bottom U, written by the kit and kept in step with the host, and `heldBy` is
   what decides; a `mount: rack` device on a shelf keeps its own U and claims
   its units (sections 7.2 and 7.3).
5. **The DCIM rack type export** is built with the open frames (step 2): NetBox
   rack types under `library/exports/`, writing `weight_unit: kg` beside
   `weight` and `max_weight` (the static load), and leaving the cooling fields
   empty, since no source gives them. Nautobot has no rack type, so its export
   is the fields of a rack it does have (`type`, `width`, `u_height`,
   `desc_units`, `outer_width`, `outer_depth`, `outer_unit`), and the facts it
   has no field for (starting unit, outer height, mounting depth, weight,
   static and rolling load) go in the rack's `comments`, one line each, as the
   device exports already carry facts neither DCIM has a field for. Custom
   fields are not used: they would need setting up on each instance first.

## 12. One-way items

Each is additive, and each becomes hard to change once a library product, a
published file or a saved rack file uses it.

| item | where | why it is one-way |
|---|---|---|
| `kind: rack`, `library/racks/<vendor>/<name>/rack.yaml`, `rack.lock.json` | manifests, devicelock | refs, listings and saved rack files name racks by this path and kind |
| `rack-product.schema.json` under `/schemas/v1/` | schemas | a published schema `$id` |
| a rack's name unique across racks and devices in its vendor | refs | a ref resolves without its kind |
| the rack ref form `<vendor>/<name>@<major>` in `frame.ref` | rack file | saved files carry it |
| `form` and its eight values, `desktop-frame` among them | rack products, `rack.json`, DCIM export | published, and mapped to NetBox and Nautobot slugs |
| `numbering` (`direction`, `start`), `width`, `hole-centres`, `opening`, `holes` (`style` with `round`, `size`, `fixing`), `rails` (`id` with `front` and `rear`, `at`, `depth` as `fixed` or `min`, `max`, `step`, `factory`), `max-device-depth`, `outer`, `posts` | rack products | the frame vocabulary every product writes |
| `points`, `channels` (`id`, `point`, `where`, `ru`, `slots`, `moves`) | rack products | the rack file names channels by id |
| `slots` (`interface`, `first`, `pitch`, `count`, `at`) on a product channel | rack products | the PDU fit check reads it |
| the rack-file key for a PDU hung on brackets | rack file | not defined here; it comes with #939 and is one-way when it does |
| `vcm-keyhole`, proposed | connectors registry | once given, ducts and uprights carry it |
| `enclosure`: `doors` (`face`, `leaves`, `kind` with `perforated`, `solid`, `glass`, `mesh`, `open-area`, `hinge`, `reversible`, `swing`, `clearance`, `lock`), `panels` (`per-side`, `split`, `removable`, `lock`), `roof` (`removable`), `entries` (`where`, `kind` with `brush`, `knockout`, `cutout`, `open`, `box`) | rack products | read by fit and the catalogue |
| `options` (`id`, and the numbers an option changes), and a depth range's `with` | rack products, rack file | a rack file names the options it takes |
| `base` (`casters`, `levellers`, `anchors`), `load` (`static-kg`, `rolling-kg`), `weight-kg`, `baying` (`centres`, `brackets`, `trim`) | rack products | read by checks and later rows |
| `hosts:` with `surface`, `cavity`, `rail`, its `box` frame of reference, `support`, `opens`, `rail` profiles (`ts35-7.5`, `ts35-15`), `set-back`, `load-kg` | device manifests | a saved rack names host ids; the frame of reference places items |
| `heldBy` (`item`, `at`, `x`, `z`, `turn`), its name chosen apart from the manager's host, and the rule that `on` and `heldBy` never share an item | rack file | saved rack files carry it |
| a held item's `ru`: its host's bottom U, written by the kit, unless it is `mount: rack`, when it keeps its own | rack file, kit | readers sort and label by it |
| a held item's DCIM rows: in the rack with no position and no face, and a comment line saying what holds it | DCIM export | an imported device keeps where it was put |
| `chassis.ears.holes` | device manifests | fit refuses on it |
| `data-class="host"` | drawings | consumers of the drawing read it |
| `frames` in `rack.json` | the rack catalogue | the Rack Builder reads it |
| rack file version 4 under `/schemas/v3/`, carrying frame `width`, `startU`, `holes.style: round`, `setback` and `options`, item `setback` and `heldBy`, zero-U `channel` | rack file | an older page refuses a version-4 file; a label is never reused |
| the setback order (item, device default ear position, frame, flush), and a default position with no `at` counting only when it is `flush` | kit fit and drawing | a saved rack's faceplates move if it changes |
| removing the 30 mm showcase default, so an unstated setback is flush | kit and Rack Builder | every saved rack's faceplates move 30 mm when it lands |
| NetBox rack types under `library/exports/`, and the Nautobot rack fields | DCIM export | an imported rack type is named by its model |
| `roll` (#550) and `tilt` | reserved names | later keys built on them; `roll` is proposed for version 4 (section 9, and section 7.1 of the cable lay note) |

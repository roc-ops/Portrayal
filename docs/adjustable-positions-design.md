# Adjustable positions: a part that slides, its range, and where it is set

Status: proposed 2026-10-10, nothing built. Issue #950. Each section gives a
recommendation and its reason; section 13 lists what is still open, and section
10 the one-way doors the build steps would open. This note is two-way.

Three things are decided already and are not reopened here:

- The position control lives in ONE place, the Explorer: a slider or named stops
  on the page of the device. The Rack Builder gets no control of its own. It
  opens the item in the Explorer.
- The chosen position is stored through the existing `fields` mechanism. There
  is no new rack file key.
- FS DINRAIL2U and DINRAIL4U are the first users, after #971 gives the rail
  panel its joint to the side brackets.

Builds on fields ([`library/components/README.md`](../library/components/README.md),
"Skins", and `kit/fields.js`), on
[switch-positions-design.md](switch-positions-design.md) (#808), on the hosts
and the setback of [rack-products-design.md](rack-products-design.md) (sections
7 and 8, #935), on the solid bodies of
[cable-lay-design.md](cable-lay-design.md) (section 1, #949), on the rack
mounting work (#904 to #909: ear positions and rail kits) and on
[format-stability.md](format-stability.md).

The goal: a device can say that a part slides, how far, and where it is drawn;
a reader can put it somewhere else in that travel; and the drawing, the 3D
view, the rack and its cables all follow.

## 1. What exists

### 1.1 The need

The FS DINRAIL2U and DINRAIL4U carry a DIN rail on a panel. The panel bolts
through two slots in each side bracket, and slides along them. As #971 models
them, the front face of the panel can stand 51.2 to 271.2 mm behind the ears on
the 2U, and 50.5 to 269.4 on the 4U. The issue quotes other figures (72 to 292,
66 to 291): they are slot ends from an earlier reading of the side view. The
device records the panel face, which is what a reader sets. The two differ by
20.8 on the 2U, and by 15.5 and 21.6 on the 4U. The maker photographs the part
at both ends of the travel.

Each device draws one position, the middle (161.2 and 159.9). The range is in
three `attrs.physical` keys (`din-rail-setback-mm`, `-min-mm`, `-max-mm`) and in
a `gaps` entry that asks for this key. One position is drawn in six views:

| view | what shows the panel | how |
|---|---|---|
| front | `rail-panel` (a well, `size.d` 161.2) and `rail`, which is `in: rail-panel` | the depth of the well |
| rear | `panel-back` and eight cut-outs | flat decor |
| top, bottom | `rail-panel`, `rail`, `tab-left`, `tab-right` | decor rects at a `y` |
| left, right | `flange`, `tab-top`, `tab-bottom`, and two screws `under:` the bracket | decor and placements at an `x` |

So one motion is 29 nodes in six frames. In the front and rear views it is
along depth, and nothing in the 2D face moves.

### 1.2 Fields, end to end

- **Declared** on a component contract, and nowhere else:
  `spec/schemas/component.schema.json`, `fields`. A field has `label`, `type`
  (`text`, `number` or `choice`), `default`, `options`, `pattern`, `unit`,
  `drawn-by-absence` and `description`. A `number` has no minimum and no
  maximum. The device schema has no `fields` key.
- **Wired** in the skin: `data-from` (text), `data-fill-from`,
  `data-stroke-from`, `data-stroke-derive`, `data-r-from`, and since #808
  `data-move-from` and `data-show-from`.
- **Set at build time** by the `attrs` of a placement, or by the `bay-attrs` and
  `component-attrs` of a configuration (`spec/schemas/device.schema.json`). A
  `component-attrs` key is a component name, or a placement or bay id; L94
  checks that it resolves.
- **Compiled** by `render.py` `fill_from_attrs`, which paints the nodes from the
  merged attrs of the instance. The value is also written on the group of the
  part as `data-<key>`.
- **Read by the kit** in `kit/fields.js`: `paintFields(el, vals)` applies the
  same rule at runtime, `unpaintFields` puts back what was drawn, `fieldRows`
  gives the rows of a form, and `fieldAccepts` says if a value is one the field
  takes. For a `number` it asks only for a finite number.
- **Read by the Explorer** in `kit/shell.js`: `setFields(path, vals)` finds every
  `[data-path]` group of that path, and its projections, on every face. The
  inspector builds a row for each field of the selected part (`fieldPart`), and
  only for a part whose component declares fields. `kit/index.html` keeps the
  map in `state.cfgFields`, writes it into the location as `fields=`
  (`encodeFields`: `path~key~value`), and hands it to the 3D viewer.
- **In 3D**, `kit/viewer3d.js` `setFields(map)` repaints the textures of the
  faces a changed part is on. A field that moves or shows a node rebuilds the
  whole scene; there is no rebuild of one part.
- **Stored in a rack item** as `fields`: `{path: {key: value}}`, the values
  strings (`spec/schemas/rack.schema.json`, `$defs/item`; `kit/rack/model.js`).
  The schema calls it "Editable text the Explorer set."
- **Set in a rack** by the `field` command of `kit/rack/commands.js`. It takes
  only the path of a seated part, `<bay>/module` or `<cage>-occupant`. The
  resolver of the rack (`kit/rack/slots.js` `resolverFor`) is given no
  `placementRef`, so the path of a fixed placement is refused: "Nothing is
  seated at".
- **Cleared** when an item takes a new configuration (`commands.js`, `CLEARED`).
- **Not drawn in the rack 3D scene**: `kit/rack/export-data.js` `threeDNotes`
  says so in a note.
- **Exported** nowhere as a field value: `dcim_export.py` writes none, and a
  rack export names the items that carry fields only in that 3D note. The range
  does reach the exports today by another road. Every device-type export lists
  the `attrs` of the device in its comments, so the DINRAIL files carry three
  fact lines, `physical.din-rail-setback-mm`, `-min-mm` and `-max-mm`. The same
  comments print the drawing version and one line for each configuration.

### 1.3 Switch positions (#808)

A switch position is a `choice` field on the component. The skin holds the
table of moves on the node that moves: `data-move="on: 0 -3.4"`, in mm, in the
frame of the skin. The build and the kit apply one rule. Lint keeps a moved
node inside its part. In 3D a position change rebuilds the scene.

It did a similar job, and it does not reach this one, for three reasons:

- A skin can move only its own nodes. This motion crosses six views, device
  decor, and parts of three components.
- A `choice` has options. A slot is a range.
- The travel belongs to the joint between two parts of one device. A component
  contract cannot know it.

### 1.4 `inset`, `only-in`, `under`, `in` and relief depth

- **`inset`** (a placement) is the mm this instance is mounted behind the panel
  face. `render.py` `_inset_feature` reduces every protrusion by it, and what is
  left wholly behind the panel is not drawn. It hides; it does not move.
- **`lift`** is its mirror: every protrusion is raised by it. A relief feature
  spans `lift` to `out`.
- **`only-in`** says in which configurations a part of the metal exists. One
  position would need one placement with its own id, and ids are addressing. A
  range cannot be written at all.
- **`under`** names the ids in this view that lie over this part. It sets paint
  order, it is published as `data-under`, and L13 does not compare the pair.
- **`in`** names the well a part stands in. The build sinks the part by the
  depth of the well: a negative `data-z-lift`, summed with any other. The well
  itself carries `data-depth`, taken from `size.d` of its component.

So the depth of the DINRAIL panel is `size.d: 161.2` on `fs/dinrail2u-panel@2`.
The default position of the device is a number in a component.

### 1.5 What the rack mounting work already says about depth

- **Ear positions** (`chassis.ears.positions`, #906): named places the ears can
  put the faceplate, with `at` in mm only when a source gives it. They move the
  WHOLE device against the rails.
- **Rail kits** (`kind: kit`): `motion` is `fixed`, `telescoping`, `sliding` or
  `shelf`. A configuration states the rack `depth` it fits, front flange to rear
  flange. A device can override one range (`chassis.kits[].depth`). The depth of
  a telescoping kit is set by the rack, at install.
- **Fit belongs to the reader of the rack**, decided 2026-10-08. The library
  computes nothing about racks.
- **`setback`** on a rack item (rack products note, section 8, proposed for rack
  file version 4): the mm the faceplate stands behind the rail plane.
- **A rail host** (same note, section 7.1, not built): `hosts:` gives a DIN rail
  a `box` and a `set-back: {min, max}`.

None of these moves one part INSIDE a device. This note adds that, and section
8.4 says how the two add up.

## 2. Decisions

1. **The motion is declared on the device**, in a new top-level `adjustments:`
   map. Each part that moves says `moves-with: <id>`.
2. **One adjustment is one axis, one range in mm, one default and optional
   named stops.** The value is a coordinate in the frame of the device.
3. **The value is a field.** It is held at the path of one placement, the
   `carrier`, under the id of the adjustment. It is a number in mm. A stop is a
   name for a number.
4. **The compiled drawing says what moves and by how much per mm**, on each
   node, in the frame of that node. The kit needs no source file and no rule
   about views.
5. **A 2D face that cannot show the motion shows nothing false.** The value is
   on the carrier, and the Explorer says which views show it.
6. **In a rack, the solids of the device move with the field.** The envelope
   does not. Routed lengths are measured again; entered lengths are not touched.
7. **Stating an adjustment on an existing device is a minor.** No coordinate
   and no id a reader holds moves.
8. **No DCIM schema field changes; the export comments do.** A rack export
   gains one note line for each item that is not at its default.

## 3. The declaration

```yaml
adjustments:
  rail-setback:
    label: Rail setback
    carrier: rail-panel            # the placement whose path holds the value
    axis: z                        # x | y | z, the frame of the device
    range: [51.2, 271.2]           # mm
    default: 161.2
    stops: {front: 51.2, middle: 161.2, rear: 271.2}
    datum: the front face of the rail panel, behind the ear plane
```

```yaml
views:
  front:
    components:
      placements:
      - {ref: fs/dinrail2u-panel@2, id: rail-panel, at: [31.4, 0.0], group: frame,
         rel-pos: 1, moves-with: rail-setback}
      - {ref: fs/din-rail-ts35-400@1, id: rail, at: [42.0, 26.25], group: rails,
         rel-pos: 1, in: rail-panel, moves-with: rail-setback}
  top:
    panel:
      decor:
      - {id: rail-panel, at: [1.5, 197.3], size: [421.2, 1.5], fill: '#1b1d20',
         kind: rail-panel, moves-with: rail-setback}
```

- **`adjustments`** is a map. The key is the id: the field key, and the name a
  member uses. It is unique in the device.
- **`axis`** is `x`, `y` or `z` in the frame the hosts and the solids already
  use (`rack_solids.py`): x from the left of the device seen from its front, y
  up from its bottom, z back from its front. The motion is a straight slide. A
  turn, and a part that changes length, are not in scope.
- **`range`** is `[min, max]` in mm, the coordinate of the datum along the axis.
  It is absolute, not an offset, so it is the number a maker prints and the
  number a host box uses.
- **`default`** is the position the views draw.
- **`stops`** is optional: a name for a position. A device can state stops and
  no `range`. Then only the stops are positions: a row of tapped holes, not a
  slot.
- **`datum`** says in words which point of the part the number measures. It is
  required. One joint has several points a number could mean. On the 2U the
  screw centre is 18.2 behind the panel face, the slot end is further back
  again, and the rail face is 7.5 in front. A range with no datum is a range
  of one of them, and the reader cannot tell which.
- **`carrier`** is the id of one placement that moves with this adjustment. Its
  path is where the value is held (section 4).
- **`moves-with`** is a key of a placement, a bay and a decor entry. Everything
  that names one adjustment moves together, by the same distance. That set is
  named by the id of the adjustment, and by nothing else.
- **Provenance**: the device states `provenance.<id>` with a confidence and a
  note that gives the source of each end of the range and of the default. The
  DINRAIL `provenance.setback` entry is that note already.

### Alternatives considered

| where | why not |
|---|---|
| a field on the component, with `data-move` in its skin (#808) | a skin moves its own nodes; this motion is in six views and three components (1.3) |
| one placement declares it | no placement owns it: decor cannot declare, and each view has its own members |
| a `groups:` entry | a group is a naming set (term, role, index). Decor has no group, and `frame` holds the panel that moves and the brackets that do not |
| a bay | a bay is an opening with an occupant. A bay can be a MEMBER, and its occupant then moves with it |
| a list of member ids inside the adjustment | a placement states its own relations on itself (`group`, `in`, `under`, `only-in`), the lock hashes them there, and a reader of one view sees what moves |
| `only-in`, one placement per position | one id per position, and no range (1.4) |
| `inset` | it hides what is behind the face (1.4) |

### Names

`on` is not used for the carrier: YAML reads a bare `on:` as a boolean, the
mistake the fix text of L106 warns of. `travel` and `motion` are kit keys with another
meaning (1.5). `setback` alone is the rack item key of the rack products note,
so the DINRAIL adjustment is `rail-setback`.

## 4. How a field value selects a position

**One field for each adjustment. Its value is a number in mm. A stop is a name
for a number, and a setter turns the name into the number before it is kept.**

- **The path** is the path of the carrier, `rail-panel`. **The key** is the id,
  `rail-setback`. So a configuration says
  `component-attrs: {rail-panel: {rail-setback: rear}}`, the Explorer calls
  `setFields('rail-panel', {'rail-setback': '271.2'})`, a link carries
  `fields=rail-panel~rail-setback~271.2`, and a rack item holds
  `"fields": {"rail-panel": {"rail-setback": "271.2"}}`. Every one of these is
  the spelling that exists today.
- **With a `range`**, any number from min to max is a position, both ends
  included. **With stops and no range**, only the stop values are.
- **A value is kept as a string**, as every field value is (`commands.js`
  writes `String(value)`; the marks file takes a string or null). It has one
  spelling: the number rounded to 0.1 mm, in decimal, with no exponent, no
  sign, and no trailing `.0`. So `120` and `271.2`, never `120.0` or `271.20`.
  `encodeFields` promises that one state is one string, and two spellings of
  one position would break that. `adjustmentAccepts` answers with this
  spelling, and every setter keeps what it answers.
- **0.1 mm** is enough: no source here is better than that.
- **A stop name is input, not storage.** A rack that says `271.2` still says it
  after the library renames `rear`. A rack that said `rear` would move when the
  number behind the name changed, with no word to its owner.
- **Refused, with a sentence.** A value that is not a position is not applied:
  the drawing stays as built, as the Explorer already does for a field value it
  does not accept. The sentences:
  - "rail-setback on DINRAIL2U takes 51.2 to 271.2 mm. 300 is outside it."
  - "ear-row on X takes one of: front (20), middle (60), rear (100)."
  - "rail-setback on DINRAIL2U takes a number in mm, or one of: front, middle,
    rear."
- **In a build**, the same test fails the build for a value a configuration
  sets (section 9).
- **In a saved rack**, a value the library no longer accepts is kept as written
  and never repaired. The item is drawn at its default, and fit says the first
  sentence above.

### Alternatives considered

- **A `choice` field with only stops** is what #808 has. It cannot say 120 mm,
  and the maker photographs positions that are not the ends.
- **A number only** leaves the reader to type 271.2 for "at the rear", and gives
  a row of holes no way to refuse the space between them.
- **A reserved path for the device** (not a placement) would keep the carrier
  out of the declaration. Every reader of `fields` keys a part path:
  `component-attrs`, `setFields`, `fields=`, the marks file and `item.fields`.
  Each would need a special case.
- **`min` and `max` on every component `number` field** would let `fieldAccepts`
  do the test with no new function. It is a larger change, to every contract
  reader, for one user. It is left as a question (section 13).

## 5. What the compiled drawing carries

The kit moves the part from the drawing alone.

- **On the root of every face of a device that states any**,
  `data-adjustments`: the map as JSON, keys
  sorted, the way `render.py` writes `data-positions` on a placement. For each
  id: `axis`, `carrier`, `range`, `default`, `stops`, `label`, `datum`, and
  `at`, the position this file was built at.
- **On every member node** (the group of a placement or a bay, a decor rect):
  `data-moves-with="<id>"` and `data-moves-by="dx dy dz"`. The three numbers are
  the mm the node moves for each mm of position: `dx` and `dy` in the 2D frame
  of the node, `dz` the change in its depth behind this face. The build works
  them out from the axis and the view, once, so no reader holds a rule about
  which way a plan faces.

  | view | `data-moves-by` for `axis: z` on DINRAIL2U |
  |---|---|
  | front | `0 0 1` |
  | rear | `0 0 -1` |
  | top, bottom | `0 -1 0` (the rear is at y = 0) |
  | right | `1 0 0` (the front is at the left) |
  | left | `-1 0 0` |

- **On the carrier**, `data-<id>` with the built value, only when a
  configuration set one. That is what `fill_from_attrs` writes for every field.
  A host does not read the position from it: `at` in `data-adjustments` is the
  built position on every face, set or not.
- **A configuration that sets a position is built moved.** Its members are drawn
  where that value puts them, and `at` in `data-adjustments` says the value. The
  kit moves a node by `(value - at)` times its `data-moves-by`.
- **The elements file**: the box of a member is its box as built, as #808 does
  for a moved node. A member entry also needs `moves-with` and `moves-by`, so a
  reader that holds only that file can move a hit box. The build step decides
  the spelling inside the rules of that file.
- **`<device>.configs.json`** of a device that states any carries
  `adjustments` at the top, and each configuration lists the positions it
  sets. A device with no adjustment gains no attribute and no key, so its
  build stays byte for byte the same. A host builds its control from
  this file, without opening a face.

### A face that cannot show it

From the front, a panel 51 mm back and a panel 271 mm back are the same
elevation. **The face is drawn the same, and nothing is added to it.**

- The root still carries `data-adjustments`, so a host reads the built
  position (`at`) off any face, this one included.
- A face shows the motion when a member on it has a `dx` or a `dy` that is not
  0. The Explorer reads that, and beside the control it names the views that
  show the motion (section 7).
- Considered and refused: a darker well for a deeper panel (a colour claim
  nothing measures), a smaller panel (a face is an elevation, not a
  perspective), and a dimension printed on the face (a face carries what is on
  the hardware; a note belongs to the host).

## 6. 3D

The relief of a node is built from its box and its depth keys. A move changes
both.

- **`dx` and `dy`** move the node, and its relief follows its box, as a #808
  move does.
- **`dz`** changes the depth at which the member is built behind its face. For
  a well that is `data-depth`. For any other member it is `data-z-lift`, with
  the sign reversed. On DINRAIL2U the front well goes from 161.2 to the value,
  and the rail, which stands on that floor, goes with it because it is a member
  too. Lint asks for that (section 9), so the kit never works out who follows
  whom.
- **The scene is rebuilt**, the way `viewer3d.js` rebuilds it for a position
  field. There is no rebuild of one part. `setFields` already keeps only the
  latest call that waits, so a dragged slider costs one rebuild at a time.
- **The build writes each member at its built position**, so a scene built from
  a configuration that sets a position is right with no field set.

## 7. The Explorer

- **One control for each adjustment, on the page of the device**, not in the
  row of a selected part. It is there whatever is selected.
- **A slider** from min to max when there is a `range`, with a number box in mm.
  **One button for each stop**, in the order of their values. With stops and no
  range, the buttons are the whole control.
- **A reset** puts the built value back, as a field row has today.
- **It writes through `setFields(carrier, {id: value})`.** So the location, a
  shared link, the marks file and the 3D viewer take it with no new path.
- **The slider applies on release.** While it is dragged, the 2D faces can
  follow; 3D rebuilds when it stops.
- **Beside it, a line names the views that show the motion** when the view on
  screen does not: "The front view does not show this. See the top or the side
  view, or 3D."
- New in `kit/fields.js`: `adjustmentRows(adjustments, current)` for the
  control, and `adjustmentAccepts(adjustment, value)`, which answers with the
  number to keep or with the sentence of section 4.

## 8. The rack

### 8.1 How the position comes back

The Rack Builder opens the item in the Explorer with the `fields` of the item,
and takes back the map the Explorer holds. The rack schema already describes
`swaps` and `fields` as what the Explorer set, and a position is one more entry
of that map. The item keeps it under the carrier path. The Rack Builder is in
the site repository; this note states what it must do, not how it does it
today. No key is added and the file stays at its version. The description of
`fields` in `rack.schema.json` ("Editable text the Explorer set.") is reworded;
that changes no file.

The kit rack core learns three things:

- **The `field` command takes an adjustment.** Today it refuses the path of a
  fixed placement (1.2). It accepts `{path: <carrier>, key: <id>}`, tests the
  value with `adjustmentAccepts`, and keeps the string it answers. An agent can
  set a
  position without a browser; a person still has one control.
- **`inspect` lists each adjustment** among the fields of the item, with its
  range, its stops and its value.
- **A new configuration clears it today**, as it clears every field of the
  item. Question 9 recommends that a position be kept.

### 8.2 The catalogue

`rack.json` carries, for a device that has any, `adjustments`: for each id the
`axis`, `range`, `stops`, `default` and `carrier`, the positions its
configurations set, and `parts`: which entries of its `solids`, `guides`,
`passes` and `trays` are members. A solid already names its part by path
(`rack_solids.py`), so membership is a list of names.

The position of an item is its field; else what its configuration sets; else
the default.

### 8.3 Fit and routing

- **The envelope does not change.** Lint keeps every member inside the device at
  both ends of the travel (section 9). So `w`, `h` and `d`, the units an item
  claims, and the depth check of `kit/rack/fit.js` against the other face all
  stay as they are.
- **The solids move.** `kit/rack/solids.js` shifts each member box along the
  axis by the position less the default. A route is checked against the metal
  where it is: a rail set back can clear a leg it blocked, or block one it
  cleared. The finding, and the way round, are the ones of the cable lay note
  (sections 1.3 and 1.4).
- **Rings, pass-throughs and trays on a member move with it**, so a route that
  names one still names it and now reaches it where it stands.
- **A route is kept.** Waypoints are ids, and no id changes. A route edited by
  hand (`routeEdited`) is left as it is, and gets a finding if a leg now
  crosses metal.
- **Routed lengths are measured again.** A length with `source: routed` is
  measured the next time a page measures it (`route.js`), as after any move in
  the rack. If the stock length steps up or down, that is said once.
- **Entered lengths are never touched.** The spare length of such a cable
  changes, and the finding for a cable too short can appear or go.
- **The rack 3D scene must take fields.** It has no fields input today (1.2).
  Until it has, an item not at its default gets a note, as optic colours do.

### 8.4 With the rack mounting keys

Three numbers place a DIN rail in a rack, and each is said once:

| number | where | what moves |
|---|---|---|
| the ear position, or the item `setback` | `chassis.ears`, rack file version 4 | the whole device against the rails |
| the kit depth range | `kind: kit`, `chassis.kits[].depth` | nothing: it says which racks fit |
| the adjustment | `adjustments`, `item.fields` | one set of parts inside the device |

The datum stands behind the rail plane of the rack by the item setback plus
the adjustment. On DINRAIL that datum is the panel face; the face of the DIN
rail is 7.5 in front of it. Neither key restates the other.

A rail `hosts:` entry (rack products note, 7.1) is drawn with `set-back: {min,
max}`. That would be a second statement of this range. When hosts are built,
the host says `moves-with` and its `box` is the box at the default (section
13, question 2). An item held on the rail then moves with it. `heldBy` has no z
on a rail, so nothing saved changes.

## 9. Lint, lock and exports

### Lint

Codes are given when the rules are built. Each rule and its reason:

1. **An adjustment is well formed.** `min < max`; the default is in the range;
   each stop is in the range; with no range there are two stops or more and the
   default is one of them; no two stops share a value. *A default outside its
   own range draws a position the part cannot take.*
2. **The carrier is a member placement with a `ref`, and it is not `only-in`.**
   It exists in every configuration; any other member may be scoped. *The
   value is held at
   its path, and a path with no part is one no reader can find.* So a motion
   made only of decor cannot be declared. That is accepted: decor that slides
   is a part, and is modelled as one.
3. **Membership resolves.** Each `moves-with` names an adjustment of this
   device; each adjustment has a member; a node names one adjustment at most.
   *A typo would leave a part behind with no error.*
4. **What stands on a member moves with it.** A part `in:` a member well, a part
   mated to a member, and the `plan` or `rear` projection of a member bay are
   members of the same adjustment. *The kit moves what the drawing marks. A rail
   left on a floor that went back would hang in the air.*
5. **The default is the position drawn**, where lint can tell: for `axis: z`
   with a carrier that is a well on the front view, the depth of the well is the
   default. *Otherwise the control starts at a number the drawing does not
   show.*
6. **A member stays inside the device at both ends.** Moved to min and to max,
   its box lies inside its view, and its depth inside `chassis.depth`. *Fit
   judges a device by its envelope, and a part must not be set outside it.*
7. **No new collision at either end, or at a stop.** L13 is asked again with
   the members moved: a member does not land on a part that is not a member,
   and a pair one of which is `under` the other still overlaps. *A panel pushed
   through a bracket is a wrong drawing that the default hides.*
8. **The id is free on the carrier group.** It is not a field of the carrier
   component, and it is not a name the build writes there as `data-<name>`:
   `depth`, `path`, `ref`, `in`, `under`, `group` and the rest of that list,
   which the rule reads from the build and does not copy. *The value is
   written as `data-<id>` on that group. An adjustment called `depth` would
   overwrite `data-depth`, and the well would be built at the wrong floor.*
9. **A position a configuration sets is one the adjustment takes**: a number in
   the range, or a stop name. *The build would draw a position the hardware
   does not have.*
10. **`provenance.<id>` exists.** *A range with no source is a guess that reads
    as a fact.*

The rule #971 adds as a test (the panel meets both brackets) holds at every
position without change: a moved panel keeps its width.

### Devicelock

`adjustments` is a new top-level key and `moves-with` a new key of a placement,
a bay and a decor entry. The lock as it is would record them badly, in three
ways, and step 1 must mend each:

- `test_lock_sees_placement_keys.py` guards the keys of a placement and a bay
  only. It fails until `moves-with` is sorted there, which is the guard doing
  its work.
- Decor is hashed whole inside the bucket a patch answers for. A `moves-with`
  on a decor entry would read as a patch. Step 1 takes decor membership out of
  that hash.
- No guard covers a new top-level key, so `adjustments` would be hashed
  nowhere. Step 1 adds it, with a test that fails when it is not recorded.

So the lock records, for each adjustment, its declaration and the set of its
members (view and id, of placements, bays and decor alike), the way it records
placement addressing today. The table below is asked of that record.

| change | bump | why |
|---|---|---|
| an adjustment is stated, with its members, at the position already drawn | minor | additive: no coordinate and no id a reader holds moves, as stating a `for`. The export comments do change (Exports, below) |
| a wider range, or a stop added | minor | every value kept before is still a position |
| a member added to an adjustment that exists | minor | the ruling for a `for` stated where there was none: nothing drawn at the default moves, and a forgotten member is a fault to mend, not a new shape |
| an id renamed or removed; the carrier, the axis or the default changed; a range made narrower; a stop removed, renamed, or its value changed; a member dropped or moved to another adjustment | major | a saved rack or a link holds a value this would move or refuse, or a caller holds a name this would refuse |
| `label`, `datum`, provenance | patch | surface |

A stop name is addressing, though a rack never keeps one. It is published in
`data-adjustments`, `configs.json` and `rack.json`, and `setFields` and the
`field` command take it as input. A caller that says `rear` must not be
refused after a patch.

So DINRAIL2U and DINRAIL4U take a minor each. The lock is checked against the
main branch before any version is written, as for every device change.

### Exports

- **DCIM device types: no schema field, and no new kind of line.** Neither
  NetBox nor Nautobot has a field for a position. Steps 1 to 4 change no file
  under `library/exports/`. Step 5 does change the comments of the DINRAIL2U
  and DINRAIL4U files, in up to three ways:
  - the drawing version line, always, because each device takes a minor;
  - the three `physical.din-rail-setback` fact lines, if those attrs are
    removed (question 5);
  - one more configuration line, if a configuration is added that sets a
    position (question 6).

  A changed export file is a one-way door (section 10).
- **The rack exports of the kit** (`kit/rack/export-data.js`): one note line for
  each item that is not at its default, in the notes a CSV and a drawn export
  already carry: "DINRAIL2U (i4) at U12: rail setback 271.2 mm (rear)." The stop
  name is given when the value is a stop.
- **The DCIM import rows of a rack** do not change.
- `describe` and `inspect` say the same sentence.

## 10. One-way doors

The note opens none. The build steps would open these:

| door | opened by | blast radius |
|---|---|---|
| the keys `adjustments` (with `carrier`, `axis`, `range`, `default`, `stops`, `datum`, `label`) and `moves-with` | the device schema | optional keys, so `format` stays 1. Every device that states them holds them. A rename or a removal later raises `format` |
| what a value means: mm, the frame, the datum, the sign of each axis | the schema description and the build | every saved rack and every shared link that holds a value. A change moves parts with no edit to those files |
| `data-adjustments`, `data-moves-with`, `data-moves-by`; `adjustments` in `configs.json` and `rack.json`; the two keys of a member in the elements file | the build | new fields, so `contract` is not raised. From that release they are under it: the kit, the site and any other reader of the build |
| kit API: `adjustmentRows`, `adjustmentAccepts`; `setFields` moving parts for an adjustment key; the `field` command and `inspect` rows of the rack core | the kit, published on npm | a kit minor. Hosts that call them |
| saved racks: `item.fields[<carrier>][<id>]`, a number in mm kept as a string in its one spelling (section 4) | the Rack Builder | every rack saved after it lands. Renaming an id or a carrier in the library is a major for that reason |
| routed lengths that follow the position | the rack core | only racks that set a position, so none when it lands. Later, a change to how solids shift moves the lengths, and can move a stock size, in every such rack |
| the note line in rack exports | the rack core | text a person reads; a script that parses notes sees one more line |
| a minor on DINRAIL2U and DINRAIL4U | the first use | two devices and their locks |
| the DCIM export comments of DINRAIL2U and DINRAIL4U: the version line, and the three setback fact lines if the attrs go | the first use | four files under `library/exports/` (NetBox and Nautobot). A DCIM that imported the type holds the old comment text; no schema field moves |

Not opened: the rack file version, any DCIM schema field and the `format`
number.

## 11. Build plan

Each step is one change with its gate. Steps 2 to 4 are proved on a fixture
device in the tests, so no library device changes before step 5.

1. **Schema, lint and lock.** The keys, their descriptions, the rules of
   section 9, the lock buckets. Nothing is drawn differently.
   *Gate:* the schema description test, the lint rule reason test, the lock key
   test; a fixture for each rule that fails as written; the lock asks no bump
   of any device.
2. **The build.** `render.py` writes the root map and the two node attributes,
   and draws a configuration that sets a position moved. `configs.json` carries
   the map.
   *Gate:* a fixture built at its default and at each end, with the box of each
   member checked; the build of every library device is byte for byte the same.
3. **Kit, 2D.** `adjustmentRows` and `adjustmentAccepts`; `setFields` moves the
   members on every face; `fields=` goes there and back; the elements follow.
   *Gate:* JS tests for accept, refuse (each sentence), move and reset; a
   composited screenshot of a plan view at both ends.
4. **Kit, 3D.** The rebuild reads the position; `dz` on a well and on what
   stands in it.
   *Gate:* vertex positions of the built scene at the default and at both ends;
   the repaint path and the rebuild path both tested.
5. **The Explorer control**, then **DINRAIL2U and DINRAIL4U**, once #971 is on
   the main branch: the adjustment, `moves-with` on the members, a minor each,
   the `gaps` entry removed. The four DCIM export files of the two devices
   change in their comments (section 9), so the change says so as a one-way
   door.
   *Gate:* `./build.sh --device` for each; the panel test of #971 at both ends;
   a review page that sets each end beside the maker photograph of that end;
   the lock check before the bump.
6. **The rack core.** `rack.json` carries the adjustments and the member parts;
   solids, rings and trays shift; `field`, `inspect`, `describe` and the export
   note; the rack 3D scene takes fields.
   *Gate:* JS tests: a route that a set-back rail clears and one it blocks; a
   routed length measured again and an entered one left; a saved rack with no
   position loads and saves byte for byte the same.
7. **The site**, in its own repository: the Rack Builder hands the fields to the
   Explorer and takes them back, and draws the item moved. It gets no control.
   *Gate:* its own browser check, on a DINRAIL2U set to each end.
8. **Hosts**, when step 3 of the rack products note lands: a rail host that is
   a member, and the items it holds moving with it.

## 12. Other parts that would use it

| part | does it fit | what it needs |
|---|---|---|
| FS DINRAIL2U, DINRAIL4U | yes, the first use | #971 on the main branch; step 5 |
| a DIN rail host on those brackets (#935) | yes | the host as a member, in place of its `set-back` (question 2) |
| a shelf or a bracket with a rear support bolted through a slot at a position a person picks | yes | nothing new: `axis: z`, a range, members |
| a part on a row of tapped holes | yes | stops and no range |
| FS-1USSH, the sliding shelf with telescopic rails, 650 to 950 mm | no, not as a field | its rails reach from the front posts to the rear posts, so the RACK sets their length. The rack products note already models it so (sections 7.1 and 11, step 4): the shelf lists a sliding kit, four-post, 650 to 950 mm, and fit refuses a rack outside that range. It needs nothing from this note. Its slide for service is the travel of that kit, a motion nobody stores |
| the faceplate setback of #908, and ear positions | no | it moves the whole device, it is already `chassis.ears.positions` and the item `setback` of rack file version 4, and a position can have a name and no number. It needs nothing from this note. The stop buttons of the Explorer can show ear positions too, as one widget for two kinds of data |
| a drawer or a sliding kit pulled out | no | a service state, not a kept position. It could share `data-moves-with` and `data-moves-by` in the drawing when it is built (question 4) |
| the rails of a rack frame, adjustable in steps | later | `adjustments` on `kind: rack`, and a `step` key; both wait for that kind |

## 13. Open questions

1. **Is the kept value a number, or may it be a stop name?** Recommended: a
   number in mm always (section 4). A name is input only.
2. **Does a rail host restate the range?** Recommended: no. When `hosts` is
   built, a rail host says `moves-with` and drops `set-back`; section 7.1 of the
   rack products note is amended in that change.
3. **If a device turns up whose telescopic rails are part of it and not a kit,
   how does it state its depth range?** None is known: the rack products note
   models FS-1USSH with a kit. Recommended, should one appear: a depth range in
   the kit vocabulary, and not an adjustment, because the rack sets it.
4. **Does a service motion (a drawer, a sliding kit) share the drawing
   attributes?** Recommended: yes for the two node attributes, when it is
   built; no field and nothing stored.
5. **Do the three `din-rail-setback` attrs stay on DINRAIL?** They restate the
   adjustment, and they are how the range reaches the DCIM export comments
   today. The lock is not what decides: it files attrs as surface, a patch. The
   export is: removing them removes three fact lines from each export file, and
   nothing else would say the range there. Recommended: keep them, so the
   export keeps the range, and add a lint rule that they equal the adjustment.
   Remove them only if the export learns to write the range from the
   adjustment in the same change.
6. **May a configuration set a position?** Recommended: yes. It is how a device
   ships "rail forward" as a named configuration, and the build must draw a
   moved position anyway.
7. **Should every component `number` field gain `min` and `max`?** Recommended:
   not in this work. If a second user appears, `adjustmentAccepts` folds into
   `fieldAccepts` then.
8. **Does the rack export carry the note line?** Recommended: yes, one line for
   each item not at its default; the DCIM rows stay as they are.
9. **Does a chosen position survive a change of configuration?** Today it does
   not: a new configuration clears every field of the item. A position is a
   physical setting of the bracket in the rack, not a property of what is
   fitted. Recommended: keep it, always. An adjustment is stated on the device,
   so every configuration has it with the same range, and lint rule 2 keeps
   the carrier in every configuration, so the path always names a part. The
   kept value wins over a position the new configuration sets, as a field
   wins over a built value today. Every other field is cleared as today. This
   changes the rule of the rack
   core for one kind of key, so it is a part of step 6 with a test of its own.

## 14. Points to weigh before building

1. **Step 5 changes DCIM export files.** The version line of four files
   moves, and more if the setback attrs go (section 9, question 5). A changed
   export is a one-way door, and it is in section 10.
2. **The value sits in `fields`, and it is not a component field.** Every
   reader that tests a value against a component declaration needs a second
   source, the adjustments of the device:
   - `applyFields` in `kit/shell.js`, which takes a `fields=` entry only where
     the component declares the key;
   - the `field` command of the rack core;
   - `inspect` in `kit/rack/queries.js`, which lists the fields of seated
     parts only;
   - the 3D rebuild in `kit/viewer3d.js`.

   A kit from before this work, or a copy a host has vendored, does not fail.
   It drops the entry and draws the default, with no word on the page (the
   Explorer logs a console warning for an entry it ignores). A rack that looks
   right in one reader and wrong in another is the cost of reusing `fields`.
3. **The default is stated twice.** The depth of the well is `size.d` on the
   component, and the default is on the adjustment. Only lint rule 5 holds
   them together, and only for the case it can see. A second device that
   reuses the panel at another default cannot: the component would need its
   depth from the device.

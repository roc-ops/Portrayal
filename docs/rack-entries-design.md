# Rack cable entries and exits: where a cable leaves a rack, and what a caller passes in

Status: proposed 2026-11-07. Issue #1299, part of the rack products work (#935).
The mechanism is **not** decided. This note lays out three decisions the issue
names, proposes each, and marks every one-way item. It is decided before any
code, because adding the `entries` key republishes `rack-product.schema.json`.

This note changes nothing in `spec/schemas`, `spec/tools`, `kit/` or `library/`.
It builds on [rack-products-design.md](rack-products-design.md) section 4 (the
`entries` example and the bullet "Cable entries") and section 12 (the one-way
table), and on [site-file-design.md](site-file-design.md) section 8.3, which
reserves the key `exit` on a rack end and leaves `entries` undefined.

## Goal

A cable that leaves a rack, to a wall outlet or to the next rack, has nowhere to
end inside the rack file, and a product cannot say where a cable may leave it.
Counted on `main`:

- `spec/schemas/rack-product.schema.json` has `additionalProperties: false` at
  its top level, and the word `enclosure` is in no rack schema. So section 4's
  `enclosure.entries` is designed and **not built**, as are the doors, panels
  and roof beside it.
- The library holds 11 rack products. None states an entry. By `form`: four are
  `2-post-frame` (`apc/ar201`, `chatsworth/13853-x03`, `chatsworth/55053-x03`,
  `generic/2-post-frame`), six are `4-post-frame` (`apc/ar203a`,
  `fs/fs-or4p-45u`, `fs/fs-or4p-xxu`, `startech/4postrack12a`,
  `startech/4postrack42`, `generic/4-post-frame`), and one is
  `4-post-cabinet` (`generic/4-post-cabinet`).
- The rack file's `$defs.end` is `{item, path, view}` with an optional `plug`,
  and `$defs.cable` requires `id`, `a`, `b`, `media`, `purpose`, `label` and
  `route`. Both ends are devices in the rack.
- `portFree` (`kit/rack/cable-rules.js`) reads a port as taken when a cable of
  `rack.cables` has it. `freePorts` (`kit/rack/queries.js`) asks it. A cable
  stored in a space, a building or the site is not in `rack.cables`, so a rack
  opened on its own shows that port free.
- The ring and duct fill (`capacityOver` in `kit/rack/route.js`) counts the
  cables whose route passes the part, by the diameter of the cable's media
  (`DIAMETERS`, and the `od_mm` of `spec/schemas/cable-types.yaml`). A cable
  that is not in the rack file is not counted.

The issue's "Done when" is four lines. The last section of this note says which
decision makes each decidable.

## What is on `main`

- **Section 4 names the key and its four kinds.** `enclosure.entries` is a list
  of `{where, kind, box}`. `where` is the roof, the floor or a side; `kind` is
  `brush`, `knockout`, `cutout` or `open`; `box` is "in the product's own frame
  of reference". "Nothing routes through them in the first build, and a later
  route can end at one."
- **Section 12 lists the key as one-way**: `enclosure`: `doors`, `panels`,
  `roof`, `entries` (`where`, `kind` with `brush`, `knockout`, `cutout`,
  `open`, `box`), "read by fit and the catalogue".
- **Section 10 designs for wall frames** (`wall-frame`, `wall-cabinet`), which
  have front rails only, and says nothing is needed until a wall is drawn.
- **The site file reserves `exit` on a rack end** (section 8.3) and says a cable
  that ends at a rack's exit with no port "is not a version-0 end". Its section
  15 gives the entries and that end to #1299.
- **The site file's rack end has no closed key list.** Its schema's `rackEnd`
  requires `rack`, `item`, `path` and `view` and does not forbid other keys;
  `end` is a `oneOf` of the rack end, the device end and the point end. A key
  added to the rack end therefore passes a version-0 reader, and a fourth whole
  form does not.
- **The frame of reference for a hosted box** is the device's own: `x` from its
  left, `y` up from its bottom, `z` back from its front (section 7.1).
- **The open frames have no roof.** `apc/ar201` is two upright rails joined by a
  top angle and a bottom angle at each end (its provenance note for `form`);
  `apc/ar203a` is a four-post frame. No held source for either describes a
  cable opening, because there is nothing to open.
- **Cabinets are not in the library.** The FS cabinet folder holds the NetShelter
  SV, SX and SX Advanced user manuals and datasheets. The intake coverage notes
  say the SX roof has "cable access holes", the SV has roof and base access
  panels, and the GR roof has six brush-covered openings. Their sizes have not
  been read for this note (the gaps are in "What a manual must give").

## 1. The `entries` key, in section 4's terms

```yaml
enclosure:
  entries:
    - {id: top-brush, where: roof, kind: brush, box: {x: 100, z: 120, w: 200, d: 80}}
    - {id: floor, where: floor, kind: open}
```

The figures are illustrative; they are not any product's.

**Where it sits: `enclosure.entries`.** Section 4 and section 12 both put it
there, and doors, panels and a roof arrive later as siblings. Until they are
built, `enclosure` holds `entries` alone and the schema says so (additional
keys of `enclosure` are refused, as at the top level). A top-level `entries`
would save a level now and cost a second home for the key the day doors are
built. Either spelling is one-way once a product uses it.

**What an entry holds.**

| key | meaning | rule |
|---|---|---|
| `id` | the name a route ends at | required; unique within the product; lowercase letters, digits and hyphens; `any` is reserved (section 3) |
| `where` | which part of the enclosure | `roof`, `floor`, `left` or `right`; sides are as seen from the front |
| `kind` | what it is | `brush`, `knockout`, `cutout` or `open`; any other word is refused |
| `box` | where in that part | optional; see below |
| `source` | what states it | a free-text note, as a provenance `note` is |

**An `id` is new to section 4**, whose example has none. A route has to end at
a named place: a roof with two brushes is two exits, and a caller that says
"the left brush" needs a word for it. The id is chosen by whoever writes the
product (`top`, `rear-brush`) and means nothing to a reader but this product.

**Front and rear are not values of `where`.** A door is `enclosure.doors`, with
its own `face`. A cable that passes a door is not an entry. A side panel that
is itself open is a `left` or `right` entry of kind `open`.

**The `box` frame.** The product's own frame is the device's (section 7.1): `x`
from the left of the outer envelope, `y` up from its bottom, `z` back from its
front, in mm, within `outer`. Section 4's example `{x, z, w, d}` is a plan box,
which is right for a roof or a floor, where `y` is the part. A side entry is
the same idea turned: `{y, z, h, d}`, with `h` along `y` and `d` along `z`, on
the plane `x = 0` (`left`) or `x = outer.w` (`right`). The keys are the ones
section 7.1 uses (`w` along `x`, `h` along `y`, `d` along `z`), so no new name
is made.

**What `box` absent means depends on `kind`.**

- `open`: the whole part of `outer`. For a roof, the plan of the envelope.
- `brush`, `knockout`, `cutout`: **not stated**. The entry exists, a route can
  end at it, and its size is a gap the product lists in `gaps` with the
  document wanted. Nothing is estimated.

A brush, a knockout and a cutout differ in what they cost a cable. A `brush`
and a `cutout` are open to a cable. A `knockout` is closed until it is punched,
so a route ends at a knockout only when it is named (section 3). The note does
not say how big a cable's lead may be through any of them: no source held states
an allowance, and the kit would not guess one.

**What the schema, the lint and the catalogue do when it is built** (a later
order, section "The first build slice"): the `kind` enum refuses an undeclared
kind; a lint holds each `box` inside `outer` and each `id` unique; `rack.json`
`frames` gains `enclosure` for a product that states one; the product page lists
the entries. Nothing else reads an entry in the first build.

### Where this note departs from section 4

1. It adds the required `id`.
2. It fixes the values of `where` to four, and gives a side's box its keys.
3. It says what `box` absent means, by kind.
4. It holds `enclosure` to `entries` alone until doors, panels and a roof are
   built.

It does not rename `entries`, `where`, `kind`, its four values or `box`.

## 2. An open frame's top as an exit

The open frames (`2-post-frame` and `4-post-frame`) have no roof, so the issue
asks what their top is for a cable. Three readings:

- **Implicit by `form`.** The kit treats the top of a `2-post-frame` or a
  `4-post-frame` as an exit. Nothing is written in the product.
- **Declared.** The product states `{id: top, where: roof, kind: open}`, with
  no `box`. The data says it, and a document can be cited for it.
- **Declared only where a manual shows it.** The same as the second, but the
  entry is written only for products whose sources say the top is open.

**Proposal: declared, with `kind: open` and no `box`.** For `apc/ar201` and
`apc/ar203a`:

```yaml
enclosure:
  entries:
    - {id: top, where: roof, kind: open}
```

- The whole plan of `outer` is the exit. A cable can leave anywhere within it;
  the posts do not close it, and the route (section 3) chooses the point.
- It is a statement the product's own sources already carry. A frame with no
  roof is open at the top by construction. AR201's `form` provenance note
  describes a top angle and a bottom angle joined to two upright rails; a
  roofless frame is the same fact. The entry's `source` says that, and cites no
  figure it has not looked at.
- Declaring is preferred to implying because the other two readings put a
  meaning in the kit that no file shows. A reader of `rack.yaml` would not know
  that the frame has an exit, and a cabinet that is also a four-post would need a
  second rule to be left out. Under the proposal the kit reads one list.

**A floor-standing frame's bottom is not declared.** A frame stands on a base or
feet. Whether a cable may pass under it, or through a floor, is a fact of the
building, and no held source for a frame says it. The note does not add a
`floor` entry to any frame. A product whose manual shows an open or cut base
adds one.

**A wall frame** (`wall-frame`, `wall-frame-vertical`): its back is the wall, and
`rear` is not a value of `where`. Its top is open on the same reasoning as a
floor-standing frame if its sources show no roof, and then it declares the same
`top` entry. A `wall-cabinet`, a `wall-cabinet-vertical` or a `4-post-cabinet`
declares only the entries a manual shows. The generic `4-post-cabinet` has
none, so a cable cannot be routed to its exit until a source gives one.

**A rack with no product `ref`.** A frame the Rack Builder has freed from its
product (`frame.customise`, section 11 step 2) is drawn from the file's numbers,
and a file holds no `enclosure`, so the kit has none to read. Under the proposal such a rack has no declared exits. The alternative is
a fall-back by `form` for these racks alone (open frames only), which gives the
second reading back for a case the data cannot cover. Open question 3 asks.

**The 11 products today.** Under the proposal the first build adds the `top`
entry to the open frames the library holds and to no cabinet:
`apc/ar201`, `apc/ar203a`, the two Chatsworth frames, the two FS and two
StarTech four-post frames and the generic two- and four-post frames. Whether the
generic frames, some of whose figures are stand-ins, also state the entry is
open question 10. The cabinets named in the intake
have entries whose sizes the intake does not yet give (below).

## 3. The shape of the outside cables a caller passes in

### The cable

A **rack-file cable**, in the rack file's own shape (`$defs.cable`), with the far
end replaced by an **exit end**:

```yaml
- id: run-17                        # the id of the cable where it is stored
  a: {item: pp-1, path: rear/12, view: rear}   # a rack end, as the rack file names it
  b: {exit: top}                    # an exit end: the id of an entry of this rack's product
  media: cat6a
  type: cat6a-ftp                   # optional, an id of cable-types.yaml
  purpose: Riser to room 2.14
  label: R17
  route: []                         # automatic, as for any cable; or waypoints that pin it
```

- **An exit end is `{exit: <id>}`.** The id names an entry of the rack's
  product. **`{exit: any}` names none**: the kit takes the nearest declared entry
  of kind `brush`, `cutout` or `open`, by the in-rack length. A `knockout` is
  taken only when named. `any` is why that word cannot be an entry's `id`.
- **The near end is a rack end**, `{item, path, view}` with `plug` where the port
  takes more than one, exactly as the rack file writes it. A caller holding the
  site file's rack end (`{rack, item, path, view}`) drops `rack`.
- **The cable is the caller's.** Its `id` is the id it has where it is stored
  (the site file's file-wide id is already unique). It is never added to the
  rack file's `cables`.
- **`length`**, if the caller has it, is the whole run's length and is not used
  for the in-rack figure. The in-rack part is returned (below).
- **Both ends in one rack** is not an outside cable. It is stored in the rack
  file (site file section 8.1).

### How a caller makes one from a site cable

A site cable with one rack end gives one outside cable for that rack. A site
cable with a rack end at both ends, in two racks, gives **two outside cables**,
one for each rack, each with its own rack end and an exit end. Each rack sees
only its half. The far end's identity is not passed: the rack has no use for it.

Which exit a run leaves by is a choice the site file stores on that **end**. The
site file reserves `exit` on a rack end, and this note proposes its form: **an
optional key `exit` on the existing rack end**, an entry id of that rack's
product. Absent, the caller passes `{exit: any}`.

```yaml
# a site-file cable, one end shown
a: {rack: rack-a, item: pp-1, path: rear/12, view: rear, exit: top}
```

Because the site file's rack end does not forbid other keys, an `exit` key on it
passes a version-0 reader and needs no new version. A portless exit end,
`{rack, exit}` (a trunk that drops into a rack at its exit and is not yet
patched), is a fourth whole form of `end` and a version-0 reader refuses it. So
that form, if it is ever wanted, is **version 1 of the site file**. No line of
the issue's "Done when" needs it, and this note does not propose it now.

### What the kit returns

For each outside cable, the kit answers, in the rack's own units:

- **`inRack`**: the length of the in-rack route from the port to the entry's
  plane, and the waypoints, the rings and ducts passed. It is measured as the
  kit measures any routed cable, with the same bend and lead rules. It does
  **not** include the lead out through the entry and what follows it: the
  caller adds the rest of the run, since only the caller knows the wall, the
  tray and the far end.
- **`exit`**: the entry id taken, so that `{exit: any}` reports which one.
- **`inRack: null`, with a sentence**, when no length can be given: the product
  declares no entry; the named id is not in the product; the rack has no
  product `ref`; the port is not on a device. Nothing is estimated.
- **Where on the entry** the route ends: the point of the entry's `box` nearest
  the last waypoint, on the entry's plane, and for an `open` entry with no box,
  the same point on the envelope's plan. The lane rules are the cable lay note's
  and are the kit order's to apply.

### What a query does with them

Fill and the free-port queries take the outside cables **as an extra input**
from the caller. The proposal is a field `outside` on the context the queries
already take (`ctx`), a list of cables in the shape above; the kit order fixes
the spelling.

- **A port is taken** when a cable of `rack.cables`, **or** a cable of
  `outside`, has it. `portFree` reads both and `freePorts` therefore leaves it
  out. With the cable not passed in, the port reads free.
- **A ring or duct counts** an outside cable whose in-rack route passes it,
  once, by the cable's media diameter. Only the in-rack part is counted.
- **`outside` absent is not `outside: []`.** An empty list is the caller saying
  that nothing is stored elsewhere. Absent says the caller has not looked.
- **The rack file never stores them.** The kit reads `outside` and writes
  nothing from it. `save` of the rack gives the same bytes with and without it.

### A rack opened on its own

A rack opened with no site shows a run stored above it as nothing: the port
reads free, the managers' fill leaves the run out, the bill of materials and the
DCIM exports leave it out. That is the cost of the rule that the rack file never
holds a cable stored elsewhere, and it is not corrected by guessing. The kit says
so once: when `outside` is absent, the description of the rack ends with a line
that cables stored outside it are not passed in and the ports they use read
free. The line is not printed when `outside` is given, empty or not.

### What the shape is, formally

The shape is the kit's **input contract**, documented in the kit README and
checked by the kit when it reads `outside`. It is not a part of the rack file
and not a key of `rack.schema.json`, so the rack schema is not republished for
it. A separate schema for it is an option (open question 5).

## What each line of the issue's "Done when" needs

| line | decided by | and made checkable by |
|---|---|---|
| A cable from a patch panel's rear port to the rack's top exit has an in-rack route and length | section 1 (an entry with an `id`), section 2 (an open frame's `top` entry), section 3 (the exit end and `inRack`) | a rack of `apc/ar203a` with a patch panel; the cable above; `inRack` is a number and the route names the waypoints |
| A manager's fill counts outside cables that pass through it | section 3 (`outside` counted once per ring or duct, by media diameter, in-rack part only) | a manager whose ring the route passes: its fill rises by the cable's area with `outside` given and does not without |
| A rear port whose cable is stored outside reads taken when that cable is passed in, and free when it is not | section 3 (`portFree` and `freePorts` read `outside`; absent is not empty) | `freePorts` lists the port without `outside` and omits it with `outside` |
| The rack file is byte-identical either way | section 3 (never stored; the kit writes nothing from `outside`) | `save` of the same rack before and after the queries, with and without `outside`, compared byte for byte |

## What moves when it is built

Counts are from `main` at the time of writing. "Before public" says whether the
change may be made while the package is at 0.x (`docs/format-stability.md`).

| # | Item | Count | One-way? | Before public |
|---|---|---|---|---|
| 1 | `enclosure.entries` in `rack-product.schema.json`, `enclosure` limited to `entries` | 1 block, 1 key | yes: products will state it; the key path is published | allowed; an optional key |
| 2 | `entries` items: `id`, `where` (`roof`, `floor`, `left`, `right`), `kind` (four values), `box`, `source` | 5 keys, 8 values | yes: the names are published and a rename breaks products | allowed |
| 3 | The meaning of `kind: open` with no `box`: the whole part of `outer` | 1 rule | yes: a narrower reading later moves every frame's exit | allowed |
| 4 | The reserved entry id `any` | 1 word | yes | allowed |
| 5 | The republished `rack-product.schema.json` | 1 `$id` under `/schemas/v1/` | yes: a schema `$id` is published; this adds a key to the same schema | allowed; additive |
| 6 | The `top` entry on the open frames | up to 10 products (the cabinet is left out) | each a minor version of its product, and a lock change | allowed |
| 7 | The exit end `{exit: <id>}` and `{exit: any}` as the kit's input shape | 1 shape | yes: callers write it | allowed |
| 8 | `exit` on the site file's rack end | 1 optional key | yes: site files carry it | allowed; needs no site file version |
| 9 | `outside` on the query context, and the meaning of absent against empty | 1 field | yes once a caller relies on it | allowed |
| 10 | The kit's `inRack` result and what it includes | 1 field | yes: callers add their own lead to it | allowed |
| 11 | The describe line for a rack opened with no `outside` | 1 line | no | allowed |
| 12 | A portless exit end `{rack, exit}` in the site file | 1 form | version 1 of the site file | not proposed |

The one-way list is items 1 to 5 and 7 to 10.

## The first build slice

The slices are later orders, each its own pull request, in this order.

1. **The key.** `enclosure.entries` in `rack-product.schema.json` with the
   `kind` enum, the lint for `id` and `box`, `rack.json` `frames` and the
   catalogue, and the `top` entry on `apc/ar201` and `apc/ar203a` with a test
   that an undeclared kind is refused. A schema republish, so it waits for a
   decision on this note.
2. **The kit.** The route from a port to an exit and the in-rack length; the
   fill and the free-port queries with `outside`; the describe line; and the
   docs for a rack opened on its own. The four lines of "Done when" are tests of
   this slice.
3. **The other open frames** (Chatsworth, FS, StarTech and the generic shapes),
   if the first slice declared only the two APC ones.
4. **The cabinets**, with the NetShelter entries, each from a manual's figure.
5. **The site file** reads `exit` on a rack end and passes the outside cables.
   That belongs to the site file's own work.

Doors, side panels, the roof and `options` of section 4 are not in this note
and stay unbuilt.

## What a manual must give

- **Entry sizes for a cabinet.** NetShelter SV, SX and SX Advanced entries need
  a figure each from the product's manual, drawing or datasheet. The user
  manuals for the three are held in the FS cabinet intake folder. The sizes have
  not been read, so no figure is written here. Wanted: the roof, base and side
  access drawings of each.
- **A cable's allowance at an exit.** How much lead a cable needs beyond the
  entry plane is not stated by any held source. The kit does not add one.
- **The GR cabinets' brush openings** are listed in the intake coverage as six;
  their positions and sizes are not held.
- **Whether a frame's base is open to a floor.** No source for any frame says.

## Open questions

Each carries the proposal.

1. **Where does `entries` sit?** `enclosure.entries` (proposed: it is section 4's
   and section 12's shape, and doors join it without a second move) or a
   top-level `entries`. One-way either way.
2. **Does an entry have an `id`?** Yes (proposed): a route ends at a named place.
   The alternative is to name an entry by `where` and its order in the list,
   which breaks when a product is edited. One-way.
3. **How is an open frame's top an exit?** Declared as `kind: open` with no `box`
   (proposed), implied by `form`, or declared only where a manual shows it. And
   for a rack with no product `ref`: no exit (proposed), or a fall-back by
   `form`. One-way as a published meaning.
4. **What is a side entry's `box`?** `{y, z, h, d}` on `x = 0` or `x = outer.w`
   (proposed), or one box form for every `where` with a stated plane. One-way.
5. **Where is the outside cable's shape defined?** As the kit's input contract
   only, in the kit README (proposed), as a new small schema with its own `$id`,
   or as a `$defs` in `rack.schema.json`, which republishes the rack schema for
   a shape the file never holds. The second and third are one-way.
6. **Does an outside cable name its entry?** Optionally (proposed): `{exit: <id>}`
   names, `{exit: any}` takes the nearest `brush`, `cutout` or `open` entry, and
   a `knockout` is taken only when named. One-way.
7. **What does the in-rack length include?** The route from the port to the
   entry's plane (proposed), with the lead out through the entry left to the
   caller; or the same plus a stated allowance, which no held source gives.
   One-way once callers add their own figure to it.
8. **What does a rack opened alone show for a run stored above it?** The port
   reads free and the description says so once when `outside` is absent
   (proposed); or the rack is refused whole when it has a port no cable explains
   (it cannot know). Neither changes the rack file.
9. **Which end form does the site file take?** An optional `exit` key on the rack
   end (proposed; needs no version) or a portless exit end as version 1 of the
   site file (one-way).
10. **Which products state `top` in the first slice?** The two APC frames
    (proposed), all open frames, or the library's frames that have a held
    datasheet. The count of version bumps differs: 2, 10 or fewer.
11. **Is the first slice the key alone, or the key and the kit together?** The key
    alone (proposed): the schema republish is the one-way step and is smaller
    reviewed alone.

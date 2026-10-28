# The site file, version 0: rooms, placed racks, surfaces, pathways and cables between racks

Status: **proposed 2026-10-28; to be decided before the schema merges.** A new
published format is one-way, so this note, its schema
(`spec/schemas/site.schema.json`), its checker
(`spec/tools/portrayal/sitefile.py`) and its fixture land in one pull request
and wait for the decision. Code that builds on the format may be stacked on
that branch while the decision is pending. Issue #1297. Read beside it: #1299
(a rack's cable entries) and #1296 (a ceiling mount).

Builds on the rack file as it stands (`kit/rack/model.js` `VERSION` 4,
`spec/schemas/rack.schema.json` under `/schemas/v3/`), on
[rack-file-v4-design.md](rack-file-v4-design.md) section 12, which reserved
rows and a room for a version 5, and on
[rack-products-design.md](rack-products-design.md) sections 5 and 10, which
left anchors, wall fixings and a room view as "data for a later room view".
[format-stability.md](format-stability.md) has the rules a format follows.

Three words are used one way throughout, as in the rack file note. **Read**
means read in a file of this repository. **Measured** means run or computed
for this note. **Inferred** means reasoned from those, and not checked. One
more: **to verify against IFC 4.3** marks every claim about IFC. The IFC 4.3
specification is not held here, and the pages in section 17 are cited, not
read. Only IFC's entity and type names are used.

## 1. What the site file is, and is not

**It is** a second document, `format: "portrayal-site"`, `version: 0`, that
sits above the rack file. It holds:

- the spatial tree: a site, its buildings, their floors, and the spaces on
  each floor (section 2);
- racks placed in a space, each by reference to its rack file and the rack's
  id in it (section 4);
- walls, and surfaces fixed to them, such as a plywood backboard holding
  devices (section 5);
- devices that are not in a rack: an outlet or faceplate, an access point, an
  adapter in a room (section 6);
- pathways, as a graph of segments with a kind and a height (section 7);
- cables whose two ends are not in one rack, each stored at the lowest level
  that holds both ends (section 8).

**It is not** a rack file version. Read in `rack-file-v4-design.md` section
12: rows of racks and a room were reserved for rack file version 5. This note
proposes instead that **the rack file stays one rack, and the room is a
separate document** (decision 1). A rack file placed in a site is
byte-identical to the same file opened alone, opens in the Rack Builder
unchanged, and needs no new key. Section 16 is the change to section 12 of
that note.

**It is not** the kit. The modules that read and write it, the editing
commands, routing and multi-rack editing are kit work that follows the
decision. Section 12 names the API the format implies, so it can be decided
with the format, and builds none of it.

### 1.1 Why a separate document

Read in `kit/rack/editor.js`: the editor edits `current.racks[0]` and nothing
else (line 28). Read in `rack.schema.json`: a cable end is
`{item, path, view}`, with no rack in it, so a cable is local to one rack.
Read in `rack-products-design.md` section 10: rows were to be
`rows: [{id, racks, gaps}]` on the rack document, and a room after rows.

Three ways were weighed:

| | (a) rack file version 5 with rows and a room | (b) a site file above the rack file | (c) a site file that embeds its racks |
|---|---|---|---|
| a rack file today | refused by every version-4 reader | unchanged | copied into the site |
| the Rack Builder | must learn rooms before it opens a file again | opens each rack file as now | must open a rack out of a site |
| a cable between two racks | an end gains a rack | an end in the site names rack, item and port | the same as (b) |
| one rack edited by two people | one file | one file a rack, and a site that names them | one file for everything |
| the version gate | one-way for every rack file | one-way for site files only | one-way for both |

**Proposed: (b).** It is the one that costs a rack file nothing. A rack file
version is a one-way door for every saved rack; a site file is a new document,
and only a site file passes through its door. (c) puts two copies of a rack
in reach of each other, and the two drift.

## 2. The document

```json
{"format": "portrayal-site", "version": 0, "name": "Zorb test site",
 "site": {"id": "site-zorb", "guid": "2FdDpCuT5VnPosDIfBc4JF", "name": "Zorb campus",
          "buildings": [...], "points": [...], "cables": [...]},
 "ext": {}}
```

`format`, `version` and `site` are required. `name` and `ext` are optional.
The document itself has no `id`: the site is what it describes, and the
site's `id` and `guid` serve.

### 2.1 The spatial tree

The four levels take IFC 4.3's names (to verify against IFC 4.3):

| level | key | IFC entity | holds |
|---|---|---|---|
| site | `site` | `IfcSite` | `buildings`, `points` (outside the site), `cables` between buildings |
| building | `buildings[]` | `IfcBuilding` | `floors`, `pathways`, `cables` between two of its spaces |
| floor | `floors[]` | `IfcBuildingStorey` | `elevation`, `spaces` |
| space | `spaces[]` | `IfcSpace` | `outline`, `height`, `walls`, `racks`, `surfaces`, `devices`, `cables` within it |

The tree is stored as JSON, not as IFC's own exchange file. The names are
taken so that an IFC export is a mapping and not a translation, and so that a
reader who knows IFC knows what a level is. Nothing in version 0 reads or
writes IFC.

A wall is IFC's `IfcWall` in name only (to verify against IFC 4.3): here it
is the face of a wall seen from one space, a line in the plan, and not a
solid (section 5).

### 2.2 Identity: an `id` and a `guid` on every object

Every object in the tree has two identifiers:

- **`id`**: a short string, unique across the whole file, as a rack file's
  item ids are short. It is what other objects refer to (`wall`, `rack`,
  `device`, `floor`, a node, a point), and what an operation log names. It
  matches `^[A-Za-z0-9][A-Za-z0-9._-]*$` and is at most 64 characters.
- **`guid`**: IFC's `GlobalId` (to verify against IFC 4.3): a 128-bit
  identifier written as 22 characters from `0-9`, `A-Z`, `a-z`, `_` and `$`,
  whose first character is `0` to `3` because it carries only the top two
  bits. It is what an export to IFC or to a DCIM carries, so that an object
  keeps its identity across two exports.

**The rule (one-way):** an `id` or a `guid` is unique across the whole file;
neither changes once written; neither is given to another object after this
one is removed. The checker holds the first part (section 11); the other two
are rules for every writer, and the kit's tests hold them.

Why two and not one: a GUID is unreadable in a log or a cable schedule, and
an id is not unique outside its file. Considered: the GUID alone, which makes
every reference 22 opaque characters; the id alone, which leaves an IFC
export to invent GUIDs and lose them on the next export.

**Why unique across the whole file, not within a list.** An operation log
says `move rk-1` or `remove out-2`, and must mean one object without a path.
Read in `rack.schema.json`: a rack file item id is unique within its rack,
which is right for one rack and is why a site names an item as rack and item
together (section 8.2). Rack file ids are not site ids; a site never takes one
as its own.

## 3. Coordinates and units

- **Millimetres throughout.** Every length and position is a number of
  millimetres. No key states a unit, and none may.
- **One plan per floor.** `x` and `y` are millimetres in the plan of the floor
  the object is on, from that floor's origin, `x` to the right and `y` up the
  plan. A space's `outline` is a closed polygon in the same plan. Nothing in
  version 0 relates one floor's plan to another's, other than `elevation`;
  a building whose floors are offset is drawn by its floors' own origins.
- **Heights are above the finished floor** of the floor the object is on.
  A floor's `elevation` is its finished floor above the building's datum.
- **Angles are degrees**, clockwise seen from above.

The two points a placement is measured to are the middle of the front of a
rack's footprint (section 4) and the middle of a device (section 6), so that
a rotation turns a rack about its front and an outlet height is the height
an installer measures to.

## 4. Racks placed in a space

```json
{"id": "rk-1", "guid": "1Nn1GUFhPU_8QfqTLh$Ywt",
 "file": "../racks/acceptance.rack.json", "rack": "r1",
 "x": 2000, "y": 800, "rotation": 0}
```

- **`file`** is the rack file as a path relative to the site file, and
  **`rack`** the id of the rack in it. A rack file today may hold more than
  one rack; the site names one.
- **`x`, `y`** are the middle of the front of the rack's footprint, and
  **`rotation`** turns it about that point. At 0 the front faces down the
  plan. The footprint's width and depth are the rack's own: its frame, or the
  catalogue product its frame names.
- **A rack stands in one place.** Two placements of the same rack of the
  same file are refused by the checker.
- **The rack file is read and never written by being placed.** Nothing in a
  site changes a rack file, and nothing a rack file needs comes from the
  site. The checker opens a placed rack file for reading only, and a test
  compares its bytes before and after (section 11).

**What this leaves of section 12 of the rack file note.** Rows, aisles and
baying are facts about two racks, so they belong where two racks are: here.
A row is a later, additive key of a space (`rows: [{id, racks, gaps}]`, the
shape rack-products-design.md section 10 gave it, with placement ids in
`racks`), and baying is checked between two placements against their
products' `baying`. Neither is in version 0, and neither needs a version of
either file when it comes: a version-0 reader keeps a key it does not know.
`between: true` on a zero-U entry is resolved by the placement beside it.
Anchors and a cabinet's wall fixings (rack-products-design.md sections 5 and
10) are drawn from the product at the placement; the site stores nothing for
them.

## 5. Walls and surfaces

```json
{"id": "wall-er-n", "guid": "1WxAloXNvKSQ845EcXC0Nv",
 "a": {"x": 0, "y": 3000}, "b": {"x": 4000, "y": 3000}}
```

A **wall** is the face of a wall seen from inside the space: a line in the
plan from `a` to `b`. Facing it from inside, `a` is the left end. A space
lists only the walls something is fixed to; its `outline` is its shape.

```json
{"id": "bb-1", "guid": "2PTTfpCL1HxxBq4T9M7x7U", "kind": "backboard",
 "material": "plywood, fire-rated", "wall": "wall-er-n",
 "along": 1000, "bottom": 900, "width": 2440, "height": 1220, "thickness": 19,
 "devices": [{"id": "wd-1", "guid": "27fXJnno9UCO7ZfJX7C8Ln",
              "ref": "zorb/wall-switch", "x": 300, "y": 600}]}
```

A **surface** is a board fixed flat to one wall of its space:

- `kind` is `backboard` in version 0. Another kind is an additive enum value,
  which a version-0 validator refuses; section 14 lists the enum as one-way
  for that reason.
- `material` is free text, as written.
- `along` is from the wall's `a` end to the board's left edge, and `bottom`
  from the finished floor to its bottom edge. `width`, `height` and
  `thickness` are the board's own.
- `devices` are mounted on it at `x`, `y` from its bottom-left corner, facing
  it, to the middle of the device.

Read in `rack-products-design.md` section 10: a wall frame or wall cabinet is
a frame with front rails only, and fits as a rack now. It is placed as a
rack, against a wall. Whether it is drawn on the wall or on the floor plan is
a drawing question, and needs no key.

## 6. Devices that are not in a rack

```json
{"id": "out-1", "guid": "3lUiNWrEDRFgzxIWhHLGoF", "ref": "zorb/faceplate-2",
 "label": "ER-01", "wall": "wall-er-n", "x": 3600, "y": 3000, "height": 450}
```

- **`ref`** is the device by its catalogue ref, as a rack item names one.
  `cfg` and `label` are as on a rack item.
- **`x`, `y`, `height`** are the middle of the device. `wall` names the wall
  it is fixed to, if it is.
- **A placed device's mount is its device's `mount`.** Read in
  `device.schema.json`: `mount` is `rack`, `rack-face`, `rack-side`,
  `din-rail`, `wall` or `desktop`, stated by the device. The placement does
  not restate it, and adds no value to it. A ceiling mount is #1296's
  question; when the device schema has one, a ceiling device is placed with
  the same keys, `height` being the ceiling's.
- **A private device in a public file.** Read in `device.schema.json` and the
  overlay library (`build.sh --overlay-library`): a device's `audience` is on
  its contract, and a project keeps private devices in an overlay. A site
  file names a private device by its ref as it names any other. A reader
  without that overlay keeps the placement as written and reports the ref as
  not in its library, as the rack kit does a removed ref. The site file
  carries no `audience` of its own (decision 9): who may see a file is
  decided by the refs it places, and a tool that publishes one reads it from
  them.

The fixture's refs (`zorb/wall-switch`, `zorb/faceplate-2`,
`zorb/access-point`) are stand-ins in an overlay's form, and resolve in no
library. Version 0's checker does not resolve refs.

## 7. Pathways

```json
"pathways": {
  "nodes": [{"id": "pn-1", "guid": "1gVfEQG4zUZxeFD$aoCvM$", "floor": "floor-1",
             "x": 2000, "y": 1300, "height": 2400}, ...],
  "segments": [{"id": "ps-1", "guid": "3DjCRCZFLNcghbo2V7V0Vf",
                "kind": "ladder-rack", "a": "pn-1", "b": "pn-2", "width": 300}, ...]}
```

Pathways are a **graph on the building**: nodes where segments end or meet,
and segments between two nodes. They are on the building and not on a space
because a tray leaves the room it starts in, and a riser joins two floors.

- **A node** is a point on a floor, `x`, `y` in that floor's plan and
  `height` above its finished floor: where a cable lies in the carrier there.
- **A segment** is a straight run of one carrier between two nodes. **Its
  height is that of its ends**: a segment whose ends differ in height is a
  rise or a drop, and one whose ends are on two floors is a riser. Routing
  (section 12) reads rises and drops from the nodes.
- **`width`** is the carrier's width, or a conduit's inside diameter, where
  stated. Fill is the routing note's.

The five kinds, aligned with IFC's `IfcCableCarrierSegmentTypeEnum` (every
row to verify against IFC 4.3):

| `kind` | what it is | IFC value |
|---|---|---|
| `j-hook` | a run of J-hooks | `CABLEBRACKETSEGMENT` if IFC 4.3 has it, else `USERDEFINED` |
| `basket-tray` | a wire basket tray | `CABLETRAYSEGMENT` |
| `ladder-rack` | a ladder rack | `CABLELADDERSEGMENT` |
| `conduit` | a closed tube | `CONDUITSEGMENT` |
| `surface-raceway` | a channel fixed along a wall | `CABLETRUNKINGSEGMENT` |

The kinds are this format's own words, so that a reader does not need IFC to
read them, and the table is the mapping an IFC export uses.

**A rack or device is not joined to the graph in version 0.** Where a cable
leaves a rack and meets a pathway is #1299's (a rack's cable entries) and the
routing note's. If the join is stored, it is an additive key on a placement
or a node, and needs no version.

## 8. Cables

### 8.1 The lowest level that holds both ends

**A cable is stored at the lowest level that holds both its ends:**

| both ends are | the cable is stored in |
|---|---|
| in one rack | that rack's rack file, as today; never in the site |
| in one space, not in one rack | the space's `cables` |
| in two spaces of one building, on one floor or two | the building's `cables` |
| in two buildings, or one at a point outside the site | the site's `cables` |

A floor holds no cables. A run between two closets on one floor and a riser
between two floors are both backbone, and one level for both means a closet
moved to another floor moves none of its cables. A rack end is in the space
its rack is placed in; a device on a surface is in the surface's space; a
point outside the site is on the site.

**The rule is the checker's, not the schema's.** A schema sees one cable at a
time and cannot know which space a rack is placed in. `sitefile.check` refuses
a cable stored above its lowest level ("it belongs in that rack's rack file"
for two ends in one rack) and one stored below it, in a space that does not
hold one of its ends.

Why a rule and not a free choice: a cable in two places is two cables, and a
reader looking for every cable of a rack must know where to look. With the
rule it looks in the rack file and in the space the rack is placed in, then
up the tree.

### 8.2 Ends

An end is one of three forms, and **an end is whole**: a port with nothing to
be a port of is refused by the schema.

| form | keys | means |
|---|---|---|
| rack end | `rack`, `item`, `path`, `view`; `plug` optional | a port of a device in a placed rack: the placement id, then the item, port path and panel as the rack file's own cable end names them |
| device end | `device`, `port`; `plug` optional | a port of a device placed in a space or on a surface |
| point end | `point`; `port` optional | a named point outside the site, such as a provider's demarcation point, listed in the site's `points` |

A rack end is the rack file's end (`{item, path, view}`, read in
`rack.schema.json`) with the placement in front of it, so the kit resolves it
with the code it has. The checker reads the placed rack file and refuses a
rack end whose item the rack does not have.

A cable carries `media` (the rack file's values), `type` (an id from
`spec/schemas/cable-types.yaml`, published as `cable-types.json`), `label`
and `purpose`, as a rack file cable does. Its length, route, slack and lay
are routing's (section 12), and each is an additive key when it comes.

### 8.3 A cable at a rack's exit: a place left for #1299

A cable from a rack to the room leaves the rack somewhere: through a roof
brush, a floor cutout or an open side. Read in `rack-products-design.md`
section 4: `enclosure.entries` are boxes in a product's roof, floor or side,
and "a later route can end at one". Which entries exist and how a route uses
them is #1299's.

This note leaves the place and defines nothing in it: **the key `exit` on a
rack end is reserved** for #1299. Version 0's rack end requires a port
(`item`, `path`, `view`); a cable that runs to a rack and ends at its exit,
with no port, is not a version-0 end. If #1299 needs one, it decides whether
that is an additive end form or version 1 of this file. `entries` is not
defined here.

## 9. Extension blocks and unknown keys

**Unknown keys are kept at every level**, as the rack file keeps them since
version 4 (read in `rack-file-v4-design.md` decision 9): a reader reads,
keeps and writes back a key it does not know. That is for this format's own
later keys, so that an optional one needs no version.

**Extension blocks are for everyone else.** The document, every object with
an `id`, and a building's `pathways` may carry `ext`, a map whose keys are a
namespace and a version:

```json
"ext": {"example.wifi@1": {"channel": 36}}
```

- **A key** is a dotted namespace of two parts or more and a version:
  `^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)+@[1-9][0-9]*$`. A bare key
  (`"poe"`) is refused by the schema, and so is one with no version.
- **A value** is an object, described by a JSON Schema the namespace's
  holder publishes.
  The site schema checks only the key and that the value is an object. A
  reader that knows a block may validate it; one that does not keeps it
  whole and writes it back unchanged.
- **A namespace belongs to whoever holds the name.** A reverse domain name
  is the convention
  (`com.example.poe@1`). `portrayal.*` is reserved for this project, for data
  that is not yet a key of the format.
- **A new version of a block is a new key** (`@2` beside `@1`), so two readers
  of different ages each find the one they know.

Why both: an unknown bare key looks like this format's own, and a later
version may take the name. A namespaced block cannot collide with the format
or with another holder's block.

## 10. Versions and the reader rule

- **Version 0 is the first version.** Its schema is
  `https://portrayal.dev/schemas/v1/site.schema.json`, titled
  "Portrayal site file (v0)".
- **A reader given a newer version refuses it whole** and names both
  versions, in the rack file's sentence: "This site file is version 1; this
  reader supports up to version 0." It never reads part of a file.
- **A reader given another format refuses it**, naming the format it found.
- **The label.** Read in `format-stability.md`: the rack schema's labels count
  that schema's own publications (`/v1/` for rack version 2, `/v2/` for 3,
  `/v3/` for 4), and a label is never reused for a different format. The same
  page says a new manifest format number goes under the next label no schema
  has taken, `/v4/`. This note proposes `/v1/`, since a label names a
  publication of one schema file, and `/v1/site.schema.json` has never been
  published. If `/v4/` is decided instead, it is a one-line change to the
  schema and to its test, made before merge (decision 2).
- **What raises the version** is what raises a format (format-stability.md):
  a key removed or renamed, a meaning changed, a file that was valid refused.
  An optional key does not.

`format-stability.md` gains the site file's section when the format is
published; it is not changed by this pull request.

## 11. The checker, the fixture and the tests

**The checker** is `spec/tools/portrayal/sitefile.py`, plain functions over a
parsed document so that the kit can mirror them:

- `read(path)`: the version-0 reader rule (section 10);
- `check(doc, base=None)`: the schema's findings, then, on a file the schema
  accepts, every id and guid unique; every reference resolved (a wall in its
  space, a node's floor in its building, a segment's nodes, an end's rack,
  device or point); each rack placed once; the lowest-level rule. Given
  `base`, each placed rack file is read and a rack end's item checked in it;
- `check_file(path)`: both, with `base` the file's folder.

It is format code, not kit code: it reads, and never writes, a site file or a
rack file.

**The fixture** is `spec/tests/fixtures/site/zorb.site.json`, made up: one
floor with two spaces; the rack of `fixtures/racks/acceptance.rack.json`
placed by reference; a plywood backboard with one wall device; two outlets;
an access point; three pathway segments (ladder rack, J-hooks, a surface
raceway that drops); and cables at three levels: in the rack file (its own
`c1` to `c8`), rack to outlet in the room, and a closet-to-closet stub in the
building.

**The tests** are `spec/tests/test_site_schema.py`:

| test | proves | planted |
|---|---|---|
| the fixture validates against `site.schema.json` | the schema and checker accept the shape this note describes | none: the positive case |
| the fixture holds what the note asks of it | the positive case is not vacuous | none |
| a cable stored above the lowest level holding both ends is refused | the placement rule is enforced | a cable with both ends in one rack, stored in the room |
| a cable between two spaces stored in one of them is refused | the rule from below | the closet stub moved into the room |
| an id used twice anywhere in the document is refused | ids are unique across the file | an outlet and the rack sharing an id |
| a guid used twice is refused | guids are unique across the file | two devices sharing a GUID |
| an extension block without a namespace and version is refused | the extension rule | `ext: {"poe": {}}` |
| an unknown well-formed extension block is valid | the other half of the rule | `example.unheard-of@3` |
| a cable end naming a port and no device is refused | ends are whole | an end with `port` alone |
| the placed rack file is byte-identical before and after the site is read | placing a rack never rewrites it | none: a hash comparison |
| the checker does read the placed rack file | the hash is not vacuous | a rack end naming an item the rack lacks |
| version 1 is refused with both versions named | the reader rule | the fixture with `version: 1` |
| another format is refused | the format gate | the fixture with `format: portrayal-rack` |

`test_schema_hygiene.py` holds the `$id`, the title and the version const;
`test_schema_descriptions.py` lists the new schema and its recorded shape.

## 12. The kit API this format implies (named, not built)

This API is decided with the format. Nothing here is built.

| area | API | what it does |
|---|---|---|
| file | `readSite(text)`, `validateSite(doc)`, `serializeSite(doc)` | read with the reader rule; the checker's findings, mirrored; write back with every unknown key and extension block kept, and the same bytes for a file opened and saved unchanged |
| edit | `createSiteEditor({doc, racks, chassisOf})`, `apply(cmds)` with `place`, `move`, `remove`, and `undo`, `redo` | place, move and remove a rack, a surface, a device, a node, a segment or a cable, each with undo; commands name objects by `id` only, so a log replays |
| racks | `select(rackId)` | a rack editor for one placed rack, its history kept per rack; the end of `racks[0]` being the only rack edited (`kit/rack/editor.js` line 28) |
| route | `routeRun(site, cable, ctx)` | the run along pathways, as parts: `in-rack`, `rise`, `pathway`, `drop` and `service-loop`, each with its millimetres and what it runs through, and their sum; never a straight line, and refused where the graph does not join the two ends |
| reach | `reach(site, from, {maxMm})` | every end reachable from `from` within a length along the pathway graph, with the length to each |

- **Moving a cable between levels** is the editor's: when a move takes one
  end of a cable into another space, the cable moves to the new lowest level
  in the same step, and its id does not change.
- **The rack file is saved by the rack editor**, never by the site editor.

## 13. Decisions (proposed 2026-10-28, to be decided)

| # | question | proposed | considered | one-way |
|---|---|---|---|---|
| 1 | Where rooms and rows go | a separate document above the rack file; the rack file stays one rack (1.1) | rack file version 5; a site that embeds its racks | yes: section 12 of the rack file note changes |
| 2 | Name, version, label | `portrayal-site`, version 0, `$id` under `/schemas/v1/` (10) | under `/schemas/v4/`, the next label no schema has taken | yes |
| 3 | The tree | site, building, floor, space, with IFC 4.3's names, stored as JSON (2.1) | an IFC file; names of our own | yes: the keys |
| 4 | Identity | an `id` and an IFC-style `guid` on every object, each unique across the file, never changed and never reused (2.2) | the GUID alone; the id alone; ids unique within their list | yes |
| 5 | Coordinates | millimetres; one plan per floor; heights above the finished floor; a rack measured to the middle of its front, a device to its middle; degrees clockwise, front down the plan at 0 (3) | metres; one plan per building; a rack measured to a corner | yes |
| 6 | Racks | placed by `file` and `rack`; read, never written; placed once (4) | a copy of the rack in the site | yes |
| 7 | Walls and surfaces | a wall is a line seen from one space; a surface hangs on one wall, at `along` and `bottom` (5) | walls as solids; surfaces placed in the plan | yes |
| 8 | A placed device's mount | its device's `mount`; no key, no new value (6) | a `mount` key on the placement | two-way: a key can be added |
| 9 | Audience | none in the file: it follows the refs placed (6) | an `audience` key on the document | two-way |
| 10 | Pathways | a graph on the building; a segment's height is its nodes'; five kinds aligned with IFC (7) | a height on the segment; pathways on the space | yes: the kinds and the graph |
| 11 | Cable levels | rack file, space, building, site; no floor level; checked, not schema (8.1) | a cable stored anywhere above its ends; a floor level | yes |
| 12 | Ends | three whole forms; `exit` reserved for #1299 (8.2, 8.3) | a free end with optional keys | yes |
| 13 | Extensions | `ext` with namespaced, versioned keys; unknown keys kept at every level (9) | unknown bare keys alone | yes |
| 14 | The reader | a newer version refused whole, naming both (10) | reading what it can | yes |
| 15 | The kit API | as section 12 | decided with the kit module | two-way until built |

## 14. One-way items

| item | where | why it is one-way |
|---|---|---|
| the format name `portrayal-site` | site file | saved files carry it; a reader keys on it |
| version 0's shape: the tree and its keys, rack placement, wall, surface (`kind` and its one value), placed device, pathway node and segment (`kind` and its five values), cable, the three end forms, `ext` | site file, schema | saved files carry it; an enum value added later is refused by a version-0 validator |
| the schema's `$id`, `https://portrayal.dev/schemas/v1/site.schema.json` | schemas | a published label is never reused |
| the GUID rule: an IFC `GlobalId` of 22 characters on every object, unique, never changed, never reused | site file, exports | exports carry it, and an object keeps its identity by it |
| the id rule: unique across the file, never changed, never reused | site file, operation logs | a log replays by it |
| the lowest-level rule for cables | site file, rack file | a reader looks for a cable where the rule puts it |
| the reader rule: a newer version refused whole, both named | readers | agents and pages match the sentence |
| the change to section 12 of the rack file note: rows, the room and cables between racks belong to the site file, and the rack file stays one rack | rack file | no rack file version 5 carries them |

## 15. Left for later

**Kit work, after the decision, and no format change:**

- the kit modules that read, validate and write a site file (section 12);
- the editing commands, with undo, and `select(rackId)` for more than one
  rack;
- routing along pathways, and the reachable-length query;
- drawing a floor plan and a wall elevation.

**Additive keys, with no version:**

- rows in a space, and baying checked between placements (section 4);
- a stored join between a placement or device and a pathway node (section 7);
- a cable's length, route, slack and lay;
- an IFC export.

**Owned by other issues:**

- a rack's cable entries, `entries`, and a cable end at a rack's exit:
  #1299 (section 8.3);
- a ceiling mount: #1296 (section 6).

## 16. The change to the rack file note

Section 12 of [rack-file-v4-design.md](rack-file-v4-design.md) listed rows of
racks, a room, and slack across racks as needing rack file version 5. This
pull request changes that section: they belong to the site file, and the
rack file stays one rack. Baying and `between: true` are resolved between
two placements in a site. A stored position for a sliding channel stays a
rack file question.

## 17. References

Cited, not read; every claim this note makes from them is marked "to verify
against IFC 4.3":

- buildingSMART, IFC 4.3, `IfcCableCarrierSegmentTypeEnum`:
  https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/HTML/lexical/IfcCableCarrierSegmentTypeEnum.htm
- buildingSMART, IFC 4.3, Port Connectivity:
  https://standards.buildingsmart.org/IFC/DEV/IFC4_3/HTML/concepts/Object_Connectivity/Element_Connectivity/Port_Connectivity/content.html

The port connectivity concept is where an IFC export of a cable end would
start: a port of an element, connected to a port of another (to verify
against IFC 4.3). Version 0 states nothing that depends on it.

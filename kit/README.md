# @portrayal/kit

The consumer half of [Portrayal](https://github.com/roc-ops/Portrayal#readme).
It reads compiled artifacts and does something with them — draws them, lets
you inspect them, exports them.

**It never reads YAML.** That line is the whole point of this package: the
manifests, the component contracts and the schema live in `spec/` and `library/`
and are the compiler's business. Everything here works from what `build.sh`
publishes, which means a consumer needs the artifacts and not a checkout.

## Install

```sh
npm install @portrayal/kit
```

`three` is an optional peer dependency, needed only for the 3D half (see
[three.js](#threejs) below).

## What it reads

Everything in `library/dist/`, documented as a contract in
[`library/README.md`](https://github.com/roc-ops/Portrayal/blob/main/library/README.md).
The short version:

- `<device>.<config>.<view>.svg` — the drawing. Addressable: `--` DOM ids, `/`
  data-paths. Its `<metadata>` names the source it was drawn from by
  `source-sha256`. Configurations that draw a face identically share one file,
  so the kit finds a configuration's face through `configs[].files` in
  `<device>.configs.json` (`faceFile` in `dist.js`), never by its name.
- `<device>.source.json` — the **whole source manifest**, every view of it: the
  device's configurations, groups, attrs and chassis. One per device.
- `devices.json`, `components.json` (+ `components-detail.json`), `kits.json`,
  `rack.json`, `labs.json`, `gaps.json`, `vendors.json`, `listings.json`.

## Where it reads from

`createShell` and `createViewer` take `dist`: either the base URL of a build
directory, or a function from a path in the build to its URL. `dist.js` makes
both:

```js
import { flatDist, packageDist } from '@portrayal/kit/dist';

// a build directory: library/dist, or a copy of it on your own server
createShell({ dist: flatDist('/portrayal/dist') });

// the npm packages, from jsDelivr: one package per device and one per
// component namespace, each fetched only when something in it is opened
const dist = await packageDist();                   // @portrayal/index@latest
const pinned = await packageDist({ index: '0.3.1' });  // one release, exactly
createShell({ dist });
createViewer(el, { dist });
```

`packageDist` resolves `latest` to an exact version first, and then reads
every file at the exact version the index's `packages.json` names for it, so a
page never mixes two releases. `at(name, version)` changes where packages are
served from: another CDN, or `library/packages/` after `./publish.sh` to try
the packages locally. The explorer does that with `?dist=packages`, and reads
jsDelivr with `?dist=cdn` (and `&index=<version>`).

## Modules

| module | what it does |
|---|---|
| `shell.js` | the explorer shell — device picker, view switching, tree. The newest `loadDevice`/`loadStage` call holds the stage: one that a newer load overtook writes nothing and rejects with an error `isSuperseded(err)` recognises. It reads the page's own query string at start-up: `device`, `listing`, `config`, `view`, `swap`, `turn` and `fields`, so an embedding page that uses one of those names for something else collides. A `fields=` entry for a part drawn only on a face the link does not open is judged once the other faces are fetched, and kept |
| `viewer3d.js` | 2D→3D: rasterises each face onto a chassis-sized box, adds relief meshes; a host can hold coloured marks on many parts (`setMarks`) and paint a lamp its own colour (`setLampColors`) |
| `relief.js` | turns `data-depth` / `data-z-*` annotations into geometry |
| `bevel.js` | a bevelled chassis body from the polygons the build publishes, triangulated and mapped for the 3D view |
| `lamps.js` | animated lamps in 3D: each blinking lamp drawn once per keyframe and swapped by the clock (used by `viewer3d.js`, not exported on its own) |
| `marks.js` | annotation and callouts |
| `states.js` | state toggling (LEDs, link states) and what a display can read; an outlet's state shown on its lamp: the lamps `for:` binds to a part that declares states (`boundLamps`), a `{path: classes}` state map with each bound lamp given its outlet's classes (`expandStates`, which `marks.js`, `relief.js` and `viewer3d.js` apply), and whether an `off` chip sets `state-off` or clears (`offIsSet`) |
| `share.js` | GLB and USDZ export |
| `gif.js` | GIF capture |
| `swap.js` | swapping a component into a bay, or an occupant into a slot at the turn it takes there (`seatTurn`); the `swap=` and `turn=` location strings (`encodeSwaps`, `decodeSwaps`, `encodeTurns`, `decodeTurns`) |
| `redirects.js` | a part the library replaced: `redirectsOf(components)` reads the `supersedes` lists of `components.json` into a resolver (`follow(ref)`, `trace(ref)`), and a rack is audited (`auditRack`) and rewritten (`rewriteRack`) against it; the rules are under "New in 0.32.0" in [Racks](#racks) |
| `fields.js` | writing a field on a part at runtime - its text and its colour, the build's rule, for 2D and 3D alike; and what a form of a part's fields needs: its rows (`fieldRows`), whether a value is one the field takes (`fieldAccepts`), and the `fields=` location string (`encodeFields`, `decodeFields`); and a part that slides: whether a value is a position (`adjustmentAccepts`), the rows of its control (`adjustmentRows`), what a face declares (`adjustmentsOf`) and the move itself (`paintAdjustments`); see [A part that slides](#a-part-that-slides) |
| `displays.js` | what a display shows: the rules for `{text}`, `{digits}` and `{image}` content against a display's kind, columns and rows, the text layout, the size and fit of a picture (a GIF cut to its first frame), and the painter 2D and 3D share (`paintDisplays`); see [Racks](#racks) |
| `devsel.js` | device selection and filtering - hardware by its maker, and each NOS vendor's listings under that vendor (`listings.json`, #709) |
| `nosnames.js` | what the chosen listing's NOS calls each port (`swp7`, `Ethernet24`, `ge100-0/0/7`), expanded by the same grammar as the DCIM export (#712) |
| `optical.js` | where a fibre goes: an optical module's front number and far end for a path, read from `components.json` |
| `dist.js` | artifact fetching, and where each file is: a build directory or the npm packages |
| `zones.js` | the ports and bays of a compiled face, each with its box in millimetres - what the diagram exports put a connectable shape over |
| `drawio.js` | draw.io: a shape library, a rack elevation, or one live drawing as a `.drawio` (`toDrawio`), with a named connection point per port |
| `omnigraffle.js` | OmniGraffle: a `.gstencil` with a named, magnetised shape per port, or one live drawing as a stencil (`toGraffle`) |
| `ears2d.js` | generic rack ears over a published face in 2D (`drawEars`, `clearEars`), from the plan the 3D viewer builds (`earPlan`); see [Rack ears](#rack-ears) |
| `positions.js` | the Explorer's control for a part that slides (`positionControl`): a slider over the range, a button for each named stop and a reset, written through the shell's `setFields`; see [A part that slides](#a-part-that-slides) |

Plain ES modules. No bundler, no build step.

## A part that slides

New in 0.19.0. A device may declare a part that slides (a rail panel on
slotted brackets), and the compiled drawing says what moves: the root of every
face carries `data-adjustments`, and each member node `data-moves-with` and
`data-moves-by`. [`docs/format-stability.md`](../docs/format-stability.md) has
the fields, and
[`docs/adjustable-positions-design.md`](../docs/adjustable-positions-design.md)
the design. The FS DINRAIL2U and DINRAIL4U declare one, `rail-setback`, the
distance of the rail panel behind the ears. The Explorer has a control for it
(0.20.0, [below](#the-position-control)); a position can also be set with
`setFields` or a `fields=` link.

**A position is a field.** It is held at the path of the adjustment's carrier,
under the adjustment's id, in the same map every other field is in:

```js
shell.setFields('rail-panel', {'rail-setback': '271.2'});   // a number in mm
shell.setFields('rail-panel', {'rail-setback': 'rear'});    // or the name of a stop
// ?fields=rail-panel~rail-setback~271.2
```

Every member on every face moves. What is kept is one spelling: a string, the
number rounded to 0.1 mm, with no exponent and no trailing `.0`. A stop name
is input, and the number is what is kept. A value that is not a position is
not applied: the drawing stays as it was, the sentence is logged, and
`setFields` returns it:

```js
shell.setFields('rail-panel', {'rail-setback': '300'});
// {refused: [{path: 'rail-panel', key: 'rail-setback', value: '300',
//   reason: 'rail-setback on DINRAIL2U takes 51.2 to 271.2 mm. 300 is outside it.'}]}
```

`setFields` returned nothing before 0.19.0; it now returns `{refused: []}` for
every call. A number is digits and one point: `-20`, `+20` and `1e2` are
refused. An empty value is a reset: `setFields(path, {[id]: ''})` puts the
members back where the drawing was built and keeps nothing, as
`resetField(path, key)` and `setFields(path, null)` do. `applyFields` takes a `fields=`
entry for a position, which no component declares, and ignores one that is not
a position.

| `fields.js` | |
|---|---|
| `adjustmentsOf(root)` | the adjustments a face declares, `{id: {axis, carrier, range, default, stops, label, datum, at, id, on}}`, or `{}`. `at` is the position the file was built at, and `on` the model the face names |
| `adjustmentAccepts(adjustment, value, who)` | `{ok: true, value}` with the one spelling to keep, or `{ok: false, reason}` with a sentence. `who` (`{id, on}`) names the adjustment and the device where the adjustment does not carry them |
| `adjustmentRows(adjustments, current)` | the rows of a control, in id order. `adjustments` is what `adjustmentsOf` answers, or `adjustments` from a device's `configs.json`; `current` is the fields map, `{path: {key: value}}`. An entry from `configs.json` has no `at`, so its row shows the default as `built`: for a configuration that sets a position, give the entry `at` from that configuration's `positions` first (`{...a, at: config.positions[id] ?? a.default}`). A row has `id`, `label`, `carrier`, `axis`, `datum`, `unit`, `type` (`range` or `stops`), `min`, `max`, `stops` (`[{name, value}]` in order of position), `default`, `built`, `value` and `stop`, positions as strings |
| `paintAdjustments(root, fields)` | moves every member under `root` to the position `fields` holds, and back as built when it holds none. Answers `{id: position}` |
| `positionsChanged(adjustments, was, now)` | whether going from one fields map to another moves a part that slides: true when the value at some carrier's path, under its adjustment's id, differs |

**In 3D** the position is in the same map: `viewer.setFields(map)` rebuilds
the scene when a position changes, as it does for a switch position. A well is
built at the depth the position gives, and what stands in it on that floor.
`relief.js` exports `applyNodeAdjustments(root, scope)`, the same move applied
from a viewer's field registry before a face is measured.

### The position control

New in 0.20.0. `positions.js` exports one function, the control the Explorer
mounts above its tree:

```js
import { createShell } from '@portrayal/kit/shell';
import { positionControl } from '@portrayal/kit/positions';

const shell = createShell({dist});
positionControl(shell, {threeD: () => true});
shell.emit('mode', '3d');      // the page says which stage is showing
```

For each adjustment of the device on screen it draws one group: the label, the
position in mm, a slider over the range in steps of 0.1 mm, a number box, one
button for each named stop in order of position, and a reset. With stops and
no range the buttons are the whole control. Nothing is drawn for a device that
declares no adjustment, or inside a module.

- **It writes through `shell.setFields(carrier, {[id]: value})`** and holds no
  rule of its own. A stop button sends the name and the shell keeps the number;
  the reset sends an empty value. So the position is in `state.cfgFields` with
  every other field, and a page that puts that map in its location and hands
  it to the 3D viewer, as `kit/index.html` does, needs nothing more.
- **A value that is refused is said under the control**, in the sentence
  `setFields` answers, in an element with `role="status"`. The drawing and the
  number box stay where they were.
- **The slider is a native range input**, so it takes the arrow keys, Page Up
  and Page Down, Home and End. It is named by the label of the adjustment and
  described by its range and datum. In 2D each value is written as it moves.
  In 3D each position is a scene to rebuild, so the value is written when the
  slider is let go.
- **A view that cannot show the motion says which views do**: "The front view
  does not show this. See the top, bottom, left or right view, or 3D." A face
  shows the motion when a member on it has a `dx` or a `dy` in its
  `data-moves-by`. The control asks the shell for the other faces
  (`loadFaces`) when an adjustment is declared and the shell does not hold
  every face of the device. A request that ends with a face still missing
  is sent once more. After that the control does not ask again until the
  shell emits `load` or starts a new set of faces, so a face that cannot be
  fetched is not fetched at every step of a slider.
  In 3D the line is not shown.

`positionControl(shell, opts)` answers `{el, refresh}`. `opts.before` is the
element the control goes in front of (the shell's tree by default), and
`opts.threeD` a function that says whether the page offers a 3D view. The
control hears the shell's `load`, `fields` and `mode` events. `mode` is the
page's own: emit `'2d'` or `'3d'` on the shell when the stage changes. The
control is styled from the shell's CSS variables, under `#positions`.

The built scene cannot be measured under node.
[`spec/tests/browser/viewer3d-adjustments.html`](../spec/tests/browser/viewer3d-adjustments.html)
reads its vertex positions in a browser, at the default and at both ends of
each axis, after a rebuild and after a repaint. Run it after a change to
`relief.js`, `viewer3d.js` or the move in `fields.js`, and before a release
that touches them; its header has the commands.

## Racks

The `rack/` modules are the Rack Builder's rules, without its page. They read
no DOM and fetch nothing but the catalogue and the cable types, so the same rack is checked the
same way in a browser, in node and in an agent. Each is imported on its own,
as `@portrayal/kit/rack/<module>`:

**Never change a rack, an item, a cable or an end in place, and make a new
route context whenever any answer of it could change.** The kit keeps what
it works out for a cable and finds it again by those objects, so one changed
in place is given the answer that was right before, with nothing to say so.
Every command and `apply` return a new rack that shares what it did not
touch, which is the way to edit one; an end is never put on the same cable
object. To find a page that breaks this, put `checkKept: true` on the route
context in its tests: every path read is then laid again from nothing and
compared, and a difference throws ("New in 0.25.0" below).

| module | what it does |
|---|---|
| `rack/catalog.js` | `loadCatalog(dist)`: the rack catalogue, and the `chassisOf(ref)` lookup everything else takes; `loadSlots(dist, refs)`: the bays, cages and parts the commands check against |
| `rack/model.js` | the rack file: `newDoc`, `parseDoc`, `serialize`, and an edit of an item, frame or name that returns a new rack |
| `rack/rails.js` | the rack's rails: unit height, opening and where a device sits between them |
| `rack/fit.js` | whether a device fits at a unit, on a face and (a narrow part) on one rail; whether a zero-U part fits beside the rack (`fitsZeroU`); how a shrink trims a rack |
| `rack/zero-u.js` | the parts beside the rack: where each stands, as words (`whereText`) and as x (`zeroUX`), whether the lane beside its upright runs through it, and each placeable entry (`zeroUEntries`) |
| `rack/managers.js` | cable managers: `placement` of a manager onto the device behind it, and moving one |
| `rack/cable-rules.js` | cables: which two ports may be joined, `withCable`, media and lengths; a cable's own colour (`parseColor`), what decides the colour it is drawn in (`colorFacts`, `cableColorOf`, `colorsKey`), and the plans a drawing reads (`cablePlan`, `cablePlan3d`) |
| `rack/cable-types.js` | the cable types (`cable-types.json`): `loadCableTypes(dist)` fetches them and returns `typeOf`, `bendOf` and `diameterOf` over them; the same lookups are exported to build over a table already in hand (a fixture, a cached copy): `typeOf(types, id)`, `cableTypeOf(types, cable)`, `radiusMm(type, which)`, `installedRadiusMm(types, id)`, `bendLookup(types)` and `diameterLookup(types)`, each radius in millimetres; `jacketLookup(types)` and the loaded `typeColorOf` give the jacket colour of the type a cable names |
| `rack/route.js`, `rack/route-path.js`, `rack/cable-geometry.js` | where a cable runs: `resolveRoute`, `ownRoute`, `trunkMeasures`, `routePath`, `trayOf`, `ringMarks`, `orientMarks`, `reverseMarks`, `routedLength`, `pathLength`, pathway fill, `ringFindings`, `bodyFindings`, `bendFindings`, `coverFindings`, and the geometry under them (`throughRings`, `cornersOf`); and the colour a cable is drawn in: `COLORS`, `cableColor`, `colorOf`, `hexColor`, `agreedJacket`, `bundleColor`; and the width it is drawn at: `WIDTH`, `widthOf` |
| `rack/solids.js` | the solid bodies a route may not pass through: `solidsOf(rack, ctx)` places every device's envelope or derived `solids` in rack coordinates; `legCrossings` tests a leg against them; `detour` takes a leg round them (with `room`, far enough out for the bends at each end); `CLEAR`, the clearance a detour keeps; `traysOf(rack, ctx)` places every device's `trays`, the floors a cable lies on; a ring's solid parts (`ring/<id>/<part>`) are met by the cable's tube |
| `rack/bundles.js`, `rack/bundle-route.js` | cable bundles: the size and bend checks (`bundleCheck`, `bundleChecks`, `pathwaysOn`, `bendCheck`, `cornersOf`), strap positions (`straps`), the trunk worked out from the members' routes (`deriveTrunk`) and a member's route along it (`followTrunk`) |
| `rack/displays.js` | the displays of a placed device and what they show: `displaysOf`, `displayRefusal`, `displaysFor`, `displayNotices`, `displayList` |
| `rack/export-data.js` | the rack as rows: `bomRows`, `cableScheduleRows` and the device-import data, what the lay finds as notes (`layNotes`, `layNotesOf`), and the bundles as the exports read them (`bundleExports`, `bundleNotes`, `strapBomRows`) |
| `rack/dcim-rules.js` | what a NetBox or Nautobot import needs of a rack: the names a type file gives its ports (`typeLists`, `resolveEnd`, and `endResolver`, which answers for every end of a rack), the modules file, the cables file (`cableImportRows`) and the README |
| `rack/validate.js` | `validate(schema, value)`, a small JSON Schema validator, and `same` |
| `rack/commands.js` | every edit as a named, validated command, and `apply` for a batch of them |
| `rack/history.js` | undo and redo as snapshots |
| `rack/editor.js` | `createRackEditor`: a rack document you edit by commands, with undo, redo and change events |
| `rack/queries.js` | reading a rack: `fitsAt`, `freeUs`, `catalog`, `describe`, `inspect`, `selectCables`, `freePorts`, `suggestMedia`, `looseEnds` |
| `rack/ports.js` | the ports of what a device's bays hold, read without a drawing: `seatedPort` (does a cable end name one, on which panel, and what holds it), `fibrePorts` (the front or rear ports of its module type that a fibre adapter is, from `optical.ports` in `components.json`), and `settleEnd` and `settleEnds`, which lay that over the facts a page read off its drawings; `seatedJacket`, `jacketAt` and `jacketsFor`, the jacket colour the part seated at a cable end states |
| `rack/resting.js` | internal, not exported: how a cable rests, for `route.js` (`DRAPE`, the free span's hang and landing, laid only where it leaves every corner its bend radius, the held face) |
| `rack/slots.js` | internal, not exported: what a placed device holds, read without a drawing, for `commands.js` and `queries.js` |

### Heights, spans and half units

A position (`ru` on an item) is a whole unit or a half, counted bottom-up
from 1: 12 is the bottom of U12 and 12.5 its middle. `rack/fit.js` owns what
follows from one, and no other module computes it:

| name | answers |
|---|---|
| `unitsOf(chassis)` | the height of a device in units, in halves: its stated `ru` rounded up to the next half, never under 0.5, and 1 when it states none |
| `spanOf(item, chassisOf)` | `[lo, hi)`: the units an item fills, half-open, so a 1.5U item at U1 is `[1, 2.5)` |
| `itemBox(rack, item, chassisOf)` | `{y0, y1, h, lo, hi}` in mm above the bottom of the rails: the body, centred in its span, and the edges of the span. A drawing stands a body here |
| `spanText(frame, item, chassisOf)` | the span in words: "U13", "U13-U14", "the lower half of U7", "U13 to the lower half of U14" |
| `heightOf(chassisOf)`, `itemsWithU(rack, chassisOf)` | as before, and now 0.5 for a half-unit device |

`rack/model.js` has `positionOf(frame, ru, units)`, the lowest-numbered half
unit an item fills as the frame counts (what NetBox calls a position), and
`uText(frame, ru, units)`, the same as "U12.5". `rack/queries.js` `freeUs`
returns half positions for a device that may start on one. `rack/rails.js`
has `holesIn(lo, hi)`, the rail holes an ear between two heights can use,
for a page that draws ears.

`setbackOf(rack, item, chassisOf)` is how far a faceplate stands behind its
rail in mm: the item's own `setback`, else the default ear position the
catalogue gives the device, else the frame's `setback`, else 0. A drawing
moves a body back by it; fit and the routes already do. `frameNotices(rack,
chassisOf)` gives a sentence for each key the kit keeps and does not yet act
on (a rail width that is not 19 in, a zero-U `channel`, an item held by
another), which the editor hands on as findings when a document is loaded.
`firstU(frame)` in `rack/model.js` is the number of the first unit (`startU`,
1 when absent); `uLabel` and `positionOf` count from it.

`rack/catalog.js` `loadSlots` keeps the `pdu-class` of each device it reads,
and `configFacts(slots, cfg)` gives what a rack entry is checked against for
the configuration it names: what the device meters (`meteringOf`), the
`states` each placed part can be set to, the `slots` it offers a hanging
part and the `mountPoints` it hangs by, as its `configs.json` states them.

`span`, the closed whole-unit pair `[ru, ru + u - 1]`, is gone: it cannot say
half a unit. Use `spanOf`, and read its second number as the top edge.

An item may be rolled in its face (`roll`: 90, 180 or 270 degrees clockwise
as seen from the face it is on; `rollOf(item)` in `rack/model.js`).
`itemUnits(item, chassisOf)` is its height in units as mounted, which is
what `spanOf`, `itemBox`, `heightOf` and `itemsWithU` use: rolled a quarter
turn it is the width of the device in whole units, and `itemBox` then also
gives `w`, the height of the device, lying across the opening.
`facePoint(rack, item, {x, y, view}, chassisOf)` turns a point of a face as
drawn (mm from its left edge and down from its top) into the rack, through
`face`, `turned` and `roll`; `rollPoint(rack, item, {x, y}, chassisOf)` turns
a rack point of the upright item to where it is as mounted. A routing
context (`portX`, `portY`, `guidesOf`) gives its points for the upright
item, and the kit turns them, so a page that rolls them itself turns them
twice. `isQuarter(item)` says an item is an outline to a route.

`rack/states.js` reads what an entry is set to against the facts of its
device (`configFacts`): `statesFor(entry, facts)` is the `{path: state}` map
to hand a drawing, holding only what each part declares and carried from an
outlet to its lamps when `facts.bindings` gives them; `readingsFor(entry,
facts)` is `{source, at, badges}`, or null; `stateNotices(rack, ctx)` names
what is kept and not applied. `rack/zero-u.js` has `fitsHang(rack, entry,
ctx)`, where a part hung on brackets stands or why it cannot,
`hangNotices(rack, ctx)` and `bracketPositions(rack, {ref, cfg, ru}, ctx)`.
A page calls the two notice functions once it has loaded the parts lists
(`loadSlots`); the editor cannot, since it holds none.

A cable's lengths are named in `rack/route.js`: `needOf(path, cable,
stock)`, `shortTolerance(cable, stock)`, `spareOf(rack, cable, ctx, path)` (need,
stock, spare, end play and what is to store, in metres, or null without a
path) and `stockLength(need, {values})`. `rack/slack.js` resolves a cable's
`slack` list against its route: `slackOf` (each entry with its metres and
whether the cable can store there), `storedText` (the words of the list),
`slackFindings`, `spareLine` (one line for a rack) and `spareExports`, which
is what `cableScheduleRows` takes as `spare` to fill its `spare` and `stored`
columns. It returns no geometry: spare is listed, not drawn.

`straps(rack, bundle, ctx)` in `rack/bundles.js` gives each strap its `kind`
(`spacing`, `breakout` or `anchor`) and its `width_mm`, with `kinds` and
`widths`, the count of each; `count` is all of them, and the spacing straps
alone are `kinds.spacing`. An anchor names its tray and the index of its tie
slot. `anchorsOf(rack, ctx)` lists
every tie slot a strap is at, rack-wide, with the bundles and cables tied
there, and `strapTotals(rack, ctx)` is what the rack buys. The stock widths
(`STRAP_WIDTHS_MM`: 12, 19 and 25 mm) and the clearance a strap keeps from a
peel point are estimates, with no maker's sheet held: 19 mm is the strap, 25
for a pack 25 mm across or more, and an anchor is no wider than its tie slot
is long. `straps()` also returns `notes`, a sentence for each tie slot no
strap goes through. A page draws a
band at each slot of `anchorsOf`, and hands the list to `strapBomRows(bundles,
{anchors})` so that single cables count.

The exports take what the routes know from the page. `cableScheduleRows`
fills `spare` and `stored` from `{spare: spareExports(rack, ctx)}` and its
last column, `straps`, from `{straps: strapTexts(rack, ctx)}`, a Map of
cable id to the tray, the face and the tie slots a single cable is strapped
at. `cableBomNotes(rack, ends, {spare})` adds the one line that totals the
spare, and `drawioCables(rack, {spare, ...})` gives each cable with a
length its `spare`, which `kit/drawio.js` writes after the length in the
edge label. `deviceImportRows({statesOf, ...})` writes what is set off in
the comment of each row, when `statesOf(entry)` answers `statesFor` for it.
`namesOf(entry)` beside it answers `configFacts(...).names`, so an outlet is
named as the device-type export names it (A2, not outlet-a2).
`rollNote(item)` is the sentence of a rolled item and `offNote(states,
names)` the line of what is off; `hungText(rack, entry, chassisOf)` in `rack/zero-u.js`
is where a part hung on brackets is, as an export words it.

`cable.lay` pins how a cable lies in a pathway (`lay` on the cable), and
`layFaceOf(cable, {item, via})` in `rack/route.js` is the face the file pins
on a tray, which a route reads before `ctx.trayFaceOf`.

`holderOf(item)` in `rack/model.js` is the id of the item that holds one on
a shelf or a rail (`heldBy`), or null, and `isHeld(item, chassisOf)` in
`rack/fit.js` says whether a held item is one the kit does not check: a page
draws such an item on its host, and not in a unit of its own.

Of the names these modules export, a page draws and calls with: `unitsOf`,
`itemUnits`, `spanOf`, `itemBox`, `spanText`, `setbackOf`, `facePoint`,
`isQuarter`, `isHeld`, `frameNotices` (`rack/fit.js`); `positionOf`,
`uText`, `firstU`, `rollOf`, `ROLLS`, `holderOf` (`rack/model.js`);
`holesIn` (`rack/rails.js`); `freeUs` (`rack/queries.js`); `needOf`,
`shortTolerance`, `spareOf`, `stockLength`, `END_PLAY_M`, `BREAK_TOL_M`,
`UNPLACED_WARN_M`, `layFaceOf` (`rack/route.js`); `slackOf`, `storedText`,
`slackFindings`, `spareLine`, `spareBomLine`, `spareExports`
(`rack/slack.js`); `rollNote`, `offNote` (`rack/export-data.js`);
`hungText` (`rack/zero-u.js`); `strapTexts`, `strapKinds`,
`anchorsOf`, `strapTotals`, `STRAP_WIDTHS_MM`, `BREAKOUT_MM`,
`BREAKOUT_MERGE_MM`, `BREAKOUT_GROUP_MM`, `BREAKOUT_TWO_MM` (`rack/bundles.js`); `configFacts`,
`meteringOf` (`rack/catalog.js`); `statesFor`, `readingsFor`, `stateNotices`
(`rack/states.js`); `bracketPositions`, `hangNotices` (`rack/zero-u.js`).
`facePoint` is the one a drawing calls for a point of a face; `rollPoint`,
which it goes through, is the kit's own.

Every other name added with rack file version 4 is the kit's own, shared
between its files, and may change without notice: `spansMeet`, `anchorY`,
`laneY`, `neighbours`, `unitsText`, `hostUnits`, `unitOn`, `hostedRu`,
`fillOf`, `overlapNotices`, `fitsDepth`, `reachOf`, `centreX`, `rollPoint`,
`heldBy`, `uncheckedText`, `unheldText`, `bothText`, `zeroUExtent` and
`notBracket` in `rack/fit.js`; `stateRefusal` in `rack/states.js`;
`fitsHang`, `hangingOn` and `HANG_TOL_MM` in `rack/zero-u.js`; `STRAP_BASE_MM`,
`STRAP_WIDE_MM`, `WIDE_PACK_MM`, `STRAP_CLEAR_MM` and `widthCounts` in
`rack/bundles.js`; `toMetres`
and `slackValues` in `rack/route.js`; `trayRefusal`, `trayText`, `mText`
and `FORMS` in `rack/slack.js`; `SLACK_FORMS` in `rack/model.js`; `isPosition`,
`HOLE_STYLES`, `railWidth`, `RAIL_WIDTH_IN`, `holdersOf` and `usableReadings`
in `rack/model.js`; `HOLE_EDGE` in `rack/rails.js`; `NO_HOSTS` in
`rack/commands.js`; `NETBOX_RACK_WIDTHS` in `rack/export-data.js`, since a
page offers no choice of width.

### Where this came from

`kit/rack/` was moved here from `roc-ops/portrayal-site`, where it was
`site/rack/`, at that repository's commit `d1a1aa8e`. This repository is now the source of
truth: edit these modules here. portrayal-site vendors
`kit/rack/*.js` read-only, and its contract check refuses a copy that has
drifted. The rules these modules follow are stated in their own comments,
and the rack file format in [`docs/format-stability.md`](../docs/format-stability.md)
and `schemas/v3/rack.schema.json`.

### The catalogue

`rack.json` is written by the build beside `devices.json`. For every device it
holds the rack units, the depth and height, how it mounts, whether its body is
sheet, the cable capacity its vendor states (with the kind of cable counted,
`capacity.media`, where a source names it), the ids a route can pass
through, and its `kind`: a plain word for what it is (`switch`, `patch panel`,
`cable manager`, ...) that `catalog(devices, { kind })` filters by. `kind` is
advisory and its words may be refined. `loadCatalog(dist)` takes what the other loaders take: a base URL, or
a function from a path in the build to its URL. It therefore works with
`flatDist` over a build directory, and with `packageDist`, which serves
`rack.json` from `@portrayal/index` (a device that is itself named `rack` would
collide with it there). `packageDist` needs an `@portrayal/index` release that
contains `rack.json`; an earlier one has none, and the load fails.

```js
import { loadCatalog } from '@portrayal/kit/rack/catalog';
import { newDoc, withItem } from '@portrayal/kit/rack/model';
import { placement } from '@portrayal/kit/rack/managers';
import { withCable } from '@portrayal/kit/rack/cable-rules';
import { resolveRoute, routedLength } from '@portrayal/kit/rack/route';
import { bomRows, cableScheduleRows } from '@portrayal/kit/rack/export-data';

const catalog = await loadCatalog('/portrayal/dist');   // or await packageDist(), or a flatDist()
const { chassisOf } = catalog;

let rack = newDoc().racks[0];
const lower = withItem(rack, { ref: 'as7726-32x', cfg: 'ac-f2b', ru: 10, label: 'leaf-1' });
const upper = withItem(lower.rack, { ref: 'as7726-32x', cfg: 'ac-f2b', ru: 20, label: 'leaf-2' });

// A cable manager put where a device is lands on it.
const where = placement(upper.rack, { face: 'front', ru: 10 }, chassisOf);
const manager = withItem(upper.rack, { ref: 'fhd-cmp5dr', cfg: 'base', ...where, label: 'mgr-1' });

const cabled = withCable(manager.rack, {
  a: { item: lower.item.id, path: 'port-1', view: 'front' },
  b: { item: upper.item.id, path: 'port-2', view: 'front' },
  media: 'cat6a',
});
rack = cabled.rack;

// A ctx comes from the drawings: the guides on each part and the x of each
// port, in mm from the rack's centre line. A plain one is enough for lanes.
const ctx = { chassisOf, guidesOf: () => [], portX: () => -100 };
const route = resolveRoute(rack, cabled.cable, ctx);
const length = routedLength(rack, cabled.cable, ctx);   // { measured, value }, in metres

const devices = rack.items.filter(i => chassisOf(i.ref)?.mount !== 'rack-face')
  .map(i => ({ ref: i.ref, cfg: i.cfg, ...catalog.devices[i.ref] }));
const bom = bomRows({ devices, frame: rack.frame, railUs: [1, 1] });
const schedule = cableScheduleRows(rack);
// With the routes, each bundle's length, straps, size and bend:
// const bundles = bundleExports(rack, { route: ctx });
// cableScheduleRows(rack, ends, items, routes, { bundles }); strapBomRows(bundles)
```

`loadCatalog` reads through `fetch` and `location`, which a browser has and plain
node does not. In node, build the same lookup from the file:

```js
import { readFileSync } from 'node:fs';
import { chassisLookup, catalogEntries } from '@portrayal/kit/rack/catalog';

const { devices } = JSON.parse(readFileSync('rack.json', 'utf8'));
const chassisOf = chassisLookup(devices);
const entries = catalogEntries(devices);
```

The rest of the example takes `chassisOf` and `devices` from either.

`resolveRoute` returns the waypoints a cable follows (`waypoints`), any stored
ones that no longer stand for anything (`gone`), and whether the route is the
automatic one (`auto`). `routedLength` is that route, measured, with the
nearest stock length above it.

A cable passes through a D-ring along the ring's `run`, not to a point inside
it: `routePath(rack, cable, ctx)` is the path every measure reads, each ring
expanded to the point where the cable enters it and the point where it leaves,
half the ring's `depth` (`RING_DEPTH`, 10 mm, estimated, when the ring states
none) either side of its centre. A route that would enter and leave a ring by
one face is not drawn through it; `ringFindings(rack, ctx)` reports it, and
neither `fill` nor `capacityOver` counts it there; since 0.12.0, not when the
ring stands right past the nearer of its neighbours and that neighbour is a
port (its near face within the ring's depth plus the cable's diameter of it,
the diameter capped at the depth): the cable only reaches in to be held, passes
(`held: true` on the path's ring) and is counted, with no finding. `routePath` decides each
ring once; `ringMarks(rack, cable, ctx)` gives those decisions, one per
waypoint, and `routed2d` and `routePoints3d` take them as an optional last
argument, so the drawings pass through each ring straight and the way it was
measured. A mark's `sense` is along the rack's axes (x right as seen from the
front, y up); a drawing whose axis runs the other way turns it with
`orientMarks(marks, flip)`: a front elevation flips y (`{ y: -1 }`), the
mirrored rear pane flips x and y (`{ x: -1, y: -1 }`), and the 3D scene passes
its marks unchanged. `reverseMarks` is for a path drawn from its other end.
**Routed lengths changed in 0.5.0**: each ring adds up to its depth, and the
automatic route no longer takes a ring behind the port, which could shorten a
length by up to 100 mm. A rack's stored `routed` lengths are re-measured the
next time a page measures them (`lengths.routed`).

Every body in the rack is solid to a route (`rack/solids.js`, #949). A box
device is its envelope; a part whose rack.json entry carries `solids` (a
sheet part's plates, a vertical duct's walls and back) is those boxes, each
with the pass-throughs that cut it as `holes`; a sheet part, or a zero-U part
that carries a lane, without them is open. A cable crosses a body only through a ring, a duct's finger
gap, or a pass-through whose smaller side fits its diameter
(`ctx.diameterOf(cable)` when given, else its media's). Where a straight leg
would cross one, `routePath` adds detour points (`at: 'detour'`): over the
body's near edge (a tray's front edge first), else round its end, else by a
side lane, going round a second body the same way when a detour meets one.
They count in the length and are never stored; `path.detours` lists them. A
zero-U part that stands in the gutter and carries no lane (a zero-U PDU)
moves the lane beside its upright outboard of it, where it stands
(`laneXAt`), and a zero-U part is gone round on its back, the side facing
into the rack, before its outward face. A leg the rules
cannot clear is left as drawn, and `path.crossings` and
`bodyFindings(rack, ctx, nameOf)` report it as `crosses-body`, with a
sentence. It warns and never refuses. `inspect` of a cable gives them as
`route.crosses`, `describe` adds a `Findings:` line when a route context is
given, and `cableScheduleRows(..., { bodies })` writes each sentence into its
cable's notes. **Routed lengths change in 0.11.0** wherever a detour is added,
and beside a zero-U PDU. Most of the change is a cable from a port on a
device's far panel: it now goes round its own device to the lane instead of
through it. On a two-post rack, where every rear port is the depth of its
device behind the one rail plane, that is most rear routes; on a four-post,
few.

The automatic route (`autoRoute`) runs a patch whose two ends leave through
one manager along it, port to port, through the rings whose centres lie
between the two ports, in order from end a, and never out to a gutter and
back. With no ring between, it goes through the ring nearest the middle of the
two ports (end a's side of two as near), the nearest one it passes through
when one does, so it is never direct; a cord that can pass none is reported
by `ringFindings`. A manager with no ring along its run, but a duct, runs it
in the duct. Any
other route takes a gutter chosen from both ends: the side both ports stand
on, or, when they stand on opposite sides of the centre line, the side whose
path (`routePath`, detours included) is the shorter, end a's on a tie or
when a port is not found. The side is decided once per rack, route context
and cable, so a page must not change a route context in place: build a new
one when what it reads changes. **Routed lengths change in 0.12.0** wherever the
two ends share a manager or stand on opposite sides; every change found so
far is shorter.

A cable leaves the far end of its plug, not the port face (#960). Since
0.13.0 each path starts and ends at the plug's **reach point**: the port's
point moved out of the face it is seen from (+z at the front, -z at the
rear) by the plug's reach, a point `at: 'reach'` with its `end`. The reach is
`ctx.plugReachOf(end, cable)` in mm when the page gives a number of 0 or more
(the far end of the plug seated there, an optic's standing-out included: the
`z` of relief.js `cablePoints`); else `PLUG_REACH` by media, the cable's own
plug and boot as the library models them: 27.6 for LC fibre, 39.4 for copper
(and a cable with no media; it assumes the boot abuts the plug, so it may err
long by a few mm), 64.8 for a DAC or an AOC. The first and last legs,
their detours included, run from there, so a cord that has to clear its plug
before it can turn round a tray's front edge is measured that way, and a
drawing that starts its tube at the reach point finds nothing more to go
round. The plug was always along the first leg; the reach turns that leg
into a dog-leg rather than adding the plug again. **Routed lengths change in
0.13.0** on every routed cable, almost all longer: by what the dog-leg out of each plug adds,
and by far more where the reach puts a leg over a tray floor.

A routed length is the path plus an **end allowance** at each end, by the
cable's media (#962, docs/cable-lay-design.md section 1.6).
`END_ALLOWANCE_BY_MEDIA` is the sourced table, in metres an end (its name
since 0.18.0; no figure changed): only what is physically there and not in
the path, the part of the plug inside the port and half the maker's short
tolerance. It is 0.0131 for LC fibre, 0.0345 for copper and a cable
with no media, 0.025 for a DAC and 0.0524 for an AOC. Service loops and
dressing slack are explicit slack held in a tray, never part of the table.
Four of its inputs are estimates, not maker's figures (the LC and RJ45 plug
depths, the AOC's tip-to-tip reading and the copper tolerance), and section
1.6 lists them.
Until a tray can hold slack (#949 step 4) the kit adds a **temporary
dressing allowance** of 0.1 m an end on top, for every media. It has no
maker's source, it is not exported, and it goes when step 4 lands.
`endAllowance(cable)` is the two together, what a length adds an end
(0.1131, 0.1345, 0.125 and 0.1524), and `routePath` returns it as
`allowance`, which `pathLength` adds. **Routed lengths change in 0.16.0** on
every routed cable, where it was 0.15 m an end (`END_ALLOWANCE_M`, gone):
73.8 mm shorter for LC fibre, 31 for copper, 50 for a DAC, and 4.8 mm
longer for an AOC.

A cable rests on what holds it up (#949 step 3, docs/cable-lay-design.md
sections 2 and 3). A tray is a pathway with a floor: rack.json lists each
device's `trays` (its floor, the height of its top, its plate, its tie slots
and the openings of the rings standing on it), `solidsOf`'s sibling
`traysOf(rack, ctx)` places them, and a route names one by its id as it names
a ring (`{item, via: 'tray'}`; `pathwaysOf` and the `cable.route` refusal list
them). Since 0.14.0 a ring on a tray holds the cable on its sill, the cable's
radius above the opening's lowest inside edge, at the side of the opening
nearer the rail; a tray waypoint lays the cable along the floor at its radius
between its neighbours, or, where the page pins the held face
(`ctx.trayFaceOf(cable, {item, via})` returns `top` or `underside`, named in
the frame of the part, and the tray has tie slots along the stretch),
strapped under the plate at the plate less its radius, sagging between two
straps no lower than the strap line. Every other leg that is not held is a
**free span**: it hangs by the catenary the 3D drawing uses, scaled by the
`DRAPE` of its family (fibre and AOC 1, twisted pair 0.5, DAC and power 0.35)
and no tighter than its installed bend radius over its drape
(`ctx.bendOf(cable)` when given, else its media's; the family is its type's
when the page gives the cable types lookup as `ctx.typeOf`, else its
media's), and where it would pass
below a surface (a tray's floor, the top of any body) it drops onto it in two
bends of that radius and lies there. A leg into or out of a detour, a
lane's run along the frame, a plug and a ring's inside are not free spans,
and a sag that would carry the cable into a body is not laid. The new points
are `at: 'tray'` and `at: 'rest'`, and `path.rests` (and `inspect`'s
`route.rests`) lists what the cable lies on. **Routed lengths change in
0.14.0** on every routed cable through a ring on a tray, which now rests
lower and further out (a cord from the device below a lacer goes round its
front edge to reach it), and on every cable with a free span, by its hang.

A ring is solid round its opening (#968, docs/cable-lay-design.md section
3.3). Where a ring's contract says what of its loop is solid (`wall`,
`height`, `slit`, with `sill`, `depth` and `aperture.at`), rack.json's
`solids` carry its legs, its bar, its seat and, over a slit, its hook, named
`ring/<id>/<part>` (`rear-leg`, `front-leg`, `hook`, `bar`, `seat`), and
`solidsOf` places them with the other solids. A cable passes a ring close by
on purpose, so `legCrossings` and `detour` meet a ring's part with the
cable's tube, the part grown by its radius; so is a zero-U part (a PDU
standing in the gutter), whose corner a leg to the lane beside it passes close
by, so that no leg runs across its outlet face. Every other body is met by its
centre line. Since 0.15.0 every pass through a ring whose opening is
placed starts and ends at an **approach point** on the run outside the ring's
band, the cable's radius and `CLEAR` past it, at the opening's height and
across position (`at: 'approach'`); a detour or a leg from behind or below
ends there, so the cable enters through the opening, and a ring the route
would double back at is gone to as far as that point. `bodyFindings` names a
ring's part ("c9 passes through CM-01 ring 3 front leg ...: route it into the
ring along its run, through its opening."). **Routed lengths change in
0.15.0** on every routed cable through a ring on a tray, and beside a zero-U
PDU. On the reference rack of #949 they grow 2 to 38 mm. On generated racks
they move by up to about a tenth of a metre either way, and the figures
depend on the layout: one sample of 3,120 cables (one layout and seed) gave
89 mm shorter to 131 mm longer, median 10 mm longer, 67 stock sizes up and
67 down; an independent sample of 3,962 cables gave 94 mm shorter to 94 mm
longer, median 4.5 mm longer, 67 up and 27 down. A route is longer where a cable
now goes over a ring to its approach point, or round a PDU it grazed, and
shorter where a detour that went round a tray's
front edge to a ring's face can end at the approach point by a shorter way.

A path leaves every turn room for its cable's bend radius (#973,
docs/cable-lay-design.md section 3.4). The path is the cable, so its corners
are its bends, and since 0.17.0 `routePath` places its points for the
cable's own installed bend radius (`ctx.bendOf(cable)`, else its media's),
judged by `cornersOf(points, {share: 'need'})` from
`@portrayal/kit/rack/route-path`: the room a corner's legs leave it, a leg
between two corners shared by what each turn uses of it (`cornersOf(points)`
alone shares it by halves, as the bundle check does, and
`@portrayal/kit/rack/bundles` still exports it). Where the route turns onto
a ring's run its **approach point** stands the bend radius from the band,
not the cable's radius and `CLEAR`; a cable whose port stands behind that
point is led square to it through a **lead point** (`at: 'lead'`, with the
ring's `item` and `via`), and one whose first turn needs more leg than its
plug gives runs on straight out of it to a lead point with its `end`. A
detour's planes stand two bend radii from each end (`detour`'s new `room`
option), and a free span is sampled evenly along its arc and hangs only as
deep as the corners beside it have room for, so `at: 'rest'` points are
fewer and further apart. What the kit's rules find no room for is still routed,
and is said: the path's `bends` lists each corner short of the radius, `{
kind: 'tight-bend', cable, point, between: [from, to], at: [x, y, z],
angle_deg, legs_mm, room_mm, need_mm, short_mm }`, and `bendFindings(rack,
ctx, nameOf)` gives them rack-wide with a sentence, as `bodyFindings` does
for crossings: where ("c9 turns 129.7 degrees between its port on LEAF-B and
CM-01 ring 3") and by how much ("with room for a 19.2 mm bend; the cable
(aoc) needs 30 mm, 10.8 mm short."). A page that draws the kit's points can show them as they are.
`inspect` of a cable carries them as `route.bends`, `describe` counts the
cables that have one on its `Findings:` line and names the worst, and
`cableScheduleRows(..., { bends })` writes one sentence into each such
cable's notes; `layNotes(rack, { bends, covers })` gives the same as one line
a cable, for a file with no row for one. Corners at one point, to a tenth of
a millimetre, are one finding.

**Also in 0.50.0: a body piece carries a side drawing, and a fitted piece follows its field.**
A piece in `body.boxes` that `shows: [left|right|top|bottom]` is painted on that side with the patch
of the part's own `body-<side>.svg` it lies under (`pieceArtCrop` in `relief.js` gives the frames;
`components.json` publishes each drawing under `body.drawings` with its viewBox origin as `at`).
A piece with `when: {field: [options]}` is built only while the part's drawing shows a node for one
of those options (`pieceFitted`, `shownOptions`), so `setFields` on the part's path fits or removes
it, and the scene is rebuilt as for any field that shows a node. `svgCanvas` takes an optional
density, `pxmm`. A page that does neither changes nothing. `kit/component.html` opens one component
in the 3D viewer with camera presets and its choice fields.

**New in 0.50.0: a card two slots wide** (docs/pcie-two-slot-bays-design.md). components.json gives a
part wider than one slot `slot-width` and a nested bay the siblings it can cover, `span`. A card
`n` slots wide seats only in a bay whose `span` names `n - 1` bays, and only while each of them holds
nothing; it is drawn in the box those bays make together (`spanBox`, which `bayTransform` now uses),
and the bay it covers is marked `data-covered-by` its bay on the face (`markSpan`). `spanWhy(path,
ref, {holds, comp})` gives the sentence a refusal says, and `coveredBy` the card's bay. `acceptSwaps`
refuses both claims on one pair and returns `why`, by key; the rack's `fit` says which bay to empty;
`slotTree` lists `covers` on the card's bay and `covered-by` on the covered one; and the explorer's
inspector disables a covered bay's select and a two-slot option over a full bay. **A rack file does
not change**: a two-slot card is a swap in its bay and `""` in the bay it covers, so an older kit
reads it, centres the card on its own bay and does not refuse a fill of the covered one.

**New in 0.49.0: the kit reads a list of dist roots, so an overlay library sits on top of Portrayal's own.**
`loadSlots([publicDist, overlayDist], refs)`, `loadCatalog([...])`, and `dist: [...]` for `createShell`
and `createViewer` take a list where they took one root (`kit/dist.js` `layeredDist` and `readIndex`);
`kit/index.html?overlay=<path>` loads one in the explorer. A later root adds devices and parts, and an id
in two roots is an error naming both, never a replacement. A single root works as before.

**New in 0.48.0: a passive panel in a bay of a module in the device's bay has an end on each panel.**
`seatedPort` answers for a holder seated in a drawer's slot (`drawer/module/slot-1/module/sc01`, front) and
shows its back on the other panel (`.../b01`, view `rear`), as it does a panel in a bay of the device. A bay
of a module is spoken for by its own path, since a configuration that fills a drawer's slots does not name
the drawer. `cable.add` and `cable.update` refuse an end on a port a passive panel (class `adapter-panel`)
does not have, on the wrong panel, or on the rear of a panel with no rear, with the loose-end sentence
(`seatedEndReason`). `freePorts` lists the far ends of a panel in a drawer from the catalogue (`backEnds`),
since no panel of the device draws them.

**New in 0.47.0: a display in a rack shows text, digits or an image.** An item and a part beside the
rack take `displays`, a map of the path of a display to `{text: [lines]}`, `{digits: "04"}` or
`{image: <data URL or library asset>}`, as `states` takes a state. The rack file's version and schema do
not change: a reader that does not know the key keeps it. `display.set` sets and clears one, and refuses
a part that is no display (naming the ones it has) and content the display cannot take; a text cut to
the display's columns and rows, and a picture fitted with bars, are said (`display.set`'s `findings`,
`displayNotices`). `displays(rack, ctx, {item})` in `rack/queries.js` lists which parts are displays
and what each shows; `inspect` of a device lists the same. `rack/displays.js` has `displaysOf`,
`displayRefusal`, `displaysFor` (the map to hand a drawing) and `displayNotices`; `displays.js` has the
rules (`contentRefusal`, `layoutText`, `layoutDigits`, `imageInfo`, `fitImage`, `loadDisplayImages`) and
the one painter both halves use (`paintDisplays`). A page draws it with `shell.setDisplays(map)` and
`viewer.setDisplays(map)`: in 3D the content is in the texture the window is painted on, flat, so the
relief and its batches are as they were. [`docs/display-content-design.md`](../docs/display-content-design.md)
is the design. **A page that vendors the kit hands both `displaysFor` of each entry, and changes nothing
else.**

**New in 0.46.0: a cable end on a view or port a seated part does not have is refused when it is added.**
`cable.add` and `cable.update` (and so a dry run) refuse an end under a bay whose seated part is known and has
no port at that path on that panel, with the sentence the loose-end finding gives (`bay-4 holds FHD-FAPM6-RJ45,
whose port p1 is on the front panel; give view "front"`), and so does a made-up port of a passive panel
(class `adapter-panel`) or the rear of a panel with no rear. A part's rear face is listed by `freePorts` from the
reader of the rear panel, as for any panel. `partName` falls back to `attrs.model` before a raw ref.

**New in 0.45.0: every lamp and digit a drawing declares can be set in a rack.** `configs[].states` lists
what each configuration's faces declare (`data-states` on a `data-path`): `led-sys`, `psu-0/module/status-led`,
`led-port-0/lamp`, `status-display/digit-1`, `breaker-a/rocker`, an outlet's lamp, as well as the outlets.
`state.set` and `statesFor` take any of them and refuse the rest, naming what the device declares;
`inspect` of a device gives `settable` (grouped by vocabulary) and `states` (what it is set to).

**New in 0.44.0: a cable ends on a port of a module in a bay of a part beside the rack.** `zeroUEnds`
lists the connector slots of the module each bay of a zero-U part holds, as `<bay>/module/<port>` (a
vertical PDU's network card: `network-module/module/eth0`, `usb-0`), placed on the part by the bay's
`at` and the slot's `mate`. `cable.add`, the route, `freePorts`, `inspect` and the exports follow.

**New in 0.43.0: the 3D relief is built and drawn in batches.** `relief.js` rasterises a drawing once
however often a face asks for it, keeping each raster by what decides its pixels (`rasterKey`; see
`rasterSource`, `setRasterBudget`, `clearRasterCache`, `rasterStats`). Once a face is built,
`batchRelief` shares equal textures and materials and merges the meshes that share a material, a part
(`userData.portrayalPath`) and a frame. A host that styles only some parts by path names them with
`ctx.parts(path)` to merge the rest across parts; `ctx.batch: false` builds a face as before. A USDZ
now carries the relief boxes it used to leave out. **A page that vendors the kit changes nothing to
keep its hover, dimming and covers; passing `parts` is optional.**

**New in 0.42.0: a power cord reaches a vertical PDU's outlet from beside it.** A leg that lands on the
outward face of a zero-U part is taken in past the side that faces the rails, at the outlet's height,
and no longer over the top or under the foot; the crossing finding does not count the body of the part
a cable ends on, at that end; and a four-post offers `left-rear-inner` (and `right-rear-`, `left-front-`,
`right-front-`) between a rail and a part beside it, listed by `waypointLanesOf(frame)` and `inspect`'s
`lanes`. The routed length of such a cord follows. **A page that vendors the kit re-vendors it, and
changes nothing else.**

**New in 0.41.0: the 3D build looks ids up from a map.** `cablePoints` and `extractRelief`
(`relief.js`) found each cable point's feature and each cavity's node with a selector per lookup.
Each now reads an id map (one per drawing, or per marker host), with the same results, warnings and
first-match order; the gain is in a drawing that is not attached to the page. **A page that vendors
the kit changes nothing.**

**New in 0.40.0: an estimated duct capacity says it is an estimate.** A stored loop in a part whose
capacity is an estimate (`attrs.performance.cable-capacity-estimated`) reads "an estimated 54 cat6
cables' worth" in `cable.slack` and its findings (`spare-capacity-estimated` within the count), and
`inspect` and `rack.json` carry `capacity.estimated: true`. A part that states none keeps
`spare-capacity-unstated`. **A page that vendors the kit changes nothing.**

**New in 0.39.0: fixes to spare in ducts.** `cable.slack` refuses an amount larger than the cable's
spare (what is already stored counts toward it) and any spare on a short cable, and says how much
spare there is or how short the cable is. A duct's cable count is the cable's own kind: a fibre cable
is not counted against a count of Cat6, and a finding says so. A route summary names a window the
route goes through (`windowsOf` in `rack/route.js`), and names a part beside the rack by its label
and, where another part shares the label, its id. **A page that vendors the kit changes nothing; a
`cable.slack` that was accepted may now be refused.**

**New in 0.38.0: a cable ends on an outlet of a zero-U PDU.** An end may be `{item, path, view}`
on a part beside the rack (`item: 'z3'`, `path: 'outlet-a2'`), on one of its own connector slots.
The commands, `settleEnds`, the routes, `freePorts`, `inspect` and the exports find it as they find
a port of a device. Its place is the slot's `mate` in `configs.json`, so **a route context needs
`slotsOf` and `compByRef`** (what `loadSlots` returns) to measure a cord to it; without them the
cord has no length, as for a port not found. `freePorts(rack, 'z3', ctx, {type: 'C39', near: 35})`
lists the free C39 outlets nearest U35. A page that draws cords reads the plug each end takes from
the settled facts (`info.plug`): at a slot that takes two, it pairs with the far end's plug.

**New in 0.37.0: an agent is told what a person sees** (P-0018). `describe`'s `Findings:` line now counts
the cables whose route would enter and leave a ring by one face (`2 cables enter and leave a ring by one
face (c1, c2)`) and the cords shorter than their route needs (for example `2 cords are shorter than their route needs (the
worst c2, 1.14 m short)`), as the Warnings panel does; `inspect` of a cable carries `route.ring_findings`, a list of
`{item, via, text}`, from the new `ringFindingsOf(rack, cable, ctx, nameOf, path)` in `rack/route.js`
(`ringFindings` is now one call of it for each cable); a short cord was already in its `spare_findings`.
A bend of one turn that is at a stop of the route has `stop`, that waypoint, in `routePath`'s `bends`, in
`bendFindingsOf` and in `inspect`'s `route.bends`, and its sentence names it before the two stops either side
(`c1 turns 90 degrees at right-front U20, between lacer ring 1 and right-front U30, with room for ...`); a corner in a
lead or a detour has no `stop` and reads as before. `cable.lay`, when the routes are known, refuses a
`position` past the number of cables whose routes pass through the pathway, and one for a cable that does not
pass through it, and says of a face on a ring or a duct that it is one. **A page that shows a bend's sentence
shows the new wording without a change; a page that lists a cable's findings adds `route.ring_findings`; the
text of `describe` has two new clauses, and a page or an agent that parses it adds them.**

**New in 0.36.0: a cable crosses a vertical manager through its back windows** (P-0016). A cable
routed front to rear past a full-height vertical duct used to go over the top of the duct, because
`legCrossings` judged a window on the plate grown by the cable's radius, where no cable fits. A window
is now judged on the true plate, so a cable at a window's height crosses straight, and `waysRound`
tries a zero-U part's holes, nearest first, before its top or bottom edge, so a cable routed at a
height with no window crosses at the nearest window. Horizontal managers are routed as before.
`pointOf` also puts the duct waypoint of a narrow rack-face part on a rail (the CMV-5U3W) on the
part, where it was at the rack's centre. **A page that vendors the kit changes nothing; the cables
through a vertical or the 5U bracket measure shorter or longer, as they are really laid.**

**New in 0.35.0: spare in a finger duct, and a part beside the rack in a route.** `cable.slack`
stores a cable's spare in a duct its route uses, a horizontal manager's, a rack-face bracket's or a
vertical manager's beside the rack, as well as on a tray or at an end. `SPARE_HOLDS` in
`rack/slack.js` is the one rule for which pathway kinds hold spare. A refusal says where the spare
can go (`whereText`). A duct is counted against the capacity its part states (`spareLoad`), and
`spareMarks(rack, cable, ctx)` gives the point, in rack millimetres, a page draws each stored loop
at. A route may name a zero-U part's duct (resolved as the lane run through it) or a window
(`pass-through-N`), and a pathway by its spoken name (`pathwayId`); `routeText` takes a fourth
argument, `ductsThrough(rack, chassisOf, nameOf)`, to say a lane run goes through a duct.
**A page that draws stored spare calls `spareMarks`; one that does not changes nothing.**

**New in 0.34.0: a power cord is drawn at its own diameter** (#1060). Every cable was drawn `WIDTH`
(3 mm) wide, so a power cord, 7.1 mm, was a thin line going into a plug stub drawn at the cord's real
size. `widthOf(cable, diameterOf)` in `rack/cable-geometry.js` answers the width to draw a cable at:
for media `power` its type's `od_mm` (`diameterOf` is the cable types lookup, `diameterLookup`),
else 7.1 mm, the `power-c13` cord; for every other media `WIDTH`, as before. **A page that draws a
cable at `WIDTH` and wants the cord to meet its plug calls `widthOf` instead; a page that does not
changes nothing.** The site's `cables.js` (2D strokes, 3D tubes) and the bundle views are such pages.

**New in 0.32.0: a replaced part leaves a redirect** (#1049). A rack file names parts by ref, and a ref whose
major was removed no longer resolves: the slot refuses it, the swap is ignored,
a cable on the part's ports goes loose, and the next edit that writes back what
a slot accepts drops the entry. The library now says, on the **replacement**,
which removed refs it stands in for (`supersedes` in its contract). The build
publishes the list on the replacement's `components.json` entry, with the
signature of the removed part's published form that proves it a drop-in (the
same part ids, port paths and names); a replacement that stops being one stops
the build.

`rack/catalog.js` `loadSlots` reads it into `redirects`, beside `slotsOf` and
`compByRef`; hand `redirects` on in the same context (`{ ...slots }`).
`redirects.follow(ref)` is the ref to read: the replacement of a removed ref,
the ref itself otherwise (one hop, or a chain, never a loop; a `:suffix` is
kept). With the context:

- **Reading follows and changes nothing.** `inspect` lists the parts a slot
  holds as the replacement, says in `notes` that the old ref was read as the
  new one, and gives `redirected: [{ path, from, to }]`. Ports, cables, the
  exports and `fit` read the same way. **A plain load and save is
  byte-identical:** `createRackEditor(...).loadDoc(doc, { ctx })` says what it
  reads as what, in its findings, and the document is not touched.
- **The first edit that lands writes the new refs, and says so.** `apply`
  rewrites every redirected swap of every device and part beside the rack, in
  the same step as the edit (one undo takes both back), and the first finding
  of the answer starts "This rack named refs the library has replaced, and the
  edit wrote the new ones". An edit that changes nothing, one that is refused
  and a command that is no step (`dcim`) write nothing. `patch` with a whole
  `swaps` map follows before it asks the slot, so an echo of what was read is
  kept, not dropped. `fit` with an old ref fits the new part.
- **A ref that is gone and redirected nowhere is kept and named.** `inspect`
  gives `unknown: [{ path, ref }]` and a note ("... is no longer in the
  library; it is kept as written"); `patch` keeps the entry, and what is seated
  under it, instead of leaving it out as a ref the slot does not take. It is
  never replaced by the slot's default.
- **No redirects in the context, none followed.** A context without
  `redirects`, or a `components.json` from before the key, behaves as before.

The page that writes back only the swaps its own slots accept (the Explorer's
lens) is the site's, and is not changed here: it drops an old ref on its next
write until it passes `redirects` on.

**New in 0.31.0: a cable's colour.** A cable was drawn in the colour of its
media and nothing could change it. It is now drawn, in this order, in:

1. the colour stated on the cable itself, `color` in the rack file;
2. else the jacket colour of its two seated ends, when both state one and
   the two agree;
3. else the colour of its named cable type, where the table gives the type a
   `jacket`;
4. else its media's, from `COLORS` in `rack/cable-geometry.js`, as before.

**No default changed.** Every media is the colour it was (an AOC is still
`#3a3f45`), so a rack that states nothing is drawn as it was. `COLORS` is
the one table that holds those colours; `JACKETS`, the hero's table, now
names entries of it and holds no colour of its own.

- **A colour is hex**: `#` and three or six hex digits, in either case, as
  `jacket-color` is written on the cable ends of the library. `hexColor(v)`
  gives it as `#rrggbb` in lower case, or `null`. A name (`red`), a CSS
  function or a number is not a colour, and is never drawn as one: the next
  rule of the order decides.
- **The cable's own.** `cable.add` and `cable.update` take `color`; `null`
  or `""` clears it, and anything that is no colour is refused with
  `COLOR_REFUSED`. `parseColor(text)` is the same rule for a form: `{ ok,
  color }` or `{ ok: false, reason }`. A file's `color` that is no colour
  moves, whole, to `colorAsWritten`, as a length does.
- **The ends.** `seatedJacket(item, end, ctx)` in `rack/ports.js` reads what
  the part seated in the port states, from the parts lists `loadSlots`
  returns. **A default is not a statement.** Every generic cable end
  declares `jacket-color` with a default (`#1c1c1c`), and if that counted
  every cable between two of them would turn black. An end states a colour
  when the rack sets the field on that part (`fields` of the item, at
  `<port>-occupant`; the default's own colour, chosen, counts) or when the
  part itself gives its jacket one (a maker's part that composes the generic
  end). One stated end and one bare end, or two that differ, settle nothing.
- **The type.** `loadCableTypes` returns `typeColorOf`, and
  `jacketLookup(types)` builds it over a table in hand. It reads only the
  type a cable names in its own `type`, never the bare type of its media.
- **The answer.** `cableColor(link)` is `{ color, from }`, `from` being
  `cable`, `ends`, `type` or `media`; `colorOf(link)` is the colour alone.
  `cablePlan(rack, readers)` and `cablePlan3d(rack, readers)` put what
  decides a colour on each link (`color`, `jackets`, `typeColor`, each only
  when it says something), so `colorOf(link)` is the colour to draw.
  `cableColorOf(cable, readers)` answers for one cable of a rack.
  `readers` is `{ jacketOf, typeColorOf }`.

**What a page does to show it:**

```js
import { cablePlan, cablePlan3d, colorsKey } from '@portrayal/kit/rack/cable-rules';
import { colorOf, bundleColor } from '@portrayal/kit/rack/cable-geometry';
import { jacketsFor } from '@portrayal/kit/rack/ports';

// parts: what loadSlots returned; ends: the Map the page's cableFacts reads;
// types: what loadCableTypes returned
const readers = { jacketOf: jacketsFor(rack, { ends, parts }), typeColorOf: types.typeColorOf };
for (const link of cablePlan(rack, readers).links) draw(link, colorOf(link));
```

- Pass the same `readers` to `cablePlan3d`. `sameCables3d` sees a cable's
  own colour change; a jacket set on an end changes no cable, so a scene
  that keeps its tubes also compares `colorsKey(rack, readers)`.
- A page that reads an end's jacket off its drawing says so with a `jacket`
  key on that end's entry of its cable facts: a colour, or `null` for an end
  it found bare. Where the key is there it stands; where it is not, the
  parts lists answer.
- `bundleColor(colors)` is `{ color, mixed }` for one band drawn for a whole
  bundle: the members' colour when they are all one, else `color: null` and
  `mixed: true`. The kit picks no colour for a mixed bundle.
- `drawioCables` gives a cable whose colour is said (rules 1 to 3) a
  `color`, and the kit's draw.io writer draws it ahead of its media's entry.
  A page's own `cableStyle` function is handed the row and reads `color`
  there. Pass `typeColorOf` in its options for rule 3.
- Both DCIM cables files fill their `color` column with the cable's own
  colour (rule 1 only), six digits with no `#`. The Nautobot file is read by
  the import script that goes with it (`import_cables.py`), which has to
  pass the column on.

A colour is no part of a lay: nothing in `rack/route.js` reads it, and
giving a cable one lays nothing again.

**New in 0.30.0: a power cord, a DC feed and a ground wire can land.** A
cable landed only on a part of class `port`, and no power end is one: an
inlet, an outlet and a DC terminal are class `inlet`, a ground stud class
`ground`. The rule is now one function, `cableLandsOn({ cls, slot },
compByRef)` in `rack/cable-rules.js`: **a part of class `port`, or a connector
slot (`kind: 'connector'` in `cages[]`) that accepts at least one part of
class `port`**, which is what every cord end and lug is. A pluggable cage, a
module bay, a guard seat and a slot that accepts nothing do not land
(`takesCableEnd(slot, compByRef)` is the slot half). The design is
[docs/cable-ends-design.md](../docs/cable-ends-design.md).

- **The address of such an end is the path of its slot**:
  `{ item, path: 'psu-1/module/inlet', view: 'rear' }`, `outlet-rear-3`,
  `ground`. An end saved to `<slot>-occupant` names the same port and still
  lands.
- **`media` has two more values, `power` and `ground`.** `power` is an AC cord
  or a DC feed (one cable; its type says which), `ground` a bonding wire.
  `MEDIA`, `MEDIA_LABELS`, `mediaKind`, `proposeMedia`, `DIAMETERS` (7.1 and
  6.3 mm), `PLUG_REACH` (77.0 for `power`), `END_ALLOWANCE_BY_MEDIA` (0.017
  and 0) and `COLORS` (`#1c1c1c` and `#3f9b4b`) each have the rows. The ground
  figures are estimates.
- **An end may state its plug**: `{ item, path, view, plug }`, a component
  ref, only where the slot takes more than one. `endPlug(slot, compByRef,
  stated)` gives `{ plug, choices, note }`: the one accepted end, else the
  stated one, else the first of `cableEndsOf(slot, compByRef)`, which sorts
  by `attrs['rating-a']` and then by ref. `plugSeats(path, slots, swaps, {
  cls, compByRef, plug })` seats it for a page that draws plugs. A derived
  plug is never a swap, a BOM line or an export row.
- **`receptacleOf(component)`** says what the part that presents a slot is:
  `{ family, mode, role }`, with `family` `power` or `ground`, `role`
  `outlet` or `inlet` where `attrs.outlet` or `attrs.input` says, and `mode`
  `ac` or `dc` where stated. `connectorName(slot, info)` words it: "C13
  outlet", "C20 inlet".
- **`mismatch` warns, as it always has, and refuses nothing**: a data cable
  into a power end, a power cable into a data port, power to ground, AC to
  DC, and two outlets or two inlets, each only where both ends state it.
- **`looseReason` reads two more facts**: `part` ("outlet-9 is NEMA 5-20R,
  which takes no plug or lug the library knows") and `side` (a slot on a side
  view, where an end cannot yet be given).
- **`freePorts(rack, id, ctx, { kinds })`** lists slot ends where the reader
  hands them in, each with `kind` (`power`, `ground`, `other`), `connector`
  and `plug`; the screws of one DC terminal carry `of` and the first
  `first: true`. `kinds: ['data']` is the ports alone. A port of class `port`
  is the same entry it was.
- **`zones.js`**: `readSvg(text, { ends })` and `readDrawing(root, doc, { ends
  })` read the part at each path in `ends` as a zone with `end: true` and its
  `ref`; `portsOf` includes them. `cableEndPaths(item, view, ctx)` in
  `rack/ports.js` makes the list. Without `ends` every answer is unchanged.
- **A device's own slots** (a PDU outlet, a chassis inlet) are settled in the
  kit from `configs.json` where a page read "drawn, and no port"
  (`ownSlot`), so they land with a page that has not changed, and only on the
  panel the item's configuration shows (`shownEnv`: a configuration's `views`
  names the panel of each face, and a slot of another build is not on it). `ctx.drawnAt(end)`
  is what a page adds: the ref of the component drawn at the end's path. With
  it an end says what it is and an outlet with no slot is named; without it
  nothing is guessed. **How a page names a part**, in the `holder.part` of an
  end's facts: by its `attrs.model`, else its ref's name in capitals
  (`celestica/psu-r3059-f8001@1` is `PSU-R3059-F8001`), exactly as the kit
  does. For a supply in a bay that only its default fills, the kit hears the
  page only where that name is the part the bay ships with; a page that hands
  in a ref for a part with no model is not heard, and the end stays loose.
  **A page supplies `drawnAt` before it offers power
  cabling**: without it an outlet-to-outlet or inlet-to-inlet cord between
  two devices' own slots gets no warning.
- **The DCIM cables file** leaves a ground wire out by name, and a power
  cable whose ends the type files do not name out with that reason; one they
  do name is written with a blank type and a note.

**New in 0.28.0: a bundle's straps are measured and placed on its cables.**
`straps(rack, bundle, ctx)` and `trunkLength` measured a trunk along the
straight line from one waypoint to the next. The members do not run there: a
cord passes a ring by its opening, hangs between a ring and a lane, and goes
round a body by a detour point. So a trunk was measured short, and a strap's
`{ segment, t }` named a place off the cables. Both now read the members'
routed paths (`routePath`).

- **Each strap carries its own place.** Beside `segment`, `t` and `along_mm`
  a strap has `point` (`{ x, y, z }` in rack coordinates, mm, to a
  hundredth), `dir` (the way the trunk runs there, a unit vector, or `null`
  where it has no length) and `on` (the id of the cable whose path the point
  is on). A page draws the strap at `point`, across `dir`, and needs no
  correction of its own. `segment` and `t` keep their meaning for a reader
  that has only those: the trunk segment between resolved waypoints
  `segment` and `segment + 1`, and the share of that segment's **routed**
  length the strap is along. On a segment whose cords do not run straight a
  place worked out from `segment` and `t` alone is still off the cable, as
  it was.
- **Which member.** The trunk is cut at every pathway and at every unit of a
  lane, and each piece is taken from the member in the middle by length of
  those that ride it (the earlier of two middles); members as long are put in
  order of id, by number (`c2` before `c10`) and then by the plain text
  (`c02` before `c2`). A strap goes round the whole pack, so it goes where
  most of the pack lies: one limp cord among stiff ones hangs lower and
  longer, and it sets neither the length, nor the count, nor the place.
  Three DACs and an AOC between two ducts 762 mm apart are measured as four
  DACs are. **An even split of two kinds goes to the kind that hangs
  less** (the earlier of the two middles is the shorter): two DACs and two
  AOCs are measured as DACs, and the two AOCs are then 50 mm and more off
  every strap. Where the member named changes kind from one piece to the
  next, at a ring where the riders change, the line steps sideways there by
  the difference of where the two kinds stand in the ring, up to about 3 mm
  (OS2 against Cat 6A; 2.12 mm for Cat 6, 1.41 mm for DAC, none for AOC or
  OM4). The order the cables or the members are written in plays no part;
  renumbering cables can change which of several like members is named, and with it a place by a few millimetres where they do not lie
  quite alike.
- **What `on` means.** The kit lays each cable on its own, so members of
  unlike kinds hang a little apart where a real pack hangs as one. A strap's
  `point` is exactly on the path of the member `on` names; members that lie
  like it are there too, and one that hangs otherwise is off it by the
  difference of the two hangs. Draw the strap at `point` only if the bundle
  is drawn on its members' routed paths.
- **Where no path can be read** (a port not found on its drawing), a piece
  is the straight line it was, a strap there has `on: null`, and it is said:
  `straps()` returns `straight: true` and a sentence in `notes`,
  `trunkLength` returns `straight: true` beside `metres`, `bundleExports`
  has `straight` on each record and the sentence in its `notes` (so on the
  sheet and in the schedule), and `inspect` carries both. The length and the
  count are then an estimate. A stretch of trunk that no member rides is
  straight too, and is not said: no strap goes there. **A readable minority
  sets the trunk**: where fewer than half of a stretch's riders have a
  path, the middle one of those is taken (one AOC with a path among three
  DACs with none gives the AOC's 946.8 mm and four straps), and that is
  said in the same places with `few: true` and its own sentence. The two
  are kept apart, on a `bundleExports` record too (`straight` and `few`,
  each always there, false otherwise): a straight line is the shortest the
  trunk could be, and a minority's figure can be over. **Exactly half
  readable says nothing**: two DACs with no path and two AOCs with one are
  measured on the AOCs, 946.8 mm and 4 spacing straps, with no note.
- **An error is let out.** A context reader that throws, or a path found
  changed under `ctx.checkKept`, throws from `straps()` and `trunkLength`
  as it does from `routePath`. `bundleExports`, `anchorsOf` and
  `strapTotals` keep their rule: a bundle that cannot be read is not
  counted. Before, such a bundle was counted along its straight lines, so
  **a total can now be lower than it was, and lower than the rack needs**:
  `bundleExports` gives `length_m: null` and `straps: null` for it, the
  BOM's strap line counts the rest, and `strapBomNotes` says "its route
  could not be read, so its straps are not counted". `strapTotals` returns
  `unread` (how many drawn bundles were left out) and `unreadBundles`
  (their ids), only when there are any; show them beside the total.
  `anchorsOf` returns a list and has nowhere to say it.
- **What the length now depends on.** A bundle's length and strap count
  move with whatever the lay of its members reads: their media and type,
  the cable types a page loads (diameter, bend radius, drape), where the
  ports are, and the solid bodies of the rack. The same trunk in Cat 6 is
  1.72 m on the rack below where in fibre it is 1.74 m. And `straps()` now
  lays every member when it is the first reader of a rack (0.1 to 0.2 s for
  that rack, where it took a few milliseconds); after any reader has read
  the paths it costs a few milliseconds.
- **The counts follow.** `straps().runs`, `along_mm`, `kinds`, `count` and
  `widths`, `strapTotals`, `trunkLength`, a bundle's `length` and `straps`
  in `inspect`, `length_m`, `straps`, `strap_kinds` and `strap_widths` in
  `bundleExports`, and so the bundle's line on the sheet and in the cable
  schedule and the BOM's strap line. A trunk that only runs along a lane is
  measured as it was. One that passes a ring, a duct or a tray, or goes from
  one lane to another, is as long as its cords, and takes a strap more where
  that crosses a multiple of the spacing. On the rack of
  `spec/tests/js/strap-path-fixture.mjs` (96 cords in eight bundles, four of
  them from a rear lane to a front one) the BOM's strap line goes from 74 to
  76 (4 more along the bundles, 2 fewer where a cable leaves, since a
  spacing strap now serves there), and the two bundles that go round a duct
  from 1.26 m to 1.74 m.
- **Not changed:** which tie slot an anchor strap is at, the widths, the
  bend check of a bundle (its corners are still the straight lines between
  waypoints), a single cable's path and length, and a saved rack: nothing
  here is stored.

**New in 0.27.0: a lead enters a ring it has room to turn into.** The
automatic route sent every lead through the ring of its manager nearest its
port. **Routed lengths on saved racks move:** a cable whose automatic route
takes another ring, or whose detour is laid another way, measures
differently the next time a page measures it, and its stock size can change.
An entered length is never touched, and a route made by hand keeps its
waypoints (the lay between them is the kit's, and can move). Nothing is
removed or renamed; the rack file and the export columns are as they were.
[`docs/cable-lay-design.md`](../docs/cable-lay-design.md) section 3.5 has the
rules and what was counted.

- **The ring is chosen by room, not by distance.** Of the rings on a lead's
  way to its gutter, the first that the lead can turn into within its
  cable's installed bend radius is taken, and one too close is passed over.
  A patch along one manager takes the rings between its ports the same way.
  Where no ring leaves room the nearest stands, and its finding says so and
  what would help, in a field of its own: `bendFindings` and
  `bendFindingsOf` give such a finding `advice` (one sentence) and
  `tooClose: { manager, device }`. Its `text` is the bend and no more: the
  advice adds nothing to it. `routePath`'s `bends` carry neither. **The gutter a cable takes does
  not change:** it is chosen first, measured as before.
- **A patch with no ring between its ports** takes, of the ring it took
  before and the nearest ring on each side, the one it lays best through
  (the tightest corner weighed first); on a tie, the ring it took before.
- **Two turns on one short leg are one finding.** A `tight-bend` that was
  two (an S-bend, or the two turns of a way out and back) is one, with
  `apart_mm`, the leg between the turns, and `turns: [{ point, at,
  angle_deg }, { point, at, angle_deg }]`. Its `at` is the middle of that
  leg, its `point` the first turn's, its `angle_deg` the wider of the two,
  and its `legs_mm` the leg into the first and out of the second; its
  sentence reads "turns twice within 22.8 mm ... (67.1 and 63.2 degrees)".
  **A page that counts `bends` counts fewer**, and one that rings each
  finding at `at` rings such a bend once; `turns[].at` are the two corners.
  `inspect` carries `turns`, `apart_mm`, `tooClose` and `advice`; a
  schedule's note says "bends" where it said "corners", and ends with the
  advice, once for each end's device. **A pair's sentence is longer than any
  bend's was** (up to 182 characters where the longest was 150), and most
  findings on a rack with lacers are pairs: a page that clips a label at a
  fixed length cuts more of them.
- **Round a tray.** `detour` in `rack/solids.js` takes two options, both
  off unless asked for: `loose`, which keeps the point where a way round a
  plate turns back in where pulled taut it would take a turn's room, and
  `rear`, which takes a floor's back edge first for an end that stands
  behind it (a device set back from its rails). `routePath` offers both
  where a corner at a detour point is short. A free span that leaves a
  surface over its edge has a point at the edge (`hang`'s `edges`, on
  unless asked off).
- A page's `plugReachOf`, `bendOf` and `diameterOf` are asked more often for
  a patch along one manager with no ring between its ports: the two rings
  are each laid once to choose.

**New in 0.26.0: a manager's stated count is a count of one kind of cable.**
`capacityOver(rack, ctx)` compared a manager's stated count with every cable
through it. A maker counts with one cable (thirty Cat6 is the section of about
a hundred and twenty 3 mm cords), so it now counts only the cables at least
as thick as the catalogue's `capacity.media`, by `DIAMETERS`: Cat6 and Cat6A
through a manager counted in Cat6, and a cable with no `media`, which `fill`
already takes as 6 mm copper. A fibre cord, an AOC or a DAC is not counted
there; the fill of the rings is the check for those. **This changes what a
page warns of, and the notes of the sheets, the cable schedule and the BOM.**
No rack file changes.

- An entry is `{ item, count, through, capacity, media, diameter }`: `count`
  of the cables counted, `through` of every kind, `diameter` the least
  diameter counted, in mm. A page that reads `item` alone reads what it did.
- `capacity.media` in `rack.json` has three shapes. A kind: compared as
  above. `null`: no source names the cable, and the count is never compared.
  Anything else, which is no key (a catalogue built before 0.26.0) or a
  kind this kit has no diameter for (a catalogue newer than the kit): its
  count is compared with the cables of 6 mm or more, so neither goes silent,
  with `media: null` in the entry. Only `null` means "never compare".
  **Take the library build and the kit together** to get the stated kinds.
- `fillNotes(rack, facts, nameOf)` names a manager with where it is, after
  the name `nameOf` gives: `LACER (U20 front)`, or `(at left-front)` for a
  part beside the rack. Two managers of one model no longer give one line.
  It reads `facts.ctx.chassisOf` where the facts carry a context: with it
  the U is right for a manager taller than one unit on a frame numbered from
  the top, and without it such a manager is named one unit off.
- The note of a pathway over its fill says both shares: `ring 1 on LACER
  (U20 front): 60 cables, 112% of its fill limit; the limit is 40% of the
  opening.` It said `guide-1 on LACER: 60 cables, 112% of a 40% fill.`
- The note of a manager over its count names the kind: `LACER (U20 front):
  31 cables at least as thick as Cat 6 copper through it, more than the 30
  Cat 6 copper cables its maker states.` With thinner kinds beside them: `31
  of the 36 cables through it are at least as thick as Cat 6 copper, ...`.
  Where the entry names no kind: `31 cables of 6 mm or more through it, more
  than the 30 its maker states.`, and with thinner kinds beside them `31 of
  the 36 cables through it are of 6 mm or more, more than the 30 its maker
  states.` A count of one reads `the 1 Cat 6 copper cable`.
- `inspect` of a manager, on the rails or beside the rack, gives `capacity:
  { count, basis, media }`, `media` null where the catalogue names no cable.
- `portLabel(path)` (`rack/cable-rules.js`) is a port in words: `bay 1 b09`
  for `bay-1/module/b09`. `tagText` uses it, so the tags a page draws, on
  the screen and on a sheet, change their words. `freePorts` gives it as a
  port's `label`, which read `bay 1/module/b09` for a port on a seated part.

**What a page must change.** A test that pins `% of a 40% fill.` or `more
than its stated` no longer matches. A page that shows the `label` of a
`freePorts` entry (an agent's tool, a picker) shows the new words. Nothing
else is asked of a page: `capacityOver`, `fillNotes` and `tagText` take what
they took.

The whole rule, with what happens for a mix of kinds, is
[cable-managers-design.md](../docs/cable-managers-design.md) section 14.

**New in 0.25.0: a large rack is read in a fraction of the time, and every
answer is the one it was.** No path, length, need, stock size, finding,
sentence, strap, spare figure or export row changes, and no name is removed
or renamed. On a generated rack of thirteen two-unit switches, a lacer on
each, two ducts and 300 cords, reading every cable's path took 36 s and
takes 0.6 s; reading them again took 2.2 s and takes 3 ms; and each
rack-wide call after that (`bendFindings`, `coverFindings`, `ringFindings`,
`bodyFindings`, `fill`, `capacityOver`, `spareOf`, `anchorsOf`) took about
2.2 s and takes 3 ms or less.

- **The lay of a cable is kept, not only what was chosen for it.** A second
  read of a rack in the same context lays nothing. A context **made anew**
  that answers as the last one did lays nothing either (26 ms for the
  300 cords, where it took 36 s): the kit keeps each lay under what the
  lay read (the cable's ports, its diameter, reach, bend radius and drape,
  its route and every waypoint's point, ring and tray) and under the solid
  bodies, trays and lanes of the rack, all compared by value. So a page
  that builds its context anew on every draw and every tool call pays for
  a lay once.
- **An edit to one cable lays that cable.** Another cable added, removed,
  moved or edited, a label, a purpose, a length or a slack entry changed, a
  rack renamed: no other cable is laid again (26 ms after one cord moved to
  another port, where it took 36 s). **A device placed, moved, turned or
  removed, a part beside the rack, or the frame's height or depth lays
  every cable again** (0.6 s), the ones nowhere near it too: a detour
  or a hang can reach round any body, and the kit does not record which
  bodies a lay never came near.
- **What a page holds to.** A rack and a context are made whole and not
  changed, as before; a context changed in place now gives the path that
  was laid before the change, whole (it gave a mixture). The lays are kept
  at each cable's end `a`, the object, so an edit that keeps the objects of
  the cables it does not touch (as `apply` and every command do) carries
  them over; a rack read again from its file is read for the first time.
  They are held weakly, and go when the rack's cables do.
- **`ctx.checkKept: true`, for a page's tests.** With it on the route
  context, `routePath` and every reader of a path lay the cable again from
  a copy of the rack, the cable, its ends and the context, compare the two,
  and throw an error that names the cable and `ctx.checkKept` where they
  differ: a rack, item, cable or end changed in place, or a context that
  answers otherwise than it did. It lays every cable on every read, so it is
  for tests and development, not for a page in use; without it the kit pays
  one look at the context a read. It does not see an end put on the same
  cable object under a new context where both lays come out alike.
- **`routePath` hands out a copy** of the path kept, and `resolveRoute` its
  own lists, so nothing a caller does to one reaches the next reader. The
  findings do the same.
- **`spareOf(rack, cable, ctx, path)`** takes the cable's `routePath` as a
  fourth argument, for a caller that already has it; without it the path
  kept is read. `bendFindingsOf` and `coverFindingsOf` already took one.
- **What was slow.** A leg was tested against every solid of the rack, each
  box read through six built strings and a regular expression: the solids of
  one device are now under one box, and a leg that stays out of it tests
  none of them. A span asked every surface of the rack for the ground under
  each of its sixty points, and every span of every cable was tested against
  every port of the rack: each now asks only what is near. The side of a
  route was measured by laying the cable down both gutters and then laying
  it again down the one chosen: the lay that was measured is the lay.
- **What is as it was.** A cable is still laid from both ends and one lay
  kept (0.21.0). No rule was found that says, without making the second lay,
  that it would not be the better one.

`spec/tests/js/rack-speed.mjs` holds the kit to this: a digest of every
answer for 91 racks and 3,911 cables, recorded from 0.24.0, and budgets for
a first read, a second, a new context and one cable moved at 300 cords.
`spec/tests/js/speed-bench.mjs` prints the table.

**New in 0.24.0: the DCIM cables files hold the cables on a panel or a
cassette.** A cable on a fibre port of a module seated in a bay was left out
of both files, because a module type does not name such a port by its part.
**This changes what the export holds.** No column, type file or rack file
changes, and a rack with no cable on such a port exports the files it did.

- The build publishes `optical.ports` in `components.json`: for each fibre
  part of a module, the front or rear ports of its module type that the part
  is, one name a position. `fibrePorts(item, end, ctx)` in `rack/ports.js`
  reads it for a cable end. The kit derives no name.
- `resolveEnd` takes that answer as `ports`, checks every name against the
  type file of the target, and answers `names` beside `name`: a duplex
  adapter on a front is two front ports (`bay-1/1`, `bay-1/2`), an adapter
  on a back one rear port (`bay-1/B01-1`), a trunk connector one rear port
  (`bay-2/MTP-1`). `endResolver({ rack, ctx, deviceOf, moduleAt, consolesOf })`
  returns the `resolve` that `cableImportRows` is handed; `ctx` is the parts
  lists that function takes as `parts`. **A page gets the new rows by
  calling it**: `resolveEnd` called as before answers as before, and those
  cables stay out, with the reason.
- NetBox: one row a cord, both names in the name cell, separated by a comma.
  Nautobot: where both ends have two ports, one row a fibre, first port to
  first port, the label followed by ` (1/2)` and ` (2/2)`; where the other
  end is a single port (an interface, a rear connector), one row to the
  first of the two, and a note names each port left without a cable.
  [`docs/optical-paths-design.md`](../docs/optical-paths-design.md) has the
  table, and what NetBox 4.7.2 and Nautobot 3.2.6 accepted.

**New in 0.23.0: a port on the back of a seated part.** The rear adapters of
a patch panel and the trunk connector of a cassette take a cable. Nothing is
removed, and the rack file and the export columns are as they were.

- A zone read off a projection (`readSvg`, `readDrawing`, `loadFace`) has
  the path of the part it shows, `bay-1/module/b01`, where it had the
  element's id, `bay-1-rear--b01`, and says `projected: true`. **This is
  the one thing that changed meaning:** a page that keyed anything on such a
  zone's `path` now gets the address. Its `id` is the element's, as before.
- The draw.io and OmniGraffle files name such a port as they did
  (`exportName`), and a cable end finds it by either name.
- `freePorts` offers `{ path: '<bay>/module/<part>', view }` for a port on
  a back, and never an element id; `cable.add` and `cable.update` refuse an
  element id and say what to give.
- `rack/ports.js` is new: `seatedPort`, `settleEnd`, `settleEnds`. A page reading whether an end lands can ask `seatedPort`
  for an end under a bay and keep its drawing lookups for the rest; where it
  still looks in a drawing, a part on a back is `data-of`, not `data-path`.
- `looseReason` reads one more fact, `onView`, and says which panel a port
  is on when an end names the other one.

**New in 0.22.0: rack file version 4.** One version for everything that had
waited for one ([`docs/rack-file-v4-design.md`](../docs/rack-file-v4-design.md));
[Heights, spans and half units](#heights-spans-and-half-units) has the names
a page calls. A version-3 file opens as it was and is saved as version 4,
**which a page or kit older than 0.22.0 refuses whole.**

What a page gains:

- A position in steps of 0.5 (`ru: 12.5`), with `unitsOf`, `spanOf`,
  `itemBox`, `spanText` and `uText`; a frame `startU`, `setback` and round
  holes; an item `setback`, `roll` and `heldBy`.
- `states` and `readings` on an item and on a part beside the rack
  (`rack/states`, `state.set`, `readings.set`), and a PDU hung on brackets
  (`zerou.hang`, `fitsHang`, `bracketPositions`).
- The lengths of a cable by name (`needOf`, `spareOf`, `END_PLAY_M`), where
  its spare is stored (`cable.slack`, `rack/slack`), and the face of a tray
  it is pinned to (`cable.lay`, which the routes act on).
- Straps of three kinds, each with a width, and the tie slots they are at
  (`straps().kinds`, `anchorsOf`, `strapTotals`, `strapTexts`).
- Exports: `spare`, `stored` and `straps` on the cable schedule, a spare
  line in the BOM notes, the spare in a draw.io edge label, and device
  comments for a rolled item, a PDU on brackets and what is set off.

What changed meaning, for a page that calls the kit:

- `span` is removed: use `spanOf`, which is half-open, `[ru, ru + units)`.
- `heightOf` and the `u` of `itemsWithU` are 0.5 for a half-unit device,
  `positionOf` answers in halves, and `freeUs` may answer a half position.
- A body is centred in its span in the solids, where it stood on the bottom.
- `END_ALLOWANCE_BY_MEDIA` and `endAllowance` are what is inside the port
  alone; the 0.1 m of dressing an end is `END_PLAY_M`. `stockLength` takes
  the need. A routed length holds `need`, not `measured`, and a cord up to
  10 mm short of full end play keeps its stock size.
- `straps().count` is every kind together; the spacing straps alone are
  `straps().kinds.spacing`. `strapBomRows` counts the straps of single
  cables only when handed `{ anchors: anchorsOf(rack, ctx) }`.
- The cable schedule has 20 columns where it had 17.
- The Nautobot device file is written at whole units, and leaves the later
  of two devices that share a unit with no position: on one face always,
  and front and rear while either type is full depth. **That last is a
  fix:** Nautobot refuses such a pair, and earlier kits wrote it.
- `rackImportRows` answers no row, and `left`, for a rack name over 100
  characters.

**New in 0.21.0, in `rack/`.** Four changes to where a cable runs and what is
said about it; nothing is removed or renamed, and the rack file and the
export columns are as they were.

- A bundle member with no route of its own joins and leaves the trunk at the
  elements nearest its two ports, and a member's own route is the gutter
  route even for a jumper within two units ([Bundles](#bundles), #1012):
  `ownRoute` and `autoRoute` take `{ gutter: true }`, `followTrunk` takes
  `nearest`, and `trunkMeasures(rack, cable, trunk, ctx)` measures it.
  **Measured lengths change** for a member whose own route never met its
  trunk: it no longer rides to the far end and back.
- A span that crosses in front of other ports is reported (below, #1013):
  `routePath().covers`, `coverFindings`, `coverFindingsOf`, and the optional
  reader `portBoxesOf(itemId)` on the routing context.
- `inspect`, `describe` and the export notes carry the bend and span
  findings (#1007): `route.bends` and `route.covers` on a cable, a fuller
  `Findings:` line, `bends` and `covers` options on `cableScheduleRows`,
  `layNotes` and `layNotesOf` in `rack/export-data`, `bendFindingsOf`, and
  one finding a corner. The summary of `bundle.create` says when a jumper
  that hung gets longer in the bundle.
- The same cable written end for end gets the same lay and the same findings
  (#986): `routePath` lays it from both ends and keeps one. **Routed lengths
  change** on the few cables whose other lay is the better one (seven of a
  sample of 1,803), and a reader on the routing context can be handed a twin
  of the cable, `a` and `b` exchanged.

**A span in front of other ports.** With no horizontal manager a cable runs
from its lane to its port across the faces between, over their ports, and
crosses no body. The path's `covers` lists each port such a span passes in
front of, `{ kind: 'port-behind-span', cable, item, path, view, between:
[from, to], at: [x, y, z], judged, estimated? }`, and `coverFindings(rack,
ctx, nameOf)` gives one finding a cable, `{ kind: 'span-over-ports', cable,
count, ports, between, judged, estimated?, text }`: "c10 crosses in front of
port-2 and port-4 on MGMT-SW1 between left-front U42 and its port on
MGMT-SW1: add a horizontal cable manager above or below MGMT-SW1 to carry it
to the gutter." It warns and never refuses. Only a span with no pathway at
either end is judged (port to lane, or port to port), never against the
cable's own two ports, and never against a port beside one of them: one on
the same panel whose box comes within the cable's bend radius of its own
port's centre, the stacked partner of its port always among them, since no
manager moves a cord off those. A jumper that only drops down its own column
is not reported. `judged` says which ports were there: `all`, or `cabled`
when the page listed none, and then the sentence ends "Only ports that hold a
cable were judged."; `estimated: true` marks a port taken at the estimated
box. The kit knows where the cabled ports are
(`portX`, `portY`); give the context the optional reader
`portBoxesOf(itemId) -> [{ path, view, x, y, w?, h? }]` (the centre of each
port's box in the frame `portX` and `portY` use, and its size in mm) and
every port of a device is judged, cabled or not. `inspect` carries a cable's
finding as `route.covers`, `describe` counts them, and
`cableScheduleRows(..., { covers })` writes the sentence into the cable's
notes. A port that states no size is taken as 12 by 10 mm, and a span covers
a port no further than 100 mm out of its panel; both are estimates. What is laid for a cable
is kept per rack, context and cable, so, as for a route's side, build a new
context when what it reads changes: a context changed in place gives the
path laid for what it read before ("New in 0.25.0" below says what is kept
and what lays a cable again). A cable is laid from both its ends and one lay is kept by a
rule that does not know which was written first (fewer bodies crossed, then
less short of room, then shorter, then the end whose port sorts first), so a
cable written the other way round lays the same and reports the same bends
(0.21.0, #986). That is the lay of a route, not the choice of one: the
automatic route still breaks its own ties from end a (a manager's rings in
order from end a, end a's side of two gutters as short), so a cable written
the other way round can be given another route, and then another lay. The
readers on the context (`plugReachOf`, `trayFaceOf`, `bendOf`, `diameterOf`,
which take the cable, and `typeOf`, which takes its id) are asked for both
lays, and those that take the cable are handed its twin, `a` and `b`
exchanged, for the lay from its other end. **Routed lengths change in 0.17.0** on
every routed cable that turns at a ring, goes round a body or hangs. On the
reference rack of #949 each of the sixteen cords is 10.9 to 179.2 mm longer
and seven pass the 0.5 m break (c1 to c3 and c5 to c8 are 1 m cords again).
On one sample of 60 generated racks (1,803 cables,
`spec/tests/js/bend-room-sample.mjs`) a length moves by 113 mm shorter to
297 mm longer, median 14 mm longer, 93 stock sizes up and 34 down; the
corners short of their radius fall from 22,910 to 959, each a bend the kit's
rules found no room for (most at a DAC's or an AOC's head, or a Cat 6A boot,
that ends beside the ring's line).

To change a rack by name rather than by function, use the command core:
`createRackEditor({ doc, chassisOf })` applies `place`, `move`, `patch`,
`remove`, `attach`, `detach`, `frame`, `rename`, `dcim`, `fit`, `field`, the
`side.*`, `zerou.*`, `cable.*` and `bundle.*` commands and the page's own `lengths.routed` as all-or-nothing
batches, with `undo`, `redo` and an `on('change')` event. Each command names
its arguments in `COMMANDS` (`rack/commands.js`), and `rack/queries.js`
answers what a command would need to know first.

### Commands and questions for an agent

`fit` seats, empties or restores one bay or cage, and `field` sets one setting
of one seated part; neither touches the rest of the device. `cable.update`
takes `a` or `b` to move an end and keep the cable, `color` to give the cable
a colour of its own (`null` takes it off), and `cable.route` checks
each new waypoint against the rack. These check what they are given against
the parts lists when the caller loads them: `loadSlots(dist, refs)` fetches
each device's `<ref>.configs.json` and `components.json` once, and
`editor.apply(cmds, { origin, ctx })` and `editor.preview(cmds, { ctx })` lay
that `ctx` over `{ chassisOf }` for the one call. Without it, nothing is
checked, as before.

`inspect(rack, id, ctx)` reads one device whole: its configurations, every bay
and cage with what it holds and what it takes, and its parts' settings. For a
cable it reads both ends, the route, the routed length (with `ctx.route`), the
slack, the pathways it may name, and its loose ends (with `ctx.cableFacts`).
A cable end is `{ item, path, view }`: the port's path, and the device's own
panel that shows it. A port on a card in a bay is `<bay>/module/<part>` on the
bay's panel. A port on the back of what a bay holds (the rear adapters of a
patch panel, the trunk connector of a cassette) is the same form on the other
panel: `{ path: 'bay-1/module/b01', view: 'rear' }`. `freePorts` offers both
by path. An element id of a drawing (`bay-1-rear--b01`) is not an address:
`cable.add` and `cable.update` refuse one and say what to give, and
`freePorts` never offers one. `fit` counts the ports of a part's back as its
ports, so a cable on one stays through a change of part that keeps the port
and is reported as a loose end through one that does not.

Whether such an end lands is answered from the parts lists where they are
loaded: `seatedPort(item, end, ctx)` in `rack/ports.js` reads the item's
swaps, the part in the bay and the parts of its back, and `looseEnds`,
`inspect`, `selectCables` and `suggestMedia` lay its answer over
`ctx.cableFacts` (`settleEnds`). The exports settle the same way when they
are handed the same lists: `cableFindings(rack, ends, parts)`, and `parts` in
the options of `cableScheduleRows`, `cableNotes`, `sheetCableNotes`,
`drawioCables`, `cableBomRows` and `cableImportRows`. Without `parts` an
export has only what the page read, so a page passes both, or hands in ends
it has already settled.

The catalogue answers for less than a drawing shows, and says nothing where
it cannot be sure:

- only for a port the part composes. A port drawn by a skin alone, and every
  port of the device itself, is the page's to read off the drawing.
- only for a bay the item's swaps or its configuration names. A device may
  give a bay to some configurations only, and `configs.json` lists every bay
  without saying which; a bay nothing names reads as holding its default,
  which the build does not draw in a configuration that has no such bay.
- it does not say whether a bay shows the back of what it holds. An enclosure
  with a closed rear has the rear adapters of its panels all the same: a
  cable on one lands, and is not drawn there. The front and the rear port of
one adapter are two ports, and each takes its own cable; that the glass
joins them is not modelled here.

`selectCables(rack, selector, ctx)` turns `{ item }`, `{ item, path }`,
`{ loose: true }`, `{ purpose }`, `{ media }` or `{ bundle }` into cable ids, for a caller to
expand into plain commands (with `{ loose: true }` and some ends unchecked, the
result also says `unchecked: true`); a `purpose` or `media` must be a name, so
`{ media: null }` is refused rather than matching every cable.
`describe(rack, ctx, { section, offset, limit })` reads one stretch of a long
rack in full: `section` is `items`, `zeroU`, `cables` or `bundles`, and `limit` is capped at
`MAX_WINDOW` (50). A section, offset or limit it cannot read returns
`{ error }`. `catalog(devices, { kind })` finds a
"patch panel" or a "switch" by `rack.json`'s `kind`.

### Beside the rack, and on one rail

A part that stands beside the rack and takes no rack unit (a `rack-side`
part: a vertical cable manager, and next a zero-U PDU) is an entry of
`rack.zeroU`, not an item: `{ id, ref, cfg, label, at, offsetMm, between? }`.
`at` is an attachment point of the frame (`left` or `right` on a two-post,
`left-front` to `right-rear` on a four-post), `offsetMm` its bottom above the
bottom of the rails. `zerou.place { ref, at, ru }`, `zerou.update` and
`zerou.remove` place, move and remove one; it fits by the rack units it states,
not its drawn height, and never overlaps another on the same upright. A
`place` of one is refused. A frame change moves each to its own side of the
new frame, or down to fit, and removes one that no longer fits, saying so.
The lane beside an upright runs through a duct standing there: `laneXAt`
(`rack/route.js`) is its centre line, so a routed length is measured through
it, and `fill` and `capacityOver` count the cables through it (`fill` with
`ctx.zeroUAperture(entry)`, its channel in mm). **Routed lengths changed in
0.6.0** beside a duct, by about 49 mm at each end beside a 138.8 mm one.

A rack-face part narrower than the 450 mm opening (a finger bracket) may be on
one rail: `side.place { ref, face, ru, side }` puts it there, and
`side.set { id, side }` moves it to the other rail or, with `null`, across
both. On one rail it takes its units on that face and rail only, so a bracket
can stand on each rail at one U. Every rack-face part is now judged on every
unit it spans, not only its bottom one. `describe` lists the parts beside the
rack and each part's rail, `inspect` reads one (`kind: 'zeroU'`), and the
export data says where each stands (`zeroUNotes`, `zeroUImportItems` for the
DCIM device rows, and `rackNotes(rack, { zeroU: false, chassisOf })`).

### Bundles

Cables that share part of their route can be combed into a bundle and held
with hook-and-loop straps ([`docs/cable-bundles-design.md`](../docs/cable-bundles-design.md)).
A rack's optional `bundles` holds each one: `{ id, number, label, members:
[{ cable, a?, b? }], route, straps? }`. Membership lives on the bundle only;
`route` is the trunk, stored once and kept; a member's `a` or `b` is the trunk
waypoint where it leaves for that end. `bundle.create`, `bundle.add`,
`bundle.peel`, `bundle.update` and `bundle.remove` make and change them, each
one undo step; `cable.remove`, and `remove` with `cables: 'remove'`, take a
cable out of its bundle in the same step.

What needs the drawings comes in on `ctx.route`, the routing context `route.js`
takes: `editor.apply(cmds, { ctx: { route } })`, and for `inspect` and
`describe` the whole `{ chassisOf, route }`. With it, `bundle.create` works the
trunk out from where its cables run together (refusing a fork, a loop, a
detour or groups that share nothing, by name), and a command's `findings` carry
the size check: the bundle's diameter, `sqrt(sum(d^2) / BUNDLE_PACK)` with
`BUNDLE_PACK` 0.8, against the smaller of 63.5 mm and each pathway's opening.
It warns and never refuses. Diameters come from `ctx.diameterOf` when given
(`loadCableTypes(dist).diameterOf`), else from fill's figures. A duct running up
a rack-face part, and a duct beside the rack (with `ctx.route.zeroUAperture`),
are estimated from their channel and the part's depth, and say so. Without
`ctx.route` a bundle is still made and changed, with a route given by hand,
and is reported not checked.

`resolveRoute` follows the bundle: a member runs its own route to the trunk,
the trunk, then its own route on, and the result names its `bundle`, `join` and
`leave`, so routed lengths, fill and the drawings follow with no change of
their own. A member's own route is the gutter route even for a jumper within
two units, which hangs when it is on its own (`ownRoute` and `autoRoute` take
`{gutter: true}`), and a member whose route still does not meet the trunk
joins and leaves it at the trunk elements nearest its two ports
(`trunkMeasures(rack, cable, trunk, ctx)` measures them for `followTrunk`), so
it never rides to an end its ports are not at. `straps(rack, bundle, ctx)` places the straps, every 12 in unless
the bundle says otherwise, as `{ segment, t, along_mm, point, dir, on }` along
the trunk as its members' paths run ("New in 0.28.0" above), kept off rings. `inspect` reads a bundle (`kind: 'bundle'`) and a member's
`bundle`, `selectCables` takes `{ bundle }`, and `describe` lists them. A
bundle of fewer than two cables is kept and listed, but not drawn.

**The bend check (0.8.0).** Pass `ctx.bendOf` as well
(`loadCableTypes(dist).bendOf`, each cable's installed minimum bend radius in
mm) and a bundle's findings also carry its bend: at each corner of the trunk,
and at each pathway whose guide states a `radius`, the bundle needs the
largest radius among the members present there, so one fibre makes it as
strict as fibre. A member at its own join or peel point makes its own turn and
is not counted there. A pathway's stated radius is the room it has; a corner's
is worked out from its legs, `min(a_in, a_out) / tan(theta / 2)`, each leg half
the way to the next corner or all the way to the trunk's end, and is marked
`estimated`. A trunk that doubles back has no room at all. It warns and never
refuses: "Bundle 2 turns at left-front U10 with room for a 24.5 mm bend; c2
(om4) needs 25 mm, 0.5 mm short." A member with no radius (no type, or no
`bendOf`) is listed as unchecked, never passed. `inspect` gives
`bend: { radius_mm, by, unchecked, points, violations }`, each point
`{ kind: 'corner' | 'pathway', at, waypoint, angle_deg?, legs_mm?, room_mm,
source: 'legs' | 'guide', estimated, need_mm, by, members, unchecked, ok,
short_mm }`, `ok` null where nothing present has a radius; `cornersOf(points)`
is the geometry on its own. A cable outside a bundle, and a member's lead to
its port, are not checked here: each cable's own path is, since 0.17.0, by
`routePath`'s `bends` and `bendFindings` (above).

**Bundles in the exports (0.9.0).** `bundleExports(rack, ctx)` in
`@portrayal/kit/rack/export-data` measures each bundle once, with the same
`ctx` as `bundleCheck`, and gives one record per bundle: `{ id, number, label,
name, members, drawn, checked, length_m, straight, few, every, straps, size_mm, limit_mm,
limit_at, limit_estimated, bend_mm, bend_by, bend_checked, warnings, notes }`.
`name` is what a tag prints (the label, else "Bundle N"), and `number` and
`label` are there on their own for label software. `straps` is the count the
BOM buys, and null when the route could not be read: never a guess.
`bundleNotes(bundles)` is one line per bundle, its members, length, straps,
size and bend ("Bundle 2 (b1): 12 cables (c1-c12), 2.4 m, 8 straps every
12 in; ..."), followed by its warnings and notes.
`strapBomRows(bundles)` is the BOM's one hook-and-loop strap line, every
bundle's straps summed, and `strapBomNotes(bundles)` says what it could not
count. `cableScheduleRows(rack, ends, items, routes, { bundles })` has a
`bundle` column straight after `route` and carries the bundle notes. NetBox's
cables file names a member's bundle first in its description; Nautobot's
cable has no description, so its notes list each bundle's cables. draw.io
draws members one by one and says so.

**The rack file is version 3 from 0.7.0.** `parseDoc` reads version 1 and 2
files as they were, and every save writes version 3, which a page or kit
older than 0.7.0 refuses rather than opening and losing its bundles. The
repairs `parseDoc` makes to bundles come back through
`parseDoc(input, { notes })`; hand the same array to `editor.loadDoc(doc, { notes })`
and they are its first `findings`.

**The rack file is version 4 from 0.22.0.** A version-3
file opens as it was and is saved as version 4, which a page or kit that
reads version 3 refuses whole. What the version holds is in
[`docs/format-stability.md`](../docs/format-stability.md) and
[`docs/rack-file-v4-design.md`](../docs/rack-file-v4-design.md).

A rack file is described by
[`rack.schema.json`](https://portrayal.dev/schemas/v3/rack.schema.json), rack file `version` 4.

## Exporting to draw.io and OmniGraffle

Both are the face as a picture, with one invisible shape over every port and
bay, named by its path: a line drawn to a port attaches to `port-12`, not to a
point on a picture. Hand either function the live drawing and a marks document,
and what is seated, lit, highlighted or cropped is what is exported:

```js
import { toDrawio } from '@portrayal/kit/drawio';
import { toGraffle } from '@portrayal/kit/omnigraffle';

const {text} = toDrawio(shell.state.svg, doc);                 // a .drawio to open
const lib = toDrawio(shell.state.svg, doc, {form: 'library'});  // or a library
const {bytes} = await toGraffle(shell.state.svg, doc);          // a .gstencil
```

`readSvg` and `portsOf` in `zones.js`, and `entry`, `library` and
`rackDiagram` in `drawio.js`, build the same files from published faces, many
at once. Reading a face needs a browser - it is parsed and laid out by the DOM
- and so does OmniGraffle's picture, which is drawn on a canvas; writing the
files from zones already read does not.

### Cables in a draw.io file

`rackDiagram` and `toDrawio` (and `diagram`) take a cable list and write each
cable as a draw.io edge whose source and target are two port cells, so its
connectors stay on their ports when a device is moved:

```js
const cables = [{
  id: 'c1',
  a: { item: 'sw-1',  path: 'slot-2/module/p0', view: 'front' },
  b: { item: 'srv-1', path: 'nic-1/p0',         view: 'rear' },
  media: 'os2', purpose: 'uplink', label: 'up-1',
  length: { value: 2, unit: 'm' },              // or a number or a string
}];

const xml = rackDiagram(groups, { cables, cableStyle: { os2: '#C9A400' }, notes: [] });
const { notes } = rackCables(groups, cables);   // the same notes, as a list
const { text, notes: n } = toDrawio(shell.state.svg, doc, { cables });
```

- **Ends.** `item` is a mounted device's `id`, else its `name`; `path` is the
  port's `data-path`, so a port on a seated card is `slot-2/module/p0`. `view`
  is the face, and may be left out. For `toDrawio` and `diagram`, `item` is
  left out or is the drawing's name. An edge ends at the port cell's centre
  connection point.
- **Pages.** Both ends on one page (two racks on one page included) make one
  edge. Ends only on different pages, such as a front-to-rear run when each
  face is a page, make a stub on each page: a short edge from the port to a
  label naming the far end (`→ rack-2 · r740 · rear/nic-1/p0`, from the rack's
  label, the device's name, and the face and path). A draw.io edge cannot
  leave its page.
- **Ends that are not drawn.** An unknown item, a face no page draws, or a
  path with no port cell (cropped away, or not in the drawing) draws nothing
  for that cable: it is listed in the file's notes, an XML comment inside
  `<mxfile>`, with the reason. `notes` adds the caller's own lines to the same
  comment. `toDrawio` also returns them as `notes`.
- **Style.** `cableStyle` is a map from `media` to a stroke colour, merged over
  `CABLE_COLOURS` (dac, aoc, cu, mm, sm, the OM and OS grades, and a grey
  `default`), or a function from a cable to a whole draw.io edge style. A
  cable that carries its own `color` (`#rgb` or `#rrggbb`) is drawn in it,
  ahead of the map; a function is handed the cable and reads `color` itself.
  `CABLE_COLOURS` is this writer's own palette, chosen to read on draw.io's
  white page, and is not the Rack Builder's `COLORS`.
- **Identity.** Edge ids are `cable-<id>`, slugged like the other cell ids (a
  stub is `cable-<id>-a` or `-b`, and its label `cable-<id>-a-far`). The edge's
  label is `label` and `length`. `id`, `media`, `purpose` and `length` are kept
  as `portrayal-cable`, `portrayal-media`, `portrayal-purpose` and
  `portrayal-length` attributes, so a cable can still be identified after the
  file is edited and saved in draw.io. The same input writes the same bytes.

## Rack ears

A device is modelled between its ear folds, and a published face has no ears.
Ears built into the face (a blanking panel, a full-width patch panel, any front
480 mm or wider) are part of the drawing and always shown. Every other rack
device can be shown with a generic L-bracket ear each side, reaching the
482.6 mm rack face, sized from `chassis.ears` in `<device>.configs.json` (the
chassis height where it states none), and silver unless `chassis.ears.color`
states another colour (the plan's `color`). It is a viewing choice: the Explorer and
Annotate start with it off, the Rack Builder with it on.

```js
import { earPlan, drawEars, clearEars, faceSize, frontWidthOfText } from '@portrayal/kit/ears2d';

// the front's declared width says whether the ears are built in
const plan = earPlan(meta, faceSize(frontSvg)[0]);  // or frontWidthOfText(text)
drawEars(shell.state.svg, plan, shell.state.view);   // shapes drawn, 0 for none
clearEars(shell.state.svg);                          // the face as published

const viewer = createViewer(el, { dist, ears: true });   // 3D, the same plan
viewer.setEars(false);
```

`plan` is null where the device gets no generic ear: not a `rack` device, a
sheet body, ears stated `behind`, or a front as wide as the rack face. The
overlay is drawn the way `render.py --with ears` draws the ear (the same
shapes, ids and colours, and the viewBox grown to hold them, with
`data-face-w`/`-h` naming the face), as one
`<g data-overlay="ears" pointer-events="none">` after the drawing. It carries
no `data-path` or `data-class`, so it is never picked, selected, listed or
offered as a port. An export of the live drawing (`toDrawio`, `toGraffle`)
carries it as picture, because exports capture what is on screen; so does a
GLB taken while the 3D viewer's ears are on. `drawEars` replaces what it drew
before, so a host calls it again after anything that changes the drawing.
The kit cannot see a device that still places `common/rack-ear@1` of its own,
which no published face draws, so that device gets the generic pair here too.

## three.js

`viewer3d.js` and `share.js` import `three` and `three/addons/` as bare
specifiers, and nothing here resolves them — supply either an import map:

```html
<script type="importmap">
{ "imports": {
  "three": "https://unpkg.com/three@0.161.0/build/three.module.js",
  "three/addons/": "https://unpkg.com/three@0.161.0/examples/jsm/"
}}
</script>
```

…or a bundler that can. It is a peer dependency, and an optional one: the 2D
half (`shell`, `marks`, `states`, `relief`) does not touch three.

## Status

Lives in the Portrayal repo for now. It has no dependency on anything outside
`dist/`, so it can move to its own repository whenever that is wanted — that is
what the artifact contract and `spec/tests/test_artifact_sufficiency.py` exist
to keep true.

Apache-2.0, same as the rest of the repository.

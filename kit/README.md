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
- `devices.json`, `components.json` (+ `components-detail.json`), `labs.json`,
  `gaps.json`, `vendors.json`, `listings.json`.

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
| `fields.js` | writing a field on a part at runtime - its text and its colour, the build's rule, for 2D and 3D alike; and what a form of a part's fields needs: its rows (`fieldRows`), whether a value is one the field takes (`fieldAccepts`), and the `fields=` location string (`encodeFields`, `decodeFields`) |
| `devsel.js` | device selection and filtering - hardware by its maker, and each NOS vendor's listings under that vendor (`listings.json`, #709) |
| `nosnames.js` | what the chosen listing's NOS calls each port (`swp7`, `Ethernet24`, `ge100-0/0/7`), expanded by the same grammar as the DCIM export (#712) |
| `optical.js` | where a fibre goes: an optical module's front number and far end for a path, read from `components.json` |
| `dist.js` | artifact fetching, and where each file is: a build directory or the npm packages |
| `zones.js` | the ports and bays of a compiled face, each with its box in millimetres - what the diagram exports put a connectable shape over |
| `drawio.js` | draw.io: a shape library, a rack elevation, or one live drawing as a `.drawio` (`toDrawio`), with a named connection point per port |
| `omnigraffle.js` | OmniGraffle: a `.gstencil` with a named, magnetised shape per port, or one live drawing as a stencil (`toGraffle`) |
| `ears2d.js` | generic rack ears over a published face in 2D (`drawEars`, `clearEars`), from the plan the 3D viewer builds (`earPlan`); see [Rack ears](#rack-ears) |

Plain ES modules. No bundler, no build step.

## Racks

The `rack/` modules are the Rack Builder's rules, without its page. They read
no DOM and fetch nothing but the catalogue and the cable types, so the same rack is checked the
same way in a browser, in node and in an agent. Each is imported on its own,
as `@portrayal/kit/rack/<module>`:

| module | what it does |
|---|---|
| `rack/catalog.js` | `loadCatalog(dist)`: the rack catalogue, and the `chassisOf(ref)` lookup everything else takes; `loadSlots(dist, refs)`: the bays, cages and parts the commands check against |
| `rack/model.js` | the rack file: `newDoc`, `parseDoc`, `serialize`, and an edit of an item, frame or name that returns a new rack |
| `rack/rails.js` | the rack's rails: unit height, opening and where a device sits between them |
| `rack/fit.js` | whether a device fits at a unit, on a face and (a narrow part) on one rail; whether a zero-U part fits beside the rack (`fitsZeroU`); how a shrink trims a rack |
| `rack/zero-u.js` | the parts beside the rack: where each stands, as words (`whereText`) and as x (`zeroUX`), whether the lane beside its upright runs through it, and each placeable entry (`zeroUEntries`) |
| `rack/managers.js` | cable managers: `placement` of a manager onto the device behind it, and moving one |
| `rack/cable-rules.js` | cables: which two ports may be joined, `withCable`, media and lengths |
| `rack/cable-types.js` | the cable types (`cable-types.json`): `loadCableTypes(dist)` fetches them and returns `typeOf`, `bendOf` and `diameterOf` over them; the same lookups are exported to build over a table already in hand (a fixture, a cached copy): `typeOf(types, id)`, `cableTypeOf(types, cable)`, `radiusMm(type, which)`, `installedRadiusMm(types, id)`, `bendLookup(types)` and `diameterLookup(types)`, each radius in millimetres |
| `rack/route.js`, `rack/route-path.js`, `rack/cable-geometry.js` | where a cable runs: `resolveRoute`, `routePath`, `trayOf`, `ringMarks`, `orientMarks`, `reverseMarks`, `routedLength`, `pathLength`, pathway fill, `ringFindings`, `bodyFindings`, and the geometry under them (`throughRings`) |
| `rack/solids.js` | the solid bodies a route may not pass through: `solidsOf(rack, ctx)` places every device's envelope or derived `solids` in rack coordinates; `legCrossings` tests a leg against them; `detour` takes a leg round them; `CLEAR`, the clearance a detour keeps; `traysOf(rack, ctx)` places every device's `trays`, the floors a cable lies on; a ring's solid parts (`ring/<id>/<part>`) are met by the cable's tube |
| `rack/bundles.js`, `rack/bundle-route.js` | cable bundles: the size and bend checks (`bundleCheck`, `bundleChecks`, `pathwaysOn`, `bendCheck`, `cornersOf`), strap positions (`straps`), the trunk worked out from the members' routes (`deriveTrunk`) and a member's route along it (`followTrunk`) |
| `rack/export-data.js` | the rack as rows: `bomRows`, `cableScheduleRows` and the device-import data, and the bundles as the exports read them (`bundleExports`, `bundleNotes`, `strapBomRows`) |
| `rack/dcim-rules.js` | what a NetBox or Nautobot import needs of a rack |
| `rack/validate.js` | `validate(schema, value)`, a small JSON Schema validator, and `same` |
| `rack/commands.js` | every edit as a named, validated command, and `apply` for a batch of them |
| `rack/history.js` | undo and redo as snapshots |
| `rack/editor.js` | `createRackEditor`: a rack document you edit by commands, with undo, redo and change events |
| `rack/queries.js` | reading a rack: `fitsAt`, `freeUs`, `catalog`, `describe`, `inspect`, `selectCables`, `freePorts`, `suggestMedia`, `looseEnds` |
| `rack/resting.js` | internal, not exported: how a cable rests, for `route.js` (`DRAPE`, the free span's hang and landing, the held face) |
| `rack/slots.js` | internal, not exported: what a placed device holds, read without a drawing, for `commands.js` and `queries.js` |

### Where this came from

`kit/rack/` was moved here from `roc-ops/portrayal-site`, where it was
`site/rack/`, at that repository's commit `d1a1aa8e`. This repository is now the source of
truth: edit these modules here. portrayal-site vendors
`kit/rack/*.js` read-only, and its contract check refuses a copy that has
drifted. The rules these modules follow are stated in their own comments,
and the rack file format in [`docs/format-stability.md`](../docs/format-stability.md)
and `schemas/v2/rack.schema.json`.

### The catalogue

`rack.json` is written by the build beside `devices.json`. For every device it
holds the rack units, the depth and height, how it mounts, whether its body is
sheet, the cable capacity its vendor states, the ids a route can pass
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
cable's media (#962, docs/cable-lay-design.md section 1.6). `END_ALLOWANCE`
is the sourced table, in metres an end: only what is physically there and
not in the path, the part of the plug inside the port and half the maker's
short tolerance. It is 0.0131 for LC fibre, 0.0345 for copper and a cable
with no media, 0.025 for a DAC and 0.0524 for an AOC. Service loops and
dressing slack are explicit slack held in a tray, never part of the table;
until a tray can hold slack (#949 step 4) the kit adds a **temporary
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
PDU. On the owner's rack of #949 they grow 2 to 38 mm. On generated racks
they move by up to about a tenth of a metre either way, and the figures
depend on the layout: one sample of 3,120 cables (one layout and seed) gave
89 mm shorter to 131 mm longer, median 10 mm longer, 67 stock sizes up and
67 down; an independent sample of 3,962 cables gave 94 mm shorter to 94 mm
longer, median 4.5 mm longer, 67 up and 27 down. A route is longer where a cable
now goes over a ring to its approach point, or round a PDU it grazed, and
shorter where a detour that went round a tray's
front edge to a ring's face can end at the approach point by a shorter way.

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
takes `a` or `b` to move an end and keep the cable, and `cable.route` checks
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
their own. `straps(rack, bundle, ctx)` places the straps, every 12 in unless
the bundle says otherwise, as `{ segment, t, along_mm }` along the trunk, kept
off rings. `inspect` reads a bundle (`kind: 'bundle'`) and a member's
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
its port, are not checked for bend.

**Bundles in the exports (0.9.0).** `bundleExports(rack, ctx)` in
`@portrayal/kit/rack/export-data` measures each bundle once, with the same
`ctx` as `bundleCheck`, and gives one record per bundle: `{ id, number, label,
name, members, drawn, checked, length_m, every, straps, size_mm, limit_mm,
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

A rack file is described by
[`rack.schema.json`](https://portrayal.dev/schemas/v2/rack.schema.json), rack file `version` 3.

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
  `default`), or a function from a cable to a whole draw.io edge style.
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

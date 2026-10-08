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
| `shell.js` | the explorer shell — device picker, view switching, tree |
| `viewer3d.js` | 2D→3D: rasterises each face onto a chassis-sized box, adds relief meshes; a host can hold coloured marks on many parts (`setMarks`) and paint a lamp its own colour (`setLampColors`) |
| `relief.js` | turns `data-depth` / `data-z-*` annotations into geometry |
| `bevel.js` | a bevelled chassis body from the polygons the build publishes, triangulated and mapped for the 3D view |
| `lamps.js` | animated lamps in 3D: each blinking lamp drawn once per keyframe and swapped by the clock (used by `viewer3d.js`, not exported on its own) |
| `marks.js` | annotation and callouts |
| `states.js` | state toggling (LEDs, link states) and what a display can read |
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

Plain ES modules. No bundler, no build step.

## Racks

The `rack/` modules are the Rack Builder's rules, without its page. They read
no DOM and fetch nothing but the catalogue, so the same rack is checked the
same way in a browser, in node and in an agent. Each is imported on its own,
as `@portrayal/kit/rack/<module>`:

| module | what it does |
|---|---|
| `rack/catalog.js` | `loadCatalog(dist)`: the rack catalogue, and the `chassisOf(ref)` lookup everything else takes; `loadSlots(dist, refs)`: the bays, cages and parts the commands check against |
| `rack/model.js` | the rack file: `newDoc`, `parseDoc`, `serialize`, and an edit of an item, frame or name that returns a new rack |
| `rack/rails.js` | the rack's rails: unit height, opening and where a device sits between them |
| `rack/fit.js` | whether a device fits at a unit, on a face, and how a shrink trims a rack |
| `rack/managers.js` | cable managers: `placement` of a manager onto the device behind it, and moving one |
| `rack/cable-rules.js` | cables: which two ports may be joined, `withCable`, media and lengths |
| `rack/route.js`, `rack/route-path.js`, `rack/cable-geometry.js` | where a cable runs: `resolveRoute`, `routedLength`, pathway fill, and the geometry under them |
| `rack/export-data.js` | the rack as rows: `bomRows`, `cableScheduleRows` and the device-import data |
| `rack/dcim-rules.js` | what a NetBox or Nautobot import needs of a rack |
| `rack/validate.js` | `validate(schema, value)`, a small JSON Schema validator, and `same` |
| `rack/commands.js` | every edit as a named, validated command, and `apply` for a batch of them |
| `rack/history.js` | undo and redo as snapshots |
| `rack/editor.js` | `createRackEditor`: a rack document you edit by commands, with undo, redo and change events |
| `rack/queries.js` | reading a rack: `fitsAt`, `freeUs`, `catalog`, `describe`, `inspect`, `selectCables`, `freePorts`, `suggestMedia`, `looseEnds` |
| `rack/slots.js` | what a placed device holds, read without a drawing: its bays and cages, what its configuration builds, and its own swaps |

### Where this came from

`kit/rack/` was moved here from `roc-ops/portrayal-site`, where it was
`site/rack/`, at that repository's commit `d1a1aa8e`. This repository is now the source of
truth: edit these modules here. portrayal-site vendors
`kit/rack/*.js` read-only, and its contract check refuses a copy that has
drifted. The rules these modules follow are stated in their own comments,
and the rack file format in [`docs/format-stability.md`](../docs/format-stability.md)
and `schemas/v1/rack.schema.json`.

### The catalogue

`rack.json` is written by the build beside `devices.json`. For every device it
holds the rack units, the depth and height, how it mounts, whether its body is
sheet, the cable capacity its vendor states, and the ids a route can pass
through. `loadCatalog(dist)` takes what the other loaders take: a base URL, or
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

To change a rack by name rather than by function, use the command core:
`createRackEditor({ doc, chassisOf })` applies `place`, `move`, `patch`,
`remove`, `attach`, `detach`, `frame`, `rename`, `dcim`, `fit`, `field`, the
`cable.*` commands and the page's own `lengths.routed` as all-or-nothing
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
`{ loose: true }`, `{ purpose }` or `{ media }` into cable ids, for a caller to
expand into plain commands. `describe(rack, ctx, { section, offset, limit })`
reads one stretch of a long rack in full. `catalog(devices, { kind })` finds a
"patch panel" or a "switch" by `rack.json`'s `kind`.

A rack file is described by
[`rack.schema.json`](https://portrayal.dev/schemas/v1/rack.schema.json).

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

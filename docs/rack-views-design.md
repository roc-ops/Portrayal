# The Rack Builder's views in the kit

Status: **proposed, for decision.** Written now (decided 2026-10-28); no code
moves until the API in §2 and §3 is decided. Issue #1298.

The kit holds the Rack Builder's model and rules under `kit/rack/`. The 2D
elevation and the 3D rack scene live only in portrayal-site, so another page
can draw a rack the way the Rack Builder does only by copying the site's code.
portrayal-site's kit-move design
(`docs/superpowers/specs/2026-10-07-rack-kit-move-design.md`) calls this step
"piece 3": "The builder as a kit component, with the 2D elevation and the 3D
rack scene".

This note does three things:

1. It sets the API of the view modules under `kit/rack/view/` (§2), and the
   editor's API for more than one rack (§3).
2. It lists which portrayal-site modules move and which stay, from the import
   graph at portrayal-site `5dbbd41bd35e92a1b46e315eb5d7215213c6aeb0` (§4).
3. It splits the moves into pull requests of no more than about 1,500 lines
   each, in graph order, with the parity tests each one carries (§5 to §8).

## 1. The rules the views keep

These hold for every module under `kit/rack/view/`. They extend the rule of the
kit-move design's §3 to code that has to draw.

- **No global.** A view uses only the `document` it is given and the window
  that document belongs to (`document.defaultView`). It never reads `document`,
  `window`, `DOMParser`, `XMLSerializer`, `localStorage`, `devicePixelRatio`,
  `ResizeObserver`, `requestAnimationFrame` or `HTMLCanvasElement` as a global.
  Today's code reads every one of these as a global; §4.3 lists where.
- **No `three` import.** 3D code takes `THREE` and `OrbitControls` as
  parameters. `kit/share.js` imports `three` itself, so the GLB and USDZ
  writers are passed in too (§2.3).
- **No page state.** A view does not remember a setting. The stage colour and
  the covers setting are options. Saving them is the page's job.
- **No page text.** A sentence that only the page shows (help text, a WebMCP
  tool's words) stays in the site.
- **No shims.** The site deletes its copies when it switches, as the kit-move
  design's D3 did for the model.
- **One module, one order.** Each module that moves moves in exactly one pull
  request (§5).

## 2. The views' API

Two views, one contract. `mountRack2d` (from `kit/rack/view/elevation.js`) draws
one face of one rack as SVG. `mountRack3d` (from `kit/rack/view/scene3d.js`)
draws the rack as a three.js scene. Both return the same shape of handle.

### 2.1 Mounting

```js
import {mountRack2d} from '@portrayal/kit/rack/view/elevation';
import {mountRack3d} from '@portrayal/kit/rack/view/scene3d';

const view2d = mountRack2d(container, {
  document,                 // required: every node is made through it
  doc,                      // the rack document, as parseDoc returns it
  rackId,                   // which rack to draw; default doc.racks[0].id
  surface: null,            // §2.5; null means "the rack named by rackId"
  face: 'front',            // 'front' or 'rear'
  chassisOf, ctx,           // the catalogue lookup and loadSlots' context
  dist: 'assets/dist/',     // where the compiled faces are
  stage: '#101214', ears: true, metal: true, cables: true,
});

const view3d = mountRack3d(container, {
  document, doc, rackId, surface: null, chassisOf, ctx, dist,
  three: {THREE, OrbitControls},          // required for 3D
  share: {toGLB, toUSDZ},                 // optional: kit/share.js's writers
  guard: (build, onFail) => build(),      // optional: a WebGL check (§4.3)
  highlight: {landed, select},            // optional: the host's highlighter
  stage: '#101214', covers: 'see', camera: null,
});
```

A mount returns at once. `view.ready` is a promise that settles when the first
draw is complete (in 3D: devices, cables, then detail, as now).

### 2.2 The handle

| Member | What it does |
|---|---|
| `ready` | Settles when the first draw is complete. Rejects only if nothing could be drawn. |
| `update(doc, {rackId} = {})` | Draws a new document. Returns a promise that settles when the new draw is complete. A draw that a later `update` overtakes stops, as `createRackScene`'s build epoch stops today. Without `rackId` the view keeps the rack it has. If that rack has gone from `doc`, the promise rejects with a sentence that names the rack. |
| `select(path)` | Sets the selection: a path as §2.4 writes it, or `null` for none. It does not draw again. In 2D the view draws the selection ring, as `drawElevation({selectedId})` draws it now. In 3D the view calls `highlight.select(scene, target)`, because the 3D selection paint (`hover.js`) stays in the site (§4.3). |
| `on('pick', fn)` | Calls `fn(event)` when the reader clicks or taps something the view drew. Returns a function that removes the listener. Unknown event names throw, as the editor's `on` does. |
| `dispose()` | Frees everything the view made and removes it from the container. A second call does nothing. |

The pick event is:

```js
{
  view: '2d' | '3d',
  rackId: 'r1',
  surface: {kind: 'rack', id: 'r1'},
  key: 'item:i3',           // what was picked (§2.4)
  path: 'xc04/port-3',      // the part of it, or null
  face: 'front',            // 2D: the pane; 3D: the face that was hit, or null
  u: null,                  // an empty unit: its position (12, or 12.5 for a half)
  originalEvent,            // the pointer event, for the host's own use
}
```

`view.select(joinPath(event.key, event.path))` selects what was picked.

**`dispose()` frees every geometry and texture the view made.** In 3D, after
`dispose()`, `renderer.info.memory.geometries` and `.textures` are back to the
values they had before the mount, and the GL context is released
(`forceContextLoss`, as `createRackScene` does now). The view also removes its
listeners, its `ResizeObserver`, its pending timers, the hidden SVG it parks in
the document to measure anchors, and its relief overrides. In 2D it removes its
SVG and its listeners. A parity test checks the 3D numbers (§6).

### 2.3 What 3D takes

- `three: {THREE, OrbitControls}` is required. The scene takes everything it
  uses from it: `THREE.WebGLRenderer`, the geometries and materials, and the
  controls. `kit/relief.js` is configured from the same `THREE`, as
  `createRackScene` does now (`configureRelief`).
- `share: {toGLB, toUSDZ}` is optional. With it, `view.scene.toGLB()` and
  `view.scene.toUSDZ()` work as they do now: the tag leaders are set aside
  and the faces are drawn in full detail. Without it, both reject with a
  sentence saying that no writer was given. The site and the showcase pass
  `kit/share.js`'s pair, so their calls do not change.
- `guard(build, onFail)` is optional. Without it the view runs `build`, and if
  `build` throws it calls `onFail`. The site passes its own `guard3d`
  (`site/webgl.js`) and its "2D only" sentence, which both stay in the site.
- `highlight: {landed(scene, id, meshes), select(scene, target)}` is optional.
  `landed` is called with each device's meshes when they land, in place of
  `hover.js`'s `paintLanded3d`. `select` is called by `view.select`. Without
  them, nothing is dimmed and no selection is painted.
- `view.scene` is the built scene: today's `createRackScene` handle, without
  its `toGLB` and `toUSDZ` unless `share` is given. Hosts that need the
  camera, `metrics()`, `portAnchor` or `rackCables` read them from here, as
  `hover.js` and `exports.js` do now.

### 2.4 Paths

A path names one thing in one rack. It is `<key>` or `<key>/<part path>`:

| Key | Names |
|---|---|
| `item:<id>` | a mounted item (`racks[].items[].id`) |
| `zeroU:<id>` | a part beside the rack (`racks[].zeroU[].id`) |
| `cable:<id>` | a cable |
| `bundle:<id>` | a bundle |
| `tie:<item>\|<via>\|<tie>` | a tie strap of single cables (today's `tie-<slot>` names) |
| `u:<position>` | an empty unit (2D only); `<position>` is `12` or `12.5` |

The part path is the `data-path` in that item's drawing, as `part-path.js`
reads it now (`xc04/port-3`, or a module seated in a bay). `joinPath(key, path)`
and `splitPath(text)` are exported from `kit/rack/view/view.js`, so a host
never builds the string by hand. The rack is not in the path: it is the view's
`rackId`, and the pick event carries it.

### 2.5 A rack id, and a surface

A rack document holds `racks[]`, and each rack has an `id` (`model.js` gives
`r1`, `r2` and so on when a file has none). A view draws one rack: the one
`rackId` names, or `racks[0]` without it. Two views on one document can draw
two racks. Cable ends stay local to one rack (rack file version 4), so a view
needs nothing outside the rack it draws.

**A surface is what the devices are mounted on.** Today the only surface is a
rack. A backboard on a wall (#1297) holds devices too, at positions in
millimetres and not in units. So that a backboard can mount in the same views
later without a change to the handle, the views take `surface` and keep the
rack-specific code behind one seam:

```js
surface: {kind: 'rack', id: 'r1'}      // the default, from rackId
surface: {kind: 'backboard', id: 'b1'} // reserved (#1297)
```

Each surface kind supplies four things to the views. The rack's are the code
that exists now:

| Seam | For a rack (now) | For a backboard (later) |
|---|---|---|
| `frame2d(out, surface)` | `drawRails`: the rails, holes and unit numbers | the board's outline |
| `frame3d(scene, surface)` | `buildPostPair` and `buildRack`: the posts, holes and numbers | the board as a plate |
| `placeOf(item)` | `fit.js itemBox`, `zero-u.js`, `setbackOf` | the item's own `x`, `y` (mm) on the board |
| `ears(item)` | `earHoles`, `earPlanFor`, `rackEars` | none: a wall device has its own mount |

Until a schema for surfaces is decided (#1297), `kind: 'backboard'` is refused
with a sentence. The views take no position on where a backboard is stored.
Its document may be the site file that #1297 proposes. The seam only
fixes where its frame and its placements plug in. No pull request in §5 adds
a second surface kind.

## 3. The editor's API: more than one rack

`kit/rack/editor.js:28` edits `racks[0]` only (`const rack = () =>
current.racks[0]`). Editing more than one rack is a separate piece of work. It
builds on this API, so the API is set here.

```js
const editor = createRackEditor({doc, chassisOf, frameOf, cap});

editor.select(rackId)           // -> {rackId} or {error}
editor.selected                 // the selected rack's id
editor.rack(rackId?)            // the selected rack, or the one named
editor.apply(cmds, {origin, ctx, rack: rackId})
editor.preview(cmds, {ctx, rack: rackId})
editor.undo({rack: rackId}) / editor.redo({rack: rackId})
editor.historyOf(rackId?)       // {canUndo, canRedo, undoSummary, redoSummary}
editor.replaceRack(next, summary, origin, {rack: rackId})
```

- **`select(rackId)`** chooses the rack that calls without `rack` act on. An
  id that is not in the document returns `{error: 'There is no rack r3 in
  this document.'}` and changes nothing. It emits `change` with `cause:
  'select'`, `step: false` and the new `rackId`. This is the rack, not the
  item selection: "selection is the page's", as the editor's banner says, and
  stays so.
- **History per rack.** Each rack has its own `createHistory({cap})`, made
  when the rack is first edited. An undo in one rack never takes back an
  edit in another. `loadDoc` clears every history and selects `racks[0]`.
  `keepDcim` holds per rack.
- **Commands take an optional rack.** `apply`, `preview`, `undo`, `redo` and
  `replaceRack` take `rack`. Without it they act on the selected rack. The
  commands themselves (`commands.js`) are unchanged: they already take one
  rack and return one rack. The editor puts the result back at that rack's
  index in `racks[]`, not at index 0.
- **Every `change` event gains `rackId`.** Nothing else in the event changes.
- **A one-rack document is unchanged.** `selected` is `racks[0].id` from the
  start. A caller that never passes `rack` and never calls `select` gets the
  same results, events (plus `rackId`) and history as today. The getters
  `canUndo`, `canRedo`, `undoSummary` and `redoSummary` stay, and read the
  selected rack's history. `spec/tests/js/rack-editor.mjs` passes as it is.

A host connects a view to the editor like this:

```js
editor.on('change', ev => view.update(editor.getDoc(), {rackId: ev.rackId}));
```

## 4. The import graph

Read at portrayal-site `5dbbd41bd35e92a1b46e315eb5d7215213c6aeb0`, the
site's `origin/main` when this note was written. Line counts are the files read
in full at that commit. An edge to `vendor/` is to the kit's own copy, so it is
"kit".

### 4.1 Modules that move

Each row is one module. "Imports" lists only its site imports, each marked
"moves" (it moves to `kit/rack/view/`) or "stays" (it stays in the site and
the edge is cut, §4.3). Every other import of these modules is "kit": `vendor/*`.

| Module | Lines | Site imports (moves / stays) | Order |
|---|---:|---|---|
| `site/rack/dom.js` | 36 | none | 1 |
| `site/rack/ear-holes.js` | 32 | none | 1 |
| `site/faces.js` | 22 | none | 1 |
| `site/rack/face.js` | 258 | `faces` (moves) | 1 |
| `site/rack/settable.js` | 62 | none | 1 |
| `site/rack/elevation.js` | 437 | `ear-holes`, `face`, `dom`, `settable` (all move) | 1 |
| `site/rack3d.js`, shell part | 968 | none | 2 |
| `site/rack3d.js`, device part | 826 | `faces`, `face`, `ear-holes` (all move) | 3 |
| `site/rack/covers.js` | 226 | `face` (moves) | 3 |
| `site/rack/bend2d.js` | 102 | none | 4 |
| `site/rack/bend3d.js` | 322 | none | 4 |
| `site/rack/bundle-view.js` | 538 | none | 4 |
| `site/rack/stage.js` | 89 | none | 4 |
| `site/rack/part-path.js` | 42 | none | 4 |
| `site/rack/spare-loops.js` | 107 | `dom` (moves) | 4 |
| `site/rack/strap-size.js` | 145 | `bundle-view`, `stage` (move) | 4 |
| `site/rack/route-context.js` | 737 | `face`, `bundle-view`, `spare-loops`, `cable-plugs` (dynamic) (all move) | 5 |
| `site/rack/cable-plugs.js` | 229 | `face`, `part-path` (move) | 5 |
| `site/rack/spare.js` | 140 | `agent-text` (**stays**: cut 1) | 5 |
| `site/rack/cables.js` | 512 | `dom`, `bend2d`, `bend3d` (move) | 6 |
| `site/rack/scene3d.js` | 909 | `dom`, `cable-plugs`, `cables`, `bundle-view`, `stage`, `bend3d`, `route-context`, `covers`, `spare-loops`, `rack3d` (dynamic) (all move); `hover` (**stays**: cut 2); `webgl` (dynamic) (**stays**: cut 3) | 6 |
| `site/rack/cable-view.js` | 1,082 | `cables`, `bundle-view`, `dom`, `bend3d`, `bend2d`, `stage`, `part-path`, `route-context`, `spare`, `spare-loops`, `strap-size` (all move) | 7 |

`site/rack3d.js` is 1,794 lines. It is one module, but it moves in two
orders, cut as §4.4 says, and each line is in exactly one of them.

### 4.2 Modules that stay

These are in the graph above as an edge target, or import a module that
moves. They stay in the site and import the moved modules from the kit after
the switch (§5, orders 8 and 9).

| Module | Lines | Why it stays |
|---|---:|---|
| `site/rack/agent-text.js` | 369 | the WebMCP tools' sentences |
| `site/rack/hover.js` | 348 | hover, filter and selection paint: the page's |
| `site/webgl.js` | 66 | the page's WebGL check and its message |
| `site/rack/exports.js` | 878 | the page's downloads |
| `site/rack/side-elevation.js` | 565 | the side panes. A view, but not named in #1298 (§9) |
| `site/rack-page.js` | n/a | the page |
| `site/rack/drag.js`, `zoom.js` | 213, 157 | drag and zoom |
| `site/rack/*-panel.js`, `inspector.js`, `picker.js`, forms | n/a | the panels |
| `site/rack/agent-*.js`, `reading.js` | n/a | the WebMCP tools |
| `site/showcase/*`, `site/hero-3d.js`, `site/drawings-page.js` | n/a | other pages that import `elevation`, `face`, `faces`, `dom`, `cables` or `rack3d` |

Three modules that move keep a few lines in the site, because those lines
are page state or page text:

| Module | Stays in the site | Lines |
|---|---|---:|
| `stage.js` | `loadStage`, `saveStage`, `mountStage` (`localStorage`, the swatch buttons) | 31 |
| `covers.js` | `COVERS_KEY`, `loadCovers`, `saveCovers`, `mountCovers` (`localStorage`, the buttons) | 36 |
| `spare.js` | the `FIGURES_HELP` import and re-export, and `SPARE_HELP` | 3 |

The table in §4.1 and the totals in §5 count these modules whole, so each
total is an upper bound by at most 36 lines.

### 4.3 The cuts

**Cut 1: `spare.js` and `agent-text.js`.** `spare.js` imports `FIGURES_HELP`
only to export it again (lines 37 and 138). Its own code never reads the
sentence. So `spare.js` needs neither an argument nor the sentence. The
re-export is dropped, and `cable-panel.js`, its only reader, imports
`FIGURES_HELP` from `agent-text.js` directly. `SPARE_HELP` (line 140) is a
help sentence that only `cable-panel.js` reads, so it moves into
`cable-panel.js`. Both sentences stay in the site.

**Cut 2: `scene3d.js` and `hover.js`.** `scene3d.js` imports `paintLanded3d`
and `portKey`. `paintLanded3d` becomes the `highlight.landed` option (§2.3).
`portKey` is a pure one-line function
(`` (item, path) => `${item}|${String(path).split('-occupant')[0]}` ``). It
moves into `kit/rack/view/part-path.js` in order 4. `hover.js` then imports it
from the kit, so there is still one source.

**Cut 3: `scene3d.js` and `webgl.js`.** This cut is not in #1298.
`mountRack3d` imports `guard3d` from `site/webgl.js` dynamically (line 804).
It becomes the `guard` option (§2.3), and its message stays with the page.

**Cut 4: `rack3d.js` and `share.js`.** `kit/share.js` imports `three` and two
of its exporters. `toGLB` and `toUSDZ` become the `share` option (§2.3).

**The globals, by module.** Each one is read from the document that is
passed in, or from its `defaultView`:

| Module | Global it reads now |
|---|---|
| `dom.js` | `document` (`createElement`, `createElementNS`, `importNode`) |
| `elevation.js` | `DOMParser` |
| `face.js` | `DOMParser`, `XMLSerializer`. Its `fetch` stays: `kit/dist.js` reads the dist with `fetch` today, and the rule does not name it. |
| `cable-plugs.js`, `route-context.js` | `DOMParser` |
| `cables.js` | `window.CSS.escape` |
| `covers.js` | `document` in `layCovers2d`; `localStorage` and `document` in the lines that stay |
| `stage.js` | `localStorage` and `document`, in the lines that stay |
| `rack3d.js` | `document` (event listeners, the label canvases, the anchor SVG it parks in `document.body`), `DOMParser`, `XMLSerializer`, `HTMLCanvasElement.prototype`, `devicePixelRatio`, `ResizeObserver`, `requestAnimationFrame` |
| `scene3d.js` | the dynamic imports of `webgl.js` and `rack3d.js` |

`dom.js`'s helpers change signature: `el(doc, tag, attrs, kids)`,
`svgEl(doc, tag, attrs)` and `importDrawingNode(doc, kid)`. Alternatively,
`dom(doc)` returns the three helpers bound to `doc`. **Recommended:**
`dom(doc)`, because then a call site changes once per module and not once
per call.

### 4.4 How `createRackScene` is cut

`createRackScene` runs from line 145 to the end, line 1,794, as one closure.
It is cut into two modules. Each one keeps the closure's state it uses, and
the device part reaches the shell's state through one object that the shell
gives it.

**Order 2, the shell: `kit/rack/view/rack-scene.js`, 968 lines.** It holds
lines 1–101, 145–383, 505–682, 739–817 and 1,424–1,794:

- the module's constants (`VIEWS`, `PXMM_*`, the CPU-canvas hold);
- the options, scene, camera, renderer and controls;
- the frame cadence, `onDemand`, and "lighter while moving";
- `frameCamera`, the label sprites, and the rack's posts, holes and unit
  numbers (`buildPostPair`, `buildRack`: the rack surface's `frame3d`);
- the tags and their leaders, and `layoutTags`;
- `disposeTree`, `hydrate`, `fitUnits` and `buildAll`;
- `resize`, the render loop, context loss, and the returned API with
  `dispose`.

`buildAll` calls `overrideFaces`, `pullFaces` and `buildDevice` through the
device builder that order 3 installs. Until order 3 lands, a shell with an
empty stack draws the frame alone.

**Order 3, the devices: `kit/rack/view/rack-devices.js`, 826 lines.** It holds
lines 102–144, 384–504, 683–738 and 818–1,423:

- `faceFrames`, `MAT_SLOT` and `VISIBLE_FACES`;
- the relief scopes (`cappedScope`, `ownScope`, `scopeFor`) and the parts
  taken off (`pullFaces`);
- the ears (`rackEars`: the rack surface's `ears`);
- the face table, shared builds, `overrideFaces` and `buildDevice`;
- the anchors (`faceDoc`, `portAnchor`, `guideAnchor`, `cableAnchor`) and
  `deviceBoxes`.

It exports `createDeviceBuilder(shell)`. `shell` is
`{THREE, scene, relief, coarse, metrics, requestFrame, epoch, mounted,
document, opts}`, and the call returns `{overrideFaces, pullFaces,
buildDevice, anchors}`. `covers.js` moves in the same order, because its 3D
half acts on the device meshes as they land (`takeCovers`).

The two parts add up to 1,794 lines: 968 + 826. The reviewer can check them
from the line ranges above. The counts follow the ranges. The imports of
`faces`, `face` and `ear-holes` (lines 23, 24 and 27) are in the shell's
range, but they go to the device module with the code that uses them.

## 5. The orders

In graph order: no order imports a module from a later one. Totals count the
lines that move, at `5dbbd41bd3`. A module is in one order only, and every
module in §4.1 is in one.

| Order | What moves | Modules and lines | Total |
|---|---|---|---:|
| 1 | the 2D elevation | `elevation` 437, `face` 258, `settable` 62, `dom` 36, `ear-holes` 32, `faces` 22 | **847** |
| 2 | the 3D shell | `rack3d` shell part 968 | **968** |
| 3 | the 3D device meshes and covers | `rack3d` device part 826, `covers` 226 | **1,052** |
| 4 | the cable and bundle geometry | `bundle-view` 538, `bend3d` 322, `strap-size` 145, `spare-loops` 107, `bend2d` 102, `stage` 89, `part-path` 42 | **1,345** |
| 5 | route context, plugs and spare | `route-context` 737, `cable-plugs` 229, `spare` 140 | **1,106** |
| 6 | the cable drawing and the 3D view | `scene3d` 909, `cables` 512 | **1,421** |
| 7 | the 2D cable view | `cable-view` 1,082 | **1,082** |
| 8 | site switch: 2D | portrayal-site, after the kit release that holds orders 1 to 7 | deletes |
| 9 | site switch: 3D | portrayal-site, after order 8 | deletes |

All seven orders move 7,821 lines.

**Why `cables` goes with `scene3d` and not with `cable-view`.** `cables` and
`cable-view` together are 1,594 lines, over the limit. Both `scene3d` and
`cable-view` import `cables`, so `cables` has to arrive before either of them.
With `scene3d` it makes 1,421 lines, and `cable-view` then moves alone at
1,082. Each module stays in one order, and no order is over 1,500.

What each order also adds (new code, not counted above):

- Order 1 adds `kit/rack/view/view.js`: the handle, the pick and select
  plumbing, and `joinPath` and `splitPath`. About 80 lines. It adds
  `mountRack2d` over `drawElevation`, and the rack surface's `frame2d`,
  `placeOf` and `ears`.
- Order 6 adds the 3D pick (a raycast on click that reads the
  `device-<id>`, `cable-<id>` and `bundle-<id>` names and
  `userData.portrayalPath`), `mountRack3d`'s handle and the `guard` and
  `highlight` options. About 60 lines.
- Order 7 adds the `cables: true` option of `mountRack2d`.

**Each order, in the kit:**

- adds its modules under `kit/rack/view/` and their paths to
  `kit/package.json`'s `exports` (`"./rack/view/elevation"` and the rest);
- in order 1 only, adds `rack/view/*.js` to `kit/package.json`'s `files`
  (which publishes only `*.js` and `rack/*.js` now) and to its `test`
  script's `node --check` loop (which checks only `rack/*.js` now). Without
  them the view modules are left out of the published package and are not
  checked;
- adds a changelog fragment under `changelog.d/`, and **does not bump the
  kit version** (`CONTRIBUTING.md`: the version is bumped when the kit is
  published);
- carries its parity tests (§6) and the site tests that move with it (§7);
- passes the no-global rule. A test reads each module's source for the
  names in §4.3's table, and fails if one is used as a global.

**The site switches (orders 8 and 9)** happen in portrayal-site, after a kit
release that holds orders 1 to 7. They follow the kit-move design's D3: the
copies are deleted, with no shims.

- **Order 8, 2D.** The site imports the 2D modules from the kit, and deletes
  `elevation`, `face`, `faces`, `ear-holes`, `settable`, `dom`, `bend2d`,
  `bend3d`, `bundle-view`, `part-path`, `spare-loops`, `strap-size`,
  `route-context`, `cable-plugs`, `spare`, `cables` and `cable-view`. It
  deletes the moved part of `stage.js` and keeps its 31 lines. It also points
  the site's contract check, which names `site/faces.js` as the one place a
  face's file name is built, at the kit's module.
- **Order 9, 3D.** The site imports `mountRack3d` and `createRackScene` from
  the kit, passes `three`, `share`, `guard` and `highlight`, and deletes
  `rack3d.js`, `scene3d.js` and the moved part of `covers.js`. `hero-3d.js`
  and the showcase change their imports in the same pull request.

Each switch passes the Rack Builder's browser checks and WebMCP tool checks
before and after (#1298, "Done when").

## 6. Parity tests

Each order proves that the kit draws what the site drew. The goldens are
recorded from the site at a named commit. The first is `5dbbd41bd3`, and each
order names the site commit and the Portrayal commit whose `library/dist` it
recorded against. They use the existing fixtures:

- `spec/tests/fixtures/racks/acceptance.rack.json`
- `spec/tests/fixtures/cable-lay/cable-lay-rack.json`

The goldens go under `spec/tests/fixtures/rack-views/`, one file per fixture,
view and face, with the two commits in the file.

**2D (orders 1, 4, 5 and 7): the same SVG.** Both panes of each fixture are
compared, front and rear, with ears, metal and hit targets on. Orders 7 and
later also compare with cables on. Before the comparison, each SVG is
serialised with sorted attributes and numbers rounded to six decimals. The
two strings must be equal. Order 1 also checks that `select` draws the same
ring as `drawElevation({selectedId})`, and that a click on a device, a part
beside the rack and an empty unit each give the pick event in §2.2.

**3D (orders 2, 3 and 6): the same object names and counts.** After
`scene.complete()`, the test lists every object in the scene as `{name, type}`,
counts each pair, and compares the list with the golden. Order 2 compares the
fixture's frame with an empty stack: posts, holes and unit numbers. Order 3
adds the devices, their ears and their covers. Order 6 adds the cables,
bundles, straps, loops and bend rings. Every 3D order also checks dispose: it
mounts, waits for `ready`, disposes, and requires `renderer.info.memory`'s
`geometries` and `textures` to be back where they were before the mount.

**Where they run.** Portrayal's CI has no browser. The 3D tests need WebGL,
and the 2D tests need a DOM and an SVG parser, which the repository's fake
DOM does not provide. So the parity tests are a page under
`spec/tests/browser/`, which is run by hand like the pages already there. The
result is quoted in each pull request. The automated gate is the site's
own browser checks, which run in its CI against the kit's copy in `vendor/`
at orders 8 and 9. **This is a decision for the owner** (§10): the other
choice is a browser job in Portrayal's CI. That job is a change to how
changes are checked, so it is a one-way door under `CONTRIBUTING.md`.

The pure functions keep their node tests (§7), which do run in CI.

## 7. Which site tests move

The site's node tests in `tests/rack/` that test only moving modules move
with their module, into `spec/tests/js/`, with a `spec/tests/*_js.py` wrapper
as the kit's other rack tests have. A test that also reads a module that
stays is split, or stays.

| Site test | Reads | Moves with | |
|---|---|---|---|
| `skin-fetch` | `face` | order 1 | moves |
| `half-unit` | `ear-holes`, `rack-page`, `rack3d` | order 1 | split: the `ear-holes` cases move |
| `lamps-displays` | `settable`, `agent-tools`, `agent-context` | order 1 | split: the `settable` cases move |
| `zero-u` | `elevation`, `library`, `route-context` | order 5 | split: the `library` cases stay |
| `covers` | `covers` | order 3 | moves, apart from the `loadCovers` and `mountCovers` cases |
| `bend2d`, `bend2d-trunk`, `bend-near` | `bend2d`, `bend3d` | order 4 | moves |
| `bundle-view`, `tag-text` | `bundle-view` | order 4 | moves |
| `part-path` | `part-path` | order 4 | moves |
| `strap-paint`, `strap-size` | `stage`, `bundle-view`, `strap-size` | order 4 | moves |
| `spare-ducts` | `spare-loops`, `agent-text` | order 4 | split: the `agent-text` cases stay |
| `route-context`, `bend-findings`, `ring-marks`, `cable-width` | `route-context` | order 5 | moves |
| `tie-straps` | `bundle-view`, `route-context` | order 5 | moves |
| `cable-spare` | `spare`, `cable-panel`, `agent-text` | order 5 | split: the `spare` cases move |
| `cable-lay`, `zero-u-cords`, `bend-radius`, `reading` | moving modules and the WebMCP tools | none | stay |
| `hover-plugs` | `hover` | none | stays |
| `imports` | `rack-page`, `svg-export`, `cables` | none | stays, and is updated in order 8 |

These stay with the site: the browser checks (`check_rack_*`) for the
panels, drag, zoom, the WebMCP tools and the page; `tools/rack-speed.py`; and
`tests/mode3d/`. They are the before-and-after gate of orders 8 and 9.

## 8. One-way items

- **The export paths under `kit/rack/view/` become a contract** once the site
  or any other page imports them from a published kit. Renaming one after
  that is a breaking change for a kit consumer. The paths are:
  `./rack/view/view`, `./rack/view/elevation`, `./rack/view/dom`,
  `./rack/view/face`, `./rack/view/faces`, `./rack/view/ear-holes`,
  `./rack/view/settable`, `./rack/view/rack-scene`,
  `./rack/view/rack-devices`, `./rack/view/covers`, `./rack/view/bend2d`,
  `./rack/view/bend3d`, `./rack/view/bundle-view`, `./rack/view/stage`,
  `./rack/view/part-path`, `./rack/view/spare-loops`,
  `./rack/view/strap-size`, `./rack/view/route-context`,
  `./rack/view/cable-plugs`, `./rack/view/spare`, `./rack/view/cables`,
  `./rack/view/scene3d` and `./rack/view/cable-view`.
- **The handle in §2.2, the pick event and the path grammar in §2.4** are
  the same kind of contract. A field can be added to them later. A field
  cannot be renamed or removed.
- **The editor's API in §3** is additive. The one-rack behaviour it keeps
  is already a contract.
- **A kit release** that holds orders 1 to 7 is one-way, as every release is.
  The orders do not publish: the maintainer does, when the kit is published.

The orders themselves are two-way doors until that release. A move can be
reverted while nothing outside the repository imports it. The blast radius
is kit consumers, once the release is out.

## 9. Not in this piece

- `site/rack/side-elevation.js` (565 lines), the side panes. It imports
  `face`, `dom`, `elevation`, `bundle-view`, `cable-view`, `stage`,
  `route-context`, `strap-size` and `spare-loops`, so it could move after
  order 7 as an order of its own. #1298 does not name it.
- `hover.js`: the hover, filter and selection paint. Until it moves, the 3D
  view paints no selection of its own (§2.2, `select`).
- A second surface kind (§2.5), and the multi-rack editor itself (§3): both
  are separate pieces that build on this API.

## 10. Decisions for the owner

1. The handle (§2.2), the pick event and the path grammar (§2.4).
2. The `surface` seam (§2.5) as the place a backboard mounts.
3. The editor's multi-rack API (§3), with history per rack.
4. "No global" as the reading of the kit's rule for code that draws (§1):
   only the document that is passed in and its `defaultView`.
5. `dom(doc)` over a `doc` argument on every helper (§4.3).
6. `cables` with `scene3d` (order 6), so that no order is over 1,500 lines
   (§5).
7. Where the parity tests run: a page run by hand plus the site's CI at the
   switches, or a new browser job in Portrayal's CI (§6).

# Format stability: what can change, and what says so

Portrayal has six version numbers, and each answers a different question. This
page says what each one covers, what raises it, and what the project promises
about it while the package is at 0.x.

| Number | Where it appears | What it versions |
|---|---|---|
| `format` | every device manifest, component contract, listing and lab (`format: 1`) | the **file format** a manifest is written in |
| schema `v1` | the schema `$id`s and titles in `spec/schemas/` (device, component, listing and lab; the marked-up drawing; and the rack file) | for the manifest schemas, the same thing, named: schema v1 *is* format 1. `marks.schema.json` is v1 of the marked-up drawing, whose own key is `v` (1). `rack.schema.json` was first published under `/v1/`, describing rack file `version` 2; it now describes `version` 3 and is published under `/v2/`, the next unused label, never under its rack version number (below) |
| package | `version` in `pyproject.toml` (0.1.0) | the **tools**: the linter, the compiler, the indexers and the exporter |
| rack catalogue `format` | `rack.json` (`format: 1`) | the **catalogue** a rack tool reads in one fetch; its own number, apart from the manifests' `format` |
| rack file `version` | the Rack Builder's file (`format: "portrayal-rack"`, `version: 3`) | the **rack file** a user saves; `parseDoc` migrates an older one on load |
| `contract` | `devices.json` (`contract: 2` at 0.1.0) | the **published build** a consumer reads from `library/dist/`; `CHANGELOG.md` records each one |

The schemas are published at `https://portrayal.dev/schemas/v1/`, one file
per schema (`device.schema.json`, `component.schema.json`,
`listing.schema.json`, `lab.schema.json`, `rack.schema.json`), and that URL is each schema's `$id`, so an editor or a
validator that follows the `$id` finds the schema it names. `rack.schema.json` describes
the Rack Builder's own file (`format: "portrayal-rack"`, its own `version`, now 3), not a
manifest, so it is published as a schema of this repository but does not carry
format 1. Its label is a publication label only; the rack file's own `version` is
migrated on load by `parseDoc`, so each rack version is published under the next
unused label rather than overwriting the one before: version 2 under `/v1/`, which
stays as published, and version 3 (#921) under `/schemas/v2/rack.schema.json`,
since no manifest format had taken `/v2/`. The label is never a rack version
number, and a label once published is not reused. A new manifest format number is
published beside the old one under the next label no schema has taken (`/schemas/v3/`
now that the rack file holds `/v2/`); a published label is never reused for a
different format.

Each device and component also carries its own semantic version and lock, which
records what changed in *that hardware's drawing*. That is a separate system,
and [DESIGN §9](../spec/DESIGN.md) covers it: art is a patch, an addition is a
minor, and geometry or ids are a major.

## What is a breaking change

**To the format** (which raises `format`, and the schema label with it):
- a key is removed or renamed;
- a key's meaning changes, for example a unit, a frame or what a value refers to;
- validation starts rejecting a file that used to be valid.

Adding an **optional** key does not raise `format`. A file written without it
stays valid, and a reader that ignores it is unaffected.

**To the published build** (which raises `contract`): the same rule applied to
the files under `library/dist/`. A field a consumer reads is removed or renamed,
or its meaning changes. A new field does not raise it.

The two move independently. A format change can leave the build's shape alone,
and a change to the build can happen without any change to the files authors
write.

A new file in `library/dist/` is a new field in the same sense. It does not
raise `contract`; from the release that adds it, its shape is under `contract`
like every other file there. The elements file below was added this way, at
`contract: 2`.

## The elements file

Beside every compiled face, under the same name, is
`<device>[.<config>].<view>.elements.json`. It lists each element the face
draws, so a reader gets the face's tree without parsing the SVG or laying it
out. Everything in it is read from the SVG it sits beside; nothing is added.

```json
{
  "device": "agr110", "device-version": "8.2.8",
  "view": "front", "config": "ac", "configs": ["ac"],
  "viewBox": [0.0, 0.0, 438.4, 44.0],
  "source-sha256": "…", "components": {"std/sfp-ganged@1": "1.1.1"},
  "generator": {"tool": "portrayal-render", "version": "0.1.0"},
  "elements": [
    {"path": "chassis", "parent": null, "id": "chassis-faceplate", "class": "chassis",
     "box": {"x": 0.0, "y": 0.0, "w": 438.4, "h": 44.0}},
    {"path": "cutout:port-0", "parent": "port-0", "id": "cutout--port-0", "class": "cutout",
     "box": {"x": 14.39, "y": 2.47, "w": 14.25, "h": 10.4}},
    {"path": "port-0", "parent": null, "id": "port-0", "class": "port",
     "ref": "std/sfp-ganged@1:1.1.1", "media": "sfp-plus", "speed": "10g",
     "group": "sfp-plus", "group-role": "traffic", "rel-pos": "0",
     "box": {"x": 14.39, "y": 2.47, "w": 14.25, "h": 10.4},
     "connection-points": {"mate": {"at": [7.125, 5.2], "face": [21.515, 7.67], "dir": "front"}}}
  ]
}
```

**The header.** `device` is the face's `data-device`. `config` is the
configuration the file is named after, and `configs` is every configuration
that draws this face: a drawing is written once and shared (`configs[].files`
in `<device>.configs.json` says which file each configuration's face is).
`viewBox` is the SVG's, as four numbers. `source-sha256`, `components` (the
resolved component versions), `device-version` and `generator` are copied from
the SVG's `<metadata>`. The default configuration's unqualified copy,
`<device>.<view>.elements.json`, is the same bytes as the file it copies.

**One row per element**, in document order, one per address: a row has either
`path` (its `data-path`) or, for a part this face only sees as a projection,
`of` (its `data-of`). The two never collide; a projection of a part the face
also draws is that part's row. Each row may carry:

| key | from | value |
|---|---|---|
| `id` | `id` | the CSS-safe id |
| `class` | `data-class` | string |
| `ref` | `data-ref` | `<component>:<resolved version>`, as the SVG writes it |
| `media`, `speed`, `group`, `group-role`, `rel-pos` | the `data-` attribute of the same name | string |
| `states` | `data-states` | list: the lamp vocabulary |
| `for` | `data-for` | list: the owners, local paths or device-absolute `/<view>/<path>` |
| `inner` | `data-inner` | `true` for a port inside another port's housing |
| `connection-points` | `data-cp`, `data-cp-at`, `data-cp-dir`, `data-cp-on` on the part's markers | `{name: {at, face, dir?, on?}}`: `at` as written, in the part's own frame; `face`, the same point in the face's frame |
| `seat` | the path | the bay or cage this row's part is seated in, innermost first; absent on the chassis's own rows |
| `parent` | the tree | the key of the row this one lists under, or `null` |
| `box` | the geometry | `{x, y, w, h}` in the face's millimetres, or `null` |

A key whose attribute is absent is left out, except `parent` and `box`, which
are always present.

**`parent`** is the nesting the Explorer shows, by the same rule
(`faceTree` in `kit/swap.js`): the path's prefix, else for a projection the
nearest drawn element it sits inside, else for a `cutout:<id>` the row `<id>`,
else for a row with `data-for` its single local owner (a placed component
naming several owners does not nest under the first) or, when it has none
here (a lamp whose targets are all in another view), `chassis`. Anything else
is a root. A test runs the kit's function over every face in the build and
compares.

**`seat`** says which rows came from what the configuration seats and which
are the chassis's own. A bay's occupant is `<bay>/module` and everything under
it; a cage's is the element whose `data-behaviour` is `occupies`, and its seat
is the cage it names. It does not say whether the configuration named that
occupant or the bay or slot shipped it by default: one file serves every
configuration that draws the face, and two of them can seat the same part for
those two different reasons.

**`box`** is the union of the shapes under the row - `rect`, `circle`,
`ellipse`, `line`, `polygon`, `polyline` and `path` - each taken through the
full transform stack, with curves and arcs at their true extremes, so a
rotated circle's box is its own and not its square's. It leaves out three
things, because without a layout pass there is nothing exact to give: the
extent of `<text>` (it depends on the reader's fonts, so a legend that is only
text has `box: null`), stroke width (the box is the shape's, not its paint's),
and clipping and masking. A zero-sized shape is not drawn and adds nothing.
Numbers are rounded to 4 decimals (0.1 µm).

**The bytes** are deterministic: keys sorted, rows in document order, no
whitespace, a final newline. The build writes the file whenever it writes the
face, `--if-stale` included.

## The labs file

`labs.json` is every lab under `library/labs/`, each with `name`, `title`,
`description`, `rack`, `devices` and `links`. A lab names devices by `name` and
ports by placement id, and holds no geometry: a viewer finds port positions in
the compiled drawings. What it does resolve is where each device is. Every
placement keeps every key its lab wrote, and carries six more:

```json
{"id": "mgr-a", "ref": "fhd-cmp5dr", "on": "enc-4u", "face": "front", "unit": 3,
 "ru": 12, "mount": "rack-face", "host": "enc-4u", "side": null}
{"id": "duct-l", "ref": "cmv-sfd45u5w", "side": "left",
 "ru": 1, "face": "front", "mount": "rack-side", "host": null, "unit": null}
```

- `ru`: the lowest rack unit the device takes, counted from U1 at the bottom of
  the rack. A placement `on` a host has no `ru` of its own and is given one:
  the host's `ru` plus `unit` less one.
- `face`: `front` or `rear`. A rack device is always `front`; a rack-face part
  says which rail face it bolts to, and defaults to `front`.
- `mount`: the device's `chassis.mount`, `rack`, `rack-face` or `rack-side`.
  A `rack-side` part stands beside the rack on the side of an upright and
  takes no rack unit; its `ru` is the unit it starts beside, default 1.
- `host`: for a rack-face part, the id of the rack device on the unit behind
  it, whether the lab placed it `on` that device or by `ru`; otherwise `null`.
- `unit`: which of the host's rack units, from 1 at the host's bottom; `null`
  without a host.
- `side`: for a `rack-side` part, the attachment point it stands at, as the
  lab wrote it: `left` or `right` on a two-post frame, or `left-front`,
  `left-rear`, `right-front` or `right-rear` on a four-post one (#934). For a
  `rack-face` part narrower than the rack opening that states one, the rail it
  bolts to, `left` or `right`, seen from the front. Otherwise `null`. The four
  four-post names are new with #934 and did not raise `contract`: a reader
  that knows only `left` and `right` can read the side of the rack as the
  word before the hyphen.

They are new fields and did not raise `contract`, which is still 2. A reader that knows none of
them still finds `ru`, and draws a rack-face part as an ordinary device on its
rack unit; one that knows `mount` but not `rack-side` or `side` draws a
rack-side part across its 45 units, which is wrong and visible, as the
rack-face case was. A lab that fails its schema or a check (lint L139 to L142,
L153, L154) is not written, and the build stops.

## Rack PDUs

A rack PDU (#934, [`pdu-model-design.md`](pdu-model-design.md)) adds keys in
four places. None raised `contract`, which is still 2: each is new, and a
reader that does not know it finds every field it read before.

- **`pdu-class`**, at the top of `<device>.configs.json` and on each entry of
  `devices.json`: one of `basic`, `switched`, `metered-input`,
  `switched-metered-input`, `metered-branch`, `switched-metered-branch`,
  `metered-outlet` and `managed`, or `null` where the device is no PDU. It is
  DERIVED from `attrs.management.metering-scope` (`none`, `input`, `branch`,
  `outlet`) and `outlet-switching` (a boolean), and never stated. The names
  and the two keys are published for filtering, so renaming one is a format
  change.
- **`configs[].mount-points`** in `<device>.configs.json`: each mount point a
  configuration draws, `{"mates": "pdu-button", "at": 72.0}`, ascending by
  `at`, which is millimetres from the bottom of its view to the point's
  `mate`. A mount point is a placement of a `class: mount` part that declares
  `mates`. The pitch is the difference of two `at`s and is stated nowhere
  else. Always a list; `[]` on a device with none.
- **`attrs.power`** gains `input-plug` (now a `PART_POWER` slug, which on the
  one device that wrote it was prose), `input-cord`, `input-phase`,
  `input-wiring`, `input-voltage-v`, `input-current-a`, `plug-rating-a` and
  `capacity-kw`; attrs are flattened to `data-*` on every drawing, so these
  names are held as attribute names too.
- **The DCIM export** writes the input rating on the input power port's
  `description` and in the comments, with the derived class; an outlet's
  description names the breaker it runs `through` and its `lines`
  (`Through breaker-a, lines L1-L2`); and `feed_leg` is written only for a
  line-to-neutral outlet on a three-phase wye input (L1 `A`, L2 `B`, L3 `C`).
  A DCIM that imported a leg holds it.

The placement key `lines`, and `through` naming a fixed breaker placement, are
manifest keys: stating either is a minor version of the device, and changing
one a major. `pdu-button` is a mounting interface in
`spec/schemas/connectors.yaml`; a slot that presents it and the fit check are
#939's and #935's.

## The kits file

`kits.json` is every rail, bracket and slide kit in the library: each
component contract with `kind: kit`, the kind added beside `component` and
`module` in #905. A kit is a set of ordinary components that a device names
from `chassis.kits` and never places, so it is never an entry of
`components.json`, and `components_index.py` writes it here instead, on every
build. While the library holds no kit the file is `{"kits": []}`.

```json
{"kits": [{"ref": "acme/slide@1", "ns": "acme", "name": "slide", "major": "v1",
  "version": "1.0.0", "kind": "kit", "description": "...",
  "motion": "sliding", "travel": "full", "install": "drop-in",
  "parts": [{"ref": "acme/inner@1", "id": "inner", "count": 2}],
  "configurations": [{"id": "four-post", "racks": ["4-post"], "parts": ["inner"],
                      "depth": {"square": [631, 868]}, "rail-depth": 714}],
  "accessories": [{"kind": "cma", "ref": "acme/cma@1", "rail-depth": 845}],
  "superseded-by": null, "provenance": {"depth": "..."}}]}
```

Rows are sorted by `ref`, and every row carries every key above. A key the
contract leaves out is `null` (`travel`, `install`, `superseded-by`), an empty
string (`description`), an empty list (`accessories`) or an empty object
(`provenance`). `parts`,
`configurations` and `accessories` are as the contract writes them; the
component schema describes each key. A part is a ref, not geometry: the
geometry of a kit's parts is read from `components.json` by their refs.

The file is new, and did not raise `contract`, which is still 2. Removing or
renaming a key, or changing what one means, is a `contract` change; adding a
key is not.

### Ears and kits on a device

A device manifest names its kits under `chassis.kits` and says where its ears
can put the faceplate under `chassis.ears` (#906). Both keys are optional and
both are additive to format 1: `chassis.ears` was the string `behind` (#865),
which stays valid with its meaning unchanged, and it may now also be an
object.

```yaml
chassis:
  ears:
    behind: true            # optional; the same statement as the bare string
    h: 43.5                 # optional; mm the ears span, when not the chassis height
    y: 0.15                 # optional; mm from the bottom of the chassis to the ears
    color: "#1b1e21"        # optional; the ears' colour, when they are not silver
    positions:
      - {name: flush, at: 0, default: true}
      - {name: mid, at: 228, racks: [2-post], part: {kit: acme/slide@1, part: mid}}
  kits:
    - {ref: acme/slide@1, supply: in-box,
       depth: {config: four-post, range: {square: [685, 868]}}}
```

- A position's `name` is one of `flush`, `recessed`, `mid`, `rear` and
  `proud`, and is required. `label` is the vendor's word for it. `at` is
  millimetres from the front of the faceplate back to the plane the ears bolt
  to, positive when the ears are behind the faceplate, and is written only
  when a source gives it. At most one position is `default` (L160). `racks`
  takes the words a kit configuration's `racks` takes. `part` names a kit the
  device lists and the `id` of one of that kit's parts (L162).
- A kit entry's `ref` is a `kind: kit` (L161), listed once. `supply` is
  `in-box` or `optional`, and `variant: reversed` marks a reverse-mount kit.
  `depth` replaces the `depth` of one configuration of the kit for this device:
  `config` names the configuration and `range` has the shape that
  configuration's `depth` has (L163).
- Both keys are for a `rack` device only (L125). A kit is never placed,
  composed or seated in a bay (L5, L10).

In the device lock both keys are chassis surface, so stating either is a
patch, and a listed kit, its parts and its accessories join the `composed`
digest, so a kit edited in place asks each device that lists it for a patch.
Those are the refs `<device>.configs.json` reads to resolve each kit, below.
`h`, `y` and `color` stay surface now that the generic ear (below) is drawn from them:
that ear is drawn only when asked for and never in a published face, an
elements file or an export, so changing either moves nothing a consumer
caches a coordinate from. If the ears ever join the default build, `h` and `y`
become geometry, and moving them is itself a major for each device that
states them.

### The generic ear

A `rack` device that places no ears of its own has a generic L-bracket ear
(#909): a flange each side reaching from the body out to the 482.6 mm rack
face, with a slot over each rail hole, and a 30 mm leg back along the body.
It is `chassis.ears.h` tall, its bottom `chassis.ears.y` above the chassis's
(the chassis's full height from `y`, and 0, where they are absent), and its
flange's back face is on the plane the default position's `at` names (0, flush,
where there is none). It is silver (`#c8cacc`, `SILVER` in ears.py, `EAR.SILVER`
in relief.js) unless `chassis.ears.color` states another, because most network
gear has bare or plated steel ears even when its faceplate is black; the plan
carries the colour as `color`. The library still draws devices without their ears, so
the default build is unchanged:

- `render.py --with ears` draws it on all six faces, as the groups `ear-left`
  and `ear-right` (`data-class="ear"`, `data-generic="ear"`), the ids and the
  tag `common/rack-ear@1` is drawn under; the viewBox grows round it and the
  root carries `data-face-w` and `data-face-h`, as for any part beyond its face.
- The kit's viewer builds it when a host asks: `createViewer(el, {ears: true})`
  or `viewer.setEars(true)`; `viewer.ears()` returns the plan drawn, or `null`.
  relief.js `genericEars(chassis, faceW)` makes the plan from configs.json.
- A page draws it over a published face in 2D with the kit's `ears2d.js`
  (`drawEars`, `clearEars`): the shapes, ids and colours `render.py --with
  ears` writes, in a `<g data-overlay="ears" pointer-events="none">` that is no
  part (no `data-path`), with the viewBox grown the same way. The Explorer
  offers it as a toggle, off by default.

A device gets none when it is not a `rack` device, states `ears: behind`, has
a front as wide as the rack face (its ears are in the drawing), or still places
`common/rack-ear@1` or anything under `optional: ears`. That last check is
2D only: those ears are never in a published face, so the 3D scene, which is
built from the published faces, gives such a device the generic pair. L164
warns when `y + h` is above the chassis, and L165 when two positions have the
same `name` and `label`.

### Ears and kits in configs.json

`<device>.configs.json` carries both under `chassis`, absent where the device
states neither (#907):

```json
{"chassis": {"...": "...",
  "ears": {"h": 43.5, "y": 0.15, "positions": [
    {"name": "flush", "at": 0.0, "default": true},
    {"name": "mid", "at": 228.0, "racks": ["2-post"],
     "part": {"kit": "acme/slide@1", "part": "mid"}}]},
  "kits": [{"ref": "acme/slide@1", "supply": "in-box", "variant": null,
    "depth": {"config": "four-post", "range": {"square": [685, 868]}},
    "version": "1.0.0", "description": "...",
    "motion": "sliding", "travel": "full", "install": "drop-in",
    "configurations": [{"id": "four-post", "racks": ["4-post"],
                        "parts": ["inner"], "depth": {"square": [685, 868]}}],
    "parts": [{"ref": "acme/inner@1", "id": "inner", "count": 2, "version": "1.0.0",
               "class": "bracket", "size": {"w": 20, "h": 40}, "body": null}],
    "accessories": [{"kind": "cma", "ref": "acme/cma@1", "version": "1.0.0",
                     "class": "bracket", "size": {"w": 30, "h": 40}, "body": null}]}]}}
```

- **`ears` is an object, always.** The bare string `ears: behind` is
  published as `{"behind": true}`; an object is published with the keys it
  states (`behind`, `h`, `y`, `color`, `positions`) and no others, so a reader
  asks `ears.behind === true` and reads `ears.positions || []`. `color` is the
  string the manifest writes, and absent means silver. `h`, `y` and each
  position's `at` are floats. A position keeps every key the manifest writes.
  From #865 to #907 the bare string was published as the string, on main
  only; no release carried it, though the site once vendored a build that
  did. The one device that states it,
  `fs/uscmh-sfdabsb2u`, now publishes the object.
- **Each listed kit is resolved inline**, in the order the device lists them.
  A row carries every key above: the device's `ref`, `supply`, `variant` and
  `depth` override (`null` where absent), then the kit's `version`,
  `description`, `motion`, `travel`, `install` (`null` where the kit leaves
  them out; `description` is an empty string where the kit has none),
  `configurations`, `parts` and `accessories`. A part keeps `ref`,
  `id` and `count`, and an accessory every key the kit writes; each gains its
  contract's `version`, `class`, `size` and `body` (`null` where absent).
- **The override is applied.** A `depth` override replaces the `depth` of the
  configuration it names, so `configurations` are what this device can do; the
  row's `depth` says that one was overridden. The kit's own figures are in
  `kits.json`.

Neither raised `contract`, which is still 2: `kits` is a new key, and `ears`
changed shape before any release published it, with nothing in the kit
reading it. From the next release both are under `contract` like every other
key.

## The rack file: parts beside the rack and on one rail

Two keys were added to rack file `version` 2 in #926, and neither raised it:

- **`zeroU` entries.** The record every rack has always carried, which the
  schema called reserved, now holds the parts that stand beside the rack:
  `{id, ref, cfg, label, at, offsetMm, between?}`. `at` is an attachment point
  of the frame, `offsetMm` the part's bottom above the bottom of the rails (a
  whole number of U as the kit writes it), and `between: true` a part that
  serves the next rack too. `parseDoc` keeps the record as written, and gives
  an entry with no id, or a repeated one, an id of its own.
- **`side` on an item**: `left` or `right`, the rail a part narrower than the
  rack opening is on. `parseDoc` keeps it; a reader that drops it puts the
  part across both rails, which is visible and is what it was before.

The schema describes the new keys and does not constrain them, so every file
that validated before still validates: an entry of `zeroU` is an object, as it
always had to be, and the kit places only the entries it can read
(`id`, `ref` and `at` as non-empty strings) and keeps the others as written.
Constraining their types, so that a validator refuses `at: 5`, would reject a
file that validates today, and so would be a format change.

The version stayed 2 because both keys are optional and an older reader of
version 2 reads the rest of the rack whole: it keeps `zeroU` as written and
draws nothing beside the rack, and it drops `side`, so its next save puts a
bracket back across both rails. The 1 to 2 bump made an older page refuse a
file rather than draw a manager as a device over its host. Here it was decided
(2026-10-08) to accept the older reader's loss, because no `@portrayal/kit`
release older than these keys was ever published: the one reader that existed,
portrayal-site's, already kept both.

## The rack file: bundles, version 3

Cable bundles (#921, [`cable-bundles-design.md`](cable-bundles-design.md))
raised the rack file to `version` 3, and its schema is published under
`/schemas/v2/` (above). A rack gains an optional `bundles` array, each bundle
`{id, number, label, members: [{cable, a?, b?}], route, straps?}`, described
by `$defs` `bundle`, `member` and `strapSpacing`; `member.a`, `member.b` and
`bundle.route` are `$defs/waypoint`. A rack that was never given a bundle has
no `bundles` key and saves as it was.

- **Migration.** 2 to 3 is the identity, as 1 to 2 was: every version-2 file is
  a valid version-3 file. `parseDoc` migrates whatever it opens and `serialize`
  writes 3, so a page with this kit saves every document it opens as version 3.
- **An older reader refuses a version-3 file.** Every page and kit from before
  #921 reads up to version 2, so it refuses the file with its "this page reads
  up to version 2" sentence rather than opening it. That is the point of the
  bump: an older `parseDoc` rebuilds a rack from the keys it names, so it
  would drop `bundles` and erase them on its next save, and an older page
  would edit a member's route alone. The refusal also protects `side` (#926),
  which a version-2 page drops. This is a one-way door: there is no way back
  to version 2 for a file a newer page has saved, and the `/v2/` label is
  never reused.
- **The repairs** are `parseDoc`'s, so every reader gets the same rack. The
  shapes are repaired silently, as a cable's are: a bundle with no usable id
  or a repeated one gets a fresh id, a member that is not `{cable}` and a peel
  point that is no waypoint are dropped, and a number that is not a whole
  number from 1 is renumbered. The references are repaired with a note: a
  bundle whose id another thing in the rack has, a member naming no cable, a
  cable in two bundles and a number used twice are each repaired, and
  `parseDoc(input, {notes})` says so, one sentence per repair naming its
  rack. No note is kept in the file.

## The cable types file

`cable-types.json` names the cable types a rack tool can lay: each one's
media, a typical outside diameter and its minimum bend radius, every figure
with its source. `cable_types_index.py` writes it from
`spec/schemas/cable-types.yaml` and refuses a table that fails its checks, so
the build stops. It is new at `contract: 2` and did not raise it.

```json
{"format": 1, "version": "1.0.0", "generated-from": "spec/schemas/cable-types.yaml",
 "sources": {"foa-tia568": {"title": "...", "url": "https://..."}},
 "types": {"cat6a": {"id": "cat6a", "label": "Cat 6A U/UTP", "media": "cat6a",
   "family": "copper", "shield": "U/UTP", "od_mm": 7.5, "od_sources": ["portrayal-estimate"],
   "min_bend_radius": {
     "installed": {"xOD": 4, "basis": "standard", "sources": ["elliott-min-bend"]},
     "loaded": {"xOD": 8, "basis": "standard", "sources": ["elliott-min-bend"]}}}}}
```

`format` is 1 and versions the shape: a removed or renamed key raises it, a
new key does not. `version` versions the table's contents, so a changed
figure is deliberate: a corrected value or a new type is a minor, a removed
type or a changed id is a major.

Each type, keyed by its `id`, always carries:

- `id`, `label`, and `media`: the Rack Builder cable media it is a kind of.
  The bare ids `os2`, `om3`, `om4`, `om5`, `cat6`, `cat6a`, `dac` and `aoc` are
  those media values themselves, so a rack cable's media names its type. A
  refinement (`cat6a-ftp`, `os2-g657a2`, `dac-26awg`) has its own id and
  names the media it refines. `power` is the media of the power cords, which
  no Rack Builder media names yet.
- `family`: `fiber`, `copper`, `dac`, `aoc` or `power`.
- `od_mm` and `od_sources`: a typical outside diameter, a sketch and not a
  measurement of any one cable.
- `min_bend_radius`: `{installed, loaded}`. Installed is the radius once the
  cable is in place and unloaded, which a route or a bundle is checked
  against; loaded is the radius while it is pulled, and is data only. Each is
  `{mm}`, a fixed radius, or `{xOD}`, a multiple of `od_mm`, with `basis`
  (`standard` or `convention`), `sources` (keys of `sources`), and optionally
  `note` and `unverified: true`, which marks a placeholder. `loaded` is `null`
  where no source gives one; `installed` is always present.

A type may also carry `fiber` (`mode`, `grade`, `core_um`, and for a named
class `class` and its own `min_bend`), `shield` or `awg`. A `power` type
always carries `conductor`, the cord it is made of (`H05VV-F 3G1.0`), so the
same connector pair on another cord (a North American SJT) is a type of its
own. A fibre type's installed radius is the cord's cable rule;
`fiber.min_bend` is the fibre class's macrobend test radius, kept as data
for a consumer that knows the cord allows the tighter figure.

The kit's `rack/cable-types.js` reads it: `radiusMm(type)` turns a radius into
millimetres, `bendLookup(types)` gives a cable's installed radius from its
`type` when the table has that type, else from its `media`, and `loadCableTypes(dist)` fetches the file and
refuses any `format` but 1.

## The rack catalogue

`rack.json` is the catalogue a rack tool reads in one fetch, so it need not open
every device's index. It is written by `rack_index.py` after the compiled faces
exist, from `devices.json`, each `<name>.configs.json` and the default
configuration's front, rear and top views.

```json
{"format": 1, "generated-from": "...", "devices": {"fhd-cmp5dr": {"...": "..."}}}
```

`format` is 1. Each device, keyed by `name`, always carries `manufacturer`,
`model`, `family`, `ru`, `h`, `w`, `d`, `airflow`, `default`, `configs`
(the names of its configurations) and `kind`. Four keys appear only when the
device has them:

- `mount`: the device's `chassis.mount`, present only when it is not `rack`.
- `shell`: `chassis.shell`, `sheet` for a body that is a sheet and not a box.
- `capacity`: `{"count", "basis"}`, the cable capacity the vendor states.
- `guides` and `passes`: per view (`top`, `front`, `rear`), the sorted ids a
  cable route can pass through on the default configuration's drawing.

`ru` is `chassis.ru` when stated (0 included, for a zero-U part), else the
height over 44.45 mm, at least 1. Removing or renaming a key, or changing what
one means, is a contract change and raises `format`; adding a key is not.

`kind` is an advisory word for what the device is, for searching a catalogue,
read from the manifest's `profile` and the vendor's own words. Today its words
are `switch`, `router`, `network device`, `server`, `pdu`, `patch panel`,
`optical`, `cable manager`, and `device` when the profile says no more. The key
is part of the format; its vocabulary is not. A word may be added, split or
refined, and a device may move from one word to another, without a format
change, so a reader should not treat the list above as closed.

`devices.json` gained `profile`, the manifest's device class. It mirrors the
profiles in `spec/schemas/profiles.yaml` and follows that file. It is a new
field, so `contract` stays 2: a reader that does not know it still finds every
field it read before.

## What else a consumer holds

Three more things reach a consumer outside this repository, and none of them
has a number of its own.

**A component major.** A manifest pins a component by name and major
(`name@2`), so removing a major breaks a manifest that pins it. While the
package is at 0.x, a superseded major may be removed, and every removal is
listed in `CHANGELOG.md` with the ref that replaces it. From 1.0, a retired
major is deprecated for at least one release before it is removed. The
deprecation is the `superseded-by:` key the schema already has, on the
retired major's contract, naming the ref that replaces it. L89 telling a
superseded major that still ships from a dead one is pending
(roc-ops/Portrayal#448).
DESIGN §9 has the reasoning.

**A lint code.** A device manifest waives a rule by its code (`lint.waive`),
so lint codes are never renumbered or reused. A rule that is deleted keeps its
code, listed as retired, and a new rule always takes a new code. A test pins
every code ever issued, so a code that moves or is handed to another rule
fails the suite.

**The DCIM exports** under `library/exports/` (NetBox and Nautobot device and
module types, and the fibre maps) are generated from the manifests and are not
covered by the `contract` number, which versions `library/dist/` only. They
follow the DCIM's own schema, and what can break is what an already-imported
record is called: a model name, a port name, a bay position. Before 1.0 such a
change is allowed, and it is announced in `CHANGELOG.md`, marked **BREAKING for
DCIM data already imported**, with what it renames. From 1.0 it is treated as
a `contract` change is.

## What is promised before 1.0

The package is at 0.x, and at 0.x the promise is deliberately small:

- **The tools read the current format only.** When `format` goes up, files are
  migrated in the same change. Older files are not read side by side.
- **Every breaking change is announced.** A `format` or `contract` change, a
  DCIM export change that re-files imported data, and a removed component major
  are each listed in `CHANGELOG.md`, with what to change in a file or a
  consumer to move across.
- **The version says so.** A change that raises `format` or `contract` also
  raises the package's minor version, so 0.1 to 0.2 is where to look.

## What 1.0 will promise

From 1.0, a change that raises `format` or `contract` is a major version of
the package. The **previous** format stays readable, and the previous
`contract` stays documented, for one release after the change, so a consumer
has a release in which to move.

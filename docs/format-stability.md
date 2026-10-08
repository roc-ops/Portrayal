# Format stability: what can change, and what says so

Portrayal has six version numbers, and each answers a different question. This
page says what each one covers, what raises it, and what the project promises
about it while the package is at 0.x.

| Number | Where it appears | What it versions |
|---|---|---|
| `format` | every device manifest, component contract, listing and lab (`format: 1`) | the **file format** a manifest is written in |
| schema `v1` | the schema `$id`s and titles in `spec/schemas/` (device, component, listing and lab; the marked-up drawing; and the rack file) | for the manifest schemas, the same thing, named: schema v1 *is* format 1. `marks.schema.json` is v1 of the marked-up drawing, whose own key is `v` (1). `rack.schema.json` is also published under `/v1/`, as its first publication label, but describes rack file `version` 2; a later rack schema is published under the next unused label, never under its rack version number (below) |
| package | `version` in `pyproject.toml` (0.1.0) | the **tools**: the linter, the compiler, the indexers and the exporter |
| rack catalogue `format` | `rack.json` (`format: 1`) | the **catalogue** a rack tool reads in one fetch; its own number, apart from the manifests' `format` |
| rack file `version` | the Rack Builder's file (`format: "portrayal-rack"`, `version: 2`) | the **rack file** a user saves; `parseDoc` migrates an older one on load |
| `contract` | `devices.json` (`contract: 2` at 0.1.0) | the **published build** a consumer reads from `library/dist/`; `CHANGELOG.md` records each one |

The schemas are published at `https://portrayal.dev/schemas/v1/`, one file
per schema (`device.schema.json`, `component.schema.json`,
`listing.schema.json`, `lab.schema.json`, `rack.schema.json`), and that URL is each schema's `$id`, so an editor or a
validator that follows the `$id` finds the schema it names. `rack.schema.json` describes
the Rack Builder's own file (`format: "portrayal-rack"`, its own `version`, now 2), not a
manifest, so it is published under `/schemas/v1/` as a schema of this repository but does
not carry format 1. The `/v1/` is its publication label; the rack file's own `version`
(2 today) is migrated on load by `parseDoc`, so a later rack version is published under the next
unused label (`/schemas/v2/` if no manifest format has taken it, else the label after) rather than overwriting
`/v1/`; the label is never a rack version number, and a label once published is not reused. A new format number
is published beside the old one under its own label (`/schemas/v2/`); a
published label is never reused for a different format.

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
- `side`: `left` or `right`, seen from the front, for a `rack-side` part (the
  upright it stands beside) and for a `rack-face` part narrower than the rack
  opening that states one (the rail it bolts to); otherwise `null`.

They are new fields and did not raise `contract`, which is still 2. A reader that knows none of
them still finds `ru`, and draws a rack-face part as an ordinary device on its
rack unit; one that knows `mount` but not `rack-side` or `side` draws a
rack-side part across its 45 units, which is wrong and visible, as the
rack-face case was. A lab that fails its schema or a check (lint L139 to L142,
L153, L154) is not written, and the build stops.

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
  refinement (`cat6a-stp`, `os2-g657a2`, `dac-26awg`) has its own id and
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
class `class` and its own `min_bend`), `shield` or `awg`. A fibre type's
installed radius is already the larger of its cable rule and its fibre
class's limit; `fiber.min_bend` is kept for a consumer that knows the cord
allows the tighter figure.

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

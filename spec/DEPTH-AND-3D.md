# Depth and 3D

How Portrayal turns flat, standards-derived SVG drawings into dimensional 3D views —
recessed ports, protruding handles, see-through vents, and removable modules —
without maintaining a second, hand-built 3D asset for every device.

---

## 1. Why this exists

Portrayal's source of truth is a **2D, declarative, plain-text drawing**: YAML
contracts plus SVG skins, compiled into flat SVG where every component is
individually addressable. That is deliberate — it is diffable, reviewable,
mergeable, and it maps cleanly onto ENTITY-MIB/YANG component trees.

But a flat faceplate is a poor likeness of real hardware:

- Ports are *holes*. A QSFP28 cage is a 37 mm tunnel, not a dark rectangle.
- Handles, latches, thumbscrews, ground studs and bezels **stick out**.
- Vents are **openings**, not painted honeycomb.
- FRUs are **objects** that come out of the chassis.

Three ways to get 3D were considered:

| Approach | Why not |
|---|---|
| Hand-model each device (glTF/STEP) | A second source of truth that instantly drifts from the drawing; unreviewable in a PR; enormous per-device cost. |
| Photogrammetry / LiDAR scans | Good for organic shells, but ±1–10 mm, one scan per unit, and it can't tell you *what* a surface is. Useful as reference, not as the model. |
| **Derive 3D from the 2D drawing + declared depth** | One source of truth; a handful of numbers per component; every device gets it for free. |

We took the third. The **drawing stays canonical**; 3D is a *rendering* of it,
the same way the compiled SVG is a rendering of the manifest.

The other half of the argument is provenance. Portrayal already tracks where every
width and height came from (`standards.yaml`, datasheets, calipers, photos).
Depth is just one more dimension with the same discipline — a QSFP cage is
37 mm deep *because SFF-8663 Fig 4-1 says so*, and that citation lives next to
the number. Nothing about the 3D view is artistic invention.

---

## 2. The core idea

> **2D art says what a thing looks like. A few declarative numbers say how it
> sits in Z. The viewer combines them.**

Nothing in the 3D pipeline knows what an RJ45 is. It knows that *this node in
this skin is a cavity 16 mm deep with metallic walls*, and that *that node is a
tube handle standing 12.7 mm proud*. The semantics stay in the contracts.

Three layers, matching the rest of Portrayal:

```
standards.yaml          depth: 37.0        (governs, cited, lint-enforced)
        │
contract.yaml           size: {w,h,d}      (component adopts the standard)
                        relief: {...}      (how its own art sits in Z)
                        body:   {...}      (module enclosure behind the face)
        │
compiled SVG            data-depth="37"  data-z-out="12.7"  data-vent="25" ...
        │
3d.html                 cavities, protrusions, domes, tubes, holes, FRU groups
```

The compiled SVG is the hand-off. Any consumer — our viewer, a future exporter,
someone else's tool — can read the depth model straight off the artifact
without parsing YAML.

---

## 3. Author-facing vocabulary

### 3.1 Component depth

```yaml
size: {w: 14.5, h: 10.0, d: 41.0}     # d = recess depth behind the panel face
conforms: sfp                          # lint checks w/h/d against the registry
```

A component with `size.d` becomes a **cavity**: the viewer punches its aperture
out of the faceplate texture and builds a real recess behind it.

### 3.2 `relief` — how a component's own art sits in Z

```yaml
relief:
  wall: '#aab0b7'        # cavity wall colour (metallic cage lining)
  cavity: inlet-face     # skin node whose shape is the recess (default: whole component)
  round: true            # circular cavity (countersunk screws)
  features:
    - {node: pin-earth, top: 12.2, color: '#c0c5cb'}
```

Each feature names a **node id in the skin** and says how it leaves the plane:

| Key | Meaning | Used for |
|---|---|---|
| `top` | rises this far above the cavity floor | C14 inlet pins, USB tongue |
| `sink` | pocket this far *beyond* the floor | RJ45 clip keyway, screw slots |
| `out` | protrudes this far from the panel face | bezel plates, latches, lid stampings |
| `dome` | domed cap, apex proud / rim inset | LEDs, bulged fan guards |
| `cyl` | cylinder (radius from the node's bbox) | ground studs, thumbscrews, coax barrels |
| `bar` | round tube along the node's long axis | handle crossbars |
| `uhandle` | complete U-shaped tube handle from one node | fan/PSU pull handles |
| `lift` | standoff: feature starts this far off the face | stacked washers, floating bars |
| `knurl` | knurled side surface | thumbscrews |
| `vent` | the node's dark cells become real holes | grilles, mesh fields |
| `color` | side colour (omit → sampled from the node's own art) | anything |

`uhandle` is a good example of the philosophy: rather than making authors
assemble legs + elbows + bar, one node declares "this is a bent-tube handle
this far proud" and the viewer generates legs, quarter-torus corners and the
crossbar. Authors describe *hardware*, not geometry.

### 3.3 `body` — the module behind the faceplate

A faceplate alone is not a PSU. `body` gives a component a real enclosure:

```yaml
body:
  depth: 195                       # how deep the module is
  color: '#b9bec4'                 # sides with no art
  footprint: {at: [4, 0], size: [44.6, 40]}   # body smaller than the face
  plate: {at: [0.8, 0], size: [47.8, 40]}     # faceplate slab bounds
  travel: 88                       # captive: pulls out this far and stays in
```

Per-side art lives beside the skins as `skins/body-{left,right,top,bottom,rear}.svg`
— the module's label, EMI grate, mounting rails, card-edge connector. Each side
is drawn **as photographed from outside that side**, the same convention device
side views use.

- `footprint` exists because mounting flanges are part of the *faceplate*, not
  the body: the AS7726 fan is a 44.6 mm cube behind a wider tab-bearing plate.
- `plate` trims the faceplate slab to its art so no bare slab edge shows.
- `travel` marks a module **captive** — the info tab slides 88 mm out of its
  115 mm slot and stays in the chassis. Omitting it means removable: the module
  fully clears the enclosure.

### 3.4 Device-level decor

Chassis decoration gets the same treatment in `device.yaml`:

```yaml
decor:
  - {at: [46, 0.8], size: [314, 7.4], pattern: vent, vent: 25}   # real holes, 25 mm interior
  - {at: [55, 22], size: [1.8, 462], fill: '#2e3236', sink: 1}   # pressed lid groove
  - {at: [8, 12], size: [40, 3], fill: '#2e3236', out: 1}        # raised stamping
  - {at: [435.6, 1], size: [2.8, 41.5], pattern: vent, vent: 25,
     pattern-offset: [0, 2.555]}        # phase-align the hex lattice across a corner
```

---

## 4. How the viewer builds it

`library/demo/3d.html` reads only compiled SVGs plus `components.json`. It
never reads YAML.

`components.json` is the LEAN half of a two-file index: identity, size, skins,
files, body, attrs, elements - what a viewer needs to draw a part. The full
`provenance` and `relief` blocks live beside it in `components-detail.json`,
keyed by the same `ns/name@major` ref. Nothing was dropped; the split exists
because those two keys were 88% of a file every demo page fetches on load, and
no viewer reads either. `library/demo/part.html` fetches both and merges them.

**Faces.** Each view (front, rear, left, right, top) is rasterised to a canvas
at 4 px/mm and applied to a `BoxGeometry` sized from the chassis. Relief meshes
are built in a **local face frame** (x right, y up, +z out of the face) and a
per-face group transform orients them, so one code path serves all faces.

**Cavities.** For every `data-depth` group: the cavity node's own art is
rasterised and used as a `destination-out` eraser on the face texture (so the
hole is exactly the aperture shape, trapezoid or circle included), then four
double-sided walls, a textured floor plane at the back of the recess, and a
dark exterior back are added. Interior features become their own boxes.

**Protrusions.** `out`/`cyl`/`bar`/`uhandle` nodes are rendered *standalone*
from their own SVG nodes — which is what lets a bezel plate carry a
plug-shaped aperture and LED holes as transparent alpha — then extruded and
placed proud of the face.

**Vents.** The vent node's raster is used as an eraser too: dark cells vanish,
the metal web survives, and an open-fronted dark box provides the interior.

**Lighting.** Face art is unlit (`MeshBasicMaterial`) so the drawing renders
exactly as authored. Only relief geometry is `MeshLambertMaterial`, so walls,
tubes and studs shade with orientation while the artwork keeps its colours.

**FRU animation.** Every relief item is tagged with its owning module (the
nearest `data-path` root that is a bay module or captive tab, matched by
`data-class` *and* `data-ref` — contract elements can share a class name).
Each module gets a subgroup, its face art is moved into that subgroup and
cleared from the chassis texture, and a bay recess is left behind. Buttons then
tween the subgroup along the face normal. Because the module's cavities,
handles, LEDs, vents and six-sided body all live in that subgroup, the whole
assembly travels together.

---

## 5. Rules learned the hard way

These are load-bearing. Most were bugs first.

1. **Clear, never fill.** Patching the chassis texture with opaque colour hides
   everything behind it — the C14 pins vanished this way. Use `clearRect`;
   alpha is what lets you see in.
2. **Everything at the panel plane needs an open front.** Vent boxes, body
   boxes and bay recesses must have an invisible +z face, or they occlude the
   cavities in front of them.
3. **`alphaTest` on every punched texture.** Without it, alpha-0 pixels still
   write depth and occlude the interior.
4. **Raised nodes are hidden from face rasters.** A handle exists as geometry;
   leaving it in the flat texture too paints a ghost — and if it overlaps a
   vent, the eraser shreds it into fragments.
5. **Art drawn over a vent must become a feature** (or the grille must carve a
   solid patch under it). The F2B silkscreen and the fan handle both taught
   this.
6. **Never reason about mirroring in prose — measure it.** Bottom faces render
   180° from naive authoring; rear-face interiors need *no* mirror
   compensation. Every flip in this codebase was settled by screenshot.
7. **Colour collisions read as missing geometry.** A domed guard's web drawn
   the same colour as the backdrop behind its holes looks like flat black in
   2D.

---

## 6. Worked example: adding depth to a new port

```yaml
# std/sfp/v1/contract.yaml
size: {w: 14.5, h: 10.0, d: 41.0}    # w/h cited (SFF-8432); d still estimated
conforms: sfp
relief:
  wall: '#aab0b7'                     # bright cage lining
  features:
    - {node: collar, out: 1.0, color: '#7d848c'}   # mouth stands 1 mm proud
```

That is the whole change. Because every SFP port on every device composes this
core, all of them gain a 41 mm recess with metallic walls and a proud collar on
the next render — no device file is touched.

---

## 7. Scope and limits

- **It is relief, not CAD.** Extrusions, cylinders, tori and domes — no
  fillets, chamfers or curved sheet metal. It is meant to read correctly at
  rack-elevation and inspection distances, not to be manufactured from.
- **Bottom faces are texture-only** in device view (no relief pass yet).
- **Estimated depths are marked.** `depth-confidence: verified` means a cited
  spec; `estimated` means a plausible number pending ingestion of its source.
  The 3D view inherits the provenance discipline of the 2D drawing.
- **Physical scans remain useful** for sculpted shells and as intake reference
  — they just aren't the model.

## 8. Where things live

| Path | What |
|---|---|
| `spec/schemas/standards.yaml` | governed cutouts + `depth`, `depth-confidence` |
| `spec/schemas/component.schema.json` | `size.d`, `relief`, `body` |
| `spec/schemas/device.schema.json` | decor `vent`, `sink`, `out`, `pattern-offset` |
| `spec/tools/portrayal/render.py` | emits `data-depth`, `data-z-*`, `data-vent`, `data-groove` |
| `spec/tools/portrayal/lint.py` | L9 (registry match incl. depth), L11 (relief nodes exist) |
| `spec/tools/portrayal/components_index.py` | publishes compiled components + body side art, and both halves of the index |
| `library/demo/3d.html` | the viewer: device mode and `?component=ns/name@major` |

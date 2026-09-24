# Tilted faces: facets, and the parts that sit on them

Status: design agreed 2026-09-24. Implementation is on `claude/tilted-facets`.

## Why

Some faceplates carry their connectors on surfaces that are not parallel to the panel:

- **Nokia 7360 ISAM FX NT cards (FANT-H, FANT-M):** the 1PPS/10MHz SMA jacks and the two QSFP28
  cages sit in a housing angled about 30 degrees upward.
- **NT I/O cards (FNIO-A, FNIO-D):** every cage sits on a 45-degree sawtooth tooth.
- **Casa UPS-32x4:** each cage is angled 45 degrees for fibre bend radius.

The format could only say that a part is face-on. So these were drawn face-on at full height, with
shading painted into the skin as a hint. A reviewer caught it by eye. It is wrong in two ways:

- **2D:** a tilted port should be foreshortened.
- **3D:** its cavity, and any optic seated in it, should run along the slope, not straight back into
  the panel.

## Decisions taken

1. **The angle belongs to the faceplate, not to each port.** A relief feature declares a *facet*;
   parts sit `on` it and inherit its plane.
   - A per-part `tilt` was considered and rejected. It states the same angle once on the housing and
     again on every port, and the copies drift.
   - A tilted copy of each standard part (`std/qsfp28-30deg`) was rejected. It multiplies the
     catalogue and breaks the L9 size check against the registry.
2. **Full 3D in the first version.** The facet surface slopes. Every cavity, raised feature, lamp and
   seated occupant on it is built along the slope. Two lesser versions were rejected: 2D only, and a
   sloped housing with straight cavities.
3. **Authors keep measuring in front-view millimetres.** A facet node's art and a part's `at` are
   what you read off a front figure. The part's `size` stays its true, registry size, and the
   renderer projects it.
4. **Scope of v1:**
   - Facets in component contracts only. Device-level placements `on` a facet are deferred.
   - One facet per node, so a sawtooth is several facet nodes.
   - No compound angles (up and left at once).
5. **Additive.** No existing contract changes. A viewer that does not know the new attributes
   draws everything flat, as today.

## Format

### The facet, on a relief feature

```yaml
relief:
  features:
    - node: qsfp-housing
      facet: {deg: 30, facing: up}
      lift: 0              # optional, as on any feature: the height of the facet's root edge
      confidence: drawing
      source: '...'
```

- **`deg`:** the facet's angle away from face-on, from 1 to 89.
- **`facing`:** `up | down | left | right`, which way the facet looks.
  - `up`: the upper edge (the *root*) sits on the plate and the lower edge stands proud.
  - `down`: the lower edge sits on the plate and the upper edge stands proud.
  - `left`: the left-hand edge is the root and the right-hand edge stands proud.
  - `right`: the reverse of `left`.
- **The node's rectangle** is the facet's footprint as seen from the front. The proud edge stands
  off by `projected extent x tan(deg)`.
- **A feature with `facet` may not also declare `out`, `profile` or `profile-y`.** The renderer
  derives the equivalent wedge.

### A part on a facet

```yaml
parts:
  - {ref: std/qsfp28@1, id: port1, at: [5.0, 120.0], rotate: 90, on: qsfp-housing}
```

- **`on`:** the `node` of a relief feature on the same contract that declares `facet`.
- **`at`:** the part's front-view top-left, in the parent's millimetres, as for any part.
- **`size` and `rotate`:** unchanged. The part's own `rotate` pivots on its own centre in its true
  frame, before projection.
- **Occupants:** anything seated in a part that is `on` a facet inherits the tilt, in 2D and 3D.

## Rendering (render.py)

- **The facet node** is drawn as authored.
  - Its `facet` compiles to the equivalent derived relief. For `up`/`down` that is a `profile-y` of
    `[[0, a], [p, b]]`, where `p` is the node's projected height and `{a, b}` is `{0, p*tan(deg)}`
    in the order the facing gives. For `left`/`right` it is a `profile` across the width, built the
    same way.
  - The derived profile is carried on the existing `data-z-profile` / `data-z-profile-y`
    attributes. The renderer also writes `data-facet-deg` and `data-facet-facing`.
- **A part `on` a facet** gets one extra transform:
  1. `translate(at)`;
  2. a scale of `cos(deg)` along the facet's axis (y for up/down, x for left/right);
  3. the part's own `rotate`, about its true centre.

  The part group carries `data-tilt-on` (the facet node's id path), `data-tilt` (deg) and
  `data-tilt-facing`.
- **Occupants** seated in such a part are drawn inside the part's projected frame and carry the
  same three attributes.

## Lint

- **L114 (new).** On each part that is `on` a facet:
  - `on` names a relief feature on the same contract that declares `facet`;
  - `facet.deg` is in 1..89 and `facet.facing` is one of the four values;
  - the part's projected box lies within the facet node's box, to within 0.5 mm.

  A feature declaring `facet` together with `out`, `profile` or `profile-y` is an error.
- **Projected boxes:** L46 (composed parts collide), L48, and the device-level L13 and L39 measure a
  facet-mounted part by its projected box, because that is what occupies the face.
- **True size:** L9 keeps checking the part's true size against the registry.
- **Confidence:** a `facet` is a relief figure. L35 and L36 require its `confidence` and `source`
  like any other; an angle read by eye says `estimated`.

## 3D (kit/relief.js, kit/viewer3d.js)

- **The facet surface is the derived wedge,** built by the existing profile-surface builder. That
  builder textures the plate from the node's front-view art, which is the correct appearance on the
  slope, and it already cuts holes.
- **Two pure functions,** exported and tested under node:
  - `tiltFrame(facet, anchor)` returns the 4x4 matrix that places a part's flat frame on the facet
    plane. The anchor lands on the sloped surface at its height there; the along-slope axis runs
    down the slope; outward is the facet's normal. For `facing: up`, with y down and z out of the
    panel, the along-slope axis is `(0, cos, sin)` and the normal is `(0, -sin, cos)`. The other
    facings are the same frame turned.
  - `unproject(rect, tilt)` restores the true extent along the tilted axis: it divides by cos about
    the part's anchor.
- **Collection.** Every cavity, raised feature, lamp dome and lifted flat node under a
  `[data-tilt-on]` ancestor carries a `tilt` record. It is unprojected, built flat exactly as today,
  then moved by the tilt frame. A cavity therefore runs its depth along the facet's normal.
- **Holes.** A tilted cavity punches the facet it sits `on`, and the hole is the cavity's front-view
  footprint. This extends the existing rule that a lifted cavity punches the raised surface it seats
  on (`cavitySeatsOn`).
- **Occupants.** A seated occupant's body group takes its host part's tilt frame. An optic therefore
  sits in the cavity, points along the slope and ejects along that axis.
- **Picking and highlighting** are unaffected; the meshes are only transformed.

## Testing

- **Python:**
  - the transform on a facet-mounted part, with and without its own `rotate`;
  - the derived wedge;
  - the emitted attributes, including on a seated occupant;
  - each L114 failure;
  - L9 still checking the true size.
- **Node:** `tiltFrame`, `unproject` and facet hole placement.
- **Fixtures** are built for the tests: a test card with a 30-degree housing and a 45-degree
  sawtooth. No live library part is borrowed as a fixture.
- **Visual:** a composited Explorer screenshot of the fixture in 2D and 3D, with an optic seated in
  a tilted cage. Not a buffer read-back.

## Migration

- **This change modifies no existing contract.**
- **After it merges,** the Nokia 7360 ISAM FX branch (roc-ops/Portrayal#538, PR #540) converts its
  painted stopgap bands to facets, with the version bumps the geometry change requires on the cards
  and on the shelves that seat them:
  - FANT-H (AA, AC, BB, BC);
  - FANT-M (ANSI and ETSI);
  - FNIO-A and FNIO-D.
- **The Casa UPS-32x4** is converted in a follow-up issue.
- **Documentation in this change:**
  - a "Tilted faces" section in `docs/modelling-a-device.md`;
  - a line in `library/components/README.md`;
  - a `docs/modelling-pitfalls.md` entry on reading an angle off a 3D figure. An angle read by eye
    is `estimated`, and what you measure is a projected footprint.

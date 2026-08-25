---
name: portrayal-model-device
description: Use when modelling a hardware device for Portrayal from reference material (datasheets, install guides, drawings, photos) - building or revising a device.yaml and any components it needs. Walks the manufacturing order with a verification gate at each stage.
---

# Modelling a device for Portrayal

A faceplate is made in a fixed order: the sheet metal is sized, it is punched,
it is printed, and only then are the parts installed. Model it in that order,
and **do not start a stage until the previous one has been checked against the
reference.** Every failure this project has had came from skipping a gate:
terminals drawn where breakers were, 54 ports that all read "SFP module", a
chassis 12% too wide because a page margin was measured as metal.

The output is `library/devices/<vendor>/<model>/device.yaml`, written in the
canonical shape (below), linting clean at `maturity: modelled`.

## Before you draw anything: sort the sources

Each kind of source is allowed to answer only certain questions. Mixing roles is
the single most repeated error.

| source | authoritative for | never use it for |
|---|---|---|
| **datasheet / spec table** | overall dimensions, RU, weight, port counts, power | positions |
| **install guide figure** | *what* is on a face and *how it is arranged*; port order; legends | absolute geometry - these figures are schematic and their aspect is wrong |
| **mechanical drawing** (vendor or hand-built from the hardware) | size and placement of every feature | colour, legend text |
| **photograph** | colour, finish, confirmation of everything above; count of things | measurement, unless something of known size is in frame |
| **standards registry** (`spec/schemas/standards.yaml`) | cage and connector sizes | anything vendor-specific |

Write the source list into `provenance:` first, before a single number. Every
number you write afterwards names its source *at the moment you write it*. That
is not paperwork - it is what makes `maturity` honest and what lets the next
person know which figure to re-measure when something is wrong.

Confidence words, used verbatim in provenance: `datasheet`, `drawing`,
`measured`, `photo-measured`, `registry`, `estimated`. Anything `estimated` keeps
the device out of `verified`.

**Reference material stays in `working/`** (gitignored). Transcribe facts; never
copy a datasheet, stencil or CAD file into the library.

## Stage 1 - the panel

Establish `chassis.width/height/depth` and each view's `size`.

- The rack face is not the chassis. A 19in / 482mm figure **includes the
  mounting ears**; the body is narrower. Ears are a separate optional placement.
- Take proportions from a figure only as *fractions* of a dimension you know from
  the datasheet. Two figures in one guide can disagree by 12% on absolute scale.
- Panel decor (vents, grooves, bezels) goes in `panel.decor`. It is what the
  metal *is*.

**Gate 1.** Render (`render.py --without silkscreen`) and overlay on the
reference at a common scale. Aspect must match. If it does not, stop; nothing
downstream survives a wrong panel.

## Stage 2 - the cutouts

Declare every hole in `panel.cutouts` before choosing what goes in it.

```yaml
panel:
  cutouts:
  - {id: p1,  at: [46.0, 12.0], size: [14.25, 10.4], shape: rect}
  - {id: sys, at: [9.5, 31.5],  size: [3.0, 3.0],    shape: circle}
```

- One cutout per opening in the metal. A 48-port block is 48 cutouts, on a
  measured pitch, not one rectangle.
- Standard openings come from the registry (`conforms:` on the component you
  will place there tells you the size). Do not eyeball an SFP aperture.
- Positions come from the mechanical drawing. If you only have a guide figure,
  derive **pitch and count** from it and anchor to a datasheet dimension.

**Gate 2.** Render and overlay again. Every hole lines up with the reference.
Count them. This is the last cheap moment to fix a pitch error - after
components are placed, moving 48 holes means moving 48 parts and 48 labels.

## Stage 3 - the silkscreen

Everything printed on the panel goes in `silkscreen[]`, and each mark says what
it belongs to.

```yaml
silkscreen:
- {at: [53.1, 30.0], text: '1',   for: port-1}
- {at: [90.0,  8.0], text: 'PSU 1', for: psu-1}
- {id: branch-1-leader, path: 'M 169 10.4 H 199.9 V 46.6 H 195.7', for: [breaker-1, branch-1]}
```

- `for:` names the placement or bay the mark annotates. A legend with no owner
  (the model name, a warning) omits it. A mark that joins two things - a leader
  line between a breaker and its terminal - lists both.
- Legends that sit *under* where a module will go are invisible on the real
  device, and the renderer paints them under too. If your label vanishes when the
  component is placed, the label is in the wrong place, not the renderer.
- Text printed on a **module's own faceplate** is not chassis silkscreen. It
  belongs in that component's skin, inside `<g id="silkscreen">`.
- Use `text:` for words and `path:` for lines and symbols. Exactly one.

**Gate 3.** Render with silkscreen, compare to the reference. Every legend is
present, spelled as printed, next to its cutout. Lint L14 checks each `for:`
target exists and is nearby; make it pass before moving on.

## Stage 4 - the components

Now populate. **Reuse before building.**

1. Search `library/components/` for an existing component. `std/` and `common/`
   hold cages, jacks, LEDs, PSUs and fans that conform to registry standards.
   A port is `std/sfp-module@1`, not a new rectangle.
2. Only build a new component when nothing fits *and* you have a source for its
   dimensions. A new component with `estimated` size is a last resort and must
   say so.
3. Modules that come out go in `components.bays` with `accepts:`. Things that
   do not come out go in `components.placements`.
4. An indicator declares what it belongs to: `{id: led-p1, ref: std/led-arrow@1,
   for: port-1, group: port-leds}`. Never rely on naming to imply it.
5. Every placement and bay carries `group:` and `rel-pos:`, and every group is
   declared under top-level `groups:` with its `term` (the vendor's word: Port,
   Slot, Bay) and `index-origin`. That is what gives the tree, the exporter and
   any DCIM their numbering.

Occupants (a transceiver in a cage) use `mate-to:` and carry no position of
their own.

**Gate 4.** `lint.py` clean. Render both with and without silkscreen. Open the
explorer: the tree reads chassis, then groups in tier order, every row
`id - model`, indicators nested under what they indicate. Then set
`maturity: modelled` and lint again; L15 will tell you if the provenance is
not good enough.

## The canonical shape

Key order is fixed and linted (L16). A view reads top to bottom in the order
the part is made.

```yaml
format: 1
kind: device
name: <slug>
version: 0.1.0
maturity: draft | modelled | verified
manufacturer: <Vendor>
model: <Model>
description: >-
  one paragraph
provenance:
  <key>: '<confidence> - <where, precisely>'
attrs: {...}
chassis: {width: , height: , depth: , ru: , color: }
groups:
  ports: {term: Port, index-origin: 1, attrs: {media: sfp-plus, speed: 10g}}
  port-leds: {term: LED, index-origin: 1}
views:
  front:
    size: {w: , h: }
    panel:
      decor: [...]
      cutouts: [...]
    silkscreen: [...]
    components:
      bays: [...]
      placements: [...]
    regions: [...]        # author-drawn callout boxes; last, optional
configurations: {...}
```

## Things that have gone wrong before, so you do not repeat them

- **A rotated crop reads bottom-to-top.** Check the frame before reading port
  order off a figure; this reversed an entire supervisor card once.
- **Rear views mirror only when the cards are vertical.** Walking round a
  chassis flips left-to-right. Vertical cards mirror; horizontal ones do not.
- **`getBBox()` is local.** Measuring a hand-built SVG in a browser: compose
  the CTM. Composing transforms by hand in Python does not reproduce Inkscape
  output; sample the path through the browser instead.
- **Pattern-match by colour, not by vector.** Rendering a guide page at 400dpi
  and detecting features by colour is reliable. Parsing its vector art is not -
  text comes out as glyph paths under nested transforms.
- **An inventory is not a layout.** Knowing a panel has four things called
  "Branch N" does not tell you they are breaker legends with leader lines. Open
  the figure that shows the layout before drawing.

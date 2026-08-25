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

**Gate 1 - prove a figure can be measured before you measure it.** Render the
guide page at 400-600 dpi (`pdftocairo -png -r 600`), find the panel in it, and
compare its pixel aspect with the datasheet's W/H. If they agree to about a
percent the figure is orthographic and carries geometry, and you can work off it
at a known px/mm. If they do not, the figure is schematic and you may take only
*fractions* from it.

**Photographs almost never pass this gate.** A camera slightly above or to one
side foreshortens the face; a near-straight-on shot of a 2RU router measured
5.43-5.77 against a true 5.06 depending on where the edge was placed. Use photos
for colour, counts and confirmation, and for construction detail a line drawing
flattens away - not for dimensions.

Then render your own panel (`render.py --without silkscreen`) and overlay. If the
aspect is wrong, stop; nothing downstream survives a wrong panel.

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
3. `components.bays` is for things that seat into an opening; everything else,
   removable or not, is a `components.placements` entry. See rule 6.
4. An indicator declares what it belongs to: `{id: led-p1, ref: std/led-arrow@1,
   for: port-1, group: port-leds}`. Never rely on naming to imply it.
5. Every placement and bay carries `group:` and `rel-pos:`, and every group is
   declared under top-level `groups:` with its `term` (the vendor's word: Port,
   Slot, Bay) and `index-origin`. That is what gives the tree, the exporter and
   any DCIM their numbering.

6. **If the guide has a replacement procedure for it, it is a part, not
   decoration** - but that does not make it a bay. Ask how it is held on:
   - it **slides into an opening** in the metal (PSU, fan, line card) -> a `bay`
     with `accepts:`, and the bay's dark opening is what shows when it is out;
   - it **bolts onto the outside** of the faceplate (an air filter, a cable
     manager, a bezel) -> a `placement`, painting over the panel and its
     silkscreen, because that is where it physically sits.
   Getting this wrong is visible: a non-rectangular part in a bay leaves the
   bay's opening showing around it, like a hole in the chassis that is not there.
7. **Read the guide's LED section for count AND arrangement, and expect them to
   differ per port family.** On one router the QSFP-DD ports carry a stacked
   pair outside each block, the QSFP28 ports four above each column, and the
   SFP28 ports one each. One rule for all of them will be wrong.
8. **Transcribe the spec table.** Switch silicon, CPU, memory, boot flash,
   storage, BMC, capacity, buffering, power draw, PSU inputs, temperature and
   humidity all belong in `attrs`. They are why someone opens the model.

Occupants (a transceiver in a cage) use `mate-to:` and carry no position of
their own.

**Model every face.** Six views, even where a face has no detail. Size them from
the spec table so a rack elevation and the 3D box are right, and say in
provenance that they are deliberately blank. A missing view is indistinguishable
from an unfinished one; an empty view that states why is not.

**Gate 4.** `lint.py` clean. Render both with and without silkscreen. Open the
explorer: the tree reads chassis, then groups in tier order, every row
`id - model`, indicators nested under what they indicate. Then set
`maturity: modelled` and lint again; L15 will tell you if the provenance is
not good enough.

## Gate 5 - audit against the source, by name

The gates above check that what you drew is *right*. This one checks that it is
*complete*, and it is the one that catches the quiet omissions.

Go back to the guide's overview figure and walk its numbered callouts one by
one. For each, name the id in your manifest that satisfies it. Then do the same
for the spec table. Write the audit down - a dozen lines of "callout 13,
grounding point -> `ground-point`" is enough.

This is not ceremony. On the first device built with this skill, every gate
passed and the model still had no grounding point, because callout 13 was never
looked for. Nothing else would have caught it: it lints clean, it renders, and
it looks finished.

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
- **Read silkscreen legends at high zoom before trusting them.** A port pair
  legend that looks like `0<up>1` at page scale turned out to be `0<up><down>1`
  at 7x - two arrows, not one - which inverts which row is even. Zoom until the
  glyphs are unambiguous, then decide.
- **A `path:` silkscreen mark is stroked, not filled.** The renderer sets
  `fill: none`, so a solid triangle or arrow comes out as an outline. Anchor the
  path at its `at` and draw the geometry relative to that, or L14 has nothing to
  test against.
- **Where two sources disagree, carry both numbers.** One datasheet said 480 mm
  deep and 16 kg; its own quick start guide said 524 mm and 14.5 kg. Record the
  disagreement in provenance rather than silently choosing, and say which you
  used.
- **An inventory is not a layout.** Knowing a panel has four things called
  "Branch N" does not tell you they are breaker legends with leader lines. Open
  the figure that shows the layout before drawing.

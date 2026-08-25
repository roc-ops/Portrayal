# Layers and conformance

Two changes that came out of one conversation: model a faceplate the way it is actually
made, and make "does this manifest comply" a question lint can answer rather than a
question a reviewer has to hold in their head.

## The canonical manifest

A view is written in the order the part is made, and lint holds it to that order
(L16). This is not a style preference: an agent building a device follows the file
top to bottom, stage by stage, and a file that reads in a different order teaches
the wrong procedure. The procedure itself is `.claude/skills/portrayal-model-device/`.

```yaml
views:
  front:
    size: {w: 438.4, h: 43.5}
    panel:                      # 1. the sheet metal
      decor: [...]              #    what it is: vents, grooves, bezels
      cutouts: [...]            #    where it is punched
    silkscreen: [...]           # 2. what is printed on it, before anything is installed
    components:                 # 3. what is installed
      bays: [...]               #    things that come out
      placements: [...]         #    things that do not
    regions: [...]              # 4. author-drawn callout boxes, optional
```

`label:` on a placement or bay no longer exists. A legend is a silkscreen mark that
says what it belongs to - `{at: [53, 30], text: '1', for: port-1}` - and it renders
where the label did. `decor` no longer takes `text` for the same reason.

### `for:` - one word for "belongs to"

```yaml
- {id: led-p1, ref: std/led-arrow@1, for: port-1, group: port-leds}      # placement
- {at: [53.1, 30.0], text: '1', for: port-1}                              # silkscreen
- {id: branch-1-leader, path: 'M 169 10.4 H 199.9 V 46.6', for: [breaker-1, branch-1]}
```

The same field on a placement, a bay and a silkscreen mark, meaning the same thing:
this belongs to that. It is **authored, never inferred from names**. One target or a
list; a leader line that joins two things names both, and on an indicator a list means
*collectively* - a FAN lamp over five trays names all five. The renderer emits
`data-for`, the explorer nests the child under its owner and highlights both on
selection, and L14 checks every target exists and is nearby - within one
owner-dimension, floored at 30 mm. The floor has to clear the largest real stack
pitch: indicators are banded, so one lamp row serves a stacked pair and the lamp for the
far member sits a whole pitch away - 27.4 mm on the AS7326-56X.

A **placement** may name two things a silkscreen mark and a bay may not, because an
indicator's subject need not be on the face the indicator is printed on:

- `view/id` - a target in another view of the same device. A front-panel PSU lamp
  indicates a PSU that lives in the rear; that relationship is real, knowable, and
  nothing else in the schema can spell it. Cross-view targets are **not** proximity
  tested: each view has its own coordinate system over its own face, so the distance
  between a lamp on the front and a supply on the rear is a subtraction of two
  unrelated origins and means nothing.
- `chassis` - the whole unit. A DIAG, LOC or unnumbered POWER lamp reports on the box
  or on a rail, not on a modelled part, and `chassis` is already a real node: the
  renderer gives the faceplate `data-path="chassis"` and it is the first row of every
  tree. An unnumbered POWER lamp takes this, not the PSU bays: "the unit has power" is
  not "these two supplies have power".

Printed ink stays where it was printed - silkscreen `for:` is a bare id in this view,
never qualified and never `chassis`, and L14 says so.

In the emitted SVG a cross-view target is written device-absolute, `data-for="/rear/psu-0"`.
Consumers split `data-for` on spaces and look each token up as a path in the drawing
they hold; `rear/psu-0` is a plausible-looking local path and could resolve to the
wrong node in silence. No `data-path` ever begins with a slash, so the qualified form
cannot be mistaken for a local one. A front-view tree cannot nest a rear-view bay -
the bay is not in that drawing - so the explorer leaves the row where it falls and
prints the target beside it: `led-ps0 — led-rect → rear/psu-0`.

Whether an LED (part of) and a label (describes) deserved different words was
considered. They do not: the distinction is already carried by which section the
child is in, and every consumer treats the relationship identically.

### `groups:` - declared, not just used

Every `group:` on a placement or bay is declared once at top level with the vendor's
word for one of them and where numbering starts (L17):

```yaml
groups:
  ports:     {term: Port, index-origin: 1, attrs: {media: sfp-plus, speed: 10g}}
  port-leds: {term: LED,  index-origin: 1}
```

That is what gives the explorer its fold titles, the exporter its shape names and a
DCIM its numbering. Freezing the vocabulary across devices is still open (#12).

### Cutouts - declared, not yet checked

`panel.cutouts` is in the schema and renders (a hole with nothing in it shows the
dark inside of the chassis, which is what the drawing shows too). The lint that
asserts every component sits in one and every one is filled is #5. No existing device
declares cutouts yet; new devices built with the skill do.

## The layer model

A faceplate is manufactured in three steps, and the model now mirrors them.

| step | layer | where it lives |
|---|---|---|
| 1. punch and drill | **panel** | chassis `decor`, and the component skins' own geometry |
| 2. print | **silkscreen** | `views.<v>.silkscreen[]` on the device; `<g id="silkscreen">` in a component skin |
| 3. install parts | **components** | `placements` and `bays` |

**They paint in that order, and the order matters.** Chassis silkscreen goes down on the
punched panel *before* the modules are installed, so a module covers it. That is not a
rendering quirk to work around — it is the truth about the hardware, and it turns a
mispositioned legend into something visibly missing rather than into a drawing that
asserts something the real device does not show.

Silkscreen printed on a **module's own faceplate** is different: it travels with the
module and is never occluded by it. That belongs in the component's skin.

Instance labels are silkscreen too — they are legends printed on the chassis beside a
part — so they come and go with the layer.

### Handing a drawing to whoever does the artwork

    python3 spec/tools/portrayal/render.py <device.yaml> --library library \
        --without silkscreen --out dist-bare

The punched panel with every component installed and nothing printed on any of it. On the
C100G that is 569 geometry nodes with and without, and 100 text nodes down to 0.

The sweep removes `<g id="silkscreen">` groups *and* any remaining `<text>` in a skin. The
group is the convention and lint will come to require it; the text sweep is the backstop,
and it is sound rather than a shortcut, because printed text on a faceplate **is**
silkscreen whether or not its author put it in the right group.

### Binding a legend to the part it names

    silkscreen:
    - at: [18.41, 102.7]
      text: '0'
      for: front-0

A silkscreen `for` names a placement or bay in the same view and is emitted as `data-for`,
so a viewer can select a component and its legend together. It also earns its keep at lint
time — see L14. A placement's `for` may reach further: `rear/psu-0` for a target in another
view, or `chassis` for the whole unit.

## Conformance: `maturity`

A device declares how far it has been taken, and lint holds it to that standard. Work in
progress can be committed without fighting the linter; a device that *claims* to be
verified has to earn it.

| level | required |
|---|---|
| `draft` (default) | nothing |
| `modelled` | a `provenance` block that cites a datasheet or hardware guide |
| `verified` | the above, and **no estimated value anywhere in the assembly** |

`verified` walks the components the device places, not just the chassis manifest. A device
built from guessed parts is not verified however carefully the chassis was measured. Set
the C100G to `verified` today and it tells you precisely what stands in the way:

    [L15] component casa/ground-bolts@1 has estimated depth
    [L15] component casa/io-6p12@1 has estimated bore, size
    [L15] component casa/pem@1 has estimated depth
    [L15] component casa/smm-8x10g@1 has estimated size

That is the deterministic checklist. It is a work list, not a scolding.

## New rules

**L14 — silkscreen binding.** A legend with `for` must name a placement or bay that exists
in that view, and must sit near it. Both fire:

    [L14] front: silkscreen '0' is for 'front-99', which is not a placement or bay in this view
    [L14] front: silkscreen '0' at (18.41, 102.7) is bound to 'front-13' but sits well
          outside it (399.29, 108.1 30.47x345.5)

The proximity test allows a legend inside its part's footprint or within one part-dimension
of it, which covers printed-beside-a-port without permitting a label on the far side of
the chassis.

**L13 — placed parts must not overlap** — and that now includes **bays**, not just
placements. Leaving bays out let a row of rivets sit on top of five fan bays with
nothing said. Two subtleties, both learned the hard way:

- A **placement's** size comes from its unrotated component, so a quarter turn
  swaps it. A **bay's** size is authored as the on-panel footprint already, and
  `rotate` only spins the occupant inside it. Transposing a bay reported the
  C40G's six horizontal card bays as overlapping by 300 mm.
- The tolerance is **0.05 mm**, not 0.001. Abutting parts on a fractional pitch
  round into a hair of overlap — the C100G's 30.47 mm card pitch puts adjacent
  bays 0.01 mm into each other — and reporting that trains people to ignore the
  rule.

**L15 — the maturity gate.** Above.

**L16 — manufacturing order.** View keys must read `size > panel > silkscreen >
components > regions`, panel `decor > cutouts`, components `bays > placements`.

**L17 — declared groups.** Every `group:` used is declared under top-level `groups:`.

## What is done and what is not

Done: the schema, the paint order, the `for` binding, `--without silkscreen`, L14, L15, and
the migration of all 443 device text marks out of `decor` into `silkscreen`.

Not done, deliberately:

- **The component-skin grouping convention is not enforced.** 26 of 149 skins contain text
  (107 nodes) and none use `<g id="silkscreen">` yet. The backstop makes the export correct
  regardless; the grouping is what would make it *checkable*. A rule requiring it should
  land with the migration, not before it.
- **Cutouts are not modelled.** The panel's holes are still implicit in the skin artwork.
  Declaring them as data is what would let lint assert that every component sits in a
  cutout and every cutout is filled — the rule that would have caught the overlapping LEDs,
  the stray comb box and the `-48/-60VDC` text running onto the terminal block. This is the
  biggest remaining win.
- **`build.sh` does not emit the bare variants.** One flag away when something needs them.

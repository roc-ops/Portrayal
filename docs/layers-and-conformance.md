# Layers and conformance

Two changes that came out of one conversation: model a faceplate the way it is actually
made, and make "does this manifest comply" a question lint can answer rather than a
question a reviewer has to hold in their head.

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

    python3 ndv-spec/tools/ndv/render.py <device.yaml> --library ndv-library \
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

`for` names a placement or bay in the same view and is emitted as `data-for`, so a viewer
can select a component and its legend together. It also earns its keep at lint time — see
L14.

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

**L15 — the maturity gate.** Above.

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

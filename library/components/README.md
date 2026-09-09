# Components

A component is a part a device places or seats: a cage, a jack, a PSU, a fan
tray, a line card, a label, a rivet. Each lives at
`components/<namespace>/<name>/v<major>/` as a `contract.yaml` that says what
the part is and where its addressable elements are, plus one or more skins
under `skins/` that say what it looks like. Devices reference a component as
`<namespace>/<name>@<major>`.

This page says which namespace a part goes in, how it is named, when to reuse
one instead of drawing another, and what a contract and a skin must contain.
The modelling guide covers measuring and drawing the part itself.

## Find it before you draw it

Most parts already exist. Before creating one:

```sh
ls library/components/std library/components/common       # standard apertures and shared shapes
grep -rl 'conforms: qsfp28' library/components              # everything that is a QSFP28 cage
./build.sh && python3 -m json.tool library/dist/components.json | less   # the built catalogue
```

A QSFP28 cage, an SFP+ cage, an RJ45 jack, a C14 inlet, a status lamp, a USB
port, a grounding lug, a rack ear: all of these exist. A new part is warranted
when the shape is different, not when the vendor is. A 650 W supply in a new
chassis is usually a placement of an existing PSU contract, or a new contract
in the vendor's namespace that `parts:` an existing one for its inlet and lamp.

## Namespaces

| namespace | holds | example |
|---|---|---|
| `std/` | apertures and cages that conform to a standard in `spec/schemas/standards.yaml`; lint checks the size against the registry | `std/qsfp28`, `std/rj45`, `std/c14-inlet` |
| `common/` | shapes that stand for a class of part rather than one product, with no manufacturer and nothing a DCIM could order | `common/led-arrow-sm`, `common/rivet`, `common/psu-550w` |
| `<vendor>/` | a manufacturer's own part: a line card, a vendor-specific PSU or fan, a faceplate, a label | `juniper/mpc7e-10g`, `ufispace/psu-132-crps-ac` |

Prefer `std/` over `common/`, and `common/` over a vendor namespace, but only
when the rule above is true. A part that is one vendor's product belongs in that
vendor's namespace even if another vendor ships something that looks the same.
Vendor slugs are the keys in `spec/schemas/vendors.yaml`; a new vendor is added
there first.

## Names

- Lower-case, digits, hyphens: `^[a-z0-9]+(-[a-z0-9]+)*$`, no double hyphen
  (lint L2). This is the component's id segment in every SVG.
- Name the part, not its position or orientation. `fan-803816-hi`, not
  `fan-left`. Orientation belongs to the placement (see #176); a second contract
  that differs only by rotation is a duplicate.
- Do not repeat the namespace in the name. `edgecore/agr-fan` carries an
  `agr-` prefix because AGR is the product line, not because it is Edgecore's.
- Do not put a version in the name. `-v2` in a name collides with the version
  directory that already says it.
- Use the vendor's model number where one exists (`psu-132-crps-ac`,
  `fan-803816-hi`); it is what a search will be for.

## Versions

`v<major>` is the directory; `version:` inside the contract is the full
semver. The bump rules, from DESIGN.md: **art is a patch** (a skin redrawn, a
colour, a label), **additive is a minor** (a new element, a new state, a new
skin), **geometry or ids are a major** (the size changed, an element moved or
was renamed), because a device that placed the part may now be wrong. A major
bump is a new `v<N+1>/` directory; the old major is removed once no device
references it (the open question of whether the directory level should stay at
all is #172).

A change to a component changes every device that draws it. After editing a
contract, run the lock check from the repository root and bump the devices it
names (see [CONTRIBUTING](../../CONTRIBUTING.md), step 5).

## The contract

The smallest complete contract in the library, `std/qsfp28/v1/contract.yaml`,
is the shape to copy:

```yaml
format: 1
kind: component              # `component` is placed; `module` seats in a bay and can be swapped
name: qsfp28
version: 1.4.0
class: port                  # port, psu, fan, line-card, blank, led, ground, filter, ... (#173 will enumerate)
profile: networking
conforms: qsfp28             # std/ only: the standards.yaml key; lint checks size against it
interface: qsfp              # this part IS a receptacle presenting this interface
description: QSFP28 cage cutout (100G, 4 lanes)
size: {w: 20.0, h: 10.15, d: 37.0}      # millimetres; d is depth into the panel
attrs: {media: qsfp28}
provenance:                  # every figure says where it came from and how sure you are
  depth: registry - SFF-8663 Rev 1.7 Fig 4-1, bezel to connector 37 REF
  size: registry - SFF-8663 Rev 1.7 Fig 5-4, spring-finger bezel opening
elements:                    # addressable sub-elements; each id must exist in every skin
  opening: {at: [0.0, 0.0], size: [20.0, 10.15], class: cutout}
relief:                      # 3D: how far things stand out or sink, with confidence
  wall: '#aab0b7'
  features:
    - {node: collar, out: 1.0, color: '#7d848c', confidence: estimated, source: '...'}
connection-points:
  mate: {at: [10.0, 5.075], direction: front}   # where an occupant aligns
skins: [default]
```

Required keys are `format`, `kind`, `name`, `version`, `class`, `size`. The
rest earns its place:

- `conforms` for anything in `std/`; lint (L9) refuses a size that disagrees
  with the registry.
- `interface` if the part is a receptacle; `mates` plus a `mate` connection
  point if it is an occupant (a transceiver, a card, a PSU in a bay).
- `parts` to compose: a vendor PSU that contains a `std/c14-inlet` and a
  `common/led` says so instead of redrawing them. Lint (L10) checks the
  composition resolves and does not cycle; L46 checks composed parts do not
  overlap.
- `fields` for what varies without the shape changing: a supply's wattage, a
  drive's capacity. Do not make a new skin per wattage.
- `states` for lamps, named as tokens (`link`, `activity`, `fault`), with the
  behaviour in `behaviour`.
- `provenance` with one entry per figure you state. The confidence words are
  `datasheet`, `drawing`, `measured`, `photo-measured`, `registry`,
  `borrowed`, `estimated`, `known-wrong`; `borrowed` must name the part the
  figure came from.

The schema, `spec/schemas/component.schema.json`, is the full reference; every
key carries a description.

## Skins

A skin is a hand-written SVG at `skins/<name>.svg`, drawn in millimetres:

- `width`/`height` carry `mm` units and `viewBox` is `0 0 <w> <h>` from the
  contract's `size` (lint L4); `d` is depth into the panel and has no place in a
  face drawing. `<svg width="20mm" height="10.15mm" viewBox="0 0 20 10.15">`.
- Every id in `elements:` is an element id in every skin (lint L3). Other
  shapes may carry ids too; those are what `relief.features` and `fields`
  address.
- Printed text sits inside `<g id="silkscreen">` (lint L38), unless the part
  is a label applied over the panel rather than printing on it.
- `default.svg` is the skin a placement gets unless it names another.
  Additional skins are for a different **appearance of the same part**: a
  colour the vendor ships (`blue.svg`), a variant of the printed art. They are
  not for wattage (use `fields`), orientation (a placement rotates), or a
  different shape (that is another component).
- `body-left.svg`, `body-right.svg`, `body-top.svg`, `body-bottom.svg`,
  `body-rear.svg` are optional side views for parts that have a 3D body
  (modules, PSUs, fans); the viewer uses them to texture the box.
- No raster images, no editor metadata, no external references. A skin is
  geometry and fills. Vendor logos are not reproduced; contracts reserve a
  `logo-zone` element instead.

## What lint will say

The rules most often met while adding a component: L2 (id grammar), L3 and L4
(skin matches contract), L9 (standard size), L10 (composition), L26 (a
`cutout` element is backed by a conforming contract), L27/L28/L52 (a
power-bearing module states its figure and its source), L35/L36 (relief
confidence), L38 (text in the silkscreen group), L46 (composed parts do not
collide). From the repository root:

```sh
python3 spec/tools/portrayal/lint.py --schemas spec/schemas --library library
```

Components are always checked in full, even with `--device`.

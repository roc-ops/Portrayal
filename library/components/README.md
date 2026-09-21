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

Most parts already exist. **Read [CATALOGUE.md](CATALOGUE.md) first** — every
component major on one page, with its size, the standard it conforms to, and how
many devices already use it. It needs no build, and a test fails if it disagrees
with the library.

To search it from a shell instead:

```sh
grep -i qsfp28 library/components/CATALOGUE.md              # every QSFP28 part, with its size
ls library/components/std library/components/common         # standard apertures and shared shapes
grep -rl 'conforms: qsfp28' library/components              # the contracts themselves
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
| `generic/` | a representative of a class under a spec: the envelope conforms to a standard (so lint checks it as `std/` is checked) and the appearance stands for every product of its kind; a vendor's product wraps one via `parts:` and adds its facts | `generic/sfp-lc`, `generic/qsfp-lc` |
| `<vendor>/` | a manufacturer's own part: a line card, a vendor-specific PSU or fan, a faceplate, a label | `juniper/mpc7e-10g`, `ufispace/psu-132-crps-ac` |

Prefer `std/` over `common/`, and `common/` over a vendor namespace, but only
when the rule above is true. A part that is one vendor's product belongs in that
vendor's namespace even if another vendor ships something that looks the same.
Vendor slugs are the keys in `spec/schemas/vendors.yaml`; a new vendor is added
there first.

### `std/x` and `common/x` are two layers, not two copies

The library holds pairs that look like duplicates and are not. `std/` holds the
**hole**; `common/` holds the **part around the hole**, and composes it:

| the aperture | the faceplate part that wraps it | what the wrapper adds |
|---|---|---|
| `std/usb-a` 12 × 4.5 | `common/usb-a` 17 × 7 | the receptacle shell and its trident mark |
| `std/db9` 20.5 × 11.4 | `common/db9-receptacle` 30.8 × 12.5 | a jackscrew standoff either side |
| `std/sma` 6.35 × 6.35 | `common/sma-jack` 9.5 × 9.5 | the gold jam nut |
| `std/qsfp-ganged` 18.5 × 9.58 | `common/qsfp-cage` 19.5 × 10.18 | the cage bezel |

**Which to place.** Place the `std/` part when the faceplate really is just a
cut opening, and the `common/` one when the panel carries the bezel, nut or
shell around it — the wrapper's own size is the thing you are drawing, and it
composes the aperture so the standard is still checked underneath. Never place
both at one position: the aperture is already inside the wrapper, and L39 will
report the overlap.

A `std/` part states `conforms:` and is size-checked against
`spec/schemas/standards.yaml`. A wrapper states no `conforms:` of its own; it
inherits the claim from the part it composes, which is why the pair is a layering
and not a fork.

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
semver. The level is here to stay: #172 weighed dropping it and kept it, because
an outside manifest pinning `name@2` is the consumer coexistence exists for and
this library acquires those the day it goes public. `spec/DESIGN.md` §9 carries
the measurement that decision was made on.

The bump rules, from DESIGN.md: **art is a patch** (a skin redrawn, a colour, a
label), **additive is a minor** (a new element, a new state, a new skin),
**geometry or ids are a major** (the size changed, an element moved or was
renamed), because a device that placed the part may now be wrong. A major bump
is a new `v<N+1>/` directory, and **the old major is deleted once nothing
references it** - that is what pays for the level, and L89 fails on a dead major
left behind an `unplaced:` sentence. What keeps a retired major alive is
something still naming it: a gap arguing from its figure, say. `common/psu-550w@1`
was kept for exactly that - the PBC-2000's `psu-module-width` gap argued from its
84.0 mm against the 73.5 mm of `@2` - and was deleted the day a square-on
photograph measured the supplies at 73.5 and closed the gap.

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

Required keys are `format`, `kind`, `name`, `version`, `class`, `size`.

`class` comes from a closed vocabulary, and it lives in
[`spec/schemas/power-roles.yaml`](../../spec/schemas/power-roles.yaml) rather
than in the schema - one list, in the file lint actually reads, sorted into the
three power roles. L51 refuses a class that appears in no role, which is how a
class invented today gets its power question asked today. Synonyms are merged
rather than admitted: `cooling` is `fan`, `fastener` is `screw`, `panel` is
`display`, `connector` is `inlet`.

The rest earns its place:

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
- `characters` for a `class: display` element - how many character cells it
  shows - and `messages` for what it can read, where the display reads whole
  strings rather than per-cell glyphs. A lamp's vocabulary is colours and a
  display's is words: Cisco's four-character LED matrix reads INIT, BOOT and
  PSEQ, which no list of `states` expresses. A seven-segment cell is the other
  shape - `characters: 1` with its glyph set in `states` - and lint (L98) asks
  every display for `characters` without asking any of them for `messages`,
  because a window framing two digits has no vocabulary of its own. Each message
  is `{text, meaning}`, the text exactly as the hardware prints it and the
  meaning in the vendor's own words; the text carries no whitespace, because the
  compiled drawing publishes the whole vocabulary on one `data-messages`
  attribute and a consumer splits it on spaces.
- `unplaced` when nothing in the library seats the part - a sentence saying
  what would seat it and what is missing, not a flag. Lint (L89) asks for it on
  any major no device reaches, and fails again if it is still there once
  something does, so a stale one cannot accumulate. Do not add it to a part that
  IS used; and do not reach for it to silence the rule on a part you could seat
  in the same afternoon.
- `provenance` with one entry per figure you state, **keyed by the figure, not
  by a headline for the note**. The core keys are `size` (the face dimensions,
  asked for by L92), `depth`, `power` (L52) and `relief` (L35/L36); a figure
  needing its own note takes a key starting with the core one - `size-width`,
  `power-output` - so it still answers when a rule asks. A finding about
  something no figure holds is welcome under its own name; it adds to the core
  keys rather than replacing one. The confidence words are
  `datasheet`, `drawing`, `measured`, `photo-measured`, `registry`,
  `borrowed`, `estimated`, `known-wrong`; `borrowed` must name the part the
  figure came from. (Older `std/` contracts, the real `qsfp28` among them, say
  `standard` where this example says `registry`; it is the same claim in the
  older spelling, and #173 is where the vocabulary gets settled.)

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
  **An additional skin is for printed art that differs** - a different legend, a
  different mark - and for nothing else. In particular it is not for:

  | not a skin | what it is instead |
  |---|---|
  | wattage, capacity, any printed value | a `field`, filled through a `data-from` node |
  | **colour** | a `field`, through `data-fill-from` and `data-stroke-from` |
  | orientation | the placement rotates |
  | a different shape | a different component |

  Colour was on that list until #177 and is the reason the rest of it is worth
  restating. Ten parts carried a `blue.svg` that differed from `default.svg` in
  one to four fills - `ufispace/psu-751-ac` in a single line - and every one of
  them was a second copy of a drawing that had to be kept in step by hand. A
  finish is one word on the configuration that differs:

  ```yaml
  component-attrs:
    fan-module: {handle-finish: '#3d7bd6', airflow-legend: B2F}
  ```

  A skin per colour also has to be CHOSEN, once per placement, which is how the
  library ended up with one Edgecore chassis drawing its back-to-front build in
  blue and two others in red from the same vendor convention.
- `body-left.svg`, `body-right.svg`, `body-top.svg`, `body-bottom.svg`,
  `body-rear.svg` are optional side views for parts that have a 3D body. NOTHING
  READS THEM TODAY: `relief.js` extrudes a box from the face skin and `data-z-*`,
  and whether these should texture that box is decided in
  docs/pluggables-3d-design.md. Do not add them to a new part.
- No raster images, no editor metadata, no external references. A skin is
  geometry and fills. Vendor logos are not reproduced; contracts reserve a
  `logo-zone` element instead.


## Adding an optic

A transceiver in this library is a GENERIC - one drawn part per form factor and
face under `generic/`, standing for every module of its kind and carrying no
rate. A vendor's optic is a WRAPPER around one: it composes the generic, sets the
generic's colour and label, and carries the facts that make it that product.

```yaml
# library/components/cisco/sfp-10g-lr/v1/contract.yaml
format: 1
kind: module
name: sfp-10g-lr
version: 1.0.0
class: transceiver
behaviour: occupies
mates: sfp                      # must equal the generic's
profile: networking
description: Cisco SFP-10G-LR, 10GBASE-LR, 1310 nm, 10 km over OS2.
size: {w: 13.55, h: 8.55, d: 47.50}
size-confidence: {w: borrowed, h: borrowed, d: borrowed}
attrs: {model: SFP-10G-LR, media: sfp-plus, speed: 10g, reach: 10km,
        wavelength: 1310nm, power-draw-max-w: 1.0}
provenance:
  size: >-
    borrowed - generic/sfp-lc@1, the generic this wraps, whose own figures are
    the sfp-module registry entry's. These are the GENERIC's numbers restated,
    not a reading of a Cisco drawing; a wrapper that measured its own would be
    a different shape and would not compose this generic.
  power: 'datasheet - Cisco SFP-10G-LR data sheet, maximum power consumption 1 W'
parts:
  - {ref: generic/sfp-lc@1, id: body, at: [0, 0],
     attrs: {latch-color: '#2f5fa8', label: SFP-10G-LR}}
connection-points:
  mate: {at: [6.775, 4.275], direction: front}
skins: [default]
```

`kind: module`, not `component`: a vendor optic is an orderable thing with a
part number, and the DCIM export emits a module type only for `kind: module`
(`spec/tools/portrayal/artifacts.py`). The generic it wraps is not orderable
and stays `kind: component`.

What goes where:

- **On the wrapper:** `model`, `media` (the rate family the port group speaks -
  `sfp-plus`, `sfp28`, `qsfp28` ...), `speed`, `reach`, `wavelength`,
  `power-draw-max-w`, and a `provenance.power` sentence naming the datasheet.
  L99 refuses every one of these on a `generic/` part, which is how the split
  stays true.
- **Passed to the generic:** `latch-color` and `label`, as `attrs` on the
  `parts:` entry. They are `fields` on the generic and the skin reads them; a
  colour is a field, not a second drawing (#177).
- **Never on either:** a rate in a component NAME. `sfp28-lr` is refused; the
  name is the vendor's part number.
- **Restated from the generic:** `size` (with `size-confidence: borrowed` and a
  `provenance.size` saying whose figures they are) and the `mate`
  connection-point. AN OCCUPANT MATES WITH ITS OWN POINT: the renderer reads
  `connection-points.mate` off the occupant's own contract and refuses a
  `mate-to` placement without one. Forwarding a mate point through `parts:`
  (#54) is what a HOST does - a vendor cage presenting its composed aperture's
  point - and it does not run the other way.

The wrapper restates the generic's mate point and so seats exactly where the
generic would - so nothing about cages, `occupants:` or L12 changes for a vendor
part. #54's mate-forwarding is the other direction: it lets a vendor CAGE
present the aperture it composes to an occupant, never a wrapper present its
occupant's point. An optic whose shape is NOT the generic's (a long-body
SC SFP+, a module with a nose heat sink) draws its own contract in the vendor
namespace with the same `mates:` and the same connection-points, and seats the
same way.

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

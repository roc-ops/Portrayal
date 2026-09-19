# Pluggables B: connectors and the cable point

Status: design agreed with Jason, 2026-09-18. Part of [pluggables-design.md](pluggables-design.md).
Depends on A for the bores the plugs seat in. Written now so it survives; refined
when A lands.

## Goal

A single LC plug and a single RJ45 plug, each with a boot that seats behind it, so
that every fibre and copper port in the library - on a chassis, on a card, on a
transceiver - can be shown with a connector in it, and so that a cabling library
built on top of Portrayal lands its cable on one published 3D point and looks
seated. One connector per kind, not seventy-five; the cable is somebody else's.

## Parts

| part | mates | seats in |
|---|---|---|
| `generic/lc-plug` | `lc` | `std/lc-bore@3` - on transceivers, on `common/lc-duplex-adapter`, anywhere the bore is composed |
| `common/lc-boot` | `lc-plug` | the plug's rear |
| `generic/rj45-plug` | `rj45` | `std/rj45-ganged@2`, `std/rj45@N`, and the vendor jacks that wrap them |
| `common/rj45-boot` | `rj45-plug` | the plug's rear |

The boots are `common/`, not `generic/`. A `generic/` part's envelope conforms to a
published standard (`spec/schemas/standards.yaml`) and stands for every product of
its kind under that standard; no standard governs a boot - its size follows the cable
OD and the vendor's own tooling. SENKO's LC 2PC datasheet lists six boot options
across three diameters, the LC-HD four; Platinum Tools sells RJ45 boots for 5.5 to
8.5mm cable. A `generic/` boot would present one vendor's accessory as the shape of a
class that doesn't exist - the error L99 already refuses for a transceiver one level
up. `common/` is the namespace for shapes that stand for a class of part rather than
one product, and makes no standards claim. Neither boot is a sourcing failure: both
are fully dimensioned, `common/lc-boot` off SENKO DS-LC-000023 (15.1 +/-0.1) and
`common/rj45-boot` off EASE J0072 rev A (26.4 +/-0.5).

Second batch, once the `cable` contract has been used by the cabling side: SC plug
and boot (with `std/sc-bore` from A); the MPO plugs - `generic/mpo12-plug`,
`generic/mpo24-plug` (same key as mpo12, own part for the two-row ferrule) and
`generic/mpo16-plug` (a different key, so a different interface), all UNPINNED
because the module receptacles they land on carry the pins; and the DAC/AOC ends - an SFP- or
QSFP-shaped plug with a boot and no optical face, which is the cleanest proof that
the contract is right because it is a transceiver AND a connector.

Sources: SENKO DS-LC-000004 Rev A (LC plug body 5.58, silhouette 10.43, latch widths
with tolerances - the strongest document in the LC corpus). Boot lengths come from
SENKO DS-LC-000023 (LC, 15.1 +/-0.1) and EASE J0072 rev A (RJ45, 26.4 +/-0.5); an
earlier draft of this spec named TE 2271178 and the SENKO technical brochure for
this, and neither gives one. The brochure carries no geometry at all - the LC intake
recorded it as "Marketing, not mechanical" - and TE 2271178 turns out to be an
industrial duplex LC ODVA bulkhead receptacle kit with a waterproof dust cap, a
panel-mount housing, not a plug and not a boot (COVERAGE.md's third pass). A TE RJ45
plug customer drawing (fetch - the jack already comes from TE 1734264). IEC 61754-20
and IEC 60603-7 are paywalled and gate the aperture keyway, not the plug body; the
plugs are built without them and say so.

An LC plug has no class-wide overall length. Three SENKO drawings give it only as a
parenthesised REFERENCE dimension, and it differs every time - `(42)` on the 2PC
(911/912), `(38.6)` on the XP Fit Plus (951), `(43)` on the LC-HD (913/914) - while
body height (5.65) and latch length (8.6) repeat across all three WITH tolerances.
The class fixes the front profile and the latch; the back end is the vendor's, and a
parenthesised REFERENCE is not a figure any drawing dimensions. So `generic/lc-plug`
carries no `d`. `generic/rj45-plug` DOES carry one (22.48) - CommScope's drawing gives
it as a plain dimension, not a parenthesised reference - so the two plugs differ for
a reason, not by oversight.

## The two-part fit

A plug declares, besides its `mate`, a rear connection-point and the interface it
presents there:

```yaml
# generic/lc-plug
mates: lc
interface: lc-plug            # what a boot mates
connection-points:
  mate:  {at: [..], direction: front}
  boot:  {at: [..], direction: rear}      # where a boot lands
  cable: {at: [..], direction: rear}      # where a cable lands when there is no boot
```

```yaml
# common/lc-boot
mates: lc-plug
attrs: {boot-length: <mm>}
connection-points:
  mate:  {at: [..], direction: front}
  cable: {at: [..], direction: rear}      # inside the boot; the cable's first vertex is hidden
```

A boot seats on a plug the way an optic seats in a cage - through `occupants:` or
`mate-to`, positioned by mate points, held by L12. Two parts, one mechanism, and a
downstream tool chooses boot or no boot per connector - but the plug hosting the boot
is itself usually seated the same way, in a bore or a jack, and that chain is the part
the renderer could not do yet. See Render change 3.

### Render change 1: an occupant carries depth

Today a `mate-to` seat has no z of its own; only `parts:` composition carries
`lift`. A boot behind a plug is displaced in depth, and so is a plug in a
transceiver's bore (the bore is already `lift`ed to the module face). The occupant
expansion gains a `lift` equal to the host's resolved protrusion at the mate point,
written as `data-z-lift` on the occupant's group exactly as composition writes it, so
`relief.js`'s existing ancestor sum places it. One code path; `test_occupants` gains
the case.

### Render change 2: connection-points reach the drawing

No connection-point is emitted into the compiled SVG today; `render.py` reads `mate`
to position an occupant and drops the rest. Each part's `connection-points` are
emitted as marker nodes inside the part's instance group:

```
<g data-cp="cable" data-cp-at="6.75 4.25" data-cp-dir="rear" .../>
```

in the part's own frame, under the same group that carries `data-z-lift` and
`data-z-out`, so a consumer resolves the point in the chassis frame with the same
walk `relief.js` uses for every feature: sum the ancestors' lifts, add the part's
own out, apply the group transforms. Nothing new to compute on the client; the point
is where the geometry already is.

`kit/states.js`-style accessor, not page code: `cablePoints(svg)` returns every
`cable` marker with its resolved chassis-frame position and direction, taking the
OUTERMOST one per connector (the boot's when a boot is seated, the plug's when not).
That function is the contract the cabling library consumes. A `mate-to` occupant is a
TOP-LEVEL SIBLING of its host in the compiled drawing, not a path descendant - a boot
seated on a plug seated on a cage gets three unrelated top-level paths, no one a
prefix of another, so grouping cannot walk `data-path` the way a composed or bayed
part's does. `render.py` already writes `data-for` on every seated occupant naming
its host; `cablePoints()` walks `data-for` to a root and groups every `cable` marker
under that root instead.

### Render change 3: mate-to resolves to a fixed point

`hosts` was built once, from placements carrying an explicit `at` - so a seated
`mate-to` occupant (the plug, seated in a bore) could never itself host a further
occupant (the boot), which blocks exactly the chain this spec asks for. Composition
is not an alternative: composed `parts:` entries have no `optional` flag and are
compile-time flattened, so a composed boot could not be chosen per connector. B2 made
resolution run to a fixed point instead: each pass seats the occupants whose host is
now known and adds them to `hosts`, until a pass seats nothing - which is either every
occupant resolved, a dangling `mate-to` (the existing error), or a cycle (a new one,
since without it an unresolvable chain would loop forever). The `cablePoints`
grouping above is the same limit at one remove, and is resolved the same way - by
following `data-for`, which records the seat chain the path does not, not by nesting
a boot into its plug's `parts:`.

## Boot

`boot-length` is the straight run before the cable may bend, an attr on the boot
part in millimetres, sourced from the manufacturer drawing. `boot-bend` is reserved
for a later spec - the two lateral deflection limits - and is not written until the
cabling side asks for it.

## Lint

- L12 already holds `mates` to the presented `interface`; a boot on a bore or a plug
  on a plug is caught by the existing rule.
- L12 grows two comparisons where both sides declare them, under the same rule
  number because it is the same question: `optical.gender` must be opposite (a
  pinned receptacle takes an unpinned plug, never pinned-to-pinned), and
  `optical.polish` must match (an APC plug does not seat in a UPC receptacle). A
  side that declares neither is not checked - the library has hundreds of bores
  that predate the keys, and silence stays silence rather than becoming an error.
- New: a part declaring `cable` must declare `direction`, and a plug must declare
  `boot` or be marked as one that takes no boot. Small, in the connection-points
  schema rather than a rule.

## Order of work

1. Render change 2 first (markers), because it is needed by A's transceivers too
   (`optical-tx/rx` reach the drawing for free) and is testable on today's library.
2. Render change 1 (occupant lift), with the test.
3. `generic/lc-plug` off SENKO DS-LC-000004; `common/lc-boot`.
4. Fetch the TE RJ45 plug drawing; `generic/rj45-plug`, `common/rj45-boot`.
5. `cablePoints()` in the kit and a JS test that resolves a boot seated on a plug
   seated in a bore on a transceiver in a cage, and checks the point against hand
   arithmetic.

## Open questions

- Whether a boot is ever a runtime choice in practice, or always seated. The
  mechanism allows both; the default configuration the kit shows should be decided
  by the first consumer.
- The RJ45 plug's latch: it stands proud of the plug body and is the part a cable
  library would clip; whether it is a relief feature or geometry the cable side
  owns.

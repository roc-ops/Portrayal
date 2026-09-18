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
| `generic/lc-boot` | `lc-plug` | the plug's rear |
| `generic/rj45-plug` | `rj45` | `std/rj45-ganged@2`, `std/rj45@N`, and the vendor jacks that wrap them |
| `generic/rj45-boot` | `rj45-plug` | the plug's rear |

Second batch, once the `cable` contract has been used by the cabling side: SC plug
and boot (with `std/sc-bore` from A), MPO plug, and the DAC/AOC ends - an SFP- or
QSFP-shaped plug with a boot and no optical face, which is the cleanest proof that
the contract is right because it is a transceiver AND a connector.

Sources: SENKO DS-LC-000004 Rev A (LC plug body 5.58, silhouette 10.43, latch widths
with tolerances - the strongest document in the LC corpus), TE 2271178 and the SENKO
technical brochure for boot lengths; a TE RJ45 plug customer drawing (fetch - the jack
already comes from TE 1734264). IEC 61754-20 and IEC 60603-7 are paywalled and gate
the aperture keyway, not the plug body; the plugs are built without them and say so.

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
# generic/lc-boot
mates: lc-plug
attrs: {boot-length: <mm>}
connection-points:
  mate:  {at: [..], direction: front}
  cable: {at: [..], direction: rear}      # inside the boot; the cable's first vertex is hidden
```

A boot seats on a plug the way an optic seats in a cage - through `occupants:` or
`mate-to`, positioned by mate points, held by L12. Two parts, one mechanism, and a
downstream tool chooses boot or no boot per connector.

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
That function is the contract the cabling library consumes.

## Boot

`boot-length` is the straight run before the cable may bend, an attr on the boot
part in millimetres, sourced from the manufacturer drawing. `boot-bend` is reserved
for a later spec - the two lateral deflection limits - and is not written until the
cabling side asks for it.

## Lint

- L12 already holds `mates` to the presented `interface`; a boot on a bore or a plug
  on a plug is caught by the existing rule.
- New: a part declaring `cable` must declare `direction`, and a plug must declare
  `boot` or be marked as one that takes no boot. Small, in the connection-points
  schema rather than a rule.

## Order of work

1. Render change 2 first (markers), because it is needed by A's transceivers too
   (`optical-tx/rx` reach the drawing for free) and is testable on today's library.
2. Render change 1 (occupant lift), with the test.
3. `generic/lc-plug` off SENKO DS-LC-000004; `generic/lc-boot`.
4. Fetch the TE RJ45 plug drawing; `generic/rj45-plug`, `generic/rj45-boot`.
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

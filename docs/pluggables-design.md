# Pluggables: generics, connectors, slotting, 3D

Status: design agreed 2026-09-18. Four specs, each its own document,
built in the order below. This page holds what they share and why they are
split; the detail is in each one.

| spec | document | delivers | depends on |
|---|---|---|---|
| A | [pluggables-generics-design.md](pluggables-generics-design.md) | `generic/` transceivers off the MSAs, the vendor-wrapper idiom, migration off the two `common/` generics | OSFP MSA fetch |
| B | [pluggables-connectors-design.md](pluggables-connectors-design.md) | LC and RJ45 plugs and boots, a `cable` point published into the compiled drawing, occupants that carry depth | A |
| C | [pluggables-slotting-design.md](pluggables-slotting-design.md) | cages swappable in the kit's inspector, accept lists derived from `interface:` plus a ladder registry, vendor-blind | A |
| D | [pluggables-3d-design.md](pluggables-3d-design.md) | every pluggable standing proud of its cage in 3D, plugs standing off their bores, the body-skin decision | A, B |
| B3 | [pluggables-caps-design.md](pluggables-caps-design.md) | dust caps as connectors in one connector slot per port, shipped as each adapter's default; SC and MPO plugs; the duplex LC host; the kit seating at a lift | B, C, D |

## What is wrong today

The library holds ~5,000 pluggable cages and two transceivers. `common/sfp-lc-duplex`
is a specific 30 km single-mode module wearing a generic's name, and
`common/qsfp-transceiver` is marked `unplaced` and protrudes 0 mm in 3D. The
mechanism for seating an optic - `configurations.<n>.occupants:` expanding into a
`mate-to` placement, L12 holding `interface:` to `mates:` - exists, is tested, and is
used by five devices to draw builds fitted with optics that this library should not
be shipping populated. No plug of any kind exists, and no connection-point reaches
the compiled drawing, so nothing downstream can find where a cable would land.

## Decisions

Taken 2026-09-18, in this order:

| # | decision |
|---|---|
| 1 | Transceivers are GENERICS drawn once per form factor and face. A vendor's optic WRAPS a generic via `parts:` and carries the vendor's facts in its own `attrs`; a vendor may draw their own outlier instead. One contribution mechanism, no third path |
| 2 | Portrayal builds the slotting mechanism and ships its device models BARE. Populating is a downstream tool's job; the five configs that seat optics today are stripped. AMENDED by B3 (docs/pluggables-caps-design.md, decision 5): a slot's `default:` occupant, such as a shipped dust cap, is the product's shipped state, like a bay's blank; Portrayal still ships no configured optic, plug or cable |
| 3 | A new namespace `generic/` - *representative of a class under a spec*: the envelope is standard, the appearance stands for every part of its kind. The future home of DIMMs, PCIe cards, CPUs and anything else interchangeable across vendors under a spec. Existing `common/` parts are not migrated in this work |
| 4 | Colour and label are FIELDS on a generic (`data-fill-from` / `data-from`), set by the wrapper. The FACE is not: bores are parts and parts are emitted for every skin, so the face is in the component's name - `sfp-lc`, `sfp-sc`, `qsfp-mpo` |
| 5 | A generic carries NO rate. `generic/sfp-lc` is SFP, SFP+ and SFP28 alike; the rate is the wrapper's attr. This is already how the cages work: every SFP-family cage presents `interface: sfp` and L12 compares interface only |
| 6 | Slotting offers anything in the library that mates the cage's interface and fits the ladder, vendor-blind. A third party's optic appears the moment it lints |
| 7 | The compatibility LADDER is the MSAs' form/electrical compatibility (QSFP-DD HW 6.3 section 1 for the QSFP families) and drives slotting. Whether a host lights a given lane arrangement is firmware, stays `port-modes-<media>` prose on the device, and is never claimed by the registry |
| 8 | Connectors are generics too. A plug and its boot are TWO parts that seat together at runtime; the `cable` point is one 3D point inside whichever is outermost, with a direction, and `boot.length` says how far the cable runs straight. Bend limits are reserved, not written |
| 9 | Every pluggable protrudes - SFP, QSFP, QSFP-DD, OSFP, XFP, CFP, CFP2 - so every generic ships with `relief.features` from its MSA, not as a later pass |
| 10 | SAME SHAPE, DIFFERENT THING is split by what it changes. A different KEY is a different interface and a different part (MPO-12 family vs MPO-16 family - they do not intermate). A different FERRULE under the same key is a separate part sharing the shell, with the count in `optical.positions` (MPO-12 vs MPO-24 two-row - the precedent is `common/mpo24-adapter`). A different FACT on the same ferrule is a field or an `optical` key on one part - lit count (`unused`), polish (APC/UPC), pin gender. Polish and gender are mating constraints and the mate check compares them |

## What is one part and what is two, once

The MSAs settle the MPO question directly. QSFP-DD HW 6.3 section 6.2.1: MPO-12 one
row is TIA-604-5 / IEC 61754-7-1; MPO-12 two row (24 fibres) is TIA-604-5 / IEC
61754-7-2; MPO-16 one row is TIA-604-18 / IEC 61754-7-3, a different key. And the
QSFP+ spec's own receptacle figure (INF-8074 Fig 21a) shows an MPO-12 with four
positions marked "unused" - an 8-fibre SR4 is a 12-position receptacle with eight
lit, not a different connector. So:

| differs by | example | modelled as |
|---|---|---|
| key | MPO-12 family vs MPO-16 family | separate interface, separate parts |
| ferrule under one key | MPO-12 vs MPO-24 two-row | separate parts, same shell, `optical.positions` |
| lit count on one ferrule | MPO-12 carrying 8 | one part, `optical.unused` on the module |
| polish | LC/UPC vs LC/APC, MPO/UPC vs MPO/APC | one part, `optical.polish`; the mate check refuses a mismatch |
| pin gender | pinned module receptacle vs unpinned plug | one part, `optical.gender`; the mate check requires opposites |
| simplex vs duplex vs dual | LC vs dual LC vs dual duplex LC | different faces, different parts (decision 4) |

Both module specs say the module-side MPO receptacle is pinned ("two alignment pins
are present in each receptacle"; "a male MPO connector"), so every plug that lands on
a transceiver is unpinned, and a panel adapter is where pinned meets unpinned.

## The vendor wrapper, once

```yaml
# library/components/cisco/sfp-10g-lr/v1/contract.yaml
kind: module
class: transceiver
behaviour: occupies
mates: sfp
size: {w: 13.55, h: 8.55, d: 47.50}
size-confidence: {w: borrowed, h: borrowed, d: borrowed}
parts:
  - {ref: generic/sfp-lc@1, id: body, at: [0, 0],
     attrs: {latch-color: '#2f5fa8', label: SFP-10G-LR}}
attrs: {model: SFP-10G-LR, media: sfp-plus, speed: 10g, reach: 10km,
        wavelength: 1310nm, power-draw-max-w: 1.0}
provenance:
  size: 'borrowed - generic/sfp-lc@1, the generic this wraps; its figures, not a Cisco drawing'
connection-points:
  mate: {at: [6.775, 4.275], direction: front}
```

The wrapper RESTATES the generic's mate point and so seats exactly where the
generic would. An occupant mates with its own point - the renderer reads
`connection-points.mate` off the occupant's contract and refuses a `mate-to`
placement without one - and mate-forwarding (#54) runs the other way, letting a
vendor CAGE present the aperture it composes to the module that seats in it. The
renderer already passes a `parts:` entry's `attrs` into the wrapped skin, which is
how the latch takes its colour. `kind: module` because a vendor optic is orderable
and the DCIM export emits module types only for `kind: module`; the generic stays
`kind: component`.

## The ladder, once

```
sfp:      sfp < sfp-plus < sfp28 < sfp56       one cage interface; SFF-8432 envelope
qsfp:     qsfp < qsfp28 < qsfp56 < qsfp112     one cage interface; SFF-8661 envelope, SFF-8663 cage governs 28 and 56
qsfp-dd:  accepts qsfp-dd and every qsfp       QSFP-DD HW 6.3 section 1
osfp, xfp, cfp, cfp2: alone
```

A cage's ceiling is its port group's `media`, declared on every port group already.

## Sources held

Held locally, not in this repository: SFF-8432 Rev 5.2a (SFP+ module and cage; Fig 4-1,
Table 4-3), SFF-8661 Rev 2.5 (QSFP module; Fig 5-1), SFF-8663 Rev 1.7 (QSFP28 cage),
QSFP-DD/QSFP-DD800/QSFP112 HW Rev 6.3 (section 7.3 module form factors, Figs 47-50).
Also held locally: SENKO DS-LC-000004 (LC plug,
toleranced), TE 2271178, the SENKO technical brochure. Not held: the OSFP MSA (free,
fetch), a TE RJ45 plug drawing (free, fetch), IEC 61754-20 and IEC 60603-7 (paywalled -
they gate aperture keyways, not plug or module bodies), TIA-604-10 (paywalled - the
only document that dimensions the LC receptacle on a module face).

Standards PDFs are read and their facts transcribed; none is committed.

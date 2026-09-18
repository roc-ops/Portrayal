# Pluggables: generics, connectors, slotting, 3D

Status: design agreed with Jason, 2026-09-18. Four specs, each its own document,
built in the order below. This page holds what they share and why they are
split; the detail is in each one.

| spec | document | delivers | depends on |
|---|---|---|---|
| A | [pluggables-generics-design.md](pluggables-generics-design.md) | `generic/` transceivers off the MSAs, the vendor-wrapper idiom, migration off the two `common/` generics | OSFP MSA fetch |
| B | [pluggables-connectors-design.md](pluggables-connectors-design.md) | LC and RJ45 plugs and boots, a `cable` point published into the compiled drawing, occupants that carry depth | A |
| C | [pluggables-slotting-design.md](pluggables-slotting-design.md) | cages swappable in the kit's inspector, accept lists derived from `interface:` plus a ladder registry, vendor-blind | A |
| D | [pluggables-3d-design.md](pluggables-3d-design.md) | every pluggable standing proud of its cage in 3D, plugs standing off their bores, the body-skin decision | A, B |

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

Taken with Jason, 2026-09-18, in this order:

| # | decision |
|---|---|
| 1 | Transceivers are GENERICS drawn once per form factor and face. A vendor's optic WRAPS a generic via `parts:` and carries the vendor's facts in its own `attrs`; a vendor may draw their own outlier instead. One contribution mechanism, no third path |
| 2 | Portrayal builds the slotting mechanism and ships its device models BARE. Populating is a downstream tool's job; the five configs that seat optics today are stripped |
| 3 | A new namespace `generic/` - *representative of a class under a spec*: the envelope is standard, the appearance stands for every part of its kind. The future home of DIMMs, PCIe cards, CPUs and anything else interchangeable across vendors under a spec. Existing `common/` parts are not migrated in this work |
| 4 | Colour and label are FIELDS on a generic (`data-fill-from` / `data-from`), set by the wrapper. The FACE is not: bores are parts and parts are emitted for every skin, so the face is in the component's name - `sfp-lc`, `sfp-sc`, `qsfp-mpo` |
| 5 | A generic carries NO rate. `generic/sfp-lc` is SFP, SFP+ and SFP28 alike; the rate is the wrapper's attr. This is already how the cages work: every SFP-family cage presents `interface: sfp` and L12 compares interface only |
| 6 | Slotting offers anything in the library that mates the cage's interface and fits the ladder, vendor-blind. A partner's optic appears the moment it lints |
| 7 | The compatibility LADDER is the MSAs' form/electrical compatibility (QSFP-DD HW 6.3 section 1 for the QSFP families) and drives slotting. Whether a host lights a given lane arrangement is firmware, stays `port-modes-<media>` prose on the device, and is never claimed by the registry |
| 8 | Connectors are generics too. A plug and its boot are TWO parts that seat together at runtime; the `cable` point is one 3D point inside whichever is outermost, with a direction, and `boot.length` says how far the cable runs straight. Bend limits are reserved, not written |
| 9 | Every pluggable protrudes - SFP, QSFP, QSFP-DD, OSFP, XFP, CFP, CFP2 - so every generic ships with `relief.features` from its MSA, not as a later pass |

## The vendor wrapper, once

```yaml
# library/components/cisco/sfp-10g-lr/v1/contract.yaml
class: transceiver
behaviour: occupies
mates: sfp
parts:
  - {ref: generic/sfp-lc@1, id: body, at: [0, 0],
     attrs: {latch-color: '#2f5fa8', label: SFP-10G-LR}}
attrs: {model: SFP-10G-LR, media: sfp-plus, speed: 10g, reach: 10km,
        wavelength: 1310nm, power-draw-max-w: 1.0}
```

Mate-forwarding (#54) seats the wrapper exactly where the generic would; the
renderer already passes a `parts:` entry's `attrs` into the wrapped skin, which is
how the latch takes its colour.

## The ladder, once

```
sfp:      sfp < sfp-plus < sfp28 < sfp56       one cage interface; SFF-8432 envelope
qsfp:     qsfp < qsfp28 < qsfp56 < qsfp112     one cage interface; SFF-8661 envelope, SFF-8663 cage governs 28 and 56
qsfp-dd:  accepts qsfp-dd and every qsfp       QSFP-DD HW 6.3 section 1
osfp, xfp, cfp, cfp2: alone
```

A cage's ceiling is its port group's `media`, declared on every port group already.

## Sources held

In OKF's `ndv-standards` bundle: SFF-8432 Rev 5.2a (SFP+ module and cage; Fig 4-1,
Table 4-3), SFF-8661 Rev 2.5 (QSFP module; Fig 5-1), SFF-8663 Rev 1.7 (QSFP28 cage),
QSFP-DD/QSFP-DD800/QSFP112 HW Rev 6.3 (section 7.3 module form factors, Figs 47-50).
On disk under `working/intake/fiber-connectors/lc`: SENKO DS-LC-000004 (LC plug,
toleranced), TE 2271178, the SENKO technical brochure. Not held: the OSFP MSA (free,
fetch), a TE RJ45 plug drawing (free, fetch), IEC 61754-20 and IEC 60603-7 (paywalled -
they gate aperture keyways, not plug or module bodies), TIA-604-10 (paywalled - the
only document that dimensions the LC receptacle on a module face).

Standards PDFs are read and their facts transcribed; none is committed.

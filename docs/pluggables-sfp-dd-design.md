# Pluggables: the SFP-DD cages

Status: built 2026-10-24. Two cages, drawn from two cage makers' drawings and
no MSA. Part of [pluggables-design.md](pluggables-design.md); a sibling of
[pluggables-osfp-xfp-design.md](pluggables-osfp-xfp-design.md).

Before this, `sfp-dd` was a value in the media vocabulary and a family on the
ladder (`spec/schemas/pluggables.yaml`) with no cage behind it, and L103 warned
about it. DSFP is left out: no maker publishes a drawing of its cage.

## What was added

| part | what it is |
|---|---|
| `std/sfp-dd@1` | a single cage: 15.45 x 10.40 panel opening, 14.00 x 8.95 interior, 38.9 deep, with a collar |
| `std/sfp-dd-ganged@1` | one port's 14.25 x 10.40 share of a ganged 1xN slot, no collar |
| `sfp-dd`, `sfp-dd-ganged` | their entries in `spec/schemas/standards.yaml`, which lint L9 holds the contracts to |

Ganged variants are added because both makers' cages ganged 1x4, 1x6 and 1x8
(TE 114-60027) and the Arista 7050X4 faces that need this cage put 48 ports in
rows. The ganged cage is the same idea as `std/sfp-ganged@1`: the cutout is one
continuous slot N x 14.25 + 1.2 wide, so the port's share is 14.25.

## Sources

| figure | TE C-2359845 rev A, 114-60027 rev A | Molex 2048233001 rev A, 2048230001 rev A |
|---|---|---|
| bezel cutout, 1x1 | 15.45 x 10.40, sheet 3, Figure 4 | 15.45 x 10.40, sheet 6 |
| port interior | 14.00 +/-0.10 x 8.95 +/-0.10, sheet 1 | 14.00 +/-0.10 x 8.95 +/-0.15, sheet 1 |
| key notch | 1.20 high, 3.90 off centre, sheet 3 | the same, sheets 1 and 6 |
| port pitch, ganged | 14.25, 3.2 A | not stated |
| single-cage pitch | 16.25 min, sheet 3 | not stated; 1.30 min web "for reference" |
| bezel to connector | 38.90 +/-0.30 to the guide pins | not stated |
| height of the cutout bottom above the board | 0.175 +/-0.10 | 0.40 +/-0.10 |
| minimum board, belly to belly | 2.20 | 2.55 on the drawing, 2.70 in the specification |

Where the makers differ the registry uses TE's figure and says so. Neither
maker states a belly-to-belly row pitch, so the registry records none. Both
draw the lower row as the upper turned over, key notches outward.

## What is unconfirmed

Only the MSA settles the lane count, the rates and whether an SFP module is
specified to work in the cage. The makers state that the cage mates with
SFP-DD MSA compliant transceivers and that its connector is 40 positions at
0.8 mm pitch. They state no rate. The registry carries two lanes, 25G or 50G a
lane and an SFP backwards-compatibility, each marked `unconfirmed`.

## What was not done

- No generic optic. An SFP-DD cage offers the SFP generics through
  `also-accepts` and the `sfp` ladder, and no part states `mates: sfp-dd`.
- The key notch and the latch are not drawn. The notch is the plain rectangle's
  only departure, and the makers word the latch differently.
- L108 does not check SFP-DD stacks, and an SFP+ group on an SFP-DD cage is an
  L22 error and an L104 warning, because `sfp-plus` and `sfp-dd` are different
  families. Both rules live in `lint.py`, which this change leaves alone; the
  first device that needs either one changes it.

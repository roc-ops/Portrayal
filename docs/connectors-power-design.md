# Connectors: AC power

Status: implemented, 2026-10-05. Issue #785. Builds on
[pluggables-caps-design.md](pluggables-caps-design.md) (a presented connector interface is
a SLOT that offers every part whose `mates:` names it) and follows
[connectors-coax-design.md](connectors-coax-design.md) part for part: a registry entry per
interface, a generic plug per interface, and a cable stub whose diameter is a field.

## 1. What existed, and what was missing

The library drew AC inlets and could seat nothing in them.

| part | interface | where it is placed |
|---|---|---|
| `std/c14-inlet@1` | `iec-c14` | 60 component `parts:` entries (supplies, one four-inlet panel) and 4 devices |
| `std/c20-inlet@1` | `iec-c20` | 13 component entries and the MX960 chassis |
| `std/saf-d-grid@1` | `saf-d-grid` | 3 supplies; no chassis |

Each inlet already declared its interface, a `mate` point at the centre of its cutout and a
cavity. None of the three interfaces was in `spec/schemas/connectors.yaml`, so no inlet
published a slot, and there was no cord end.

## 2. Decisions

1. **One interface per inlet:** `iec-c14`, `iec-c20` and `saf-d-grid`, each citing the
   `standards.yaml` key its inlet already conforms to (`c14-inlet`, `c20-inlet`,
   `saf-d-grid`). A Saf-D-Grid receptacle sits in a C14 cutout, but a C13 does not mate
   it, so it is its own interface.
2. **Three generic cord ends:** `generic/c13-plug@1`, `generic/c19-plug@1` and
   `generic/saf-d-grid-plug@1`. Each is `class: port` with `mates:`, no `behaviour` and no
   `size.d`; its length is in its `standards.yaml` entry and its relief, as on the coax
   plugs.
3. **Drawn from the cable end.** A front elevation of a seated plug looks at its rear, so
   each skin draws the overmould's section, the strain relief and the cord. The contact
   face is in the inlet and is not drawn.
4. **A 30 mm stub of cord** from the end of the strain relief, sized by `cable-od` and
   coloured by `jacket-color`, with the `cable` point on it. The far end of the cord is not
   a part (section 7).
5. **The inlets are unchanged.** No inlet contract's geometry moves; registering the
   interfaces is what makes them slots.
6. **A cord end's `media` is its connector** (`c13`, `c19`, `saf-d-grid`), not `ac`. A
   `class: port` part's media becomes a connector word for lint L62, and `ac` there would
   flag every placement whose id opens with `ac-`.

## 3. The slots

With the registry entries, every inlet publishes a `kind: connector` slot on the next build,
by the same core (`render.slot_entry`) as every other slot. Three shapes occur, and none
needed a wrapper changed:

- **An inlet placed on a chassis** (the ReadyLinks GL-12xB-240D, the MX960) is a slot in the
  device view's `cages[]`, keyed by the placement.
- **An inlet on a supply that seats in a bay** is a nested slot in the supply's own
  `components.json` entry, keyed `<bay>/<part>` (`psu-0/inlet`). A four-inlet panel placed
  on a face (`casa/c40g-ac-inlet-panel@1`) publishes its four the same way, keyed
  `<placement>/<part>`.
- **A supply PLACED on a face that composes one inlet** (`common/psu-550w@2`) presents that
  inlet as its own, so the slot is the supply's placement.

After the build 76 component `parts:` entries are inlets: 60 `iec-c14`, 13 `iec-c20` and
3 `saf-d-grid`. Of those, 74 publish a slot on the component that composes them and 2
(`common/psu-550w@2`, `ufispace/psu-120-ac@1`) are forwarded to wherever the supply is
placed. Each slot offers exactly one part, its cord end.

## 4. Sources

IEC 60320-1 is not held. Every "IEC-shaped" figure is what a vendor drawing prints.

| part | source | what it prints |
|---|---|---|
| C13 | Volex Power Products catalogue, Aug-2025, cat. no. V1625, p.240, and V1625BS, p.249 | overall 64 +/-1; nose 18 MIN, 23 x 15.8, two corners cut at 45 degrees; overmould 26 +/-0.5 |
| C19 | the same catalogue, cat. no. VAC19, p.262 | overall 76 +/-1; nose 20 (MIN), 28 x 20, R3.5 (MIN) four times; overmould 29 x 24, 26.00 long; lugs 37 across; strain relief 30.0 +/-0.5 |
| Saf-D-Grid | Anderson Power Products data sheet DS-SDG REV 19, p.16 | 26.0 wide, 18.9 high, 80.5 long, and nothing else |
| C13 cord (the `cable-od` of a NEMA 5-15P cord; the IEC ends default to the H05VV-F rows below, #1060) | Belden 19348 technical data sheet, revision 0.388, 09-07-2025, p.1 | SJT 3 x 18 AWG, 0.328 in nominal (8.33 mm, converted) |
| C19 and Saf-D-Grid cord (the 5-20P cord's `cable-od` and the Saf-D-Grid end's) | Belden 19354 technical data sheet, revision 0.525, 09-07-2025, p.1 | SJT 3 x 14 AWG, 0.380 in (9.65 mm) nominal |
| C13/C14 and C19/C20 cord, IEC ends' default | Oznur Kablo, H05VV-F 300/500 V flexible cord technical data (cited in `spec/schemas/cable-types.yaml`) | H05VV-F 3G1.0 7.1 mm and 3G1.5 7.9 mm nominal overall diameter: the `power-c13` and `power-c19` cords the kit draws |

The Volex catalogue gives no drawing number or revision for a connector; the citation is
catalogue, date and page. All three drawings are of moulded straight connectors. A
rewireable connector is a larger body and was not used.

The Saf-D-Grid cord is 14 AWG SJT because DS-SDG REV 19 pp.13-14 list that cord on the
Saf-D-Grid to IEC jumpers and p.16's dimensioned plug is the 18-14 AWG one; Anderson prints
no cord diameter, so the diameter is the cable maker's.

Black is the default jacket: every held source that states a colour states black, and none
states a convention.

## 5. The seated depth

**Ruling: each plug seats with its nose on the floor of the cavity its inlet MODELS**, the
way `generic/lc-plug@2` seats in its bore. The inlet presents at its own face (its `mate`
carries no `on:` and no `seat-out`), so the published slot `lift` is 0 on a flat panel, and
the plug's own relief starts there. The plug therefore stands its overall length less the
modelled cavity depth in front of the inlet's face:

| plug | overall | nose | modelled cavity | nose left in front | stands off | stub ends |
|---|---|---|---|---|---|---|
| C13 | 64 | 18 MIN | 17.0 (drawing, #793) | 1.0 | 47.0 | 77.0 |
| C19 | 76 | 20 (MIN) | 19.0 (estimated, #793) | 1.0 | 57.0 | 87.0 |
| Saf-D-Grid | 80.5 | about 25.5 (scaled) | 17.0 (measured) | 8.5 | 63.5 | 93.5 |

**The nose is longer than the modelled cavity on all three.** For the IEC pair the nose is
the printed figure: a nose that went fully home would leave 46 and 56 at most, 1 less than
is drawn. #793 moved both inlets 4 deeper: the C14's 17.0 is dimensioned (Adam Tech drawing
S00087C rev D, shroud face to floor 17.00 +0/-1.00), and the C20's 19.0 is estimated from it
(the C19 nose less 1, as the C13/C14 pair stands) and is still the depth to revisit. When an
inlet's depth moves, its plug's `lift` and `out` figures move by the difference and nothing
else changes; a test pins the two together so one cannot move without the other.

For Saf-D-Grid it is the other way round. The 17.0 is dimensioned on drawing 115171S1 rev
12, which also puts 5.8 of housing in front of the panel that `std/saf-d-grid@1` does not
model, and the nose is scaled. A nose seated to its collar on that housing would leave
about 60.8 in front of the panel. What to revisit there is the inlet's missing front
housing and a dimensioned plug drawing.

The part of the nose inside the cavity is not built. In 3D the plug's solids start at the
panel plane and the inlet's own cavity is behind them.

## 6. What is estimated

- **Both IEC inlet depths**, and so every `lift` and `out` on the two IEC plugs. Each relief
  feature says `estimated` for that reason, including the ones whose length is dimensioned.
- **C13:** the overmould's thickness (16.0), its length (26.0) and the strain relief (20.0
  long, 11.6 across) are scaled from catalogue rasters of 4 to 6 px/mm, good to about 0.3.
  The overmould's cut corners take the nose's. The taper to the strain relief is built as
  two steps, the rear one at the 21.6 the moulding's ears span.
- **C19:** the strain relief's 16 section is scaled; the overmould's corner radius and the
  lugs' centring are estimated; the tolerance on the 24 is garbled in the raster.
- **Saf-D-Grid:** everything but 26.0, 18.9 and 80.5 is scaled from the data sheet's vector
  drawing. The nose outline is not traced; it is drawn as the mate of the inlet's own
  cavity. The latch button is not drawn. The overmould's taper is not built.
- **The stub** is a rule, not a reading.

One vendor's drawing stands behind each IEC part; no second moulded drawing was found to
check it against.

## 7. Out of scope

- **The far end of the cord:** the wall plug, a C14 or C20 on a jumper, and the regional
  plugs. Issue #792.
- Locking variants, angled connectors and rewireable connectors.
- C15, C17 and C21 connectors, which are different interfaces.
- The 12 AWG wide-latch and 300 V keyed Saf-D-Grid plugs, which are larger bodies.
- Power distribution, and any cable run or bend. The stub is straight and stops at the
  `cable` point.
- Devices ship bare. A cord end is in a slot's accept list because it mates the slot's
  interface; nothing seats one by default.

## 8. Testing

`spec/tests/test_ac_cord_ends.py`, against the real library and builds made by the test:

1. The registry holds the three interfaces, each citing its inlet's standard.
2. Slots: a chassis inlet, a supply's inlet in a bay, the four-inlet panel and a placed
   supply each publish theirs; a census finds no composed inlet that is neither a slot nor
   forwarded.
3. Each plug's class, `mates`, fields and registry entry; no `size.d`.
4. The stub is 30 long from the end of the strain relief, and the `cable` point is on it.
5. Seating in real inlets, flat and turned: the plug's mate lands on the inlet's.
6. The seated depth: the compiled plug stands its overall length less the compiled cavity
   depth in front of the inlet face, and the published slot lift is where it starts.
7. 3D: every solid is right side out and the chain has no gap.
8. The stub's diameter is `cable-od`, by default and from a placement.

## 9. The outlet side: NEMA receptacles and the Eaton C39

Issue #1045. Sections 1 to 8 made an inlet a slot. A rack PDU's C13 and C19 outlets became
slots with #933. Two outlet parts were still no slot, so a cord could not be addressed to
them: `std/nema-5-20r@1` and `eaton/c39-outlet@1`.

### 9.1 Three interfaces

| interface | presented by | mated by |
|---|---|---|
| `nema-5-15r` | `std/nema-5-15r@1` | `generic/nema-5-15p-cord@1` |
| `nema-5-20r` | `std/nema-5-20r@1` | `generic/nema-5-15p-cord@1`, `generic/nema-5-20p-cord@1` |
| `eaton-c39` | `eaton/c39-outlet@1` | `generic/c14-plug@1`, `generic/c20-plug@1` |

- **The key names the receptacle**, as `iec-c13` names the outlet and not the plug that
  enters it. `nema-5-15r` and `nema-5-20r` are the NEMA WD 6 designations in lower case:
  the spelling the `nema-5-20r` entry of `standards.yaml` and the outlet type of both DCIM
  targets already have. `eaton-c39` is the outlet type both targets carry.
- **A 5-15R and a 5-20R are two interfaces.** What each accepts differs: a 5-20P does not
  enter a 5-15R. One interface for both would offer a 20 A plug to a 15 A receptacle.
- **`nema-5-15r` was registered before a part presented it.** A 5-15P names it to be a
  true statement of where the plug goes, and `std/nema-5-15r@1` then needed no change to
  the plug. Its face is borrowed from the 5-20R, because no drawing of a 5-15R is held;
  the contract and the `nema-5-15r` entry of `standards.yaml` say so.
- **The C39 takes a C14 or a C20 plug.** The Eaton Rack PDU G4 installation and setup
  guide, P-164001156 rev 3, section 1.5, says the outlet is a combination of the C13 and
  C19 styles designed to accept both.

### 9.2 `mates` is one interface or a list

A 5-15P seats in two receptacles, and so does each of the C14 and C20 plugs. `mates` on a
component is therefore one interface, as before, or a list of them. A part is offered by a
slot that presents any interface it lists. A contract that states one interface is read
and published exactly as it was.

Rejected: an `also-accepts` on a connector interface, as pluggable families have. That
would say a 5-20R accepts whatever mates a 5-15R, which is true today and is a statement
about receptacles that the plug contract can make more plainly about itself. It would
also not serve the C39, which takes two plugs that share no other receptacle.

One reading serves every tool: `manifest.mates_of(contract)` gives the list. Its readers
are `render.py` (the candidate walk behind every accept list, its on-disk cache, a seated
part's own slot and `mount-points`), `lint.py` (L12, L102, L116 and the family lookup),
`components_catalogue.py` (the `fits` column) and, in the kit, `rack/zero-u.js` (a mount
point's `mates`). `components_index.py` publishes the key as the contract states it, so
`mates` in `components.json` is a string or a list of strings.

### 9.3 Two cord ends

`generic/nema-5-15p-cord@1` and `generic/nema-5-20p-cord@1`, by the rules of section 2:
`class: port`, `mates`, drawn from the cable end, a 30 mm stub sized by `cable-od`, no
`size.d`. Each states `attrs.rating-a`, 15 and 20, so a reader that orders the plugs of a
5-20R by rating puts the 5-15P first.

- **Not `generic/nema-5-20p-plug@1`.** That part is `class: inlet`: the plug at the end of
  a PDU input cord, drawn face on with its contacts, and it exports as the power port of
  the device. It mates nothing and is unchanged. The name `-plug` is its own, so the cord
  ends are `-cord`: a rename of a placed part costs a major on every device that seats it.
- **Sources.** Volex Power Products catalogue, Aug-2025: PS204 (5-15P, drawing on p.147)
  and PS520 (5-20P, p.159), both moulded straight plugs. PS204 is dimensioned throughout.
  PS520 dimensions its two face figures, its blades and its length; its shoulders, lobe
  and taper are scaled at 2.6 px/mm.
- **A plain body.** A moulded cord cap differs by maker. Each part draws one maker's
  outline with no grip pattern and no mark, and says so.
- **Seated depth.** A flat receptacle face has no well. The face of the plug sits on the
  face of the receptacle, and the plug stands its whole length in front of it.
- **The blades are not drawn.** They are in the receptacle, as a C13's contacts are.

### 9.4 The outlets

`std/nema-5-20r@1` and `eaton/c39-outlet@1` gain `interface` and a `mate` point, and
nothing drawn moves. The 5-20R's `mate` is on its earth axis at the line of the blades,
which is 2.6 left of the middle of its face. The C39's is one point for two plugs, 0.04
from the middle of its nose (its contract says why).

All four AC outlet parts now state `media: ac` beside `outlet`. `outlet` is the DCIM type
and says which way power runs. It did not say AC, so a reader could not tell a C13 outlet
from a DC terminal.

What it costs: a minor on each part and on the four Eaton PDUs that place them. Each
outlet of the PDUMH20NET, EVMI2130X and EVMA8365X that was no slot is one now, in the
`cages` of its `configs.json`. No DCIM export changes beyond its version line: an outlet
exports because `PART_OUTLET` lists its part, and a slot adds no row.

### 9.5 Not done here

- DC: the output terminals and input studs of the breaker panels, and the DC terminals
  that supplies draw as art.
- Cord types with two named ends, and the cable types for them.
- The printed name of an outlet beside its path, for a cables export.
- A 5-15R part.

## Decisions taken

- 2026-10-05: the three inlet interfaces are connector slots; the inlets are unchanged.
- 2026-10-05: generic cord ends for C13, C19 and Saf-D-Grid, drawn from the cable end, with a
  30 mm stub sized by `cable-od`.
- 2026-10-05: each plug seats with its nose on the inlet's modelled cavity floor, and
  records that the nose is longer than that cavity.
- 2026-10-05: a cord end's `media` is its connector, not `ac`.
- 2026-10-12: `nema-5-15r`, `nema-5-20r` and `eaton-c39` are connector slots; `mates` is
  one interface or a list; the NEMA cord ends are `-cord` parts beside the face-on plug.

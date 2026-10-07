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
| C13 cord | Belden 19348 technical data sheet, revision 0.388, 09-07-2025, p.1 | SJT 3 x 18 AWG, 0.328 in nominal (8.33 mm, converted) |
| C19 and Saf-D-Grid cord | Belden 19354 technical data sheet, revision 0.525, 09-07-2025, p.1 | SJT 3 x 14 AWG, 0.380 in (9.65 mm) nominal |

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

## Decisions taken

- 2026-10-05: the three inlet interfaces are connector slots; the inlets are unchanged.
- 2026-10-05: generic cord ends for C13, C19 and Saf-D-Grid, drawn from the cable end, with a
  30 mm stub sized by `cable-od`.
- 2026-10-05: each plug seats with its nose on the inlet's modelled cavity floor, and
  records that the nose is longer than that cavity.
- 2026-10-05: a cord end's `media` is its connector, not `ac`.

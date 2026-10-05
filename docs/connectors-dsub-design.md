# Connectors: D-subminiature and VGA

Status: implemented, 2026-10-05. Issue #787. Builds on
[pluggables-caps-design.md](pluggables-caps-design.md) (a presented connector interface is
a SLOT that offers every part whose `mates:` names it) and follows
[connectors-usb-design.md](connectors-usb-design.md) part for part: a registry entry per
interface, a generic plug per interface, and a cable stub whose diameter is a field.

## 1. What existed, and what was missing

The library drew four D-shaped panel connectors and could seat nothing on them.

| part | interface | on a panel it is | where it is placed |
|---|---|---|---|
| `std/db9@1` 20.47 x 11.40 | `db9` | male (pins) | only inside `common/db9-receptacle@1` |
| `std/vga@1` 20.47 x 11.40 | `hd15` | female | 7 device placements, and inside `common/vga-receptacle@1` |
| `std/da15@1` 28.80 x 11.40 | `da15` | female | 1 device placement and 3 on cards |
| `std/db25@1` 42.52 x 11.40 | `db25` | female | 1 on a card |
| `common/db9-receptacle@1` 30.8 x 12.5 | none of its own | | 8 device placements and 26 on cards |
| `common/vga-receptacle@1` 30.8 x 12.5 | none of its own | | 6 device placements and 1 on a card |

None of the four interfaces was in `spec/schemas/connectors.yaml`, so no connector
published a slot. There was no cable plug.

## 2. Decisions

1. **One interface per core:** `db9`, `hd15`, `da15` and `db25`, each citing the
   `standards.yaml` key its core already conforms to.
2. **Gender is part of the interface.** See section 3.
3. **No existing part changes.** Not a core, not a wrapper, and no device: the lock check
   asks for no version bump and no export moves.
4. **Four generic cable plugs:** `generic/db9-plug@1`, `generic/hd15-plug@1`,
   `generic/da15-plug@1` and `generic/db25-plug@1`. Each is `class: port` with `mates:`, no
   `behaviour` and no `size.d`; its length is in its `standards.yaml` entry and its relief.
   Each states `media` with the key its core states (`db9`, `vga`, `da15`, `db25`), its
   `connector` and its `gender`.
5. **Drawn from the cable end.** A front elevation of a seated plug looks at its rear, so
   each skin draws the hood, the two thumbscrews and the cable. The contacts are in the
   panel connector and are not drawn. Nothing is printed on a hood.
6. **Three backshell hoods and one moulded hood.** The DE-9, DA-15 and DB-25 plugs are a
   connector in a two-piece die-cast backshell. The VGA plug is the moulded hood a monitor
   cable has, with a strain relief and two thumbscrew knobs behind it.
7. **A 30 mm stub of cable** from where the plug ends, sized by `cable-od` and coloured by
   `jacket-color`, with the `cable` point on it. The far end of the cable is not a part.
8. **The moulded VGA hood's colour is a field; a metal backshell's is not.**
   `jacket-color` paints the cable on all four plugs. `generic/hd15-plug@1` also has
   `hood-color`, which paints its hood, strain relief and thumbscrew knobs as one
   moulding. Its default is the blue of the VGA port (`#1f4f9e`, as `std/vga@1` draws
   its insert), the PC 99 colour code a VGA cable end commonly matches; black
   (`#26282b`) is the other common finish and is one word on the placement. A colour
   is a field and not a second skin. The three backshells are drawn in the nickel of
   the die-cast hood their dimensions come from.
9. **The kit labels the four media keys** (`DB9`, `VGA`, `DA15`, `DB25`), which is what
   its fallback already read.

## 3. The gender naming rule

A D-sub shell is made in both genders, and which one is on the panel is a property of the
equipment, not of the shell. **An interface key names the panel connector with the gender
the library draws**, and its registry note says so:

| interface | panel connector | the plug that mates it |
|---|---|---|
| `db9` | male, pins | `generic/db9-plug@1`, female |
| `hd15` | female, sockets | `generic/hd15-plug@1`, male |
| `da15` | female, sockets | `generic/da15-plug@1`, male |
| `db25` | female, sockets | `generic/db25-plug@1`, male |

A panel connector of the other gender is a different interface and takes a different key
when the library first draws one; it does not reuse the key with an attribute, because a
slot offers every part that `mates:` its interface and the wrong plug would be offered.
Each plug states its own `gender` in `attrs`, and a test holds it to the opposite of what
its core records.

`db9` and `hd15` are one shell (size E) with different inserts. Their plugs have front
shells of one size and are not interchangeable: neither slot offers the other plug.

## 4. The slots

With the registry entries, every core publishes a `kind: connector` slot on the next
build, by the same core (`render.slot_entry`) as every other slot. Three shapes occur:

- **A connector placed on a chassis** is a slot in the device view's `cages[]`, keyed by
  the placement: 22 of them (8 `db9`, 13 `hd15`, 1 `da15`).
- **A connector on a card that seats in a bay** is a nested slot in the card's own
  `components.json` entry: 31 of them (26 `db9`, 1 `hd15`, 3 `da15`, 1 `db25`).
- **A wrapper that composes one core** presents that core as its own, so the slot is the
  wrapper's placement, on a chassis and on a card alike.

**The two wrappers needed no change.** Unlike the USB bezels, each already names a
connection point `mate`. That point is not what is read: a part that states no
`interface` forwards the presented point of the one interface-bearing part it composes,
through that part's own `at`. Here the two are the same point. The core's mate at
(10.235, 5.7), composed at (5.165, 0.55), lands on (15.4, 6.25), which is the wrapper's
own `mate`. A test measures the seat on the composed core's element in the compiled face,
not only on the wrapper.

Each slot offers exactly one part, its cable plug.

## 5. Sources

| part | source | what it prints |
|---|---|---|
| mating | Tyco Electronics catalogue 82068, AMPLIMITE Subminiature D Connectors (revised 1-08), p.126 | mated flanges 6.73 +/-0.38 apart for shell sizes 1 and 2, 6.50 +/-0.38 for sizes 3 to 5; mounting holes on 24.99, 33.33 and 47.04; rear-mount cutouts 20.47, 28.80 and 42.52 wide |
| front shells | Amphenol M2000 Series D-Sub Connectors catalogue (D-Sub-01 Rev. 10/10), p.22 | pin connector shell 16.79 to 17.04 (9), 25.12 to 25.37 (15), 38.84 to 39.09 (25) by 8.23 to 8.48, 5.82 to 6.05 long; socket connector shell 16.21 to 16.46 (9) by 7.77 to 8.03, 6.05 to 6.30 long |
| DE-9 hood | NorComp 979-009-030R121 Rev 8, sheet 1 | 31 across the ears, 19.9 by 15.6 at the front, 13.22 by 12.52 at the cable end, 46.86 long, lip 1.9, 9.64 to the saddle washer, cable 10.4 maximum |
| DA-15 hood | NorComp 979-015-030R121 Rev 8, sheet 1 | 39.9 across the ears, 27.4 by 15.3, 14 by 13.21, 48.3 long, lip 2.4, 10.4 to the saddle washer, cable 10.5 maximum |
| DB-25 hood | NorComp 979-025-030R121 Rev 7, sheet 1 | 53.5 across the ears, 41.8 wide, 16.2 wide at the cable end, 15.7 thick, 49.5 long, lip 2.5, 10.6 to the saddle washer, cable 11.2 maximum |
| thumbscrew | NorComp 160-000-050R031 Rev 3 | 44.45 long, body diameter 4.01, the body starts 13.21 from the tip |
| second hood | NorComp 977-009-0Y0RYY1 and 977-015-0Y0RYY1 Rev 4 | plastic hoods: 31.2 and 39.6 across, 25.0 and 33.3 between screws |
| VGA hood | Legrand technical data sheet S000091720EN-01 (updated 18/10/2017), p.2 | straight connector 15.5 x 34.0 x 47.5; cable 9.00 +/-0.20 (p.1) |
| VGA hood, second | CableWholesale drawing 10H1-202xx Rev B (10-2006) | a moulded hood with slotted moulded thumbscrews, black; no dimensions |
| VGA and serial cables | Hatteland Technology data sheet, Appliance cables and connectors, revision 19 (18 Sep 2024), pp.2 and 5 | VGA: black moulded hood, black thumbscrews, black jacket, 5.0; serial: beige moulded hood and cable, 5.0 |
| cables | Belden 9539, 9541 and 9543 data sheets (09-07-2025) | 9, 15 and 25 conductors of 24 AWG, foil shield: 6.20, 7.21 and 8.61 nominal |

The NorComp, CableWholesale and Amphenol drawings are vector and were read from 600 dpi
renders. The Tyco page is vector with printed dimensions.

The application specification the four cores cite (TE 114-40010) could not be fetched
again for this work. The Tyco catalogue page prints the same two mating dimensions and
the same cutouts, and is what the plugs cite.

## 6. The seated depth

**Ruling: each plug seats by the mating dimension, measured from the face the core
presents.** The catalogue dimensions two mated connectors by the distance between their
flanges. Each core presents at its own face, the panel plane (its `mate` carries no `on:`
and no `seat-out`), so the published slot `lift` is 0 on a flat panel, and the flange of a
seated plug stands the mating dimension in front of it. The front shell of the plug
reaches back from there by its own length:

| plug | mating dimension | front shell | shell starts at | plug overall | hood or relief ends | stub ends | core models |
|---|---|---|---|---|---|---|---|
| DE-9 | 6.73 | 6.18 | 0.55 | 51.14 | 51.69 | 81.69 | 6.73 |
| VGA | 6.73 | 5.94 | 0.79 | 47.5 | 48.29 | 78.29 | 6.73 |
| DA-15 | 6.73 | 5.94 | 0.79 | 51.84 | 52.63 | 82.63 | 6.73 |
| DB-25 | 6.50 | 5.94 | 0.56 | 52.94 | 53.50 | 83.50 | 6.50 |

**The cores agree on the seat.** This is where D-sub differs from USB, where every
receptacle modelled a cavity the drawing did not give. Each core states its depth as the
mating dimension itself, so the lip of its modelled shell, the end of a wrapper's
standoffs and the flange of a seated plug are one plane, and a thumbscrew reaches the
post it threads into.

**What a core does not agree with is its own shell.** The Amphenol table gives a panel
connector's front shell as 5.82 to 6.30 long, so a core that stands 6.73 (or 6.50) proud
is 0.3 to 0.8 taller than a real one; each core's own provenance already says its depth
is a mating dimension standing in for a reading. Each plug records this in
`provenance.seated-depth`. That is the figure to revisit, and no plug figure moves when
it is. A test pins each modelled depth so the plug's provenance is read again when one
changes.

The front shell is built where it is, inside the height the core's shell occupies. The
two nest in the real connector and overlap in the model, hidden by the hood from the
front and by the core's shell from the side.

## 7. Which way is up

Each core draws the long side of its D at the top, and so does each plug's front shell,
so the turn a seat applies carries the plug round with a turned core: a Dell front panel
places its VGA at 270, the SR-12 seats its SF/CPM in a bay at 90, and fifteen Cisco route
processors turn the DE-9 wrapper itself.

Nothing that keys a plug is visible from the cable end. The D is behind the hood, and the
hood, the two screws and the cable are the same either way up.

## 8. The thumbscrews and the standoffs

Each plug draws its two thumbscrews on the mounting centres of its shell size: 24.99 for
the DE-9 and VGA plugs, 33.32 for the DA-15 and 47.04 for the DB-25.

The two wrappers draw their standoffs 24.99 apart, at 2.905 and 27.895 across a 30.8
part, level with the mate point. That is the standard figure exactly, so a plug seated
through a wrapper has each thumbscrew over a standoff, and a test measures it in the
device frame to 0.01 mm.

A bare core draws no standoffs. A plug seated on one still shows its thumbscrews; that is
accepted, and no part draws standoffs for the DA-15 or DB-25.

## 9. What is estimated

- **Backshell hoods:** every section and length is dimensioned, to +/-0.3. Where the
  taper starts (27 to 28 behind the flange) is scaled on a drawing marked not to scale.
  The taper is built as one step. The ears are drawn the full thickness of the hood,
  which no view dimensions. The two small tabs in front of the flange are not built.
- **Backshell thumbscrews:** the hood drawings show a slotted mating screw; the
  thumbscrew is the alternative the same maker lists for the same hoods. Its diameter
  and length are dimensioned. Where it sits along the plug assumes it is tightened onto
  its saddle washer.
- **VGA hood:** the 34.0 by 15.5 section and the 47.5 length are three figures printed
  in a table on a cable data sheet. That the 47.5 runs from the shell lip to the end of
  the strain relief is an assumption. How it divides between hood (32.5) and strain
  relief (9.06), the strain relief's 14.5 width, and the thumbscrew knobs (7.7 across,
  9.3 long) are scaled on a second, undimensioned drawing whose two internal rulers
  disagree by 5 per cent. The strain relief's 11.0 thickness is estimated.
- **Front shells:** drawn at the middle of each printed range; the corner radius, 2.0,
  is estimated.
- **The stub** is a rule, not a reading.
- **Cable diameters** are one nominal figure each; a placement sets its own. The 9.0 VGA
  default is the cable the hood figures belong to and is at the thick end; another held
  VGA cable is 5.0.
- **Colour:** the held sources do not agree. Serial cables are listed in grey and beige;
  VGA cables in black and grey. Black is the default jacket the library's plugs share.

## 10. Out of scope

- Cisco route processors that draw their own alarm connector instead of composing
  `std/db9@1`.
- DB9-to-RJ45 console adapters, gender changers and null-modem adapters.
- The far end of the cable, and any cable run or bend.
- Right-angle and 45-degree hoods; hoods with slotted screws or spring latches.
- A panel connector of the other gender for any of the four shells.
- Standoffs for the DA-15 and DB-25, and any change to a core's or a wrapper's geometry,
  including the shell heights section 6 questions.
- Devices ship bare. A plug is in a slot's accept list because it mates the slot's
  interface; nothing seats one by default.

## 11. Testing

`spec/tests/test_dsub_plugs.py`, against the real library and builds made by the test:

1. The registry holds the four interfaces, each citing its core's standard and stating
   the panel gender; each core states that gender.
2. Slots: a chassis connector, a card's connector and each wrapper publish theirs; DE-9
   and VGA slots do not offer each other's plug; a census finds no composed core or
   wrapper that is neither a slot nor forwarded, and no part stating a D-sub medium that
   it does not know.
3. Each plug's class, `mates`, media, connector, gender, fields and registry entry; no
   `size.d`; nothing outside its box; no mark on the hood; the long side of its shell up.
4. The solids chain from the front shell to the stub, which is 30 long, and the
   thumbscrews start at the rear of the section that holds them.
5. Seating on real connectors, bare and wrapped, on a chassis and on a card, two of them
   turned: the plug's mate lands on the connector's and the plug turns with it.
6. The seated depth: the compiled plug has its flange the mating dimension in front of
   the core face, each core models that dimension, and each wrapper's standoffs end there.
7. Thumbscrew centres land on the wrapper's standoff centres.
8. 3D: every solid is right side out and the chain has no gap.
9. The stub's diameter is `cable-od`, by default and from a placement.

## Decisions taken

- 2026-10-05: the four D-sub interfaces are connector slots, each key naming the gender
  on the panel; no core, wrapper or device changes.
- 2026-10-05: generic hooded cable plugs for DE-9, VGA, DA-15 and DB-25, drawn from the
  cable end with two thumbscrews and a 30 mm stub sized by `cable-od`.
- 2026-10-05: each plug seats with its flange the mating dimension in front of the core
  face, which is also the depth each core models.

# Connectors: USB

Status: implemented, 2026-10-05. Issue #786. Builds on
[pluggables-caps-design.md](pluggables-caps-design.md) (a presented connector interface is
a SLOT that offers every part whose `mates:` names it) and follows
[connectors-power-design.md](connectors-power-design.md) part for part: a registry entry per
interface, a generic plug per interface, and a cable stub whose diameter is a field.

## 1. What existed, and what was missing

The library drew USB receptacles and could seat nothing in them.

| part | interface | where it is placed |
|---|---|---|
| `std/usb-a@1` | `usb-a` | 137 device placements, 30 on cards, and one inside each of two bezels |
| `std/micro-usb@1` | none | 40 device placements and 18 on cards |
| `std/usb-c@1` | `usb-c` | 9 device placements and 2 on one card |
| `common/usb-a@2`, `common/usb-a-bezel@1` | none of their own | 3 and 5 device placements |

None of the three interfaces was in `spec/schemas/connectors.yaml`, so no receptacle
published a slot. The Micro-USB jack stated no interface and no connection point at all.
There was no cable plug.

## 2. Decisions

1. **One interface per receptacle:** `usb-a`, `micro-usb-b` and `usb-c`, each citing the
   `standards.yaml` key its receptacle already conforms to. An interface is the connector,
   not the bus: none states a speed or a USB generation, and neither does a plug.
2. **The Micro-USB jack gains `interface: micro-usb-b` and a `mate` point** at the centre
   of its opening. Its drawing, its size and its depth are unchanged. That is a contract
   change, so `std/micro-usb@1` takes a patch and so does each of the 39 devices that
   draw it.
3. **Three generic cable plugs:** `generic/usb-a-plug@1`, `generic/micro-usb-b-plug@1` and
   `generic/usb-c-plug@1`. Each is `class: port` with `mates:`, no `behaviour` and no
   `size.d`; its length is in its `standards.yaml` entry and its relief.
4. **Drawn from the cable end.** A front elevation of a seated plug looks at its rear, so
   each skin draws the overmould, the strain relief and the cable. The contacts are in the
   receptacle and are not drawn. Neither is the USB icon: it is a logo mark, and it is on
   a face this view does not see.
5. **Drawn at the maximum overmould.** Each USB specification dimensions the largest
   overmould a compliant plug may have, and that is the section drawn: the envelope a
   neighbouring port has to clear. A real plug is a little smaller.
6. **A 30 mm stub of cable** from the end of the strain relief, sized by `cable-od` and
   coloured by `jacket-color`, with the `cable` point on it. The far end of the cable is
   not a part.
7. **USB-A offers the cable plug only.** A storage stick and a console dongle are
   different bodies; neither is modelled.
8. **A plug's `media` is the key its receptacle states** (`usb-a`, `micro-usb-b`,
   `usb-c`). The kit already labelled all three, and lint L62 raised nothing.

## 3. The slots

With the registry entries, every receptacle publishes a `kind: connector` slot on the next
build, by the same core (`render.slot_entry`) as every other slot. Three shapes occur:

- **A receptacle placed on a chassis** is a slot in the device view's `cages[]`, keyed by
  the placement.
- **A receptacle on a card that seats in a bay** is a nested slot in the card's own
  `components.json` entry, keyed `<bay>/<part>` (`re0/usb`).
- **A bezel that composes one receptacle** (`common/usb-a@2`, `common/usb-a-bezel@1`)
  presents that receptacle as its own, so the slot is the bezel's placement. Neither bezel
  needed changing: each already had a `usb` connection point exactly where the forwarded
  mate lands, and neither takes a version bump.

52 component `parts:` entries are USB receptacles: 32 `usb-a`, 18 `micro-usb-b` and 2
`usb-c`. Forty-nine publish a slot on the card that composes them and two are the bezels'
forwarded apertures. Each slot offers exactly one part, its cable plug.

**One receptacle is not published, and it is a known gap.** `commscope/cc3008@1` seats in
a bay of the CA3008 carrier, which is itself a card, and composes one interface-bearing
part: its Micro-USB jack. A card writes its `bays:` as a mapping where a device view writes
a list, and `components_index.seated_in_bays` reads only the list, so the CC3008 is taken
for a placed wrapper that forwards its one aperture, and `components.json` lists no slot
for it. The build is not affected: a configuration seats a plug there by its deep key
(`slot-3-4/cc/usb`) and a test does. Reading the mapping as well would publish the jack,
and with it the one LC duplex adapter on each of four Smartoptics dispersion compensation
modules that are hidden the same way; that changes what the kit offers on a family this
work does not touch, so it is left for its own change.

## 4. Sources

| part | source | what it prints |
|---|---|---|
| USB-A plug | Universal Serial Bus Specification Revision 2.0 (April 27, 2000), figure 6-9, p.99 | shell 12.00 x 4.50, 11.75 MIN long; overmould 16.0 MAX x 8.0 MAX |
| | the same, figure 6-2, p.87 (typical, for reference) | overmould 15.7 x 7.5 and 27.0 long; optional moulded strain relief 9.0 |
| | the same, figure 6-7, p.95 | receptacle 8.88 +/-0.20 from its face to the plug stop; 2.67 MIN from the face to the overmould |
| Micro-B plug | Micro-USB Cables and Connectors Specification Revision 1.01 (April 4, 2007), figure 4-5, p.18 | overmould 10.6 MAX x 8.5 MAX, two corners chamfered; nothing else |
| | the same, figures 4-7 and 4-8, pp.20-21 | shell 6.85 x 1.8, 5.4 MIN long; latch hook 1.05 MIN to 2.8 MAX behind the front |
| | the same, figure 4-10, p.23 | receptacle 3.5 +/-0.1 from its mouth to the wall the plug meets |
| USB-C plug | USB Type-C Cable and Connector Specification Release 2.5 (March 2026), figure 3-3, pp.53-54 | shell 8.25 x 2.40, 6.65 +/-0.10 long; overmould 12.85 MAX x 7.0 MAX; overmould length (35), a reference |
| | the same, note 7 to figure 3-1, p.47, and figure 3-82, p.147 | receptacle shell 6.20 +/-0.20; 0.05 MIN between overmould and product |
| USB-A and Micro-B cable | USB 2.0 table 6-5, p.105 | nominal 4.06 mm for the 28/28 cable, up to 5.21 for 28/20 |
| USB-C cable | Same Sky CBL-UC-UC-1 data sheet, 09/12/2024, p.2 | 5.2 +/-0.15; USB Type-C section 3.3.3 (p.80) gives 4 to 6 mm as typical |
| second drawing | Same Sky CBL-UA-MUB-1 data sheet, 09/12/2024, p.2 | A overmould 15.8 x 7.8, strain relief 9.85; Micro-B overmould 11 x 6.9; cable 3.5; black |

The USB 2.0 figures are vector and were read from a 600 dpi render. The Micro-USB and
Type-C figures are rasters embedded at 120 to 220 ppi and were read at that resolution.

Black is the default jacket: the one held source that states a colour states black.

## 5. The seated depth

**Ruling: each plug seats to the depth the USB drawing gives for its shell, measured from
the face the receptacle presents.** Each receptacle presents at its own face (its `mate`
carries no `on:` and no `seat-out`), so the published slot `lift` is 0 on a flat panel and
the plug's own relief starts there. The plug leaves its shell length less the drawn
insertion in front of that face:

| plug | shell | drawn insertion | shell left in front | overall | stands off | stub ends | receptacle models | mismatch |
|---|---|---|---|---|---|---|---|---|
| USB-A | 11.75 MIN | 8.88 | 2.87 | 47.75 | 38.87 | 68.87 | 13.7 (estimated) | 4.82 too deep |
| Micro-B | 5.4 MIN | 3.5 | 1.9 | 32.5 | 29.0 | 59.0 | 5.9 | 2.4 too deep |
| USB-C | 6.65 | 6.20 | 0.45 | 50.85 | 44.65 | 74.65 | 6.5 (estimated) | 0.30 too deep |

**All three receptacles model a cavity deeper than the drawing gives.** This is where USB
differs from the AC cord ends, which seat on the modelled cavity floor. A USB-A or Micro-B
plug cannot: the modelled depth is longer than the whole plug shell, so a plug seated on
that floor would have its overmould behind the panel. The plugs therefore take nothing
from the modelled depth. Each records the mismatch in `provenance.seated-depth`, and the
receptacle depth is the figure to revisit; when it is, no plug figure moves. A test pins
each modelled depth so the plug's provenance is read again when one changes.

The part of the shell inside the receptacle is not built. In 3D the plug's solids start at
the panel plane and the receptacle's own cavity is behind them.

## 6. Which way is up

- **USB-A:** `std/usb-a@1` draws its tongue in the upper half of the opening, so the plug
  has its insulator down and its icon side up. Nothing that keys the plug is visible from
  the cable end, so the part as drawn is the same either way up.
- **Micro-B:** latch side up, the way the specification draws the receptacle, with the
  board below. `std/micro-usb@1` draws a symmetric opening and states no up of its own.
  The overmould's two chamfers are on the latch side, so they are drawn at the top. A
  device whose jack is mounted the other way up turns the jack, and the plug follows.
- **USB-C:** symmetric.

A seat applies the receptacle's turn to the plug, on a chassis, through a bezel and on a
card alike.

## 7. What is estimated

- **Every overmould section is a maximum, not a measurement.** One held vendor drawing has
  a Micro-B overmould 0.4 wider than the 10.6 maximum.
- **USB-A:** where the overmould's taper starts (21 of the 27) and the strain relief's 6.9
  section are scaled; the taper is built as one step; the corner radius is estimated.
- **Micro-B:** the overmould's length (18.5), the strain relief (8.6 long, built round at
  6.5) and the chamfer (1.75) are scaled from a 150 ppi raster, good to about 0.15. The
  one vendor drawing gives 26 for overmould and strain relief together, against 27.1.
- **USB-C:** the overmould length is the specification's (35), a reference dimension; the
  same figure is drawn about half that long, and one vendor drawing gives 31 for overmould
  and strain relief together. The strain relief (9.2 long, 6.1 across) is scaled.
- **The stub** is a rule, not a reading.
- **Cable diameters** are one nominal figure each from a range; a placement sets its own.

## 8. Out of scope

- Mini-USB, USB Standard-B, Micro-A and Micro-AB, and the wider USB 3.x Micro-B.
- Storage sticks, console dongles and adapters.
- The far end of the cable, and any cable run or bend.
- Right-angle plugs.
- Any change to a receptacle's geometry, including the three depths section 5 questions.
- Devices ship bare. A plug is in a slot's accept list because it mates the slot's
  interface; nothing seats one by default.

## 9. Testing

`spec/tests/test_usb_plugs.py`, against the real library and builds made by the test:

1. The registry holds the three interfaces, each citing its receptacle's standard.
2. Slots: a chassis receptacle, a card's receptacle and each bezel publish theirs; a
   census finds no composed receptacle that is neither a slot nor forwarded, names the one
   forwarded by a card in a card (section 3), and finds no part stating a USB medium that
   it does not know.
3. Each plug's class, `mates`, media, fields and registry entry; no `size.d`; no mark on
   the overmould.
4. The solids chain from the receptacle face to the stub, which is 30 long.
5. Seating in real receptacles at 0, 90, 180 and 270: the plug's mate lands on the
   receptacle's and the plug turns with it.
6. The seated depth: the compiled plug leaves its shell less the drawn insertion in front
   of the receptacle face, and the published slot lift is where it starts.
7. 3D: every solid is right side out and the chain has no gap.
8. The stub's diameter is `cable-od`, by default and from a placement.

## Decisions taken

- 2026-10-05: the three USB interfaces are connector slots; the Micro-USB jack gains its
  interface and mate point and nothing else.
- 2026-10-05: generic cable plugs for USB-A, Micro-B and USB-C, drawn from the cable end at
  the maximum overmould, with a 30 mm stub sized by `cable-od`.
- 2026-10-05: each plug seats to the drawn insertion from the receptacle's presented face,
  and records that the receptacle models a deeper cavity.
- 2026-10-05: USB-A offers the cable plug only.

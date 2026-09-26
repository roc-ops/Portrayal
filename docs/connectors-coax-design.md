# Connectors: coax

Status: draft, 2026-09-26. Issue #650. Builds on
[pluggables-caps-design.md](pluggables-caps-design.md) (B3: a presented connector interface
is a SLOT that offers every part whose `mates:` names it) and on
[pluggables-cables-design.md](pluggables-cables-design.md) (a cable stub whose diameter is a
field, and a `cable` point on a `cyl`).

## 1. What exists, and what is missing

The library draws coax jacks and cannot seat anything in them.

| part | interface | placements |
|---|---|---|
| `std/f-type@1` | `f-type` | 70 |
| `std/mcx@1` | `mcx` | 104 |
| `std/sma@1` | `sma` | 46 |
| `std/smb@1` | `smb` | 123 |
| `common/sma-jack@1`, `common/smb-jack@1` | through their core | |

Each `std` jack has a `mate` point and an interface. What is missing:

- **Slots.** None of the four interfaces is in `spec/schemas/connectors.yaml`, so no coax
  port publishes a slot.
- **Plugs.** There are no coax plugs.
- **Jacks.** There is no BNC jack and no 1.0/2.3 jack. The Juniper DS3/E3 MIC draws its
  jacks with the SMB opening "because no BNC standard exists in the registry yet", and the
  Cisco T3/E3 SPAs draw their 1.0/2.3 jacks as skin art, not as ports.

## 2. Decisions

1. **One interface per connector family:** `f-type`, `bnc`, `sma`, `smb`, `mcx` and
   `din-1.0-2.3`. A slot answers "does it physically mate", as it does for LC, SC and RJ45
   (decided 2026-09-26).
2. **Impedance is an attr, never part of the interface.** 50 and 75 ohm BNC intermate
   mechanically, and so do the 50 and 75 ohm variants of 1.0/2.3, MCX and SMB. A part or a
   placement that knows says `attrs.impedance: 50` or `75`. The generic jacks and plugs state
   none, as a generic states no `rate`. F-type is 75 ohm by definition, and its parts say so.
   A mismatch check (a 75 ohm plug in a 50 ohm jack) is a later lint warning, not this work
   (decided 2026-09-26).
3. **Reverse-polarity SMA is out** until a device needs it. It is a distinct interface when
   it comes (RP-SMA does not mate SMA).
4. **Plugs draw a cable stub.** Each plug is a coupling part, a strain relief and a 30 mm
   stub of cable whose diameter is the `cable-od` field, reusing the cable-end machinery
   (decided 2026-09-26).
5. **Generics only.** No vendor coax plug is built here, as no vendor fibre plug was built
   with the fibre plugs.
6. **Two new jacks, and the devices that used a stand-in move to them where a source names
   the connector on the faceplate** (decided 2026-09-26).

## 3. The registry

`spec/schemas/connectors.yaml` gains six interfaces. Each cites its standard, and the
`standards.yaml` key its figures live under:

| interface | standard | `standards.yaml` key |
|---|---|---|
| `f-type` | IEC 61169-24 / ANSI/SCTE 02 | `f-type` (exists) |
| `bnc` | IEC 61169-8 | `bnc` (new) |
| `sma` | IEC 61169-15 | `sma` (exists) |
| `smb` | IEC 61169-10 | `smb` (exists) |
| `mcx` | IEC 61169-36 | `mcx` (exists) |
| `din-1.0-2.3` | IEC 61169-29 | `din-1.0-2.3` (new) |

With the entries, every existing coax port publishes a `kind: connector` slot on the next
build: a device view's `cages[]` and a card's own `cages` in `components.json`, by the same
core (`render.slot_entry`) as every other slot. The kit needs no change to offer them.

## 4. The jacks

- **`std/bnc@1`**: a bulkhead panel jack. Face on: the bayonet collar with its two lugs and
  the insulator ring around the centre contact; the mounting nut is behind the panel. The
  panel hole and collar come from IEC 61169-8 where the figure is held, otherwise from a
  vendor panel-jack drawing, and each figure is labelled to its source.
- **`std/din-1.0-2.3@1`**: the small push-pull jack, a plain barrel and insulator, sourced
  the same way from IEC 61169-29 or a vendor drawing.
- **The existing jacks are unchanged.** Each already presents its interface and a `mate`
  point, which is all a slot needs. `common/sma-jack@1` and `common/smb-jack@1` present the
  interface through their core, as the RJ45 wrappers do. MCX keeps its recorded caveat: at
  least one vendor (Casa) uses a variant recessed into the faceplate, so the seated plug's
  depth follows the placement's presented lift, not the `std/mcx` barrel.

## 5. The plugs

Six generics, one per interface: `generic/f-type-plug@1`, `generic/bnc-plug@1`,
`generic/sma-plug@1`, `generic/smb-plug@1`, `generic/mcx-plug@1` and
`generic/din-1.0-2.3-plug@1`. Each declares `mates:` its interface and follows the class,
behaviour and seating idiom of `generic/lc-plug@2` and `generic/rj45-plug@1`.

Each is drawn end on from the face, nearest the viewer last:

1. **The coupling part:** a hex nut (SMA, F), a knurled bayonet sleeve with its slots (BNC),
   a plain snap-on sleeve (SMB, MCX), or a push-pull sleeve (1.0/2.3). It overlaps the jack's
   barrel by the mated engagement length the standard gives, so in 3D the nut sits over the
   barrel, not in front of it.
2. **The crimp ferrule and strain relief:** a `cyl` behind the coupling part.
3. **The cable stub:** a `cyl` 30 mm long from the end of the strain relief. Its end-on
   circle carries `data-r-from="cable-od"`, and the `cable` connection point sits `on` it, so
   a downstream tool continues the run from its far end.

Fields on every plug: `cable-od` and `jacket-color`. There is no strap and no `latch-color`.
Each `cable-od` default is the typical cable for its connector, from a cable maker's data
sheet:

| plug | default cable | OD (mm) |
|---|---|---|
| F | RG-6 | 6.9 |
| BNC | RG-58 | 4.95 |
| SMA, SMB, MCX | RG-316 | 2.5 |
| 1.0/2.3 | RG-179 | about 2.5 |

A placement or a later vendor wrapper overrides it: RG-59 on a 75 ohm BNC, RG-6 on a headend
F run. Every figure is within L122's 2-15 mm range.

Out of scope: right-angle plugs, cable assemblies, caps and RP-SMA.

## 6. Moving the stand-ins

A sweep lists every device and card that notes a stand-in or an unsettled coax jack. A part
moves to `std/bnc@1` or `std/din-1.0-2.3@1` only when a held document names the connector ON
THE FACEPLATE. An accessory cable's connector or a far end does not count.

- **Juniper MIC-3D-8DS3-E3 and -V:** 16 jacks drawn with the SMB opening. They move if the
  hardware guide names the jack.
- **Cisco SPA-2XT3/E3 and SPA-4XT3/E3:** their 1.0/2.3 jacks become `std/din-1.0-2.3@1`
  placements instead of skin art, and so become slots.
- **Stay as they are:** the MX80 CLK/SYNC jacks and the Nokia CPM5 1PPS jack, whose sources
  conflict (their gaps stay open), and the UfiSpace S9321, whose jack is SMB (BNC is on the
  accessory cable's far end).

Each moved part, and each device that seats it, takes the version bump devicelock asks for.

## 7. What does not change

- Devices ship bare. A plug is in a slot's accept list because it mates the slot's
  interface; nothing seats it by default.
- No cable run, no routing and no bend geometry. The stub is straight and stops at the
  `cable` point.

## 8. Testing and gates

1. The registry holds the six interfaces, each citing its standard.
2. Slots: a known port of each family publishes a `kind: connector` slot that accepts its
   plug. Examples are the MX304 SMB clock port, a CommScope F-type port, and a moved BNC and
   1.0/2.3 port.
3. Seating: each plug seats at its jack's `mate` point in a built device.
4. 3D: each plug's solids build right side out, and the stub's cylinder diameter equals
   `cable-od`.
5. Fields: the `data-r-from` binding sizes each plug's stub, and a placement's `cable-od`
   overrides the default.
6. Census and exemption tables: the new parts join them; nothing is waived.
7. A review page before the final rebuild: each new jack and plug beside its source drawing,
   in 2D and 3D, plus one timing face with SMB, SMA and BNC plugs seated and one T3/E3 card
   with 1.0/2.3. Sign-off, then gates.
8. Gates: lock (checked before any update), lint (no change against the baseline except new
   passes), build, publish, catalogue, the full suite, kit tests, and CI time against main's
   last green run.

This work also corrects [pluggables-heads-design.md](pluggables-heads-design.md), whose
section 5 says RJ45 connector slots are not in the explorer's swap menu. They are (#610,
#611, #570; #648 closed).

## Decisions taken

- 2026-09-26: plugs and slots for the four existing jacks, plus BNC and 1.0/2.3 jacks and
  the stand-in moves (decision 6).
- 2026-09-26: plugs draw a cable stub sized by `cable-od` (decision 4).
- 2026-09-26: one interface per family, with impedance as an attr (decisions 1-2).

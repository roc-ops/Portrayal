# Connectors: coax

Status: implemented, 2026-09-26. Issue #650. Builds on
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
   `din-1-0-2-3`. A slot answers "does it physically mate", as it does for LC, SC and RJ45
   (decided 2026-09-26). The interface is spelled with hyphens throughout, never a dot:
   `component.schema.json`'s interface/mates `segment` pattern refuses one (decided
   2026-09-26).
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
| `din-1-0-2-3` | DIN 41626/2 | `din-1-0-2-3` (new) |

The 1.0/2.3 standard is cited as DIN 41626/2, the standard the held HUBER+SUHNER catalogue
names; IEC 61169-29 covers the connector internationally but is not held.

With the entries, every existing coax port publishes a `kind: connector` slot on the next
build: a device view's `cages[]` and a card's own `cages` in `components.json`, by the same
core (`render.slot_entry`) as every other slot. The kit needs no change to offer them.

## 4. The jacks

Each new jack, like the existing SMA and SMB jacks, is a `std/` core inside a `common/`
bezel: the core draws the connector's own art (collar, bore, insulator, contact) inside the
panel-hole box, and the bezel composes it and adds the flange or nut that sits in front of
the panel. A device or card places the bezel, never the bare core, and a guard test refuses
any device or card that places a `std/bnc@1` or `std/din-1-0-2-3@1` core directly.

- **`std/bnc@1`** (core) + **`common/bnc-jack@1`** (bezel): the bayonet collar, bore and
  the insulator ring around the centre contact, inside the panel hole; the bezel draws the
  flange (12.7) that sits in front of the panel and the collar's two bayonet lugs. The panel hole and collar come from IEC
  61169-8 where the figure is held, otherwise from a vendor panel-jack drawing, and each
  figure is labelled to its source. `common/bnc-jack@1` ships `unplaced:` — no held source
  puts a BNC jack on a modelled faceplate yet (section 6).
- **`std/din-1-0-2-3@1`** (core) + **`common/din-1-0-2-3-jack@1`** (bezel): the small
  push-pull jack, a plain barrel and insulator, sourced the same way from DIN 41626/2 or a
  vendor drawing; the bezel's nut (7.01) sits in front of the panel.
- **The existing jacks are unchanged in art.** Each already presents its interface and a
  `mate` point, which is all a slot needs. `common/sma-jack@1` and `common/smb-jack@1`
  present the interface through their core, as the RJ45 wrappers do. `std/mcx@1` presents
  at its barrel front (2.0), where a seated plug stops. At least one vendor (Casa) uses a
  variant recessed into the faceplate; that variant is recorded in the part's provenance but
  not modelled.

## 5. The plugs

Six generics, one per interface: `generic/f-type-plug@1`, `generic/bnc-plug@1`,
`generic/sma-plug@1`, `generic/smb-plug@1`, `generic/mcx-plug@1` and
`generic/din-1-0-2-3-plug@1`. Each declares `mates:` its interface and follows the class,
behaviour and seating idiom of `generic/lc-plug@2` and `generic/rj45-plug@1`.

Each is drawn end on from the face, nearest the viewer last:

1. **The coupling part:** a hex nut (SMA, F), a knurled bayonet sleeve (BNC; its slots are hidden from the face),
   a plain snap-on sleeve (SMB, MCX), or a push-pull sleeve (1.0/2.3). It overlaps the jack's
   collar, barrel or thread by the mated engagement length the standard gives, so in 3D the
   coupling part sits over that feature, not in front of it — except MCX, where the plug's
   slotted outer contact engages INSIDE the jack (its body stops at the jack face), so "the
   nut sits over the barrel" does not apply to MCX.
2. **The crimp ferrule and strain relief:** a `cyl` behind the coupling part.
3. **The cable stub:** a `cyl` 30 mm long from the end of the strain relief. Its end-on
   circle carries `data-r-from="cable-od"`, and the `cable` connection point sits `on` it, so
   a downstream tool continues the run from its far end.

Fields on every plug: `cable-od` and `jacket-color`. There is no strap and no `latch-color`.
Each `cable-od` default is the typical cable for its connector, from the cable maker's
(Belden) data sheets:

| plug | default cable | Belden part | OD (mm) |
|---|---|---|---|
| F | RG-6 | 1694A | 6.96 |
| BNC | RG-58 | 8240 | 4.90 |
| SMA, SMB, MCX | RG-316 | 83284 | 2.49 |
| 1.0/2.3 | RG-179 | 179DT | 2.54 |

A placement or a later vendor wrapper overrides it: RG-59 on a 75 ohm BNC, RG-6 on a headend
F run. Every figure is within L122's 2-15 mm range.

### Seating

Each jack presents its interface at the plane a mated plug's coupling front sits on — the
standard's reference plane less the plug's overlap past it — not at its own front face:

| jack | presents at (mm) | how |
|---|---|---|
| SMA | 0 | the jack's own face (no key) |
| SMB | 0 | the jack's own face (no key) |
| MCX | 2.0 | `on: barrel` — the barrel front, since the plug engages inside the jack |
| BNC | 3.7 | `seat-out: 3.7` |
| 1.0/2.3 | 3.85 | `seat-out: 3.85` |
| F | 7.8 | `seat-out: 7.8` |

The last three use the new `seat-out` connection-point key: a number of mm a seated part
stands off, absolute from the part's own face, where no drawn feature's rear sits at that
plane already. It is read only on the presented point (`manifest._seat_out`) and is
mutually exclusive with `on:`; lint L106 refuses a point that carries both, a value that is
not a number at or above 0, or a `seat-out` on any point other than the presented one. A bezel forwards its core's seat out: composing a core no longer drops
the core's own presented depth, so `common/bnc-jack@1` and `common/din-1-0-2-3-jack@1`
present at their core's plane, not at the bezel's own placement lift alone.

Out of scope: right-angle plugs, cable assemblies, caps and RP-SMA.

## 6. Moving the stand-ins

A sweep lists every device and card that notes a stand-in or an unsettled coax jack. A part
moves to `common/bnc-jack@1` or `common/din-1-0-2-3-jack@1` only when a held document names
the connector ON THE FACEPLATE. An accessory cable's connector or a far end does not count.

- **Moved, to `common/din-1-0-2-3-jack@1`:** the four Cisco T3/E3 SPAs —
  `spa-2xt3e3`, `spa-4xt3e3`, `spa-2cht3-ce-atm` and `spa-4xct3-ds0`. Each guide names its
  jacks 75-ohm coaxial Siemax (the 1.0/2.3 family) with "1.0/2.3 RF to BNC" cables, so a
  table naming BNC describes the cable's far end, not the faceplate. Their 1.0/2.3 jacks
  become real placements instead of skin art, and so become slots.
- **Stays on SMB:** the Juniper MIC-3D-8DS3-E3 (and -V). The MX2000 and MX104 datasheets
  name its jack 75-ohm mini-SMB, not BNC, so it keeps its `common/smb-jack@1` placements; the
  part's description is corrected to give that reason (mini-SMB) in place of the old "no BNC
  standard exists in the registry yet". BNC appears only at the far end of the
  CBL-DS3-E3-M-S accessory cable, which does not count. Mini-SMB as an interface is a
  follow-up (section 7).
- **Stay as they are:** the MX80 CLK/SYNC jacks and the Nokia CPM5 1PPS jack, whose sources
  conflict (their gaps stay open), and the UfiSpace S9321, whose jack is SMB (BNC is on the
  accessory cable's far end).
- **`common/bnc-jack@1` ships unplaced.** No held source puts a BNC jack on a modelled
  faceplate; the ReadyLinks GL-12xB/24xB BNC switches (staged, not yet modelled) are its
  first natural user.

Each moved part, and each device that seats it, takes the version bump devicelock asks for.

## 7. What does not change

- Devices ship bare. A plug is in a slot's accept list because it mates the slot's
  interface; nothing seats it by default.
- No cable run, no routing and no bend geometry. The stub is straight and stops at the
  `cable` point.

## 8. Testing and gates

1. The registry holds the six interfaces, each citing its standard.
2. Slots: a known port of each family publishes a `kind: connector` slot that accepts its
   plug. Examples are the MX304 SMB clock port, a card F-type port (Casa), and a moved 1.0/2.3
   port on a Cisco T3/E3 SPA.
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
section 5 said RJ45 connector slots are not in the explorer's swap menu. They are (#610,
#611, #570; #648 closed).

## Follow-ups

- **Mini-SMB as an interface.** The Juniper DS3/E3 MIC's jack is 75-ohm mini-SMB, not SMB;
  today it is still placed as `common/smb-jack@1` (section 6). A mini-SMB interface, and the
  MIC's move to it, is later work.
- **The DCIM export counts tx and rx as two interfaces per port.** This follows the existing
  library convention (the same MIC already does it); it is not fixed by this work and is
  carried as a follow-up issue.

## Decisions taken

- 2026-09-26: plugs and slots for the four existing jacks, plus BNC and 1.0/2.3 jacks and
  the stand-in moves (decision 6).
- 2026-09-26: plugs draw a cable stub sized by `cable-od` (decision 4).
- 2026-09-26: one interface per family, with impedance as an attr (decisions 1-2).
- 2026-09-26: the interface is spelled `din-1-0-2-3`, not `din-1.0-2.3` — the schema's
  interface/mates pattern refuses a dot.
- 2026-09-26: the Juniper DS3/E3 MIC does not move; its jack is 75-ohm mini-SMB per the
  MX2000/MX104 datasheets, not "no BNC standard exists in the registry yet" as the part
  formerly said, and BNC on its accessory cable's far end does not count.
- 2026-09-26: the Cisco SPA-2XT3/E3 and SPA-4XT3/E3 jacks move to `common/din-1-0-2-3-jack@1`,
  and so do SPA-2CHT3-CE-ATM and SPA-4XCT3-DS0 (their guides also name DIN 1.0/2.3 / Siemax on
  the faceplate; the original sweep missed them).
- 2026-09-26: each new jack (BNC, 1.0/2.3) and F present at the mated plane by a new `seat-out`
  connection-point key; a bezel forwards its core's seat out. MCX presents at its barrel (2.0)
  because the plug engages inside the jack, so "the nut sits over the barrel" does not
  describe MCX.
- 2026-09-26: plug `cable-od` defaults take the Belden data-sheet figures (RG-6 6.96, RG-58
  4.90, RG-316 2.49, RG-179 2.54) in place of the spec's earlier nominal figures.
- 2026-09-26: each new jack is a `std/` core inside a `common/` bezel, following the existing
  SMA/SMB pattern; devices place the bezel, and a test refuses a bare core.
- 2026-09-26: the 1.0/2.3 standard is cited as DIN 41626/2, the standard the held
  HUBER+SUHNER catalogue names; IEC 61169-29 is not held.

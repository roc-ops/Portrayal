# Connectors: pluggable terminal headers and the DC barrel jack

Status: implemented, 2026-10-06. Issue #789, all three parts. Builds on
[pluggables-caps-design.md](pluggables-caps-design.md) (a presented connector interface is
a SLOT that offers every part whose `mates:` names it) and follows
[connectors-usb-design.md](connectors-usb-design.md): a registry entry per interface and a
generic plug per interface. It differs in one thing. A terminal plug carries one wire per
pole, not one cable. The DC barrel jack, section 9, follows the USB pattern exactly.

## 1. What existed, and what was missing

The library drew three pluggable terminal headers on a 5.08 mm pitch and could seat
nothing in them.

| part | class | where it is placed |
|---|---|---|
| `common/terminal-header-508-5f@1` | inlet | the power input of 10 AurCore AIS switches |
| `common/terminal-header-508-2@2` | port | the relay output of the same 10 |
| `common/dc-terminal-header-6@1` | inlet | two on the rear of the ReadyLinks GL-12xB-240D |

None stated an interface or a connection point, and there was no plug.

## 2. Decisions

1. **One interface per header form, named for the connector and not the use:**
   `terminal-508-2`, `terminal-508-5` and `terminal-508-6`. The pitch and the number of
   positions are in the key. A header that feeds power and one that carries a relay
   contact are the same interface when they are the same header.
2. **A flange is not part of the interface.** `terminal-508-5` is the five-position
   mating face, which a flanged or a plain header presents and a flanged or a plain plug
   mates. The header part keeps its name, `common/terminal-header-508-5f@1`. The plug is
   the screw-flange form, because the one five-position header placed is flanged and its
   data sheet lists flanged plugs as its mates; the plug says so in its description and
   provenance, because the interface does not. A plain five-position plug is a different
   part that mates the same interface and is not drawn yet.
3. **Each header gains its interface and a `mate` point** at the middle of its row of
   contacts. Drawings, sizes, classes and attrs are unchanged. Each is a contract change:
   the three headers take a patch and so does each of the 11 devices that draw one.
4. **Three generic plugs:** `generic/terminal-508-2-plug@1`,
   `generic/terminal-508-5-plug@1` and `generic/terminal-508-6-plug@1`. Each is
   `class: port` with `mates:`, no `behaviour` and no `size.d`.
5. **In-line wire entry.** The plugs are the screw-clamp form whose wires enter parallel
   to the plugging direction, the form each header's data sheet lists as its mate. Plugs
   with the wires entering across the plugging direction are other bodies.
6. **Drawn from the wire side.** A front elevation of a seated plug looks at the side the
   wires enter: the body, a wire entry at each pole and, on the flanged plug, the two
   flange screws. The clamp screws are on the top face, which this view sees edge on, and
   are not drawn.
7. **One stub of wire per pole.** Each pole carries a 30 mm stub of insulated wire from
   the wire-side face of the body, and a connection point named `wire-1` to `wire-N` on
   it. There is no `cable` point.
8. **Three fields.** `wire-od` sizes every stub and `wire-color` paints every stub;
   `body-color` paints the body and the flanges. The default wire is 3.0 mm, a 1.5 mm2
   conductor; 4.0, for 2.5 mm2, is the largest the plug takes. The default body is the
   green the AurCore headers are drawn in.
9. **A plug's `media` is `terminal-block`** on all three. The two-position header states
   that key. The other two headers state `dc-terminal`, which a `class: port` plug cannot:
   lint L62 reads a port part's media as a connector word, and `dc` as a connector word
   flags every `dc-in` placement id in the library. The kit labels both keys.

## 3. The slots

Every header is placed directly on a chassis face, so each is a slot in the device view's
`cages[]`, keyed by the placement: 10 `terminal-508-5`, 10 `terminal-508-2` and 2
`terminal-508-6`. No component composes a header. Each slot offers exactly one part.

## 4. Sources

| part | source | what it prints |
|---|---|---|
| plain plug, 2 and 6 positions | Phoenix Contact MSTB 2,5/ 2-ST-5,08 (1757019) and MSTB 2,5/ 6-ST-5,08 (1757051) data sheets, 28.01.2005, p.4 | a + 5.08 wide, 15 high, 18.2 long, nose 8.3, first pole 2.54 from the end; a is 5.08 and 25.4 (p.1) |
| | the same, pp.1-2 | clamp screw M3; conductor 0.2 to 2.5 mm2, AWG 24 to 12; nominal 2.5 mm2; stripping length 7 |
| flanged plug | Phoenix Contact MSTB 2,5/16-STF-5,08 (1778124) data sheet, p.7, the drawing of the MSTB 2,5/..-STF range | body a + 5.69 wide, a flange 4.7 each end, 15 high, 18.2 long, nose 8.3, flange screw 5.08 outside the end pole |
| plain header, with a plug seated | Phoenix Contact MSTBA 2,5/ 6-G-5,08 (1757284) data sheet, p.5 | header a + 7.08 wide, 8.6 high, 12 long; 22 from the back of the header to the back of a seated plug; plug 15 high, underside level with the header's |
| flanged header | Phoenix Contact MSTB 2,5/ 5-GF-5,08 (1776537) data sheet, Sep 27, 2023, p.3 and pp.16-25 | 35.56 wide, 12.1 high, 12 long; seventeen mating plugs, all flanged; MSTB 2,5/ 5-STF-5,08 (1778014) on p.18 |
| wire | Waskoenig+Walter H07V-K data sheet, status 05.10.2026, p.2 | outside diameter approximately 3 for 1.5 mm2 (the default) and 4 for 2.5 mm2 (the largest the plug takes) |

The plug and header drawings are rasters embedded at about 130 to 155 ppi and were read at
that resolution. A figure the drawing dimensions is exact; a scaled one is good to about
0.3 mm.

The five-position flanged plug's own data sheet is not held. The range drawing is read at
five positions, where a is 20.32: a body of 26.01 and 35.41 across the flanges, with the
screws 30.48 apart, the spacing of the header's two threaded inserts.

## 5. The seated depth

**Ruling: each plug seats by the engagement its drawing gives, measured from the face the
header presents.** The mated figure is on the plain header's data sheet: 22 from the back
of the header to the back of the plug, and the header 12 long. A seated plug therefore
stands 10 in front of the mouth of the header, and 8.2 of its 18.2 is inside, of a nose
the plug drawing dimensions 8.3.

| header | presents at | models | the drawing gives | mismatch |
|---|---|---|---|---|
| `common/terminal-header-508-5f@1` | the mouth of its housing, 2.5 proud (estimated) | a well 1.7 deep (2.5 less a floor at 0.8, both estimated) | 8.2 of nose inside | 6.5 too shallow |
| `common/terminal-header-508-2@2` | the same | the same | 8.2 | 6.5 too shallow |
| `common/dc-terminal-header-6@1` | its own face, the panel plane | nothing: drawn flat, no depth, the mouth 0.3 behind the panel on the vendor's model | 8.2 | no cavity modelled |

No plug figure is taken from a modelled depth. Each plug starts on the face its header
presents and the nose is not built. Each records the mismatch in
`provenance.seated-depth`, and a test pins the modelled figures so the plug's provenance
is read again when one changes. No header's geometry is changed.

## 6. Which way is up, and which pole is which

- **Up.** Each plug is drawn with the board side of the header down, so the clamp-screw
  tower rises above the header. `common/dc-terminal-header-6@1` draws its latch posts
  above its body, and the vendor's photograph shows the scalloped, board side below. The
  two AurCore headers are drawn the same either way up. For the flanged one the vendor's
  video shows the open side toward the POWER legend, which is where its top edge lands as
  placed. For the two-position one the same video (0:34 and 1:02) and the vendor's
  AIS4001P and AIS2001 product images show the keyed, open side toward the RELAY legend,
  with the two contacts side by side along it and parallel to the five of the power
  header. Both headers are placed turned 90, so the tower of each seated plug is toward
  its legend. The two-position header was first placed unturned, a quarter turn out, and
  was turned in its second major (#804).
- **Poles.** `wire-1` is at the left of the unrotated header. The two AurCore headers
  name their contacts `cell-1` and `pin-1` onward from the left and the wires follow them.
  The six-position header names none, so left to right is a convention there. Pole names
  (`+`, `-`, earth, `-48V`) are printed on the panel beside each header, differ by device,
  and are not on the plug.
- A seat applies the header's turn to the plug. Both AurCore headers are placed turned 90
  on every AurCore device and each plug follows its header.

## 7. What is estimated, and what is not expressible

- **The row of poles** is placed 4.3 above the underside of the plug, the middle of a
  header 8.6 high whose underside is level with the plug's. The clamp opening reads 10.6
  below the top of the plug on the drawing and is drawn at 10.7.
- **The wire entries** (3.7 by 6.8) and the flange (5.7 high) and screw head (4.0) are
  scaled. The floor of an entry, 1.5 below the face, is estimated.
- **How far the flange and its screw head stand in front of the header** (6.0 and 1.5) is
  estimated: the drawing shows the flange in the face view only.
- **The body is one box.** The step at the top of the tower and the latch arm are not
  built.
- **The stub** is a rule, not a reading.
- **The wire diameter** is one figure from a range, stated by its source to the whole
  millimetre; a placement sets its own.
- **The wire points are not routed in 3D yet.** The viewer reads one cable end per plug,
  the point named `cable`; reading `wire-1` to `wire-N` is #805.
- **Every pole is drawn wired, in one colour.** An unwired pole and a colour per pole are
  not expressible: a field per pole would be six fields on the longest plug here.
- **The plug covers the header's legend where the real one does.** On the AurCore
  switches the tower overhangs the POWER legend, and the two-position plug's the RELAY
  legend.

## 8. Out of scope

- Parts drawn with their plug already seated: `common/dc-terminal-plug-2@1` and the two
  Telco Systems DC plugs.
- Any change to a header's or the jack's geometry, including the depths sections 5 and 9
  question. The two-position header's width and its turn on the AurCore top face were
  settled afterwards, in its second major (#804): 12.16 wide, the Phoenix Contact MSTBA
  2,5/ 2-G-5,08 (1757242) width, where the first major was photo-measured at 10.16, and
  placed turned 90. Both AurCore headers are still drawn 12.1 high, the data sheets' `h`,
  which counts the 3.5 solder pin below the board; the installed height is 8.6 (#873).
- Plugs with angled wire entry, spring-clamp plugs and cable housings.
- Devices ship bare. A plug is in a slot's accept list because it mates the slot's
  interface; nothing seats one by default.

## 9. The DC barrel jack

**Ruling: the library treats the DC barrel jack as one nominal connector, `dc-barrel`.**
Barrel diameters vary by product. `common/dc-barrel@1` is placed on four devices and no
document held for any of them states the size of its jack, so the interface claims no
diameter, and one plug stands for the class.

- **The jack** (1.0.1) gains `interface: dc-barrel` and a `mate` point at the coordinates
  of its existing `power` point, the centre of the bore. `power` is kept. Lint L11 asks a
  part that states an interface for a point named `mate`, so presenting at `power` alone is
  refused. Its drawing and size are unchanged; the four devices take a patch.
- **The rating is on the placement, not the part.** Each placement of the jack states
  `input-voltage` and `current-max-a`, the two names a DC power entry module in the
  library already used, from that device's own documents:

  | device | `input-voltage` | `current-max-a` | its document says |
  |---|---|---|---|
  | `halny/hlx-tgv` | 12 VDC | 1.0 | datasheet, "DC +12V/1.0A" |
  | `nokia/xs-010x-r` | 12 VDC | 1.0 | product guide, Table 2-2 |
  | `nokia/xs-010xr-p` | 12 VDC | 1.0 | product guide, Table 4-2 |
  | `telco-systems/tm-280` | 5 VDC | 3.0 | data sheet, "5VDC @3A (max)" |

  Neither the interface nor the plug states a voltage or a current. The DCIM exports do
  not read the two attributes; each device's export changes in its drawing version line
  only.
- **The plug,** `generic/dc-barrel-plug@1`, is drawn at the common 5.5 mm barrel from one
  manufacturer's drawing, the Same Sky PP3-002A data sheet (09/12/2024), p.2: barrel 5.5
  across with a 2.1 bore and 9.5 long, a flange 7.8 across and 3 long, a round cover 8.2
  across, 33.5 overall, and a cable entry of (4). It is a nominal size chosen for the
  library. That it is the right plug for a given device is not claimed, and its provenance
  says so. Seen from the cable end it is the flange, the grip and a 30 mm stub of cable
  sized by `cable-od` and coloured by `jacket-color`, with the `cable` point on the stub.
- **The grip is that plug's screw-on cover, not a moulding.** No drawing of a moulded
  power-supply plug is held, so no strain relief is drawn; the grip is 21 long, the 33.5
  less the barrel and the flange.
- **Seated depth.** The plug seats with its flange on the face of the jack and all 9.5 of
  its barrel inside, so 33.5 - 9.5 = 24 stands in front. The jack is drawn flat and states
  no depth, so the barrel has no modelled cavity to enter; the plug records that and takes
  nothing from the jack. The jack's skin draws a bore 6.2 across and a pin 1.8 across,
  neither sourced, which a 5.5 barrel with a 2.1 bore enters.
- **Naming.** The plug's `media` is `barrel` and its registry key `barrel-plug`. Lint L62
  reads a port part's media and every `conforms:` value, with its leading segment, as a
  connector word, and `dc` as one flags every `dc-in` placement id.
- **Polarity is not modelled.**
- **The default cable** is 4.0, the plug's cable entry and so the largest it takes; no
  cable data sheet is held.

`spec/tests/test_dc_barrel_plug.py` holds the ruling's wording in the registry, the four
placements and their ratings, the slot on each device, the plug's shape, a seat on two
devices and a `cable-od` from a placement.

## 10. What follows

The second part of #789 is the fixed terminals. The barrier blocks are section 12 and the
ground studs section 13. The terminals drawn inside DC power supplies, and a two-hole lug,
are later work.

## 11. Testing

`spec/tests/test_dc_terminal_plugs.py`, against the real library and builds made by the
test:

1. The registry holds the three interfaces, each citing a standard; a flange is not part
   of a key.
2. Each header presents its interface at the middle of its row of contacts and kept its
   size, class, attrs and elements.
3. Slots: each interface is mated by exactly its plug; a census of the parts that present
   one and of the placements, with non-zero counts.
4. Each plug's class, `mates`, media, positions, fields and registry entry; no `size.d`;
   no mark.
5. One stub and one point per pole, at the pitch, each bound to `wire-od` and
   `wire-color`; the poles numbered as the header numbers its contacts; the flange screws
   on the header's inserts.
6. The solids chain from the header face to the stubs.
7. Seating in real headers, one of them turned 90: mate on mate, each wire over its own
   contact, the seated depth, and the published slot.
8. `wire-od`, `wire-color` and `body-color` from a placement.

## 12. Barrier terminal blocks: a seat per pole, and the ring lug

A barrier block is not plugged. Each wire is crimped into a lug and the lug is landed on a
terminal screw, so the slot is the pole and the part that seats is the lug on its wire.

### 12.1 The interface

**Ruling: the library treats a screw or stud terminal that a lug lands on as one nominal
connector, `terminal-stud`.** Stud and screw sizes vary by product and most placing parts
state none, so the interface claims no size, as `dc-barrel` claims no diameter. Where a
document states a size it is an attribute of the placement.

No attribute for a stud or screw size is introduced yet. None existed in the library, and
nothing in this change states a size: no document held for any of the four devices gives
the thread or the head of its terminal screws. The first part whose document prints a
size brings the attribute with it.

### 12.2 The seat is the screw

| part | head | height | used by |
|---|---|---|---|
| `common/terminal-screw-34@1` | 3.4 | 1.2 | `common/dc-terminal-24@1` |
| `common/terminal-screw-38@1` | 3.8 | 1.4 | `common/dc-terminal-27@1` |

Each is `class: screw`, states no `media` and no `conforms`, and presents `terminal-stud`
at a `mate` point on the screw axis. It is the screw itself: the slotted head and its
`cyl` relief were moved out of each block's skin and contract into it, unchanged.

They are two parts and not one with a size field. A field can set the radius of a circle;
it cannot resize the slot, the box of the part or the height of its relief, and the two
blocks draw heads of different sizes.

### 12.3 The blocks

`common/dc-terminal-24@1` and `common/dc-terminal-27@1` (each 1.0.1) compose three seats,
`lug-1` to `lug-3`, each on its pole's screw with the `lift` of the pole's top face (7.9
and 9.0). Neither block states an interface of its own, so each publishes its seats as
nested slots. The element ids `pole-1` to `pole-3`, the size, the class, the attrs and the
`dc-in` point are unchanged, and each block compiles to the same drawing as before: the
faces of the CSR180, the CSR200 and the TM-8104 were rasterised before and after and
compared pixel for pixel, with no difference.

| device | reaches the block through | slot keys |
|---|---|---|
| `edgecore/csr180` | two placements of `common/dc-terminal-24@1` | `psu1-input/lug-1` to `psu2-input/lug-3` |
| `edgecore/csr200` | two placements of `common/dc-terminal-27@1` | `psu1-input/lug-1` to `psu2-input/lug-3` |
| `telco-systems/tm-8104`, `tm-8106` | `telco-systems/tm810x-psu-dc@1` in a supply bay | `psu-1/terminal/lug-1` to `psu-2/terminal/lug-3` |

Each device takes a patch. Every slot offers exactly one part, the ring lug.

### 12.4 The lug

`generic/ring-lug@1` is a one-hole insulated ring terminal on its wire, seen in plan as a
front elevation sees it landed on a screw: the ring tongue, the sleeve over the crimp
barrel, a 10 mm stub of insulated wire leaving the sleeve in the plane of the face, and
the head of the screw that holds it. `class: port`, `mates: terminal-stud`, no `behaviour`
and no `size.d`. `mate` is at the centre of the stud hole. `cable` is at the free end of
the stub and points down, along the wire.

**It is a nominal lug chosen for the library.** The screw size is not documented for any
of the four devices. What their documents do fix is the wire and the room:

| device | its document says |
|---|---|
| Edgecore CSR180 | quick start guide: four ring lugs in the package, pictured with blue sleeves; #14 AWG / 1.5 mm2 wire, AWG 10 to 14 suggested; terminal screws 7 in-lb maximum |
| Edgecore CSR200 | quick start guide: four ring lugs, the same picture; #14 AWG / 1.5 mm2 wire |
| Telco Systems TM-8104, TM-8106 | no installation guide is held; the data sheets say only that the supply is 24 or -48 VDC |

So the lug is the narrow-tongue terminal for 16 to 14 AWG wire whose tongue fits the 6.0
pole window of the smaller block. That it is the right lug for a given terminal is not
claimed, and the Telco supply's provenance says nothing states what it takes.

| figure | value | source |
|---|---|---|
| tongue width | 5.5 | JST solderless terminals catalogue, RING TONGUE (R type) Vinyl-insulated (flared), sheet of 23-06-08, FV2-MS3, B |
| stud hole | 3.2 | the same row, d2; listed for an American 3-4 or metric 3 stud |
| overall length | 17.4 | the same row, L |
| hole centre to sleeve | 5.6, drawn 5.65 | the same row, F; drawn so the sleeve ends at L |
| sleeve | 9.0 long, 4.5 across | the same row |
| material thickness | 0.8 | the same row, T |
| sleeve colour | blue | the Edgecore guides' package pictures, sampled; the JST sheet lists blue for the whole 16 to 14 AWG range |
| wire | 3.0 across | Waskoenig+Walter H07V-K data sheet, status 05.10.2026, p.2, 1.5 mm2 |
| neck | about 3.3 at the sleeve | scaled from the catalogue drawing |
| screw head | 3.8 across, 1.4 high | borrowed from `common/terminal-screw-38@1`, an estimate |

The terminals on that sheet for a 5-6 or 3.5 stud are 6.4 wide and more, which the 6.0
pole window does not admit.

**A stub in the plane of the face is 10 long, not 30.** The stub rule of
[connectors-coax-design.md](connectors-coax-design.md) section 5 was written for a stub
that points at the viewer, where its length hides nothing. Lying in the plane of the face
a stub covers what is beside the terminal: at 30 it ran far past the lower edge of a 1RU
chassis and across the supply below on the TM-8104. At 10 it still overhangs the lower
edge of the CSR180 a little, which is what a wire does.

Fields: `wire-color` (black) and `barrel-color` (the blue above).

**There is no `wire-od` field.** A wire lying in the plane of the face cannot take a size
field today. The one size binding, `data-r-from`, sets the radius of a circle, which is
how the plugs' stubs are sized, end on. This stub is a rectangle in plan and a `bar` in
3D, and a `bar` takes its diameter from the number in the contract. A field would need a
binding that sets a rectangle's width and a `bar` that reads its diameter from its node.
A ring terminal is in any case made for one wire range, so another wire is another lug.

### 12.5 How the lug and the host's screw are layered

A real lug lies on the pole with the screw through its hole. That form was tried first
and does not build cleanly on these blocks. Each block builds a lip along its lower edge
that stands higher than its poles, and the tongue of a lug lying on the pole runs into it:

| block | pole top | lip | the tongue would be at | and would cross the lip |
|---|---|---|---|---|
| `common/dc-terminal-24@1` | 7.9 | 9.0 | 7.9 to 8.7 | from 4.15 to 5.6 below the screw axis |
| `common/dc-terminal-27@1` | 9.0 | 10.2 | 9.0 to 9.8 | from 4.55 to 5.6 below the screw axis |

The lips are estimates, and the Edgecore guides draw each pole open at its lower edge
between the barriers, so the lip is probably the wrong shape there. No block is changed
here: cutting a notch would alter a drawing this change promises to leave alone.

So the seat presents at the top of its screw head (`mate` sits `on: head`), 9.1 and 10.4
off the face of the block, and the whole lug stands above the lips:

| block | host head | tongue | the lug's head | sleeve | wire |
|---|---|---|---|---|---|
| `common/dc-terminal-24@1` | 7.9 to 9.1 | 9.1 to 9.9 | 9.9 to 11.3 | 9.1 to 13.6 | 9.85 to 12.85 |
| `common/dc-terminal-27@1` | 9.0 to 10.4 | 10.4 to 11.2 | 11.2 to 12.6 | 10.4 to 14.9 | 11.15 to 14.15 |

- **In 2D** the lug paints over the host's head and draws a head of its own over its
  hole. An open hole would show only the middle of the host's head, since a ring
  terminal's hole is smaller than the head that holds it.
- **In 3D** the host's head ends where the tongue starts, so no solid of the lug shares
  its volume, and the head the lug draws stands on the tongue.
- **What is wrong with it:** the tongue is 1.2 or 1.4 higher than it should be, the
  height of the host's head. The sleeve's underside is built level with the tongue's,
  where a real sleeve is centred nearer the tongue and hangs below it.
- The head the lug draws is one size and does not follow its host's.

### 12.6 Which way the wire leaves

The wire leaves downward in the lug's own unrotated frame. On both Edgecore blocks the
guides draw the screws facing the viewer, the barriers between the poles and each pole
open toward the legend printed below the block, so a seated lug's wire leaves over the
block's lower edge with no turn.

**The lug on a terminal screw does not turn (#829).** A configuration may turn an
occupant on its seat with `turn:` where the seat allows it (section 13.4). The
`terminal-stud` interface allows the four right angles, and each terminal screw narrows
that to 0 on its own `mate` point (`turns: [0]`): the barriers either side of the pole
fix the direction, and a turn there would lay the lug across the barrier. L146 and the
build refuse any other turn on a pole, and a lug seated on one draws exactly what it drew
before.

### 12.7 Limits, and what is not covered

- **No two-hole lug.** `nokia/sr-1-dc-terminal-block@1` is not touched. The 7750 SR-1
  chassis installation guide (3HE22130AAAATQZZA01, release 25.10) calls for a Panduit
  LCD6-10AH-L two-hole, 45-degree lug on #6 AWG wire across each pair of 10-32 studs
  (Table 58, Table 59 and Figure 50: hole 0.27 in, spacing 0.63 in). A one-hole lug on
  each stud would put two lugs on one terminal, overlapping. That block waits for a lug
  that spans a pair.
- **Ground studs are section 13.** The ground pads, plates and bolts listed there are not
  covered.
- **The DC power supplies and power entry modules that draw their own terminals** are
  not covered; their terminals are art in the supply's skin and are not seats.
- **One wire size, one colour for the wire, and every seat takes the same lug.**
- **A lug on a supply in a bay is painted with that supply,** so anything of it that
  reached past the supply would be painted under the next one. At a 10 stub it ends inside
  the TM-8104 supply's own face.
- **A lug swapped onto a block placed straight on the device reaches the 3D scene.**
  The explorer's 3D scene is cut from faces that `seatViews` (kit/swap.js) rewrites, and
  `viewsToRewrite` names the faces. A key such as `psu1-input/lug-2` is claimed by no
  bay and no cage of any view: the block publishes slots and is not itself a cage. For
  such a key every view is rewritten (#814), since the index cannot say which face holds
  the slot and `seatFace` does nothing on a face without it. Before that rule the lug
  chosen on a CSR180 or CSR200 showed in 2D and was silently missing in 3D.
- **The `cable` point states no `on:`.** That key takes a feature built with `out` or
  `cyl`; the wire is a `bar`. The depth the viewer reads for the cable end is the seat's,
  2.25 below the axis of the wire. Accepted for now; routing of cable ends is #805.

`spec/tests/test_terminal_lugs.py` holds the registry entry, the seat parts, each block's
seats and slots, the bare blocks' compiled screws, a lug on one pole of the CSR180, the
CSR200 and a TM-8104 supply in its bay with its neighbours empty, the depths of every
solid against the host's head and the lips, the two colour fields, and the kit's own
slot walk offering the seats and seating a lug as the build does.

## 13. Ground studs: a seat per stud

A chassis ground point is a stud or a tapped hole that a lug is landed on, so it is the
same nominal connector as a terminal screw, `terminal-stud`, and the same lug seats on it.

### 13.1 The parts

| part | what it draws | a lug rests on | lift |
|---|---|---|---|
| `common/ground-lug@1` (1.4.1) | a boss, a washer and a cross-head screw under an earth symbol | the screw head, `on: screw-cap` | 4.7 |
| `common/ground-stud@1` (1.0.1) | a stud with its hex nut | the end of the stud, `on: stud` | 6.0 |
| `juniper/mx-ground-stud@1` (1.0.1) | a threaded stud on a washer | the end of the stud, `on: stud` | 8.0 |
| `casa/shelf-ground-stud@1` (1.0.0, new) | a star washer, a hex nut and the end of a stud | the end of the stud, `on: stud-top` | 3.5 |

Each of the first three gained `interface: terminal-stud` and a `mate` point on the stud
axis and nothing else: the drawing, the size, the class and the elements are unchanged, and
each took a patch. Every placement of one is therefore a slot of its device, in the view's
`cages[]`, keyed by the placement id, the way a USB jack became one.

**Each seat is on top of everything its part builds,** as section 12.5 seats a lug on the
head of a terminal screw and for the same reason. A real lug lies under the screw head or
the nut. Seated there, its tongue and the head it draws would share the volume of the
solids the part builds:

| part | the part builds, off the panel | the lug's tongue | head | sleeve | wire |
|---|---|---|---|---|---|
| `common/ground-lug@1` | boss 0 to 3.2, washer 3.2 to 3.7, screw head 3.7 to 4.7 | 4.7 to 5.5 | 5.5 to 6.9 | 4.7 to 9.2 | 5.45 to 8.45 |
| `common/ground-stud@1` | nut 0 to 3.2, stud 0 to 6.0 | 6.0 to 6.8 | 6.8 to 8.2 | 6.0 to 10.5 | 6.75 to 9.75 |
| `juniper/mx-ground-stud@1` | stud 3.0 to 8.0 | 8.0 to 8.8 | 8.8 to 10.2 | 8.0 to 12.5 | 8.75 to 11.75 |
| `casa/shelf-ground-stud@1` | washer 0 to 0.7, nut 0.7 to 2.9, stud 0 to 3.5 | 3.5 to 4.3 | 4.3 to 5.7 | 3.5 to 8.0 | 4.25 to 7.25 |

On `common/ground-stud@1` the nut ends at 3.2 and the stud at 6.0. A lug on the nut would
have the stud, drawn 4.0 across, through its 3.2 hole and through the head it draws, so
the seat is the end of the stud. Every one of those heights is an estimate in its own
contract, and so the lug stands too far off the panel by the height of the hardware above
the real seat.

### 13.2 The Casa terminal

`casa/c40g-ground-studs@1` drew three studs in one skin. Each stud is now a part,
`casa/shelf-ground-stud@1`, composed three times as `stud-tr`, `stud-bl` and `stud-br`,
the ids the three groups carried in the skin. The washer, nut and stud art and their
relief moved into that part unchanged, as section 12.2 moved the terminal screws. The
terminal states no interface, so it publishes three nested slots,
`ground-studs-rear/stud-tr` and so on, and the rear of the C40G compiles to the same
pixels as before.

No existing stud part draws this hardware. `casa/ground-bolts@1` holds the same art for a
pair and is not touched.

**All three studs are seats.** The C40G hardware installation guide says the terminal
provides two M6 screws for one double-lug cable, and its figures draw three studs; the
device records the disagreement as its `ground-stud-count` gap and follows the figures. No
document says which two of the three positions take the lug, so none is left out.

### 13.3 `stud-size`

Section 12.1 left the size of a stud or screw to the first document that printed one.
Ground points are where documents print them. The attribute is `stud-size`, text, on the
placement: `M4`, `M5`, `M6`, `10-32`, `1/4-20`, `1/4 in`. It is written only where a
document for that device states the size, each with its source in the device's
`provenance.ground-stud-size`.

| devices | `stud-size` | their documents say |
|---|---|---|
| 13 UfiSpace: M3000-14XC, S9500-22XST, S9500-30XS, S9501-18SMT, S9501-28SMT, S9502-16SMT, S9510-28DC, S9510-30XC, S9511-20CT, S9600-102XC, S9600-28DX, S9601-102XC, S9601-104BC | M4 | hardware installation guide: a screw kit of 2 x M4*L8.0mm for the grounding lug, locked with 2 M4 screws |
| Edgecore AGR110, AGR130 (`ground-right`), DCS500 | M5 | quick start guide, package contents: one grounding lug, 2 M5 screws and 2 washers |
| Edgecore AIS800-64D, AIS800-64O | M6 | quick start guide: two M6 screws and washers through one grounding lug |
| Casa C40G | M6 | hardware installation guide: two M6 screws |
| Nokia Lightspan MF-8 (LMFS-F) | M6 | installation manual s4.5.2.2: a dual-hole M6 lug, 6.35 mm holes, 16 mm spacing |
| Juniper MX80, MX104, MX150 | 10-32 | hardware guides: holes for SAE 10-32 screws at 0.625 in. centres; MX150 Table 22 |
| Juniper MX240, MX480 | 1/4-20 | hardware guides: PEM nuts for UNC 1/4-20 screws at 0.625 in. centres |
| Amphenol 300CB08, 300CB08-SC, 300CB08-C, the six nrg300CB08 CTRL and SENS versions, the nrgILS300CB08 and its -SC | 1/4-20 | the one installation guide for every version, specifications: three sets of 1/4-20 threaded holes on 5/8 in. centres; a dual-hole or a single-hole lug |
| Nokia 7360 FX-16, FX-8, FX-4 | 1/4 in | HIM R6.9: a 1/4 in. stud at 1 in. spacing (FX-16); a dual-hole lug with 1/4 in. holes at 3/4 in. spacing (FX-8, FX-4) |

That is 116 placements on 39 devices. The other 29 placements state none, because no
document held prints a size for them: every ground point of the other 22 devices, and the
left-hand point of the AGR110 and the AGR130, where the kit fits the right-hand one. On the FX-8 and the FX-4 the
figure is the hole of the lug the guide calls for, not a stated stud.

The interface still claims no size and nothing reads the attribute: not the lug, not the
kit, not the DCIM exports. It is a fact carried beside the slot.

### 13.4 Which way the wire leaves

**A configuration states the turn, or the build chooses it (#829).** `occupants:` takes
`turn:`, the occupant's turn on its seat, RELATIVE to the seat: `render.solve_seat`
draws it at the host's turn, plus any axis a spanning host's pair runs on, plus the
turn. The turns a seat allows are its interface's `turns` in
`spec/schemas/connectors.yaml` narrowed by the part's presented point
(`manifest.allowed_turns`); `terminal-stud` allows 0, 90, 180 and 270, every ground stud
part takes all four, and an interface naming none allows 0 alone. L146 holds a
configuration's `turn:` to the list; L147 holds a point's `turns` to a subset of its
interface's.

**Where a configuration states no turn, the default is rule B, "may leave the face".**
`render.default_seat_turn` takes the whole lug, its 10 stub of wire included, turned
about its own `mate`, and tries the four directions in the order an installer would:
DOWN; toward the NEARER SIDE EDGE of the face; the other side; UP. It takes the first
in which the lug crosses no placement, no bay and no other seat. A part the stud stands
on is not crossed, and the other studs of a terminal that composes them are other
seats; the two studs a pair host's own slot spans are not, because the two-hole lug
lands on both (#828). The directions name where the WIRE goes, read off the occupant's
own `cable` point: a ring lug is drawn leading down and a two-hole lug leading right
(13.7), so a pair stood on end leads its wire down at turn 0 and a pair side by side,
which cannot lead down, leads toward the nearer edge. Running past the edge of the face is allowed: on a 1RU rear most studs sit low,
and a wire leaves the box. A printed legend is a soft preference: of the directions that
cross nothing hard, the one over the fewest legends wins, in the same order. The answer
is computed from the view as authored, so one answer serves every configuration; it is
published per view as `seat-turns` in configs.json (`{slot key: {ref: turn}}`, a nested
slot by its path, `ground-studs-rear/stud-tr`), each slot publishes its `turns`, and the
seated occupant carries `data-seat-turn`. The kit seats by those and never re-derives
the default; a reader's turn travels in its own `turn=` parameter of a share link.

Across the library, 2026-10-07, once the grounding batch (13.7) made 51 pairs: 155
ring-lug seats on 63 devices and 51 two-hole-lug seats on 25 devices:

| the wire leaves | ring lug | two-hole lug |
|---|---|---|
| down | 103 | 45 |
| toward the left edge | 24 | 4 |
| toward the right edge | 22 | 1 |
| up | 6 | 1 |

No ring lug's default crosses a part, a bay or another seat. Two cross a legend, the FAN legend
beside `ground-2` on the UfiSpace S9600-102XC and S9601-102XC, where every direction
that crosses no part crosses that or another; the MX304 plate's two-hole lug crosses a
legend down, and the ESD jack up. Two two-hole lugs cross a part whichever way they lead
along their pair, both because of where the model puts things: the MX150's ESD jack
starts under the tongue of a lug 10.67 wide across its studs, and the MX480's pair
stands 0.34 inside the PEM3 bay's edge. The crossings the seat's own direction
made, listed below, are gone: on the Supermicro SYS-111E-FWTR and SYS-111E-FDWTR the
wire leads up, away from LAN1; on the Juniper MX150 the second stud leads up, away from
the ESD jack; on the Edgecore DCS500 `ground-0` leads to the right of the fan bay; and
every upper stud of a pair drawn one above the other leads sideways, clear of the lower
stud. `spec/tests/test_occupant_turn.py` pins both distributions, the three residual
legends and the two residual parts.

**What the seat's own direction gave, turn 0, kept as the record it was.** A lug's wire
leaves in the lug's own "down" turned by the placement. Seating a lug on every one of
the 147 seats in the library at turn 0 gives:

- **143 leave down the face and 4 leave to the left.** The only turned placements are the
  two on the Edgecore DCS500 and the two on the Nokia FX-16 side panels, all at
  `rotate: 90`. On the FX-16 the same turn is placed on the left and on the right side
  view, so the wire runs toward the rear on one side and toward the front on the other.
- **70 run past the lower edge of the face,** by 2.95 to 20.05. A lug is 24.65 long below
  its stud and most of these are on 1RU rears and side panels, where the stud sits in the
  lower half. The longest overhang is on the Edgecore DCS520, whose studs are 4.6 above
  the lower edge of a 2RU rear.
- **Two run across a port:** on the Supermicro SYS-111E-FWTR and SYS-111E-FDWTR the stud
  is in the vent field above LAN1 and the sleeve lies across that jack. This is the worst
  case.
- **One runs across another connector and its legend:** on the Juniper MX150 the second
  stud is above the ESD jack.
- **One runs across a bay:** the left-pointing lug of `ground-0` on the DCS500 reaches the
  edge of the first fan bay.
- **Seven, on five devices, run across a printed legend only:** both studs of the Juniper
  MX240 and MX480, and the stud of the Edgecore ECS4120-28Fv2-I, ECS4530-54CSFP and
  ECS4530-54CSFP-I.
- **Forty-two run across the second stud of their own pair** (13.5). Thirty-three of them
  are on the eleven Amphenol 300CB08 panels (the plain, -SC and -C, the six nrg300CB08
  CTRL and SENS versions, the nrgILS300CB08 and its -SC), which share their ground landings and
  whose three landings are each drawn one stud above the other: on the
  side views the wire leaves down, the lower lug 12.45 past the lower edge, and on the
  bottom view it leaves toward the front of the panel.
- None runs off the top or a side of its face.

On a ground point the direction of the lug is the installer's choice, so every one of
these was a limit of the model and not a reading of the hardware. The default above
answers them; a configuration that knows the installed direction states it.

### 13.5 What this shows that was wrong already

Making each stud a seat puts a to-scale lug beside drawings that were never to scale with
one. None of this is corrected here.

- **`common/ground-lug@1` is drawn smaller than the hardware it stands for.** Its screw
  head is about 5.1 across in a part 7.0 wide, about an M3 pan head, and the lug is the
  M3-class terminal 5.5 wide. The devices that state a size state M4, M5, M6 and 1/4 in. A
  real lug for those is wider than the part.
- **Most pairs are the two holes of one two-hole lug.** Thirteen pairs of
  `common/ground-lug@1` on twelve devices, the five pairs of `juniper/mx-ground-stud@1`
  and thirty-four pairs of `common/ground-stud@1`, one on the Nokia LMFS-F and three on each of
  the eleven Amphenol 300CB08 panels, are two holes that one lug spans; the Casa terminal takes one two-hole lug across two of its three studs. Two
  one-hole lugs are a stand-in.

  | drawn | pitch | devices | two one-hole lugs |
  |---|---|---|---|
  | side by side | 11.0 | UfiSpace S9500-22XST, S9501-28SMT, S9502-16SMT, S9510-28DC, S9510-30XC, S9511-20CT | lie beside each other, 5.5 apart |
  | side by side | 13.0 to 16.0 | UfiSpace M3000-14XC (13.0), S9501-18SMT (15.8 and 15.7); Juniper MX150 (13.0), MX104 (16.0) | lie beside each other |
  | one above the other | 13.2 to 16.5 | Edgecore AIS800-64D, AIS800-64O (16.2); UfiSpace S9600-102XC (14.7), S9601-102XC (16.5); Juniper MX240, MX480 (13.2), MX80 (14.0); Nokia LMFS-F (16.3); Amphenol 300CB08 and its ten versions (15.9, three pairs each); Casa C40G (15.3) | OVERLAP: the upper lug lies across the lower stud |

  The documents give the pitch as 0.625 in. (15.86) on the MX80, MX104, MX240 and MX480,
  as 16 on the LMFS-F and as 5/8 in. (15.9) on the eleven 300CB08 panels, which are drawn at it; several
  are drawn closer than that. The LMFS-F and 300CB08 documents also allow a single-hole
  lug on one stud, so one lug there is a documented landing and two are not.
- **Some single placements stand for a two-hole landing.** One `common/ground-lug@1` is
  placed where the device's documents describe a plate or a pair for one two-hole lug: the
  right-hand point of the Edgecore AGR110 and AGR130, both points of the DCS500, the
  points of the AGR560, EPS112 and EPS203, the points of the Nokia FX-16, FX-8 and FX-4,
  and those of the UfiSpace S9500-30XS, S9600-28DX and S9601-104BC. That is fourteen
  placements on twelve devices. A one-hole lug there is one hole short.

A two-hole lug, on its own interface or on a seat that spans a pair, is the part that
answers the last two. It is the same part `nokia/sr-1-dc-terminal-block@1` waits for
(section 12.7).

### 13.6 What is not covered

- **A two-hole lug,** and so every pair above. Section 13.7 adds it.
- **`cisco/a9k-ground-pad@1` and `common/ground-screw-washer@1`,** which are not seats.
- **The ground plates and bolts:** `casa/ground-bolts@1`, `edgecore/agr-ground-plate@1`,
  `juniper/mx204-ground-plate@1`, `juniper/mx304-ground-plate@1` and the ground point on
  `maiaedge/pbc-2000-rear-bracket@1`.
- **The terminals drawn inside DC power supplies and power entry modules.**
- **A lug of another size:** every seat takes the one nominal lug. Turning one is
  section 13.4.

`spec/tests/test_ground_stud_lugs.py` holds each part's interface and seat, the Casa
terminal's three composed studs and the art they kept, a census of all 145 placements with
every one a slot, every `stud-size` and its absence elsewhere, a lug seated on a real
device for each part with its solids above what the part builds, a turned placement, two
pairs with the overlap recorded, and the kit offering the studs and seating a lug as the
build does, with the view its 3D pass names.

### 13.7 A two-hole lug across a pair (#828)

**The pitch is the interface.** A two-hole lug is one stamping, so a lug for 5/8 in.
centres does not land on studs 3/4 in. apart. Three interfaces in
`spec/schemas/connectors.yaml`, `stud-pair-5-8`, `stud-pair-3-4` and `stud-pair-1`, each
`spans: {interface: terminal-stud, count: 2}`, the mechanism `lc-duplex` uses for two LC
bores. Each cites the standards entry of the lug that mates it, `two-hole-lug-5-8`, `-3-4`
and `-1`, which carries the pitch, 15.875, 19.05 and 25.4, as `lc-duplex` cites the bore
entry carrying 6.25. The stud size is not in the key; it stays the placement's `stud-size`.

**A pair host** presents the interface and composes two stud parts at exactly that pitch,
the first at the left. Its `mate` is the midpoint of the studs' own mate points, with
`seat-out` the height each stud presents at, so a lug across the pair lies where a one-hole
lug on either stud already does (13.1). L116 holds the count, the pitch, the midpoint and
the depth; its depth arm now reads what a spanned part PRESENTS, its placed `lift` plus its
own seat out, which for an LC bore is its lift as before and for a stud is the top of the
stud. L115 makes the pair and its two studs one level or the other, and each stud still
offers the ring lug alone.

| host | studs | interface |
|---|---|---|
| `juniper/mx-ground-stud-pair-5-8@1` | `juniper/mx-ground-stud@1` twice | `stud-pair-5-8` |
| `juniper/mx-ground-stud-pair-3-4@1` | `juniper/mx-ground-stud@1` twice | `stud-pair-3-4` |
| `common/ground-stud-pair-5-8-m6@1` | `common/ground-screw-m6@1` twice | `stud-pair-5-8` |
| `common/ground-stud-pair-5-8-m4@1` | `common/ground-screw-m4@1` twice | `stud-pair-5-8` |
| `common/ground-stud-pair-5-8-1-4@1` | `common/ground-screw-1-4@1` twice | `stud-pair-5-8` |
| `common/ground-stud-pair-3-4-1-4@1` | `common/ground-screw-1-4@1` twice | `stud-pair-3-4` |
| `common/ground-stud-pair-1-1-4@1` | `common/ground-screw-1-4@1` twice | `stud-pair-1` |

**The sized screws (#830, part 1).** `common/ground-lug@1` stays the library's nominal
ground screw, unsized, as the owner ruled. `common/ground-screw-m6@1` (ISO 7045 pan head,
12.0 across, 4.6 high) and `common/ground-screw-1-4@1` (ASME B18.6.3 pan head, 12.50
across, 3.66 high) are drawn at a stated size and used only inside a pair host.
`common/ground-screw-m4@1` (ISO 7045, 8.0 across, 3.1 high) joined them with the UfiSpace
pairs: eight chassis fix their accessory lug with two M4 screws, and seven of their guides
draw the holes on a flank figure - three distinct drawings, one of them shared byte for byte
by four guides and another by two - that reads 15.6 to 15.9 apart, so each landing is one
`common/ground-stud-pair-5-8-m4@1`. An M5 screw is still not added: the one device stating
M5 for a two-hole plate, the Edgecore DCS500, reads 17.2 between its screws, which is no
lug pattern, so its screws stay single placements.

**One earth symbol per landing.** `common/ground-lug@1` draws an earth symbol above its
stud, so a two-screw plate drawn as two of them printed two where the chassis prints one.
`common/ground-screw@1` is the same stud, washer and cap without the symbol, presenting
`terminal-stud` at the same 4.7: an unsized landing places `common/ground-lug@1` on the
screw the printed symbol sits by and `common/ground-screw@1` on the other (the Edgecore
AGR560, DCS500, EPS112 and EPS203).

**The lugs.** `generic/two-hole-lug-5-8@1` (Panduit LCD6-10A-L, #6 AWG),
`generic/two-hole-lug-3-4@1` (LCC10-14BW-L, #10 AWG) and `generic/two-hole-lug-1@1`
(LCD6-14D-L, #6 AWG), read off distributors' attribute tables (`estimated`: the Panduit
drawings refused the fetch). Each is drawn ACROSS, the canonical axis of a spanning
connector: holes along +x from the tongue's tip, the barrel and a 10 stub of wire leaving
along +x. Fields `wire-color` and `barrel-color`, as on the ring lug.

**Which way the wire leaves** is the pair's axis, derived from the order its studs are
composed in (`manifest.spanning_axis`), plus the host placement's `rotate`. A pair side by
side sends the wire right; a pair stood on end is the host placed at `rotate: 90`, which
puts the first stud on top and sends the wire down. Turning a lug the other way along its
pair is #829, which gives the three pair interfaces `turns: [0, 180]`.

**The Juniper MX chassis are the first placed.** The MX80, MX240 and MX480 pairs (drawn
14.0, 13.2 and 13.2 apart, one stud above the other) are each one
`juniper/mx-ground-stud-pair-5-8@1` at `rotate: 90`, at the 0.625 in. their guides give; the
MX104's (16.0, side by side) is the same host unturned. The MX150's 13.0 is
`juniper/mx-ground-stud-pair-3-4@1`: no MX150 document gives the spacing, and the 3/4 in. is
inferred from the lug its Table 22 names, the Panduit LCC10-14BWL. Each pair moved
symmetrically about the midpoint the photographs placed, with its cutouts. The MX204's plate
became `juniper/mx204-ground-plate@2`, two 10-32 screws on the 0.75 in. its guide states
(@1 drew 16.0). The MX304's plate became `juniper/mx304-ground-plate@2`, two M6 screws
stood one above the other on 5/8 in.: its guide's "0.63-in. (16-mm) centers" is the 5/8 in.
pattern, 0.63 the lug-table rounding of 0.625 and 16 the metric rounding of 15.875 (@1 drew
16.0, the metric figure taken literally). So section 13's census moves:
`juniper/mx-ground-stud@1` is placed by no device and composed by the two MX hosts, leaving
135 single-stud placements on 56 devices, 106 of them with a `stud-size` on 34 devices,
beside the seven pair placements.

**Not built:** a lug whose tongue is bent at 90 or 45 degrees (the UfiSpace S96xx and the
Nokia SR-1 documents call for one); a pair whose documented pitch is not one of the three.

`spec/tests/test_two_hole_lugs.py` holds the registry, the screws, every host's pitch,
midpoint, depth and axis under L115 and L116, each lug drawn across, every host placed side
by side and on end on a built face with a lug whose holes land on the studs and whose wire
leaves right or down, its solids above the studs, and the kit seating it as the build does.

## 14. The P40 output connector

The connectorized Amphenol Network Solutions power panels (the 300CB08-C and -SC and their
four nrgSMART versions) end each output in a two-pole latching receptacle,
`amphenol-ns/output-p40@1`, that takes a P40 plug: the Amphenol PRM series with 4 mm RADSOK
contacts, BATT above RTN. The receptacle was drawn and presented nothing (#831), and the
plug was not drawn.

### 14.1 Decisions

1. **One vendor interface, `p40`.** It is in `spec/schemas/connectors.yaml` with no
   `standard`: no standard is held for the connector, and the registry entry says so. Only
   a pair of spanned interfaces reads a `standard` (L116), and this is not one.
2. **The receptacle gains its interface and its mate point and nothing else**, as the
   terminal headers did (section 2): `mate` is midway between its two cavities, on the mouth
   of the shroud it builds 6.0 proud (`on: shell`). The receptacle goes to 1.1.0 and the six
   panels that place it take a patch.
3. **One plug, `amphenol-ns/p40-plug@1`.** It is the connector maker's part sold by the panel
   maker as three kits (150325, 150326, 152799) that differ only in the contacts and the wire
   they take, so the housing is one part and the kit is the wire it carries. It lives in the
   panel vendor's namespace, beside the receptacle, because it is one vendor's connector and
   no other part in the library takes it.
4. **Drawn from the wire side, one 30 mm stub per pole**, exactly as the screw-clamp plugs
   (sections 2 and 7): points `wire-1` (BATT) and `wire-2` (RTN), and the fields `wire-od`,
   `wire-color` and `body-color`. The default wire is 8.0, the largest insulation the housing
   takes; no held document states the wire the panels are meant for beyond 14 to 6 AWG.

### 14.2 Sources

| part | source | what it gives |
|---|---|---|
| plug | Amphenol customer drawing PRM SERIES FEMALE, PLUG SIDE 4MM, rev A1, 4 JAN 20 | 9.7 wide and 34.2 high across the latch arms (end view), 35.1 long (side view), 8 mm maximum insulation, contact and kit numbers, BATT and RTN engraved |
| receptacle | 300CB08 installation guide 149722-2 A9, Fig. 3-8 and 3-10, at 2.85 px/mm | the 10.5 by 29.8 frame, two cavities 11.0 apart, BATT over RTN (#831) |
| colour | the connector kit photographs on the vendor's product pages | a black housing |

The drawing is marked SCALE NONE, so everything inside the plug's outline is a fraction of a
dimension the same view prints (the 34.2 on the end view, the 35.1 on the side view).

### 14.3 The seated depth, and what is estimated

**No document draws the plug mated.** The side view puts two contact noses 12.8 in front of
the housing with the latch hooks at their roots; the plug is taken to seat with its housing
on the mouth of the receptacle's shroud, so 35.1 - 12.8 = 22.3 of it stands in front of
that mouth, and its outer face is 28.3 from the panel. Both the 12.8 and the shroud's 6.0
are estimates, and the 12.8 is the figure to revisit against a mated drawing.

**The two drawings disagree on the pole pitch.** The plug's contacts are 9.8 apart on its
maker's drawing; the receptacle's cavities, scaled off the coarse panel drawing, are 11.0
apart. The plug's figure is the better one; the two are aligned on their mid points, so each
contact is drawn 0.6 off its cavity, and the receptacle is not redrawn here.

Also estimated: the floor of each wire opening (1.5 below the wire-side face), the housing
height between the latch arms (26.2) and the press tabs (6.8 by 4.0). The latch arms' flare,
the engraving and the moulded maker's name are not built.

### 14.4 What is not covered

- **A seated plug by default.** The panels ship without plugs; nothing seats one.
- **A wire colour per pole.** The industry habit of a red BATT and a black RTN is stated by
  no held source, and one field paints both stubs.
- **The DCIM side.** `amphenol-ns/output-p40` is a power outlet in the exports (#806); being a
  slot changes nothing there.

`spec/tests/test_p40_plug.py` holds the interface, the receptacle's mate and unchanged
drawing, a census of every part presenting or mating `p40` and every placement of the
receptacle, the plug's size, fields, poles and relief, and the plug seated in two real
panels: mate on mate, the slot offering exactly the plug, the stand-off, and every solid
right side out.

## Decisions taken

- 2026-10-05: the three pluggable terminal headers are connector slots; each gains its
  interface and mate point and nothing else.
- 2026-10-06: one five-position interface, `terminal-508-5`; a flange is not part of it.
- 2026-10-05: generic screw-clamp plugs with in-line wire entry, drawn from the wire side,
  one 30 mm stub of wire per pole.
- 2026-10-05: each plug stands 10 in front of the face its header presents, and records
  what its header models.
- 2026-10-06: the default wire is 3.0 mm.
- 2026-10-06: the DC barrel jack is one nominal connector, `dc-barrel`; its voltage and
  current are attributes of each placement.
- 2026-10-06: a screw or stud terminal a lug lands on is one nominal connector,
  `terminal-stud`; the terminal screw is the part that presents it, one per pole.
- 2026-10-06: the ring lug has no `wire-od` field; a wire in the plane of the face cannot
  take a size field yet.
- 2026-10-06: the lug lies on the head of its host's screw, above the lips of the block,
  and no block's shape is changed.
- 2026-10-06: the Nokia 7750 SR-1 terminal block waits for a two-hole lug.
- 2026-10-06: a ground stud is a `terminal-stud` seat; the lug lands on top of what the
  part builds.
- 2026-10-06: all three studs of the Casa C40G terminal are seats.
- 2026-10-06: `stud-size` is a text attribute of a placement, written only where a
  document for that device states it.
- 2026-10-06: no lug is turned and no ground part is redrawn; the overlaps and overhangs
  that result are recorded.
- 2026-10-07: a configuration turns a seated occupant with `turn:`, relative to the seat,
  one of the turns its host allows: the interface's `turns` narrowed by the presented
  point's. `terminal-stud` allows the four right angles; a terminal screw allows 0 (#829).
- 2026-10-07: where none is stated, the default is rule B, "may leave the face": down,
  the nearer side, the other side, up - the first that crosses no part, bay or other
  seat - with legends a soft preference, published as `seat-turns`; a share link
  carries a turn in its own `turn=` parameter (#829).
- 2026-10-07: the P40 receptacle presents a vendor interface, `p40`, citing no standard,
  and gains its mate point and nothing else.
- 2026-10-07: the two-position AurCore header is 12.16 wide and placed turned 90, as the
  five-position one beside it is; its height is left for #873 (#804).
- 2026-10-07: one P40 plug, `amphenol-ns/p40-plug@1`, drawn from the wire side with a stub
  per pole; it seats 22.3 in front of the receptacle's shroud, an estimate.

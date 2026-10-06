# Connectors: pluggable terminal headers and the DC barrel jack

Status: implemented, 2026-10-06. Issue #789, first and second parts. Builds on
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
| `common/terminal-header-508-2@1` | port | the relay output of the same 10 |
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
| `common/terminal-header-508-2@1` | the same | the same | 8.2 | 6.5 too shallow |
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
  placed. For the two-position one the same video shows the keyed, open side toward the
  RELAY legend with the two contacts side by side along it, but the header is placed
  unturned on those devices, with the legend at its right. As placed, the tower of a
  seated plug is therefore not toward the legend. The header is a quarter turn out (#804);
  when it is turned the plug follows.
- **Poles.** `wire-1` is at the left of the unrotated header. The two AurCore headers
  name their contacts `cell-1` and `pin-1` onward from the left and the wires follow them.
  The six-position header names none, so left to right is a convention there. Pole names
  (`+`, `-`, earth, `-48V`) are printed on the panel beside each header, differ by device,
  and are not on the plug.
- A seat applies the header's turn to the plug. The flanged header is placed turned 90 on
  every AurCore device and the plug follows it.

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
  switches the tower overhangs the POWER legend.

## 8. Out of scope

- Parts drawn with their plug already seated: `common/dc-terminal-plug-2@1` and the two
  Telco Systems DC plugs.
- Any change to a header's or the jack's geometry, including the depths sections 5 and 9
  question, the two-position header's 10.16 width and the way the two-position header is
  turned on the AurCore top face (#804).
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

The second part of #789 is the fixed terminals. The barrier blocks are section 12. Ground
studs and the terminals drawn inside DC power supplies follow.

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

**A configuration cannot turn an occupant on its own.** `occupants:` carries a ref, an
id, attrs and a skin; a seat applies its host's turn and nothing else. That is right for
a barrier block and is a limit for a ground stud, where the direction of the lug is the
installer's choice.

### 12.7 Limits, and what is not covered

- **No two-hole lug.** `nokia/sr-1-dc-terminal-block@1` is not touched. The 7750 SR-1
  chassis installation guide (3HE22130AAAATQZZA01, release 25.10) calls for a Panduit
  LCD6-10AH-L two-hole, 45-degree lug on #6 AWG wire across each pair of 10-32 studs
  (Table 58, Table 59 and Figure 50: hole 0.27 in, spacing 0.63 in). A one-hole lug on
  each stud would put two lugs on one terminal, overlapping. That block waits for a lug
  that spans a pair.
- **Ground landings are not covered:** `common/ground-lug@1`, `common/ground-stud@1` and
  the vendor ground studs and pads.
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

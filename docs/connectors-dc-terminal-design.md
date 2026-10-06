# Connectors: pluggable terminal headers

Status: implemented, 2026-10-05. Issue #789, first part. Builds on
[pluggables-caps-design.md](pluggables-caps-design.md) (a presented connector interface is
a SLOT that offers every part whose `mates:` names it) and follows
[connectors-usb-design.md](connectors-usb-design.md): a registry entry per interface and a
generic plug per interface. It differs in one thing. A terminal plug carries one wire per
pole, not one cable.

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
   `terminal-508-2`, `terminal-508-5f` and `terminal-508-6`. The pitch and the number of
   positions are in the key. A header that feeds power and one that carries a relay
   contact are the same interface when they are the same header.
2. **The flanged header is an interface of its own.** The data sheet of the flanged
   five-position header lists seventeen mating plugs and every one has screw flanges; the
   data sheet of the plain header lists plain plugs and no flanged one. No held drawing
   shows a plain plug in a flanged header, so `f` is part of the key. A plain five-position
   header, when the library draws one, is a different interface.
3. **Each header gains its interface and a `mate` point** at the middle of its row of
   contacts. Drawings, sizes, classes and attrs are unchanged. Each is a contract change:
   the three headers take a patch and so does each of the 11 devices that draw one.
4. **Three generic plugs:** `generic/terminal-508-2-plug@1`,
   `generic/terminal-508-5f-plug@1` and `generic/terminal-508-6-plug@1`. Each is
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
   `body-color` paints the body and the flanges. The default body is the green the AurCore
   headers are drawn in.
9. **A plug's `media` is `terminal-block`** on all three. The two-position header states
   that key. The other two headers state `dc-terminal`, which a `class: port` plug cannot:
   lint L62 reads a port part's media as a connector word, and `dc` as a connector word
   flags every `dc-in` placement id in the library. The kit labels both keys.

## 3. The slots

Every header is placed directly on a chassis face, so each is a slot in the device view's
`cages[]`, keyed by the placement: 10 `terminal-508-5f`, 10 `terminal-508-2` and 2
`terminal-508-6`. No component composes a header. Each slot offers exactly one part.

## 4. Sources

| part | source | what it prints |
|---|---|---|
| plain plug, 2 and 6 positions | Phoenix Contact MSTB 2,5/ 2-ST-5,08 (1757019) and MSTB 2,5/ 6-ST-5,08 (1757051) data sheets, 28.01.2005, p.4 | a + 5.08 wide, 15 high, 18.2 long, nose 8.3, first pole 2.54 from the end; a is 5.08 and 25.4 (p.1) |
| | the same, pp.1-2 | clamp screw M3; conductor 0.2 to 2.5 mm2, AWG 24 to 12; nominal 2.5 mm2; stripping length 7 |
| flanged plug | Phoenix Contact MSTB 2,5/16-STF-5,08 (1778124) data sheet, p.7, the drawing of the MSTB 2,5/..-STF range | body a + 5.69 wide, a flange 4.7 each end, 15 high, 18.2 long, nose 8.3, flange screw 5.08 outside the end pole |
| plain header, with a plug seated | Phoenix Contact MSTBA 2,5/ 6-G-5,08 (1757284) data sheet, p.5 | header a + 7.08 wide, 8.6 high, 12 long; 22 from the back of the header to the back of a seated plug; plug 15 high, underside level with the header's |
| flanged header | Phoenix Contact MSTB 2,5/ 5-GF-5,08 (1776537) data sheet, Sep 27, 2023, p.3 and pp.16-25 | 35.56 wide, 12.1 high, 12 long; seventeen mating plugs, all flanged; MSTB 2,5/ 5-STF-5,08 (1778014) on p.18 |
| wire | Waskoenig+Walter H07V-K data sheet, status 05.10.2026, p.2 | outside diameter approximately 4 for 2.5 mm2 and 3 for 1.5 mm2 |

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
  seated plug is therefore not toward the legend. That is the placement's to revisit; when
  the header is turned the plug follows.
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
- **Every pole is drawn wired, in one colour.** An unwired pole and a colour per pole are
  not expressible: a field per pole would be six fields on the longest plug here.
- **The plug covers the header's legend where the real one does.** On the AurCore
  switches the tower overhangs the POWER legend.

## 8. Out of scope

- **The DC barrel jack.** `common/dc-barrel@1` is placed on four devices and no document
  held for any of them states the size of its jack. It is unchanged and has no plug.
- Parts drawn with their plug already seated: `common/dc-terminal-plug-2@1` and the two
  Telco Systems DC plugs.
- Any change to a header's geometry, including the depths section 5 questions, the
  two-position header's 10.16 width and the way the two-position header is turned on the
  AurCore top face.
- Plugs with angled wire entry, spring-clamp plugs and cable housings.
- Devices ship bare. A plug is in a slot's accept list because it mates the slot's
  interface; nothing seats one by default.

## 9. What follows

The second part of #789 is the fixed terminals: barrier blocks and ground studs. Those
take a lug per pole, not a plug, so the slot there is the pole and the part that seats is
a ring or fork lug on its wire.

## 10. Testing

`spec/tests/test_dc_terminal_plugs.py`, against the real library and builds made by the
test:

1. The registry holds the three interfaces, each citing a standard; the flanged header is
   keyed apart.
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

## Decisions taken

- 2026-10-05: the three pluggable terminal headers are connector slots; each gains its
  interface and mate point and nothing else.
- 2026-10-05: the flanged header is an interface of its own.
- 2026-10-05: generic screw-clamp plugs with in-line wire entry, drawn from the wire side,
  one 30 mm stub of wire per pole.
- 2026-10-05: each plug stands 10 in front of the face its header presents, and records
  what its header models.
- 2026-10-05: the DC barrel jack is left as it is until a source states its size.

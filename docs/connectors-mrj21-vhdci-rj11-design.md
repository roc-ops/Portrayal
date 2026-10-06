# Connectors: MRJ21, VHDCI and RJ11

Status: implemented, 2026-10-06. Issue #790. Follows
[connectors-usb-design.md](connectors-usb-design.md) and
[connectors-dsub-design.md](connectors-dsub-design.md) part for part: a registry entry per
interface, a generic cable plug per interface, and a cable stub whose diameter is a field.

## 1. What existed

| part | size | placed on |
|---|---|---|
| `std/mrj21@1` | 28.92 x 13.45 | `nokia/m48-1gb-xp-tx@1`, eight to the card, each turned 270 |
| `common/vhdci-receptacle@1` | 40.4 x 5.2 | `oscilloquartz/btoh-16@1`, `cpoh-16@1` and `ptoh-16@1`, one each |
| `common/rj11-jack@1` | 14.0 x 13.5 | `halny/hlx-tgv`, twice, both turned 180 |

None of the three interfaces was in `spec/schemas/connectors.yaml`, so no jack published a
slot. The VHDCI and RJ11 parts stated no interface. There was no cable plug.

## 2. What each jack is

- **MRJ21.** The installation guide of the card calls them mini RJ21 connectors, six
  10/100/1000 ports each, and draws its two breakout cables (to six RJ45 plugs, and to an
  RJ21) with a straight plug: a rectangular backshell, a jackscrew at two opposite corners
  and a ribbed boot in line. That is the TE Connectivity MRJ21 48-position connector.
- **VHDCI.** The Oscilloquartz documents call the connector high density and VHDCI and
  state no position count. The receptacle as measured off the card image agrees with the
  one connector SFF-8441 standardizes, the 68-position: an opening 28.2 wide against 28.3,
  a shell 30.9 against 31.65 and screw centres 37.2 against 37.7. The manual names two high
  density cables by part number and shows neither.
- **RJ11.** The Halny guide calls both ports RJ-11 FXS. The jack is a six-position body,
  narrower than the RJ45 jacks beside it, with two contacts loaded (6P2C).

## 3. Decisions

1. **Three interfaces:** `mrj21`, `vhdci` and `rj11`. `mrj21` cites the standards entry its
   jack already conforms to; `vhdci` and `rj11` cite new entries that claim no envelope,
   because the two jacks are photo-measured `common/` parts and stay so.
2. **No count in the VHDCI key.** SFF-8441 standardizes only the 68-position connector, so
   no other count of it could be on a panel. The count is in the note.
3. **`rj11` is the six-position body,** whichever of its contacts are loaded. The
   four-position handset jack and the RJ45 are different interfaces.
4. **The two `common/` jacks gain `interface:`,** and the RJ11 jack a `mate` point at the
   centre of its opening. The VHDCI receptacle already had one, midway between its screw
   locks. No drawing, size or depth changes. Each takes a patch, as do the three
   Oscilloquartz cards and the five devices the lock check names.
5. **Three generic plugs:** `generic/mrj21-plug@1`, `generic/vhdci-plug@1` and
   `generic/rj11-plug@1`, each `class: port` with `mates:`, no `behaviour`, and a 30 mm
   stub of cable sized by `cable-od` and coloured by `jacket-color`.
6. **Straight exits.** All three cables leave along the mating axis, so each stub stands
   out of the face. The MRJ21 exit is the one the card guide draws. Nothing held draws the
   Oscilloquartz cable; the straight VHDCI exit rests on SFF-8441, which says the connector
   is small enough to do without right angle backshells, and on the one cable drawing held.
7. **The RJ11 plug follows `generic/rj45-plug@1`:** the same view, contacts at the top and
   the latch at the bottom, `size` as the body without the latch, and a `size.d`. It does
   not present a second interface for a boot, because no boot is modelled; it carries its
   own stub.
8. **A plug states the media key its jack states.** Lint L62 raised nothing. The kit labels
   the three keys as its fallback already read them.

## 4. Sources

| part | source | what it gives |
|---|---|---|
| MRJ21 plug | Bel Stewart Connector drawing CT210028 rev B0, sheet 1 | a vector face view and side view of the straight plug, no plug dimension; marked not to be scaled |
| | registry `mrj21` (TE customer view model C-1761482-4 rev G) | the two guide holes the jackscrews thread into, 22.88 and 7.20 apart |
| | Bel Stewart MRJ21 Cable Assemblies brochure; AMP NETCONNECT MRJ 21 Connector System sheet 1654775 rev. 8 | die-cast backshell, jackscrews, 180 and 45 degree exits, grey or white cable |
| VHDCI plug | SFF-8441 Rev 14.1, Figures 18, 25 and 27 | front shell 7.10 long, flange 35.08 x 5.80, screwlocks on 37.7 centres, mated gap 0.34, fixed shell 5.2 proud |
| | Cliff Electronic Components data sheet VHDCI Cable (08/2021 ISS.2) | a raster drawing of the hood with thumbscrews; cable OD 10.0, black; 5 mm screws |
| RJ11 plug | Multicomp drawing M10002356 rev A, sheets 1 and 2 | body 9.65 x 6.60 x 12.43, latch 2.77 below, cable entry 2.90 x 5.20 |
| RJ11 jack | TE customer drawing C-1775675 rev C | six-position housing 13.34 x 12.6 x 20.57, opening 9.88 |

**The MRJ21 plug is scaled throughout.** No dimensioned drawing of the plug is held: the
public documents found dimension the receptacle and not the plug. The Bel Stewart drawing is
scaled at 2.517 points a millimetre, fixed by the two jackscrew separations against the
receptacle guide holes (2.513 and 2.521), and checked by the backshell width, 28.99 against
the 28.92 of the receptacle shell.

**The VHDCI hood is scaled** from a 209 ppi raster at 3.34 pixels a millimetre, the scale
that puts its thumbscrews on the specified 37.7 centres; the front shell and the knob
diameter agree at that scale and the cable does not, so nothing is scaled from the cable.

## 5. The seated depth

| plug | seats by | starts | ends | stub ends | jack models |
|---|---|---|---|---|---|
| MRJ21 | backshell on the receptacle face; shroud 5.6 inside (scaled) | 0 | 93.5 | 123.5 | no depth |
| VHDCI | SFF-8441 mated gap 0.34 and front shell 7.10; hood from 7.44 | 0.34 | 55.44 | 85.44 | no depth |
| RJ11 | body 12.43 less an estimated 7.9 insertion | 0 | 4.5 | 34.5 | no depth |

None of the three jacks models a depth, so no modelled floor disagrees with a plug. What is
missing instead:

- `common/vhdci-receptacle@1` records that nothing it held gave how far its shell stands
  proud. SFF-8441 Figure 25 gives 5.2, with the screwlocks at 5.8.
- `common/rj11-jack@1` states no depth; the TE jack is 20.57 deep. It also draws its
  opening 11.6 wide, the width of an RJ45 opening, where the six-position opening is 9.88,
  so a seated plug shows about a millimetre of opening either side.
- No held document dimensions a mated MRJ21 pair, so that the backshell stops on the shell
  face is an assumption.

No jack geometry is changed here.

## 6. Which way round

- **MRJ21:** the two jackscrews are over the two guide holes of the receptacle, upper left
  and lower right unrotated. The card turns its connectors 270 and some chassis turn the
  card a further 90; the plug follows.
- **VHDCI:** nothing that keys the plug is visible from the cable end.
- **RJ11:** latch at the bottom unrotated, where the jack draws its keyway. The Halny jacks
  are fitted at 180, latch up.

## 7. What is estimated or simplified

- Every MRJ21 plug figure, the cable diameter (12.2) included. The boot is built as one
  cylinder at its widest rib and is assumed round.
- The VHDCI hood (43.4 x 9.0, a pixel is 0.3), its one-step taper, and the thickness of its
  strain relief. The stated 10.0 cable is thicker than the hood scales, so the stub
  overhangs the box by 0.5. A loop the cable drawing shows on one face of the hood is not
  drawn.
- The RJ11 insertion (7.9). A telephone cord is flat; the stub is a round one of the
  entry height, 2.9.
- Each thumbscrew and jackscrew is one cylinder; no slot is drawn.

## 8. Out of scope

- `common/esd-jack@1`.
- The far end of any cable, and breakout or fan-out cables as parts.
- The 45 degree MRJ21 backshell, offset and squeeze-latch VHDCI hoods, the four-position
  handset plug.
- Any change to a jack or a card geometry.

## 9. Testing

`spec/tests/test_small_connector_plugs.py`, against the real library and builds made by the
test: the registry; each jack presenting its interface; the nested slots of the Nokia MDA
and the three Oscilloquartz cards; a census of composed and placed jacks; each plug's
contract and skin; the solids chain; seats on the SR-7 and the SR-12 (two bays down, flat
and turned), two OSA chassis and the Halny; the seated depth; `cable-od` from a placement;
and the kit's own slot walk and seat under node for two nested seats.

## Decisions taken

- 2026-10-06: `mrj21`, `vhdci` and `rj11` are connector slots; the two `common/` jacks gain
  their interface and nothing else.
- 2026-10-06: generic straight cable plugs for the three, each with a 30 mm stub sized by
  `cable-od`.
- 2026-10-06: the RJ11 plug follows the RJ45 plug's shape and carries its own stub.

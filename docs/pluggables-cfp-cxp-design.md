# Pluggables: generic optics for the CFP, CFP2, CFP4 and CXP cages

Status: built 2026-10-05. Eight generic optics, one thumbscrew, one module
receptacle and four module envelopes, each on a pattern the library already
had. Part of [pluggables-design.md](pluggables-design.md); uses the head of
[pluggables-heads-design.md](pluggables-heads-design.md), the connector slot
of [pluggables-caps-design.md](pluggables-caps-design.md) and the module-side
MPO receptacle of
[pluggables-mpo-bidi-pon-design.md](pluggables-mpo-bidi-pon-design.md). It
follows [pluggables-osfp-xfp-design.md](pluggables-osfp-xfp-design.md) and is
built the same way.

Before this, a CFP, CFP2, CFP4 or CXP cage offered nothing: no part stated
`mates:` any of the four. No device places one of these cages directly; all
of them are on cards.

## The parts

| part | what it is | its slots offer |
|---|---|---|
| `generic/cfp-lc@1` | a CFP with two LC bores (`std/lc-bore@3`), latch up, transmit left, and a thumbscrew at each end of the faceplate | `generic/lc-plug@2`, `common/lc-dust-cap@1`, per bore |
| `generic/cfp-sc@1` | a CFP with two SC openings (`std/sc-bore@1`) side by side, key slot up, transmit left, and the same two thumbscrews | `generic/sc-plug@1`, `common/sc-dust-cap@1`, per opening |
| `generic/cfp-mpo@1` | a CFP with one two-row MPO receptacle (`std/mpo24-module-receptacle@1`), key up, pinned | `generic/mpo24-plug@1`, `generic/mpo12-plug@1`, `common/mpo-dust-cap@2` |
| `generic/cfp2-lc@1` | a CFP2 with two LC bores and a bail across the top of its head | as `cfp-lc` |
| `generic/cfp2-mpo@1` | a CFP2 with one two-row MPO receptacle and the same bail | as `cfp-mpo` |
| `generic/cfp4-lc@1` | a CFP4 with two LC bores and a bail | as `cfp-lc` |
| `generic/cfp4-mpo@1` | a CFP4 with one MPO receptacle of twelve positions (`std/mpo-module-receptacle@1`) | as `cfp-mpo` |
| `generic/cxp-mpo@1` | an optical CXP with one two-row MPO receptacle and a pull tab loop | as `cfp-mpo` |
| `common/cfp-thumbscrew@1` | the knurled knob the three CFP parts compose twice | - |
| `std/mpo24-module-receptacle@1` | the MPO mouth on a module with a two-row ferrule: twenty-four fibre positions | what `std/mpo@2` offers |
| `cfp-module`, `cfp2-module`, `cfp4-module`, `cxp-module` | the module envelopes in `spec/schemas/standards.yaml`, each with a `head:` | - |

Each generic is named by form and face and states no rate, reach, wavelength
or wattage (L99). A plug seated in an MPO optic is keyed `<cage>-occupant`;
in a duplex LC or SC optic, `<cage>-occupant/tx` and `<cage>-occupant/rx`.

## Where the head envelope lives

On the module entry the optic conforms to. No cage contract and no cage
registry entry changed in this work; #802 later redrew the four cages as their
panel openings (below).

| entry | w | h | depth | head: w-max | above | below | length |
|---|---|---|---|---|---|---|---|
| `cfp-module` | 77.20 | 13.60 | 130.25 | 82.0 | 0.2 | 0.2 | 14.5 |
| `cfp2-module` | 41.5 | 12.4 | 91.5 | 42.5 | 3.4 | 1.6 | 20.1 |
| `cfp4-module` | 21.5 | 9.5 | 76.0 | 22.1 | 3.4 | 1.6 | 20.1 |
| `cxp-module` | 21.20 | 9.81 | 28.45 | 24.05 | 4.79 | 1.61 | 33.55 |

Each depth is the length behind the head, and each closes against the
overall length its document gives: 130.25 + 14.5 is the 144.75 of a CFP,
91.5 + 16.0 the 107.50 of a CFP2, 76.0 + 16.0 the 92.00 of a CFP4, and 28.45
+ 33.55 the 62.00 of a CXP plug. The CFP2 and CFP4 lengths are the 16.0
enlarged section plus the 4.10 the connector receptacle may stand in front
of it. The CFP head figures are nominal figures with tolerances, not maxima;
only its 14.5 length is printed as a maximum.

## Sources

No vendor document is committed. Each contract cites its own figures; this is
the list. The CFP MSA's own site no longer serves its documents; they were
read from a public web archive of it.

| part | sources |
|---|---|
| `cfp-module`, the three CFP optics, `cfp-thumbscrew` | CFP MSA Hardware Specification Rev 1.4 (7 June 2010): sections 5.3 and 5.6, Tables 5-2 and 5-3, Figures 5-16 and 5-17; the MSA Module Dimensions drawing it defers to (CFP MODULE, 04/07/10), keys A1 to LL1; CFP MSA Mechanical Layout, 17 Mar 10, revision 14, Figures 19 and 25 |
| `cfp-lc` | Gigalight GCF-S101-LR4C datasheet (2017/2/8) p11; Modulelink CFP-100G-LR4 datasheet pp16-19, Figure 10 and Table 14; Cisco 100GBASE CFP Modules Data Sheet C78-633027 (the SC duplex form) |
| `cfp-sc` | the end view of the MSA Module Dimensions drawing (04/07/10); CFP MSA Hardware Specification Rev 1.4 Figure 5-16 and Table 5-3; Cisco 100GBASE CFP Modules Data Sheet C78-633027 pp3-6 (photographs and the connector statement). No dimensioned vendor outline of an SC duplex CFP is held |
| `cfp-mpo` | Gigalight GCF-M101-SR10C datasheet p8 Figure 4 and p9 Figure 5 (the FS CFP-SR10-100G datasheet p12 embeds the same drawing) |
| `cfp2-module`, both CFP2 optics | CFP MSA CFP2 Hardware Specification Rev 1.0 (31 July 2013): sections 5.3 and 5.6, Figure 5-10; CFP2 Baseline Drawing Rev 1L (2013-08-06), sheets 1 to 3, 13 and 14 |
| `cfp2-lc` | Finisar FTLC1122RDNL Product Specification Rev C1 (20-Oct-2017) p8; Gigalight GF2-S101-LR4C datasheet Rev V3 p12 Figure 9 |
| `cfp2-mpo` | Fibermall CFP2-100G-SR10 datasheet Rev 1.1 p11; Gigalight GF2-M101-SR10C datasheet p7 Figure 3 and p8 |
| `cfp4-module`, both CFP4 optics | CFP MSA CFP4 Hardware Specification Rev 1.1 (18 March 2015): sections 5.3 and 5.6; CFP4 Baseline Drawing Rev R, sheets 1 to 3 and 14 to 16 |
| `cfp4-lc` | Finisar FTLC1141RDNL Product Specification Rev C1 (20-June-2016) p8; FS CFP4-LR4-100G datasheet p13; Gigalight GF4-S101-LR4C datasheet Rev V0 p10; 10Gtek TR-KC13L-N00 datasheet p12 (the pull-tab variant) |
| `cfp4-mpo` | Gigalight GF4-M101-SR4C datasheet p6 Figure 3 and p13 Figure 6 |
| `cxp-module`, `cxp-mpo` | SFF-8642 Rev 3.3 (2018-08-31): Figures 5-2 to 5-6, Tables 5-2, 5-3, 5-7 and 5-8; SFF-8617 Rev 1.7 and SFF-8647 Rev 1.5, which defers to it; Finisar FTLD12CL3C Product Specification Rev C1 (31-Oct-16) p10 (the FTLD10CE3C specification Rev B4 embeds the same drawing); Cisco 100GBASE CXP Modules Data Sheet C78-734364 |
| `mpo24-module-receptacle` | the sources of `std/mpo-module-receptacle@1`; US Conec handout SM-0022-0823 p1 (0.50 between rows); Gigalight GCF-M101-SR10C p8 Figure 4 (which fibre is where, looking in) |

## What is drawn from a callout and what is not

| part | from a printed or toleranced figure | scaled or estimated |
|---|---|---|
| CFP optics | body; faceplate 82.00 x 14.00 x 14.50 MAX; thumbscrew axes 72.00 apart at the body mid-height; knob 9.50 long; 6.25 pitch; latch up; transmit left; key up | the optical axis height, 6.8 (scaled off one vendor end view, and where the MSA drawing puts its SC openings); the MPO insert (borrowed) |
| `cfp-sc` | body, faceplate and thumbscrews as the other CFP optics; transmit left (lettered on Figure 5-16 and on the vendor photograph) | everything about the openings: 9.0 across by 7.5 up and 12.7 apart (scaled off the MSA drawing: 9.07, 7.55, 12.7), key slot up (the same drawing and one photograph), on the thumbscrew centreline (scaled) |
| `cfp-thumbscrew` | length 9.50; knurled | diameter 9.2 (scaled off the MSA drawing, two views, about +/-0.2) |
| CFP2 optics | body; head 42.5 MAX wide and 16.0 long (the MSA limits); 2.70 above and 1.60 below (one vendor, printed); LC axis 6.79 below the top (one vendor, a reference dimension); 6.25 pitch; latch up; transmit left; key up; pinned; the 14.80 x 9.80 MPO block | the MPO receptacle height (estimated, the LC axis); the bail bar, 1.9 tall (scaled); the bail arms and pivot are not drawn |
| CFP4 optics | body; head 21.90 wide, 3.1 above and 1.5 below (one vendor, printed), 16.0 long (the MSA limit); LC axis 4.95 below the top (one vendor, a reference dimension); 6.25 pitch; latch up; transmit left; key up | the MPO receptacle height (estimated, the LC axis); the MPO insert (borrowed); the bail bar, 1.1 tall (scaled) |
| `cxp-mpo` | snout; body 23.9 wide and 14.0 high (one vendor, printed); 1.61 below the snout (the SFF-8642 limit); 33.55 long (62.00 Ref less 28.45); tab tip 82.2 from the bezel plane, loop 19.7 wide with a 13.5 opening (one vendor, printed) | the receptacle height, 4.6 (scaled, about +/-0.3); the key direction (estimated: no drawing cited shows it); the insert (borrowed); the tab's 1.5 thickness and 3.1 end bar; its S-bend is not drawn |
| `mpo24-module-receptacle` | everything `std/mpo-module-receptacle@1` has from a callout; 0.25 pitch | 0.50 between the rows (printed for the sixteen-fibre family's two-row ferrule, borrowed for this one) |

## Where a vendor and the MSA disagree

- **Which connector a duplex CFP carries.** The CFP MSA lists SC, LC and MPO,
  its module drawing draws an SC duplex (two 7.5 x 9.0 openings 12.7 apart),
  and one vendor's long-reach CFP is SC. Two other vendors draw a duplex LC.
  Both are real products and both are built: `generic/cfp-sc@1` and
  `generic/cfp-lc@1`.
- **CFP thumbscrew.** The MSA prints the knob 9.50 +/-0.50 long and no
  diameter. One vendor prints 10.00 across and 15.50 long, another 14.00
  long. The MSA length is drawn, with the diameter its own drawing scales.
- **CFP optical axis height.** The MSA leaves it to the manufacturer. One
  vendor draws the LC pair on the thumbscrew centreline, 6.8 below the module
  top; another scales about 8.5 below it, in a housing standing 3.9 in front
  of the faceplate. The first is drawn.
- **CFP2 head.** The MSA allows 3.40 above the module top and offers 2.50 as
  a low-profile option. One vendor prints 2.70, one 2.50 MAX, and one a head
  only 1.2 taller than the body, with its bail along the bottom edge and not
  the top. 2.70 and a bail across the top are drawn. The head length is the
  MSA's 16.0; vendors print 15.70 and 10.30.
- **CFP2 LC axis.** One vendor prints (5.61) above the module bottom; another
  scales about 4.3. The MSA allows 5.90 +/-1.50. 5.61 is drawn.
- **CFP4 head.** One vendor prints 14.1 high with 1.5 below; another prints
  13.5; a third only the 3.40 and 1.60 limits. The first is drawn. The head
  length is the MSA's 16.0; one vendor prints 13.0.
- **CFP4 actuator.** Three vendors draw a bail. One draws a long pull tab.
  The bail is drawn.
- **CXP length.** SFF-8642 gives the plug 62.00 Ref overall. The one vendor
  drawing cited prints 62.3. The reference length is drawn.
- **CXP pull tab.** SFF-8642 draws, as an example on a cable plug, a narrow
  strap to a ring. The vendor draws a moulded loop the width of the ring.
  The vendor is drawn, flat.

## Known gaps

- **The cages were the module, not the opening (closed by #802).** The
  first majors of the four cages drew a module envelope: `std/cfp` the
  faceplate width on the body height, `std/cxp` an estimate SFF-8642 does not
  bear out, `std/cfp2` and `std/cfp4` the module bodies. Their second majors
  draw the panel opening each document prints, as `std/sfp@1` and
  `std/qsfp28@1` do: CFP 82.8 x 14.8 (Mechanical Layout Figure 25), CXP
  23.50 x 12.10 (SFF-8642 Table 5-7), CFP2 14.30 high (Baseline Drawing sheet
  13) at the 41.50 body width, CFP4 11.30 high (sheet 14) at the 22.10
  faceplate width. Their depth is the bezel to the connector (28.96 printed
  for CXP; 126.15, 87.5 and 67.9 derived for the CFP family, each estimated)
  and their cavity the module body or, for CXP, the snout opening. A seated
  optic is still centred on the cage's mate point and its head and plugs
  stand where they did; only the cage around it changed. The CFP cage face
  still stands for the front of the MSA's external bracket, which is not
  drawn.
- **The receptacle nose of a CFP2 or CFP4 is not drawn.** The MSA lets the
  connector receptacle stand up to 4.10 in front of the head; vendors print
  3.6 to 4.10. The bores and the MPO mouth are on the head front.
- **The MPO key on a CXP is an estimate.** The one vendor end view cited is
  too coarse to read it.
- **The SC face of a CFP has no dimensioned source.** Its openings are
  scaled off the MSA module drawing, which is vector and dimensions neither,
  and its key direction rests on that drawing and one photograph.
- **One vendor each for the MPO faces of CFP and CFP4.** The second CFP sheet
  held embeds the first one's drawing, and the second CFP4 sheet embeds an LC
  outline.
- **No twenty-four-fibre CFP4.** The MSA lists MTP24 for CFP4; no drawing of
  one is held.
- **A twelve-fibre plug is offered to a two-row receptacle.** The accept list
  is the interface's, and `mpo` is the housing and its centred key. The plug
  enters and latches; its one row lies between the two rows of the ferrule.
- **The one turned CFP4 cage in the library ends up upright.** It is turned
  90 on a card that sits in a bay turned 270.
- **Out of this work:** CFP8; CFP2-DCO and CFP2-ACO as parts of their own (a
  coherent CFP2 with a duplex LC is `generic/cfp2-lc@1`); CXP cable ends;
  SFP-DD optics.

## Decisions

- 2026-10-05: the head of a CFP is its faceplate, 14.5 long, and the cage
  face stands for the front of the host bracket. The thumbscrew knobs stand
  on it and are not part of it.
- 2026-10-05: the CFP thumbscrew is a `common/` part, because the CFP optics
  all compose it. The CFP2 and CFP4 bails and the CXP tab are nodes of each
  optic's own skin: nothing else composes them, and a relief feature that
  starts at the head front is outside what L121 holds to the head.
- 2026-10-05: the SC duplex CFP is one part, key slot up. Unlike the SC SFP,
  where two vendors draw the key on opposite sides and both parts exist, no
  source read draws a CFP keyed the other way.
- 2026-10-05: every knob, bail and tab colour defaults to the neutral grey.
  No document read for these four families codes a colour.
- 2026-10-05: a two-row module receptacle is its own part,
  `std/mpo24-module-receptacle@1`, on the `mpo` interface. A different
  ferrule under the same key is a separate part sharing the shell
  ([pluggables-design.md](pluggables-design.md), decision 10).
- 2026-10-05: the CFP2 and CFP4 head lengths are the MSA's 16.0 and not a
  vendor's shorter figure, so that the registry depth plus the head is the
  whole module.
- 2026-10-05: the `cfp`, `cfp2`, `cfp4` and `cxp` rungs of
  `spec/schemas/pluggables.yaml` name the documents they now rest on.
- 2026-10-07 (#802): the four cages are the panel openings, `d` the bezel
  to the connector, `relief.size` the module behind the opening, with the one
  1.0 collar. The CFP2 pitch floor is the 42.50 faceplate, because the
  baseline drawing seats two modules in one 86.35 opening; the CXP floor is
  SFF-8642's 27.00.
- 2026-10-05: no family with a placed cage is empty any more, so the test
  that an empty accept list is `[]` and not absent runs on a fixture: a real
  card's cage against the candidate pool with its family removed.

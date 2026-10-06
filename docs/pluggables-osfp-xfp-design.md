# Pluggables: generic optics for the OSFP and XFP cages

Status: built 2026-10-05. Three generic optics, one pull tab and two module
envelopes, each on a pattern the library already had. Part of
[pluggables-design.md](pluggables-design.md); uses the head of
[pluggables-heads-design.md](pluggables-heads-design.md), the connector slot
of [pluggables-caps-design.md](pluggables-caps-design.md) and the module-side
MPO-16 receptacle of
[pluggables-mpo-bidi-pon-design.md](pluggables-mpo-bidi-pon-design.md).

Before this, an OSFP or XFP cage offered nothing: no part stated `mates:
osfp` or `mates: xfp`.

## The parts

| part | what it is | its slots offer |
|---|---|---|
| `generic/osfp-mpo16@1` | an OSFP with one MPO-16 receptacle (`std/mpo16-module-receptacle@1`), key up, pinned | `generic/mpo16-plug@1`, `common/mpo16-dust-cap@1` |
| `generic/osfp-lc@1` | an OSFP with two LC bores (`std/lc-bore@3`), latch up, transmit left | `generic/lc-plug@2`, `common/lc-dust-cap@1`, per bore |
| `generic/xfp-lc@1` | an XFP with two LC bores, latch up, transmit left, and a bail across the top of its head | the same |
| `common/osfp-pull-tab@1` | the pull tab the two OSFP parts compose | - |
| `osfp-module`, `xfp-module` | the module envelopes in `spec/schemas/standards.yaml`, each with a `head:` | - |

Each generic is named by form and face and states no rate, reach, wavelength
or wattage (L99). A plug seated in the MPO-16 optic is keyed
`<cage>-occupant`; in a duplex LC optic, `<cage>-occupant/tx` and
`<cage>-occupant/rx`.

## Where the head envelope lives

On the module entry the optic conforms to, as for SFP, QSFP and QSFP-DD. No
cage contract changed. `std/xfp@1` keeps conforming to the `xfp` cage entry,
which gains nothing. `std/osfp@1` still states an interface and no
`conforms:`, and there is still no `osfp` cage entry: the OSFP MSA dimensions
a bezel cut-out (24.28 by 14.70 for a 1x1 cage) and a port (22.88 by 13.30
inside the EMI fingers), and `std/osfp@1` draws neither, so an entry would
either enshrine a vendor measurement as a standard or move 424 placed cages.
That is a decision for the cage, not for an optic.

| entry | w | h | depth | head: w-max | above | below | length |
|---|---|---|---|---|---|---|---|
| `osfp-module` | 22.58 | 13.00 | 79.01 | 22.93 | 0.0 | 1.6 | 21.39 Type 1, 37.39 Type 2 |
| `xfp-module` | 18.35 | 8.5 | 69.0 | 22.35 | 3.0 | 2.0 | 9.0 |

Both depths are the inserted length, derived from two printed figures each,
and both close against the overall length the MSA allows: 79.01 + 21.39 is
the 100.40 MAX of an OSFP, and 69.0 + 9.0 is the 78.0 an XFP comes to
(71.1 MAX to datum D plus 6.9 behind it).

## Sources

No vendor document is committed. Each contract cites its own figures; this is
the list.

| part | sources |
|---|---|
| `osfp-module`, both OSFP optics | OSFP MSA, OSFP Module Specification Rev 5.22 (2025-08-09): Figures 3-2 and 3-3 (body, outside envelope), 3-8 (rear end), 3-16 and 3-20 (heat sink), 5-6 and 8-4 (module in the cage), 14-27 (duplex LC) and 14-46 (MPO-16), section 3.8 Table 3-3 (colour code), Appendix B Figure B-1 (pull tab length) |
| `osfp-mpo16` | FS 400GBASE-SR8 OSFP datasheet p11 Figure 3 |
| `osfp-lc` | 6COM 6C-OSFP-400G-LR4 datasheet Rev 1.0 p15 |
| `osfp-pull-tab` | the same two vendor outlines, and Figure B-1 |
| `xfp-module`, `xfp-lc` | XFP MSA INF-8077i Rev 4.5 (2005-08-31): Figures 31 and 32, section 6.7 (colour code); Approved Networks XFP-LR data sheet REV 4.2 p3; FS 10GBASE-LR XFP datasheet p9 |

## What is drawn from a callout and what is not

| part | from a printed or toleranced figure | scaled or estimated |
|---|---|---|
| OSFP optics | body; nose 22.93 wide, 1.6 below, 21.39 long; nose top 3.8 down (the 9.20 reference height under the heat sink); ten 1.80 x 3.20 vents; heat sink front 1.39 out (21.39 less the 20.0 front envelope); key up, offset right; pinned; latch up; transmit left; 6.25 pitch | the MPO-16 receptacle height (estimated, mid-height of the nose); the LC ferrule height 8.7 (scaled off one vendor front view); the receptacle insert (borrowed) |
| `osfp-pull-tab` | reach 49.31 (139.1 to the stop, less 89.79) | width, 2.4 strap and arms, the 2.45 climb and where it happens, 7.8 grip (all scaled off one vendor raster, about +/-0.3) |
| `xfp-lc` | body; head 2.85 above and 0.80 below (one vendor, printed), 22.15 wide (the other vendor, printed), 9.0 long; 6.25 pitch; latch up; transmit left | ferrule height 4.25 (scaled); the bail bar (scaled, 1.3 tall, full width); the bail arms and pivot are not drawn |

## Where a vendor and the MSA disagree

- **OSFP, below the body.** FS prints 1.65 +/-0.1; the MSA limit is 1.60 MAX.
  1.6 is drawn.
- **OSFP pull tab.** The MSA figure draws a flat strap. Both vendor outlines
  raise the grip, by different paths, to about 1.5 below the module top. The
  vendors are drawn, because a grip at the height of the nose top would lie
  across the latch slots and the MPO key.
- **OSFP heat sink.** The MSA gives two example sections and allows others.
  The closed-top example is drawn. One vendor front view draws a much
  shallower grille.
- **XFP head height.** One vendor prints a 12.05 head and its split, the
  other prints 13 and no split. Both are inside the 13.5 the MSA allows. The
  one that prints the split is drawn.

## Known gaps

- **The lower row of a stacked OSFP column.** The devices that stack OSFP
  cages draw the lower cage at `rotate: 180`, on a row pitch of 14.5 to 14.9.
  A seated optic takes that turn, so the two noses of a column face each
  other and their 1.6 undersides overlap by about 1.3 to 1.7 in the drawing.
  The OSFP MSA draws its stacked 2x1 cages (14.9 pitch) with both modules the
  same way up, where the same 1.6 clears. The optic is drawn in the unrotated
  convention of the cage; whether those lower cages should be turned is a
  question about the devices.
- **No second vendor drawing of a duplex LC OSFP,** and no vendor end view
  of an MPO-16 OSFP. The MPO-16 receptacle height is an estimate.
- **`std/osfp@1` depth.** Its 47.0 is an estimate. The MSA puts the cage
  front 68.40 ahead of the forward stop and the bezel about 4 behind the
  cage front. Not changed here.
- **Out of this work:** OSFP-RHS, OSFP Type 2 and Type 3 fronts, the dual
  and multi-connector OSFP faces, OSFP MPO-12, OSFP copper and active
  cables, and the CFP, CFP2, CFP4 and CXP families, which followed in
  [pluggables-cfp-cxp-design.md](pluggables-cfp-cxp-design.md).

## Decisions

- 2026-10-05: the head of an OSFP optic is the nose, not the nose and the
  heat sink above it. The nose stands 21.39 out; the heat sink front stands
  1.39 out and is its own relief feature inside that length.
- 2026-10-05: every latch colour defaults to the neutral grey. The XFP MSA
  codes the colour by wavelength and the OSFP MSA by product type, and none
  of these three faces fixes either. The OSFP table also uses grey, for an
  active optical cable; the default is the library neutral and not that
  code.
- 2026-10-05: the XFP bail is a node of the optic skin, painted by
  `latch-color`, as on the SFP generics. It is not a `common/` part: nothing
  else composes it.
- 2026-10-05: the `osfp` and `xfp` rungs of `spec/schemas/pluggables.yaml`
  name the MSAs they now rest on.

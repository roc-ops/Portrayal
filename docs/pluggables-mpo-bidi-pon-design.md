# Pluggables: MPO, single-LC and SC faces, and the MPO-16 plug

Status: built 2026-10-04. Five generic optics, one plug and one pull handle,
each on a pattern the library already had. Part of [pluggables-design.md](pluggables-design.md);
uses the head of [pluggables-heads-design.md](pluggables-heads-design.md) and
the connector slot of [pluggables-caps-design.md](pluggables-caps-design.md).

## The parts

| part | what it is | copies | its slot offers |
|---|---|---|---|
| `generic/qsfp-mpo@1` | a QSFP with one MPO receptacle (`std/mpo@2`), key up, pinned | `generic/qsfp-lc@2` | `generic/mpo12-plug@1`, `generic/mpo24-plug@1`, `common/mpo-dust-cap@2` |
| `generic/qsfp-dd-mpo16@1` | a QSFP-DD with one MPO-16 receptacle (`std/mpo16@1`) in a Type 2 nose, with the Type 2 handle | `generic/qsfp-dd-lc@2` | `generic/mpo16-plug@1`, `common/mpo16-dust-cap@1` |
| `generic/qsfp-lc-simplex@1` | a QSFP with one LC bore in the left bay of a duplex-shaped shell | `generic/qsfp-lc@2`, `generic/sfp-lc-simplex@2` | `generic/lc-plug@2`, `common/lc-dust-cap@1` |
| `generic/sfp-sc@1` | an SFP with one SC opening, long axis horizontal, key slot down, and a bail | `generic/sfp-lc-simplex@2` | `generic/sc-plug@1`, `common/sc-dust-cap@1` |
| `generic/sfp-sc-key-up@1` | the same module with the SC key slot up | `generic/sfp-sc@1` | the same |
| `common/qsfp-dd-pull-tab-type2@1` | the pull handle of a Type 2 QSFP-DD module | `common/qsfp-pull-tab@2` | composed by `generic/qsfp-dd-mpo16@1` |
| `generic/mpo16-plug@1` | the sixteen-fibre MPO plug, key offset | `generic/mpo12-plug@1` | mates `mpo16`; seats in `std/mpo16@1` |

Each generic is named by form and face and states no rate, reach, wavelength
or wattage (L99). The faces they stand for are the parallel multimode QSFP,
the sixteen-fibre QSFP-DD, the single-fibre bidirectional QSFP and the PON
line-terminal SFP.

Each optic composes exactly one part that presents a connector interface, so
it forwards that part as its own slot (`presents` in `components.json`), the
way `generic/sfp-lc-simplex@2` presents its bore. A plug seated in an optic is
keyed `<cage>-occupant`.

## Sources

No vendor document is committed. Each contract cites its own figures; this is
the list.

| part | sources |
|---|---|
| `qsfp-mpo` | SFF-8661 Rev 2.5 Figure 5-1 (body, head envelope); SFF-8679 Rev 1.9 sections 7.2 (colour code), 7.3 and 7.3.1 (pinned, key up); SFF-8436 Rev 4.9 sections 5.1 and 5.5; FS QSFP28-SR4 datasheet p10; Gigalight GQS-MPO101-SR4C Rev V2 Figure 9; the maintainer's photographs of a QSFP28 SR4 module |
| `qsfp-dd-mpo16` | QSFP-DD HW Rev 6.3 sections 6.2.1 and 6.3, Figure 52; JPC 400G QSFP-DD SR8 datasheet p2 and p10; FluxLight QSFP-DD-400GBase-SR8 datasheet revision 21.04 p13; Gigalight GQD-MPO401-SR8CB Rev V2 Figure 6 (the two-row sibling) |
| `qsfp-lc-simplex` | ROBOfiber QSFP-10010-WA/WB datasheet Rev 1.1 p8 Figure 3; GBC Photonics QSFP28 BiDi 100GbE datasheet p4; Ascent Optics datasheet-381 p5 |
| `sfp-sc`, `sfp-sc-key-up` | Superxon DS00001553 V1.1 p10 Figure 8 and DS00001552 V1.1 p7 Figure 5; 6COM 6C-XGSPON-E1-OLT-SFP+ Rev 3.1 p8; SFF-8432 Rev 5.2a Table 4-3 |
| `qsfp-dd-pull-tab-type2` | JPC 400G QSFP-DD SR8 datasheet p2 (shape and reach); FluxLight QSFP-DD-400GBase-SR8 datasheet revision 21.04 p13 (reach only); QSFP-DD HW Rev 6.3 Appendix B |
| `mpo16-plug` | US Conec customer drawings C17864 rev H, C18012 rev F, C21364 rev C (sheet 2); US Conec MTP-16 handout SM-0022-0823 p1; SENKO DS-MPO-000001 Rev B p4 |

## What is drawn from a callout and what is not

| part | from a printed or toleranced figure | scaled, photo-measured or estimated |
|---|---|---|
| `qsfp-mpo` | body; key up; pinned; 20 MAX nose | nose 1.4 above and 1.4 below (photo-measured, carried from `generic/qsfp-lc@2`); receptacle centre (9.175, 4.5), photo-measured, +/-0.4, read by eye; the 13.1 x 9.4 black insert (photo-measured); the 12.9 x 8.0 mouth is the estimate `std/mpo@2` records; the beige hex |
| `qsfp-dd-mpo16` | body; nose 3.13 above, 1.5 below (JPC, toleranced); nose length 31.9 (JPC, 80.5 less 48.61); key up, offset right; pinned | receptacle position (estimated: centred, at body mid-height, scaled off the two-row sibling); the insert (borrowed from `qsfp-mpo`) |
| `qsfp-lc-simplex` | body; nose 2.2 above, 1.5 below; nose length 19.2 (72.00 less 52.80) | bore x 6.05 (scaled off an undimensioned end view, 6.07 +/-0.2); bore height (estimated, the duplex optical axis); which side (a projection reading on one sheet, the drawn bay on the other) |
| `sfp-sc`, `sfp-sc-key-up` | body; head 14 MAX wide, 2.1 MAX above, 1.4 below; length 20.0 (67.5 REF less 47.5) | the opening lying across (scaled); its centre (6.775, 3.7) (scaled); the key slot side (one vendor each, see below); every bail figure but its 8.4 width (scaled) |
| `qsfp-dd-pull-tab-type2` | width 18.35; reach 37.1 (117.6 less 80.5); top level with the nose top | arm width 2.25, post 10.0 tall and 6.8 long, dogleg to 12.5, strap 3.2 thick, grip plate 8.7 long (all scaled off the JPC raster, about +/-0.25) |
| `mpo16-plug` | 12.5 x 7.6; pin pitch 5.3; fibre pitch 0.25 | key 3.65 x 0.68, centre 1.12 off the centreline, and the 6.36 x 2.46 ferrule window (measured off vector line art marked for reference only); which long face carries the key (a convention argument); the 15.2 standoff (borrowed from `mpo12-plug`) |

## Known gaps

- **Neither MPO aperture draws its keyway or its pins.** `std/mpo@2` and
  `std/mpo16@1` are the estimated mouth with no key notch, and they draw the
  pale sleeve of a panel adapter. Key up is carried by the placement and by
  the plugs, and pinned is stated in prose. IEC 61754-7-1 Table 5 and
  TIA-604-18 would settle the mouth and the offset keyway.
- **The Type 2 handle's reach differs by vendor.** JPC prints a handle
  reaching 37.1 from the nose front on a 31.9 nose; FluxLight prints 35.06 on
  a nose that derives to 34.7. JPC is drawn, because its spans share one
  datum. The handle's shape is scaled off JPC's raster; its thumb pad, the
  arc of its grip plate and its ribbed neck are not drawn.
- **The SC key slot: two vendors, two directions.** The 6COM end view draws
  the slot at the bottom of the opening, above the bail bar. The Superxon
  end view draws a 2.1 notch above the opening, with the bail bar below.
  Both agree the bail bar is at the module bottom. So both exist:
  `generic/sfp-sc@1` is the 6COM reading (`rotate: 270`) and
  `generic/sfp-sc-key-up@1` the Superxon one (`rotate: 90`), and they differ
  in nothing else. A vendor wrapper composes the one its product is.
- **The empty bay of the single-LC face is painted,** not a cavity.
- **The receptacle position on a QSFP-DD nose** has no dimensioned source and
  no photograph.

## Build change

A host's own field default now reaches a part it composes when the two
defaults differ (`render._inherited_fields`). Before, only a value that was
set reached the part, so a host could not choose a default colour for a
composed tab without pinning it against every wrapper. A default equal to the
part's own is not handed down, so no drawing that agreed before changed.

## Decisions

- 2026-10-04: the MPO faces default `latch-color` to beige. SFF-8679 Rev 1.9
  section 7.2 and QSFP-DD HW Rev 6.3 section 6.3 code an exposed feature
  beige for 850 nm, and an MPO face on these two forms is the multimode
  parallel face. The single-LC and SC faces keep the neutral grey: their
  wavelengths differ by product, and by end of link.
- 2026-10-04: `generic/qsfp-lc@2` 2.2.1 corrects its `tab-colour` note, which
  said the QSFP documents carry no colour code. SFF-8661 carries none;
  SFF-8679 section 7.2 does. Provenance only.
- 2026-10-04: the QSFP-DD MPO-16 head is a Type 2 nose, because both drawings
  of that face show one. `generic/qsfp-dd-lc@2` stays Type 1.
- 2026-10-04: the MPO-16 plug conforms to a new `mpo16-plug` registry entry
  with the `mpo-plug` envelope. It is a separate entry because the key
  differs, and the key is the interface.
- 2026-10-04: the single LC bore of the QSFP sits in the duplex transmit
  position, on two vendors' end views.
- 2026-10-04: the SC key slot is built both ways, one part per vendor
  reading, because nothing held says which is general. Neither is a variant
  of the other in the contract: the receptacle's turn is the only difference.
- 2026-10-04: a Type 2 QSFP-DD module gets its own handle part,
  `common/qsfp-dd-pull-tab-type2@1`. The Type 1 handle on the Type 2 nose
  stood 12.7 too far out.

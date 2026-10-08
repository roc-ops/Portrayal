### Added
- `common/ground-screw-m4@1` (ISO 7045 M4 pan head, 8.0 across, 3.1 high) and
  `common/ground-stud-pair-5-8-m4@1`, two of them on 5/8 in. (15.875) centres
  presenting `stud-pair-5-8`, so a `generic/two-hole-lug-5-8@1` seats across an
  M4 grounding pair (#830).

### Changed
- UfiSpace grounding points are one M4 pair host where they were two
  `common/ground-lug@1` studs 11.0 or 13.0 apart (#830). The accessory lug is
  fixed with two M4 screws, and the guides' own flank figures read the holes
  15.6 to 15.9 apart, the 5/8 in. pattern; each landing is re-anchored where
  its own figure puts it, about 16.4 behind the front face. **Breaking for
  anything holding the old placement ids** `ground-1` and `ground-2`, now
  `ground-screws`; each device takes one major: M3000-14XC 4.0.0, S9500-22XST
  3.0.0, S9501-28SMT 4.0.0, S9502-16SMT 2.0.0, S9510-28DC 6.0.0 (its two
  stand-in cutouts are gone), S9510-30XC 4.0.0, S9511-20CT 3.0.0.
- UfiSpace S9601-104BC (4.0.0): the grounding lug is on the LEFT flank at its
  rear end, as HIG Figure 20, the vendor render and the boss on the rear
  elevation show, not on the rear strip. `ground-1`, the upper hole of a pair
  drawn on the rear, is gone with the pad behind it; `ground-screws` is one M4
  pair host on the left view, its depth estimated and a gap saying so (#830).
- Edgecore grounding plates drawn as one stud are their two screws (#830),
  still `common/ground-lug@1` because no pair host fits:
  - DCS500 (3.0.0): each plate is `ground-1` and `ground-1b`, `ground-0` and
    `ground-0b`, M5, 17.2 apart on the datasheet rear, which is no two-hole lug
    pattern; a gap records it;
  - EPS112 (2.0.0), EPS203 (2.0.0) and AGR560 (3.0.0): `ground` is now
    `ground-1` and `ground-2`, one above the other, 16.3, 16.2 and 16.1 apart as
    read off the rear photographs and datasheet elevations, unsized because no
    document names the screw. **Breaking for anything holding `ground`.**

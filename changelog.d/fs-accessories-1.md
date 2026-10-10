### Changed
- Lint L43 stands down when the body itself is as wide as the rack face
  (`chassis.width` at or above the generic ear's 480 mm threshold,
  `ears.EAR_WIDE`): a blanking plate's ears are built into its face, so the
  face is the part (decided 2026-10-09). A body narrower than that,
  drawn with a rack-wide front and nothing seated in its ears, still warns. No
  existing device changes; L43 had no hits in the library.

### Added
- FS.com blanking panels: FHU-BPS-1U-10, FHU-BPS-2U and FHU-BPS-4U (screw-on
  steel), FHU-BPSTL-1U-10, FHU-BPSTL-2U and FHU-BPSTL-4U (tool-less steel with
  ABS clips, the new `fs/bpstl-clip@1`), FHU-BPA-1U-10 (ABS, pegs and magnets)
  and FHU-BPAD-2U and FHU-BPAD-4U (ABS, wave-ribbed, snappable). Each is drawn
  as the whole plate, 482.6 mm (482 for the BPA), with its slots or clips.

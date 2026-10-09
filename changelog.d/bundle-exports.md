### Added
- `@portrayal/kit` 0.9.0: cable bundles in the exports (#923,
  `docs/cable-bundles-design.md` sections 7 and 13). `bundleExports(rack, ctx)`
  in `@portrayal/kit/rack/export-data` gives one record per bundle (number,
  label, members, length, strap count, size, bend, warnings), `bundleNotes`
  one line per bundle with its warnings, and `strapBomRows` the bill of
  materials' one hook-and-loop strap line, every bundle's straps summed.
  draw.io's notes say bundles are drawn there as separate cables.

### Changed
- The cable schedule has a `bundle` column straight after `route`, so
  `length_source`, `status` and `notes` move one place right, and its notes
  carry a line per bundle. NetBox's cables file names a member's bundle first
  in its description ("Bundle 2. uplink. Length measured along its route."),
  and its over-limit note now speaks of the whole description. Nautobot's
  cables file is unchanged; its notes list each bundle's cables.

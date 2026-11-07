### Added
- `smartoptics/dcp-rack-kit@1`, the rack-mount kit of the Smartoptics DCP chassis, and its seven
  parts: `dcp-front-bracket-600@1`, `dcp-front-bracket-700@1`, `dcp-bracket-extension-270@1`,
  `dcp-bracket-extension-470@1`, `dcp-rear-bracket-142@1`, `dcp-rear-bracket-42@1` and
  `dcp-mid-mount-bracket@1`. It is a telescoping kit with one four-post configuration for each of
  the seven rack-depth bands the user manual prints. Six bands print two figures and state a
  `depth` range, overlaps kept as printed. The first prints one figure, 600 mm, and states a
  `preset` with no `depth`, so the kit's `gaps` say its range is unknown. The two-post
  mid-mount part is in no band, because it has no rack depth. The two front brackets and the
  mid-mount bracket carry the protective ground terminal, composed from the library's ground stud.
  All seven parts are plain placeholder plates with estimated sizes.

### Changed
- `smartoptics/dcp-2` version 3.0.0 states its ears and its kit: `chassis.kits` lists the rack-mount
  kit as in-box, and `chassis.ears` gives the manual's four positions (chassis flush, transponder
  flush, recessed, and mid-mount in a two-post rack, which needs the kit's mid-mount part), with no
  distance because the manual prints none. The four placed `common/rack-ear@1` ears (`ear-left`,
  `ear-right`, `ear-left-r`, `ear-right-r`) are gone, so a viewer that asks for ears draws the
  generic bracket out to the rack face. A rack file or a page that names one of those four paths no
  longer finds it. The ground terminal gap is narrowed to what is left: the generic ear draws no
  stud. The default faces do not change.

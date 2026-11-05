### Added
- **Two Chatsworth two-post frames as rack products** (#1108): the Standard Rack
  `chatsworth/55053-x03` (45U, aluminium, 7 ft) and the SeismicFrame
  `chatsworth/13853-x03` (44U, welded steel, 19 in). Both are 19 in frames with
  tapped #12-24 holes, a front rail alone, and the outer box from the maker's
  data sheets. The 45U states its 1000 lb (453.6 kg) capacity as a static
  load, a reading the sheet does not spell out, so a `load-kind` gap says so.
  The SeismicFrame's rating is a seismic Zone 4 load under GR-63-CORE, not a
  static one: it is in the description and a gap, not in `load`. Where a sheet
  disagrees with itself (the 45U's capacity in kilograms on its two pages, the
  SeismicFrame's channel depth in millimetres) the figure the inches support is
  written and both are named in the product. The 23 in SeismicFrame, the 8 ft
  and 9 ft Standard Racks, the square-punched and painted-rail variants and the
  weights are not modelled; no weight is written as the sheets print only a
  shipping weight. Each product has a NetBox rack type and a Nautobot rack
  under `library/exports/*/rack-types/Chatsworth Products/`.

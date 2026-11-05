### Added
- Device42 spreadsheet files, a new format under `library/exports/device42/`: a
  hardware-model sheet (name, size in U, manufacturer) written from the NetBox
  device types, one row per model under the maker that built it, with a NOS
  vendor's relisting of a box left out, and a rack-side writer
  (`kit/rack/device42.js`) for the buildings, rooms, racks, devices and
  devices-to-racks sheets of a rack file. The column headers are the field
  names from Device42's import description and are not confirmed against its
  import page; the sheets are CSV, and ports, images and cables are not written.
  Mapping and open questions: `docs/device42-export-design.md`.

### Added
- `generic/nema-6-15p-plug@1` and `generic/nema-6-20p-plug@1`, the faces of the 250 V NEMA 6-15P and 6-20P
  plugs at the end of a cord, each with its `standards.yaml` entry. A device that places one exports a
  power port of type `other` labelled "NEMA 6-15P plug" or "NEMA 6-20P plug", as the L5-30P cord's does,
  because no target's power-port slug for either has been read from a source file. The body, the blade pitch
  and thickness, the earth pin and how far each stands proud are read from the Volex "Power Products
  catalogue" (Aug-2025), pages 164 and 166. The drawings are rasters, so the outline and the blade line's
  distance from the top are measured off the face view and stated as estimated in each part's provenance.
  No device places either part yet, so no device is re-locked and no export file changes. Closes no row:
  the NEMA L6-30P, BS 1363, AS/NZS 3112 and IEC 60309 plugs are not drawn yet, for want of a dimensioned
  drawing.

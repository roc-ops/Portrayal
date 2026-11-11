### Added
- `spec/tools/dev/layout_fit.py` counts the longhand devices `expand.py` could
  write and says, block by block, why the others cannot: numbering, x gaps,
  row gaps, rotation, `rel-pos` against the id, the keys a placement carries,
  and the order the items sit in. A lamp block is folded into the port block it
  names, because `expand.py` writes lamps from that block's `led:` key.
  Anything it reports is a place to look; `expand.py --check` is what decides.

### Changed
- 4 devices are authored as a `layout.yaml`, with `device.yaml` generated
  from it: Celestica ES1010, Celestica DS4100, Opengear CM8008, Opengear CM8008-C.
  Each parsed `device.yaml` is the same as before, its
  lock does not move, and its compiled faces are byte-identical. The cutouts
  and silkscreen beside the generated ports stay longhand.
  The change closes no conformance rows.

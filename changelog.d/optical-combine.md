### Added
- **`combine` on an optical path**, an optional component key
  (roc-ops/Portrayal#246): several sources landing on one destination, the
  opposite of a split, written in place of `from` as a list of `{at}` entries
  with one `to` endpoint. Each source says how it joins - a `band` for a
  wavelength combine (the add side of a filter) or a `ratio` for a power
  combine (a coupler run backwards) - and the two do not mix. Two plain paths
  into one position are still an error; only a declared combine may share
  one. The DCIM projection writes one fibre-map row per source, carrying its
  `band` or `ratio`, exactly as it writes one per destination of a split, so
  a combine onto a trunk position and banded legs off it export the same
  rows. A contract written before this key reads as it did.
- Lint **L171**, on components: a `combine` has one destination and no
  path-level `band`, names each source once, and its sources either all carry
  a `ratio` summing to 100 or carry bands, no two the same, with at most one
  source carrying what the bands leave. L78, L80 and L130 read a combine's
  sources as they read any other endpoint, and L79 allows several sources on
  one destination only inside a declared combine.
- `optical.legs` in the tools: one reader for the three path shapes, which the
  fibre map, the fibre-ends index and the lint rules now share.

### Changed
- `smartoptics/ppm-ad1-1510@2` and `ppm-ad1-1625@2` (2.2.0 to 2.3.0) state
  their add direction as a `combine` onto Line Tx, from the signal-flow
  figures of ds-ppm-r4.0. It was written as banded legs off the line port
  while the vocabulary had no combine. The glass is the same and no export
  changes: the NetBox and Nautobot types and both fibre maps are byte for
  byte what they were. `smartoptics/dcp-2` composes both and takes the patch
  the lock asks for (2.1.2 to 2.1.3); the drawing version in its two device
  types' comments is the only line of any export that moves.
- `docs/optical-paths-design.md` records the combine form, how a path reads
  in both directions, and that `optical.trunk` is the statement of an
  endpoint's role: a position it names, or a rear face carries, is a trunk,
  and every other routed position is a branch.

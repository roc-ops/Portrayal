### Changed
- **BREAKING for a manifest outside this repository that pins the old majors.**
  The five six-way Fibrain HD LC holders, `fibrain/xmi1021ca`, `-da`, `-ga`,
  `-ha` and `xmi1031ga`, and each `-rear`, are `@3`. The rear drew each adapter
  turned half a turn about its centre, which put the ferrule axis 2.90 mm from
  where the front puts the same sleeve (9.05 from the top of the holder against
  11.95). The rear's adapters now stand 2.90 mm lower, so the front and the rear
  of one sleeve share an axis; each rear port is 2.90 mm lower than it was, and
  the rear adapter's outline is drawn 2.90 mm lower with it, a stand-in, as no
  held document shows the back of an adapter. Part ids, fibre positions, port
  paths and DCIM port names are unchanged. A rack file that names `@2` or `@1`
  of one of these parts is read as `@3`. The twelve-way LC holders keep their
  rear as it was: the same move would overlap their two rows.
- `fibrain/xpu` 1.0.0 and `fibrain/xcu` 1.0.3 seat the `@3` holders, and
  `fibrain/xcu-drawer@1` accepts them. The 1U frame is a major because the
  holders its slots accept are named by new refs.
- The bottom view of `fibrain/xpu` draws the rear cable bar as the top view
  does: the two strips, the upright line and the 48 tie slots, the other way
  across because the underside is seen from below, where it drew one plain
  435 x 29 rectangle. The slot size and spacing are the top view's estimates.
- `provenance.cross-member` of `fibrain/xpu` says which holder rows the upright
  is in line with by ferrule axis: the one row of a six-way LC only in an upper
  slot.

### Removed
- `fibrain/xmi1021ca@2`, `xmi1021da@2`, `xmi1021ga@2`, `xmi1021ha@2`,
  `xmi1031ga@2` and each `-rear@2`; each is replaced by its `@3`, and a
  rack that names the old ref is read as the new one.

### Changed
- Seven parts carry an `unmated` sentence that says why nothing plugs into them: `common/ground-symbol@1`
  (a printed earth symbol), `common/screw-head@1`, `amphenol-ns/cover-thumbscrew@1`,
  `dell/thumbscrew-blue-14g@1` and `edgecore/agr-panel-screw@1` (fasteners), and `common/esd-jack@1` and
  `casa/ground-strap@2` (ESD wrist-strap points that no cable of the rack lands on). None presents an
  interface, a slot or a mate. Each part takes a patch, and so does each of the 274 devices that compose
  one (version +0.0.1, its lock, and the `Drawing version` line of its exported device types, and nothing
  else in them). No skin, element or size changed, so nothing is drawn differently. The seven rows of
  `library/conformance-exceptions.yaml` that named these parts are gone and its `cap:` is 215.

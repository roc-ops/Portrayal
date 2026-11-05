### Changed
- The output terminal and the input stud terminal of the Amphenol Network Solutions 300CB08 panels are places a lug lands.
  `amphenol-ns/output-terminal@1` (1.0.0 to 1.1.0) composes `common/terminal-screw-34@1` at the centre of its BATT screw and of
  its RTN screw, so each presents the registered `terminal-stud` key that `generic/ring-lug@1` mates. `amphenol-ns/input-stud-pair@1`
  (1.0.0 to 1.1.0) presents `stud-pair-1` over two such screws exactly 1 inch apart, the spacing the installation guide prints for
  its 3/8-16 studs, so `generic/two-hole-lug-1@1` mates the pair and a ring lug still mates each stud. The screw heads are declared
  estimates that claim no thread, and the skins are not redrawn: the input terminal's skin draws its studs 23.0 apart, and the
  contract says so. Two rows of the conformance records are gone, those of these two parts; the input busbar of the -C models keeps
  its row, because the guide prints its hole spacing as a range of 5/8 to 1 inch and no registered key covers a range.
- The eight panels that place them (`amphenol-ns/300cb08`, `300cb08-sc`, `nrg300cb08-ctrl`, `nrg300cb08-ctrl-sc`, `nrg300cb08-sens`,
  `nrg300cb08-sens-sc`, `nrgils300cb08` and `nrgils300cb08-sc`, 2.0.4 to 2.0.5) take a patch, with their locks and the drawing
  version line of their exported device types (16 files in NetBox and Nautobot). No port, interface or id moves.

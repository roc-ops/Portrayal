### Added
- **`edgecore/dcs240-psu-dc@2`**, the DC supply of the Edgecore DCS240 and DCS511 drawn from the photograph in the vendor's quick
  start guides, where version 1 borrows the AC supply's face with a green three-slot block that no document shows: a black
  two-screw block with "-" and "+" under the screws, a black bail at the left, a perforated grille behind and above the block, a
  cross-head earth screw at the upper right and the red latch at the right. The four element ids stay (`handle`, `latch`,
  `vent-field`, `dc-inlet`) and the latch is not moved; the bail, the grille and the block are, so the redraw is a new major
  (decided 2026-11-03). Every position other than the latch's is read off the photograph at the plate's width and is an estimate;
  the photograph shows the bail and the latch larger than the bay allows, so they are drawn inside the face. Its description says
  what the face carries, a two-screw DC terminal block and an earth screw beside it, and no longer that it is the AC variant's.
- The same major composes the two screws of its terminal block as parts, each a seat a ring lug lands on, and states one DC input
  port of two poles that carry the callouts of the guide (`batt` for the negative voltage range, on the left screw, and `rtn` for
  the DC return, on the right one), the wire size (`#8 AWG`) and the input current (40 A), and no voltage, because the guides give
  a range and no nominal. Its earth screw stands beside the block, not on it, so it is not a pole of the port: the supply composes it
  as a ground part of its own, a seat a ring lug lands on outside the port, drawn as `common/ground-screw@1` and declared a
  stand-in because no document held gives its thread. The supply now offers a power end a DC feed can land on.

### Changed
- The DCS240 (`edgecore/dcs240`, 1.1.10 to 1.2.0) and the DCS511 (`edgecore/dcs511`, 2.0.11 to 2.1.0) each take a minor: their
  two DC configurations seat `edgecore/dcs240-psu-dc@2`, their two supply bays accept it beside `@1`, and the build now publishes
  a DC port for them. Their locks and the drawing version line of their exported device types change (14 files in NetBox and
  Nautobot). The supply's module type is written from `@2`: its new description and its contract version (2 files). Their
  `dc-supply-face` gap now names `@2` and says its face is drawn from the guide's photograph with every position an estimate. No
  port, interface or id moves.
- **`edgecore/dcs240-psu-dc@1` is retired, not deleted** (1.2.0 to 1.2.1): it says `superseded-by` `edgecore/dcs240-psu-dc@2` and
  is otherwise unchanged, so a rack or a contract that names it still draws what it drew, and it is no longer exported as a module
  type. Nothing seats it in a configuration. One row of the records file is gone and its `cap:` is 158.

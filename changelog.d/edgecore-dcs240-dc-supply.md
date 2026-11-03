### Changed
- The DC supply of the Edgecore DCS240 and DCS511 (`edgecore/dcs240-psu-dc@1`, 1.2.0 to 1.3.0) is drawn from the photograph in the
  vendor's quick start guides, where it used to borrow the AC supply's face with a green three-slot block that no document shows:
  a black two-screw block with "-" and "+" under the screws, a black bail at the left, a perforated grille behind and above the
  block, a cross-head earth screw at the upper right and the red latch at the right. The four element ids stay (`handle`, `latch`,
  `vent-field`, `dc-inlet`) and the latch is not moved. Every position other than the latch's is read off the photograph at the
  plate's width and is an estimate; the photograph shows the bail and the latch larger than the bay allows, so they are drawn inside
  the face.
- The same supply composes the two screws of its terminal block as parts, each a seat a ring lug lands on, and states one DC input
  port of two poles that carry the callouts of the guide (`batt` for the negative voltage range, on the left screw, and `rtn` for
  the DC return, on the right one), the wire size (`#8 AWG`) and the input current (40 A), and no voltage, because the guides give
  a range and no nominal. Its earth screw stands beside the block, not on it, so it is not a pole of the port: the supply composes it
  as a ground part of its own, a seat a ring lug lands on outside the port, drawn as `common/ground-screw@1` and declared a
  stand-in because no document held gives its thread. The supply now offers a power end a DC feed can land on.
- The DCS240 (`edgecore/dcs240`, 1.1.10 to 1.2.0) and the DCS511 (`edgecore/dcs511`, 2.0.11 to 2.1.0) each take a minor, because the
  build now publishes a DC port for them, with their locks and the drawing version line of their exported device types (14 files
  in NetBox and Nautobot); the supply's module type carries the new contract version (2 files). Their `dc-supply-face` gap now says
  the face is drawn from the guide's photograph with every position an estimate. No port, interface or id moves. One row of the
  records file is gone and its `cap:` is 171.

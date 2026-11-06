### Added
- The key `smartoptics-dcp-dc-block-3` for the DC power connector of the Smartoptics DCP-2-PSU-DC-FB supply: a pluggable connector
  with three gold-coloured cells in a column, one small, one large and one small from the top down, and a "+" scribed on the panel
  at its upper end (Smartoptics DCP-series User Manual 14.0 A, figure 2-13 and section 3.1.5, "the DC power connector"). The manual
  names no maker, part number or pitch for it, so the key claims no maker, standard or pitch. `smartoptics/dcp-2-dc-header@1`
  presents it and `smartoptics/dcp-2-dc-plug@1`, the cable connector, mates it; both are declared stand-ins with estimated sizes.

### Changed
- The supply `smartoptics/dcp-2-psu-dc@1` (1.4.1 to 1.5.0) composes its connector as the part `dc-header`, standing in the box its
  skin already reserves for it, so it offers a place a cable lands. The one role the manual's marks print (the "+" at the top cell)
  is recorded in its provenance and the other two cells are recorded as not printed; no DC port is stated, because the poles are the
  contacts of one pluggable connector. No skin is edited. The supply's exported power port is `{module}/dc-header` of type `other`
  where it was `{module}/Inlet` of type `dc-terminal`.
- The two devices that seat it (`smartoptics/dcp-2` and `smartoptics/dcp-m32-cso-zr`) take a patch, with their locks and the drawing
  version line of their exported device types; the supply's module types carry the new contract version and the new port name. One
  row of the records file is gone.

### Added
- The keys `telco-dc-block-3` and `telco-dc-block-2` for the pluggable DC connectors of the Telco Systems XM-3352 and XM-8424H
  supplies: a green block with a screw at each end and three cells printed "-" and "+" over the outer two (XM-3352), and a green block
  with two cells and a latch tab (XM-8424H), both read from the data sheets' front photographs. No held document names a maker, series
  or pitch for either, so each key claims none. `telco-systems/xm3352-dc-header@1` and `telco-systems/xm8424-dc-header@1` present them
  and `telco-systems/xm3352-dc-cable-plug@1` and `telco-systems/xm8424-dc-cable-plug@1` mate them; all four are declared stand-ins with
  estimated sizes.

### Changed
- The two Telco Systems DC supplies (`telco-systems/xm3352-psu-dc@1` and `telco-systems/xm8424-psu-dc@1`, 1.0.0 to 1.1.0) compose the
  new header in place of the plug part they composed before, at the place their skins already draw it, so each offers a place a cable
  lands. The XM-3352 supply records the roles its marks give (`neg` on the left cell, `pos` on the right one, the middle cell unmarked) and
  the XM-8424H supply records that no pole mark is legible; neither states a DC port. The skins are unchanged, and the exported power
  port keeps its name `{module}/dc-in` and its type `dc-terminal`.
- The two devices that seat them (`telco-systems/xm-3352` and `telco-systems/xm-8424h`) take a patch, with their locks and the drawing
  version line of their exported device types; the supplies' module types carry the new contract version. Two rows of the records file are
  gone.

### Removed
- `telco-systems/xm3352-dc-plug@1` and `telco-systems/xm8424-dc-plug@1`, the two plug parts the supplies composed before; the headers
  above draw the same green blocks and nothing else composed them.

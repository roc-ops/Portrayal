### Added
- The key `telco-ac-cloverleaf-3` for the three-lobe AC inlet of the Telco Systems XM-3352 AC supply: a dark rectangular surround holding
  three round lobes with a pin in each, read from the data sheet's front photographs. No held document names its type, maker or part
  number, so the key claims none. `telco-systems/xm3352-ac-inlet@1` presents it and `telco-systems/xm3352-ac-cord-plug@1`, a declared
  stand-in for the cord connector with an estimated size, mates it.
- `telco-systems/tm-7124s-dc-cable-plug@1`, a declared stand-in for the cable connector of the TM-7124S's four-pole DC feed header, with
  an estimated size. It mates the registered key `screw-terminal-4`.

### Changed
- The XM-3352 AC supply (`telco-systems/xm3352-psu-ac@1`) and its inlet (`telco-systems/xm3352-ac-inlet@1`), and the TM-7124S's DC feed
  header (`telco-systems/tm-7124s-dc-feed@1`), each 1.0.0 to 1.1.0, now present a registered connector key, so each offers a place a
  cord or cable lands. The feed header, until now registered but presented by no part, presents `screw-terminal-4`; its provenance
  records the legend `-48VA RETA -48VB RETB` and reads it top to bottom as `batt`, `rtn`, `batt`, `rtn`, and states no DC port. The
  skins are unchanged, and the exported power ports keep their names and types (`{module}/inlet`, `iec-60320-c6`; the feed's `dc-terminal`).
- The two devices that carry them (`telco-systems/xm-3352`, 0.1.1 to 0.1.2, and `telco-systems/tm-7124s`, 0.1.4 to 0.1.5) take a patch,
  with their locks and the drawing version line of their exported device types; the AC supply's module type carries the new contract
  version. Two rows of the records file are gone: the supply and the feed header.
- The registry note of `screw-terminal-4` names its cable connector. The registry census and the terminal-header census list the new key and the header.

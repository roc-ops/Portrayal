### Changed
- The Juniper MX240 normal-capacity AC supply (`juniper/mx240-psu-ac@1`, 1.0.0 to 1.1.0) composes the C20 appliance inlet its
  hardware guide names (`std/c20-inlet@1`, id `inlet`), so it offers a power end a cord lands on: a C19 cord end mates it. Its
  module type gains one power port, `{module}/inlet` of type `iec-60320-c20`; no port that was exported before is renamed or
  removed. The inlet stands on a free place of the drawn face, declared an estimate because the guide's figure is line art with
  no scale; the handle, the input switch, the lamps and the vents are drawn as before, and no photograph of the AC variant is
  held. One row of the records file and the supply's lint warning about its power entry are gone.
- The MX240 (`juniper/mx240`, 6.4.5 to 6.4.6) takes a patch with its lock and the drawing version line of its exported device
  types; the supply's module type carries the new contract version and the power port (4 files in all, in NetBox and Nautobot).

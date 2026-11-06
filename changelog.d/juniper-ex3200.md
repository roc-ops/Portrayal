### Added
- Juniper EX3200 access switches, from the EX3200 Switch Hardware Guide (published 2020-12-15) and the
  EX3200 datasheet: `juniper/ex3200-24t` and `juniper/ex3200-48t` (configurations `ac`, the 320 W AC
  build, and `dc`, the DC-powered -DC build, which gives no PoE), `juniper/ex3200-24p` and
  `juniper/ex3200-48p`. Each has one field-replaceable power supply bay, a fan tray bay and a covered
  uplink module slot. The uplink modules are not modelled.
- Three Juniper EX3200 parts: `juniper/ex3200-fan-tray@1` (the single-fan tray), `juniper/ex3200-uplink-cover@1`
  and `juniper/ex3200-poe-legend@1` (the "8PoE" model plate line, left off the -DC builds). The power
  supplies are the existing `juniper/ex4200-pwr-320-ac@1`, `-600-ac@1`, `-930-ac@1` and `-190-dc@1`, which
  carry the same part numbers.

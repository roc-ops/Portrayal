### Added
- Juniper (`juniper/ex4550-32f`): the EX4550-32F, a 1RU switch with 32 SFP+ ports, a front and a rear
  module slot, three fan modules and two supply slots. Five orderable configurations: EX4550-32F-AFO
  (the default), -AFI, -DC-AFO, -DC-AFI and the spare chassis -S. One example configuration seats a
  second supply.
- Juniper (`juniper/ex4550-32t`): the EX4550-32T, the same chassis with 32 RJ-45 10GBASE-T ports.
  Four orderable configurations: EX4550-32T-AFO (the default), -AFI, -DC-AFO and -DC-AFI.
- Juniper (`juniper/ex4500-40f`): the EX4500-40F, a 2RU switch with 40 SFP+ ports, two uplink module
  slots, two supply slots, one fan tray and a rear module slot. Eight orderable configurations:
  EX4500-40F-FB (the default), -BF, -FB-C, -BF-C, -DC-C, -VC1-FB, -VC1-BF and -VC1-DC.
- The EX4550 units: the fan modules `juniper/ex4550-fan-afo@1` and `juniper/ex4550-fan-afi@1`
  (EX4550-FAN-AFO and -AFI), the supply cover panel `juniper/ex4550-psu-cover@1` and the module slot
  cover panel `juniper/ex4550-em-cover@1`. The EX4550 seats the JPSU-650W supplies that the library
  already holds as `juniper/ex4600-jpsu-650-ac-afo@1`, `-ac-afi@1`, `-dc-afo@1` and `-dc-afi@1`. The
  EX4550 expansion and Virtual Chassis modules are named and not modelled.
- The EX4500 units, each named for its role because its guide prints no part number: the supplies
  `juniper/ex4500-psu-ac-fb@1`, `-ac-bf@1` and `-dc-fb@1`, the fan trays `juniper/ex4500-fan-tray-fb@1`
  and `-bf@1`, the intraconnect module `juniper/ex4500-lb@1`, the Virtual Chassis module
  `juniper/ex4500-vc1@1`, the cover panels `juniper/ex4500-psu-cover@1` and
  `juniper/ex4500-uplink-cover@1`, and the legend `juniper/ex4500-vc-legend@1` that the VC1 models print.
  The EX4500 uplink modules are named and not modelled.

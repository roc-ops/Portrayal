### Changed
- The Juniper MX960 AC power supply (`juniper/mx960-psu-ac@1`, 1.0.1 to 1.0.2) carries a sentence saying that its AC inlet is on
  the chassis strip above each supply and not on the supply, as the hardware guide describes the normal-capacity supply, so the
  part checks no longer report the supply as drawn with no power end. The supply still composes no inlet and states none: the
  chassis's four C20 inlets stay the only ones exported, and no port, drawing, size or id changes. The MX960 takes the version
  bump the lock asks for, and the version comment of the supply's module types and of the MX960's device types moves with it.
- One row of the port-usable records file is gone: the MX960 AC supply.

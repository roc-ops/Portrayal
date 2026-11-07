### Added
- Juniper EX4400 copper campus switches, the first of the EX line: `juniper/ex4400-24t`,
  `juniper/ex4400-24p`, `juniper/ex4400-48t` and `juniper/ex4400-48p`, each a 1RU switch with its
  front and rear drawn from the hardware guide's renders. A PoE model and its non-PoE sibling are
  separate devices. The 24T and 48T have orderable configurations `ac`, `afi`, `dc`, `dc-afi` and
  `s` (EX4400-24T, -24T-AFI, -24T-DC, -24T-DC-AFI, -24T-S and the 48T equivalents). The 24P and 48P
  have `ac` and `s` (EX4400-24P, -24P-S, -48P and -48P-S). Each device also has example
  configurations that seat an extension module and a second power supply.
- Shared EX4400 field-replaceable units, named by their Juniper part numbers:
  `juniper/jpsu-550-c-ac-afo`, `juniper/jpsu-550-c-ac-afi`, `juniper/jpsu-550-c-dc-afo`,
  `juniper/jpsu-550-c-dc-afi`, `juniper/jpsu-1050-c-ac-afo`, `juniper/jpsu-1600-c-ac-afo` and
  `juniper/jpsu-2000-c-dc-afo`; the fan modules `juniper/ex4400-fan-afo` and
  `juniper/ex4400-fan-afi`; the extension modules `juniper/ex4400-em-4s`, `juniper/ex4400-em-4y`
  and `juniper/ex4400-em-1c`; the slot covers `juniper/ex4400-psu-cover` and
  `juniper/ex4400-em-cover`; and the front `juniper/ex4400-mode-button`. The other EX4400 models
  share these parts where the guide lists them.
- The DCIM exports gain one device type for each of the 14 orderable EX4400 configurations, and 14
  module types: one for each power supply, fan module, extension module and slot cover.

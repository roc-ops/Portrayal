### Added
- Juniper (`juniper/ex4600-40f`): the EX4600-40F, a 1RU switch with 24 SFP+ ports, 4 QSFP+ ports
  and two expansion module bays. Five orderable configurations: EX4600-40F-AFO (the default),
  -AFI, -DC-AFO, -DC-AFI and the spare chassis -S. Three example configurations seat two
  QFX-EM-4Q, two EX4600-EM-8F or a single power supply with a cover panel.
- The EX4600 field-replaceable units, each its own component: the fan modules
  `juniper/ex4600-fan-afo@1` and `juniper/ex4600-fan-afi@1` (QFX5100-FAN-AFO and -AFI), the
  supplies `juniper/ex4600-jpsu-650-ac-afo@1`, `-ac-afi@1`, `-dc-afo@1` and `-dc-afi@1`
  (JPSU-650W-AC and DC, AFO and AFI), the expansion modules `juniper/ex4600-em-8f@1`
  (EX4600-EM-8F) and `juniper/ex4600-em-4q@1` (QFX-EM-4Q), the cover panel
  `juniper/ex4600-em-blnk@1` (QFX5100-EM-BLNK) and the supply cover panel
  `juniper/ex4600-psu-blank@1`. Their DCIM module types carry the suffix (EX4600) so that they do
  not share a file with the same part numbers in another Juniper line.

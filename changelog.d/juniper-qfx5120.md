### Added
- Juniper QFX5120-48Y and QFX5120-48YM, the two 48 x SFP28 plus 8 x QSFP28 data-centre
  leaf switches of the QFX5120 line (`juniper/qfx5120-48y`, `juniper/qfx5120-48ym`),
  each with its front and rear faces drawn from the QFX5120 hardware guide and Juniper's studio
  photographs. The power and airflow variants the guide lists are orderable configurations of
  each device (QFX5120-48Y-AFO2 and -AFI2, QFX5120-48YM-AFO and -AFI), each exporting its own
  NetBox and Nautobot device type. The DC variants, the rack mount kits and the 48T and 32C
  models are not modelled yet.
- Juniper field-replaceable units for the QFX5120: the fan modules `juniper/qfx5110-fanafo`
  and `juniper/qfx5110-fanafi`, and the AC power supplies `juniper/jpsu-650w-ac-ao` and
  `juniper/jpsu-650w-ac-ai` (QFX5120-48Y) and `juniper/jpsu-850w-ac-afo` and
  `juniper/jpsu-850w-ac-afi` (QFX5120-48YM).

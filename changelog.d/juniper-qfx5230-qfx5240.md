### Added
- Juniper QFX5230-64CD, QFX5240-64OD and QFX5240-64QD (Refs #39): fixed 2RU data-centre switches with 64 ports and two
  SFP+ ports, from the QFX5230-64CD Switch Hardware Guide (2026-04-28), the QFX5240 Switch Hardware Guide (2026-07-10)
  and the QFX5240 line datasheet, as `juniper/qfx5230-64cd` (64 QSFP-DD at 400 GbE), `juniper/qfx5240-64od` (64 OSFP at
  800 GbE) and `juniper/qfx5240-64qd` (64 QSFP-DD at 800 GbE). Each port side has the network ports with their lamps and
  numerals, the SFP+ pair, the RJ-45 management and console ports (and a time-of-day port on the QFX5240), USB, reset,
  the chassis lamps and the clock connectors; each rear has two power supplies and four fan modules. The QFX5230-64CD-AFO,
  -AFI, -D-AFO and -D-AFI builds, the QFX5240-64OD-AO and QFX5240-64QD-AO builds and the three spare chassis (-CHAS) are
  orderable configurations, and each exports as a DCIM device type. New components under `juniper/`:
  `qfx5230-64cd-fan-afo`, `qfx5230-64cd-fan-afi`, `qfx5230-jnp-3000w-ac-afo`, `qfx5230-jnp-2700w-ac-afi`,
  `qfx5230-jnp-3000w-dc-afo`, `qfx5230-jnp-2400w-dc-afi`, `qfx5240-2u-fanao` and `qfx5240-pwr-ac-ao`. The QFX5241
  models are not modelled.

### Added
- Juniper QFX5241-32OD, QFX5241-64OD and QFX5241-64QD (Refs #39): the QFX5241 variants of the QFX5240 line, from the
  QFX5241-32OD Switch Hardware Guide (2026-10-11) and the QFX5241-64OD and QFX5241-64QD Switches Hardware Guide
  (2026-09-28), as `juniper/qfx5241-32od` (1RU, 32 OSFP at 800 GbE and two SFP28), `juniper/qfx5241-64od` (2RU, 64 OSFP)
  and `juniper/qfx5241-64qd` (2RU, 64 QSFP-DD). Each port side has the network ports with their lamps and numerals, the
  SFP pair, the RJ-45 management and console ports, USB, reset and the chassis lamps (and the time-of-day port and clock
  connectors on the 64-port models); the 32OD rear has two power supplies at its ends and seven fan modules, the 64-port
  rears two supplies and four fan modules. The QFX5241-32OD-AO, QFX5241-64OD-AO and -DO, QFX5241-64QD-AO and -DO builds
  and the three spare chassis (-CHAS) are orderable configurations, and each exports as a DCIM device type. New
  components under `juniper/`: `qfx5241-1u-pwr-ao`, `qfx5241-1u-fan-o`, `qfx524x-2ru-pwr-do` and `qfx524x-2ru-fan-o`;
  the AC builds of the 64-port models seat the existing `qfx5240-pwr-ac-ao` and `qfx5240-2u-fanao`. The ORv3
  switch-tray builds (-DO-T1, -DO-T2 and the -TCHAS spares) are not modelled.

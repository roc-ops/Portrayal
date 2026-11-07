### Added
- Juniper QFX5220-32CD and QFX5220-128C (Refs #39): the QFX5220 line of 400G and 100G spine switches, from the
  QFX5220 Switch Hardware Guide (2026-10-14), as `juniper/qfx5220-32cd` (1RU, 32 QSFP-DD and 2 SFP+ ports) and
  `juniper/qfx5220-128c` (4RU, 128 QSFP28 and 2 SFP+ ports). Each has its time-of-day port, four clock
  connectors, console, management, USB, reset, chassis lamps and ESD point on the port side. The 32CD has two
  power supplies and six fan modules. The 128C has four power supplies and six two-fan modules. The AC, DC and
  airflow builds and the spare chassis are orderable configurations (QFX5220-32CD-AFO, -AFI, -D-AFO, -D-AFI and
  -CHAS, and QFX5220-128C-AFO, -D-AFO and -CHAS), and each exports as a DCIM device type. The 32CD reuses the
  QFX5130 supply and fan components and the 128C reuses the QFX10002 supply components, by part number. New
  components under `juniper/`: `qfx5220-128c-fan-afo` and `qfx5220-128c-port-lamps`. The QFX5220-32CD ORv3 tray
  assembly and the 128C EMI front panel are not modelled.

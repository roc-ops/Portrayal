### Added
- Juniper QFX5130-32CD (Refs #39): a fixed 1RU 400G data-centre leaf and spine switch, from the QFX5130 Switch
  Hardware Guide (2026-10-14) and datasheet (July 2025), as `juniper/qfx5130-32cd`. The port side has 32 QSFP-DD
  ports in two rows of sixteen and two SFP+ ports with their lamps, the RJ-45 console and management ports, USB,
  reset, the chassis lamps, the 10 MHz and 1 PPS outputs and the ESD point. The rear has two power supplies and
  six fan modules. The AFO and AFI airflow builds, the DC builds (QFX5130-32CD-AFO, -AFI, -D-AFO and -D-AFI) and
  the spare chassis (QFX5130-32CD-CHAS) are orderable configurations of it, and each exports as a DCIM device
  type. New components under `juniper/`: `qfx5130-jpsu-1600-ac-afo`, `qfx5130-jpsu-1600-ac-afi`,
  `qfx5130-jpsu-1600-dc-afo`, `qfx5130-jpsu-1600-dc-afi`, `qfx5130-32cd-fan-afo` and `qfx5130-32cd-fan-afi`. The
  QFX5130E-32CD, the ORv3 tray assembly, and the QFX5130-48C and QFX5130-48CM (which need an SFP-DD cage) are not
  modelled.

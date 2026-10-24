### Added
- Juniper QFX5130-48C and QFX5130-48CM (Refs #39): fixed 1RU data-centre leaf switches with 48 SFP56-DD ports
  (100 GbE) and 8 QSFP-DD uplinks (400 GbE), from the QFX5130 Switch Hardware Guide (2026-10-14) and datasheet
  (July 2025), as `juniper/qfx5130-48c`. It is the first device to place the SFP-DD cage (`std/sfp-dd-ganged`). The
  guide draws both models with one front panel and one rear, so the 48CM (MACsec capable) is a set of
  configurations of the same device. The port side has the 48 SFP56-DD cages in three groups of eight columns and
  the eight uplinks with a lamp for each; the rear has the management panel (RJ-45 management and console ports,
  USB, reset, the chassis lamps, the 10 MHz and 1 PPS connectors, two SFP+ ports and the ESD point), six fan
  modules and two power supplies. The AFO and AFI airflow builds, the DC builds and the spare chassis are
  orderable configurations (QFX5130-48C-AFO, -AFI, -D-AFO, -D-AFI and -CHAS, and the same five for
  QFX5130-48CM), and each exports as a DCIM device type. New components under `juniper/`:
  `qfx5130-48c-fan-afo` and `qfx5130-48c-fan-afi`; the four JPSU-1600W supplies of the QFX5130-32CD are reused.

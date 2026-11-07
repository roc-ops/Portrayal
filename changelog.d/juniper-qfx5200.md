### Added
- Juniper QFX5200-32C and QFX5200-48Y (#39): 1RU 100G data-centre spine and leaf switches, from the QFX5200 Switch Hardware
  Guide (2026-03-09). Each model is one device. The 32C (32 QSFP28 ports, the management panel on the FRU side) takes AC or DC
  supplies and front-to-back or back-to-front airflow as configurations, with the QFX5200-32C-AFO, -AFI, -DC, -LAFO and -LAFI
  part numbers each exported as a DCIM device type; the 48Y (48 SFP28 and 6 QSFP28 ports) exports as QFX5200-48Y, with its
  back-to-front and DC builds drawn as examples because the guide names no chassis part number for them. Each fan module
  and power supply is a component in a bay, named by its Juniper part number; the 32C reuses the existing JPSU-850W-AC-AFO
  and -AFI.

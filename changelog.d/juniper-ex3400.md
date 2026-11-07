### Added
- Juniper EX3400 access switches (Refs #39): the EX3400-24T, EX3400-24P, EX3400-48T and EX3400-48P,
  as `juniper/ex3400-24t`, `juniper/ex3400-24p`, `juniper/ex3400-48t` and `juniper/ex3400-48p`. Each is a
  1U device with its front (RJ-45 block, four SFP or SFP+ uplinks, status lamps, Factory Reset/Mode
  button) and rear (two QSFP+ uplinks, management, console and USB ports, two fan
  modules, two power supply bays). The EX3400-48T also carries the EX3400-48T-AFI (back to front)
  and EX3400-48T-DC builds, and the EX3400-24T the EX3400-24T-DC build, as orderable configurations.
  New components under `juniper/`: `ex3400-fan-afo`, `ex3400-fan-afi`, `ex3400-jpsu-150-ac-afo`,
  `ex3400-jpsu-150-ac-afi`, `ex3400-jpsu-150-dc-afo`, `ex3400-jpsu-600-ac-afo`,
  `ex3400-jpsu-920-ac-afo`, `ex3400-psu-blank` and `ex3400-ground-pair`. The front Mini-USB console
  is drawn but not placed as a port, because the DCIM exporter has no route for it. The DCIM exports add
  seven device types (one per orderable configuration) and the module types for the power supplies
  and fan modules. The EX3400-48T-DC-T1 ORv3 tray assembly is not modelled.

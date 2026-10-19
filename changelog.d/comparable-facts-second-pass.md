### Added
- **Comparable facts: `macsec`, `srv6` and `usb`, and two qualified `nebs`
  readings** (#112, `spec/tools/portrayal/comparable.py`,
  `docs/comparable-facts-design.md`). `comparable-facts.json` gains three facts:
  `macsec` (from `macsec`, 11 devices), `srv6` (from `routing`,
  `segment-routing` and `srv6`, 19 devices, every value naming Segment Routing
  over IPv6) and `usb` (from `usb` and `service-port`, 23 devices, every value
  naming a USB port). `nebs` also reads `nebs-emc-safety` and `nebs-physical`
  as qualified readings (`emc-safety`, `physical`) behind the headline, so seven
  ASR 9000 chassis show three readings. `encryption` and `tpm` are deliberately
  not sources of `macsec`. Nothing is renamed and no device file changes; a
  fact name, once published, is a key to add to and not to rename.

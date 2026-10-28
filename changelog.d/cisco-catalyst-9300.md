### Added
- Cisco: the Catalyst 9300 line begins with two devices, `cisco/c9300-48p` (C9300-48P, 48 x
  10/100/1000 PoE+) and `cisco/c9300-48t` (C9300-48T, 48 x 10/100/1000), each with its fan modules,
  two power supply bays and a network module bay. The two are the first slice of the Cisco
  Catalyst line; the other Catalyst 9300 models follow.
- The Catalyst 9300's shared parts, named by Cisco part number: the FAN-T2 fan module
  (`cisco/fan-t2@1`), nine power supplies (`cisco/pwr-c1-350wac@1`, `pwr-c1-350wac-p`,
  `pwr-c1-715wac`, `pwr-c1-715wac-p`, `pwr-c1-1100wac`, `pwr-c1-1100wac-p`, `pwr-c1-1900wac-p`,
  `pwr-c1-1900whv-t` and `pwr-c1-715wdc`), the C9300-NM-BLANK network module blank, the power
  supply slot cover (`cisco/c9300-psu-blank@1`), the Mode button, and the StackWise-480 and
  StackPower connectors.
- `std/mini-usb@1`, the USB Mini-B receptacle that conforms to the registry's `mini-usb-b`, used
  for the Catalyst 9300's console port.

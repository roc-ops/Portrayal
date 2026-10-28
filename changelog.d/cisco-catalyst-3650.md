### Added
- Cisco's first Catalyst 3650 (#1275), from the Cisco Catalyst 3650 Switches Hardware Installation Guide
  (OL-29734-01): the WS-C3650-48PD (`cisco/ws-c3650-48pd`, 1RU, 48 PoE+ 10/100/1000 RJ-45, two 1G SFP and two
  1G SFP / 10G SFP+ uplinks), front and rear. -L, -S and -E are software images of this one hardware and are
  listed as aliases. It has five configurations: the shipped build (one 640 W AC supply and a blank cover),
  two 640 W, one 1025 W, one DC and two DC; the guide prints no ordering code for a supply build, so none
  carries a part number. Every position is estimated from the guide's isometric drawings, and the USB mini-B
  console port is left as a gap until the jack is a library part. The other 3650 models follow in later batches.
- The 3650's field-replaceable units: the supplies PWR-C2-250WAC, PWR-C2-640WAC, PWR-C2-1025WAC and
  PWR-C2-640WDC, the PWR-C2-BLANK cover and the FAN-T1 fan module (`cisco/pwr-c2-640wac` and its five siblings), and
  the StackWise adapter blank, which the guide gives no part number (`cisco/c3650-stackwise-blank`).
- The DCIM device type for the WS-C3650-48PD, in the NetBox and Nautobot exports.

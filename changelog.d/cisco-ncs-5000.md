### Added
- Cisco's first two NCS routers (#1265), from the Hardware Installation Guide for Cisco NCS 5000 Series Routers:
  the NCS 5001 (`cisco/ncs-5001`, 1RU, forty SFP+ and four QSFP28) and the NCS 5002 (`cisco/ncs-5002`, 2RU,
  eighty SFP+ and four QSFP28), each with its port-side and fan-side faces. Each has four example
  configurations, AC or DC with port-side intake or exhaust; the guide prints no ordering code for a build. The guide is silent on sale status, so both are
  recorded as unknown, and every face position is estimated from its three-quarter figures.
- The NCS 5000 field-replaceable units, one component per Cisco part number: the AC supplies NC5K-PAC-650W-FR and
  -BK, the DC supplies NC5K-PDC-930W-FR and -BK, the NCS 5001 fan modules NCS-5001-FN-FR and -BK and the
  NCS 5002 fan modules NCS-5002-FN-FR and -BK (`cisco/nc5k-pac-650w-fr` and its seven siblings).
- The DCIM device types for the NCS 5001 and NCS 5002, one each, in the NetBox and Nautobot exports.

### Added
- Cisco NCS routers (#1265), from the Hardware Installation Guide for Cisco NCS 5000 Series Routers and the Hardware Installation Guide
  for Cisco NCS 5700 Series Fixed-Port Routers: the NCS 5011 (`cisco/ncs-5011`, 1RU, thirty-two QSFP28, four example
  configurations that take the NCS 5000 supplies already in the library), the NCS-57C3-MOD-S (`cisco/ncs-57c3-mod-s`, 3RU, forty-eight SFP28
  and eight QSFP28, with three modular port adapter bays that hold their blanks, two route processor bays, two front supplies and six rear fan
  trays; also sold as NCS-57C3-MOD-SYS) and the NCS-57C3-MOD-HX (`cisco/ncs-57c3-mod-hx`, its environment-hardened variant, which takes only the hardened
  route processor and fan trays). The guides print no ordering code for a build, so every build is an example or a derived base. The guides are silent on
  sale status, so all three are recorded as unknown. The 5011's positions are estimated from three-quarter figures; the 57C3's are read from flat figures.
- The parts they take, one component per Cisco part number: the NCS 5011 fan modules NCS-5011-FN-FR and -BK, the 57C3's supplies NC57-1600W-ACFW and
  -DCFW, fan trays NC57-C3-FAN2-FW and NC57-C3-FAN1-FW (and -HX), route processors NC57-MOD-RP2-E and -E-HX, and the blanks NC55-MPA-BLNK,
  NC57C3-RP-BLNK and NC57C3-PS-BLNK (`cisco/ncs-5011-fn-fr` and its eleven siblings).
- The DCIM device types for the three routers, one each, in the NetBox and Nautobot exports.

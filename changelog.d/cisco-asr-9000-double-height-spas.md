### Added
- **The two double-height ASR 9000 shared port adapters seat.** `cisco/spa-1xchoc48-ds3@1` 1.3.0 and `cisco/spa-2xchoc12-ds0@1` 1.3.0
  state `slot-width: 2` and no longer carry `unplaced:`. On `cisco/a9k-sip-700@2` and `cisco/a9k-sip-700-8g@2` (both 2.1.0) the left bay of each
  row, `bay-2` and `bay-3`, lists the two and states `span: [bay-0]` and `span: [bay-1]`, the bay beside it, which the guide's Table 10, Figure 2,
  Table 7 with Figure 3, and Figures 6 and 8 put under one plate twice a single's thickness. `bay-0` and `bay-1` list no double, and the 22 single-width
  adapters stay listed in all four bays. The six ASR 9000 chassis that seat a SIP (9006, 9010, 9904, 9910, 9912 and 9922) each take a patch and the
  drawing version line of their exported device types. This closes two rows of the ASR 9000 parts no chassis accepts.

### Changed
- **BREAKING for DCIM data already imported:** in Nautobot the interfaces of the two double-height adapters are named `{module.parent}/{module}/p0` and so
  on, the name every adapter seated in a SIP takes, where they were `{module}/p0` while no SIP took them. A module type already imported keeps the
  old names until it is imported again. NetBox's names do not change. The two adapters' module types and the two SIPs' (a bay that spans says so in its
  description) gain a `Contract version` line, and `slot-width: 2` is listed among the adapters' facts.

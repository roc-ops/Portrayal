### Changed
- The ASR 9000 SIP-700 and SIP-700-8G (`cisco/a9k-sip-700@2`, `cisco/a9k-sip-700-8g@2`) are accepted by the
  line card bays of the ASR 9006, 9904, 9910, 9912 and 9922, 44 bays, as well as the ASR 9010's. Cisco's SIP and
  SPA Hardware Installation Guide and the SIP-700 data sheet say the card is supported on all ASR 9000 chassis,
  and the ASR 9000 Overview and Reference Guide excepts the ASR 9906, whose bays do not take it. Each bay is the
  card's own 41.4 x 395.7 mm, so no bay, port or id changes and no drawing changes. The five chassis take a
  minor (`cisco/asr-9006` 3.4.0, `cisco/asr-9904` 3.4.0, `cisco/asr-9910` 2.1.0, `cisco/asr-9912` 2.4.0 and
  `cisco/asr-9922` 2.4.0); the DCIM device types of the five differ in the count the line card module bays'
  `Accepts:` text gives and in the `Drawing version` line. No conformance row is closed or opened.

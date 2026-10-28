### Added
- Cisco Nexus 9500 line cards, batch 1: `cisco/n9k-x9736c-fx` (36 x QSFP28 100G), `cisco/n9k-x97160yc-ex`
  (48 x SFP28 1/10/25G and 4 x QSFP28 40/100G), `cisco/n9k-x9732c-fx` (32 x QSFP28 100G) and
  `cisco/n9k-x9716d-gx` (16 x QSFP-DD 400G). Each is a 17.0 x 1.75 in line card at the guides' line-card row
  with its ports, the BCN and STS lamps and one Link triangle per port; their faces are drawn from the
  guides' text and every position is estimated. Four DCIM module types are exported: `N9K-X9736C-FX`,
  `N9K-X97160YC-EX`, `N9K-X9732C-FX` and `N9K-X9716D-GX`. The N9K-X9788TC-FX is not modelled yet (the guides
  name its 48 ports three ways); the R-series, -EX and classic cards follow.

### Changed
- The line-card bays of `cisco/n9k-c9504` (2.1.0), `cisco/n9k-c9508` (1.1.0) and `cisco/n9k-c9516` (2.1.0)
  accept the line cards their own guide supports in addition to the line-card blank, which every bay still
  seats: all four on the 9504 and 9508, and the first three on the 9516, whose guide says the
  N9K-X9716D-GX is not compatible. Every bay, default and configuration is unchanged. The fabric modules a
  card is paired with are recorded as a gap and not enforced. The DCIM device types of the three chassis
  differ only in the `Accepts:` text of their `lc-N` module bays.

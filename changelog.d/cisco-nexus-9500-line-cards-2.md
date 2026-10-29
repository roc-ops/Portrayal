### Added
- Cisco Nexus 9500 line cards, batch 2: `cisco/n9k-x9736c-ex` (36 x QSFP28 100G), `cisco/n9k-x9732c-ex`
  (32 x QSFP28 100G), `cisco/n9k-x9736c-fx3` (36 x QSFP28 100G), `cisco/n9k-x9736q-fx` (36 QSFP28 cages at
  40G) and `cisco/n9k-x9408pc-cfp2` (8 x CFP2 100G). Each is a 17.0 x 1.75 in line card at the guides'
  line-card row with its ports, the BCN and STS lamps and one Link triangle per port; their faces are drawn
  from the guides' text and every position is estimated. Five DCIM module types are exported:
  `N9K-X9736C-EX`, `N9K-X9732C-EX`, `N9K-X9736C-FX3`, `N9K-X9736Q-FX` and `N9K-X9408PC-CFP2`. The
  N9K-X9788TC-FX is still not modelled; the R-series and the classic cards follow.

### Changed
- The line-card bays of `cisco/n9k-c9504` (2.2.0), `cisco/n9k-c9508` (1.2.0) and `cisco/n9k-c9516` (2.2.0)
  also accept the five batch-2 cards, which all three guides list, after the cards of batch 1 and the
  line-card blank, which every bay still seats. Every bay, default and configuration is unchanged. The
  fabric modules each card is paired with are recorded in the chassis' gap and not enforced. The DCIM device
  types of the three chassis differ only in the `Accepts:` text of their `lc-N` module bays and in the
  description sentence and drawing version the exporter writes from the chassis.

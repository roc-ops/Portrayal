### Changed
- A device's group `role` gains the value `stack-control`: the control and sync links between the units of a stack, never user
  traffic. It is its own bucket, so a filter on `traffic` counts only the ports user traffic can use and one on
  `management` only the ways in to the box. The data ports of a stack stay `traffic`. A group's `role` is what a consumer may rely
  on; the group's name promises nothing. The DCIM export treats it as a port role, as it does `traffic`.
- The Edgecore CSR310 (`edgecore/csr310`, 1.1.1 to 2.0.0) puts its STACK-CTRL and STACK-SYNC RJ-45 jacks in a new group,
  `stack-control`, with that role. Until now STACK-CTRL sat in `stacking` under `traffic`, so a filter on `traffic` counted it
  as a 1G service port, and STACK-SYNC sat in `timing` under `management`. The two stacking QSFP28 stay in `stacking` as `traffic`.
  Nothing drawn moves; the lock takes a major because two ports change group.

### Fixed
- `juniper/mx480` 7.0.0 and `juniper/mx240` 6.0.0: the line-card bays no
  longer accept the Switch Control Board `juniper/scb-mx@3`. The MX480
  hardware guide seats SCBs only in `scb0` and `scb1`, so `dpc0` to `dpc5`
  take line cards and blank panels only. On the MX240, `dpc1` and `dpc2` lose
  it; the multifunction slot `scb1-dpc0` keeps it, as the guide gives that
  slot to a DPC, MPC or SCB. The MX960 is unchanged: its multifunction slot
  `fpc6` (slot 2/6) takes either. A test now holds this for every MX chassis.

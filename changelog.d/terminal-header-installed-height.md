### Changed
- `common/terminal-header-508-2@3` and `common/terminal-header-508-5f@2` are
  drawn 8.6 high, the Phoenix Contact installed height, not the data sheets'
  `h` of 12.1, which counts the 3.5 solder pin under the board (#873). Both now
  claim their registry entries (`terminal-508-2-header`,
  `terminal-508-5-header`, whose `h` is now 8.6), and each `mate` sits at 4.3,
  on the axis the 508 plugs already assumed. The ten AurCore AIS switches seat
  the new majors (2.0.0), each placement moved 1.75 so the header's centre
  stayed put. The three 508 plugs take patch bumps for their provenance.

### Removed
- `common/terminal-header-508-2@2`, replaced by `common/terminal-header-508-2@3`,
  and `common/terminal-header-508-5f@1`, replaced by
  `common/terminal-header-508-5f@2` (#873). Element ids are unchanged.

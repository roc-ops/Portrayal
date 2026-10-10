### Changed
- **The end allowance is per media and covers only what is there**
  (`@portrayal/kit` 0.16.0, #962; `docs/cable-lay-design.md` section 1.6).
  A routed length is the path plus, at each end, the part of the plug inside
  the port and half the maker's short tolerance, where it was 0.15 m of
  unsourced dressing slack: 13.1 mm for LC fibre (generic/lc-plug@2; FS
  fibre cords are +x/-0), 34.5 for copper and a cable with no media (9.5 of
  generic/rj45-plug@1, and half of the 1 per cent a Brand-Rex Cat6A cord may
  be short at 5 m), 25 for a DAC (half the FS SFP+ DAC's +/-5 cm; its length
  is measured between the heads) and 52.4 for an AOC (generic/qsfp-cable@1's
  head in the cage; L-com's AOC is +x/-0). `END_ALLOWANCE` and
  `endAllowance(cable)` replace `END_ALLOWANCE_M`, and `routePath` returns
  its cable's `allowance`, which `pathLength` adds (a path without one takes
  the copper figure). Service loops and dressing slack belong in explicit
  tray slack (#949 step 4). Every routed length is shorter, by 195.2 to
  273.8 mm; on the owner's rack of #949 all sixteen cords are 0.5 m cords
  (fifteen were 1 m), and on a 3,120-cable generated sample 1,326 move down
  a stock size and none up. A saved rack's routed lengths and stock sizes
  are re-measured the next time a page measures them; an entered length is
  never touched. BREAKING for a page that imports `END_ALLOWANCE_M`.

### Changed
- **The end allowance is per media, sourced, with a temporary dressing
  allowance beside it** (`@portrayal/kit` 0.16.0, #962;
  `docs/cable-lay-design.md` section 1.6). A routed length was the path plus
  0.15 m an end, a figure with no source. The sourced part is now a table,
  `END_ALLOWANCE`, of what is physically there and not in the path: at each
  end, the part of the plug inside the port and half the maker's short
  tolerance. It is 13.1 mm for LC fibre (generic/lc-plug@2; FS fibre cords
  are +x/-0), 34.5 for copper and a cable with no media (9.5 of
  generic/rj45-plug@1, and half of the 1 per cent a Brand-Rex Cat6A cord may
  be short at 5 m), 25 for a DAC (half the FS SFP+ DAC's +/-5 cm; its length
  is measured between the heads) and 52.4 for an AOC (generic/qsfp-cable@1's
  head in the cage; L-com's AOC is +x/-0). The LC and RJ45 plug depths rest
  on estimates, which section 1.6 lists. Service loops and dressing slack
  belong in explicit tray slack (#949 step 4), which is not built yet, so
  until it is the kit adds a dressing allowance of 0.1 m an end on top, for
  every media: temporary, by decision, with no maker's source, and not
  exported. `endAllowance(cable)` gives the two together (113.1, 134.5, 125
  and 152.4 mm an end) and `routePath` returns it as the path's `allowance`,
  which `pathLength` adds (a path without one takes the copper figure);
  both, with `END_ALLOWANCE`, replace `END_ALLOWANCE_M`. A routed length is
  73.8 mm shorter for LC fibre, 31 for copper and 50 for a DAC, and 4.8 mm
  longer for an AOC. On the owner's rack of #949 seven of the sixteen cords
  move from 1 m to 0.5 m; on a 3,120-cable generated sample 221 move down a
  stock size and one moves up. A saved rack's routed lengths and stock sizes
  are re-measured the next time a page measures them; an entered length is
  never touched. BREAKING for a page that imports `END_ALLOWANCE_M`.

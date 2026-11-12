### Changed
- `cisco/asr-9001` takes a major (3.0.3 to 4.0.0): the 10MHz and 1PPS holes on the front panel are now filled by
  `common/din-1-0-2-3-jack@1`, the DIN 1.0/2.3 jack that Table 4 of the ASR 9000 Series Fixed-Port Routers Hardware Installation
  Guide names for both, and each hole takes that jack's round 5.59 mm opening where it was drawn at 4.0 mm. The ids `clk-10mhz`
  and `clk-1pps` are unchanged and now name two ports of the `timing` group; no id is removed or renamed, and the major is the
  geometry of the two holes. The gap that asked for the part is gone, and the 10MHz and 1PPS legends say which hole they name.
  This closes two of the front panel's holes that had nothing in them.

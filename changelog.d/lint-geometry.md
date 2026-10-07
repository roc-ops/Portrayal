### Fixed
- L39 centres a part's composed opening on its cutout, not the part's whole
  footprint (#248). `common/qsfp28-cage@3` carries the chassis lamp band above
  the cage, so its `std/qsfp-ganged@1` opening sits 4.2 mm below its top edge;
  the TE 2322551-4 drawing has the cage itself centred on that opening. Every
  correctly punched AS7726-32X port, and its USB beside a printed symbol, read
  as 1.5 to 1.74 mm off. The 33 baselined warnings are gone and no component
  or device changed.
- L46 measures what composed parts draw, not their boxes (#684). A pair whose
  boxes collide is measured again on each part's skin shapes (rects, circles,
  ellipses, polygons, text; a skin with a path or a transformed group counts as
  its whole box), so the open middle of `common/qsfp-pull-tab@2` and
  `common/qsfp-dd-pull-tab-type2@1` no longer reads as covering the bores and
  inserts it frames. Seven baselined warnings are gone, and the provenance
  sentences that explained them are removed from `generic/qsfp-lc@2` 2.2.2,
  `generic/qsfp-dd-lc@2` 2.2.1, `generic/qsfp-lc-simplex@1` 1.0.1,
  `generic/qsfp-mpo@1` 1.0.1 and `generic/qsfp-dd-mpo16@1` 1.0.1.

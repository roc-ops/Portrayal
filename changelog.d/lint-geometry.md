### Fixed
- L39 centres a part's composed opening on its cutout, not the part's whole
  footprint (#248). `common/qsfp28-cage@3` carries the chassis lamp band above
  the cage, so its `std/qsfp-ganged@1` opening sits 4.2 mm below its top edge;
  the TE 2322551-4 drawing has the cage itself centred on that opening. Every
  correctly punched AS7726-32X port, and its USB beside a printed symbol, read
  as 1.5 to 1.74 mm off. The 33 baselined warnings are gone and no component
  or device changed.

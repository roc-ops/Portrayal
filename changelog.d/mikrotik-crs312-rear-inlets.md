### Changed
- The MikroTik CRS312-4C+8XG-RM (`mikrotik/crs312-4c-plus-8xg-rm`, 1.0.0 to 1.2.3) draws its rear. MikroTik's brochure prints a rear
  photograph that shows two IEC C14 inlets, POWER 1 and POWER 2, each with the legend `100-240 V~1.5 A MAX 50/60 Hz`. The device
  places the library's `std/c14-inlet@1` twice, as `ac-inlet-1` and `ac-inlet-2`, so each is a place a power cord lands. The
  places are estimates read off a photograph taken slightly from above, good to about 2 mm. The rear also
  draws the four fan grilles (the library's vent pattern), the twelve crosshead screws (the library's screw head part), the
  spring wire clip over each inlet and the printed legends, all read from the same photograph. The device takes a minor, with its lock, and its
  exported device type in NetBox and Nautobot (2 files) gains two power ports of type `iec-60320-c14` and the new drawing version.
  No existing port, interface or id moves. One row of the records file is gone.
- The MikroTik CRS328-24P-4S+RM is not changed. No document held shows its rear or says where its AC inlet is, so its row of the
  records file stays.

### Changed
- The micro-USB ports and the front-panel RF test points of the CommScope CH3000 receivers (AR3002E,
  AR3044H, AR3044L, DR3450N, DR3600N), the HT358xH transmitter, the CC3008 control module and the four
  power supplies (PS3006D, PS3006N, PS3248D, PS3248N) now join a port group, so a port on a module seated
  in the chassis says what it is for: the micro-USB ports are `management` and the test points are
  `traffic`, as the test points of the passive modules already are. Neither group states a speed: the
  data sheets print no data rate for a service port or a test point. Part ids, positions and drawn
  geometry are unchanged; each of the eleven modules takes a minor, and the CH3000 takes a patch.

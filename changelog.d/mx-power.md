### Fixed
- The MX chassis state the power their vendor publishes (roc-ops/Portrayal#113).
  `power-typical-w` on the MX80 (310 W, output side, Tables 14 and 20),
  MX240 (1860 W), MX480 (3470 W) and MX960 (6520 W) - the last three from
  the family datasheet with the DC figure in `power-typical-scope` and
  `power-envelope: unstated` - and on the MX10004 (7.5 kW), MX10008 (12 kW)
  and MX10016 (23 kW), typical and fully loaded per their datasheets.
  `power-max-ac-w` 600 and `power-max-dc-w` 625 on the MX104 (input side,
  Table 6); 1520 W typical and 4420 W at 55 C on the MX2008 for the base
  system only (`power-envelope: bare`); the MX10003's `typical-draw-w` is
  now `power-typical-w` 1676 beside `power-max-w` 2110 (Tables 24 and 25).
  Provisioning ceilings go under `thermal.max-thermal-output`, flagged as
  ceilings (MX80, MX480, MX960). The MX2010 and MX2020 carry no figure: their
  guides contradict themselves, recorded as a `sources-disagree` gap scoped
  to both power facts. Five records that called the vendor silent or the
  tables unextracted are corrected (MX80, MX104, MX960, MX10004, MX10008).
  Each device is a patch version; the DCIM device-type exports change only in
  their comments.

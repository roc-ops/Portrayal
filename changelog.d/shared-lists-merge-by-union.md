### Changed
- **The exporter's register tables moved to `spec/tools/portrayal/dcim_registers.py`, and the
  maker registry, the connector registry and that file merge by union.** `NOT_A_DCIM_PORT`,
  `MGMT_NOT_A_DCIM_PORT`, `PART_OUTLET`, `OUTLET_LABEL` and `POWER_LABEL` are the same tables with
  the same entries, still read as `dcim_export.<name>`. A new `.gitattributes` keeps both sides'
  lines when two changes add an entry at the same place in one of those three files, so adding a
  maker, a connector key or a part the exporter names no longer needs a merge of main to settle
  it. `spec/tests/test_shared_lists_merge.py` holds the module to literal tables and fails on an
  entry written twice. No device, component or export changes.

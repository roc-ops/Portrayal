### Added
- The part-conformance runner has two new codes and a scan mode. C21 asks of every published
  connector or cage slot that its `accepts` hold a mate (a part of class `port` or `transceiver`),
  and C22 asks of every drawn `port` that it presents a registered interface, itself or through
  what it composes. `part_conformance.py --scan` judges C19 to C22 over every configuration of every
  device, with no cable laid, and records its wall-clock time, the CPU time of the node child and
  the load average.
- Every C19 to C22 finding lists every cause, never capped, each `{part, device, cfg, view, path}`.
- `unmated` in a component contract, a `connectors.yaml` entry or a `pluggables.yaml` family (a map
  from a rate to its sentence) says why no mate can exist. A contract's `unmated` is an optional key
  of at least 40 characters in the component schema.
- `library/conformance-exceptions.yaml` holds the rows of gaps a mate or a part can close, and
  `spec/tests/test_port_usable_records.py` holds them. The file has no rows and no `cap:`, so the
  test reports what it finds and passes until a later change writes a `cap:`.
- `part_conformance.py --by-family` sorts a scan's causes into families of port by the rules of
  `spec/tools/dev/port_families.yaml`.

### Changed
- C20 no longer skips a placed part that presents nothing as "a marking": it reports it unless the
  part carries `unmated`. C19 does not report a supply whose part carries `unmated`.

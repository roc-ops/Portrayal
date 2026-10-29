### Changed
- `edgecore/csr310-psu-ac@1` and `edgecore/csr310-psu-dc@1` (1.0.2), `edgecore/agr-psu-ac@1` (1.0.1) and
  `edgecore/agr-psu-dc@1` (1.0.2) state `attrs.input` as `ac` or `dc` and keep the range sentence they carried,
  word for word, in `attrs.input-note`. A consumer that reads a build's supply type takes only `ac`, `dc` and
  `hvdc` from `input`, and read the sentence as "not stated", so neither build of the devices that seat them was
  recognised as AC or DC. `edgecore/csr310` (1.0.7), `edgecore/csr430` (1.0.8), `edgecore/as7946-30xb` (4.0.6)
  and `edgecore/as7946-74xksb` (4.0.6) take a patch bump. No drawing, size, port or id changes. The DCIM
  exports' module-type comments list the two attrs; no port, name or interface type changes, so this is not
  breaking.

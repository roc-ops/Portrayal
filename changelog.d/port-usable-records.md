### Added
- `library/conformance-exceptions.yaml` holds the starting list of port-usable findings: 222 rows (C19
  172, C20 35, C22 15), one per part or device and code, each naming the open issue that closes it,
  with `cap: 222`. From this change `spec/tests/test_port_usable_records.py` fails a pull request on a
  finding that no row, mate or `unmated` sentence covers, on a row whose finding no longer occurs, on
  more rows than the cap, and on a runner that fails or times out.

### Added
- `edgecore/dcs500-psu-dc@1` (1.0.0): the Edgecore DCS500 (AS7816-64X) 850 W -36 to -72 VDC
  supply, input `dc`, inlet `dc-terminal`, a three-pole barrier terminal block on the AC
  supply's borrowed 50.9 x 39.4 envelope. It is named for neither FRU (YM-2851J ER and FR
  differ only in airflow), and the terminal block is drawn from the quick start's photograph
  of the terminal end, so its position is estimated. A DCIM module type is exported for it.

### Changed
- `edgecore/dcs500` 4.0.0 to 4.1.0: the two rear supply bays accept the AC and the DC supply,
  and two orderable configurations are added, `dc-f2b` (7816-64X-O-48V-F-R, FP3ZZ7664024A) and
  `dc-b2f` (7816-64X-O-48V-B-R, FP3ZZ7664026A), each seating the DC supply through `bays`.
  The DC builds are sold only in the O series and wear this device's OZ labels as a declared
  stand-in; the `o-series-numbering` gap says so. DCIM device types are exported for both.
- `edgecore/dcs500-psu-ac@1` 1.0.0 to 1.0.1: its `dc-build` provenance sentence no longer says
  the DC supply is not modelled. No drawing change.

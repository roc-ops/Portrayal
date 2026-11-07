### Changed
- `celestica/ds6000` 0.1.1 to 0.1.2: the chassis states `airflow: front-to-back`, so the
  `ac-f2b` and `dc-f2b` builds resolve to it and `ac-b2f` keeps its own `back-to-front`. The
  data sheet's three order lines end in `F2B`, `F2B` and `B2F`. The index's airflow options
  for the DS6000 gain `front-to-back`, the drawn fans and supplies of the two front-to-back
  builds carry `data-config-airflow`, and the DCIM device types for `R4087-F9004-A1` and
  `R4087-F9005-A1` gain `airflow: front-to-rear`; the two `R4087-F9013-A1` types change by the
  drawing version line only. Nothing is drawn differently.

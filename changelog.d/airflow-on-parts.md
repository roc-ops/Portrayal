### Added
- Every fan and supply in a compiled face carries `data-config-airflow`, the
  airflow of the configuration it is drawn in (`front-to-back` or
  `back-to-front`), and nothing where the configuration states none. A tool
  filtering by airflow can check that the fans and supplies drawn in a build
  are the ones for that direction. `data-airflow` on a unit is unchanged: it is
  still the part's own statement. `docs/format-stability.md` lists it.
- `library/components/README.md` has an "Airflow" section: the values of
  `attrs.airflow`, how a build restates it, and how to read each vendor word a
  fan or supply uses (`exhaust`, `intake`, `port-side intake` and the rest),
  with the words that are not mapped (#1329).

### Changed
- The back-to-front builds of `edgecore/ais800-32d`, `ais800-32o`, `ais800-64d`,
  `ais800-64o`, `as5912-54x`, `as7326-56x`, `as7726-32x`, `dcs201`, `dcs202`,
  `dcs240`, `dcs510`, `dcs511`, `eps201` and `exp800-16o` state
  `airflow: back-to-front` on each fan and supply they recolour, as the Cisco
  and UfiSpace builds do. Each of the 14 devices takes a patch version (#1329).

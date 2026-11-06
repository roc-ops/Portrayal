### Added
- `edgecore/cor550-psu-dc@1`, `edgecore/fsj033-610g@1` (FSJ033-610G, 1300 W 48 VDC) and
  `edgecore/csr440-psu-dc@1` (`AS7535-28XB DC PSU`), the DC supplies of the COR550, COR580 and
  CSR440. Each is drawn from the terminal-end illustration in the device's quick start, with the AC
  supply's envelope borrowed and every position on the face estimated; each states `input: dc`,
  `inlet: dc-terminal` and the quoted range in `input-note`. No photograph or 3D model of any of
  the three is held.

### Changed
- `edgecore/cor550` is 3.1.0, `edgecore/cor580` 3.1.0 and `edgecore/csr440` 2.1.0: the supply bays
  accept the DC part too, the DC configurations seat it through `bays:` and the `component-attrs`
  override that drew the AC face is removed, so each build now reads `ac` or `dc`. The DC gaps are
  restated as what remains: the borrowed envelope, the illustrated face and the values not stated.
  The three devices are re-locked, and the DCIM device types and the three module types are
  re-exported.
- `edgecore/cor550-psu-ac@1` is 1.0.1 (its provenance no longer says the DC build is not drawn) and
  `edgecore/csr440-psu-ac@1` is 1.1.2 (`input: ac`, the range sentence unchanged in `input-note`,
  and the same provenance correction).

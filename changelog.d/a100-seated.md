### Added
- `nvidia/a100-pcie-80gb@1` is two slots wide (`slot-width: 2`) and seats in
  `dell/riser-1a-14g@2`'s `slot-1`, which spans `slot-2`. The Dell R740xd has
  an example configuration, `sff24-rc4-1a2a3a-a100`, that seats it there and
  empties `slot-2`.
- The A100's connectors are parts that mate: `std/eps12v-header@1` (`aux-power`,
  the CPU 8-pin) on its rear face, and three `nvidia/nvlink-a100-connector@1`
  (`nvlink-1` to `nvlink-3`, under the caps) on its new plan face,
  `nvidia/a100-pcie-80gb-top@1`, which is the top edge seen from outside.
- The A100's module type in the NetBox and Nautobot exports carries a power
  port, `aux-power`, type `other`, labelled "EPS12V 8-pin (CPU 8-pin)".

### Changed
- The DCIM module export reads the power inlets composed on a card's rear face
  (`faces.POWER_FACES`), not only those in its own `parts:`. No other card's
  export changes.
- `dell/riser-1a-14g@2` (2.3.0) accepts the A100 in `slot-1`. `dell/r740xd`
  (29.0.0) gains the example configuration; the lock asks a major bump for a
  configuration added to the placements' `only-in` lists.
- `nvidia/a100-pcie-80gb@1` no longer carries the attr `slots: 2`; `slot-width`
  says it, and nothing read the attr.

### Removed
- `nvidia/a100-eps12v-standin@1`, the stand-in for the EPS12V header, which was
  never in a release and which `std/eps12v-header@1` replaces.

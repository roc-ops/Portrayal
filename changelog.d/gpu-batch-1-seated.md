### Added
- `nvidia/a100-pcie-40gb@1` (two slots wide) and `nvidia/l4@1` (one slot, full
  height) seat in `dell/riser-1a-14g@2`'s `slot-1` on the Dell R740xd. The
  A100 40GB covers `slot-2`; the L4 needs no span and stays out of `slot-3`.
  Dell's R740xd manual (table 27) lists double-width GPUs, the A100 among them,
  in riser 1A's slot 1, and its spec sheet caps them at 300 W.

### Changed
- `dell/riser-1a-14g@2` (2.4.0) accepts the two cards in `slot-1`. `dell/r740xd`
  (29.0.2) is re-locked.
- `nvidia/h100-pcie@1`, `nvidia/h100-nvl@1` and `nvidia/l40s@1` stay unplaced:
  at 350 W, 400 W and 350 W they are over the R740xd's 300 W double-width GPU
  ceiling, and no other riser in the library spans. Their `unplaced:` notes say
  so.

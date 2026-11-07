### Added
- The SFP-DD cage (#1204): `std/sfp-dd@1`, a single cage with a 15.45 x 10.40 panel opening, and `std/sfp-dd-ganged@1`, its
  14.25 x 10.40 share of a ganged 1xN slot. Both are drawn from two cage makers' own drawings (TE Connectivity C-2359845
  and application specification 114-60027; Molex 2048233001 and application specification 2048230001), with a 14.00 x 8.95
  port interior and a 38.90 bezel-to-guide-pin depth from TE. The MSA was not used. No device places either cage yet.
- `sfp-dd` and `sfp-dd-ganged` entries in `spec/schemas/standards.yaml`. The lane count, the rates and whether an SFP module
  is specified to work in the cage are marked unconfirmed, because only the MSA settles them.
- The DCIM export types a placement of either cage, and a port that states `media: sfp-dd` and `speed: 100g`, as
  `100gbase-x-sfpdd`, the name NetBox and Nautobot both give an SFP-DD interface. A port stating 50g is not typed, as neither
  has a 50G SFP-DD type, and an SFP-DD cage no longer types as an SFP28 one by the "sfp" in its name.

### Changed
- `spec/schemas/pluggables.yaml` no longer says the `sfp-dd` family has no cage, and lint L103 now reports no family. The
  DSFP cage is not added, as no maker publishes a drawing of it.

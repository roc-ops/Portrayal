### Changed
- `juniper/mx960-blank@1` 1.1.0 carries `model: DPC-SCB-BLANK`, the MX960
  guide's Table 5 part number (#899). **Breaking for DCIM data already
  imported**: its module type is renamed from `mx960-blank` to `DPC-SCB-BLANK`.
- `juniper/mx960-craft@2`: the fourteen slot clusters sit where the MX960
  photograph puts them relative to the slots, at 16.65 + 31.40 k, instead of on
  the retired 30.1 slot pitch (#899).
- `juniper/mx960` 5.0.0: a new orderable `ac` configuration, the chassis as
  photographed (DPC 40xGE in slots 1 and 3, DPC 4x10GE in 7 and 9), so a seated,
  turned line card renders in the build and in CI (#899).
- `juniper/mx240` 5.0.1, `mx480` 6.0.1, `mx960`: a `slot-pitch` note on why the
  three chassis read 31.0, 31.3 and 31.0 for one card, and why the guides'
  1.25 in is the card's height and not a pitch (#899).

### Removed
- `juniper/mx960-craft@1`, replaced by `juniper/mx960-craft@2` (#899). Nothing
  seats it any more, so per #448 it is removed rather than kept.

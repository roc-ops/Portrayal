### Changed
- Juniper's DPC and SCB slot blank is one part, DPC-SCB-BLANK, in the MX240, MX480 and MX960 (Table 5 of the MX480
  and MX960 hardware guides). `juniper/mx-dpc-blank@2` is 2.1.0 and carries the part number as its model; it has
  a second skin, `plain`, without the printed 0/1 rotary mark the MX480 photograph shows beside the left knob, and
  the MX960 uses it, as its photograph shows no mark. **BREAKING for DCIM data already imported**: the module
  type that was named by its description, `MX Series DPC slot blank`, is now `DPC-SCB-BLANK`, so the one blank is
  written once and the old name is no longer in the exports. The MX240 and MX480 are 6.3.1 and 7.3.1; the MX960
  is 6.0.0, with its slots seating the one blank and its gap on the card catalogue noting it.

### Removed
- `juniper/mx960-blank@1`, replaced by `juniper/mx-dpc-blank@2`, which supersedes it, so a saved rack that names
  the old ref is sent to the new one. The module type `DPC-SCB-BLANK` it exported is now written from
  `juniper/mx-dpc-blank@2`, and the module type `MX Series DPC slot blank` is gone.

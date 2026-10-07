### Changed
- The MPC1E, MPC2E and MPC3E carriers (`juniper/mpc1e-3d`, `mpc2e-3d`,
  `mpc3e-3d` and the `-v2k`/`-v960` form of each, 1.2.0) are each their base
  SKU and nothing else (#417). `power-draw-max-w` is the base row of the MX240
  guide's Table 93: MPC1E 175 -> 165 W, MPC2E 294 -> 274 W, MPC3E 440 W. Each
  bay's `accepts` is exactly that SKU's column of the Interface Module
  Reference Tables 10-12, so the MPC1E no longer takes the 4x10GE XFP, the
  10GE SFP-E, the ATM or the three channelized/CE OC3 MICs, the MPC2E no
  longer takes the 10GE SFP-E, the ATM or those OC3 MICs, and the MPC3E no
  longer takes the 4x10GE XFP, the 10GE SFP-E or the ATM MIC; the MPC3E now
  takes the OC192 XFP, both multirate OC3/OC12/OC48 MICs, the DS3/E3, the
  MACsec 20GE and the MS-MIC-16G. `model-variants` keeps only the SKU that
  shares the row and the column (MX-MPC1-3D, MX-MPC2-3D). The queuing, P and
  NG SKUs are not these contracts and will be their own parts. The MX240,
  MX480, MX960, MX2008, MX2010 and MX2020 take a patch.
- **BREAKING for DCIM data already imported:** the MPC3E module type is now
  named by its part number, `MX-MPC3E-3D`, not its component name `MPC3E`
  (#417). Its NetBox and Nautobot module-type file is renamed to match, and an
  import keyed on the old model creates a second module type rather than
  updating the first.
- **BREAKING for DCIM data already imported (Nautobot):** no carrier now
  takes `MIC-3D-10GE-SFP-E` (#417; it fits only the NG MPCs, which are not
  modelled yet), so its Nautobot module type names its ports
  `{module}/port-0-N` instead of `{module.parent}/{module}/port-0-N`. The six
  MICs no carrier takes say so in `unplaced:`.
- `juniper/mic-3d-4xge-xfp@2` and `mic-3d-4xge-xfp-v@2` (2.0.0): the four XFP
  cages are re-laid from the Interface Module Reference's Figure 31
  (g100580), measured on the embedded image and scaled on the 19.5 mm XFP
  opening, at a pitch of about 32.7 mm instead of the guessed 22.0 and 21.1
  mm (#238). The card keeps its size. The MPC2E carriers seat the new
  majors.

### Removed
- `juniper/mic-3d-4xge-xfp@1` and `juniper/mic-3d-4xge-xfp-v@1`, whose cages
  were laid out from registry sizes rather than measured (#238). Pin
  `juniper/mic-3d-4xge-xfp@2` and `juniper/mic-3d-4xge-xfp-v@2` instead.

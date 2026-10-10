### Changed
- Every horizontal Juniper MIC is its own plate, 168.8 x 29.2, measured off
  the MX104 and MX80 front photographs (#261). It was the estimated 168 x 27
  "window". The 20 single-wide MICs take a major (`juniper/mic-3d-4xge-xfp`
  @2 to @3, the others @1 to @2) and their art is re-enveloped, not redrawn.
  The two dual-wide MICs, `juniper/mic-3d-40ge-tx@2` and
  `juniper/mic3-100g-dwdm@2`, are one 338.1 x 29.2 plate across both MIC
  slots, as the MX2010 photograph shows a dual-wide MIC.
- The MICs the photographs show are drawn from them:
  - `mic-3d-2xge-xfp@2` has its cages at 45.4 and 91.75 along the plate,
    where they were at 25.75 and 54.75.
  - `mic-3d-4xge-xfp@3` has its cages at 31.8, 65.9, 99.8 and 133.7, a 34.0
    pitch, read off the MX2010. The Figure 31 reading it replaces was about
    3% stretched.
  - `mic-3d-20ge-sfp@2` has its two five-cage blocks centred at 46.85 and
    121.4.
- `juniper/mpc1e-3d@3`, `mpc2e-3d@3` and `mpc3e-3d@3`: the two MIC bays are
  the measured plate, abutting at the card plate's centre (x 37.7 and 207.0,
  y 0.15).
- `juniper/mx104` 4.0.0: the MIC bays sit on the measured 169.3 pitch
  (x 17.8 / 187.1; it was 175.2) and at rows y 42.6 / 74.1, which were 6 to
  7 mm low.
- `juniper/mx80` 3.0.0: the MIC bays sit at x 28.7 / 198.3, y 6.5.
- `juniper/mx240` 4.0.0, `juniper/mx480` 4.0.0 and `juniper/mx960` 3.0.0
  seat the @3 carriers.
- `juniper/mx2008`, `juniper/mx2010` and `juniper/mx2020` 1.0.0:
  - Each LC slot seats the new adapter card. The slots are the adapter's
    43.18 x 449.8 on a 43.18 pitch, which three front photographs confirm.
    They were an estimated 41.0 x 425.0 on 41.0.
  - The native MX2K cards and the slot blank keep their estimated size,
    centred in the slot.
  - The MX2010 gains a `photographed` example configuration.
- `nokia/m2-oc192-xp-xfp` 1.0.1 names `juniper/mic-3d-1oc192-xfp` without
  the major it retires; `nokia/sr-7` and `nokia/sr-12` take the patch.
- Deprecated, not deleted: each part below stays in the library, marked
  `superseded-by:` its replacement and given a patch bump, so a manifest
  that pins it still resolves (#448). No device seats them any more.
  - The eleven MX2000 vertical card twins, `juniper/<base>-v2k@1` for
    `mpc-3d-16xge-sfpp`, `mpc1e-3d`, `mpc2e-3d`, `mpc3e-3d`,
    `mpc4e-3d-2cge-8xge`, `mpc4e-3d-32xge-sfpp`, `mpc5e-100g10g`,
    `mpc5e-40g10g`, `mpc7e-10g`, `mpc7e-mrate` and `ms-mpc`, each superseded
    by `juniper/<base>@2` (`@3` for the MPC1E/2E/3E), which the MX2000 slots
    seat inside `juniper/mx2000-lc-adapter@1`.
  - The twenty vertical MIC twins, `juniper/<mic>-v@1`
    (`mic-3d-4xge-xfp-v@2`), each superseded by the horizontal MIC's new
    major. `juniper/mx-mic-blank-v@1` is live, because the native MPC8E and
    MPC9E seat it.
  - The old majors of the 22 MICs, blank included (`@1`;
    `mic-3d-4xge-xfp@2`), and of the three carriers (`@2`), each superseded
    by its next major above.
- The DCIM module export leaves out a contract that carries
  `superseded-by:`. A retired major shares its successor's model, and
  exporting both wrote one file twice. `components.json` now carries the
  `superseded-by` field.

### Added
- `juniper/mx2000-lc-adapter@1`, the MX2000-LC-ADAPTER (ADC, 150 W). It
  seats an MX240-form MPC turned 90 in its one bay, `mpc`, as the MX960
  seats it. Its module type exports as `MX2000-LC-ADAPTER.yaml`.
  - In NetBox an MPC installed under the adapter names its components
    `fpcN/mpc/...`.
  - Nautobot is not given the adapter's `mpc` bay, because the same MPCs
    also seat directly in the MX240, MX480 and MX960. Superseded by the
    Nautobot entry under Fixed (#917): Nautobot has the bay today, with a
    blank position.

### Removed
- `MIC-3D-4COC3-1COC12-CE` loses `port-1-0` to `port-1-3`: `juniper/mic-3d-4choc3-1oc12@1`
  drew eight cages in two PICs, while the card has four OC3/STM1 ports,
  numbered 0 to 3. The module reference states it and the MX104 photograph
  shows it. `@2` has `port-0-0` to `port-0-3`, and the module type is
  written from it. **BREAKING for DCIM data already imported.**
- `juniper/mic3-100g-dwdm` leaves the MPC3E's MIC bays: it is dual-wide, and
  no bay can take a module that fills two (`unplaced`, as
  `mic-3d-40ge-tx`).
- Nautobot module types `MIC-3D-4XGE-XFP`, `MIC3-3D-10XGE-SFPP`,
  `MIC3-3D-1X100GE-CFP`, `MIC3-3D-1X100GE-CXP`, `MIC3-3D-2X40GE-QSFPP` and
  `MIC3-100G-DWDM` name their interfaces `{module}/port-...`. They were
  `{module.parent}/{module}/port-...`. The exporter writes the one-token
  name for a model seated at several depths or at none. The first five are
  now seated at two depths: in an MPC on the MX240 to MX960, and in an MPC
  inside the adapter on the MX2000. `MIC3-100G-DWDM` is seated nowhere,
  because no bay can take a dual-wide MIC (above). NetBox is unchanged.
  **BREAKING for DCIM data already imported** (Nautobot). Superseded for the
  first five by the Nautobot entry under Fixed (#917), which gives them
  `{module.parent}/{module}/port-...` again. Of the six, only
  `MIC3-100G-DWDM` keeps the one-token name today.

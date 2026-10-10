### Added
- The Dell PowerEdge R660 (`dell/r660`, `draft`), a 16th-generation 1U
  two-socket server, 434.0 x 42.8 x 773.5 (#721):
  - Five fronts as variant views: ten 2.5 inch bays (`front`), eight with a
    Smart Flow vent (`front-sff8sf`), no backplane (`front-nobp`), and
    sixteen or fourteen EDSFF E3.S (`front-e3s16`, `front-e3s14`).
  - A rear whose riser band takes riser configurations 0 to 9, and a top
    view of the interior into which seated supplies, risers, cards and front
    drives project. The bottom and sides are estimates.
  - 42 orderable configurations, named `<front>-rc<n>-<risers>`, and four
    examples. Its NetBox and Nautobot device types are named
    `PowerEdge R660 <configuration>`.
  - The riser slots accept the cards the R740xd slots accept: the generic
    brackets and cards and the NVIDIA ConnectX adapters, and on the
    full-height risers 1P and 4P the UfiSpace N3100-4C.
- The `dell/` parts the R660 needs, 71 component majors on main today, among
  them: the 60 mm AC supplies
  (`dell/psu-700w-ac-60mm@1`, `-800w-`, `-1100w-`, `-1400w-`); six OCP NIC
  3.0 cards and a blank (`dell/ocp3-*`); the LOM card, the MIC card and the
  rear I/O board; the BOSS-N1 module, its M.2 carrier and blank; the E3.S
  carrier, blank and fillers; twelve 16G risers (`dell/riser-1p-16g` to
  `riser-4p-16g`) and the cages they compose; the interior plan parts; and
  the 1U 16G bezel, drawn fitted.
- `std/drive-e3s@1` and the `drive-e3s` standard in
  `spec/schemas/standards.yaml`: the EDSFF E3.S drive, 76.0 x 7.5 x 112.75,
  which the E3.S bays accept beside `dell/e3s-carrier@1` (#721).

### Changed
- `dell/r660` took five majors between its first merge and today, none of
  them in a release. Each is listed for a consumer of main or of the npm
  packages:
  - 1.0.0: riser 3 starts at x 270.6, where the cage of riser 2 ends, and
    slot 3 is back at 268.5 (#743). Before that, low-profile slots were
    re-handed (slot 1 turned over, slots 2 and 3 tip-left) and every riser
    gained its 3D boxes, as patches (#726, #729).
  - 2.0.0: the Gen5 riser print, riser configuration 9 and the redrawn E3.S
    blank, with the six removals listed under Removed (#749).
  - 3.0.0: the rears not yet drawn. `dell/riser-blank-full-16g@1` and five
    `<front>-rc0-none` configurations for no risers,
    `dell/rear-io-board-dlc-16g@1` for liquid cooling, and examples without
    a LOM card and with the MIC (#750).
  - 4.0.0: riser 2S, the liquid-cooling module `dell/dlc-module-1u-16g@1`
    and the PCH shroud in the top view. The heatsinks are `only-in` every
    configuration but the liquid-cooled example (#751).
  - 5.0.0: risers 2Q, 1P and 4P project into the top view, as estimates
    (`size-confidence: estimated`), and the gap that names them is renamed
    `risers-2q-1p-4p-from-above-estimated` (#753).

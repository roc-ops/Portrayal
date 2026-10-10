### Added
- Lint L172 (error): whatever is named for a logo is a reserved place and
  paints nothing (#964). A contract element, a skin node or a device region
  whose id has the word `logo` in it is `logo-zone` (or `logo-zone-<n>`); the
  skin node is an empty `rect` with `fill="none"` and no stroke; the region
  states `at` and `size`; and no decor, cutout, silkscreen mark, bay or
  placement of a device carries the word. The library is clean under it and
  nothing was added to the lint baseline. The rule reads names only: a box
  standing for a mark under another name is not caught.

### Fixed
- Vendor marks are reserved, not drawn or boxed, on fifteen devices and one
  component (#964). No DCIM export changes and nothing is renamed.
  - Edgecore: `edgecore/dcs240` 1.1.9 drops the grey `brand-badge` box that
    stood for the logotype and reserves its measured box as the region
    `logo-zone`; `edgecore/dcs511` 2.0.9, `edgecore/eps121` 2.0.8 and
    `edgecore/eps122` 2.0.9 gain the region where the logotype sits.
  - FS blanking panels: `fs/fhu-bps-1u-10`, `fhu-bps-2u`, `fhu-bps-4u`,
    `fhu-bpstl-1u-10`, `fhu-bpstl-2u`, `fhu-bpstl-4u` and `fhu-bpa-1u-10`
    (each 0.1.1) gain a `logo-zone` region at the mark measured on the
    straight-on render; `fs/fhu-bpad-2u` and `fs/fhu-bpad-4u` 0.1.1 gain one
    region per unit, `logo-zone-1` upward, inside the recess each unit
    already draws.
  - Casa: `casa/chassis-label@1` 1.4.0 no longer draws a black triangle where
    the vendor mark sits; the skin node `logo` is gone and the measured box is
    the element `logo-zone`, left empty. `casa/c100g` 1.0.2 and `casa/c40g`
    0.5.20 take the patch for the part they place.

### Added
- Two more APC cable managers for NetShelter SX cabinets (#1097, part of #1091), modelled from APC's own data sheets and
  installation sheets. `apc/ar7721` is two 20U lengths for a 600 mm wide 42U cabinet (107 x 1778 x 45 mm, 40 crossbars,
  one to each rack unit). It places a new version of the 20U length, `apc/nsx-vcm-20u@2`, twice. Version 1 is unchanged
  and the AR7722 still places it. `apc/ar7502` is a perforated rear cable channel for a 42U cabinet (117 x 1930 x 13 mm).
  It is drawn with its 4 mesh windows, 12 keyholes and 18 hook slots. A column of rack-unit slots runs down each edge.
  Each device is `chassis.mount: rack-side` and is drawn on all six sides. Neither has a connector, and APC states no
  cable capacity for either. It closes no row of the conformance records. AR7710 and the other parts that share the
  AR7502's installation sheet are not in this change.

### Changed
- `dell/r740xd` takes three majors, 24.0.1 to 27.0.0. No placement, bay or
  port id changes in any of them, and each major is one change:
  - 25.0.0 adds the example configuration `sff24-rc4-1a2a3a-connectx-100g`:
    the NVIDIA ConnectX-6 Dx MCX623106A in riser 2, `nvidia/mcx623106-fh@1`
    in slot 4 and `nvidia/mcx623106-lp@1` in slot 6 (#702). It joins six
    `only-in` lists, which the lock counts as a placement change. The device
    has 43 configurations.
  - 26.0.0 seats `common/drive-carrier-25@2` and `common/drive-blank-25@2`
    in every 2.5 inch bay, in place of the `@1` of each (#721). The bays keep
    their size and ids.
  - 27.0.0 states `chassis.ru: 2` (#741). The DCIM device types export 2U
    where they exported 1U, as the height entry in this section says.

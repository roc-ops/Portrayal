### Changed
- Nine Arista 7280R3 builds state their own hardware and a DCIM description of their own, and the open gap
  `config-scoped-device-attrs` closes on five devices (five rows). The 7280CR3K-32P4 and 7280CR3K-32P4A (each
  front-to-rear and rear-to-front), the 7280CR3K-96, the 7280DR3K-24, the 7280PR3K-24 and the 7280SR3E-40YC6-M
  (front-to-rear and rear-to-front) take a description of their own and, where the 7280R3 Series Data Sheet
  prints one value for their column, their own memory, CPU, storage and minimum EOS. Where it prints a choice
  (the base models' "8 GB (64 GB optional)") the device's own line stays. No build states a power figure of its
  own: the guide's Table 4 gives every build of these five devices the device's figure.
- The DCIM device types of the five devices change in the NetBox and Nautobot exports (16 types, 32 files): the
  nine builds above gain a description of their own and their own memory, CPU, storage and EOS lines in
  `comments`, and every type of the five devices carries the new drawing version. No model, slug, part number,
  port, interface or bay name changes, so a DCIM that already imported these types keeps the old text until it
  imports them again.

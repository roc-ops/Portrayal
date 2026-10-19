### Changed
- **BREAKING for DCIM data already imported: the three `nokia/lmfs-f` device
  types are now filed under the product name, with the mnemonic in brackets,
  as the 7360 ISAM FX shelves are** (#997). `nokia/lmfs-f` is now at 2.0.0, a
  major because the rename is one-way. `LMFS-F`
  becomes `Lightspan MF-8 (LMFS-F)`, `LMFS-F AA kit` becomes
  `Lightspan MF-8 (LMFS-F) AA kit` and `LMFS-F AB kit` becomes
  `Lightspan MF-8 (LMFS-F) AB kit`, in both the NetBox and the Nautobot export.
  The six files of the old names are gone and a DCIM that imported them keeps
  the old device types, which no longer match. The six new files differ from
  the old ones only in the names and the drawing version. The part numbers (3FE 79748 AA,
  3FE 79747 AA, 3FE 79747 AB), `model: Lightspan MF-8` and the `LMFS-F` alias
  are unchanged, so a search on the mnemonic still finds the shelf. A test now
  fails a device that exports under a `kind: vendor` alias of its own.

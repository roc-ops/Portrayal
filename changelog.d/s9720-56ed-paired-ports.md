### Changed
- `ufispace/s9720-56ed` (3.0.5) states 18 of its 36 service cages as 100/200/400/800G and the other 18 as
  100/200/400G, on each placement's `speed` and `speeds`, from the installation guide's page 12 and Figure 9
  (each pair of cages runs as one 800G port or as two ports at 400G or lower). The blue label patch is drawn
  beside the 18 cages the vendor marks and no longer beside the other 18. `attrs.performance` states the pair rule
  (`port-modes-qsfp-dd`) and `attrs.features` the ZR/ZR+ ports (`zr-ports`), and two gaps record that the pair exclusion has no
  field and that the guide's text does not say which cage of a pair runs the 800G port. **BREAKING for DCIM data
  already imported**: the 18 cages that state 400G are typed `400gbase-x-qsfpdd` in the NetBox and Nautobot
  device types instead of `800gbase-x-qsfpdd`, so a DCIM that already imported this device keeps the old types.
  No port, name, id, position or size changes, and the group id `qsfpdd-800g-service` is unchanged.

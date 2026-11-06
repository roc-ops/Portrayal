### Added
- **`std/nema-5-15r@1`, the NEMA 5-15R receptacle face.** A flat 27 x 27 face
  with a U earth hole and two parallel slots, no T, presenting the registered
  `nema-5-15r` interface at a `mate` point. A PDU that places it offers each
  outlet as a connector slot, and `generic/nema-5-15p-cord@1` seats in it; a
  5-20P does not. No dimensioned drawing of a 5-15R is held, so the size, the
  holes and the mate are borrowed from the 5-20R's drawing and declared as
  such in the contract and in the new `nema-5-15r` entry of `standards.yaml`.
  The registry entry `nema-5-15r` now cites that standard.
- DCIM: `nema-5-15r` joins `OUTLET_TYPES` and `PART_OUTLET`, so an outlet of
  this part exports as a `nema-5-15r` power outlet in NetBox and Nautobot. No
  device places the part yet, so no committed export changes.
- It closes no records row.

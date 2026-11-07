### Fixed
- `cisco/asr-9006`, `asr-9904`, `asr-9906`, `asr-9910`, `asr-9912` and `asr-9922` now
  accept `cisco/a9k-mod400-se@2`, `a9k-mod400-tr@2`, `a9k-mod200-se@2` and
  `a9k-mod200-tr@2` in every line card slot, as the `asr-9010` already did. Cisco data sheet
  c78-735809 (p4, and Table 2, "Chassis compatibility", with its per-chassis card counts)
  names all seven routers; each chassis cites it in its provenance, and its line card slot
  count equals Table 2's maximum. The RSP and RP slots do not take them. The MOD80 and MOD160
  are not in that data sheet and stay where they were. The DCIM exports change in their slot
  bay descriptions (#885).
- The skins of all four cards changed so the card seats in a rotated slot the way the slot
  cover does. On the MOD400 cards the recessed field runs the slot's full length like the
  cover, and STATUS sits inside the plate. The MOD200 cards use the cover's plate, ears,
  screws and recess. The four components take a patch bump for the art.
- Versions: `a9k-mod400-se`, `a9k-mod400-tr`, `a9k-mod200-se` and `a9k-mod200-tr` (all v2)
  are 2.1.1. `asr-9006` and `asr-9904` are 3.2.3, `asr-9906` and `asr-9910` are 1.2.3,
  `asr-9912` and `asr-9922` are 2.1.3, and `asr-9010` is 1.1.3.

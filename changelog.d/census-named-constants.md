### Changed
- A test-only change, with no behaviour change. The census counts of
  `test_ground_stud_lugs.py` and `test_occupant_turn.py` are named module-level
  constants (`GROUND_SCREW_COUNT`, `GROUND_SCREW_LOCATIONS`, `STUD_SEATS_SEEN`,
  `STUD_PLACEMENTS`, `STUD_DEVICES`, `RING_DEVICES`, `PAIR_DEVICES` and
  `CROSSED_SEATS`) instead of numbers inside assertions. Each keeps its value and
  its comments, and `test_census_constants.py` keeps them named.

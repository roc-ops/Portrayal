### Changed
- The part-conformance check counts only the supply bays a configuration has. A bay that states `only-in` belongs to the
  configurations it names and is left out of every other, as the drawing leaves it out, so a configuration whose own supply bays
  are all open (a spare chassis) is no longer held to the defaults of a bay it does not have. The EX6210 spare chassis, whose
  3 U supply bays belong to the 5000 W build alone, stops being reported as powered with no power end offered.
  Nothing in the library, its exports or any lock changes.
- One row of the port-usable records file is gone: the EX6210 device row.

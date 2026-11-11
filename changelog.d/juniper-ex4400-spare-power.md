### Changed
- The spare chassis of seven Juniper EX4400 switches (the EX4400-24P-S, -24MP-S, -48P-S, -48MP-S, -24T-S, -48T-S and -48F-S)
  now says what feeds it, so a tool filtering by feed no longer misses the spare. The spare ships with no power supply, so the
  value comes from the hardware guide and not from a supply the build seats. `power` is `ac` and `dc` on each spare build: for
  the four PoE and multigigabit spares the guide's power supply ratings tables print a 1600 W AC row (the 24P-S and 24MP-S) and
  a 2000 W DC row for all four, and for the 24T, 48T and 48F the guide says the model supports 550 W AC or DC supplies. The
  48F-S also takes a 550 W variable DC supply (120 to 310 VDC), which this field has no word for, so it is not stated and the
  `vdc-supply` gap stays. Every other build of the seven devices is unchanged, and no bay, port or part changes. The seven
  devices each take a patch, with their locks, the `power` of the spare in its `configs` file and in the `options` of the
  device, and the version line of their exported device types. The lint baseline no longer records the missing feed (L119) of
  these seven devices. This closes no row of the port records.

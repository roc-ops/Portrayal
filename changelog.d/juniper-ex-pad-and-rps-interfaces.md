### Changed
- `juniper/ex4100-h-terminal-pad@1`, the wire terminals behind the terminal door of the EX4100-H-24MP and -24F, is 1.1.0: it
  presents the registered `terminal-stud` interface, with a mate point at the centre of the pad, so `generic/ring-lug@1` seats
  on each of the twelve. The EX4100-H Switch Hardware Guide draws a crimped ring lug under each screw head (Figures 109 and 110)
  while its text says the wire goes into the slot behind the screw; the part takes the figures and records both statements. The
  pad is drawn as before and claims no lug size.
- `juniper/ex2200-rps-port@1`, the RPS port of the EX2200, is 1.1.0: it presents `ex3300-rps`, with a mate point at the centre
  of its opening, so `juniper/ex3300-rps-plug@1` seats in it. The EX Series Redundant Power System Hardware Guide says each EX2200
  and EX3300 has a built-in RPS connector and shows one RPS cable going into an EX2200 (Figures 16 and 17); that is a reading
  from one cable, and no guide names the connector type. The registry note of `ex3300-rps` says so, and each EX2200 keeps its
  `rps-port-connector` gap for the type, with the sentence that the part presents no interface taken out.
- The EX2200-24P, -24T, -48P and -48T and the EX4100-H-24F and -24MP take a patch, with their locks and the `Drawing version` line
  of their exported device types and nothing else in them.
- Two rows of the port-usable records file are gone, one for each part.

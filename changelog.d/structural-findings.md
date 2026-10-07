### Added
- Lint L144 (warning): members of one group that one configuration draws on
  one face hold one `rel-pos` each (roc-ops/Portrayal#414). Variant views of
  a face and bays that `only-in` scopes to different builds are alternatives
  and may share a position; a position reused on another face is not
  reported. Thirteen devices carry a clash and are in the lint baseline: the
  six Juniper MX chassis whose `grounding` group puts an ESD jack at position
  0 beside the first earthing stud or plate (mx80, mx150, mx204, mx240,
  mx304, mx480), `dell/r740xd` furniture, `ufispace/s8901-54xc` lane lamps,
  and the port lamps of `edgecore/agr110`, `agr130`, `agr560`, `csr310` and
  `ecs4120-28fv2-i`. Each cure renumbers or regroups placements, a major
  device version, and is left for a decision.
- Lint L145 (warning): a group is not named `ports`, which names no port
  family (#414). `dell/r660`, `dell/r740xd` and `maiaedge/port-extender` are
  in the baseline; renaming a group is a major device version.

### Changed
- Lint L19 also reads a bay in a group whose role is `indicator`: it states
  `for:` as a lamp placement does (#414).

### Fixed
- The craft interface bays of `juniper/mx960` (1.1.0), `mx2008`, `mx2010`
  and `mx2020` (0.3.0) state `for: chassis`. The hardware guides describe
  the craft interface as the router's status panel, with LEDs for the
  router's components. `dell/r660` (5.1.0) does the same for its left
  control panel, which the R660 Installation and Service Manual describes as
  holding the system health, system ID and status lamps (#414).

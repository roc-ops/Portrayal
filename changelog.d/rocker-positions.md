### Added
- The snap-in rocker (`common/rocker-switch@1`, 1.1.0) has a `state`, `off`
  or `on` (#808), and is the first part whose position SHOWS rather than
  moves. It is drawn as the see-saw it is: one surface tipped about its
  centre, a node for each position, rising toward the I end for `off` (drawn,
  as before) and toward the O end for `on`. In 3D each is a sloped `profile`,
  4.9 at the raised end and 2.2 at the low end, both read off the GL-12xB GLB.
  The ReadyLinks GL-12xB-240D and the Catalyst 4948E (through its AC supply)
  draw as before and take a patch. `common/power-switch-slide@1` is left
  without positions: no source says which end of its travel is ON or how far
  the slider moves.
- Seven parts that draw their own rocker take the same see-saw (#808): the
  Juniper JNP10K-PWR-AC2 and MX80 AC supplies and the Telco Systems TM-7124S
  AC supply (`state`), the Casa C40G AC inlet panel (`switch-1` to
  `switch-4`), the Casa PEM's rocker breakers (`breaker-1` to `breaker-4`),
  and the Nokia SR-7 and SR-12 PEM-3 (`breaker`, `power-switch`), each a
  contract minor with estimated heights. The devices that seat them draw as
  before and take a patch. Rockers whose art marks no ON end, and the SR-1 DC block whose
  lamp rides on its rocker, are left as drawn; the design note says why for
  each.

### Fixed
- L50 no longer reports printing as painted over by a node that is never on
  screen with it: a position's other option, drawn after it (#808).

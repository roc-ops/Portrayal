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

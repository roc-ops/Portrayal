### Added
- The snap-in rocker (`common/rocker-switch@1`, 1.1.0) has a `state`, `off`
  or `on` (#808), and is the first part whose position SHOWS rather than
  moves: each half of the rocker is a node raised for the position that does
  not press it, the I half for `off` (drawn, as before) and the O half for
  `on`. The pressed height (3.0) is estimated; the raised one is the GL-12xB
  GLB's 4.9. The ReadyLinks GL-12xB-240D and the Catalyst 4948E (through its
  AC supply) draw as before and take a patch. `common/power-switch-slide@1`
  is left without positions: no source says which end of its travel is ON or
  how far the slider moves.

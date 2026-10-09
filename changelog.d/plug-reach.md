### Changed
- **Routed lengths start at the plug's reach** (`@portrayal/kit` 0.13.0,
  #960; `docs/cable-lay-design.md` section 1.5). A cable leaves the far end
  of its plug, so each `routePath` now starts and ends with a straight
  stretch out of the port's face, to a new point `at: 'reach'` (with `end`),
  and its first and last legs, their detours included, run from there. The
  reach is the page's `ctx.plugReachOf(end, cable)` when it gives one, else
  `PLUG_REACH` by media: 27.6 mm for LC fibre (generic/lc-plug@2 and
  common/lc-boot@1), 39.4 for copper and a cable with no media
  (generic/rj45-plug@1 and common/rj45-boot@1, with the boot taken to abut
  the plug, so it may err long by a few mm), 64.8 for a DAC or an AOC
  (generic/qsfp-cable@1). The 0.15 m end allowance is unchanged: it is the
  dressing slack, and the plug was always along the first leg, which the
  reach turns into a dog-leg rather than lengthening by a plug. Almost every
  routed length grows, by what the dog-leg out of each plug adds (median about 43 mm on a
  780-cable sample) and by up to about 0.33 m where the reach puts a leg over
  a tray floor, so it goes round the tray's front edge; one cable in six
  to eight moves up a stock size. On the owner's rack of #949, c7 and c9 to c14
  move from 0.5 m to 1 m stock (c9 to c12 measured 0.494 to 0.496 m from the
  port faces, 0.517 to 0.524 m now). A saved rack's routed lengths and stock
  sizes are re-measured the next time a page measures them; an entered
  length is never touched. A plug in a panel port behind a deep shelf is now
  a `crosses-body` finding ("at its port on ...").

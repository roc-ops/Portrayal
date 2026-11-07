### Changed
- The 2D rack view reads the library it is given, not one set for the whole
  module (#1298). `mountRack2d` and `drawElevation` take `distAt`, a function
  from a path in the build to its URL (`flatDist(base)` in `kit/dist.js` makes
  one), in place of the `dist` option; `setDist` and the exported `DIST` of
  `kit/rack/view/face.js` are gone, and a view given `dist` is refused with a
  sentence naming `distAt`. `configuredFace`, `loadSkin`, `components`,
  `earPlanFor`, `zeroUModuleEnds` and `faceUrl` take the `distAt` too, and what
  they remember is kept per library, so two views of two libraries on one page
  each draw their own. No kit release held the old option, and the kit version
  is not bumped.

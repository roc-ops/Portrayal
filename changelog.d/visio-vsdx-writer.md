### Added
- **The kit writes Visio: `toVisio` and `buildVsdx` in `kit/visio.js`** (#11). A
  live drawing becomes a one-page `.vsdx`, a zip of XML in Visio's format. The
  face is a picture. Over it, every port and every bay is an invisible shape
  named by its `data-path` (`port-12`, `slot-2/module/p0`), with that path again
  in its Shape Data (`portrayal-path`) and one connection point at its centre,
  so a named port can still be found in the file, by script or by hand. The
  shapes are the same zones that `toDrawio` and `toGraffle` read. The geometry
  is the kit's own: nothing is taken from a vendor's Visio stencil. The zip
  writer is the one in `omnigraffle.js`. The module is exported as
  `@portrayal/kit/visio`. The file draws no cable, and no page of the site
  offers it yet. No existing export changes.

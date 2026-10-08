### Fixed
- `edgecore/eps122` 2.0.8 draws the orange bands that mark its 90 W ports 41-48: one
  behind the legend row above them and one behind the lamp row below, measured on the
  guide's front elevation at its native resolution and coloured from a pixel count. The
  single band it carried sat at x 601.74 on a 440 mm face, so it was never seen. The
  panel legend is transcribed as "1.65A Max/Port41-48", not 1.85 A, and the row under
  the ports is identified as the per-port lamp row (#878).
- `juniper/mx204` 4.0.2 no longer carries four ear-flange rects beside its front and
  rear faces. They lay wholly outside the drawing and were never seen, and the device's
  own provenance says the ears are not modelled (#878).

### Changed
- L44 also reports decor whose box lies wholly outside its view's drawing - the face
  plus every placement the default build draws beyond it - where it is never seen (#878).

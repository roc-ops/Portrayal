### Fixed
- `edgecore/eps122` 2.0.8 draws the orange bands that mark its 90 W ports 41-48: one
  behind the legend row above them and one behind the numeral row below, measured on
  the guide's front elevation. The single band it carried sat at x 601.74 on a 440 mm
  face, so it was clipped and never drawn. The panel legend is transcribed as
  "1.65A Max/Port41-48", not 1.85 A (#878).

### Changed
- L44 also reports decor whose box lies wholly outside its view, where the renderer
  clips it and never draws it. The four ear flanges `juniper/mx204` draws as decor
  beside its front and rear faces are such rects and are recorded in the lint baseline
  (#878).

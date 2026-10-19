### Fixed
- **draw.io rack exports now draw each face at its true width, so devices
  narrower or wider than the opening change** (#993, `kit/drawio.js`). The whole
  drawing was fitted to the cabinet opening, which squeezed a drawing with parts
  outside its face (end rings past the ears) and stretched a narrow face across
  the opening. `rackDiagram` now scales x by the opening in millimetres (482.6 mm
  is the 138 units of the opening), so a millimetre is as wide for every device
  in a cabinet, and y stays one rack unit per unit. A narrow face that declares no
  ears is centred between the rails with rail showing on both sides, and a
  drawing that declares its face (`data-face-w`) keeps its true position,
  hanging out over the opening on the side or sides its viewBox extends. A face exactly as wide as the opening is written as before.
  Port cells stay on their ports. `entry` with `ru` set had the same defect and
  is sized by the same rule. No argument or export is added.

### Added
- **A body piece carries a side drawing** (`shows: [left|right|top|bottom]`
  on `body.boxes`). The piece is painted on that side with the patch of the
  part's own `skins/body-<side>.svg` it lies under, so a GPU's printed top
  edge and its ribbed shroud are one drawing each, not hundreds of boxes.
  Each side drawing is that side of the whole body seen from outside, in the
  frame the one-box body already reads it in, and its viewBox names the patch
  it covers. `components.json` publishes each one under `body.drawings` with
  the viewBox origin as `at`. L71 asks that the drawing exists, that its
  stated size is its viewBox's and that every patch lies inside it.
- **A body piece can be a fitted option** (`when: {field: [options]}`). It
  stands only while the part's drawing shows a node for one of those options
  of its choice field, so a configuration's `bay-attrs` and a viewer's
  `setFields` fit or remove it. Such a piece may reach past `size.d`, which
  is the part as it ships. L148 asks that the field is a choice, that the
  options are its options, and that every skin shows a node for each.
- **`kit/component.html`** opens one component in the 3D viewer with a camera
  for each side, a flat lens for laying a view over a photograph, and a
  selector for each choice field. It is a page of the kit's checkout, not
  part of the npm package.
- `nvidia/a100-pcie-80gb@1` uses both. Its top edge carries "A100", "NVLINK"
  under each NVLink cap and the word "NVIDIA", with the NVIDIA mark reserved
  as `logo-zone`. Its shroud's top and lower edges are ribbed on a 2.194 mm
  pitch, and its broad side has a matte grain. Its `extender` field fits
  NVIDIA's straight extender (312 mm overall) or long offset extender (339
  mm), or none, the default. The bracket's retention tabs have a thickness,
  and the standoff behind the bracket below the card is drawn.

### Changed
- **`@portrayal/kit` is 0.50.0.** `relief.js` exports `pieceFitted`,
  `shownOptions` and `SIDES`; `pieceArtCrop` takes the four sides with an
  `{at, depth}` argument; `svgCanvas` takes an optional raster density. A
  page that uses neither key draws as before.
- **`body-<side>.svg` is documented as read**: the README said nothing read
  those drawings, and the one-box body has painted them on its sides all
  along.

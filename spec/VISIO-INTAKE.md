# Visio stencil intake

Vendors publish far more Visio stencils than mechanical drawings, and those
stencils encode real geometry — port positions, panel layouts, rack units. This
tooling extracts that artwork so it can be used the way we use a datasheet:
**read facts from it, then author original Portrayal art**.

```bash
python3 tools/portrayal/visio_extract.py STENCIL... --out DIR
```

## What it handles

| Input | Storage | How it is read |
|---|---|---|
| `.vssx`, `.vsdx` | OPC package (a zip) | parsed directly — masters from XML, artwork from `visio/media/` |
| `.vssx` with no media | native Visio geometry | shape tree rendered to SVG by `visio_geom.py` |
| `.vss`, `.vsd` | OLE2 compound document | `libvisio` (`brew install libvisio`); we parse its raw dump, which carries master names and sizes alongside the images |

Three different situations, and the tool picks the right one from the file's
magic bytes. Two of them were surprises worth recording:

- **Modern stencils are often bitmap-free.** The rack cabinets in the first test
  set contain 508 geometry sections and zero images — the artwork *is* the
  geometry. `visio_geom.py` walks the shape tree, applies each shape's
  placement (`PinX/PinY`, `LocPin`, `Width/Height`, `Angle`, `FlipX/FlipY`) and
  emits SVG paths. Visio is y-up, so everything renders inside one flip group.
- **Legacy stencils cannot be carved.** A `.vss` is a single proprietary
  `VisioDocument` stream; scanning it for EMF/PNG signatures finds nothing
  because the chunks are compressed. It needs a real parser.
- **Pick the right libvisio output.** `vss2xhtml` renders the artwork but drops
  the master names; `vss2raw` keeps them, because each master arrives as a page:

  ```
  startPage(draw:name: A9903-20HG-PEC, svg:height: 0.1525in, svg:width: 1.7188in)
    drawGraphicObject (librevenge:mime-type: image/emf, office:binary-data: ...)
  ```

  Visio has to show those names in its stencil palette, so of course they are in
  the file - they just are not in the rendered output. The raw dump is parsed as
  a stream since it runs to tens of megabytes of base64.

## Output

```
<out>/<stencil>/media/      artwork exactly as embedded
<out>/<stencil>/svg/        vector conversions (Inkscape, if installed)
<out>/<stencil>/by-master/  the same files named after their Visio master
<out>/<stencil>/index.json  master -> shape properties + files
<out>/index.html            contact sheet across every stencil
```

`index.json` carries what the stencil knows about each master: its name, width
in inches, and shape properties such as `RackUnits` — often the fastest way to
learn a chassis's height in U.

## Known limits

- **Legacy metadata is limited.** `.vss` gives master names, sizes in inches and
  the text drawn in the artwork, but no Property or Connection sections -
  libvisio does not surface the ShapeSheet. Modern OPC stencils give all of it.
- **Curve fidelity.** `NURBSTo` and `PolylineTo` degrade to straight segments,
  and `EllipticalArcTo` is approximated; complex curves (fan blades, logos) show
  artifacts. Straight-edged panel geometry — the part we care about — is exact.
- **Theme colours are not resolved.** Colours given as literal hex survive;
  theme-indexed ones fall back to a neutral palette.

## Licensing

Vendor stencils are typically licensed for *making diagrams*, not for
redistribution or modification; some terms prohibit reposting on any public
service. Treat extracted art as reference only:

- do **not** commit it to `library` or publish it,
- do **not** trace it into skins,
- **do** read the facts — port counts and order, panel positions, RU heights —
  and author original art with provenance naming the measurement source.

This is the same posture the project takes with vendor datasheets: facts are
uncopyrightable, expression is not.

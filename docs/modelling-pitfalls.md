# Modelling pitfalls

Things that have gone wrong before, so you do not repeat them. Each cost
somebody a cycle, and several survived a lint run, a render and a review before
anyone noticed. Read this when a figure, a measurement or a lint warning is not
behaving the way you expect; the answer is very often here. You do not need it
to start a device: [modelling-a-device.md](modelling-a-device.md) is the method.

## Reading figures

- **A rotated crop reads bottom-to-top.** Check the frame before reading port
  order off a figure; this reversed an entire supervisor card once.
- **Rear views mirror only when the cards are vertical.** Walking round a
  chassis flips left-to-right. Vertical cards mirror; horizontal ones do not.
- **Pattern-match by colour, not by vector.** Rendering a guide page at 400 dpi
  and detecting features by colour is reliable. Parsing its vector art is not;
  text comes out as glyph paths under nested transforms.
- **Read silkscreen legends at high zoom before trusting them.** A port pair
  legend that looks like `0<up>1` at page scale turned out to be
  `0<up><down>1` at 7x, two arrows not one, which inverts which row is even.
- **One label serving two ports is usually a bracket, not two leaders.** Where
  a faceplate names a pair once, the printing is typically a horizontal bar with
  a drop at each end. A high-zoom crop or the vendor's 3D viewer settles it.
- **The filled rectangle in a guide figure is the module, not the port.** A
  cage drawing shows the transceiver's face as a solid block, and the port owns
  more of the panel than that block does. Measure centre to centre between
  those fills and you get the module pitch, which is wider than the port pitch,
  so every column drifts outward. The symptom is a regular gutter down the
  middle of each block that the reference does not have. Take pitch from a
  feature that repeats once per port (the lamp above it, the numeral, the
  cutout edge) and check the total span against the panel width.
- **Two figures can describe different things that look like the same thing.**
  The ASR 9006 has three "NEBS bonding and grounding points" in one figure and
  one "grounding receptacle", a kit part with its own location, in another.
  Read together they look like one fact contradicted; they are two facts about
  two things. Before recording a disagreement, check both sources are talking
  about the same object; the words to look for are the ones that differ
  (`point` versus `receptacle`), not the ones that match.
- **Where two sources disagree, carry both numbers.** One datasheet said
  480 mm deep and 16 kg; its own quick start guide said 524 mm and 14.5 kg.
  Record the disagreement in provenance and say which you used.
- **Where a bay and a component disagree, the answer may be in neither.** Both
  C40G PEM figures were wrong, and what settled it was the card slot next door,
  whose bottom edge made one candidate physically impossible. Look at what
  constrains two disagreeing numbers from outside rather than re-reading each
  harder.
- **Two sources agreeing is evidence only if they were derived independently.**
  The C40G's device provenance and its PEM's both said the band starts at
  y 194, and it was one sentence copied from the other, both wrong by two
  millimetres. When you copy a provenance sentence between files, say where it
  came from in the sentence itself, so the next reader can tell corroboration
  from an echo.
- **Reconciling a bay and a module silences the only check that can see
  them.** A fit check compares two numbers to each other and neither to the
  world. If the reconciliation was a judgement rather than a measurement, file a
  gap. [bay-and-component-size.md](bay-and-component-size.md) has the full
  argument.
- **A derived extent stated to two decimal places implies a precision the
  source cannot support.** Write the number the subtraction gives, then write
  what the figure actually resolves to: "stated to the hundredth because that is
  what the subtraction gives, not because the figure resolves to it; the whole
  disagreement is six pixels at 2.982 px/mm."
- **An inert claim is the hardest kind to catch, because nothing depends on
  it.** Six modular carriers stated as fact that the adapters seated in them
  are inside their own power figure. The vendor says no such thing. The claim
  survived because no adapter stated a power figure, so nothing was being
  summed. A false statement that is currently unused is invisible to every
  check, and it waits for the day someone finds the missing figure. Where the
  source is silent about scope, say so and record the question; do not pick the
  safer reading and state it as the vendor's.
- **An angled port is not face-on, and its footprint is not its size.** A cage
  on a 30-degree housing measures about 13% shorter in a front view than its
  registry size, and a 45-degree sawtooth cage 29% shorter. Model the surface
  as a facet and let the renderer project the part; never shrink a `std/` part
  to match the drawing. Read the angle from a 3D or side figure and record it
  as `estimated` unless a document states it.
- **If a cage shows through the back of a tooth in the 3D view, the facet
  angle, the facet's height or its return is wrong.** The viewer does not
  clip it, on purpose. The same holds for a sunk facet whose cage comes out
  through the floor of its pocket: check the facet's lift and angle, and the
  pocket's depth, against the drawing.

## Axes and views

- **State the axis convention on any face where the arithmetic could read as
  an error.** A top or bottom view laid out from a vendor's footprint figure
  usually has y = 0 at the rear, because those figures print "Rear of chassis"
  at the top. Write the convention in provenance next to the number. A bottom
  view mirrors left and right, not front and back.
- **Left and right views run their depth axis in opposite directions.** On a
  right view x = 0 is the front; on a left view x = 0 is the rear (derived from
  how `viewer3d.js` orients each face, front at +z). Mirroring one from the
  other by copying x is exactly wrong; the correct mirror is
  `depth - x - width`. Two ASR 9000 chassis had seven features wrong this way,
  including two grounding pads sitting in each other's places.
- **A feature that is symmetric about an axis cannot be at the wrong end of
  it, which is why this class of error is discovered late.** When a face
  carries only symmetric content, say so in provenance: it records that the
  axis was checked rather than that it happened not to matter.

## Silkscreen and skins

- **The advice to draw a symbol as strokes is about symbols, not letters.**
  Solid triangles are worth drawing as paths because they rasterise unreliably.
  An ordinary letter is set as `<text>`. A fan's exhaust tag, a plain capital E,
  was drawn as three strokes with the spine left off and rendered as an identity
  sign. Rasterise it and ask whether you would recognise the character with no
  idea what it was supposed to say.
- **A `path:` silkscreen mark is stroked, not filled.** A solid triangle drawn
  as a path comes out as an outline. Anchor the path at its `at` and draw the
  geometry relative to that, or L14 has nothing to test against.
- **Three lint-geometry facts that each cost a cycle.** (1) Text extent
  assumes `anchor: start` unless the mark says otherwise, so a legend you
  centred reads as extending a full width to its right; write `anchor: middle`
  explicitly rather than nudging `at`. (2) The path extent parser reads
  coordinate pairs: `M 0 0 V 4.5` contributes a stray number, `M 0 0 L 0 4.5`
  does not. (3) An L-shaped mark is measured by its bounding box, so a bracket
  drawn as one path claims the whole rectangle it spans. Split it: the bar as
  one mark `for: [a, b]`, each drop as its own mark.
- **A warning about a legend can be a warning about an abstraction.** A device
  with fixed supplies had its input connectors modelled as bays so a
  configuration could swap input types. L21 then reported the supply's legend
  sat inside its bay. Going back to the guide found the real error: the two
  input variants print that legend at different heights and open their windows
  at different heights. They are two different panels, not one panel with two
  occupants. When a rule complains about where a mark sits, check what the mark
  is attached to before you move it.
- **A legend printed on a module's face is not the chassis's silkscreen.**
  Vendors letter the FRU, not the frame. Put it in `silkscreen[]` and the mark
  sits inside the bay and paints over the module (L21), and the drawing claims
  the chassis carries printing it does not. It belongs in the component's skin,
  inside its `<g id="silkscreen">`.
- **A `std/` port draws the opening. The shell around it is yours to draw.**
  Where the real faceplate carries a bright metal connector shell (the strip a
  ganged jack block sits in, the collar on a USB receptacle), that metal is
  panel, not part, and belongs in `panel.decor`. Skip it and a dark connector on
  a dark faceplate is invisible, which no rule can see and every reviewer can.
  It has been the single most repeated by-eye finding across unrelated vendors.
  Measure the flange, not the cage.
- **Labels are rectangular unless you have seen otherwise.** There is an oval
  label component that belongs to exactly one platform. Never transcribe a real
  serial, SKU or MAC into artwork; draw placeholder blocks.
- **Connectors have an orientation, and a component draws only one.** A
  stacked pair of RJ45s mirrors: the upper is keyway-up, the lower keyway-down.
  Use `rotate: 180` where it differs. The same goes for anything with a latch
  or a pin-1 mark.
- **Two correct things in one place is still a defect.** Ears over the
  convention, decor over ports, a USB outside its hole, ejector levers over the
  model name. L13, L46 and L48 check the device and the component; inside a
  skin's own SVG, nothing does. Look.

## Parts and pitch

- **A repeated block's pitch decides which part you may use.** A standard
  connector with a moulded bezel needs bezel-width spacing; a shared shell
  presents bezel-less openings on a tighter pitch, and the library carries both
  (`...-ganged` variants). If the pitch you measured is smaller than the part's
  own width, the part is wrong, and L39 will say so once per adjacent pair. A
  wall of overlap messages on one block means one wrong `ref`, not fifty bad
  coordinates.
- **A library part can simply not fit, and the right pitch beats the right
  shape.** Lamp parts are drawn at whatever size their first device needed. If
  none sits on the pitch you measured, fall back to the simplest part that fits
  (usually a plain dot) and say in provenance that the shape is a compromise. A
  part at the right pitch in the wrong shape is closer to the hardware than the
  reverse, and only the reverse collides with its neighbour.
- **Prefer `std/` over `common/`.** `std/` parts derive from a published
  standard; `common/` ones were drawn by hand and can be wrong. If the standard
  part lacks a feature (LEDs, a bezel), place that on top of it rather than
  reaching for a hand-drawn variant.
- **An inventory is not a layout.** Knowing a panel has four things called
  "Branch N" does not tell you they are breaker legends with leader lines. Open
  the figure that shows the layout before drawing.

## Relief and 3D

- **Depth on a leaf is a hole, not a lump.** `size.d` on anything that is not
  `kind: module` compiles to `data-depth`, which the 3D viewer reads as a cavity.
  Rivets, a grounding plate and three labels all got depth "so they would stand
  proud" and rendered as neat little pits. Anything that stands proud says so
  with `relief.features` and no depth at all.
- **An empty `relief.features` does not mean a flat part.** A composed `std/`
  or `common/` port emits its own `data-depth` regardless of the parent's relief
  block, so a line card with 48 composed cages already has 48 recessed ports in
  3D. Before writing "renders flat" or adding a feature to fix a flatness that
  is not there, compile the component and count `data-depth` in the output.
- **A raised feature is textured from its own node, and uses that node's
  bounding rect.** Put `out` on a group holding the part and all its detail,
  never on a bare rect or path: on a bare path it gave a rectangular shadow with
  nothing in it. A stepped outline needs one group per step. A raised node is
  taken off the flat plate, so a sibling that is not raised stays behind and
  reads as a coloured shadow; raise the whole group.
- **Pick the right relief primitive.** `out` builds a box from the node's
  bounding rect; `cyl` builds a cylinder of the node's radius and takes `thread`
  or `knurl`; `lift` stacks parts up a shaft. A bolt made with `out` is a square
  blob. Made of three nodes (stud as a threaded `cyl`, washer and nut as short
  `cyl`s with `lift`) it is a bolt.
- **A module with a real body should declare one.** `body: {depth, color,
  footprint?, plate?}` plus `skins/body-{left,right,top,bottom,rear}.svg` makes
  a FRU eject as a six-sided box instead of a floating faceplate. If you were
  handed photographs of all six faces of a part, draw all six.
- **A skin cannot compose parts; only a component can.** Two variants that
  differ in what they compose (an AC PSU with an IEC inlet, a DC one with a
  terminal block) are two components, not two skins of one.
- **Alternate skins are only reachable through a configuration.** The viewers
  switch configuration, not skin, so a variant needs a `configurations:` entry
  carrying `skins: {component: variant}` or nobody can see it.
- **Measuring a hand-built SVG in a browser: compose the CTM.** `getBBox()` is
  local. Composing transforms by hand in Python does not reproduce Inkscape
  output; sample the path through the browser instead.

## If you script it

A device with hundreds of repeated placements wants a generator, and
`layout.yaml` with `expand.py` is the supported one. If you write your own,
kept in `working/` beside your notes:

- **Generate per group, never generate then split.** A filter's foam was one
  list of cells cut into groups by x, which put a cell's backing rect in one
  group and its dots in the next.
- **Assert that an edit matched something.** A scripted change aimed at a
  coordinate that was not in the file silently rewrote nothing. Count the
  substitutions and fail on zero.
- **Read every source into memory before writing any destination.** A loop that
  copied one skin onto `default.svg` and then used `default.svg` as the source
  for the next variant gave the third variant the first one's artwork. Lint was
  green and the only symptom was a card wearing the wrong model name.
- **Re-read what you rewrote.** Diff the rendered output, not just the source.
- **BSD `sed` has no `\b` and will not honour `0,/re/` reliably.** A probe that
  relies on either silently does nothing on macOS; use Python for anything
  conditional.

## If you write a test

A test that asserts something is missing from a live manifest is pinned to that
model's incompleteness. Three tests broke in one session because a device got
better: two used the C100G as their "stuck at level 2" fixture and failed the
day it grew its side faces. Build the fixture instead of borrowing it: load a
real device and remove exactly what the assertion is about. And check how the
code under test reads the manifest before choosing where to build it; a function
that takes a path and ignores the dict you hand it needs the fixture written to
`tmp_path` as a real file.

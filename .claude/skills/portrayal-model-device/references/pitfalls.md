# Things that have gone wrong before, so you do not repeat them

Each of these cost somebody a cycle, and several of them survived a lint
run, a render and a review before anyone noticed. They are here rather than
in SKILL.md because you do not need them to START a device - you need them
when a specific thing looks odd, and reading 6,700 tokens of other people's
mistakes before drawing a single port is not how that time is best spent.

**Read this file when a figure, a measurement or a lint warning is not
behaving the way you expect** - the answer is very often already here.

- **A rotated crop reads bottom-to-top.** Check the frame before reading port
  order off a figure; this reversed an entire supervisor card once.
- **Rear views mirror only when the cards are vertical.** Walking round a
  chassis flips left-to-right. Vertical cards mirror; horizontal ones do not.
- **`getBBox()` is local.** Measuring a hand-built SVG in a browser: compose
  the CTM. Composing transforms by hand in Python does not reproduce Inkscape
  output; sample the path through the browser instead.
- **Pattern-match by colour, not by vector.** Rendering a guide page at 400dpi
  and detecting features by colour is reliable. Parsing its vector art is not -
  text comes out as glyph paths under nested transforms.
- **Read silkscreen legends at high zoom before trusting them.** A port pair
  legend that looks like `0<up>1` at page scale turned out to be `0<up><down>1`
  at 7x - two arrows, not one - which inverts which row is even. Zoom until the
  glyphs are unambiguous, then decide.
- **The advice to draw a symbol as strokes is about SYMBOLS, not letters.**
  Non-ASCII shapes like solid triangles are worth drawing as paths because they
  rasterise unreliably. An ordinary letter is not: set it as `<text>`. A fan
  module in this library had its exhaust tag - a plain capital E, the letter the
  vendor prints - drawn as three horizontal strokes with the spine left off, so
  it rendered as a mathematical identity sign. Every other fan in the same
  library sets that glyph as text and reads correctly. When you hand-draw a
  letterform you take on the job of a typeface and will usually lose a stroke;
  the check is to rasterise it and ask whether you would recognise the character
  with no idea what it was supposed to say.
- **A `path:` silkscreen mark is stroked, not filled.** The renderer sets
  `fill: none`, so a solid triangle or arrow comes out as an outline. Anchor the
  path at its `at` and draw the geometry relative to that, or L14 has nothing to
  test against.
- **Three lint-geometry facts that will each cost you a cycle.** They are
  mechanical, they are not in any rule's message, and they are why a mark
  that renders perfectly still warns. (1) `_text_extent` assumes
  `anchor: start` unless the mark SAYS otherwise, so a legend you centred
  reads as extending a full width to its right and collides with whatever is
  there - write `anchor: middle` explicitly rather than nudging `at` to
  silence it. (2) The path extent parser reads coordinate PAIRS: `M 0 0 V 4.5`
  contributes a stray number and misplaces the box, `M 0 0 L 0 4.5` does not.
  (3) An L-shaped mark is measured by its bounding box, not its stroke, so a
  bracket drawn as one path claims the whole rectangle it spans and paints
  over the ports inside it. Split it: the bar as one mark `for: [a, b]`, each
  drop as its own mark `for:` its port.
- **A WARNING ABOUT A LEGEND CAN BE A WARNING ABOUT AN ABSTRACTION. FOLLOW IT
  TO THE FIGURE.** A device with FIXED supplies had its input connectors
  modelled as bays, so that a configuration could swap one input type for the
  other. L21 then reported that the supply's own legend sat inside its bay and
  would be painted over - an ordinary-looking text-position complaint. Going
  back to the guide to move the text is what found the real error: the two
  input variants print that legend at DIFFERENT HEIGHTS and open their windows
  at different heights. They are two different front panels, not one panel
  with two occupants, and a bay was claiming both that the supply pulls out
  and that everything around it is identical. Draw the panel you have sources
  for, file the other as a gap, and keep the component you built for it.
  **When a rule complains about where a mark sits, check what the mark is
  attached to before you move the mark.**
- **One label serving two ports is usually a BRACKET, not two leaders.**
  Where a faceplate names a pair once, the printing is typically a horizontal
  bar with a drop at each end, not a separate leader per port. Both render
  plausibly and only one is what the metal says; a high-zoom crop or the
  vendor's own 3D viewer settles it in seconds.
- **Where two sources disagree, carry both numbers.** One datasheet said 480 mm
  deep and 16 kg; its own quick start guide said 524 mm and 14.5 kg. Record the
  disagreement in provenance rather than silently choosing, and say which you
  used.
- **A raised feature is textured from ITS OWN node, and uses that node's
  bounding rect.** `relief.features: [{node: X, out: N}]` lifts a slab, paints it
  with only what is inside `X`, and shapes it as `X`'s bounding box. So put `out`
  on a **group** holding the part and all its detail, never on a bare rect or
  path. On a bare path it gave a rectangular shadow with nothing in it; on a bare
  rect the plate came out a blank grey bar with its bolt holes missing. A stepped
  outline needs one group per step. The same applies in reverse: a raised node is
  taken OFF the flat plate, so a sibling that is not raised stays behind and reads
  as a coloured shadow under the part. Raise the whole group.
- **Pick the right relief primitive.** `out` builds a BOX from the node's
  bounding rect; `cyl` builds a cylinder of the node's radius running
  `lift..lift+cyl`, and takes `thread` or `knurl`. A bolt made with `out` is a
  square blob with the nut and washer painted flat on its top. Made of three
  nodes - stud as a threaded `cyl`, washer and nut as short `cyl`s stacked with
  `lift` - it is a bolt. `lift` is what stacks parts up a shaft.
- **Depth on a leaf is a HOLE, not a lump.** `size.d` on anything that is not
  `kind: module` compiles to `data-depth`, which the 3D viewer reads as a cavity
  to look into. Rivets, a grounding plate and three labels all got depth "so they
  would stand proud" and rendered as neat little pits. A module gets
  `data-body-depth` instead and fills its bay; everything else that stands proud
  says so with `relief.features` and no depth at all.
- **A module with a real body should declare one.** `body: {depth, color,
  footprint?, plate?}` plus `skins/body-{left,right,top,bottom,rear}.svg` makes a
  FRU eject as a six-sided box instead of a floating faceplate. The mechanism
  already exists - check before deciding a module can only be a face. **If you
  were handed photographs of all six faces of a part, draw all six** - being
  given the sides and being asked for a faceplate are not the same request.
- **A skin cannot compose parts; only a component can.** `parts:` sits on the
  component, so two variants that differ in what they compose - an AC PSU with an
  IEC inlet, a DC one with a terminal block - are two components, not two skins of
  one. Trying to do it with skins forced a rebuild; splitting into
  `agr-psu-ac` / `agr-psu-dc` and selecting between them per configuration did
  not.
- **Alternate skins are only reachable through a configuration.** The 3D and 2D
  selectors switch CONFIG, not skin, so a variant like an AC versus DC PSU needs
  a `configurations:` entry carrying `skins: {component: variant}` or nobody can
  see it.
- **A `std/` PORT DRAWS THE OPENING. THE SHELL AROUND IT IS YOURS TO DRAW.**
  A standard part draws the aperture and what is inside it, and stops there.
  Where the real faceplate carries a bright metal connector shell - the strip
  a ganged jack block sits in, the flange around a stacked pair, the collar
  on a USB receptacle - that metal is PANEL, not part, and belongs in
  `panel.decor` as a light fill sized from the placements it sits behind plus
  the flange the photograph shows. Skip it and a dark connector on a dark
  faceplate is simply INVISIBLE, which no rule can see and every reviewer
  can. It has been the single most repeated by-eye finding, on unrelated
  devices from unrelated vendors, and it renders and lints perfectly each
  time. **Measure the flange, not the cage**: what is visible on the outside
  of the panel is narrower than the connector body behind it, and using the
  body swallows the lamps that sit just above and below the strip.
- **THE FILLED RECTANGLE IN A GUIDE FIGURE IS THE MODULE, NOT THE PORT.** A
  cage drawing shows the transceiver's own face as a solid block, and the
  port owns more of the panel than that block does - the EMI gasket band, the
  shell lip, the gap the latch needs. Measure centre-to-centre between those
  fills and you get the MODULE pitch, which is wider than the port pitch, and
  every column in the block drifts outward from the one before it. The
  symptom is unmistakable once you have seen it: a regular gutter down the
  middle of each block that the reference does not have, repeated identically
  in every block. Take pitch from a feature that repeats once per PORT - the
  lamp above it, the numeral, the cutout edge - and check the total span
  against the panel width before you place anything.
- **A repeated block's PITCH decides which part you may use.** A standard
  connector with a moulded bezel needs bezel-width spacing; a shared shell
  presents bezel-less openings on a tighter pitch, and the library carries
  both (`...-ganged` variants). If the pitch you measured is smaller than the
  part's own width, the part is wrong - and L39 will say so once per adjacent
  pair, so a wall of overlap messages on one block means one wrong `ref`,
  not fifty bad coordinates. Check the pitch against the part before
  believing you mis-measured.
- **A LIBRARY PART CAN SIMPLY NOT FIT, AND THE RIGHT PITCH BEATS THE RIGHT
  SHAPE.** Indicator and lamp parts are drawn at whatever size their first
  device needed, and a denser panel will have pitches none of them can sit on -
  a lane-LED strip that spans a whole band where you measured two lamps inside
  it, a lamp pair moulded 8 mm apart where the hardware's are 3.4, an arrow
  wider than the gap between two of them. Lint finds these as collisions
  (L13), which is the good case; the bad case is nudging parts apart until the
  warning stops and shipping a row that is subtly wrong everywhere.
  **Fall back to the simplest part that fits the measured pitch** - usually a
  plain dot - and say in provenance that the shape is a compromise and what the
  real lamp looks like. A part at the right pitch in the wrong shape is closer
  to the hardware than a part in the right shape at the wrong pitch, and only
  the second kind collides with its neighbour. If the panel deserves better,
  the answer is a new component sized from this device, not a shoehorned one.
- **A LEGEND PRINTED ON A MODULE'S FACE IS NOT THE CHASSIS'S SILKSCREEN.**
  Vendors letter the FRU, not the frame: the position number on a fan, the
  rating on a supply, the model on a line card. Put it in `silkscreen[]` and
  two things go wrong at once - the mark sits inside the bay and paints over
  the module (L21 says so), and the drawing now claims the chassis carries
  printing it does not. The mark belongs in the component's own skin, inside
  its `<g id="silkscreen">`. Where the part is shared across positions and
  cannot carry a per-position digit, that is a gap to file, not a reason to
  print it on the chassis.
- **Prefer `std/` over `common/`.** `std/` parts are derived from a published
  standard; `common/` ones were drawn by hand and can be wrong. One
  `common/` RJ-45 puts its integrated LEDs on the contacts side, which no real
  jack does. If the standard part lacks a feature - LEDs, a bezel - place that
  on top of it rather than reaching for a hand-drawn variant.
- **Labels are rectangular unless you have seen otherwise.** There is an oval
  label component in the library that belongs to exactly one platform and gets
  reached for by default. Measure the label in the photograph and make a
  device-specific rectangular one if nothing fits. Never transcribe a real
  serial, SKU or MAC into artwork - draw placeholder blocks.
- **Connectors have an orientation, and a component draws only one.** A stacked
  pair of RJ-45s mirrors: the upper is keyway-up, the lower keyway-down. Check
  which way round each jack is and use `rotate: 180` where it differs. The same
  goes for anything with a keyway, a latch or a pin-1 mark.
- **Two correct things in one place is still a defect.** Every review has found
  more of this family than any other: ears over the convention, decor over ports,
  a USB outside its hole, ejector levers over the model name. The gates check
  that a thing is present and where a source says. L13, L46 and L48 cover the
  device and the component; inside a skin's own SVG, nothing does. Look.
- **An inventory is not a layout.** Knowing a panel has four things called
  "Branch N" does not tell you they are breaker legends with leader lines. Open
  the figure that shows the layout before drawing.
- **A device with hundreds of repeated placements wants a generator**, kept in
  `working/` (gitignored) beside the notes, so the pitch lives in one line
  instead of 300. Three rules make it safe:
  - **Generate per group, never generate then split.** A filter's foam was one
    list of cells cut into relief groups by x, which put a cell's backing rect in
    one group and its dots in the next - one segment ended up with 112 circles and
    no rect behind them. Emit each group's art from its own loop and assert that
    every piece it needs is inside it.
  - **Assert that an edit matched something.** A scripted change aimed at a
    coordinate that was not in the file, so it silently rewrote nothing and only
    the captions moved. Count the substitutions and fail on zero.
  - **Re-read what you rewrote.** A later pass over the same block quietly
    dropped the system LEDs' state semantics. Diff the rendered output, not just
    the source.
- **Two figures can describe DIFFERENT THINGS that look like the same thing,
  and the trap is assuming they conflict.** The ASR 9006 has THREE "NEBS bonding
  and grounding points" - right side, rear, left side, drawn in one figure - and
  ONE "grounding receptacle", a kit part with its own documented location, "Top
  rear right side", in a different figure and a different table. Reading the two
  together they look like one fact stated twice and contradicted; they are two
  facts about two things. Before recording a source disagreement, check that both
  sources are talking about the same object - the vendor's own vocabulary usually
  distinguishes them, and the words to look for are the ones that differ
  (`point` versus `receptacle`) rather than the ones that match (`grounding`).
  The cost of getting this wrong is a fabricated conflict in provenance, which is
  worse than a missing one because it looks like diligence.
- **`git add -A` IS A SNAPSHOT OF EVERY AGENT'S WORK, NOT YOURS.** The
  corollary of the rule below, and it bites the one holding the commit. With
  four agents writing devices underneath, `git add -A library` swept a device
  nobody had verified into a commit whose message named a different one -
  so the log now asserted, in the place people go to find out, that a file
  had been reviewed when it had not. Stage the explicit paths you verified
  (`git add library/devices/<vendor>/<model>`), and if you do catch one late,
  amend the message to name what the commit actually holds rather than
  leaving the record wrong.
- **A COMMIT IS ATOMIC; THE WORKING TREE IS NOT.** With more than one agent in
  the repo, a test suite or a lint run is not a verdict - it is a photograph of
  whatever was half-written when it started. An agent here saw four failures
  including `test_lint_green` seconds after its own lint run came back clean,
  because another agent was writing files underneath it. Re-run before believing
  a failure you cannot explain, and never commit a "fix" for one until you have
  seen it twice.
- **TWO SOURCES AGREEING IS EVIDENCE ONLY IF THEY WERE DERIVED INDEPENDENTLY.**
  The C40G's device provenance and `casa/c40g-pem`'s both said the PEM band
  starts at y 194, which read as independent confirmation and was ONE SOURCE
  WEARING TWO HATS - one sentence had been copied from the other, so the second
  file added no information and only added confidence. Both were wrong by two
  millimetres. A copied provenance sentence is indistinguishable from a
  corroborating measurement once it is in the file, and it is worse than no
  second source, because it converts a single reading into an apparent
  agreement. Twice in one component the same night: that part's POWER provenance
  was also the C100G's verbatim, asserting a 30 A nameplate this module does not
  have. **When you copy a provenance sentence between files, say where it came
  from in the sentence itself**, so the next reader can tell corroboration from
  an echo.
- **Where a bay and a component disagree, THE ANSWER MAY BE IN NEITHER.** Both
  C40G PEM figures were wrong, and what settled it was the card slot next door -
  a part with nothing to do with either, whose bottom edge made one of the
  candidates physically impossible. Then the FRONT face settled the replacement,
  by showing a measured margin in the equivalent position. When two numbers
  disagree, look at what constrains them from outside rather than re-reading
  each of them harder: neither of two disagreeing numbers has to be the right
  one.
- **RECONCILING A BAY AND A MODULE SILENCES THE ONLY CHECK THAT CAN SEE THEM.** A
  fit check compares two numbers to each other and neither to the world, so it is
  satisfied by both being wrong together exactly as easily as by both being right.
  If the reconciliation was a judgement rather than a measurement, FILE A GAP -
  otherwise the library accumulates numbers that agree with each other and no
  record of which were sourced.
- **A derived extent stated to two decimal places implies a precision the source
  cannot support, and the only defence is to say so.** Write the number the
  subtraction gives, then write what the figure actually resolves to: "stated to
  the hundredth because that is what the subtraction gives, NOT because the
  figure resolves to it - the whole disagreement is six pixels at 2.982 px/mm".
  The number and the sentence together are honest; the number alone is not.
- **AN INERT CLAIM IS THE HARDEST KIND TO CATCH, BECAUSE NOTHING DEPENDS ON IT.**
  Six modular carriers and the SIP-700 stated as fact that the adapters seated in
  them are inside their own power figure. Cisco says no such thing: Table 35's
  heading names the carrier without saying whether the measurement was taken
  populated or bare, and both readings are open - populated means adding an
  adapter's draw DOUBLE-COUNTS, bare means a budget built from it is SHORT. The
  claim survived review for one reason: no MPA or SPA states a power figure
  anywhere in the intake, so nothing was being summed and the error could not
  show up in any total, any lint rule or any test. **A false statement that is
  currently unused is invisible to every check you have**, and it does not stay
  unused - it waits for the day someone finds the missing figure, by which point
  it reads as an established fact with a citation beside it. When an assertion
  costs nothing today, that is the reason to check it NOW rather than the reason
  to leave it: the tempting direction is usually the conservative one, which is
  exactly why it gets written down. Where the source is silent about SCOPE, say
  the source is silent and record the question - do not pick the safer reading
  and state it as the vendor's.
- **State the axis convention on any face where the arithmetic could read as an
  error.** A top or bottom view laid out from a vendor's footprint figure
  usually has y = 0 at the REAR, because those figures print "Rear of chassis"
  at the top. A dimension measured from the front then sits at y = depth - D,
  and to anyone assuming y = 0 is the front it reads as an error of nearly the
  whole depth. Write the convention in provenance next to the number. And note
  that a bottom view mirrors LEFT and RIGHT, not front and back - so a full-width
  feature is unaffected but an asymmetric one needs the flip.
- **LEFT AND RIGHT VIEWS RUN THEIR DEPTH AXIS IN OPPOSITE DIRECTIONS, and this is
  the one that will bite.** They are two views of the same axis from opposite
  sides, so a feature at the front sits at one end of one view and the other end
  of the other. Derive it from the renderer rather than assuming: `viewer3d.js`
  builds each face in local coordinates and orients it with a fixed rotation,
  front at +z, and applying those rotations to the local x axis answers it
  outright - **on a RIGHT view x = 0 is the FRONT; on a LEFT view x = 0 is the
  REAR**. Mirroring one from the other by copying x is exactly wrong; the correct
  mirror is `depth - x - width`. Two ASR 9000 chassis had this wrong on seven
  features between them, including two grounding pads sitting exactly in each
  other's places, and it survived because the labels were right and only the
  coordinates were wrong.
- **A feature that is symmetric about an axis cannot be at the wrong end of it,
  which is why this class of error is discovered late.** Nothing asymmetric on a
  bottom face and nothing off-centre on a side face means every convention looks
  correct. The first grounding pad, drain hole, serial label or asymmetric vent
  drawn on one of those faces is what exposes the axis - by which time several
  models share the mistake. When a face carries only symmetric content, say so in
  provenance: it records that the axis was checked rather than that it happened
  not to matter.
- **A test that asserts something is MISSING from a live manifest is pinned to
  that model's incompleteness.** Three tests broke in one session because a
  device got BETTER: two capability tests used the C100G as their "stuck at
  level 2" fixture and failed the day it grew its four side faces, and an attrs
  test used the C40G's one `attrs.other` key and failed the day that key was
  correctly removed. A test failing because the thing it tests improved is the
  wrong way round. Build the fixture instead of borrowing it: load a real device
  and REMOVE exactly what the assertion is about, so the test keeps its strength
  and stops tracking one model's to-do list. **And check how the code under test
  reads the manifest before choosing where to build it** - the capability tests
  take a dict and can be mutated in memory, but `capability._rule_warnings` calls
  `lint.lint_device(path, ...)` and ignores the dict you hand it, so that fixture
  has to be written to `tmp_path` as a real file. Getting that wrong looks like
  the rule not firing.
- **A commit is atomic; the working tree is not.** Fixing the SMM's lamp order
  meant editing a contract and a skin, done in two writes. Between them the tree
  was genuinely inconsistent - the contract said one thing and the skin still
  said the other - and a reviewer reading at that instant reported a defect that
  the commit did not contain. In a tree with other agents in it, paired edits
  belong in ONE write, or behind a check that both landed. The commit being
  correct is not the same as the tree never having been wrong.
- **A loop that writes a file and later reads that same file has already
  corrupted it.** Splitting one component into three, the loop copied
  `bdm/v1/skins/bdm.svg` onto `bdm/v1/skins/default.svg` for the first variant -
  and `default.svg` was the source the THIRD variant was about to be copied
  from. So the third got the first one's artwork. Lint was green, the schema was
  satisfied, the file rendered, and the only symptom was a card wearing the
  wrong model name in a chassis view. Read every source into memory BEFORE
  writing any destination, and assert on what you read. This is the same family
  as "re-read what you rewrote", but it bites in one pass rather than two.
- **Two environment traps that waste an afternoon.** Do not run Python from
  `/tmp` - a stray `bisect.py` there shadows the standard library and every
  import breaks in a way that looks like your code. And BSD `sed` has no `\b` and
  will not honour `0,/re/` reliably, so a probe silently does nothing; use Python
  for anything conditional.

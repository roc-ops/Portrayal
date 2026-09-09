---
name: portrayal-model-device
description: Use when modelling a hardware device for Portrayal from reference material (datasheets, install guides, drawings, photos) - building or revising a device.yaml and any components it needs. Walks the manufacturing order with a verification gate at each stage.
---

# Modelling a device for Portrayal

A faceplate is made in a fixed order: the sheet metal is sized, it is punched,
it is printed, and only then are the parts installed. Model it in that order,
and **do not start a stage until the previous one has been checked against the
reference.** Every failure this project has had came from skipping a gate:
terminals drawn where breakers were, 54 ports that all read "SFP module", a
chassis 12% too wide because a page margin was measured as metal.

The output is `library/devices/<vendor>/<model>/device.yaml`, written in the
canonical shape (below), linting clean at `maturity: modelled`.

## Before you draw anything: sort the sources

Each kind of source is allowed to answer only certain questions. Mixing roles is
the single most repeated error.

| source | authoritative for | never use it for |
|---|---|---|
| **datasheet / spec table** | overall dimensions, RU, weight, port counts, the box's own power figure | positions; per-module power, which it almost never carries |
| **install guide figure** | *what* is on a face and *how it is arranged*; port order; legends | absolute geometry - these figures are schematic and their aspect is wrong |
| **install / reference guide appendix** | per-card and per-fan-tray power, and the ambient each figure assumes | anything the datasheet answers better |
| **mechanical drawing** (vendor or hand-built from the hardware) | size and placement of every feature | colour, legend text |
| **vendor 3D model** (GLB/glTF, STEP, USDZ) | size and placement of every feature, at CAD truth - see below | which of two adjacent lamps belongs to which port, and anything the geometry does not name |
| **photograph** | colour, finish, construction, confirmation of everything above; count of things | measurement, unless something of known size is in frame - but see below |
| **standards registry** (`spec/schemas/standards.yaml`) | cage and connector sizes | anything vendor-specific |

### A VENDOR 3D MODEL OUTRANKS EVERY FIGURE. LOOK FOR ONE FIRST.

Product pages increasingly embed a 3D model to drive an in-page viewer, and
it is often an **export of the actual CAD** rather than a display proxy: one
mesh per physical part, at millimetre scale, with hundreds of thousands of
triangles. Where one exists, port pitch, lamp positions, cage depths and
screw locations come off it directly and Gate 1 does not apply, because
there is no projection to be wrong about. Scrape the product page for
`.glb`, `.gltf`, `.usdz` and for a `model-viewer` element before concluding
you only have figures.

Parsing a GLB needs no library: a 12-byte header, a JSON chunk, a BIN chunk.
Walk `scenes -> nodes`, compose each node's TRS (or `matrix`) down the tree,
and transform the eight corners of each primitive's accessor `min`/`max` to
get world-space boxes. Then pick the face plane and convert to view
coordinates once, in one place - getting that mapping wrong once is cheap
and getting it wrong per-feature is not. (Working parsers live in the
intake's `gen/` directory alongside whichever vendor first needed them.)

**Expect the datasheet's overall dimensions to disagree with the CAD body,
and read the SHAPE of the disagreement.** If the three deltas are unequal
per axis, they are protrusions and mounting furniture outside the metal -
handles, jack noses, feet, bosses - and the CAD body is what you model. If
they are equal, you have a scale or unit error and must stop. This is the
ear-fold rule arriving from a different direction: model the body, record
the stated overall, say which is which.

**What CAD cannot tell you is anything with a name rather than a shape** -
which of four adjacent lamps serves which cage, what an unlabelled boss on a
side wall is for, which of two identical jacks carries the special role.
Geometry has no labels. Those stay `vendor-silent` gaps no matter how good
the mesh is.

### THE FIGURES ARE ALREADY IN THE DOCUMENTS YOU HOLD. EXTRACT THEM FIRST.

Before searching the web, and before declaring a vendor silent about what a face
looks like, **pull the figures out of the PDFs already in `working/intake/`.**
This project modelled two vendors and ~250 components before anyone did, and the
intake turned out to hold **2,193 figures across 112 documents** - faceplate
elevations with every port numbered, isometric drawings showing ejectors and
rails, and LED callout tables sitting under the drawing that names them.

That is the KEPT count. 5,087 pictures were saved and 2,894 classified as icons
or chapter banners, and counting the files on disk instead of the kept figures
overstates the haul by more than double. **Say which of the two any figure count
is** - the rejects are deliberately kept on disk, so `find -name '*.png' | wc -l`
will always flatter you.

    spec/tools/intake/extract.py  docling: figure + caption + page + section,
                                  into working/images/<stem>/

Use docling rather than `pdfimages`. A figure without its caption is an image; a
figure WITH "Figure 27: 1-Port 100-Gigabit Ethernet Modular Port Adapter with
CFP2" is evidence, and the callout legend under a faceplate comes through with it.

**A filter that selects figures by size is shaped like the last vendor you looked
at.** A Cisco line-card faceplate is wide and short (~1080x123); a Casa card is
tall and narrow; a SPA is wide again. The first filter written here dropped every
Cisco datasheet faceplate - too short to be a figure, too wide not to be a
banner - and each datasheet then returned zero figures, which reads exactly like
"this vendor published no pictures". SAVE EVERY PICTURE FIRST AND CLASSIFY
SECOND, so retuning costs a second instead of an hour and the rejects stay on
disk to argue with. Then LOOK at a sample of what you dropped.

**A negative answer is only as good as the extraction's coverage.** Count
`^Figure \d+:` in the document's text and compare it against what you captured.
"No figure for this part" means something very different at 62/62 than at 39/62.

### A SUBSTRING TEST OVER PROSE CERTIFIES WHAT IT SHOULD CATCH. RUN IT FIRST.

A check was proposed here to stop a `borrowed` confidence token claiming an
ancestry that does not exist: resolve the part it names, and see whether that
part's provenance claims a measurement. It was proposed twice, to two agents,
and neither time was it RUN. When somebody finally ran it against the six
origins the library actually cites, it passed FIVE OF SIX - including the
clearest false claim of the lot, whose only occurrence of the word is inside its
own denial:

    depth: 'estimated - it stands proud but was NOT MEASURED'

Four different ways to be wrong, in four files:

    negation           the hit is inside the sentence that refutes it
    wrong object       `measured - 360.7 mm` is the MODULE's depth, not the latch's
    wrong object       `measured - 132 mm` is the module again, not the handle
    wrong attribute    `size: photo-measured` is the label's outline, not its thickness

And the ONE that failed was the honest file whose provenance is simply short. So
the rule punished candour and certified the four that needed catching.

**A check that returns PASS on a false claim is worse than no check**, because it
converts "nobody looked" into "looked and cleared" - and it does it in a
machine-readable field a consumer will filter on.

THE FIX IS ALWAYS THE SAME SHAPE: test the STRUCTURE, not the prose. Resolve the
reference, read the origin's own declared token, and require it to be one of the
two that mean a caliper touched something. No sentence to parse, so no negation
problem and no wrong-object problem - the origin states its own confidence or it
states nothing.

**And run any rule about provenance against the real corpus before proposing
it.** This is the third time in one session that searching prose has measured the
searcher's expectations instead of the files.

### AN EMPTY `relief.features` DOES NOT MEAN A FLAT PART. COMPILE IT AND COUNT.

This has now been got wrong three times in one day, by three different readers,
in both directions - so do not reason about it, measure it.

A COMPOSED PART CARRIES ITS OWN DEPTH. `render.py` treats anything that is not
`kind: module` as an aperture, so a `std/` or `common/` port emits `data-depth`
from its own `size.d` REGARDLESS of what the parent card's relief block says. A
line card with 48 composed cages already has 48 recessed ports in 3D even though
its own `relief` is a wall colour and nothing else.

    "all 127 relief blocks have no features"          <- true
    "therefore every part renders flat"               <- FALSE, 82 of 128 have cavities

The same error in reverse: a wrapper assembly with no relief of its own reads as
flat, when the `std/` part it composes is doing the work. `common/sfp-plus-cage`
has no relief block at all and its ten placements on a supervisor still compile
to ten 41 mm cavities, because it composes `std/sfp`.

THE CHECK, which takes a minute and settles it:

    compile the component through instance_group, count `data-depth` in the output

Do that before writing "renders flat" anywhere, and before adding a feature to
fix a flatness that is not there. A part that already has cavities does not need
them invented, and the invented ones will be wrong.

### A FIGURE'S OWN ASPECT TELLS YOU WHETHER TO TRUST IT

Before taking any fraction off a drawing, measure the drawing against something
you already know - usually the part's own outline against its contract size.

    Casa BDM      figure aspect 12.54   real 11.34      10% out
    Casa PEM      isolated part drawings                10% out
    Cisco SPA     plate against subslot band             4% out

At 4% you can take fractions along the good axis. At 10% you cannot take absolute
scale at all, and you should say so rather than quietly using it anyway.

**A round feature that reads two different sizes is measuring the drawing, not
the feature.** A lamp 15 px across and 17 px down scales to 3.25 mm and 4.16 mm.
A lamp is round; those are not two candidate diameters, they are one drawing 12%
out in aspect. Leave the diameter alone and say why. This has settled three
separate lamp-diameter questions without moving a single number.

**Take proportions on the axis you can anchor, and only that one.** Where a
contract holds a trusted height and no equally trusted width, an x-fraction off a
drawing known to be wrong about x is the softer number - fix the y, leave the x,
and say which is which.

Write the source list into `provenance:` first, before a single number. Every
number you write afterwards names its source *at the moment you write it*. That
is not paperwork - it is what makes `maturity` honest and what lets the next
person know which figure to re-measure when something is wrong.

Confidence words, used verbatim in provenance: `datasheet`, `drawing`,
`measured`, `photo-measured`, `registry`, `borrowed`, `estimated`, `known-wrong`.
Anything `estimated` keeps
the device out of `verified`.

**Use every image you have, not the first one that answers.** Guide art is often
a mock-up rather than a finished unit, and it will show placeholders where the
real part has hardware. On one router the guide drew plain diamonds along the
rear where the real chassis has rivet heads, and drew two more where the real
device has a two-hole grounding plate under an earth symbol. Vendor stock renders
are a third source again, and may show a different SKU - the stock rear showed an
AC PSU where the unit in hand was DC.

So: check the guide figure, the vendor's stock renders AND the photographs of the
real device before drawing anything. **Where they disagree, the real device
wins**, and say so in provenance. Where they differ because they are different
variants, model both - usually as skins of one shell.

**A photograph with a ruler in it IS a measurement.** Two close-up shots of this
router had a tape measure lying beside the part, which turned two estimated
depths into measured ones. Look for scale before writing `estimated`.

### Before you write "no document states this", run two searches

**"Not in the document I looked in" is not "not in the intake."** Those are
different claims and the second is much stronger. Writing the second while
having checked only the first is the most repeated error in this repository:
seven times in one vendor's set, every one found later by somebody grepping
differently, and every one had produced a paragraph of well-written provenance
explaining a silence that was not there.

Two searches, both cheap, before that sentence is allowed:

**Grep the intake for the FIELD NAME, not the part number.** Searching for
`A9K-RSP-4G` finds the release-note inventories that mention it and nothing
else. Searching all 78 documents for the string `Power consumption` finds that
card's own data sheet, with the dimensions, the depth and the weight that a
component had been carrying as "NOT STATED ANYWHERE IN THE INTAKE" and had
taken from a sibling instead. Do the same for `Physical dimensions`,
`Physical specifications`, and for any wattage figure - the answer is usually
in a document about a different part, filed under a name you would not have
guessed.

**Check whether an OLDER REVISION carries a table the current one dropped.**
Vendors delete content between revisions. The current Ethernet Line Card
Installation Guide replaced its entire per-part dimensions table with one
sentence pointing at a URL; the older revision of the same guide, sitting in
the same intake directory, still has the table - height, width, depth and
weight for every card in a generation. Anything sized from the newer guide
alone would have had to guess.

**And note HOW that one defeats a search rather than merely failing it.** The
newer guide still has a section headed "Ethernet Line Card Physical
Dimensions". Grep for the heading and you find it; the reader concludes the
guide covers dimensions, reads the sentence, and stops. A heading that
advertises coverage its section does not have is worse than no heading, because
it converts a careful search into a confident wrong answer. The other traps of
this shape are quieter and just as effective: a bulleted list whose fourth item
sits on the far side of a page break, so the extracted text shows three; and a
figure caption naming a part the figure does not contain. **When a section
heading promises exactly what you are looking for, read the section rather than
trusting the heading.**

Then **record which searches you ran**, not just the conclusion. "Table 35 has
no row for any 5th-generation card, and no data sheet carries one either" is a
statement somebody can check and overturn. "No document states this" is not.

### Before you write "the artwork prints no X", render it

**Text extraction finding nothing and the drawing printing nothing are
different claims**, and outlined glyphs make the first look exactly like the
second. A vendor stencil will set some legends as text and convert others to
paths; a text scan returns the first set and is silent about the second, with
no indication that a second set exists.

One master printed all twelve of its port numerals as outlined glyphs and the
extractor returned none of them - so a first draft asserted the card numbered
no ports, and the numbering had to be reconstructed from a positional rule. A
later pair of adapters got the same sentence written about them, on the same
evidence, and rendering the master showed a numeral in vendor blue above each
cage, an A/L triangle beside it and a STATUS lamp.

So: **render the master and look at it** before any claim about what a drawing
does or does not carry. What the extractor missed is usually recoverable once
you know it is there - numerals as small dark ink boxes, indicators as
triangles, lamps as stroked `fill:none` circles that appear in no filled-shape
list. Their positions are exact even when their glyphs are not, and glyph
WIDTHS can carry information the positions do not: on one card the single
narrow ink box fell where the positional rule said port 1 was, and the only
two double-width boxes fell on 10 and 11, which turned a guess into three
independent agreeing facts.

**MEASURE PITCH FROM FLAT FEATURES, NEVER FROM PROJECTING ONES.** In any image
with perspective - and that is every photograph and most isometric renders - a
feature that STANDS OUT of the face is seen at a different angle in each
repeat, so its drawn width shrinks across the frame while a feature painted
FLAT on the same face does not. Five identical modules gave handle widths of
10.4, 8.8, 6.6, 5.0 and 4.7 because the handles project 25 mm; the flat badges
beside them held constant width and gave a pitch of 52.49 against 52.45 from a
second image, agreeing to four hundredths. A step taken from the handles would
have been 54.4 and wrong by two millimetres per bay, compounding across the
row.

**The monotonic shrink is the tell, and it is diagnostic rather than annoying**:
if a repeated feature's measured width slides in one direction across the
frame, you are measuring the projection and not the part. Switch to something
painted on the surface - a badge, a legend, a lamp, a screw head - and
corroborate in a second image.

**A FIGURE IN THE RIGHT DOCUMENT CAN BE A PICTURE OF THE WRONG PRODUCT.**
Where a vendor ships near-twin models, its documents get illustrated with
whichever artwork existed first. One guide's port figures, its datasheet's
front and rear views and all three of its product renders lettered the
faceplate with the SIBLING's model number - while the dimensions, port table,
LED table and callouts in that same guide were written for the device on the
cover. The document was right and its pictures were of something else.

So **read the model name printed in the artwork and check it against the
document you found it in.** When they disagree, the text is usually the
device you want and the geometry may or may not be; say which parts you took
from which, and if you print the correct name on a panel every held image
letters differently, SAY THAT IS A JUDGEMENT rather than letting the drawing
imply you read it somewhere. A photograph of a real unit closes it.

**Measure the repeating features twice, from two different images.** When the
intake holds two independent shots of the same face - an AC and a DC variant, a
guide figure and a DAM photograph - measure the pitch in both before recording
either. The MX304's fans were modelled unevenly spaced because edge detection
assigned fan 1's edges to its grille internals; the DC-variant rear photograph
was sitting unused in the same intake and gave the even layout immediately.

**Implausibility is a failed check, not a finding.** If a measurement produces a
layout no real device has - staggered fans, an off-centre lone port, a slot
pitch that changes halfway - re-measure before you write the provenance
sentence. The MX304's asymmetry survived every gate *because* the provenance
asserted it confidently ("THE GAP BETWEEN FAN 1 AND FAN 2 IS WIDER..."). Lint
passed, the render matched the mis-read overlay, and the sentence read like
diligence. A confident sentence is what makes an error permanent. (L49 now
catches the mechanical half of this; the instinct is still yours.)

**Reference material stays in `working/`** (gitignored). Transcribe facts; never
copy a datasheet, stencil or CAD file into the library.

## Stage 1 - the panel

Establish `chassis.width/height/depth` and each view's `size`.

- The rack face is not the chassis. **The modelled body is the metal between the
  ear fold lines, and ears are never drawn** - not bolt-on ones, and not integral
  flanges either. A 19in / 482mm figure includes them; so does a spec table that
  calls the chassis 19 inches, which is how the MX204 came to be modelled wearing
  its flanges and passed every gate. Measure between the folds, record the ear
  extent in provenance, and subtract it before laying anything out. L43 warns when
  a front or rear face lands in 480-487mm, which is a rack face under a body's name.
- Take proportions from a figure only as *fractions* of a dimension you know from
  the datasheet. Two figures in one guide can disagree by 12% on absolute scale.
- Panel decor (vents, grooves, bezels) goes in `panel.decor`. It is what the
  metal *is* - never what is *installed on* it. If a rectangle has an identity a
  person could put a part number to (a cover, a door, a filler, a blank), it is a
  component in a bay, not paint. The MX80's rear cover was a bare white decor
  rect that a reviewer could not identify because it appeared in no component
  list, and no rule can tell a cover from a recess by its geometry - only you
  know which one you meant.

**Gate 1 - prove a figure can be measured before you measure it.** Render the
guide page at 400-600 dpi (`pdftocairo -png -r 600`), find the panel in it, and
compare its pixel aspect with the datasheet's W/H. If they agree to about a
percent the figure is orthographic and carries geometry, and you can work off it
at a known px/mm. If they do not, the figure is schematic and you may take only
*fractions* from it.

**Photographs almost never pass this gate.** A camera slightly above or to one
side foreshortens the face; a near-straight-on shot of a 2RU router measured
5.43-5.77 against a true 5.06 depending on where the edge was placed. Use photos
for colour, counts and confirmation, and for construction detail a line drawing
flattens away - not for dimensions.

**When two drawings disagree, measure both against something that repeats.** A
hand-built drawing and a vendor figure of the same chassis gave aspects of 0.694
and 0.758, and arguing from the outlines got nowhere. Counting slot pitch across
each - a feature whose true spacing is known - settled it in one step: the widths
agreed to 1%, the heights differed by 8%, so one drawing was stretched
vertically. A repeated feature of known pitch is a ruler that is already in the
picture.

Then render your own panel (`render.py --without silkscreen`) and overlay. If the
aspect is wrong, stop; nothing downstream survives a wrong panel.

## Stage 2 - the cutouts

Declare every hole in `panel.cutouts` before choosing what goes in it.

```yaml
panel:
  cutouts:
  - {id: p1,  at: [46.0, 12.0], size: [14.25, 10.4], shape: rect}
  - {id: sys, at: [9.5, 31.5],  size: [3.0, 3.0],    shape: circle}
```

- One cutout per opening in the metal. A 48-port block is 48 cutouts, on a
  measured pitch, not one rectangle.
- Standard openings come from the registry (`conforms:` on the component you
  will place there tells you the size). Do not eyeball an SFP aperture.
- Positions come from the mechanical drawing. If you only have a guide figure,
  derive **pitch and count** from it and anchor to a datasheet dimension.

A cutout is a promise that something is there. If you punch one and neither
place a part in it nor draw anything inside it, the render shows a dark empty
hole - the MX960 rear had four `switch-N` cutouts punched for inlet rockers with
nothing in them. Either seat something, or draw the thing as decor, or do not
punch the hole. L39 reports openings nothing fills.

**Gate 2.** Render and overlay again. Every hole lines up with the reference.
Count them. This is the last cheap moment to fix a pitch error - after
components are placed, moving 48 holes means moving 48 parts and 48 labels.

L39 checks what it can once the holes are declared: no two overlap, each matches
the standard its occupant `conforms:` to, no legend is printed on one, and a
`port` on a punched panel has a hole of its own. **Name a cutout after the thing
that goes in it** - that identity is what ties the two together, in the rule and
in the tree, and a `cut-` prefix on the same panel as bare ids means neither can
see the other. It says nothing about a panel that declares no cutouts at all,
which is most of the library; a clean run is not a finished panel.

## Stage 3 - the silkscreen

Everything printed on the panel goes in `silkscreen[]`, and each mark says what
it belongs to.

```yaml
silkscreen:
- {at: [53.1, 30.0], text: '1',   for: port-1}
- {at: [90.0,  8.0], text: 'PSU 1', for: psu-1}
- {id: branch-1-leader, path: 'M 169 10.4 H 199.9 V 46.6 H 195.7', for: [breaker-1, branch-1]}
```

- `for:` names the placement or bay the mark annotates. A legend with no owner
  (the model name, a warning) omits it. A mark that joins two things - a leader
  line between a breaker and its terminal - lists both.
- Legends that sit *under* where a module will go are invisible on the real
  device, and the renderer paints them under too. If your label vanishes when the
  component is placed, the label is in the wrong place, not the renderer.
- Text printed on a **module's own faceplate** is not chassis silkscreen. It
  belongs in that component's skin, inside `<g id="silkscreen">`.
- Use `text:` for words and `path:` for lines and symbols. Exactly one.

- **Label what the panel labels.** Every port, lamp and button that carries a
  printed legend on the hardware gets one here. Missing labels are the single
  most repeated review finding: a face that renders correctly and says nothing
  passes every gate, because lint can check a mark that exists and cannot ask
  for one that does not.
- **Anchor a mark to the centre of what it names**, not to a corner of it. A ToD
  label sat on its cutout's top-left edge and looked deliberate. L14 checks that
  a `for:` target is *nearby*; nothing checks alignment, so this is on you.
- **One gap per lamp block.** Measure the lamp-to-label distance once from the
  photograph and reuse it for every lamp in that block. The MX204's RE block had
  gaps of 6.1 mm and 2.2 mm side by side. A multi-line legend centres on its
  lamp rather than straddling the row.

**Gate 3.** Render with silkscreen, compare to the reference. Every legend is
present, spelled as printed, next to its cutout. Lint L14 checks each `for:`
target exists and is nearby; make it pass before moving on.

## Stage 4 - the components

Now populate. **Reuse before building.**

1. Search `library/components/` for an existing component. `std/` and `common/`
   hold cages, jacks, LEDs, PSUs and fans that conform to registry standards.
   A port is `std/sfp-module@1`, not a new rectangle.
2. Only build a new component when nothing fits *and* you have a source for its
   dimensions. A new component with `estimated` size is a last resort and must
   say so.
2b. **Reuse applies inside a component too.** A module's own faceplate carries
   standard hardware - an IEC inlet, a jack, an LED - and a component composes
   those through `parts: [{ref, id, at}]` rather than redrawing them in its skin.
   A PSU here got a hand-drawn "IEC C13" that was not one; `std/c14-inlet` as a
   `parts:` entry was both correct and shorter.
3. `components.bays` is for things that seat into an opening; everything else,
   removable or not, is a `components.placements` entry. See rule 6.
4. An indicator declares what it belongs to: `{id: led-p1, ref: std/led-arrow@1,
   for: port-1, group: sfp28-leds}`. Never rely on naming to imply it.
5. Every placement and bay carries `group:` and `rel-pos:`, and every group is
   declared under top-level `groups:` with its `term` (the vendor's word: Port,
   Slot, Bay), its `role` and `index-origin`. That is what gives the tree, the
   exporter and any DCIM their numbering.

   **`role:` is the one thing the drawing cannot work out for itself.** A PSU
   bay, a fan bay and a line-card bay are all class `bay` - the same hole with a
   module in it - so nothing reading the compiled SVG can tell which of them is
   why the box exists and which two keep it alive. Without it the only ordering
   left is the order the placements happen to be written in, which opened one
   chassis with its power supplies and another with its air filters.
   `traffic` is the work the box is bought to do; `management` is how you reach
   and discipline it (OOB, console, craft, timing and sync); `service` is what
   keeps it running (PSUs, fans, filters); `indicator` is what you read;
   `furniture` is what you neither connect to nor read. Management is its own
   rank rather than part of traffic because it is often written FIRST in a
   manifest, and folding it in still opens the tree with a console socket.
   L37 warns at `modelled` and fails at `verified`.

   **Declare a group when you populate it, not before.** A group nothing joins
   is a category the drawing promises and the hardware does not have; L37 warns.
   **One group per port family, named for the family** - `sfp28`, `qsfp28`,
   `qsfpdd-400g`, with the speed appended where the media token alone does not fix
   it. Then the block declares `attrs: {media, speed}` once instead of on every
   port (lint L22 checks that promise against the members). Not `sfp-ports`, which
   names only the cage; not `row-top`, which names only where it sits; not `ports`,
   which names nothing. If the block genuinely spans media because the vendor's
   faceplate treats it as one thing - a management cluster, a timing block - say so
   in `mixed:` and name the job they do together; lint L23 asks for exactly that.

6. **If the guide has a replacement procedure for it, it is a part, not
   decoration** - but that does not make it a bay. Ask how it is held on:
   - it **slides into an opening** in the metal (PSU, fan, line card) -> a `bay`
     with `accepts:`, and the bay's dark opening is what shows when it is out;
   - it **bolts onto the outside** of the faceplate (an air filter, a cable
     manager, a bezel) -> a `placement`, painting over the panel and its
     silkscreen, because that is where it physically sits.
   Getting this wrong is visible: a non-rectangular part in a bay leaves the
   bay's opening showing around it, like a hole in the chassis that is not there.
7. **`rotate:` pivots a placement on its OWN pre-rotation centre**, so after
   turning a part you have to recompute `at` - the landed box is not where the
   unrotated one sat. Look at the render. The MX204's USB was the right size and
   the right way round and landed 3.75mm outside its own cutout, because the sizes
   agreed and only the position was wrong. L39 now compares the landed box with
   the hole; it did not before, and nothing else does.
8. **Cable-management accessories are not drawn** - cord-retainer bails, tie
   anchors, straps, velcro. They are photographed on a real unit, they are not
   panel facts, and they are noise to every consumer of the drawing. Note them in
   provenance instead.
9. **A row of indicators and buttons sharing one baseline on the real device is
   modelled on one centreline.** A schematic's few-mm scatter is noise, not fact:
   the MX204's OFFLINE button sat 3mm above its five lamps, faithfully copied from
   a drawing already known to be 4.6 percent stretched, and read as sloppiness at
   faceplate scale. Record the deviation if you align them, and the drawing's
   scatter if you do not. No rule enforces this - on some devices the stagger is
   real, and a rule here would fight them.
7. **EVERY BAY GETS A `default:`, OR IT RENDERS AS A HOLE.** A chassis whose bays
   name no occupant draws as an empty frame: no module means no lamp, so nothing
   in it is clickable, nothing is addressable, and the 3D viewer - which finds
   FRUs by looking for `data-path="<bay>/module"` - finds nothing to extrude. All
   eight ASR 9000 chassis sat like that, 121 bays, while 104 components existed
   and were never seated. It reads as a broken renderer and it is empty data.

   The rule, which is what a real chassis looks like: **seat a COVER where the
   vendor makes one, and the REAL PART where it does not.** An empty slot in a
   shipped router has a blank filler in it, not a void. Where no cover exists as
   a part - power, fabric, fan - those bays are never empty in a working chassis,
   so seat the module.

   If the vendor REQUIRES a filler and you have no component for it, that is a
   missing COMPONENT and should say so, not a missing decision. Leave the default
   off and record the sentence that says the filler is required.

8. **A CARRIER IS A MODULE WITH BAYS OF ITS OWN.** A modular line card holding
   MPAs, a SIP holding SPAs - those bays live in the COMPONENT contract and need
   `accepts` and a `default` exactly as a chassis bay does. Check an occupant is
   actually seatable before listing it: one that SPANS TWO BAYS has no
   representation, so naming a double-width part in a single-width subslot draws
   a part wider than its own opening. List what fits; record what does not, and
   why.
9. **Read the guide's LED section for count AND arrangement, and expect them to
   differ per port family.** On one router the QSFP-DD ports carry a stacked
   pair outside each block, the QSFP28 ports four above each column, and the
   SFP28 ports one each. One rule for all of them will be wrong.
10. **Transcribe the spec table, into SECTIONS.** Switch silicon, CPU, memory,
   boot flash, storage, BMC, capacity, buffering, power draw, PSU inputs,
   temperature and humidity all belong in `attrs`. They are why someone opens
   the model. `attrs` is not a flat bag: it is
   `physical / performance / power / thermal / environmental / platform /
   features / management / compliance / lifecycle`, plus `other`. Three rules:
   - **A key keeps its own prefix** - `power.power-max-w`, not `power.max-w`.
     Every attr leaves the manifest as `data-<key>` on the SVG root and is read
     there without its container. Keys are unique across sections; lint L25 is
     an error if two claim one name.
   - **Do not restate what the structure already says.** `rack: '13 RU'` beside
     `chassis.ru: 13`, `slots: '14 front + 14 rear'` beside 33 modelled bays,
     `ports: 28` beside 28 placements. Two sources for one fact, and the prose
     one is the one no tool can use.
   - **`other` is for facts that fit no section, and it is counted.** Lint L24
     reports it and the gaps register carries it as `attrs-unclassified`. Use
     it honestly - it is how the next section gets discovered - but do not use
     it to avoid choosing.
8b. **Every module you place or build gets its power figure, and the key says
   which way the power goes.** Chassis power depends on what is in the chassis,
   so the figure belongs on the module's contract, not in the chassis's prose -
   `psus: '2x 400 W 1+1 redundant'` is a sentence no tool can add up.

   Two keys, and choosing between them is the whole point:
   - a module that **PROVIDES** power - `psu`, `power` - states
     `power-output-w`, the continuous output on its nameplate;
   - a module that **CONSUMES** it - `line-card`, `supervisor`, `fan`,
     `cooling`, `transceiver` - states `power-draw-max-w`, and
     `power-draw-typical-w` beside it where the vendor gives one.

   They are opposite signs of one unit and must never share a key. The library
   used to write `watts: '650'` on every PSU, which says nothing about
   direction: sum it over a chassis holding two PSUs and eight line cards and
   you get a number that is neither, and looks entirely plausible. Lint L28 is
   an **error** on `watts` and on the device-level spellings (`power-max-w` and
   its relatives), which are reserved for the whole box. Numbers, not strings.

   **Where to look, because it is usually not the datasheet.** Vendors publish
   per-card power in the install or reference guide's technical-specifications
   appendix. Cisco's ASR9000 table gives one figure per card per ambient - the
   RSP-440 is 285 W at 25 C, 350 at 40 and 370 at 55 - and `power-draw-max-w`
   takes the highest, which is what `max` means. Note how large the spread can
   be before you decide a low figure is safe: the ASR 9912 fan tray is 290 W at
   25 C and 1800 W at 55.

   **If no document you hold states it, write nothing and leave L27 standing.**
   That warning is the record that the figure is missing, and while it stands
   the chassis total is a floor rather than a total. An estimated watt figure is
   the same number minus the warning, and it will be summed by somebody who
   cannot see that you guessed.

8b-i. **Capture what a power figure MEASURES, not just its value.** The
   qualifier is what makes two numbers comparable later, and a number captured
   without it is the problem. Three questions, every time:
   - **Which measure?** Typical, maximum, minimum. If the document does not say
     — "Total Power 300 W", "Power Consumption: 160W" — file it as
     `power-draw-max-w`, because a single figure on a card spec table is what a
     chassis is budgeted with, **and say in provenance that the vendor did not
     qualify it.** That sentence is not paperwork: it tells the next reader the
     `max` is your reading, so a later document giving a real typical is new
     information rather than a contradiction.
   - **Which scope?** Card alone, or card plus its paired I/O module? Bare
     chassis, or fully configured? At what ambient? Casa heads a row "Maximum
     consumption WITH I/O module"; Cisco gives one figure per card per ambient.
     Put the scope in provenance, and on a device use `power-envelope`.
   - **Which side of the meter?** Draw or supply. A number under a "Power
     Consumption" heading is not automatically consumption: the C100G's
     datasheet prints 4000 W there, and the install guide shows it is the AC
     input to provision for a 3600 W load. Recording it as the device's draw
     put a wrong number in the manifest for two commits.

8b-ii. **When two documents give different numbers, work down this list and
   stop at the first that fits.** Most apparent conflicts are not conflicts.
   1. **Different measures** — typical against maximum. Not a conflict: record
      **both**, as `power-draw-typical-w` and `power-draw-max-w`.
   2. **Different scopes** — with or without a paired module, at different
      ambients, bare against configured, draw against required input. Not
      comparable as they stand; the qualifier belongs with the figure.
   3. **Same measure, same scope, different value.** *Only now* is it a
      conflict. Record it in `gaps:` as `reason: sources-disagree` with both
      figures and their sources in the `note`, and say in provenance which one
      the manifest carries and why.

   `sources-disagree` is the last resort, not the first response to two
   different numbers. Reaching for it early manufactures a finding that is not
   there, and a manufactured conflict looks exactly like a real one.

8c. **What the device's own `power-typical-w` covers, if the document says.**
   On a modular chassis the vendor's figure is ambiguous by default and you
   generally cannot resolve it: the AGR400's datasheet says "Max 527 W, Typical
   186 W" while its own QSG says "638 W at 25 C", a 21 % spread on one SKU with
   neither document naming what was installed. Cisco publishes no chassis draw
   at all for the ASR9000 - only the per-card table and an instruction to
   compute your own budget - while publishing chassis weight *twice*, bare and
   "fully configured using all card slots and six power modules". The vocabulary
   exists; it is just not applied to power.

   So **transcribe the vendor's figure as the vendor's figure and do not
   reconcile it against your module total.** Never add module draw to it, and
   do not treat the total exceeding it as an error. They are two facts with two
   provenances, and asserting a relationship between them is asserting something
   no source states.

11. **Transcribe compliance, and do not tidy the wording.** Every datasheet
   carries a compliance line and we hold it for two devices in thirteen. The
   AGR420's is the worked example: `nebs: 'NEBS Level 3 (pre-test; certificate
   by request)'` is a materially different claim from "NEBS Level 3", and
   shortening it under a heading called `compliance` would turn a hedge into a
   certification - a false statement about a product.
12. **Search for an EOL announcement.** Two minutes, and the notices are nearly
   always public: "<vendor> <model> end of life", "<vendor> <model> end of
   sale", and the vendor's own product-notices page. GA is assumed and GA dates
   are NOT worth hunting; only what has been ANNOUNCED goes in.
   - found -> `lifecycle: {eol: announced, eol-announcement: <url>,
     end-of-sale: ..., end-of-life: ...}`, with the link, because a date no
     reader can check is a claim about a product.
   - searched and found nothing -> `lifecycle: {eol: none-announced}`. Record
     it. This is the state that earns the two minutes: absent means NOBODY
     LOOKED, and "we checked and the vendor has announced nothing" is a real
     finding that must not be indistinguishable from it.

Occupants (a transceiver in a cage) use `mate-to:` and carry no position of
their own.

**Model every face.** Six views, even where a face has no detail. Size them from
the spec table so a rack elevation and the 3D box are right, and say in
provenance that they are deliberately blank. A missing view is indistinguishable
from an unfinished one; an empty view that states why is not.

**Gate 4.** `lint.py` clean. Render both with and without silkscreen. Open the
explorer: the tree reads chassis, then groups in tier order, every row
`id - model`, indicators nested under what they indicate. Then set
`maturity: modelled` and lint again; L15 will tell you if the provenance is
not good enough.

**Read the capability level and its `blocked:` reason before calling it done.**
A view counts toward level 3 `solid` - the level that gets a device into 3D -
only if something is DRAWN on it. A size-only face is honest and still does not
count, which is how the MX204 finished at level 2, `blocked: 4 views top, bottom,
left, right`, with every gate green. Give every face its honest content - a rail,
a label, a vent field, estimated and marked as such - or accept level 2 and say
why in provenance. L45 warns about a size-only face at `modelled`. Then open the
demo and confirm 2D **and** 3D actually load.

**Lint after every structural addition, not just at the end.** The rules see
what is declared, so a rule can only find a collision once both sides exist.
Adding the rear bays to this router immediately surfaced fifteen rivets sitting
on top of the fan modules - L13 had been comparing placements with placements
and had nothing to compare them against. Re-run after each stage.

**Check in a browser you know is current.** Verify against a build you just made;
if you are looking at the deployed demo, confirm the page carries your change
before you trust what it shows. A session was spent chasing a rendering fault
that a deploy had already fixed.

## Gate 5 - audit against the source, twice

**A DEVICE THAT STOPPED HALFWAY AND A FINISHED ONE ARE INDISTINGUISHABLE TO
EVERY AUTOMATED CHECK.** Several models built in parallel were interrupted
mid-task. Some had already written a `device.yaml` that lint passed, carried
six views, said `maturity: modelled` and rendered plausibly - and one of
those carried a defect that a reviewer had caught by eye on a different
device an hour before. The rest were genuinely finished. **Nothing in the
files, and nothing any rule could compute, separated them.**

So the completion signal cannot be the artifact. It has to be a statement
about what was DONE to it: *"I put the render beside the reference at
matched scale, and here is what it showed."* A model that cannot produce
that sentence is not finished however green it lints; if you are reviewing
someone else's, ask for the sentence before you believe the file; and if you
are delegating, require it back, because "lint clean, six views" is exactly
what an interrupted attempt leaves behind.

### By name

**When you audit your OWN files, ask a structural question, not a string one.**
A sweep of 88 components for "which reading does this figure rest on" searched
their provenance for the words the author expected to have used - `highest`,
`conservative`, `disagree` - and reported 24 files with no recorded basis. The
gap was not real. Those 24 record their basis in phrasing the pattern never
anticipated: *"NOT the ... row at 310/320/350 - that is the A9K-8T/4, a
different part number with the same port count, and the two differ by 280 W"*,
and *"READ THAT SPREAD BEFORE USING THE LOW FIGURE"*. Both are model provenance
sentences and neither contains a searchable marker.

**A string search over your own prose measures your recall, not your files** -
and your recall is the thing you are trying to check, so the audit is circular
in exactly the direction that returns a clean answer. The structural form does
not care what words you chose: *does any figure have no provenance key that
could carry its source?* That returned the right answer, zero, in one pass.

The general shape is that **the query you want to run is often not the query the
data supports, and the fix is to ask what the structure can actually answer.**
The same thing one level up stopped a lint rule being useless: region labels
could not be checked against their own regions, because 60 of 61 regions carry
no geometry at all, so the rule had to re-derive the geometry from the face
rather than follow a link that does not exist. And do not try to write prose
that is both good and grep-able - the sentences above are the right ones to have
written. Ask the structure instead.

Then go back to the guide's overview figure and walk its numbered callouts one by
one. For each, name the id in your manifest that satisfies it. Then do the same
for the spec table. Write the audit down - a dozen lines of "callout 13,
grounding point -> `ground-point`" is enough.

This is not ceremony. On the first device built with this skill, every gate
passed and the model still had no grounding point, because callout 13 was never
looked for. Nothing else would have caught it: it lints clean, it renders, and
it looks finished.

**Then walk the L27 and L29 warnings the same way, one at a time.** They name
every module in this device with no power figure. For each, either the source
states it and you missed it - most vendors bury per-card power in an appendix,
not on the datasheet - or no document you hold says, and the warning stays. What
must not happen is the list going unread: a chassis whose L29 count you never
looked at is one whose module total is a floor without anybody knowing it is.

### By eye, at matched scale

A name audit proves things are *present*. It says nothing about whether they are
*right*. For that, put your drawing next to the reference at the SAME scale:

```sh
# reference px/mm = reference panel width in px / real width in mm
cairosvg out.svg -o mine.png --output-width <panel_px>    # same px/mm
# then crop the identical millimetre range from both and view them side by side
```

Rendering to the reference's scale rather than to a convenient pixel width is
what makes the comparison work: the same feature lands in the same place in both
images, and anything that differs stands out immediately. When something looks
off, crop that feature alone at 4-5x from both and confirm before claiming it.

**Do this for EVERY face the vendor photographed, not just the front.** A batch
verifier used across three dozen devices in one run compared only front faces,
so every rear went to commit on trust - and the rear is where the fans, the
supply inlets, the ground stud and the airflow tags live, none of which the
front can vouch for. Front-only checking does not announce itself: the report
line looks identical whether the rear was compared and matched or never compared
at all. If a face has no reference image, say so in the report rather than
letting a short list read as a clean result.

This is how the AGR400's RJ-45s were caught. At matched scale it was obvious
that four of six jacks were upside down - a 2-high ganged jack mirrors its rows
so both release tabs stay reachable, and the component draws only one
orientation. Nothing in the manifest was wrong; nothing would ever have linted.
Only looking found it.

### A RULE YOU APPLIED TO PART OF A FACE MUST REACH THE END OF IT

The most common defect that survives lint is not a wrong feature - it is a right
feature that stops early. A numbering scheme printed under fifty ports and not
the last four. Per-port lamps counted across one block and not carried onto the
block beside it. A shell drawn on the ganged cages at one end of the panel and
not the other.

It happens because the rule is derived where the evidence is strongest - the
dense repeating block that made the pitch obvious, the band where the colour
sampling worked - and the tail of the face is a different block, sampled
separately, finished later. By then the rule feels like something already done.

Nothing catches this. Lint sees a legal face. A name audit sees every port
present, because the ports ARE present - it is their *printing* that stopped.
And the provenance usually reads perfectly, because the sentence describing the
rule was written while it was still true of everything the writer was looking at.

So at Gate 5, for each rule you applied - numbering, lamps, shells, decor bands,
legends - **find the last element it covers and check what comes after it.** If
the rule stops, the file must say which of the two is true:

    the rule really stops there            say so, in provenance or a gap
    the rule was not carried to the end    carry it

A reader comparing your render against a photograph cannot tell those apart, and
will read the second one as an error in the model. Four unprinted numerals among
fifty printed ones is indistinguishable from four ports you got wrong.

**But do not assume the answer is "carry it".** Real faceplates stop rules all
the time - a block identified by band colour and a row symbol instead of by
number, a legend the vendor prints on one bank and not its neighbour. Going and
looking is the requirement; extending the rule is only one of its two outcomes.
A device was sent back on exactly this finding and came back correct as drawn,
because the metal genuinely carries no printing there. **Printing ink that is
not on the device is the one thing silkscreen must never do**, and it is the
harder error to detect later, because it looks like diligence.

### A NEGATIVE READING OFF A COARSE IMAGE NEEDS A CONTROL IN THE SAME IMAGE

Which raises the real problem: at low resolution, "this area carries no
printing" and "this image cannot resolve the printing here" produce an
identical pixel field. You cannot separate them by looking harder at the area
in question.

**Find something in the same image, at the same scale and similar contrast,
whose printing you KNOW is there - and check that it survives.** If the known
printing resolves and the questioned area is uniform, the silence is a reading.
If the known printing has also dissolved, you have learned the image's limit and
nothing about the device.

    questioned area is blank                     proves nothing on its own
    + a comparable known-printed area resolves   now it is evidence

Pick the control for similarity, not convenience: same darkness of ground, same
glyph size, same distance from the lens. A crisp black-on-white legend elsewhere
on the panel is not a control for pale grey text on a dark band.

This also tells you when to stop arguing. If no suitable control exists in any
image you hold, the honest output is a gap saying the area is unresolved - not a
confident sentence in either direction.

### Against a second party, for completeness only

If the device is in **NetBox Labs NDX** (`netboxlabs.com/ndx/<vendor>/<model>/`),
walk their field list and account for anything they have that you do not. It is a
free second reading of the same public datasheet.

Use it for **completeness, never correctness**. Almost no failure in this project
has been a wrong number; they have been categories nobody looked for - a
grounding point that was callout 13, a rear air filter, an entire compliance
section. A second party who read the same document is a cheap way to ask "did I
miss a KIND of thing?".

Two rules, because it is a derived aggregate and not a source:

- **A disagreement sends you back to the vendor document, not to their number.**
  Their own confidence scale runs down to "Unverified (community contribution)"
  and "heuristic derivation". They can be wrong in exactly the way a confident
  secondary source is always wrong.
- **A difference is expected and is usually ours to keep.** They list interfaces
  and stop; we model USB, timing inputs, SMA and SMB jacks, grounding plates and
  rivets. Finding that we have more is the normal outcome. The question is only
  ever whether they have something we lack.

Do not ingest their enrichment layer. Reading a public page to check your own
work is diligence; copying a commercial catalogue into this repo is not.

## The canonical shape

Key order is fixed and linted (L16). A view reads top to bottom in the order
the part is made.

```yaml
format: 1
kind: device
name: <slug>
version: 0.1.0
maturity: draft | modelled | verified
manufacturer: <Vendor>
model: <Model>
description: >-
  one paragraph
provenance:
  <key>: '<confidence> - <where, precisely>'
attrs:
  physical: {...}      # sections, not a flat bag - see step 8. Omit any that
  performance: {...}   # have no data; `other` is counted, not free.
  power: {...}
  thermal: {...}
  environmental: {...}
  platform: {...}
  features: {...}
  management: {...}
  compliance: {...}
  lifecycle: {eol: none-announced}
  other: {...}
chassis: {width: , height: , depth: , ru: , color: }
groups:
  sfp-plus: {term: Port, role: traffic, index-origin: 1, attrs: {media: sfp-plus, speed: 10g}}
  sfp-plus-leds: {term: LED, role: indicator, index-origin: 1}
  mgmt: {term: Port, role: management, index-origin: 1, mixed: <the job these ports share>}
views:
  front:
    size: {w: , h: }
    panel:
      decor: [...]
      cutouts: [...]
    silkscreen: [...]
    components:
      bays: [...]
      placements: [...]
    regions: [...]        # author-drawn callout boxes; last, optional
configurations: {...}
```

## When something is not behaving: `references/pitfalls.md`

Everything above is what you need to START a device. There is a second file in
this skill holding the mistakes this project has actually made - a rotated crop
read bottom-to-top, a lint rule that fabricated an error, a legend that belonged
to a module rather than the chassis, and about forty more. Several of them
survived a lint run, a render and a review before anybody noticed.

**Read it when a figure, a measurement or a lint warning is not doing what you
expect.** The answer is very often already there, written by whoever lost the
cycle to it. It is not required reading before you draw - six thousand tokens of
other people's mistakes is not the best use of the attention you need for the
face in front of you.

## What is already deterministic - do not re-derive it

Three things were being worked out by hand, per device, and are now lookups.
Using them is not a shortcut; it is the difference between a number with a
source and a number off a 520-pixel render.

- **`spec/schemas/standards.yaml` states cage PITCH.** It has all along, with a
  confidence token and a paragraph of derivation. It states it two ways and the
  difference matters: some standards carry an explicit `pitch` beside a narrower
  opening, because ganged cages share a wall; others carry no pitch key at all
  because for that family `w` IS the pitch and instances abut exactly. Never
  measure a ganged pitch off an image without checking here first.
- **`spec/tools/portrayal/facts.py`** pulls the stated dimensions, RU, weight,
  port counts, ordering lines and power figures out of a model's converted
  documents, each citing the file and line it came from. Read that before paging
  the PDFs. It also says when a document NAMES specifications and states none of
  them - a datasheet set in outlined glyphs converts to its labels and not its
  numbers, which is why such a file reads as complete when it is empty.
- **`spec/tools/portrayal/expand.py`** generates the repeating half of a face -
  placements, cutouts, numerals and lamps - from a compact block description in
  a `layout.yaml`. Roughly 41% of a device file is these items and none of it
  carries a decision. A loop does not get tired near the end of a face, which is
  the failure it exists to remove.

Absence in a facts file means the tool did not find it, NEVER that the vendor is
silent. Only someone who has looked can make that second claim.

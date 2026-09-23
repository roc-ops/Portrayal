# Modelling a device

A faceplate is made in a fixed order: the sheet metal is sized, it is punched,
it is printed, and only then are the parts installed. Model it in that order,
and do not start a stage until the previous one has been checked against the
reference. Every serious defect this library has shipped came from skipping
that check: terminals drawn where breakers were, fifty-four ports that all read
"SFP module", a chassis twelve percent too wide because a page margin was
measured as metal.

You will produce `library/devices/<vendor>/<model>/device.yaml` in the
canonical shape at the end of this page, linting clean at `maturity: modelled`,
and one sentence: *I put the render beside the reference at matched scale, and
here is what it showed.* A model that cannot produce that sentence is not
finished, however green it lints. [CONTRIBUTING](../CONTRIBUTING.md) has the
commands; this page is the method. When a figure or a lint warning behaves
oddly, [modelling-pitfalls.md](modelling-pitfalls.md) probably already explains
why.

## Before you draw anything: sort the sources

Each kind of source may answer only certain questions. Mixing their roles is the
most repeated error in the library.

| source | authoritative for | never use it for |
|---|---|---|
| **datasheet / spec table** | overall dimensions, RU, weight, port counts, the box's own power figure | positions; per-module power, which it almost never carries |
| **install guide figure** | *what* is on a face and *how it is arranged*; port order; legends | absolute geometry: these figures are schematic and their aspect is wrong |
| **install / reference guide appendix** | per-card and per-fan-tray power, and the ambient each figure assumes | anything the datasheet answers better |
| **mechanical drawing** (vendor's, or hand-built from the hardware) | size and placement of every feature | colour, legend text |
| **vendor 3D model** (GLB/glTF, STEP, USDZ) | size and placement of every feature, at CAD truth | which of two adjacent lamps belongs to which port, and anything the geometry does not name |
| **photograph** | colour, finish, construction, confirmation of everything above; counts | measurement, unless something of known size is in frame |
| **standards registry** (`spec/schemas/standards.yaml`) | cage and connector sizes | anything vendor-specific |

Write the source list into `provenance:` first, before a single number. Every
number you write afterwards names its source at the moment you write it. That is
what makes `maturity` honest, and what lets the next person know which figure
to re-measure when something is wrong.

An entry is `{confidence, note}`, not a sentence. The `note` is the prose - what
you read and out of which figure - and `confidence` is the word, so that a rule
can ask what previously only a reader could answer. The eight words, used
verbatim: `datasheet`, `drawing`, `measured`, `photo-measured`, `registry`,
`borrowed`, `estimated`, `known-wrong`. Anything `estimated` keeps the device out
of `verified`, and L15 now reads both the word and the note, so burying
"estimated" in the middle of a paragraph no longer hides it.

**Omit `confidence` rather than guess at it.** It is optional for exactly this
reason: a figure whose standing you do not know is a figure whose standing
nobody has written down, and L93 counts those so they can be worked through. A
word chosen to make the count go down is the one outcome this field is against.

### A vendor 3D model outranks every figure. Look for one first.

Product pages increasingly embed a 3D model to drive an in-page viewer, and it
is often an export of the actual CAD: one mesh per physical part, at millimetre
scale. Where one exists, port pitch, lamp positions, cage depths and screw
locations come off it directly and the panel gate below does not apply, because
there is no projection to be wrong about. Look on the product page for `.glb`,
`.gltf`, `.usdz` or a `model-viewer` element before concluding you only have
figures. `spec/tools/intake/glb_parts.py` lists a model's parts with their
world-space boxes.

Expect the datasheet's overall dimensions to disagree with the CAD body, and
read the shape of the disagreement. If the three deltas are unequal per axis,
they are protrusions and mounting furniture outside the metal (handles, jack
noses, feet) and the CAD body is what you model. If they are equal, you have a
scale or unit error and must stop.

What CAD cannot tell you is anything with a name rather than a shape: which of
four adjacent lamps serves which cage, what an unlabelled boss is for. Geometry
has no labels. Those stay `vendor-silent` gaps no matter how good the mesh is.

### The figures are already in the documents you hold. Extract them first.

Before searching the web, and before declaring a vendor silent about what a face
looks like, pull the figures out of the PDFs you have staged. Two vendor lines
and some 250 components were modelled here before anyone did, and the documents
turned out to hold over two thousand captioned figures: faceplate elevations
with every port numbered, isometric drawings showing ejectors and rails, LED
callout tables sitting under the drawing that names them.

`spec/tools/intake/extract.py` converts a PDF into `working/images/<stem>/`
with each figure beside its caption, page and section. Use it rather than
`pdfimages`: a figure without its caption is an image; a figure with "Figure
27: 1-Port 100-Gigabit Ethernet Modular Port Adapter with CFP2" is evidence.

Two habits that keep the extraction honest:

- **Save every picture first and classify second.** A filter that drops
  pictures by size is shaped like the last vendor you looked at. The first one
  written here dropped every Cisco datasheet faceplate, too short for a figure
  and too wide for a banner, and each datasheet then returned zero figures,
  which reads exactly like "this vendor published no pictures". Keep the rejects
  on disk and look at a sample of what you dropped.
- **A negative answer is only as good as the extraction's coverage.** Count
  `^Figure \d+:` in the document's text and compare it with what you captured.
  "No figure for this part" means something very different at 62 of 62 than at
  39 of 62.

### A vendor stencil is a diagram symbol, not a drawing of the product

Visio stencils are vector, they carry connection points, and they are the
fastest thing in the box to measure. They are also drawn to be legible at
rack-elevation size in someone's network diagram, and they are simplified in
ways that look complete. Get a product photograph or a vendor render and check
the stencil against it before you place anything.

The Smartoptics DCP-404 was first built from its stencil and came out
confidently wrong: one vent feature drawn of seven, a single status lamp far
right where the unit has two lower left, traffic lamps under the cages where the
unit has them beside the Tx/Rx captions, the port block 16 mm off because the
stencil dropped the vent column that pushes it right, and a face height of 41
against a real 44, so every y was six percent short. Nothing there is visible
without the photograph. The model rendered plausibly and passed every gate.

What the stencil was still good for: it agreed with the photograph on the
brand, model and hazard marks to a millimetre, and its connection points showed
that the four client cages abut, which is the difference between composing
ganged cages and composing single cages that overlap. Use it as a second opinion
and as the source of connection points; never as the only thing you looked at.

Find the datasheet's dimensions first; they settle the stencil's scale. Check
the axis labels rather than trusting them: the DCP-404 datasheet reads "Size
(WxDxH) 44 x 205 x 270mm", which is transposed.

### A figure's own aspect tells you whether to trust it

Before taking any fraction off a drawing, measure the drawing against something
you already know, usually the part's own outline against its contract size.

    Casa BDM      figure aspect 12.54   real 11.34      10% out
    Casa PEM      isolated part drawings                10% out
    Cisco SPA     plate against subslot band             4% out

At four percent you can take fractions along the good axis. At ten you cannot
take absolute scale at all, and you should say so rather than quietly using it.

A round feature that reads two different sizes is measuring the drawing, not
the feature. A lamp 15 px across and 17 px down is not two candidate diameters;
it is one drawing twelve percent out in aspect. Leave the diameter alone and say
why. Take proportions on the axis you can anchor, and only that one: where a
contract holds a trusted height and no equally trusted width, fix the y, leave
the x, and say which is which.

### Use every image you have, not the first one that answers

Guide art is often a mock-up rather than a finished unit and shows placeholders
where the real part has hardware. On one router the guide drew plain diamonds
along the rear where the real chassis has rivet heads, and two more where the
real device has a two-hole grounding plate under an earth symbol. Vendor stock
renders are a third source again and may show a different SKU: a stock rear
showed an AC supply where the unit in hand was DC.

Check the guide figure, the vendor's stock renders and the photographs of the
real device before drawing anything. Where they disagree, the real device wins,
and say so in provenance. Where they differ because they are different
variants, model both, usually as skins of one shell. A photograph with a ruler
in it is a measurement: two close-ups of that router had a tape measure lying
beside the part, which turned two estimated depths into measured ones.

**Measure pitch from flat features, never from projecting ones.** In any image
with perspective, a feature that stands out of the face is seen at a different
angle in each repeat, so its drawn width shrinks across the frame while a
feature painted flat on the same face does not. Five identical modules gave
handle widths of 10.4, 8.8, 6.6, 5.0 and 4.7 because the handles project 25 mm;
the flat badges beside them held constant width and gave a pitch of 52.49
against 52.45 from a second image. The monotonic shrink is the tell: if a
repeated feature's measured width slides in one direction across the frame, you
are measuring the projection. Switch to a badge, a legend, a lamp, a screw head,
and corroborate in a second image.

**Measure the repeating features twice, from two different images.** The
MX304's fans were modelled unevenly spaced because edge detection assigned fan
1's edges to its grille internals; the DC-variant rear photograph was sitting
unused in the same folder and gave the even layout immediately.

**A figure in the right document can be a picture of the wrong product.** Where
a vendor ships near-twin models, its documents get illustrated with whichever
artwork existed first. One guide's port figures, its datasheet's views and all
three product renders lettered the faceplate with the sibling's model number,
while the dimensions, port table and LED table in the same guide were written
for the device on the cover. Read the model name printed in the artwork and
check it against the document you found it in. When they disagree, the text is
usually the device you want and the geometry may or may not be; say which parts
you took from which.

**Implausibility is a failed check, not a finding.** If a measurement produces
a layout no real device has (staggered fans, an off-centre lone port, a slot
pitch that changes halfway) re-measure before you write the provenance
sentence. The MX304's asymmetry survived every gate because the provenance
asserted it confidently. A confident sentence is what makes an error permanent.

### Before you write "no document states this", run two searches

"Not in the document I looked in" and "not in anything I hold" are different
claims, and the second is much stronger. Writing the second while having checked
only the first happened seven times in one vendor's set here, every one found
later by somebody searching differently, and every one had a well-written
paragraph of provenance explaining a silence that was not there.

- **Search every document for the field name, not the part number.** Searching
  for `A9K-RSP-4G` finds release notes. Searching for `Power consumption` finds
  that card's own data sheet, with the dimensions, depth and weight a component
  had been carrying as "not stated anywhere". Do the same for `Physical
  dimensions` and for any wattage figure; the answer is usually in a document
  about a different part.
- **Check whether an older revision carries a table the current one dropped.**
  Vendors delete content between revisions. One line-card installation guide
  replaced its entire per-part dimensions table with a sentence pointing at a
  URL; the older revision of the same guide still has the table. And note how
  that one defeats a search: the newer guide still has a section headed
  "Ethernet Line Card Physical Dimensions". When a heading promises exactly
  what you are looking for, read the section rather than trusting the heading.

Then record which searches you ran, not just the conclusion. "Table 35 has no
row for any 5th-generation card, and no data sheet carries one either" is a
statement somebody can check and overturn. "No document states this" is not.

### Before you write "the artwork prints no X", render it

Text extraction finding nothing and the drawing printing nothing are different
claims, and outlined glyphs make the first look exactly like the second. One
master printed all twelve of its port numerals as outlined glyphs and the
extractor returned none of them, so a first draft asserted the card numbered no
ports. Render the master and look at it before any claim about what a drawing
does or does not carry. What the extractor missed is usually recoverable once
you know it is there: numerals as small dark boxes, indicators as triangles,
lamps as stroked circles that appear in no filled-shape list.

Reference material stays in `working/`, which is gitignored. Transcribe facts;
never copy a datasheet, stencil, photograph or CAD file into the library.

## Stage 1: the panel

Establish `chassis.width/height/depth` and each view's `size`.

- **The rack face is not the chassis.** The modelled body is the metal between
  the ear fold lines, and ears are never drawn, neither bolt-on ones nor
  integral flanges. A 19-inch / 482 mm figure includes them; so does a spec table
  that calls the chassis 19 inches, which is how the MX204 came to be modelled
  wearing its flanges and passed every gate. Measure between the folds, record
  the ear extent in provenance, and subtract it before laying anything out.
  Lint L43 warns when a front or rear face lands between 480 and 487 mm.
- Take proportions from a figure only as fractions of a dimension you know from
  the datasheet. Two figures in one guide can disagree by twelve percent on
  absolute scale.
- Panel decor (vents, grooves, bezels) goes in `panel.decor`. It is what the
  metal *is*, never what is *installed on* it. If a rectangle has an identity a
  person could put a part number to (a cover, a door, a filler, a blank), it is
  a component in a bay, not paint. The MX80's rear cover was a bare white decor
  rectangle nobody could identify because it appeared in no component list.

**Gate 1: prove a figure can be measured before you measure it.** Render the
guide page at 400 to 600 dpi (`pdftocairo -png -r 600`), find the panel in it,
and compare its pixel aspect with the datasheet's width and height. If they
agree to about a percent the figure is orthographic and carries geometry, and
you can work off it at a known px/mm. If they do not, the figure is schematic
and you may take only fractions from it.

Photographs almost never pass this gate. A camera slightly above or to one side
foreshortens the face; a near-straight-on shot of a 2RU router measured 5.43 to
5.77 against a true 5.06 depending on where the edge was placed. Derive px/mm
on a photo twice, once across from the known width and once down from the known
height: if they agree the face is near-orthographic and you can measure it; if
they diverge you are looking at perspective.

When two drawings disagree, measure both against something that repeats. A
hand-built drawing and a vendor figure of the same chassis gave aspects of
0.694 and 0.758; counting slot pitch across each settled it in one step, because
the widths agreed to one percent and the heights differed by eight. A repeated
feature of known pitch is a ruler already in the picture.

Then render your own panel (`render.py --without silkscreen`) and overlay it. If
the aspect is wrong, stop; nothing downstream survives a wrong panel.

## Stage 2: the cutouts

Declare every hole in `panel.cutouts` before choosing what goes in it.

```yaml
panel:
  cutouts:
  - {id: p1,  at: [46.0, 12.0], size: [14.25, 10.4], shape: rect}
  - {id: sys, at: [9.5, 31.5],  size: [3.0, 3.0],    shape: circle}
```

- One cutout per opening in the metal. A 48-port block is 48 cutouts on a
  measured pitch, not one rectangle.
- Standard openings come from the registry; `conforms:` on the component you
  will place there tells you the size. Do not eyeball an SFP aperture.
- Positions come from the mechanical drawing. If you only have a guide figure,
  derive pitch and count from it and anchor to a datasheet dimension.
- Name a cutout after the thing that goes in it. That identity is what ties the
  two together in the rules and in the tree.

A cutout is a promise that something is there. If you punch one and neither
place a part in it nor draw anything inside it, the render shows a dark empty
hole; the MX960 rear had four rocker-switch cutouts with nothing in them.
Either seat something, draw the thing as decor, or do not punch the hole. L39
reports openings nothing fills, checks that no two overlap, that each matches
the standard its occupant conforms to, and that no legend is printed on one. It
says nothing about a panel that declares no cutouts at all.

**Gate 2.** Render and overlay again. Every hole lines up with the reference.
Count them. This is the last cheap moment to fix a pitch error; after
components are placed, moving 48 holes means moving 48 parts and 48 labels.

## Stage 3: the silkscreen

Everything printed on the panel goes in `silkscreen[]`, and each mark says what
it belongs to.

```yaml
silkscreen:
- {at: [53.1, 30.0], text: '1',   for: port-1}
- {at: [90.0,  8.0], text: 'PSU 1', for: psu-1}
- {id: branch-1-leader, path: 'M 169 10.4 H 199.9 V 46.6 H 195.7', for: [breaker-1, branch-1]}
```

- `for:` names the placement or bay the mark annotates. A legend with no owner
  (the model name, a warning) omits it. A mark that joins two things, such as a
  leader line between a breaker and its terminal, lists both.
- Legends that sit under where a module will go are invisible on the real
  device, and the renderer paints them under too. If your label vanishes when
  the component is placed, the label is in the wrong place.
- Text printed on a module's own faceplate is not chassis silkscreen. It
  belongs in that component's skin, inside `<g id="silkscreen">`.
- Use `text:` for words and `path:` for lines and symbols. Exactly one.
- **Label what the panel labels.** Every port, lamp and button that carries a
  printed legend on the hardware gets one here. Missing labels are the single
  most repeated review finding: a face that renders correctly and says nothing
  passes every gate, because lint can check a mark that exists and cannot ask
  for one that does not.
- **Anchor a mark to the centre of what it names**, not a corner of it. L14
  checks that a `for:` target is nearby; nothing checks alignment.
- **One gap per lamp block.** Measure the lamp-to-label distance once from the
  photograph and reuse it for every lamp in that block.

**Gate 3.** Render with silkscreen, compare to the reference. Every legend is
present, spelled as printed, next to its cutout. Make L14 pass before moving on.

## Stage 4: the components

Now populate. Reuse before building.

1. **Search `library/components/` first.** `std/` and `common/` hold cages,
   jacks, lamps, PSUs and fans that conform to registry standards. A port is
   `std/sfp@1`, not a new rectangle. The
   [components README](../library/components/README.md) says which namespace a
   new part goes in and how it is named.
2. **Build a new component only when nothing fits and you have a source for
   its dimensions.** A new component with `estimated` size is a last resort and
   must say so. Reuse applies inside a component too: a module's faceplate
   carries standard hardware, an inlet, a jack, a lamp, and the component
   composes those through `parts:` rather than redrawing them. A PSU here once
   got a hand-drawn "IEC C13" that was not one; `std/c14-inlet` as a `parts:`
   entry was both correct and shorter.
3. **Bays are for things that seat into an opening; everything else is a
   placement.** If the guide has a replacement procedure for it, it is a part,
   not decoration, but that does not make it a bay. Ask how it is held on: it
   slides into an opening (PSU, fan, line card), so a `bay` with `accepts:`,
   whose dark opening shows when it is out; or it bolts onto the outside (an
   air filter, a cable manager, a bezel), so a `placement`, painting over the
   panel. Getting this wrong is visible: a non-rectangular part in a bay leaves
   the bay's opening showing around it.
4. **An indicator declares what it belongs to**: `{id: led-p1, ref:
   std/led-arrow@1, for: port-1, group: sfp28-leds}`. Never rely on naming.
5. **Every placement and bay carries `group:` and `rel-pos:`**, and every group
   is declared under top-level `groups:` with its `term` (the vendor's word:
   Port, Slot, Bay), its `role` and `index-origin`. That is what gives the tree,
   the exporter and any DCIM their numbering.

   `role:` is the one thing the drawing cannot work out for itself. A PSU bay,
   a fan bay and a line-card bay are all the same hole with a module in it, so
   nothing reading the compiled SVG can tell which is why the box exists and
   which two keep it alive. `traffic` is the work the box is bought to do;
   `fabric` is the cell or chassis interconnect of a distributed chassis (the
   ports only; a fabric card is still `service`);
   `management` is how you reach and discipline it (OOB, console, craft,
   timing); `service` is what keeps it running (PSUs, fans, filters);
   `indicator` is what you read; `furniture` is what you neither connect to nor
   read. L37 warns at `modelled` and fails at `verified`.

   Declare a group when you populate it, not before. One group per port
   family, named for the family: `sfp28`, `qsfp28`, `qsfpdd-400g`, with the
   speed appended where the media token alone does not fix it. The block then
   declares `attrs: {media, speed}` once (L22 checks that promise against the
   members). Not `sfp-ports`, which names only the cage; not `row-top`, which
   names only where it sits. If a block spans media because the vendor treats
   it as one thing, a management cluster, a timing block, say so in `mixed:`
   and name the job they do together (L23).
6. **`rotate:` pivots a placement on its own pre-rotation centre**, so after
   turning a part recompute `at`; the landed box is not where the unrotated one
   sat. Look at the render. L39 compares the landed box with the hole.
7. **Cable-management accessories are not drawn**: cord-retainer bails, tie
   anchors, straps. They are not panel facts. Note them in provenance instead.
8. **A row of indicators and buttons sharing one baseline on the real device is
   modelled on one centreline.** A schematic's few-millimetre scatter is
   noise. Record the deviation if you align them, and the drawing's scatter if
   you do not; on some devices the stagger is real.
9. **Every bay gets a `default:`, or it renders as a hole.** A chassis whose
   bays name no occupant draws as an empty frame: nothing in it is clickable
   or addressable, and the 3D viewer finds nothing to extrude. All eight ASR
   9000 chassis sat like that, 121 bays, while 104 components existed and were
   never seated. Seat a cover where the vendor makes one and the real part
   where it does not; an empty slot in a shipped router has a blank filler in
   it, and power, fabric and fan bays are never empty in a working chassis. If
   the vendor requires a filler and no component exists for it, that is a
   missing component, not a missing decision: leave the default off and record
   the sentence that says the filler is required.
10. **A carrier is a module with bays of its own.** A modular line card holding
    adapters has those bays in its component contract, with `accepts` and a
    `default` exactly as a chassis bay does. Check an occupant is actually
    seatable before listing it; one that spans two bays has no representation.
11. **Read the guide's LED section for count and arrangement, and expect them
    to differ per port family.** On one router the QSFP-DD ports carry a
    stacked pair outside each block, the QSFP28 ports four above each column,
    and the SFP28 ports one each.
12. **Transcribe the spec table, into sections.** `attrs` is not a flat bag:
    `physical / performance / power / thermal / environmental / platform /
    features / management / compliance / lifecycle`, plus `other`. A key keeps
    its own prefix (`power.power-max-w`, not `power.max-w`) because every attr
    leaves the manifest as `data-<key>` on the SVG root, and keys are unique
    across sections (L25). Do not restate what the structure already says:
    `ports: 28` beside 28 placements is two sources for one fact, and the
    prose one is the one no tool can use. `other` is for facts that fit no
    section and it is counted (L24); use it honestly, not to avoid choosing.
13. **Transcribe compliance, and do not tidy the wording.** `nebs: 'NEBS Level
    3 (pre-test; certificate by request)'` is a materially different claim
    from "NEBS Level 3", and shortening it would turn a hedge into a
    certification.
14. **Search for an end-of-life announcement.** Two minutes, and nearly always
    public. Found: `lifecycle: {eol: announced, eol-announcement: <url>,
    end-of-sale: ..., end-of-life: ...}`. Searched and found nothing:
    `lifecycle: {eol: none-announced}`, because absent means nobody looked.

Occupants (a transceiver in a cage) use `mate-to:` and carry no position of
their own.

A placement that presents **more than one interface** says so with
`interfaces:`. A Compact SFP (CSFP) cage is the case that needs it: the module
fits a standard SFP cage and carries two independent BiDi fibre connections,
so a 24-cage switch has 48 interfaces. They belong on the host cage, not the
optic, because the switch's silicon has both whether or not a module is
seated - `{ref: std/sfp-ganged@1, id: csfp-1-3, interfaces: [port-1, port-3]}`.
The DCIM export lists each interface and not the cage. The ids must be unique
in the view and must not be a placement's or bay's id, and only a port can
present them (L105). Breakout is different and stays a description on one
interface: it is a mode a port is configured into, not two ports that always
exist.

### Power figures

Every module you place or build gets its power figure, and the key says which
way the power goes. Chassis power depends on what is in the chassis, so the
figure belongs on the module's contract: a module that **provides** power
(`psu`, `power`) states `power-output-w`; a module that **consumes** it
(`line-card`, `supervisor`, `fan`, `cooling`, `transceiver`) states
`power-draw-max-w`, with `power-draw-typical-w` beside it where the vendor
gives one. They are opposite signs of one unit and must never share a key.
L28 is an error on the old `watts` and on device-level spellings used on a
module. Numbers, not strings.

Vendors publish per-card power in the install or reference guide's
specifications appendix, not the datasheet. Cisco's ASR 9000 table gives one
figure per card per ambient (the RSP-440 is 285 W at 25 C, 350 at 40, 370 at
55) and `power-draw-max-w` takes the highest. Note how large the spread can be
before deciding a low figure is safe: the ASR 9912 fan tray is 290 W at 25 C and
1800 W at 55.

If no document you hold states it, write nothing and leave L27 standing. That
warning is the record that the figure is missing, and while it stands the
chassis total is a floor rather than a total. An estimated figure is the same
number minus the warning, and it will be summed by somebody who cannot see that
you guessed.

Capture what a figure measures, not just its value. Three questions every time:
**which measure** (typical, maximum; if unqualified, file it as `max` and say in
provenance that the vendor did not qualify it), **which scope** (card alone or
with its paired module, bare or configured chassis, at what ambient; use
`power-envelope` on a device), and **which side of the meter** (a number under
"Power Consumption" is not automatically consumption: the C100G datasheet
prints 4000 W there, and the install guide shows it is the AC input to
provision for a 3600 W load).

When two documents give different numbers, work down this list and stop at the
first that fits. Different measures (typical against maximum): record both.
Different scopes: not comparable; the qualifier belongs with the figure. Same
measure, same scope, different value: only now is it a conflict, recorded in
`gaps:` as `reason: sources-disagree` with both figures and their sources.
Reaching for `sources-disagree` early manufactures a finding that is not there.

Transcribe the vendor's chassis figure as the vendor's figure and do not
reconcile it against your module total. Never add module draw to it, and do not
treat the total exceeding it as an error. They are two facts with two
provenances.

### Every face

Model six views, even where a face has no detail. Size them from the spec table
so a rack elevation and the 3D box are right. A face with nothing documented on
it says so in an `empty:` sentence that names what you searched; a missing view
is indistinguishable from an unfinished one, and an empty view that states why
is not. [deliberately-empty-faces.md](deliberately-empty-faces.md) is the
reasoning.

**Gate 4.** `lint.py` clean. Render both with and without silkscreen. Open the
viewer: the tree reads chassis, then groups in tier order, every row `id -
model`, indicators nested under what they indicate. Set `maturity: modelled`
and lint again; L15 will tell you if the provenance is not good enough. Read
the capability level and its `blocked:` reason before calling it done. Lint
after every structural addition, not just at the end: rules see what is
declared, so a collision is only visible once both sides exist. Adding the rear
bays to one router immediately surfaced fifteen rivets sitting on the fan
modules.

## Gate 5: audit against the source, twice

A device that stopped halfway and a finished one are indistinguishable to every
automated check. Several models built in parallel here were interrupted
mid-task; some had written a `device.yaml` that lint passed, carried six views,
said `maturity: modelled` and rendered plausibly, and one carried a defect a
reviewer had caught by eye on a different device an hour before. Nothing in the
files separated them. So the completion signal is a statement about what was
done: *I put the render beside the reference at matched scale, and here is what
it showed.* If you are reviewing someone else's, ask for that sentence before
you believe the file.

### By name

Go back to the guide's overview figure and walk its numbered callouts one by
one. For each, name the id in your manifest that satisfies it. Then do the same
for the spec table. Write the audit down; a dozen lines of "callout 13,
grounding point → `ground-point`" is enough. On the first device built with
this method, every gate passed and the model still had no grounding point,
because callout 13 was never looked for.

Then walk the L27 and L29 warnings the same way. They name every module in the
device with no power figure. For each, either the source states it and you
missed it, or no document you hold says and the warning stays. What must not
happen is the list going unread.

When you audit your own files, ask a structural question, not a string one. A
search of your provenance for the words you expect to have used measures your
recall, not your files. "Does any figure lack a provenance key that could carry
its source?" is a question the structure can answer.

### By eye, at matched scale

A name audit proves things are present. It says nothing about whether they are
right. Put your drawing next to the reference at the same scale:

```sh
# reference px/mm = reference panel width in px / real width in mm
# cairosvg is optional (pip install cairosvg); CI does not need it. Any SVG
# rasteriser that takes an output width does the same job.
cairosvg out.svg -o mine.png --output-width <panel_px>    # same px/mm
# crop the identical millimetre range from both and view them side by side
```

Rendering to the reference's scale is what makes the comparison work: the same
feature lands in the same place in both images. When something looks off, crop
that feature alone at four or five times from both and confirm before claiming
it. This is how the AGR400's RJ45s were caught: four of six jacks were upside
down, because a stacked ganged jack mirrors its rows and the component draws one
orientation. Nothing in the manifest was wrong and nothing would ever have
linted.

Do this for every face the vendor photographed, not just the front. The rear is
where the fans, the inlets, the ground stud and the airflow tags live. If a
face has no reference image, say so in the pull request rather than letting a
short list read as a clean result.

### A rule you applied to part of a face must reach the end of it

The commonest defect that survives lint is a right feature that stops early: a
numbering scheme printed under fifty ports and not the last four, per-port lamps
carried across one block and not the next. It happens because the rule is
derived where the evidence is strongest and the tail of the face is a different
block, finished later. For each rule you applied, find the last element it
covers and check what comes after it. If the rule stops, the file must say
which is true: the rule really stops there (say so, in provenance or a gap), or
it was not carried to the end (carry it). Do not assume the answer is "carry
it"; real faceplates stop rules all the time, and printing ink that is not on
the device is the one thing silkscreen must never do.

### A negative reading off a coarse image needs a control in the same image

At low resolution, "this area carries no printing" and "this image cannot
resolve the printing here" produce an identical pixel field. Find something in
the same image, at the same scale and contrast, whose printing you know is
there, and check that it survives. If it resolves and the questioned area is
uniform, the silence is a reading. If it has also dissolved, you have learned
the image's limit and nothing about the device. If no control exists in any
image you hold, the honest output is a gap saying the area is unresolved.

### Against a second party, for completeness only

If the device is in NetBox Labs NDX (`netboxlabs.com/ndx/<vendor>/<model>/`),
walk their field list and account for anything they have that you do not. It is
a free second reading of the same public datasheet. Use it for completeness,
never correctness: almost no failure here has been a wrong number; they have
been categories nobody looked for. A disagreement sends you back to the vendor
document, not to their number, and finding that we have more than they do is
the normal outcome. Do not ingest their enrichment layer.

## The canonical shape

Key order is fixed and linted (L16). A view reads top to bottom in the order the
part is made.

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
  <key>:
    confidence: <one of the eight words>   # omit it rather than guess
    note: >-
      <where, precisely: which document, which table or figure, at what scale,
      and what you rejected on the way>
attrs:
  physical: {...}      # sections, not a flat bag; omit any with no data
  performance: {...}
  power: {...}
  thermal: {...}
  environmental: {...}
  platform: {...}
  features: {...}
  management: {...}
  compliance: {...}
  lifecycle: {eol: none-announced}
  other: {...}         # counted, not free
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
gaps: [...]               # what you could not find, and why
```

For a fixed-port device with long repeated rows, `layout.yaml` plus
`spec/tools/portrayal/expand.py` generates the placements from a pitch; two
Edgecore devices are built that way and the plan is for all of them to be
(#168).

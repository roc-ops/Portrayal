# Handoff — Casa C100G / C40G, and the explorer

Written before a context compaction, for whoever picks this up (probably me).
Everything described is committed and deployed. Start by reading
`docs/casa-modular-chassis.md` — it holds the facts; this holds the state and the
traps.

Demo: `http://10.22.32.248:9003/demo/explore.html` — `./deploy.sh rocnet@10.22.32.248`
from the repo root builds and ships. Lint: `python3 ndv-spec/tools/ndv/lint.py
--schemas ndv-spec/schemas --library ndv-library` (clean at 99 files as of writing).
`./build.sh` runs lint first, so a broken manifest fails the build rather than
silently shipping a partial `dist`.

---

## Where it stands

| | |
|---|---|
| **C100G** | front 14/14, rear 14/14, 2 configurations, plus 3 fan bays and 2 PEM bays |
| **C40G** | front 6/6, rear 6/6, 2 configurations, cards rotated 90. **No PEM or fan bays** |
| **components** | 12 under `components/casa/` — 7 cards, `fan`, `pem`, and the furniture: `cable-manager`, `ground-strap`, `ground-bolts` |
| **explorer** | `demo/explore.html` — drawing left, live hierarchy right, slot inspector |

### The seven cards

`bdm` (BDM/BDM2/BDM2m as three skins) · `io-6p12` · `io-6p12-sw` · `smm-8x10g` ·
`lc-sw-bdm` · `smm-sw-bdm-a` · `smm-sw-bdm-b` · `fan` · `pem`

Chassis furniture, placed with `placements` rather than `bays`: `cable-manager` ×2 and
`ground-strap` on the front, `ground-strap` and `ground-bolts` on the rear.

Each carries `attrs.model` — the human name, which the explorer uses for tree rows.
Nothing else in the contract had one: `name` is a slug, `description` is a paragraph.

---

## The next thing to do

**PEM and fans are done** — `casa/fan` and `casa/pem` exist and the C100G rear carries
them as real bays (`fan-l`/`fan-c`/`fan-r`, `pem-b`/`pem-a`) instead of decor. **Size**
comes from Jason's hand-built SVGs, **layout** from Figures 1-4 and 1-6 of the guide.
Keep those two roles separate; mixing them is what went wrong the first time.

Next, in order:

1. **`SMM 300G`** as a second supervisor variant — his front carries it, with `XG0`–`XG9`
   plus `CG0`/`CG1`, matching the guide's Fig 1-9 "ten 10GigE, two 100GigE".
2. **C40G PEM and fans.** Deliberately not done. His hand-built SVGs are **C100G only**,
   and the C40G is 6RU with horizontal cards, so its power and cooling layout does not
   follow from anything measured. Guessing it would have been worse than leaving the
   existing decor in place. Needs a C40G rear figure or photograph.
3. Then internal structure — `backingPlate`, `insideFrame1/2`, `plasticCover`.

His SVGs are Inkscape-style with per-card groups (`c132`–`c145` front, `c312`–`c325`
back) and `slot0`–`slot13` on both faces, so the geometry is addressable by id. To measure
one: serve the file and read `getBBox()` composed through `getScreenCTM()`, or walk the
tree in Python composing `transform` attributes — but see the trap below about the latter.

## Also queued

- **Cable combs, properly.** Deliberately removed. When they return it is with their
  labels and with slots cut to expose the MCX jacks and standoffs — a real drawing job,
  not the strip that was there.
- **Airflow direction is contested.** Figure 1-5 says front-bottom in / rear-top out;
  Jason said the reverse. `c100g/device.yaml` still carries his version. One look at a
  running chassis settles it. The filter's position argues for the guide.
- **PEM and fan depth.** Both are `estimated` in the contracts. Nothing in the guide or
  the SVGs gives a depth, and it only matters to the relief/3D path.
- **A lint rule for element-vs-skin agreement.** See below; this is the most valuable
  rule left.

---

## Traps, all of them paid for this session

**The chassis is not the rack face.** Table A-1's 19 in / 482 includes the mounting
ears, which sit *outside* the body. Body is **432.95**, cards span 3.175 to 429.75 at a
**30.47** pitch with a 1/8 in flange each side. Ears are deliberately not drawn.

**The guide figures are schematic.** Using one scale factor, two figures disagree by
12 %. Taking each axis as a *proportion of the real chassis dimension* undoes the
drawing's aspect error. Card is **345.5 tall**, and the isolated card figures draw it
~17 % narrower than reality, so their port positions are used as **fractions**, never as
absolute geometry.

**Rear slots mirror on the C100G, not on the C40G.** Rear N pairs with front N. Walking
round a chassis flips left-to-right, not top-to-bottom — so the C100G's vertical cards
mirror (`FL + (13-N)*pitch`) and the C40G's horizontal cards do not. Two chassis
behaving differently looks like a bug until you think about it.

**Bays rotate now.** They could not before, which made "one card, two orientations"
true on paper and unbuildable. `render.py` also offsets a rotated occupant by half the
difference of the bay's dimensions, because `instance_group` spins a component about its
**own centre**, not its origin.

**`getBBox()` is only safe when you own the frame.** It cost three separate bugs:
the relief filter reading local instead of world, the explorer halo landing several
slots away, and a verification that transformed one corner of a rotated box and
concluded the card was misplaced when it was not. Compose the CTM.

**A component's elements and its skin can drift apart.** The LEDs overlapped while lint
said the spacing was fine, because the *elements* were 4.07 apart with a 4.07 diameter
and the *drawing* was what collided. Successive rescalings had moved positions by one
factor and radii by another. **Nothing checks that a declared element sits where its
artwork is.** That rule would have caught the LEDs, the stray comb box, and probably
more. Write it.

**Composing transforms by hand is not the same as `getScreenCTM()`.** Walking his SVG in
Python and multiplying `transform` attributes resolved the *shape* geometry correctly but
put the text 20 units outside the group's own bounding box — some nesting the hand-rolled
matrix code did not account for. The browser CTM never disagreed with `getBBox()`. Where
both were available the browser won, and where only the Python walk was available (the
per-feature positions inside `pemA`) the result was treated as an **inventory**, not as
coordinates.

**Serving from `/tmp` breaks Python.** There is a stray `/tmp/bisect.py` on this machine
that shadows the stdlib module, so `python3 -m http.server` in `/tmp` dies importing
`random`. Serve from a subdirectory. Half an hour went into this.

**And an inventory is not a layout.** Reading the hand-built SVG told me the PEM had four
things labelled `Branch N`, so I drew four terminal blocks in a row. They are **circuit
breakers** — the terminals are the two recessed blocks below them, and the `Branch N`
labels belong to leader lines joining each terminal to its breaker. The guide says so in
words and Figure 1-6 draws it. The lesson is not "check the PDF" but *which* source
answers *which* question: the hand-built SVG is authoritative on **size and placement in
the chassis**, the guide figure on **what is on a faceplate and how it is arranged**. I
had the better source for layout in hand and did not open it.

**L0 only covered one code path.** The colon-in-scalar guard was added to `lint_device`
and not `lint_component`, so a component with the same fault crashed with a traceback
instead of reporting. Both are guarded now, and `main()` skips the remaining checks when
a file did not parse. A rule that covers one path is not a rule.

---

## How to read a figure

What worked, repeatedly: render the page at 400 dpi with `pdftocairo -png`, then detect
features **by colour** and cluster the blobs. Parsing the vector art directly is
fragile — `pdftocairo` renders text as glyph paths under nested transforms.

Palette in these guides: faceplate `#a7a9ac` (sometimes `167,169,172`), orange
`#f7931d`, ink `#231f20`, lit green `#39b54a`.

And check the frame. A rotated crop reads bottom-to-top; that reversed the entire SMM
port order on the first pass.

---

## What Jason has corrected, so do not re-introduce it

No tie rod down the card face. Latches are **vertical, pinned left**. Standoffs are
**hexagonal and centred**. MCX jacks are inset — dark bore, gold body, white insulator,
copper pin — not flat dots. Port labels are on **both** the card face and the comb.
Slots 5 and 8 never carry a plain 6+12 I/O: 5 takes `LC-BDM-SWITCH`, 8 takes
`6+12 SW-IO`. The `Power Supply Monitor` on the SMM-SW-BDM cards is an **RJ45**. The
fan opening at the front bottom is an **exhaust** — air enters at the rear and passes
through the cards.

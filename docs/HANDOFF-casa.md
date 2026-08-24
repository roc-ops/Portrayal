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
| **C100G** | front 14/14, rear 14/14, 2 configurations, full chassis furniture |
| **C40G** | front 6/6, rear 6/6, 2 configurations, cards rotated 90 |
| **components** | 7 cards under `components/casa/`, all shared between both chassis |
| **explorer** | `demo/explore.html` — drawing left, live hierarchy right, slot inspector |

### The seven cards

`bdm` (BDM/BDM2/BDM2m as three skins) · `io-6p12` · `io-6p12-sw` · `smm-8x10g` ·
`lc-sw-bdm` · `smm-sw-bdm-a` · `smm-sw-bdm-b`

Each carries `attrs.model` — the human name, which the explorer uses for tree rows.
Nothing else in the contract had one: `name` is a slug, `description` is a paragraph.

---

## The next thing to do

**Mine Jason's hand-built SVGs.** They are in `working/intake/casa/handbuilt/`
(`front.svg`, `back.svg`, gitignored). Drawn from the hardware, not from the guide,
and they contain named groups for everything we are still faking as `decor`:

| group | what |
|---|---|
| `pemA`, `pemB` | PEM faceplates, with `OK` / `HS` / `!` and `Branch 1`–`Branch 4` |
| `fanL`, `fanC`, `fanR` | three rear fan modules |
| `chassisManager1`, `chassisManager2` | two front chassis-manager cards — **not modelled at all** |
| `groundStrapLocation`, `groundingBolts` | grounding, both faces |
| `backingPlate`, `insideFrame1/2`, `backPlaneBackGround`, `plasticCover` | structure behind the cards |

Jason's suggested order, and it is the right one: **PEM and fans first** (biggest gap,
already drawn), then the chassis managers, then `SMM 300G` as a second supervisor
variant. Grounding and internal structure can trail.

His SVGs are Inkscape-style with per-card groups (`c132`–`c145` front, `c312`–`c325`
back) and `slot0`–`slot13` on both faces, so the geometry is addressable by id.

### Unresolved: the two drawings disagree on chassis aspect

His viewBox is **191.575 × 275.873** — aspect **0.694**. Ours is **432.95 × 571** —
aspect **0.758**. One is wrong. Ours derives from Table A-1's 482 less the ears Jason
confirmed; his anchor is unknown.

**Settle it with an overlay, not by argument.** Render both to a common scale and diff.
This session's repeated failure was judging by eye; do not add to it.

---

## Also queued

- **Cable combs, properly.** Deliberately removed. When they return it is with their
  labels and with slots cut to expose the MCX jacks and standoffs — a real drawing job,
  not the strip that was there.
- **PEM and fan photos** from Jason for both chassis, if they arrive. The hand-built
  SVGs may make them unnecessary.
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

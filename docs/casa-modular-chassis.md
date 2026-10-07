# Casa C100G / C40G — modular chassis model

Facts extracted from the vendor hardware installation guides (C100G rev 07/08/2022,
C40G rev 07/07/2022). The guides themselves are vendor material and are held
locally, not in this repo. Cited, not copied.

These are the first genuinely **modular** devices in the library, so the slot rules
below are also the first real test of whether the contract can express a chassis
whose valid configurations are constrained.

---

## Chassis

|  | C100G | C40G |
|---|---|---|
| slots | 0–13 (14 front + 14 rear) | 0–5 (6 front + 6 rear) |
| SMM | front 6, 7 | front 2, 3 |
| line cards | front 0–5, 8–13 | front 0–1, 4–5 |
| "sides" | 0–5 left, 8–13 right | 0–1 left, 4–5 right |

**Front and rear slots are associated 1:1** — *"if a specific slot in the front has a
DQM/DCU module installed, the associated slot in the rear must have a RFD/RFU
module."* They are not independent bays; they are two halves of one position.

---

## The slot map is a function of (chassis, card family, HA scheme)

This is the thing that makes it harder than a fixed table, and it is where my first
pass was wrong. Three variables move the redundancy slots:

### Classic DOCSIS (DQM/DCU + RFD/RFU)

Redundancy is **per side**, one protecting slot each:

| | C100G | C40G |
|---|---|---|
| protecting slots | front/rear **5 and 8** | front/rear **1 and 4** |
| rear occupant | LC Switch | LC Switch |
| SMM switch | rear 6, 7 | rear 2, 3 |

The guide states the rule plainly: *"The standby module must be installed on the same
side of the chassis as the primary module."* On the C40G, primary QAM in slot 0 is
protected by slot 1; primary UPS in slot 5 by slot 4. Redundancy is also limited to
**one failure at a time** — a second concurrent failover is refused.

### BDM family (BDM / BDM2 / BDM2m + 6+12 I/O)

Adding BDM **collapses redundancy to a single protecting slot**, and the far slot
becomes an ordinary active one:

| | C100G — "11+1" | C40G — "3+1" |
|---|---|---|
| protecting slot | **5** | **1** |
| freed to active | **8** | **4** |
| rear of protecting slot | LC-BDM-SWITCH | LC-BDM-SWITCH |
| rear of freed slot | **6+12 SW-IO / SW-IO2** | **6+12 SW-IO / SW-IO2** |
| SMM switch | SMM-SW-BDM-A rear 6, -B rear 7 | -A rear 2, -B rear 3 |

**Why it collapses:** the `6+12 SW IO` is a *combined switch + I/O card*. The far slot
no longer needs a separate LC Switch behind it, so it stops being a spare and starts
carrying traffic. One protecting slot then covers both sides — which breaks the
"same side" rule that governs the classic scheme.

C100G front 0–4 and 8–13 take BDM / BDM_204MHZ / BDM2m_204MHZ; slot 5 is the
redundant HA slot; slot 8 is explicitly *non-redundant* under 11+1.

### Remote PHY (CSC + OOB)

CSC 8x10G occupies front **0–5 and 8–13** on the C100G — up to twelve slots, 96 ports
— paired with the rear **OOB 2+8 I/O** (two NDF downstream, eight NDR upstream).
CSC 2x10G is explicitly **not** supported. Three sanctioned layouts:

- **Non-redundant option 1** — rear 5 takes a CSC, rear 6/7 unpopulated.
- **Non-redundant option 2** — front 5 and 8 unpopulated, rear 5 and 8 unpopulated,
  rear 6/7 either unpopulated or SMM Switch.
- **Redundant 10+1** — rear 5 and 8 LC Switch, rear 6/7 SMM Switch, and *one* of front
  5 or 8 deliberately left empty.

---

## Spectrum pairing, and why front↔rear is not just "type matches"

The BDM pairing is by **upstream spectrum**, not merely by family:

- `BDM` operates with `6+12 IO` only, 5–85 MHz
- `BDM_204MHZ` and `BDM2m_204MHZ` operate with `6+12 IO2` exclusively, 5–204 MHz

Mixing across a chassis is allowed, but the guide qualifies it twice: *"Limited to
spectrum range supported by the I/O in service"* and *"HA redundancy limitations."*
So a valid pairing depends on the card, its I/O partner, **and** whether that position
participates in redundancy.

---

## What the contract has to express

Nothing in the library does any of this yet:

Checked against the schema by building `devices/casa/c100g`, rather than assumed:

| need | verdict |
|---|---|
| empty as a real occupant | **already works** — a bay's `default` is `["string","null"]`, and null means open |
| slot map varying by configuration | **already works** — `configurations[].bays` overrides per-bay occupancy, and `configurations[].skins` picks the card variant |
| paired slots (front N ↔ rear N) | **not expressible** — bays are independent, with nothing to bind one to another |
| compatibility with a reason | **not expressible** — `accepts` is a flat ref list, so "wrong spectrum" cannot be said |

So two of my four supposed gaps were me not reading the schema. The two that remain
are the two that are genuinely about *relationships between* bays rather than the
contents of one.

A third limitation turned up that I had not anticipated: **`accepts` must be
non-empty**, so a slot whose occupant type is not modelled yet cannot be declared at
all. The C100G's SMM slots (front 6, 7) are therefore absent rather than shown empty,
which is the wrong picture for a chassis viewer — an undeclared slot and an open slot
look identical, and they mean different things.

## Orientation: the same card, rotated

**The C100G takes line cards vertically; the C40G takes the same cards horizontally.**
Confirmed against Fig 1-1 in each guide - the C40G front view shows cards stacked flat,
with their silkscreen labels rotated, which is exactly what a card designed vertical
looks like laid on its side.

| | C100G | C40G |
|---|---|---|
| card orientation | vertical | horizontal |
| slot order | 0 at left → 13 at right | **5 at top → 0 at bottom** |
| SMM position | 6, 7 (centre pair) | 2, 3 (centre pair) |
| pitch runs | across the 482 face | up the 265.9 height |

That C40G numbering is inverted relative to reading order - slot 0 is the **bottom**
card. Easy to get backwards in a manifest.

The arithmetic holds for one card serving both. Taking roughly 440 long by 31.4 pitch:
14 x 31.4 = 440 across the C100G face, and 6 x 31.4 = 188 of the C40G's 265.9 height,
leaving ~78 mm for the fan trays and cable management visible along the bottom of the
C40G front view.

**This is what `rotate` in a placement is for.** The line card is modelled once and
placed at rotate 0 in the C100G and rotate 90 in the C40G. Lint L13 is already
rotate-aware, so overlap checking survives it.

What does *not* transfer: PEM and fan modules differ between the chassis, so those get
their own components per chassis rather than the shared-body treatment.

## Dimensions, and how the figures get scaled

From Table A-1 in each guide:

| | C100G | C40G |
|---|---|---|
| height | 22.5 in / **571 mm** | 10.47 in / **265.90 mm** |
| width | 19 in / **482 mm** | 19 in / **482 mm** |
| depth | 15.25 in / **386 mm** | 15.25 in / **388.45 mm** |
| rack | 13 RU | 6 RU |
| slots | 14 | 6 |
| weight | 132 lb / 61.23 kg loaded | — |

13 RU nominal is 577.9 mm against a stated 571, and 6 RU is 266.7 against 265.9 - both
chassis sit just inside their RU envelope, as they should.

This is what makes the vector figures usable. They come out of `pdftocairo` in page
points with no intrinsic scale, but every figure contains something of known size -
the chassis outline, or a card whose height is set by the chassis - so each can be
calibrated rather than guessed. Record the calibration reference per figure in
provenance, the same way the QSFP views were.

---

## How the cards decompose

Per the maintainer, and this is what makes the set cheap to build:

- **The PCB and the rear/backplane connectors are common to every card.** One shared
  body component - board, backplane connector set, ejectors, side rails - serves all
  of them. Photographed as top / bottom / rear-edge.
- **Only the faceplate differs**, and every faceplate is already in the guides as
  vector art.

So an I/O card is `common body + faceplate skin`, and adding the next card is a skin,
not a new model. The rear-edge photograph shows the shared connector set: a large gold
multi-pin block, four white contact blocks, a centre bracket, and a fine-pitch
connector at the opposite end.

## From a C40G rear photograph

Things the line drawings do not show, and which the figures alone would never have
given us. Measurements are the maintainer's, from the hardware.

### Cable combs and standoffs

Every I/O card is fronted by a **cable comb** - a notched strip carrying the
`U0-U11` / `D0-D5` silkscreen. Per the maintainer the labels are on **both** the card face and
the comb, so the comb repeats them at the point where a cable actually lands rather
than replacing them.

| | |
|---|---|
| brass standoffs | ~**3/8 in / 9.5 mm** proud of the faceplate |
| comb thickness | ~**1/16 in / 1.6 mm** |
| fitted to | both plain and SW variants of the I/O card |

### The 6+12 SW I/O is not the same shape

The photo has plain 6+12 I/O in C40G slots 0 and 5 and the **6+12 SW I/O in slot 4**,
and they are visibly different:

- **slightly different overall dimensions** from the plain card
- a section carrying the RF ports that stands **~5/8 in / 15.9 mm proud** of the
  faceplate, ahead of the comb

Which is consistent with what the guide says functionally - the SW card is switch and
I/O combined, so it has more inside it. It should be its own component, not a skin.

### Confirmations

- C40G rear slots really do run **5 at the top to 0 at the bottom**, printed on the
  chassis, with **3 and 2 in red** as the SMM switch pair.
- `SMM-SW-BDM` A and B occupy **specific** slots on both chassis and are not
  interchangeable - the faceplate legend says so and the photo shows them fitted that
  way. A is C100G 6 / C40G 2, B is C100G 7 / C40G 3.
- The PEM area is at the bottom rear with **PEM 1 / PEM 2** silkscreen, twin IEC
  inlets with their own switches, and ground studs.

## The hand-built SVGs — what they add

Two hand-drawn chassis SVGs (front and back), held locally.
Independently built from the hardware, so where they agree with what I read off the
guide figures that is real corroboration, and where they have parts I do not, they are
the better source.

### Confirms, independently

`slot0`–`slot13` on both faces. `U0`–`U11` and `D0`–`D5` port naming. STATUS / ALARM /
ACTIVE. `LC-SW-BDM`. `6+12 SW IO` as its own card. And `SMM-SW-BDM` with **`C100G
Slot 6 / C40G Slot 2`** for A and **`Slot 7 / Slot 3`** for B — the same slot legend I
took off Fig 1-14, arrived at from the other direction.

### Parts we do not have

| named group | what it is |
|---|---|
| `pemA`, `pemB` | **PEM faceplates**, with `OK` / `HS` / `!` indicators and `Branch 1`–`Branch 4` |
| `fanL`, `fanC`, `fanR` | **three fan modules** on the rear |
| `groundStrapLocation`, `groundingBolts` | grounding points, both faces |
| `chassisManager1`, `chassisManager2` | **two chassis manager cards** on the front — not modelled at all |
| `cableCombs` | the combs, already drawn |
| `exhaust`, `filter`, `plasticCover`, `insideFrame1/2`, `backingPlate`, `backPlaneBackGround` | chassis structure behind the cards |
| `logo`, `modelLabel`, `moduleNamePlate` | branding furniture |

### A different SMM

His front carries **`SMM 300G`**, not the 8x10G I modelled — and its ports read
`XG0`–`XG9` plus `CG0` and `CG1`. That is exactly the guide's "ten 10GigE, two 100GigE"
for the 300G (Fig 1-9), so the CG pair is the 100G uplinks. Two real variants, both
worth having.

### Blank and EMPTY are drawn

He has explicit `Blank` and `EMPTY` cards. That is the same distinction the schema only
half expresses - an unpopulated slot versus a slot with a filler plate in it.

### Scale — settled, and the error is vertical

His viewBox is 191.575 x 275.873; his `chassisFrame` is 190.26 x 274.56, aspect **0.693**,
against our 432.95 x 571 at **0.758**. That looked like an open question. It is not.

Measure both against **the slot pitch**, which is the one thing the two drawings agree on
independently. His `slot13` sits at x 0.71 and `slot0` at x 176.63, so 13 pitches span
175.92 and his pitch is **13.532 units**. Ours is 30.47 mm. That gives a scale of
**2.2517 mm/unit** derived from geometry neither drawing guessed at.

Now apply it to a part and compare against mapping that same part as a *fraction* of each
frame:

| | via slot pitch | via frame fraction | agree? |
|---|---|---|---|
| `pemA` width | 204.5 | 206.6 | yes, 1 % |
| `fanL` width | 135.2 | 136.7 | yes, 1 % |
| `pemA` height | 99.2 | 91.6 | **no, 8.3 %** |
| `fanL` height | 98.7 | 91.2 | **no, 8.2 %** |

The disagreement is confined to one axis. And the pitch-derived heights do not fit: stack
his bands at 2.2517 mm/unit and fan 98.7 + card 345.5 + PEM 99.2 plus his gaps overruns
571 by about 5 mm, whereas the fractional heights land the PEM at 568.3 with 2.7 to spare.

So **his drawing is roughly 8 % stretched vertically** and our 432.95 x 571 stands. Both
drawings independently agree that the cards span ~99 % of the body width (his 98.9 %, ours
98.5 %) and sit between ~18 % and ~78 % of its height (his 18.2–77.6, ours 18.9–79.4).

Two further things fell out of the same measurement:

- His `slot0` is on the **right** and `slot13` on the **left** of the rear view. The rear
  mirroring is confirmed from a second source.
- His `pemA` is on the **right** and `pemB` on the **left**. Our rear decor had those two
  labels the wrong way round; fixed.

### PEM and fan geometry, as built

Mapped fractionally onto the 432.95 x 571 body and symmetrised about the centre line,
because the real parts are symmetric and his measured margins were not (6.8 vs 4.05 on the
PEMs, 6.5 vs 3.15 on the fans):

| part | size | at |
|---|---|---|
| `casa/fan` x3 | 137.25 x 91.2 | x 4.0 / 147.85 / 291.7, y 4.5 |
| `casa/pem` x2 | 207.0 x 91.6 | `pem-b` x 6.0, `pem-a` x 219.95, y 476.7 |

Depths are **estimated**, not measured — nothing in the guide or the SVGs gives them.

### The PEM face, from Figure 1-6

The hand-built SVG gives the PEM's **size**; Figure 1-6 of the guide, "C100G Power Entry
Module, terminal covers removed", gives its **layout**. Do not mix the two the other way
round — the figure's own aspect is 3.43 against the module's 2.26, the same schematic
distortion the isolated card figures have, so everything is taken as a percentage of the
figure's faceplate and stretched.

Top row is **four rocker circuit breakers**, not terminals. The guide says so plainly:
each PEM has terminals for four 30 A branches, each branch a -48 VDC cable and its return
behind a 30 A breaker, and the breakers protect the circuit rather than serve as power
switches. Measured centres 18.04 / 37.99 / 61.36 / 81.33 %, each 15.07 % wide and
24.2 % tall.

The **terminals** are the two dark recessed blocks below, at 6.99 % and 71.1 %, each
21.5 % wide and 61.9 % tall, holding four studs in 2 columns × 2 rows. The **top row is
-48/-60VDC and the bottom row is RTN**, labelled once per block in the central gap. Left
block carries Branch 4 (left column) and Branch 3; right block carries Branch 2 and
Branch 1 (right column). So branches run **4-3-2-1 left to right** across the whole face,
breakers included.

### The leader lines are not uniform

Each branch has a leader running from its terminal-cover screw up to the breaker that
protects it, and the two shapes differ:

| | route |
|---|---|
| **outer** (Branch 4, Branch 1) | leaves the breaker's **outer side edge** at 12.9 % height, runs outward to 3.41 % / 96.27 %, then straight down to the cover screw |
| **inner** (Branch 3, Branch 2) | drops from the breaker's **bottom centre**, then runs inward to the cover screw |

Every run is interrupted where its `Branch N` label sits, which is why the figure shows
short tick stubs either side of the inner labels. Cover screws are at 5.25 / 30.80 /
68.39 / 94.33 %, all at 60.3 % height.

Indicators sit in the central gap: a black hot-swap button at ~43.7 %, then blue / red /
green at 48.22 / 52.13 / 56.92 %, all at 72.1 % height, captioned HS / ⚠ / OK.

The lower rail is 12.2 % of the module height and carries two captive screws. The A / B
letter is *not* in the skin — the chassis supplies it as the bay label.

### The fan face, from Figure 1-4

Same rule, same source discipline. Figure 1-4's "Fan tray front view" is close to scale
(aspect 1.563 against the module's 1.505) but is still read as fractions.

The face is a **punched perforation grid**, 19 columns × 9 rows, each cell 4.15 % wide and
7.83 % tall on a 5.09 × 10.84 % pitch starting at 2.31 / 2.75 %. A black **pull handle**
runs across at 78–88 % height, and three cells in the bottom row are blanked where its
latches land. The **indicator panel** sits at 33.8–68.3 % of the width and 1.6–31.7 % of
the height, with the hot-swap button at 40.2 % and three indicators at 49.2 / 55.9 /
62.5 % — icons on top (HS, warning triangle, boxed OK), LEDs below. There is **no model
silkscreen** on the fan face.

Three modules, LEFT / CENTER / RIGHT, each holding two fans designated front (0) and
back (1). 100 W each, 300 W total.

The perforations are drawn **dark**. Figure 1-4 shows them white, which is line-art
convention — they are holes looking into the chassis.

### Where the guide figure and the hardware disagree on proportion

Figure 1-6 is right about *what* is on the PEM and *where*, and wrong about how tall
things are. Corrected against the hardware:

| | figure | drawn |
|---|---|---|
| breaker height | 24.2 % of the plate | **18.2 %** (a quarter off) |
| terminal block | 61.9 % tall, uneven split | **40.4 mm in two equal halves of 20.2** |

The block's top edge is unchanged; only its height and the split moved. Studs sit at the
centre of each half.

### Labels: the guide's convention does not survive the scale change

Figure 1-6 interrupts each leader line where its `Branch N` label sits. At the size a whole
chassis renders at, that reads as text slicing through the line, and the `-48/-60VDC`
captions ran onto the terminal blocks. So: **lines unbroken, labels moved clear** — outer
labels above their horizontal run, inner labels below theirs, and the polarity captions
centred in the clear lane between each block and the nearest leader vertical, sized to fit
that lane. Faithful to the figure's *content*, not to its typesetting.

## Chassis furniture — cable managers and grounding

These are `placements`, not `bays`: fixed components with real ids and data-paths, so they
appear in the explorer, but nothing goes in or out of them.

| part | face | at | size |
|---|---|---|---|
| `casa/cable-manager` ×2 | front | 13.2 / 348.4, y 539.7 | 71.4 × 10.8 |
| `casa/ground-strap` | front | 348.4, y 530.4 | 15.0 × 7.9 |
| `casa/ground-strap` | rear | 6.3, y 461.9 | 15.0 × 7.9 |
| `casa/ground-bolts` | rear | 393.2, y 460.2 | 27.6 × 11.3 |

The ground strap is on the **right of the front view and the left of the rear view** — the
same physical corner, seen from two sides. That is the same fact as the mirrored rear slot
order, and it arrived independently, which is a useful check that the mirroring is real.

`chassisManager1/2` in the hand-built front SVG are **plain grey rects with no internal
detail**, so only their outline is measured. The end screws on `casa/cable-manager` are the
minimum needed to read as a bracket and are marked as such in its provenance.

### Front bezel bands, corrected against the hardware

| band | was | now |
|---|---|---|
| card-guide strip | 58.0, h 15.6 | 58.0, **h 32.85** |
| slot-number bar | 73.6, h 34.5 | **90.85, h 17.25** |
| slot numbers | y 97.6, 11 pt | y 102.7, 9 pt |

The number bar's bottom edge stays on the card line at 108.1; only its top moved. The
card-guide strip grew to fill what it gave up. His `moduleNamePlate` measures 13.75 tall,
so the corrected 17.25 sits between his drawing and the original — worth tightening if it
still reads tall.

**Filter pull handles.** His `filter` group is a dark bar with two white handles either
side of the FILTER caption, at 32.8–38.4 % and 61.7–67.4 % of the bar's width. Drawn at
142.0 and 266.5, 24.5 × 10.3, symmetric about the centre line.

**The bezel swoop.** `casa/brand-swoop`, placed at 109.2, 8.2 and 258.3 × 40.5. A closed
lens outline, stroked, not filled. Its path was **sampled** — 160 points along
`getTotalLength()` through the browser CTM, decimated to 80 — rather than composed from
transforms by hand, which is the only reliable way to lift a curve out of that file. Its
tip reaches x 367.5, which is why `C100G` moved from 406.95 to 417.9; his `modelLabel`
starts at 374.5, so the original text was too far left and the swoop ran into it.

### Airflow — the guide and the maintainer disagree

Recorded, not decided.

**Figure 1-5** ("C100G chassis air flow cross section") draws Front on the left and Rear on
the right. Cyan arrows enter at the **front bottom**, pass up through the filter and across
the cards, turn red, and leave at the **top**. The body text agrees: *"the air flow as
system fans draw air from the front of the chassis to the rear."* That makes the rear fan
face an **outlet**.

**The maintainer** stated the opposite from the hardware — in at the rear, out at the front bottom,
and that the grille below the front filter is the fan exhaust. `c100g/device.yaml` still
records his version under `provenance.airflow`.

The guide has one physical argument on its side: the **filter sits on the front bottom
opening**, and filters go on intakes. Worth one look at the machine to settle.

## Faceplates, read off the vector figures

### BDM / BDM2 / BDM2m (front, Fig 1-14)

**No RF connectors.** The BDM family faceplate carries a model band at the top, two
groups of orange stripes, and three LEDs - **STATUS / ALARM / ACTIVE** - with an
ejector top and bottom. All RF lands on the rear I/O card. That is the whole point of
the architecture, and it means a front BDM in the drawing is a blank plate plus LEDs.

### SMM Switch BDM A / B (rear, Fig 1-14)

Each carries a **Power Supply Monitor** window and prints its own slot legend on the
faceplate:

| module | C100G | C40G |
|---|---|---|
| SMM-SW-BDM-A | slot 6 | slot 2 |
| SMM-SW-BDM-B | slot 7 | slot 3 |

This is now **verified from the figure**, not inferred by symmetry as it was on the
first pass. `LC-SW-BDM` is a blank faceplate.

### 6+12 IO / 6+12 IO2 (rear, Fig 1-15)

Ports are **U0–U11** (twelve upstream) and **D0–D5** (six downstream), in two
interleaved columns - which is literally where the "6+12" comes from.

**The module connector is MCX, not F.** The figure's cable note: *"Single quad-shielded
cable with MCX male snap-on plug; 75 ohm male F-connector on opposite end."* So the F
connector is at the far end of the cable, at the headend equipment - never on the
6+12 card itself. Also available as 3-metre colour-coded 4- and 6-cable bundles.

## Line cards are shared, the rest is not

Per the maintainer: the front and rear **line cards are common to both chassis**; PEM, fans and
the other cards are not. So line cards belong in `components/`, shared, while the
chassis-specific parts stay with their device.

---

## Source figures

Vector line art extracted with `pdftocairo -svg` (hundreds of paths per page, so it is
real geometry, not a scan). Held locally beside the guides.

| figure | C100G page | subject |
|---|---|---|
| 1-1 | 28 | front view — 14 slots, SMM pair centre |
| 1-2 | 29 | rear view |
| 1-6 | 35 | power entry module |
| 1-7 … 1-10 | 37, 38, 39, 41 | SMM variants (2x10GE, 8x10GigE, 300G, 300Gm) |
| 1-11 | 44 | DOCSIS downstream and upstream line cards |
| 1-12 | 46 | RF I/O upstream and downstream modules |
| 1-13 | 47 | SMM and LC switch modules |
| 1-14 | 49 | BDM module — SMM Switch BDM A, B, LC Switch BDM |
| 1-15, 1-16 | 50, 51 | Casa 6+12 I/O modules, 6+12 Switch I/O |
| 1-17 | 53 | PON16x10G |

C40G equivalents are at pages 26, 27, 28, 32, 35, 36, 38–42, 44, 46, 47, 49, 50 —
note it has four rear views (AC/DC × redundant/non-redundant) where the C100G has one.

Photographs of the C100G-BDM2M-RF front line card (top, bottom, back) and the I/O card
are held locally with the guides.

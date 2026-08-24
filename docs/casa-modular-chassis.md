# Casa C100G / C40G — modular chassis model

Facts extracted from the vendor hardware installation guides (C100G rev 07/08/2022,
C40G rev 07/07/2022). The guides themselves are vendor material and live in the
gitignored `working/intake/casa/`, not in this repo. Cited, not copied.

These are the first genuinely **modular** devices in the library, so the slot rules
below are also the first real test of whether the contract can express a chassis
whose valid configurations are constrained.

---

## Chassis

| | C100G | C40G |
|---|---|---|
| front slots | 0–13 | see note |
| rear slots | 0–13 | varies by AC/DC and redundancy |
| SMM slots | front 6, 7 | front (same pair) |

**Front and rear slots are associated 1:1.** The guide is explicit: *"Front and rear
slots 0 to 13 on each side of chassis are associated with each other. This means that
if a specific slot in the front has a DQM/DCU module installed, the associated slot in
the rear must have a RFD/RFU module."*

That association is the core constraint. A front slot and its rear partner are not
independent bays — they are two halves of one logical position.

---

## What goes where

| slot | front | rear |
|---|---|---|
| 0–5, 8–13 | DOCSIS line card — **DQM** (downstream) or **DCU** (upstream), any mix | RF I/O — **RFD** or **RFU**, matching the front card |
| 5, 8 | DOCSIS line card, redundant | **LC Switch** (optional) — enables DOCSIS N+1 |
| 6, 7 | **SMM** | **SMM Switch** (optional) — enables SMM redundancy |

**Minimum configuration**, per the guide: one SMM, a DQM/RFD pair, a DCU/RFU pair,
a fan tray, and a power entry module.

### The rear card is not always required

Rear slots may be unpopulated. In the Remote PHY non-redundant Option 2, front slots
5 and 8 and all of 6/7 rear sit empty. So "I/O card optional" is a real state, not an
omission — the model needs an explicit *empty* occupant, distinct from *unknown*.

### Remote PHY (CSC / OOB) combinations

Front **CSC** modules pair with rear **OOB I/O** modules, and the guide gives three
sanctioned layouts rather than a free choice:

- **Non-redundant, option 1** — front 0–5 and 8–13 CSC, rear 0–4 and 9–13 OOB I/O,
  rear 5 CSC, rear 8 OOB I/O, front 6/7 SMM, rear 6/7 unpopulated.
- **Non-redundant, option 2** — front 5 and 8 unpopulated, rear 5 and 8 unpopulated,
  rear 6/7 either unpopulated or SMM Switch.
- **Redundant 10+1** — rear 5 and 8 LC Switch, rear 6/7 SMM Switch, and *one* of the
  two front redundant slots (5 or 8) deliberately left empty.

That last one matters: a valid configuration can require a slot to be empty. Any
validation we write has to express "must be empty", not just "may be empty".

---

## Line cards are shared, the rest is not

Per Jason: the front and rear **line cards are common to both chassis**; PEM, fans and
the other cards are not. So line cards belong in `components/`, shared, while the
chassis-specific parts stay with their device.

---

## Source figures

Vector line art extracted with `pdftocairo -svg` (hundreds of paths per page, so it is
real geometry, not a scan). Staged at `working/intake/casa/svg/`.

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
are in `working/intake/casa/photos/`.

# Casa C100G / C40G — modular chassis model

Facts extracted from the vendor hardware installation guides (C100G rev 07/08/2022,
C40G rev 07/07/2022). The guides themselves are vendor material and live in the
gitignored `working/intake/casa/`, not in this repo. Cited, not copied.

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

1. **Paired slots** — front N and rear N as one logical position, not two bays.
2. **Empty as a real occupant** — distinct from unknown, and sometimes *required*
   (redundant 10+1 mandates one of front 5/8 be empty).
3. **A slot map that varies by configuration** — the same chassis has different
   redundancy slots depending on card family and HA scheme. A static per-slot
   `accepts` list cannot say this.
4. **Compatibility with a reason** — "these two cards pair" is not enough; the
   constraint is spectrum, and the error message should say so.

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

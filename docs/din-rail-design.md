# DIN rails: profiles as data, a length set where the rail is used, and the device side

Status: proposed 2026-10-19. Issue #736, with #972 in section 9. This note
changes nothing: no code, schema, library file or test. It proposes, and the
open questions in section 7 are for the maintainers to answer. Every count was
taken from `main` at commit `713499fab`, and every figure in section 3 carries
the drawing it came from. Where the sources do not settle a figure, the note
says so and lists it as open; it fills no gap with a guess.

Read with [cable-managers-design.md](cable-managers-design.md) (the lab schema
and its checks, the pattern for a mount type that is not a rack unit),
[rack-products-design.md](rack-products-design.md) section 7 (hosts, including
`kind: rail`), [rack-file-v4-design.md](rack-file-v4-design.md) section 7.2 (the
rack-file part of #972), [adjustable-positions-design.md](adjustable-positions-design.md)
(the FS rail panel's own motion) and [format-stability.md](format-stability.md).

## 1. The problem

Ten devices in the library say `chassis.mount: din-rail`, every one of them in
`library/devices/aurcore/` (AIS2001 to AIS4001P), and nothing in Portrayal can
mount one. The one lab on `main`, `library/labs/roadm-ring-demo/lab.yaml`, is a
rack elevation: its `rack` key holds two keys (`height-ru`, `rails-only`), its
nine placements are rack devices, and `lab.schema.json` allows no rail. A lab
placement of a `din-rail` device is accepted but is nowhere: the `ru` rule
applies to `rack` only (`spec/tools/portrayal/labs.py` line 179), and a
placement of any other mount claims no unit (lines 270 to 276). What rail data
there is sits in free-text attributes and one component: the profile as the
string `ts35x7.5` in four files (the clip contract, the rail contract, DINRAIL2U
and DINRAIL4U), the clip's `din-profiles: ts35x7.5 ts35x15` and
`rail-centre-y: 29.5`, and a rail 400 mm long that exists only as the component
`fs/din-rail-ts35-400@1`, placed by the two FS DINRAIL devices. No lint rule
reads any of it (nothing under `spec/tools/` or in the device and lab schemas
names a profile; the only DIN statement the tools make is the export sentence
`Mounts on a DIN rail (IEC 60715); not rack-mounted.`, `dcim_export.py` line
1768). Of the three parts #736 asks for, the clip is already built (#737, closed
2026-10-02, `common/din-clip-ts35@1`, placed by all ten devices) and the mount
type is built (#734, closed 2026-10-02). What is missing is the rail itself: its
profiles as data, its length where a lab uses it, the device's statement of
which profiles it takes, and a placement that checks the two against each other.

## 2. The proposal

Four pieces, in the order the issue gives and the build should follow.

1. **Profiles are data**, one entry per profile: cross-section, thickness,
   slot pattern, the finishes that exist. Four profiles: `ts35x7.5`,
   `ts35x15`, `ts15` and `g32`. The figures and their sources are section 3.
   Where the data lives is the first decision (section 4, options A to C).
2. **A lab declares its rails and sets their length**, as it declares a rack:

   ```yaml
   rails:
     - {id: r1, profile: ts35x7.5, length: 500, slotted: true}
   ```

   `length` is the finished length in millimetres. The slots are worked out
   from the length and the profile's pitch, section 3.3. Any length is valid:
   the sources sell stock in 1 m and 2 m and cut it to length (section 3.2).
3. **A device states the profiles it takes**, and the point on its rear face
   that sits on the rail's centreline:

   ```yaml
   chassis:
     mount: din-rail
     din: {profiles: [ts35x7.5, ts35x15], at: [x, y]}
   ```

   This differs from the issue, which writes `din: {profiles, clip}`. The clip
   is now a placed component with its own contract, so a `clip` key would
   state it twice. Lint ties the two together instead (section 5, rule c).
4. **A lab places a device on a rail** by `rail` and `along`:

   ```yaml
   devices:
     - {id: sw-1, ref: ais4001p, rail: r1, along: 40}
   ```

   The issue writes `on: {rail: r1, at: 120}`. `on` is already a string in
   `lab.schema.json`, the id of a host placement, and `labs.json` publishes it
   under that meaning; giving it a second type would change what a reader of
   that key gets. Two new keys leave it alone.

What a rail draws is the site's work, as the cable managers' rack drawing was
(cable-managers-design.md section 6, "As built on the site"): this repository
publishes the rail, its slots and where each device sits, and a consumer draws
the elevation (a device's front view, its rear face on the rail's crown) and the
3D extrusion. Rendering is not in the first build slice.

## 3. The profile figures

Three drawings from three makers, each cited by title and URL, are the only
sources; IEC 60715's text is paywalled and was not read. The figures are read
off the drawings and the makers' tables. No drawing is copied. Page numbers are
the PDF's own.

- **AD**: AutomationDirect, "Steel DIN Rail (One-Meter Length)" and "Steel DIN
  Rail (Pre-Cut Lengths)", DINnectors Accessories, pages tTBL-123 to tTBL-128
  (PDF pages 1 to 6). https://cdn.automationdirect.com/static/specs/dinrails.pdf
- **EN**: Entrelec (ABB), "Mounting rails: Symmetrical - DIN 3" (PDF pages 1 and
  2) and "Mounting rails: Asymmetrical - DIN 1, Symmetrical - DIN 2", with its
  rail tolerances (PDF page 3). The file has five pages; G32 and TS15 are on page
  3, where the issue says pages 3 and 4.
  https://files.kempstoncontrols.com/files/8de077c0866b2f99bd31d7823afc7e4b/TS32.pdf
- **ITC**: ITC Electrical Components, "DIN Rail & Accessories" (PDF pages 2 to 5
  are the rails; the file has 12 pages and the rest are accessories, not read).
  https://cdn-e.soneparcanada.io/PIM_Docs/Docs/STEP_ASSETS_PDF/13048389.pdf

### 3.1 The table

All lengths in millimetres. A dash is a figure no source gives. "Crown" is the
dimension a drawing labels between the two flanges of a hat.

| figure | `ts35x7.5` | `ts35x15` | `ts15` | `g32` |
|---|---|---|---|---|
| width | 35.0 (AD 1, EN 1, ITC 2) | 35.0 (AD 1, EN 2, ITC 3) | 15.0 (AD 1, EN 3, ITC 5) | 32.0 (EN 3, ITC 4) |
| depth | 7.5 (AD 1, EN 1, ITC 2) | 15.0 (AD 1, EN 2, ITC 3) | 5.5 (AD 1, EN 3, ITC 5 drawing; **ITC 5 text says 5**) | 15.0 (EN 3, ITC 4) |
| thickness | 1.0 (AD 1, EN 1, ITC 2) | 1.5 (AD 1, EN 2, ITC 3) | 1.0 (AD 1, EN 3, ITC 5) | 1.5 (EN 3, ITC 4) |
| crown | 27.0 (AD 1, ITC 2, EN 3 tolerance drawing; **EN 1 labels 25**) | **27.0 (AD 1, ITC 3) or 24 (EN 2, EN 3): open** | 10.5 (AD 1, ITC 5) | – |
| flange (hat) or lip (G) | 4.0 (AD 1) | 4.0 (AD 1) | – | **6 (EN 3) or 9 (ITC 4): open** |
| slot | 6.3 x 18.0 (AD 1 and 4, EN 1, ITC 2) | 6.3 x 18.0 (AD 1, EN 2, ITC 3) | 4.2 x 12.2 (AD 1, EN 3, ITC 5) | 6.3 x 18 (EN 3, ITC 4) |
| slot pitch | 25.0 (AD 1, EN 1, ITC 2) | 25.0 (AD 1, EN 2, ITC 3) | 20.0 (AD 1, EN 3, ITC 5) | 25.0 (EN 3, ITC 4) |
| first slot centre from the end | 12.5, derived (AD 4, section 3.3) | as `ts35x7.5`, not drawn | – | – |
| mass per metre, kg, plain / slotted | 0.35 / 0.315 (ITC 2) | 0.67 / 0.62 (ITC 3) | 0.21 / 0.20 (ITC 5) | 0.74 / 0.68 (ITC 4) |
| standard the makers name | EN 60715 (AD, ITC); EN 50022 / DIN 46277-3 (EN) | EN 60715 (AD); EN 50022 and DIN 46277/3 (ITC, EN) | **EN 50045 / DIN 46277-2 (EN 3, ITC 5); AD 1 lists EN 60715 for the whole page** | EN 50035 / DIN 46277-1 (EN 3, ITC 4) |
| unslotted stock exists | yes (AD 1 `DN-R35`, ITC 2 `TS35`, EN 1 `TS 35`) | yes (AD 1 `DN-R35H`, ITC 3 `TS35C`) | yes (ITC 5 `TS15`) | yes (ITC 4 `TS32`) |

What the table does not settle, and what the note does about it:

- **The 6.2 x 15 slot.** The issue says some makers use it. None of the three
  drawings shows it. The slots the three do show on a 35 mm rail are 6.3 x 18 on
  25 (all three makers), and, as other patterns of the same width, ITC's
  `TS35/F5` at 5.1 x 25 on a 36 pitch and its aluminium and PVC rails at 4.5 x 25
  on 50 (ITC 2). The note records 6.3 x 18 on 25, which three makers agree on, and
  leaves 6.2 x 15 out until the maker's drawing is cited (question Q7).
- **The crown of the 15 mm rail.** AD and ITC label 27.0; EN labels 24. They are
  not reconciled here: the table keeps both, and the profile entry would carry a
  figure only after one is chosen (Q6). The depth of a hat and its thickness are
  the figures a 3D extrusion needs first, and those agree.
- **The G32 section.** It is not a hat. Width, depth, thickness and a 16.5
  figure agree between EN and ITC (what the 16.5 spans no text says), but the
  lip is 6 in EN and 9 in ITC, and from text and a small drawing alone the note
  cannot tell whether they dimension the same feature. A G32 entry would hold its envelope (32 x 15 x 1.5)
  and its slot pattern, and no cross-section outline until that is settled (Q6).
  The issue says G32's slots are "per maker": here two makers state the same
  6.3 x 18 on 25.
- **A standard's status.** The issue calls EN 50035 "withdrawn". None of the three
  sources says so, so the note does not write it. EN and ITC name EN 50045 for the
  15 mm rail where the issue's table says IEC/EN 60715; AD's page lists EN 60715
  once for all its rails. The data would record the standard each source names,
  not a status (Q6).
- **Finish.** The issue's two finishes are supported: EN names a zinc bichromate
  plated rail (pictured gold) and a white passivated galvanised one (pictured
  silver) (EN 1); AD says "zinc-plated and chromated" as one plating (AD 1); ITC
  says electrolytic zinc, minimum coating 6 micrometres (ITC 2). No source gives a
  colour value, so none is recorded; the colour is the drawing's choice.
- **Not four, more.** The sources also sell aluminium, copper, plastic and
  stainless rails, a 10 mm high TS35, 35 x 15 at 2.2 mm thick (ITC 3), a 75 x 26
  rail (ITC 5) and raised rails. The issue asks for four profiles and no device
  needs another, so none of these is proposed.

### 3.2 Length

EN says rail is "supplied in lengths of 1 or 2 meters or in custom cut lengths"
and to "allow 3 mm for the rail cutting blade thickness" (EN 3). ITC: standard
supply length 2 m, some 1 m, and "all rails can be cut to length" (ITC 2). AD sells
1 m and a set of eighteen pre-cut steel TS35 x 7.5 lengths from 50 to 600
(AD 4). So any length is valid, and a lab's `length` is the finished length.

### 3.3 The slot rule, and how far it is sourced

AD's pre-cut table lists the slot count of each steel length: 50 has 2, 75 has 3,
100 has 4, up to 600 with 24, and 400 with 16 (AD 4). Every one of the eighteen is
the length divided by 25. Read on a zoomed copy of AD's drawing, the last slot's
end arc centres stand 6.7 from the cut end, and the slot is 18 long with 6.3
wide ends, so the arc centres are 11.7 apart: the slot's own centre is
6.7 + 5.85 = 12.55 from the end, which is half the 25 pitch to the drawing's
precision. That is the issue's "first slot half a pitch from the end", and it is
sourced for lengths that are a multiple of 25.

The rule the note proposes for every length: slot centres at 12.5, 37.5, ...
(half a pitch, then a pitch each), counted from the left end, and a slot is
present only if it lies whole inside the length. It gives AD's count for all
eighteen lengths. For a length that is not a multiple of 25 no source states
what the cut end looks like, and the rule above is the proposal, not a
sourced figure (Q5). Cut stock keeps its punch pattern from the stock's end and
is cut anywhere at the other, which is why the rule starts from one end and
does not centre the leftover; that is reasoning, not a source.

## 4. Options

### Where the profile data lives

**A. A new library kind, `kind: rail`, one file per profile** (the issue's
wording: `library/rails/...`). Own schema, own lock, an indexer, a dist file, and,
because `kind: rack` was decided to need it (decided 2026-10-09, on #935), an npm
package type and a package resolver in the kit. It matches how racks are
carried. Cost: all of that for four rows of numbers that have no drawing, no
version history of their own and no art; a lock that records what changed in a
drawing has nothing to record on a table of measurements. A new kind is the
heaviest one-way door in the format.

**B. One registry table, `spec/schemas/din-rails.yaml`, with a tool that writes
`din-rails.json` to the build's dist.** The pattern is the cable types file:
`spec/schemas/cable-types.yaml`, `spec/tools/portrayal/cable_types_index.py`,
the line in `build.sh` (lines 183 to 185) that runs it with no library walk,
`spec/tests/test_cable_types.py`, the tool's name in
`spec/tests/test_tools_layout.py` (line 83), and a section in this repository's
`docs/format-stability.md`. It has its own `format` and `version`, a `sources`
map every figure cites, and a build that stops on a table that fails its checks.
The kit already loads such a file (`loadCableTypes(dist)`, described in
format-stability.md), so #972's rack side can read it the same way. Cost: it is
one file, not one file per profile, and the lock does not track it (the table's
own `version` does: a new profile is a minor, a changed figure or id a major).

**C. No data: one component per rail and length**, as `fs/din-rail-ts35-400@1`
is today. Costs: a rail of any other length is a new component; the length cannot
be set in a lab, because a component field changes a text node and not a shape
(`component.schema.json`, `fields`: "a different shape is a different
component"); and no tool can check a device against a profile it does not know.
This is what the library does now.

**D. A profile id only**: the device states `din.profiles`, the lab names
`profile`, and lint compares two strings against a short list in code. Cheap,
and nothing about the rail's shape is data, so the 3D extrusion and the slots
have nowhere to read from.

### Where the device states the rail

**D1. The issue's `din: {profiles, clip: {face, at}}`.** The clip is stated twice:
once as a placed component, once here.

**D2. Derive everything from the clip.** The clip's contract already holds
`din-profiles` and `rail-centre-y: 29.5` in `attrs`, and on the AIS4001P the clip
is placed at `[19.9, 49.3]`, so the rail centreline is at 49.3 + 29.5 = 78.8 from
the top of the rear face, where the device's own note says "about 79". Cost: those
two values are free-text `attrs`, estimated from a render at that (the clip's
provenance says so), and no schema types them.

**D3. `chassis.din: {profiles, at}`, with lint holding `at` to the clip.** The
device states the profiles it takes, which is a fact about the device and the
datasheet's ("DIN rail (TS35)"), and the centreline point, which the lab needs.
Lint checks that the device places a component whose contract lists those
profiles and that `at` agrees with the clip's own centre within a tolerance.

### Where a device is placed on a rail

**P1. `on: {rail, at}`** (the issue). Changes the type of an existing key.

**P2. `rail: <id>` and `along: <mm>`** beside the existing keys. `along` is the
distance from the rail's left end to the device's left edge; one reference
point is needed for the overlap check and the width the device takes along the
rail is its `chassis.width` (the ports hang vertically, clip hook at the top,
so the rail runs along the face's width: 72.1 for the small housing, 83.8 for
the large, read from `ais2001` and `ais4001p`).

## 5. Lint

New rules, with codes assigned when they are built (no code is named here
because the next free number is the build's to read):

- **a.** A lab's `rails` ids are unique, `length` is a positive number, and
  `profile` is in the table; `slotted: true` only on a profile that has slots.
- **b.** A placement's `rail` names a rail of the lab, and the placement states no
  `ru`, `on`, `face`, `unit` or `side` (those are for rack devices and
  rack-face and rack-side parts).
- **c.** The placed device's `chassis.mount` is `din-rail`, its `din.profiles`
  includes the rail's profile, and its `din.at` agrees with the placed clip.
- **d.** The device lies within the rail: `along` is at least 0 and
  `along + width` is at most `length`.
- **e.** Two devices on one rail do not overlap along it.
- **f.** A `din-rail` device states `din` (a warning at first, so the ten
  existing devices do not fail before they are updated).

The existing rules L139, L141 and L142 are untouched: a placement with `rail`
claims no rack unit, as every non-rack mount already does.

## 6. What changes when it is built

Each change to a saved or published output, and whether it can be undone:

| change | one-way or two-way |
|---|---|
| `spec/schemas/din-rails.yaml`, a new table | two-way until a device or lab names an id; **a published profile id is addressing** after |
| `library/dist/din-rails.json`, a new build file | **one-way**: from the release that adds it, its shape is under `contract` (format-stability.md, "A new file in dist") |
| `device.schema.json`: optional `chassis.din` | additive; two-way until a device states it, **one-way after** (removing a published key is a break) |
| the ten AIS devices state `din`: each a minor in the device lock | **one-way** per device; their NetBox and Nautobot files (20, ten each) change the "Drawing version" line and may change the DIN sentence of `dcim_export.py` line 1768, regenerated by the exporter only |
| `lab.schema.json`: top-level `rails`, placement `rail` and `along` | additive; **one-way once `labs.json` carries them** |
| `labs.json`: each lab gains `rails` with its slot centres, each placement `rail`, `along` and a null `ru` | additive, `contract` is not raised, **one-way** as a published shape |
| new lint codes (section 5) | two-way until published in `lint-rules.json`; a code is never reissued |
| docs: a section in `format-stability.md`, a line in `lint-rules.md` | two-way |
| a DCIM file | **no change for a lab's rail**: neither export reads a lab (checked: `dcim_export.py` names no `labs.json`, `lab.yaml` or `labs_index`), and neither NetBox nor Nautobot has a rail |

The rack file does not change. A lab is not a rack file.

## 7. Open questions

Each is answerable in one line. The recommendation after each is the note's, not
a decision.

1. **Q1. Where do profiles live?** A new kind, a registry table, components, or an
   id only (section 4)? **Recommendation: B**, the registry table: it is the
   pattern for numbers with sources and no art, the kit can already load such a
   file, and it avoids a new kind and its packaging. It departs from the issue's
   "one file per profile".
2. **Q2. The id spelling.** `ts35x7.5` (in four files today) or `ts35-7.5` (the
   draft in rack-products-design.md section 7.1), with or without a namespace
   (the issue's `din/ts35x7.5`)? **Recommendation: `ts35x7.5` without a
   namespace**, since it is one table and the spelling is already in use;
   rack-products-design.md would take the same id when hosts are built.
3. **Q3. Device side.** D1, D2 or D3 (section 4)? **Recommendation: D3**, with
   `at` optional and lint comparing it to the clip when both are stated.
4. **Q4. Placement keys.** `rail` and `along` beside `on`, or `on: {rail, at}`?
   **Recommendation: `rail` and `along`**, because `on` already means a host
   placement. And is `along` the device's left edge? **Recommendation: yes**; it
   is also what `heldBy.x` of #972 must mean (rack-products-design.md 7.2 says
   "from the host's left" without naming the point), so one answer settles both.
5. **Q5. The cut end of a rail of any length.** Whole slots only, from the left
   end (section 3.3), or something else? No source states it for a length that is
   not a multiple of 25. **Recommendation: whole slots only, from the left end**;
   note the rule in the profile entry as proposed and not sourced.
6. **Q6. The figures the sources disagree on.** TS35 x 15 crown (27 or 24), G32
   lip (6 or 9), TS15 depth (5.5 from three drawings, 5 in ITC's text), and the
   standard named for TS15. **Recommendation: record only agreed figures, and
   hold each disputed one as `unsourced` with both values in its note**, and
   obtain a drawing for each from one maker with a stated tolerance before the
   cross-section outline is drawn. No outline for G32 until the lip is settled.
7. **Q7. The 6.2 x 15 slot.** Which maker and which drawing? **Recommendation:
   leave it out and add it as a slot variant when a drawing is cited**; the issue
   does not give the source.
8. **Q8. Is a finish data?** Two names (zinc, zinc bichromate), no colour value,
   an optional lab key later. **Recommendation: record the two names with their
   sources and put no colour in the table**; defer a lab `finish` key to the
   drawing slice.
9. **Q9. A lab with a rail and no rack device.** Does it draw the default 42U
   frame? `lab.schema.json` says `height-ru` "omitted means 42". **Recommendation:
   no frame is drawn for a lab whose placements are all on rails and that states
   no `rack`; this is the site's call and is listed so it is not left silent.**
10. **Q10. Which profiles the first slice carries.** All four of the issue, or
    the two a device takes today (`ts35x7.5`, `ts35x15`)? **Recommendation: all
    four** for the figures that agree, so the table is complete at its first
    release and a profile is never added under a published id; G32 and TS15
    carry no outline.
11. **Q11. A shelf's DIN device in a DCIM: a child device or an unpositioned
    device?** (section 9.) **Recommendation: unpositioned, with a comment**, as
    rack-products-design.md section 7.4 has it.

## 8. The first build slice

Small enough for one task, and data only, as the issue's "order of work" starts:
the registry, its tool, its test, and no device, schema, lab or lint change.

Files:

- `spec/schemas/din-rails.yaml` (new): `format`, `version: 1.0.0`, `sources`
  (the three makers by title and URL), and `profiles` with the section 3.1
  figures that agree, each with a `sources` list.
- `spec/tools/portrayal/din_rails_index.py` (new): validates and writes
  `din-rails.json`; refuses a table where a figure has no source, an id repeats,
  or a pitch is not positive.
- `build.sh`: one line beside lines 183 to 185.
- `spec/tests/test_din_rails.py` (new): the checks of the tool, one failing table
  each, and a test that the slot rule of section 3.3 reproduces AD's eighteen
  counts.
- `spec/tests/test_tools_layout.py`: the tool's name in the list at line 83.
- `docs/format-stability.md`: a section for the file, as the cable types file has.
- a changelog fragment.

It moves no lock, since it changes nothing in `library/`. The slot rule belongs
in the tool so a consumer does not derive it again.

Later slices, each its own task: the device side (`chassis.din`, the rules c and
f, the ten devices); the lab (`rails`, `rail`, `along`, rules a, b, d, e,
`labs.json`); the drawing, which lives on the site.

## 9. #972: how the shelf's rail would use the same data

The rack-file part of #972 is already in rack file version 4, and needs no
version 5. [rack-file-v4-design.md](rack-file-v4-design.md) section 7.2 says so:
an item on a shelf's rail is `heldBy: {item, at, x}` (`rack.schema.json` line
298 describes it), `at` the id of a host of `kind: rail`, and the rail's depth
follows the shelf adjustment through `fields`, decided 2026-10-10 on #950. That
section lists what is not ready, and this note answers the first two in part:

- **A rail host declares its profile.** rack-products-design.md section 7.1
  already sketches `kind: rail` with `rail: ts35-7.5`, a `box` whose `w` is the
  length, and `set-back`. With this note the `rail` value is an id from the
  table of section 3 (spelling by Q2), the host's `box.w` is the rail's length,
  and the **usable span** is the part of it a device may occupy. DINRAIL2U and
  DINRAIL4U each state one 400 mm rail (`attrs.physical`, `din-rail-length-mm`).
  On the 2U the panel is 421.2 mm between the brackets, which leaves 10.6 mm
  each side of the rail (421.2 less 400, halved; the 4U's panel was not read).
  No document states a usable span: it is open, not derived from the rail's
  ends. Both devices also carry a recorded gap that FS does not name the profile
  and `ts35x7.5` is read off a render. A table cannot settle that: the profile stays unconfirmed until FS or
  a measurement states it.
- **A device states its profiles.** Section 2 piece 3 is that statement, in the
  form fit can compare. A device on a shelf rail and a device on a lab rail use
  the same `chassis.din`.
- **Position along it.** `heldBy.x` and a lab's `along` are one concept, a
  distance from the rail's left end, and Q4 settles the reference point for both.

**What upstream does.** Read at netbox-community/netbox commit
`4b034ea21986b014e5c56a59b9228ef926ae20e8`, `netbox/dcim/models/devices.py`
(NetBox `main` on 2026-10-19): a device type has `subdevice_role` (lines 124 to
133), a child device type must be 0U (lines 382 to 384), a child device
cannot be given a rack face or position, as those belong to the parent (lines
897 to 910), and a 0U device type cannot be given a position (lines 884 to 891).
Read at nautobot/nautobot commit `1efddad00a009ee1d8ecdbaad502909301df079b`,
`nautobot/dcim/models/devices.py` (`develop` on the same day): the same, with
`subdevice_role` at line 185, the 0U rule for a child at lines 371 and 372, the
0U position rule at lines 781 to 783 and the child's face and position rules at
lines 789 to 803. Neither file contains "din" or "rail". So a rail-mounted device
in both is, at most, a child device in a device bay of a parent, a discrete slot,
where a rail has a continuous position, and no field says on which rail or how
far along. rack-products-design.md section 7.4 says a hosted device is a device in
the rack with no position and no face, and a comment line saying what it is on;
that stands, and the upstream reading is why: a child device would need a bay
count the rail does not have. This was asked in #972 and not checked upstream
before (rack-file-v4-design.md section 7.2); it is now. The conclusion drawn
from it is a recommendation (Q11), not a statement about either DCIM.

The Rack Builder's part of #972 (dragging a device onto a rail, the Explorer
preview) and its DCIM export beyond the sentence above are not designed here.
The one question this section leaves is Q11 in section 7.

## 10. Checked against `main`

Every path, key, rule code and count in this note was read at `origin/main`
commit `713499fab` on 2026-10-19: the ten devices that state `mount: din-rail`,
the ten that place `common/din-clip-ts35@1`, the two that place
`fs/din-rail-ts35-400@1`, the one lab, `lab.schema.json`'s `on` as a string,
L125, L139 to L143, `labs.py` lines 179 and 270 to 276, `dcim_export.py` line
1768, `build.sh` lines 183 to 185, `test_tools_layout.py` line 83,
`rack.schema.json` line 298, rack-file-v4-design.md section 7.2, #950's and #972's
decisions of 2026-10-10 and #734, #737, #738 and #739 closed on 2026-10-02 to
2026-10-16.

## 11. Sources

- #736, #972, #734, #737, #738, #739, #935 and #950, https://github.com/roc-ops/Portrayal/issues/736 and the same path for each number.
- AutomationDirect, "Steel DIN Rail" and "Steel DIN Rail (Pre-Cut Lengths)", https://cdn.automationdirect.com/static/specs/dinrails.pdf
- Entrelec (ABB), "Mounting rails: Symmetrical - DIN 3" and "Asymmetrical - DIN 1", https://files.kempstoncontrols.com/files/8de077c0866b2f99bd31d7823afc7e4b/TS32.pdf
- ITC Electrical Components, "DIN Rail & Accessories", https://cdn-e.soneparcanada.io/PIM_Docs/Docs/STEP_ASSETS_PDF/13048389.pdf
- NetBox, `netbox/dcim/models/devices.py` at `4b034ea21986b014e5c56a59b9228ef926ae20e8`, https://github.com/netbox-community/netbox/blob/4b034ea21986b014e5c56a59b9228ef926ae20e8/netbox/dcim/models/devices.py
- Nautobot, `nautobot/dcim/models/devices.py` at `1efddad00a009ee1d8ecdbaad502909301df079b`, https://github.com/nautobot/nautobot/blob/1efddad00a009ee1d8ecdbaad502909301df079b/nautobot/dcim/models/devices.py

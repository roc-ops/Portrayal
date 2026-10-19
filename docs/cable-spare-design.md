# Cable spare: drawing it, and placing it

Status: a proposal, 2026-10-19. It decides nothing and builds nothing. It
measures, lists options for each of the six points #1011 names, and recommends.
Every count was taken from `main` at `713499fab` (2026-10-18). Where the sources
do not settle a question, it is listed as open (section 6).

## 1. The problem

Rack file version 4 (kit 0.22.0, built in #1018) records where a cable's spare
is stored (`slack`), measures it (`spareOf`: need, stock, spare, end play, to
store) and lists it (`spare` and `stored` in the schedule). It draws a tag at the
place and nothing else. Decision 4 of
[rack-file-v4-design.md](rack-file-v4-design.md) left the drawing, and the
choice of a place, to a later kit release, because the coil geometry worked in
that note did not fit the one tray that holds slack. On `main` that is still
the position, and the library has not moved:

- **One part holds slack.** One component states a cable tray
  (`fs/fhd-cmp5dr-tray`), and one device uses it (`fs/fhd-cmp5dr`). It states
  `slack: {kind: area}`. No library file states `slack: {kind: spool}`,
  although the component schema accepts one and the build reads it
  (`spec/schemas/component.schema.json`, `spec/tools/portrayal/rack_solids.py`).
  The FHD-1UFMT-N notes two slack spools inside its tray and does not draw them
  (`library/devices/fs/fhd-1ufmt-n/device.yaml`, `provenance.interior`).
- **Twenty-nine devices carry a `cable-capacity`**, all FS managers (some of
  them an estimate, marked as one). It is a count of one kind of cable, not a
  storage room: [cable-managers-design.md](cable-managers-design.md) section 15
  shows FS's vertical counts imply a sixth of the section of one cable.
- **On the reference rack of #949** (the fixture of
  `spec/tests/js/route-direct-fixture.mjs`: sixteen OM4 cords, one lacer) the
  cords have 4.96 m to store in all; twelve of them have more than 0.3 m
  (`UNPLACED_WARN_M`) and so give `spare-unplaced`, the count
  `spec/tests/js/rack-slack.mjs` asserts. Sixteen of sixteen cords rest in a ring
  of the lacer's tray. **Three of sixteen have the tray among the places their
  spare may go** (`sparePlaces`): the automatic route threads a ring, and for
  the other thirteen it rests on no tray.
- **The lacer takes twelve turns**, 1.89 to 3.12 m, against 31.6 turns these
  sixteen cords ask at the smallest legal turn (section 3.2).

Six things stand between that and a drawn spare: geometry on a real part,
capacity, a coil larger than a cell, a part that can hold a rack's spare,
placement that does not depend on the order cables are written in, and what a
rack saved before sees.

## 2. The proposal

Take the six points in the order of section 3 and do the following. Each is a
recommendation, not a decision.

1. **Draw the coil with legs, and count the legs as spare.** The path, the need
   and the stock size are not touched. `routePath` keeps returning the same
   points with and without a `slack` entry, as `spec/tests/js/rack-slack.mjs`
   already asserts. The coil and its legs are separate output.
2. **Measure the cells from the part, and warn rather than refuse past a bound.**
   A cell is the floor between two rings. It holds a turn only where the turn
   fits at the cable's bend radius. How high turns may stack is not in any
   source and has to be measured on a lacer; until it is, the bound is the fill
   rule decided 2026-10-09 and marked as an estimate.
3. **One coil, in the nearest cell with room, as tall as it must be.** Split
   across cells only if that is wanted (question 4).
4. **Library data before kit:** the slack spools of the FHD enclosures, from
   their datasheets, and a storage figure for vertical managers only if a source
   states one. Neither is in the first slice.
5. **Place by the cord alone:** the tray under the ring the cord threads, the
   cell nearest that ring, a stack position ranked by cable id. Nothing is
   saved; `"slack": []` still means none.
6. **Saved racks keep their lengths.** With legs counted as spare, nothing in a
   saved rack moves. What changes is the picture and the text of `stored`.

No further rack file key is needed. Coil points and the stored detail are kit
output.

## 3. The six points, with options

### 3.1 Geometry on a real part

**What the kit gives on the FS FHD-CMP5DR** (read from the fixture's catalogue
copy of the part and `routePath`; figures in millimetres from the rail):

| | |
|---|---|
| floor (the strip) | 48.8 to 110, so 61.2 deep, 448.4 across |
| ring openings | 72.2 to 104.2, each band 6.8 along the run |
| lay line of a 3 mm cord | 73.7 (`alongTray`, `railSide`: the side of the openings nearer the rail, plus the cord's radius) |
| centre-line room beyond the line | 110 less 1.5, less 73.7: 34.8, so a radius of 17.4 |
| centre-line room behind it | 73.7 less 48.8, less 1.5: 23.4, so a radius of 11.7 |
| bend radius of an OM4 cord | 25 (`BEND` in `rack/resting.js`) |

No turn at 25 mm can touch the lay line from either side: the figure #1011
gives, 17.4 against 25, reproduces. The floor does hold a turn at 25 mm
elsewhere: its centre-line box is 58.2 deep against the 50 a turn needs, so the
centre of a turn may stand from 75.3 to 83.5. **In every such place the lay line
(73.7) is inside the turn's footprint.** A drawn coil and the cord through the
cell cross in plan. The kit's own mark for a stored loop on this tray is at
79.4 (`spareMarks`), inside that range.

Which media can turn on this floor at all (twice the bend radius plus the
diameter against 61.2, the test version 4 applies; defaults of `BEND` and
`DIAMETERS`, which a cable type can override):

| media | needs | on the 61.2 floor |
|---|---|---|
| os2, om3, om4, om5 | 53 | turns |
| dac | 51 | turns |
| cat6 | 54 | turns |
| aoc | 63 | does not |
| cat6a | 67.5 | does not |
| power | 92.3 | does not |

**Option A: a coil with legs, the legs counted as spare.** The cord keeps its
path. A leg leaves the lay line to the coil and a leg returns, and both are part
of what is stored. The coil's first turn stands one cord diameter above the
through cords, so a cord threading the cell passes under it (4.5 mm to the
centre for a 3 mm cord, against 1.5; derived, not a library figure). Costs: one
turn less of stack; legs and coil share the stored length, so a cord with little
to store may not be able to afford a turn (the smallest turn is 157.1 mm of cord
on the centre line). Breaks: nothing in a saved rack. `need`, `length` and the
stock size do not change.

**Option B: a coil with legs, the legs part of the path** (the reading of #1011).
The legs lengthen the path, so the need, and a stock size can rise. Costs: every
cord that stores has a longer path, and the length that is stored depends on a
stock size that depends on the legs. That is a loop; it is cut by deciding
placement on the figure with legs and at the stock the cord has (a cord whose
stored length after legs is under one turn is not placed, and has no legs). A
stock size then rises only for a cord with an explicit entry that cannot afford
its legs (section 3.6). Breaks: the lengths of such cords on saved racks
(section 4), and the test in `rack-slack.mjs` that the path is the same with and
without a `slack` entry.

**Option C: move the lay line to the edge of the floor** where a cell holds a
coil. A line at 50.3 leaves 58.2 of centre-line room beyond it, enough for a turn
of 25. Costs: the ring openings stand at 72.2 to 104.2, so the cord must jog
back to them at each ring; the jogs are legs, and every cord on the tray changes
path, not only those that store. Breaks: as B, for the whole tray.

**Option D: a turn tighter than the bend radius.** Rejected: it contradicts the
bend rule the kit already enforces (#973, `tight-bend`) and would be drawn as a
fault.

**Recommendation: A.** It is the physical answer (a cord with a coil is not
shorter than one without; the extra is spare), it keeps `need` and the stock size
where they are, and it needs no stock-size decision on saved racks.

### 3.2 Capacity

**Measured, by the kit's own functions on the reference rack of #949.** The
command (Node 20; the script is scratch and is not part of this change):

```
node lacer-capacity.mjs <checkout>
```

It loads `spec/tests/js/route-direct-fixture.mjs` and calls `traysOf`,
`routePath`, `spareOf`, `routedLength` and `pathLength` from `kit/rack/`, and
works the cells and turns out from the arithmetic given here. A second scratch
script, `places.mjs`, calls `sparePlaces`, `routePath` and `spareMarks` for the
places a cord's spare may go. Reading the output of the first:

| | |
|---|---|
| cells along the run (mm) | 15.0, 88.6, 103.6, 103.6, 88.6, 15.0 (six, between five bands of 6.8; they add to the 448.4 floor) |
| cells that take a turn of an OM4 cord | the four middle ones; the end cells (15.0) take none |
| shortest turn | a rounded rectangle 50 by 50 on the centre line: 157.1 mm of cord |
| longest turn a cell takes | 244.7 mm (88.6 cells), 274.7 mm (103.6 cells), centre-line box the cell less the cord by the floor less the cord |
| turns stacked at `FILL_LIMIT` | 3 (0.4 of the 29.5 mm opening, in 3 mm cord) |
| turns stacked to the full opening | 9 |
| capacity at three high | 12 turns: 1.89 m (shortest turn) to 3.12 m (longest) |
| capacity at nine high | 36 turns: 5.66 m to 9.35 m |
| what the sixteen cords ask | 4.96 m to store; 31.6 turns at the shortest turn; twelve cords of 352 to 486 mm |

This differs a little from the 2.2 to 3 m of the version-4 note (1.89 to 3.12
here); the turn shape is the difference, and both say the same thing: **at three
high one lacer takes 38 to 63 per cent of the 4.96 m sixteen cords ask**
(1.89 to 3.12 m; 12 of the 31.6 turns at the shortest turn), and the number
that decides it, how high turns may stack, is not in the sources. The three-high
figure is `FILL_LIMIT` times the ring opening, a rule made for the area a
cable fills in a ring, applied to turns on a floor. It is not a measurement of a
lacer. Nine high is the opening and has no better standing.

Scaling to 48 cords is arithmetic and not a measurement: three times the sixteen
cords, if they were alike, is 14.88 m.

**Option A: the bound is the fill rule (three high), a warning.** As decided
2026-10-09 (comment on #949, question 4): warn at `FILL_LIMIT`, draw the layers
as they fall, do not refuse because a tray is full; a loop that does not fit is
still refused. Costs: the number is unsourced, so the warning is an estimate and
says so (the pattern of `capacity.estimated`, cable-managers-design.md section
15). Breaks: nothing.

**Option B: measure a lacer.** Stack a real FHD-CMP5DR with 3 mm cord to the
point a technician would stop and state the height. Costs: someone with the part
in hand. It is the only way to the bound #1011 asks for ("measured on a lacer,
not invented"). The result would be a library fact: an optional `stack` figure
beside `slack: {kind: area}` in the tray contract. Breaks: a new optional
contract key (section 4).

**Option C: no bound.** Draw whatever is asked. Costs: the picture claims the
tray holds what it may not. The 31.6 turns of the reference rack over four cells
are eight high, 24 mm of 3 mm cord, under the nine the opening holds; so
whether this tray "holds" the rack is wholly the stack bound, and that is the
number in question 1.

**Recommendation: A now, B when a lacer can be measured, and the warning says
which it is.** The decision on the warning exists already; only the number is
open (question 1).

### 3.3 A coil larger than one cell, and a cell with less room

Two facts decide this. A cell between rings cannot be spanned: a ring band stands
6.8 mm wide and 29.5 tall across the floor. And the end cells (15.0) take no turn.

**Option A: one coil in one cell, stacked as tall as it must be.** The cell is
the nearest to the ring the cord threads that takes a turn. A cord that stores
3 m is about 19 turns of the shortest size, 57 mm tall, with the warning of 3.2.
Costs: tall stacks, drawn above the lip as already decided. Breaks: nothing.

**Option B: split across cells.** The coil is cut into one coil per cell, each
with legs. Costs: more legs, and a rule for how to cut (cells by position, equal
shares, or fill one to the bound and then the next) that has to be chosen.
Breaks: nothing saved.

**Option C: do not place what does not fit.** The remainder reads in `stored`
("0.9 m not placed: more than the tray's cells take") and in a finding. Costs:
the same under-reporting #1011 names for a normal rack, since 31.6 turns are
asked of 12.

**A turn is solved to the length.** A coil's turns are sized so that its drawn
length equals the stored length to the millimetre, between the shortest turn and
the longest the cell takes. A stored length under one shortest turn (157.1 mm),
after the legs, is not drawn; `stored` reads it as not placed, with the length.

**Recommendation: A, then C.** One coil, the nearest cell, as tall as it must
be; if the cord's stored length after legs is under one turn, say so in words.
Splitting (B) is not needed to be right, and costs a rule that has to be chosen
(question 4).

### 3.4 A part that can hold a rack's spare

Today `SPARE_HOLDS` (`rack/slack.js`) lists tray and duct. A tray holds twelve
turns; a duct is judged by a cross-section count that fibre does not meet (a
fibre cord is "not counted" against a Cat6 figure, `spareLoad`), so a duct
takes unbounded fibre spare.

**Option A: the slack spools of the FHD enclosures.** The component schema has
the key (`slack: {kind: spool, at, diameter}`). Nothing states one. What is
missing: the spool position and drum diameter, and the drum height or flange
(the schema has no height, so how much a spool holds in metres cannot be
computed). And a use the sources do not settle: the spools stand inside the
enclosure's drawer (cable-lay-design.md section 6), and routing inside an
enclosure from a cassette to a spool is drawn only where the drawer is open in
3D (section 9). Whether a patch cord at a front port is ever stored on one is
not stated in any text read here; the datasheets that would say were not opened.
Costs: a measurement task per enclosure (FHD-1UFCE, 2UFCE, 4UFCE, 1UFMT-N,
1UFMT-S), a device version bump and lock move for each, and a contract key for
the drum height. Breaks: library schema additions (section 4).

**Option B: a vertical manager that states storage room.** The managers state
only a cross-section count. A storage figure would be an estimate by the method
of cable-managers-design.md section 15 and could be reached by no loop (section
15: "FS's vertical counts are not a fill"). Costs: a new estimated key; its basis
is the 2745 count that section 15 shows is not a fill. Breaks: nothing until used.

**Option C: a duct holds spare as it does, with a length bound.** Add to
`spareLoad` a bound on the length of fibre stored in a duct by section. Costs:
a rule with no maker figure; the count compares only cables as thick as Cat6.

**Option D: leave spare at the ends** (`{end: a}`), which exists. It places
nothing and draws a tag.

**Recommendation: no new part in the first slice; library data first, in the
order A (after a source says what the spools take), then B only if a source
states a room.** The lacer cells stay the one drawn place until then.

### 3.5 Automatic placement, whatever the order of the cables

Decision 8 of the version-4 note kept the kit from placing spare on its own, and
kept `"slack": []` (said none) apart from no key (nothing said) so that a later
build could place the second and leave the first. Placement has to give the same
answer in whatever order `rack.cables` is written. Two facts shape it: the
automatic route threads a ring and does not name the tray (three of sixteen cords
have a tray place today), and cords compete for cells.

**Option A: none** (as version 4).

**Option B: first come, in the order of the list.** The obvious loop. Rejected:
the answer depends on the order.

**Option C: sorted greedy.** Cords in a fixed order (position along the tray,
then id) each take the nearest cell with room left. Costs: a new cord can move
others to another cell; the answer is order-free and not stable under an edit.

**Option D: the cell nearest the ring, stacked, ranked by id.** Per cord: the
tray is the one on its route or under the ring it rests in; the cell is the
nearest to that ring that takes a turn; cords in one cell stack in the order of
their ids. Capacity warns and does not refuse. Costs: tall stacks (section 3.2).
Nothing a cord does depends on another cord but its layer in the stack.

**What each option reads for the tray:** only trays on the route (three of
sixteen cords of the reference rack), or the tray under a ring the cord threads
(sixteen of sixteen). The second is the only one that places most cords of a rack
that was routed automatically.

**The test, for any option:** the same rack with `cables` shuffled many ways gives
the same coils, the same `stored` text and the same findings. A cord's own end
order (#986: 38 of 1,803 sample cables measure differently written end for end,
as the version-4 note's section 3.7 records) is not fixed here, and placement
inherits it.

**Recommendation: D, the tray under the ring, on for a cord with no `slack`
key.** Computed, not saved; `"slack": []` and an explicit entry are not
overridden. In `stored` it reads "placed automatically" so nobody takes it for
something they wrote.

### 3.6 Saved racks

What a reader of a rack saved before sees depends on section 3.1.

| rack | Option A (legs are spare) | Option B (legs are path) |
|---|---|---|
| the file | the same; no key is added | the same until a measure |
| a routed length | the same | rewritten at the next measure (`withRoutedLengths`) where the stock size rises; `need` rewritten for every cord with legs |
| an entered length | the same | never touched, but the spare falls by the legs; where it is under the need, `spare-short` ("c7 is 0.5 m and needs 0.62 m") |
| a cord with a tray entry | the coil is drawn where the tag was | the same, and its length may rise |
| a cord with no key | a coil is drawn, if placement is on (3.5); `stored` reads a place | the same, and a cord that stores may rise a size |
| `"slack": []` | nothing | nothing |
| the same file in a kit before this one | the tag, as now | the tag, as now |

Under Option B the cords at a stock break are the exposed ones. On the reference
rack a cord's margin before its stock size rises is its stored length plus the
10 mm break tolerance (`BREAK_TOL_M`): 10.0, 10.0, 10.2 and 18.6 mm for c3, c7,
c2 and c4 (the four 0.5 m cords), and 362 mm or more for the other twelve. A cord
is placed only if it can afford a turn at its stock, so those four are never
placed and never get legs, and no placed cord's stock moves. A cord an explicit
entry names is the exception: it gets legs whether it can afford them or not, and
moves a size.

**Recommendation: Option A, so the answer is that nothing a saved rack records
moves.** The change a reader sees is the picture, the `stored` text and a fall in
`spare-unplaced`.

## 4. What changes when it is built

Each item is marked one-way (a saved or published form others rely on) or
two-way (nothing depends on it once it is back out).

| change | where | |
|---|---|---|
| a coil and its legs as kit output (`spareCoils`, or a field of `spareMarks`); `routePath` `points` untouched | kit API | two-way until a page draws it; one-way once a published page or a script reads it |
| cells of a tray, with capacity, as kit output | kit API | two-way |
| the `stored` text of the schedule, the BOM spare line, `inspect` and `describe` for a placed cord (from "not placed" to a place) | export content, downloads | one-way: spreadsheets read the text |
| `spare-unplaced` falls; a new finding kind for a spare that does not fit (`spare-no-room`) | finding kinds | one-way for the new kind: readers match finding kinds |
| a stack bound in the tray contract (`slack: {kind: area, stack}`), if measured | library schema, optional key | one-way (schema label); the contract `format` stays 1 |
| the drum height of a spool, spool data on the FHD parts | library schema and the parts | one-way for the key; each part's version and lock move |
| a stored-room key for a vertical manager, if a source states one | library schema | one-way |
| the rack file | none | no key, no version; a kit before this one reads the file as now |
| Option B only: stock sizes and `need` of routed cords with legs | saved racks | one-way |
| digests of `speed-goldens.json` (`slack`, `slack-findings`, `spare-lines`, `spare-exports`, `schedule`, `bom`, `describe`, `inspect`) where placement is on | tests | two-way |
| drawing in the Rack Builder page (3D coil, 2D marked loop with the length) | portrayal-site | its own change; not in this repository |

## 5. The first build slice

Small enough for one task, with no change to any output:

**The cells and the coil geometry in the kit, tested on this note's numbers.**
No page, no export and no finding changes.

- `kit/rack/coil.js` (new): the cells of a tray (`traysOf` floors cut by its ring
  bands), what turn a cell takes for a cable (bend radius and diameter, as
  above), the capacity at a given stack, and a coil of a given stored length in a
  cell: turns solved to the length, the first turn one diameter up, legs from a
  given point on the lay line. Pure functions of data the kit already holds.
- `kit/rack/slack.js`: `spareCoils(rack, cable, ctx)` for a cable with an
  explicit tray entry only, beside `spareMarks`, which it leaves as it is.
- `kit/README.md`: the new function, as the 0.35.0 entry does `spareMarks`.
- `spec/tests/js/rack-coil.mjs` (new): the numbers of 3.1 and 3.2 on the
  reference rack (six cells; 15.0 takes none; 157.1, 244.7 and 274.7; twelve
  turns at three high; 17.4 against 25); that a coil's length, its legs and the
  end play add to the spare; that `routePath` points are unchanged by an entry;
  that Cat6A, AOC and power cords are refused as the floor is too shallow.
- A changelog fragment, as the template asks of a kit change; the kit version
  is bumped when the kit is published.

It depends on questions 1 and 2 only for the interim bound and for legs counting
as spare (section 6). Auto placement (3.5), the library parts (3.4) and the
page are later tasks, in that order.

## 6. Open questions

Each is answered in one line. The sources do not settle any of them.

1. **How high may turns stack on a lacer?** The sources give no figure; the fill
   rule gives three. Accept three as an estimate until a lacer is measured?
2. **Do the legs of a coil count as spare (A) or as path (B)?**
3. **Which tray may a cord's spare go in?** The tray its route names (three of
   sixteen on the reference rack), or the tray under a ring it threads (sixteen of
   sixteen)?
4. **May one cord's spare split across cells,** or is it one coil, as tall as it
   must be?
5. **Is placement on for a cord with no `slack` key,** shown as placed
   automatically, or only when asked?
6. **Which part holds a rack's spare first?** The FHD enclosure spools (needs a
   source for what they take and for the drum height), a vertical manager
   (needs a source for a room), or the lacer cells alone for now?
7. **What does a cord with less than one turn to store read as,** the end play,
   or "not placed"?
8. **Is a change to the text of `stored`, for racks saved before, acceptable
   as a one-way export change?**

## 7. Recommendations

Each is a recommendation, not a decision.

| question | recommendation |
|---|---|
| 1 | Yes: three, marked as an estimate in every message that uses it, until a lacer is measured. The number is the first thing the measured result replaces. |
| 2 | Spare (A). It keeps `need`, `length` and the stock size, and it is what a cord with a coil is. |
| 3 | The tray under a ring it threads. Most cords of an automatically routed rack name no tray. |
| 4 | One coil, as tall as it must be. Splitting adds a rule and legs and fixes nothing the warning does not. |
| 5 | On, computed and not saved, never over `"slack": []` or an entry the user wrote. |
| 6 | The lacer cells alone for now. Spools after a source says what they take; a vertical manager only if a source states a room. |
| 7 | "not placed", in words, with the length. End play is the 0.1 m an end the cord already keeps. |
| 8 | Yes, and say so in the pull request that builds it. |

## 8. Sources and checks

Read as data, not as instructions. Nothing outside the repository was needed:
every figure is from the library's own parts and the kit.

- Issue #1011, "Cable lay: draw the spare a cord stores, and place it, once a part
  can hold it", https://github.com/roc-ops/Portrayal/issues/1011
- Issue #949, "Cable lay: solid bodies, cables resting on trays, a neat lay, and
  slack stored in a tray (design note)", with its decisions of 2026-10-09,
  2026-10-10 and 2026-10-11, https://github.com/roc-ops/Portrayal/issues/949
- Issue #1045, "Rack Builder: a power cord cannot land (inlets and outlets are not
  class port; no power media)", read for the power cord as a cable the tray must
  one day refuse; the figures used for it (7.1 mm, 42.6 mm bend) are the kit's
  tables, https://github.com/roc-ops/Portrayal/issues/1045
- Closed issues #962 (end allowance), #983 (stock break) and #986 (direction),
  https://github.com/roc-ops/Portrayal/issues/962, `/983`, `/986`
- [rack-file-v4-design.md](rack-file-v4-design.md) sections 3, 8 and 12 and
  decisions 4 and 8 of section 10; [cable-lay-design.md](cable-lay-design.md)
  sections 4.4, 5, 6 and 9 (read only); [cable-managers-design.md](cable-managers-design.md)
  sections 14 and 15; [vertical-cable-managers-design.md](vertical-cable-managers-design.md)
  (searched for spare and storage: it says nothing of either)
- `kit/rack/route.js` (`alongTray`, `railSide`, `STOCK_M`, `END_PLAY_M`,
  `BREAK_TOL_M`, `spareOf`, `withRoutedLengths`, `FILL_LIMIT`, `DIAMETERS`),
  `queries.js`, `slack.js`, `solids.js` (`traysOf`), `resting.js` (`BEND`);
  read only. `route-path.js` and `bundle-route.js` were searched for spare and
  slack and hold neither
- `library/components/fs/fhd-cmp5dr-tray/v1/contract.yaml`, whose provenance cites
  FS's 0U/1U Horizontal Cable Manager Datasheet (updated 2025-05-11); the
  repository records no URL for it. `library/devices/fs/fhd-1ufmt-n/device.yaml`,
  citing the FHD-1UFMT-N Fiber Enclosure Datasheet, page 4; no URL recorded.
- Tests: `spec/tests/js/rack-resting.mjs` (the strip, 48.8 to 110),
  `rack-slack.mjs` (twelve `spare-unplaced`; the unchanged points),
  `rack-spare-ducts.mjs`, `rack-speed.mjs` and `speed-goldens.json` (the digests
  that placement would move), `route-direct-fixture.mjs` (the reference rack).
  `rack-lay-findings.mjs` was searched for tray and spare and holds neither.

**Checked against `origin/main` at `713499fab`:** each file path, function, key
and constant named above exists there; the counts (one tray component, one device
using it, no `slack: spool`, twenty-nine devices stating `cable-capacity`, kit
0.51.0, twelve `spare-unplaced` on the reference rack) were taken there. The
capacity figures are the output of the command in 3.2 run on that commit; the
bend and diameter figures are the kit's defaults (`BEND`, `DIAMETERS`) and a
cable type may state others. The FS datasheets themselves were not opened: the
floor, ring and tie figures are the library's, which cites them.

# Cable lay: solid bodies, cables resting on trays, a neat lay, and slack in a tray

Status: decided 2026-10-09, nothing built. Issue #949. Each section gives a
recommendation and its reason; the five questions the note first left open
were decided as it recommended, and are listed in section 11; the one-way
doors are in section 12.

Builds on the rack core in `kit/rack/` (rack file `version` 3), on how a route
passes a ring ([cable-managers-design.md](cable-managers-design.md) section
13, #930), on cable bundles and their checks
([cable-bundles-design.md](cable-bundles-design.md), #921, #922 and #923), on
the cable types table (#919), on the hosts and the rack file version 4 of
[rack-products-design.md](rack-products-design.md) (sections 7 and 9), on the
`states` and `readings` held for version 4 by
[pdu-model-design.md](pdu-model-design.md) (#934), and on
[format-stability.md](format-stability.md). It is read with #939 (PDU
brackets) and portrayal-site#142 (bundles drawn, and the packing of members).

The goal: a routed cable never passes through metal, lies on whatever holds it
up, runs beside its neighbours without crossing them, and can leave its spare
length coiled in a tray, in 2D, in 3D and in the numbers.

## What exists

- **A route is waypoints.** `{item, via}` names a ring, a duct or a
  pass-through on a placed device; `{lane, ru}` a lane in the gutter beside a
  post at a U. `route.js routePath` joins the two ports through them, each ring
  expanded into the faces a cable enters and leaves by (#930). The routed
  length is that polyline plus 0.15 m at each end, rounded up to a stock
  length.
- **A waypoint is placed coarsely.** `pointOf` puts a guide at its `x`, at the
  middle of the bottom U of its item (the middle of the unit for a 1U part;
  low on a taller one), and, for a rack-face part, half its
  projection out from the rail plane. Nothing says where the opening is in
  height or in depth, so every cable through a ring passes the same point: its
  centre, not its bottom.
- **The drawings join the points.** In 2D `routed2d` draws straight runs with
  4 mm corners and an unrouted cable hangs by `sag2d`. In 3D `routePoints3d`
  runs taut through the points with 30 mm eased corners as a Catmull-Rom tube,
  and an unrouted one hangs by a catenary (`sag3d`, 20 mm plus 0.3 of the
  chord).
- **The only body check is a drawing patch.** `cable-geometry.js clearOf`
  pushes a 3D control point that falls inside a device box out along z. It
  tests the points and not the tube between them, and the boxes the Rack
  Builder hands it (`deviceBoxes` in the site 3D scene, `site/rack3d.js`,
  called from `site/rack/cables.js`) leave out every sheet-bodied part on
  purpose ("a sheet manager is open"). So a lacer such as the FHD-CMP5DR is never solid to it,
  the kit does no check at all, and nothing is reported.
- **Nothing is a surface.** The FHD-CMP5DR tray is a `well` component
  (`fs/fhd-cmp5dr-tray`, 448.4 x 110, its sheet 41 mm below the top of the
  44 mm envelope), and its sixteen slots, 22.5 x 3 and 3 x 23.3 mm, are decor
  on the bottom view. The router knows neither the floor nor that the slots
  take a tie and not a cable.
- **Lay order exists only for bundles.** A bundle keeps its members in combing
  order, packs them round (`BUNDLE_PACK` 0.8) and straps them; portrayal-site#142
  draws them. Single cables that share a ring are spread a few millimetres in
  3D and otherwise cross freely.
- **Slack is a number nobody places.** `inspect` of a cable reports `slack`:
  an entered length less the routed one. It is not stored, not drawn and not
  in an export.
- **The library declares pathways but not cable management.** Rings
  (`guide`), ducts and pass-throughs exist on the FS horizontal managers. The
  FHD enclosures carry slack spools, bend-radius brackets and, on the
  FHD-1UBE, a front lacer panel with five D-rings, and none of them is placed:
  rule 7 of [modelling-a-device.md](modelling-a-device.md) says cable
  management accessories are not drawn, and the FHD-1UBE provenance says the
  rings were noted, not placed.
- **The rack file keeps a cable whole but not a waypoint.** `readCables`
  keeps keys of a cable it does not know; `readRoute` rebuilds each waypoint
  as `{lane, ru}` or `{item, via}`, so an extra key on a waypoint is dropped.

The four faults #949 names follow from these: a run from a port below a lacer
to its ring goes straight up through the tray floor (no solid); every cable
floats at the middle of the unit (no surface); cables through one ring cross
(no lane); and slack has nowhere to go (no tray, and the FHD panel declares
nothing).

## 1. Solid bodies

**Recommendation: every body is solid to the router; a cable crosses one only
through a declared opening its diameter fits; otherwise the route goes around,
and what still crosses is a finding.**

### 1.1 What is solid

- **A box-shelled device** (every `mount: rack` device that is not a sheet) is
  its envelope, `w` by `h` by `d`, where it stands: the kit already knows all
  three and the item placement. **Except where the envelope holds cable
  space.** A device whose stated depth includes room cables run in (the
  FHD-1UBE: 227 mm overall, of which 107 mm is the front lacer zone ahead of
  the patch plate and 120 mm the rear lacer bar behind it) is solid as its
  compiled body, not its envelope: the patch plate (the plane its ports and
  module faces sit in), the modules behind it, and the plates and bars of its
  lacers. Its rings, trays and pass-throughs are then openings and floors
  inside the box, not inside a solid. A device is treated so when it declares
  any pathway or tray (sections 2 and 6) that lies inside its envelope; a
  plain box device with pathways only on its faces stays its envelope.
- **A sheet-bodied part** (`shell: sheet`: the rack-face lacers, the brush and
  finger managers) is its plates, not its envelope: the floor of each well
  (the sheet `thickness` thick), each part that stands proud of a face (the
  ears) and each web, as boxes. Its rings are not solid; they are openings
  (1.2).
- **A zero-U part that carries a lane** (a vertical duct, #926) is a pathway,
  not a solid: a lane waypoint at a U it spans runs through its channel, so
  only its walls and back are solid, derived as a sheet part is. A zero-U part
  that carries no lane (a PDU) is its envelope, as the fit check already takes
  it.

The plates are **derived, never stated.** `rack_index.py` writes them into
`rack.json` per device as `solids: [{part, box: {x, y, z, w, h, d}}]`, in the
frame the hosts of the rack products note use (x from the left of the device,
y up from its bottom, z back from its front), from the compiled faces it
already reads: a sheet well gives a floor plate, a proud placement a plate of
its own size, a duct its walls, and a device with cable space inside its
envelope its plate plane and the bodies of what is seated behind it. A plain
box device carries no `solids`: its envelope is enough. A second statement of
geometry the drawing already holds is a number that can disagree with it, the
reason the PDU note derived `mount-points`.

### 1.2 What a cable may pass

A cable crosses a solid only through:

- **a ring**, entering and leaving along its `run` (#930), inside its aperture;
- **a duct**, into its channel and out through a finger gap;
- **a pass-through**, along z, when the diameter of the cable (or of the
  bundle, at that point) is no larger than the smaller side of its `size`.

A pass-through is the one opening kind for a hole in a plate. A slot that is
big enough to take a cable is declared as one, with its size, and the check
holds the cable to it. **A tie slot is never an opening:** it is declared under
the tray (2.1) and nothing routes through it, whatever its size. The FHD-CMP5DR
slots are 3 mm wide, and a 3 mm fibre cord would otherwise pass the size test
on paper.

### 1.3 Going around

`routePath` adds **detour points** where a straight leg between two of its
points would cross a solid. They are computed, never stored, so the file does
not change, and they are part of the measured path, so the length counts them.
In order of preference:

1. **Over the near edge.** A cable that reaches a tray or a plate from the
   wrong side goes out past its front edge, clear by its own radius and
   `CLEAR` (5 mm, the figure `clearOf` uses), and comes back in from the open
   side. The FHD-CMP5DR case: a port on the switch below comes out, rises in
   front of the tray floor and drops onto it, as a lead is dressed by hand.
2. **Round the end.** A leg that would cross a body side to side goes past its
   end, into the gutter, which is where the automatic route already goes.
3. **Front to back by a side lane.** A cable whose ends are on opposite faces
   goes through the lane beside a post, as the automatic route does today.

A hand route keeps its waypoints; the detours are added between them in the
same way, and a leg the three rules cannot clear is left as drawn and reported.

### 1.4 The finding

`bodyFindings(rack, ctx)`, beside `ringFindings`, returns per cable each solid
its path still crosses: `{kind: 'crosses-body', cable, item, part, between:
[from, to], at: [x, y, z]}`, with a sentence: "c7 passes through mgr-1 tray
between its port and ring 2: route it over the front edge of the tray, or
through a ring." It **warns and never refuses**, as fill, size and bend do
(bundles decision 2): a device moving can make a route cross something without
any cable command. The finding appears in the cable list, in the export notes
and in the agent route output (section 8).

The check is on the kit path, which both drawings follow. The 3D tube rounds
its corners inside 30 mm of that path and may cut a corner; a browser check
samples the tube of every routed cable and fails on a point inside a solid,
so a corner that cuts metal is a drawing fault to fix, not a finding. For a
routed cable `clearOf` then has nothing to do, and a test holds it to that;
it stays for the unrouted hangs, which section 3 also brings to rest.

## 2. Trays: the library vocabulary

**Recommendation: a tray is a pathway with a floor. It is declared as `tray`
on a component contract and as `trays` on a device view, the way a ring is
`guide` on a contract and a duct is `guides` on a view; a route names it by its
id like any other pathway.**

### 2.1 The key

```yaml
# on fs/fhd-cmp5dr-tray (a contract), so every placement inherits it;
# the figures show the shape and are illustrative
tray:
  floor:                          # where a cable can lie, in the frame of the part
    - {at: [0.0, 48.8], size: [448.4, 61.2]}
  height: 3.0                     # mm, the top of the floor above the bottom of the envelope
  lip: 0                          # mm an edge stands up above the floor; 0, a plain edge
  run: x                          # the direction cables lie along it
  ties:                           # where a strap goes through; never a cable
    - {at: [54.85, 95.0], size: [22.5, 3.0]}
  slack: {kind: area}             # section 5; or {kind: spool, at, diameter}
```

- **`floor`** is one or more rectangles on the view the tray is placed on
  (the top view, for a tray seen from above), in that part frame. A tray of
  several strips (the FHD-CMP5DR strip and its two arms) lists each.
- **`height`** places the floor surface in the third axis, which the plan does
  not show. For the FHD-CMP5DR it is 3.0: its sheet top is 41 mm below the top
  of a 44 mm envelope.
- **`lip`** is how far an edge stands up. It bounds what a full tray holds
  (4.4). A tray with walls (a finger duct channel) states their height.
- **`run`** is the direction cables lie along it, as a ring states one.
- **`ties`** are the tie slots, in the same frame as `floor` (the part, on
  the view it is placed on), so each lies inside a floor rectangle. They are
  what hook-and-loop straps or cable ties pass through, so they are data for
  the straps of a cable lying there, never openings (1.2).
- **`slack`** says how the tray holds spare length (section 5).

A tray is compiled as an invisible `data-class="tray"` rect per floor, as
guides, pass-throughs and hosts are, and listed in `rack.json` beside `guides`
and `passes`, with its geometry under the new `trays` key in the same frame as
`solids`. Its `id` (the placement id; for the FHD-CMP5DR, `tray`) shares the
namespace of the guides of the device, so a waypoint `{item, via: 'tray'}`
names it and the route shape does not change. Lint holds every floor inside
its part, every tie inside a floor, a tray id unique among the pathways of its
device, and the `ties` in step with any slots the device draws on its bottom
view, as L137 holds a brush to its pass-through.

**Not a host.** The rack products note gives a shelf a `hosts:` surface, which
holds devices, carries a load rating and is named by a rack item `heldBy`. A
tray holds cables and is named by a waypoint. Reusing `hosts` would make fit
read a lacer as somewhere a switch could stand. The two share the frame of
reference only.

### 2.2 Rings gain what resting needs

A ring states its opening size today but not where the opening is. Two
optional keys join `guide`, whose schema is closed today, so both are minor
versions of the parts that state them:

- **`depth`**, mm along the run, which #930 reads and no part states (the kit
  estimates 10 mm, `RING_DEPTH`);
- **`sill`**, mm from the base the part stands on (its seat, or the face it is
  fixed to) to the lowest inside edge of the opening: where a cable through
  it comes to rest. With `aperture.at`, the corner of the opening in the part
  frame where the drawing shows it, the opening is placed in all three axes.

## 3. Resting

**Recommendation: a supported cable lies on its support, lifted by its own
radius; only a free span sags, and it never sags below a surface under it.**

- **Supports** are a tray floor, the sill of a ring, the floor of a duct
  channel, and any solid the cable would otherwise sag into. A port is not a
  support; it is an end.
- **On a support** the cable centre is at the surface plus its radius (half
  the type `od_mm`, or half the bundle size at that point), plus the layers
  below it (4.2). Along a tray the cable follows the floor at that height, so a
  route through a lacer drawn today at mid-unit drops to the floor line, 3 mm
  above the bottom of the unit, plus the radius.
- **A free span** is a stretch between two supports, or between a port and a
  support. It hangs as today (the catenary of `cable-geometry.js`, now in the
  kit path and not only in the 3D drawing), its depth scaled by the drape of
  the cable type, and no corner on it tighter than the installed bend radius.
  A span whose curve would pass below a surface between its ends is cut there:
  the cable lands on the surface and becomes supported.
- **Stiffness is derived, not stated.** The first build reads it from what
  #919 publishes: a kit constant, `DRAPE`, by family, 1 for fibre and AOC
  (limp: drapes onto a tray within a short span), 0.5 for twisted pair, 0.35
  for DAC and power cords (stiff: a wider curve, landing further along), and
  the installed bend radius as the floor on every corner. It is a kit table and
  not a library key, so it can be tuned without a door, and no per-type key is
  added (decision 2).
- **Unrouted cables** hang by the same rule, so the 3D sag no longer dips a
  cable into the device below; it rests on top of it.

**What 2D shows.** The front and rear elevations show resting as height: a
cable in a tray runs along the floor line of the tray, not across the middle
of its unit, and drops to it from the port. They cannot show depth, so where a
cable lies across the tray (its lane) is not seen there. No plan view is added
for this (decision 1); the 3D view shows it.

## 4. Lay order

**Recommendation: cables that share a tray, ring or duct get lanes, assigned
by port order so that none crosses another; flat in a tray, round in a
bundle; kept through the run; stacked when a layer is full, and a full tray
warns.**

### 4.1 The order

A cable reaches a tray from one of two sides, and the side decides its
lanes. The lanes are counted from 1 at the host side (the back of a tray, at
the rail).

- **Rail-side cables** come into the tray from the back: from the host behind
  it, or down from a device above whose ports are at the rail plane. They take
  the **inner** lanes, ordered by how far their port is from the exit they
  take: the one nearest the exit innermost, each one further away one lane
  further out. A cable then drops from its port into its lane without passing
  any cable already laid, because every rail-side cable already there comes
  from further along and lies further out.
- **Front-edge cables** come over the front edge (section 1.3, rule 1): from a
  device below the tray. They take the **outer** lanes, the other way round:
  the one nearest the exit outermost, each one further away one lane further
  in. A cable coming over the edge then lands in its lane without passing any
  front-edge cable already laid, since those come from further along and lie
  further in, and the rail-side group lies inside both.

Cables at the same distance from the exit (one port above another) are ordered
by U, the lower first, then by cable id.

**Traffic both ways.** Today the automatic route picks the gutter from the x
of end A alone, and when both ends leave through the same manager it goes out
to the gutter and back through the same rings (a patch from a switch port at
x -150 to a panel port at x -20 runs ring 1, left-front U12, U11, ring 1,
ring 2). **A patch whose two ends share one manager runs along the tray
directly, port to port, through the rings between them, with no gutter.** It
is a local patch, and it takes lanes only over its own stretch:

- a local patch with both ends on one side lies nearest that side (innermost
  for rail-side ends, outermost for front-edge ends), and of two such patches
  the shorter lies nearer, so patches that nest never meet;
- through cables (to a gutter) going opposite ways occupy separate stretches,
  since a port left of the centre line runs left of it and one right of it
  runs right, so they meet only local patches.

Some meetings no order avoids: a through cable whose port lies between the
ends of a local patch, a patch from one side to the other, and two patches
whose ends interleave. In plan these are a cable having to cross a cable that
lies between it and its lane. **Such a cable passes over, never through:** it
steps up a layer at the one point where it must and back down after, and the
kit counts these forced crossings per tray and names them, so a crossing is
always one the hardware forces and never one the order made.

### 4.2 Flat and round

- **Single cables lie flat**, side by side across the floor, each lane as wide
  as its cable. The layer is as wide as the narrowest opening on the shared
  stretch: through an FHD-CMP5DR ring that is the 32.0 mm across the opening,
  not the 61.2 mm of the strip.
- **A layer that is full starts the next** on top of it, in the same order.
  For the snap-in ring that is five 6 mm Cat6 cords a layer and four layers
  under its 29.5 mm, twenty cables, against the theoretical 30 the datasheet
  states for the panel: the figure the vendor gives assumes a pack tighter
  than square layers.
- **A bundle is one lane.** Its members pack round inside it, as the bundle
  model (#922) and the member packing of portrayal-site#142 already draw them,
  and the bundle takes a lane of its own diameter among the single cables, in
  the order of its first member.

### 4.3 Across a run

- A lane is **kept along the shared stretch**: it is assigned where the cable
  first shares a pathway and held through every pathway it shares with the
  same neighbours.
- **A cable joining** takes the lane its port order gives; the cables already
  there do not move, which is what the order of 4.1 guarantees.
- **A cable leaving** (at its own pathway, or at a bundle peel point) gives up
  its lane, and the lanes outside it close up only after the next support, so
  no cable is drawn sliding sideways inside a ring.
- **A turn keeps the order on the same side:** a flat run turning from a tray
  into a gutter keeps its outermost lane outermost, so it never twists over
  itself.
- **A hand lay** pins one cable to one lane in one pathway (`lay`, section
  7); the others are laid round it in order.

Lanes are computed, not stored, except a hand lay. The lane position is part
of `routePath`, so it moves the measured length by millimetres and agrees in
every view.

### 4.4 A full tray

A tray holds, at the fill share rings already use (`FILL_LIMIT`, 0.4), the
area of its narrowest opening on the stretch, or of its floor width by its
`lip` where no ring bounds it, and a tray with neither a lip nor a ring takes
its envelope height. Over that, or over the cable count the device states, it
**warns, and draws the layers as they fall**, above the lip if need be: as for
rings and bundles, a device moving can fill a tray without a cable command,
so it must be able to sit over the limit and say so. Storing slack into a
full tray warns the same way and is not refused (decision 4).

## 5. Slack storage

**Recommendation: a tray states how it holds slack; a cable stores spare
length in a named tray as a coil (or a serpentine, or on a spool); the stored
length counts in the routed length; the exports say where it is.**

### 5.1 What a tray holds

- `slack: {kind: area}` is the floor less the footprints of the rings on it.
  The kit works out what fits for a given cable: a loop needs the installed
  bend radius both ways, so its outside is twice the radius plus the
  diameter, across the floor and between two rings.
- `slack: {kind: spool, at, diameter}` is a spool the cable winds round: the
  FHD enclosures ship two. Its diameter must be at least twice the radius of
  the cable laid on it, which lint and the command both check.
- How much a tray holds in metres is not stated. It depends on the cable, so
  it is computed: the free volume (the slack area by the stack height) at
  `FILL_LIMIT` over the cable section. The stack height is the `lip`, or where
  a ring bounds the stretch, the height of its opening above its sill: 29.5 mm
  on the FHD-CMP5DR. Its slack area is the 448.4 x 61.2 strip less the five
  ring bands across it (5 x 6.8 x 61.2), about 25,360 square mm. That holds
  about 42 m of 3 mm fibre, or 10.6 m of 6 mm Cat6.
- **A loop that does not fit is refused.** Cat6A is 7.5 mm with a 30 mm
  installed radius, so its loop needs 67.5 mm, and the strip is 61.2 deep:
  `cable.slack` refuses with that sentence. The tray geometry is fixed, so this
  is a fit fact, as a device that does not fit a U is. A later change that
  makes a stored loop not fit (the type of the cable changed) keeps it and
  warns, as fit keeps an item it would no longer accept.

### 5.2 On the cable

```json
{"id": "c7", "...": "...",
 "slack": [{"item": "i4", "via": "tray", "value": 1.2, "unit": "m", "form": "coil"}]}
```

- `item` and `via` name the tray as a waypoint does; the tray must be on the
  route, and a route edit that takes it off keeps the entry and says so, as a
  waypoint that no longer resolves is kept and reported (`gone`).
- **`value` absent means the rest:** the spare length, an entered length less
  the path, all stored there. A cable with a routed length and no entered one
  has no rest, so it needs a value.
- `form` is `coil` (the default, decision 5: least floor along the run), `serpentine`
  (runs along the tray with U-turns at the bend radius, for a narrow floor
  between close rings) or `spool` (for a tray that states one).

### 5.3 The length

The stored length **adds to the routed length**: path plus stored slack plus
the end allowances, then the stock length. A cable with an entered length
stores its rest and the numbers balance (path plus stored equals entered); one
that stores more than its spare is a finding ("c7 stores 1.5 m in mgr-1 tray
but has 0.6 m to spare"). A routed cable that stores a value grows by it, and
may move up a stock size, which is the honest answer: that is the cable to buy.

### 5.4 Drawn

- **3D**: a coil is loops of the cable lying flat on the floor, concentric and
  stacked, each at least the bend radius; a serpentine is runs along the run
  joined by half-turns; a spool winds round its drum. The cable enters and
  leaves at its lane.
- **2D**: a marked loop, an ellipse in the colour of the cable at the tray,
  with the stored length in its tag ("1.2 m slack"), since an elevation sees a
  flat coil only edge on (decision 1).

### 5.5 Exports

- **Cable schedule**: a `slack` column **appended after the last column**
  ("1.2 m in mgr-1 tray"), so no column a reader takes by position moves.
  #923 moved three columns for `bundle`; this does not need to.
- **BOM**: the cable lines are unchanged in shape; the length bought already
  counts the slack, and a note per cable that stores some says where.
- **DCIM**: nothing new. The length both targets import is the stock length,
  which counts the slack.

## 6. Library data: the parts, and what to measure

Each part takes a minor version when it states a tray or the new ring keys.
Rule 7 of the modelling guide is narrowed with the first of them: **cable
management that is part of the product** (a lacer panel, its rings, a tray, a
slack spool, a bend-radius bracket) **is declared, and drawn where it is a
part**. Tie slots and tie anchors that are part of a plate are drawn, as the
plate they are cut in, and declared as `ties` (decision 3); loose ties,
straps and retainer bails added in the field stay undrawn. Without that, the FHD-1UBE rings stay noted and not placed, and a
route has nothing to lay slack in.

| part | what it needs | what to measure | sources |
|---|---|---|---|
| `fs/fhd-cmp5dr-tray` (FHD-CMP5DR) | `tray`: floor, height, ties, `slack: area` | the strip and the two arms as floor rectangles; the floor height (3.0, already read); whether the front edge turns up (the ring-profile view draws none, so `lip: 0`); the sixteen slots, already measured, moved into `ties` | the 0U/1U horizontal manager datasheet three-view (read for the part), seven renders including the underside, the horizontal managers quick start guide |
| `fs/d-ring-snap-in` | `depth`, `sill`, `aperture.at` | the band along the run (6.8 mm, drawn); the seat under the opening (2 mm, estimated today: wanted from the underside render or a ruler) | the same datasheet, the ring-profile view |
| the 1U D-ring panels: CMH-5DR1U, CMH-5DR1U-N, USCMH-5DR1U, CMH-4DRB1U, CMH-6DR1U | ring `depth`, `sill`, `aperture.at`; the plate is a solid, derived | each ring band along its run and the height of the lower leg of its opening in the face; the CMH-6DR1U end ring, which runs along y | the D-ring managers datasheet, the CMH-5DR1U quick start guide, the CMH-4DRB1U datasheet and dimensioned render, renders of each; CMH-6DR1U has renders only |
| the finger ducts: CMH-SFD1U and 2U, CMH-DFD1U, the SFDS and DFDS models, USCMH-SFDABS and SFDABSB, CMH-BS, CMH-HD and CMH-UHD | `trays` on the view, each channel a floor with walls as `lip`, `slack: area` | the channel floor height in the face, its depth front to back, the finger height, and the clearance under the cover | the finger duct datasheets (ABS and steel) and the high-capacity and single-sided manager datasheets; renders for most, none for the CMH-BS, HD and UHD lines |
| FHD-1UBE | its five front D-rings placed, a lacer floor, the rear lacer bar | ring positions along the panel (107 mm in front of the plate is read), the lacer floor, the bar | its datasheet and assembly illustration, the FHD cabling system guide |
| FHD-1UFCE, FHD-2UFCE, FHD-4UFCE | the drawer floor as a `trays` entry inside the body, two spools (`slack: spool`), the two bend-radius brackets as ring-like guides, the rear grommets as pass-throughs with sizes | spool positions and drum diameter, the bracket radius, the grommet sizes; the drawer floor height | the FHD-1UFCE datasheet and the slide-out family datasheet (the exploded illustration names two slack spools, two bend-radius brackets, two strain-relief brackets and four grommets), the enclosure quick start guide (24 pages), photographs of the drawer pulled out |
| FHD-1UFMT-N | the two slack spools (its datasheet front view shows them behind openings 1 and 4), the rear entries as pass-throughs | spool positions and diameter, the entry and grommet sizes, which the datasheet lists without dimensions | its datasheet and quick start guide, and a render with dimension callouts |
| FHD-1UFMT-S | the tray inside its sliding drawer, and whatever slack holder it has, which no held text names yet | the drawer floor and its rear entries; first, whether it carries spools | its datasheet and quick start guide, and a render with dimension callouts |
| FHD-1UME | its rear cable manager as a lacer with guides | the manager position and openings | its datasheet and quick start guide |
| the FHD adapter panels and cassettes | nothing new | none: they are solid faces whose ports are already the ends | none needed |

The vertical managers need nothing for this note: a cable in a vertical duct
runs along gravity, so nothing rests in it, and its lane is already a pathway
with an aperture (#926).

## 7. The rack file

Two cable keys, read and written by the kit:

| key | where | what |
|---|---|---|
| `slack` | cable | a list of `{item, via, value?, unit?, form?}` (section 5.2) |
| `lay` | cable | a list of `{item, via, lane}`: the hand lay in one pathway, its lane counted from 1 at the host side (sections 4.1 and 4.3) |

An older reader **keeps both** (a cable keeps keys `readCables` does not know)
**and misreads them**: its `withRoutedLengths` measures the path without the
stored slack, rewrites the routed length shorter, may drop a stock size and
saves that; and its route editor takes a tray off a route and leaves the slack
naming it. That is the case version 2 was raised for (a part an older page
would mishandle), so a bump is needed.

**They join rack file version 4,** with the keys the rack products note
gathers for it (frame `width`, `startU`, round holes, `setback`, `options`,
item `setback` and `heldBy`, zero-U `channel`) and the keys held for it by
#934 (`states`, `readings`) and #939 (the PDU bracket key): one bump, published
under `/schemas/v3/`, an identity migration from 3. **Both keys are reserved
in version 4 whenever it ships**, with the hosting step of the rack products
note: its schema defines them and its `parseDoc` keeps them from the first
build of version 4, before anything consumes them. Slack (step 4 of section
10) and lay order (step 5) then only start reading keys version 4 already
carries, so neither needs a version 5. The version-4 table of the rack
products note (section 9 there) gains `states`, `readings`, the PDU bracket
key, `slack` and `lay` when version 4 lands.

Routed lengths of saved racks change without a file change (section 12): the
kit re-measures a routed length the next time a page measures it, as it did
for #930, and never touches an entered one. When a re-measure moves a stock
size, the page says so once, naming the cables, since a stock length is what
someone orders.

## 8. Agent tools

The site builds its `edit_rack` schema from the kit command table, so new kit
commands are offered with no new tool. The kit gains:

- **`cable.slack {id, at: {item, via}, value?, unit?, form?}`**, and
  `cable.slack.clear {id, at?}`: store or remove slack, refused where the loop
  does not fit or the tray is not on the route.
- **`cable.lay {id, at: {item, via}, lane}`**, and `lane: null` to unpin.
  The name keeps the lay apart from the gutter lanes: a waypoint is already
  `{lane, ru}`, and `inspect` already returns `lanes`, the gutter lanes of the
  frame.
- **Routing into a tray** needs nothing new: `cable.route` takes `{item, via:
  'tray'}` as it takes a ring, and the refusal that lists what exists lists
  trays too.

And the reads:

- **`inspect` of a cable**: its route output, which has `rings` today, gains
  `crosses` (each finding of 1.4, with the two waypoints it lies between) and
  `rests` (each support it lies on, and its lane there). `slack` keeps one
  meaning, the spare length: it stays `{metres}` and gains `stored`, the
  stored entries of section 5.2, each with the length it holds.
- **`inspect` of a device**: each tray, with its fill, the cables in it and the
  slack it holds.
- **`describe`**: one line of totals for the findings ("2 cables cross a
  body; 1 tray is full"), so an agent that only describes the rack still
  sees fault 1, as the session behind #949 did not.

The site prints these in `cableText`, as it prints `routed` and `slack`; that
is the site check of step 2, a test that an agent reading `inspect` on a cable
through the tray floor is told so and told what to do.

## 9. What this does not do

- Straps through `ties` are not drawn or counted for single cables; the bundle
  straps of #921 are unchanged (decision 3).
- No plan view of the rack (decision 1).
- No cable weight, tension or load on a tray.
- Slack across racks, service loops at a device, and slack in a vertical duct.
- Routing inside an enclosure from a cassette to a spool is drawn only where
  the drawer is open in 3D; the elevation shows the closed front.

## 10. Order of work

The order #949 proposes holds, with the FHD enclosure data split out as its
own step.

1. **This note.** Gate: preflight against main, and the doc tests.
2. **Solid bodies and the finding** (kit, then site). `solids` in `rack.json`;
   detour points in `routePath`; `bodyFindings`; `crosses` in `inspect`; the
   totals line in `describe`; the export notes. The site stops leaving sheet
   parts out of its boxes and adds the tube-sampling browser check. Gate: kit
   tests on a fixture rack (an FHD panel, a leaf switch below it and an
   FHD-CMP5DR on the panel) with no crossing on the automatic routes and one
   finding for a hand route through the tray; the `rack.json` test for
   `solids`; the site routing checks re-run; a changelog fragment that says
   routed lengths change.
3. **Trays and resting.** The `tray` and `trays` schema, ring `depth`, `sill`
   and `aperture.at`, lint, the compiled `data-class="tray"`, `trays` in
   `rack.json`; the FHD-CMP5DR tray and the snap-in ring stated (a minor
   each); rule 7 narrowed in the modelling guide; then resting and `DRAPE` in
   the kit. Gate: `./build.sh --device fhd-cmp5dr`; `devicelock.py` checked
   against the lock on main, with the versions bumped, before `--update`; a review
   page of source against render, and kit tests that a cable on the tray runs
   at floor height plus its radius and that no span passes below a surface.
4. **Slack storage**, on rack file version 4. The `slack` and `lay` keys are
   reserved in the version-4 schema by the hosting step of the rack products
   note (section 7); if that step has not landed, this step brings version 4
   with all its keys. Then `cable.slack`, the length, the 2D loop and 3D coil,
   the schedule column and BOM note. Gate: a version-4 round trip, a version-3 page refusing
   a version-4 file, the export tests, and the PR naming its one-way doors.
5. **Lay order**, after #922 and portrayal-site#142 have settled: lanes by
   entry side, local patches along the tray, layers, bundles as one lane,
   `cable.lay`, the forced-crossing count, the full-tray warning. Gate: kit
   tests on the fixture of #949 (one FHD panel with an FHD-CMP5DR lacer, a
   switch above it and a switch below it, cabled to bays 2 to 4) that no two
   cables cross in plan except the forced crossings counted, and the same for a
   grid of ports; a browser check of the same in 3D.
6. **The FHD enclosures and the other FS managers**, as routine modelling
   after step 3, in parallel with 4 and 5: the rows of section 6. Gate: the
   modelling gates per device.

## 11. Decisions

The five questions this note first left open were each decided on
2026-10-09 as it recommended:

1. **2D.** Resting is shown as height on the elevations and slack as a marked
   loop with its length. No plan view is added.
2. **Stiffness.** A kit table by cable family, `DRAPE`, tuned in the kit. No
   per-type key in the cable types table.
3. **Tie slots.** Drawn on the part and declared as `ties`. Straps are not
   drawn under single cables; bundle straps are unchanged.
4. **A full tray** warns and draws the layers as they fall, above the lip if
   need be; storing slack into it is not refused.
5. **Slack** is stored as a coil by default.

## 12. One-way items

Each is additive, and each becomes hard to change once a library part, a
published file or a saved rack file uses it.

| item | where | why it is one-way |
|---|---|---|
| `tray` on a contract and `trays` on a device view, with `floor`, `height`, `lip`, `run`, `ties`, `slack` (`kind: area`, `kind: spool` with `at` and `diameter`) | library manifests | every part that states a tray is written in these names; a rename moves every one |
| a tray id sharing the pathway namespace, named by `{item, via}` | library and rack file | saved routes and slack name trays by it |
| ring `guide.depth`, `guide.sill`, `guide.aperture.at` | component contracts | parts state them; the kit and compiled drawings read them |
| `data-class="tray"` | drawings | consumers of the drawing read it |
| `solids` and `trays` in `rack.json` | the rack catalogue | the kit reads them; additive, so `format` stays 1 |
| the narrowed rule 7 of the modelling guide | library policy | parts modelled under it carry their cable management |
| cable `slack` (`item`, `via`, `value`, `unit`, `form` with `coil`, `serpentine`, `spool`) and cable `lay` (`item`, `via`, `lane`) | rack file version 4 | saved rack files carry them; an older page refuses a version-4 file, and the schema label is never reused |
| lane 1 at the host side, counting outward | rack file (`lay`), kit, `inspect` | a saved hand lay names a lane by this count |
| the version-4 table of the rack products note gaining `states`, `readings`, the PDU bracket key, `slack` and `lay` | `docs/rack-products-design.md` section 9, rack file version 4 | one bump carries them all; a key left out needs a version 5 |
| the stored slack counting in the routed length | kit | a saved routed length and stock size depend on it |
| routed lengths changing on saved racks: detours, cables resting at the floor and at the ring sill, lanes, slack | kit | stored routed lengths and stock sizes move on the next measure; an ordered stock length may no longer match |
| `crosses-body` and the tray findings, `bodyFindings` | kit API, agent output | agents and pages read the kinds |
| `cable.slack`, `cable.slack.clear`, `cable.lay` | kit commands, offered to agents | agent sessions and saved prompts call them by name |
| `inspect` fields: `crosses` and `rests` on a cable route, `slack.stored`, the tray block of a device | kit queries, agent output | agents and the site read them by name |
| the crossing and tray lines in the export notes | exports | a reader of the notes matches them |
| the `slack` column of the cable schedule, after the last column | export | a reader takes it by its header |

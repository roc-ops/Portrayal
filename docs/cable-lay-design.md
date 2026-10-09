# Cable lay: solid bodies, cables resting on trays, a neat lay, and slack in a tray

Status: decided 2026-10-09, nothing built. Issue #949. Each section gives a
recommendation and its reason; the five questions the note first left open
were decided as it recommended, and are listed in section 11, with three
additions made the same day (the underside of a tray, a manager per device,
and a manager mounted upside down), which this note now carries; the one-way
doors are in section 12.

Builds on the rack core in `kit/rack/` (rack file `version` 3), on how a route
passes a ring ([cable-managers-design.md](cable-managers-design.md) section
13, #930), on cable bundles and their checks
([cable-bundles-design.md](cable-bundles-design.md), #921, #922 and #923), on
the cable types table (#919), on the hosts and the rack file version 4 of
[rack-products-design.md](rack-products-design.md) (sections 7 and 9), on the
rack entry `states` and `readings` of
[pdu-model-design.md](pdu-model-design.md) (#934), which names no rack file
version for them and which this note proposes for version 4, and on
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
(no lay); and slack has nowhere to go (no tray, and the FHD panel declares
nothing).

## 1. Solid bodies

**Recommendation: every body is solid to the router; a cable crosses one only
through a declared opening its diameter fits; otherwise the route goes around,
and what still crosses is a finding.**

### 1.1 What is solid

- **A box-shelled device** (every `mount: rack` device that is not a sheet) is
  its envelope, `w` by `h` by `d`, where it stands: the kit already knows all
  three and the item placement. **Except where the envelope holds cable
  space.** A device whose envelope includes room cables run in (an FHD
  enclosure drawer with its spools; the FHD-1UBE, 227 mm overall, of which
  107 mm is the front lacer zone ahead of the patch plate and 120 mm the rear
  lacer bar behind it) is solid as its compiled body and its shell, not as one
  block:
  - **the shell walls:** a plate on every face of the envelope (top and
    bottom covers, both sides, the rear wall), of the `thickness` it states
    or 1 mm where it states none, since only the plane of a wall matters to a
    crossing;
  - **its openings:** the pass-throughs it declares on those faces are the
    only way through a wall (the rear grommets of an FHD-1UFCE, its open back
    behind each slot). A face that is open as a whole is declared as one
    pass-through the size of the face: the FHD-1UBE has no cover, no sides
    and no back, so it simply has fewer walls, and every one of its open
    faces says so;
  - **inside:** the patch plate (the plane its ports and module faces sit
    in), the bodies of the modules seated behind it, and the plates and bars
    of its lacers.

  Its rings, trays and spools are then openings and floors inside the shell,
  not inside a solid, and a cable reaches them only through a declared
  opening. A device is treated so when it declares any pathway or tray
  (sections 2 and 6) that lies inside its envelope; a plain box device with
  pathways only on its faces stays its envelope.
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
envelope its shell walls less their declared pass-throughs, its plate plane
and the bodies of what is seated behind it. A plain
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

**Lying against a plate is not crossing it.** Both faces of a tray floor are
pathway surfaces (2.3): a cable on the resting face lies on the plate, and a
cable on the held face lies against it from below, strapped up to it. In either case
the centre line of the cable stays its own radius outside the plate box, so
it never enters the solid and nothing is found. The rule is unchanged: a
crossing is a leg of the centre line that enters a solid, so a leg that runs
from one face of the plate to the other inside the footprint of the plate (a
cable dropping from a device above straight onto the held face, or a lay
pinned to the held face whose next waypoint is above the tray) passes
through the plate and is a finding, unless the detours of 1.3 take it round
the front edge first. A point of the tube exactly on a face of the plate is
not inside it; the browser check of 1.4 tests the inside with the same
tolerance it uses for every surface a cable rests on.

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
   The wrong side depends on the face the cable lies on (2.3): for the
   resting face, below the plate; for the held face, above it, so a cable
   from a device above that is pinned to the held face goes down past the front edge and
   back in under the plate. For a cable that does not lie in it, the stack on
   the held face of a tray, from the plate down to its strap line, is solid
   as the plate is: a cable passing under it keeps below the strap line by
   its radius and `CLEAR`, dropping first where its port is higher. It need
   only be below the strap line by the back edge of the stack, so the drop
   is bounded by a single arc: a cable leaving its port level can drop
   R - sqrt(R^2 - g^2) over a gap g up to R, and any amount when g is more
   than R, where R is its installed bend radius (`installedRadiusMm` in
   `kit/rack/cable-types.js`). R 30 mm over g 20 mm allows 7.6 mm. **g is
   measured from the port face to the back edge of the rear tie slot of the
   pair that straps the stack**, since the strap passes down through that
   slot: on the FHD-CMP5DR, the pairs across the tray that hold a cable
   running along x, whose rear slot starts 89.7 mm forward of the rail (the
   floor of the strip starts at 48.8 mm and the arms at 15.4 mm, but nothing
   holds a cable there on the held face). A cable that needs more cannot
   clear, and its leg is left and reported (1.4) with the held face named. This obstacle lands with step 5 of section 10, not step 2:
   it needs cables laid on a held face, which step 5 brings.
2. **Round the end.** A leg that would cross a body side to side goes past its
   end, into the gutter, which is where the automatic route already goes.
3. **Front to back by a side lane.** A cable whose ends are on opposite faces
   goes through the lane beside a post, as the automatic route does today.

A hand route keeps its waypoints; the detours are added between them in the
same way, and a leg the three rules cannot clear is left as drawn and reported.

### 1.4 The finding

`bodyFindings(rack, ctx)`, beside `ringFindings`, returns per cable each solid
its path still crosses: `{kind: 'crosses-body', cable, item, part, face?,
between: [from, to], at: [x, y, z]}`, with a sentence. `part` names the solid
(a plate, a wall, a tray); `face`, `top` or `underside`, is present only when
the solid crossed is the held-face stack of a tray (1.3, rule 1), and then
`part` is the tray. The sentence: "c7 passes through mgr-1 tray
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

### 2.3 Two faces

**Recommendation: a tray floor has two faces, and each is a pathway of its
own. The face that looks up holds a cable by gravity; the face that looks
down holds it by straps through the tie slots, and is offered only where the
tray declares `ties`.**

- **The names** are `top`, the side of the plate the part declares its floor
  and rings on, and `underside`, the other side of the same plate. They are
  names in the frame of the part, so turning the item over (section 7.1)
  does not rename them: a cable pinned to the top of a manager stays with its
  rings when the manager is mounted upside down, as it would in the rack.
- **The roles** follow the item as mounted. The **resting face** is the one
  that looks up and the **held face** the one that looks down. On a tray
  mounted the usual way the top rests and the underside is held; on one
  mounted upside down (`roll: 180`, 7.1) the two swap, so its top is
  underneath and held by straps, and its underside, now facing up, is a plain
  floor with no rings on it.
- **What is offered.** The resting face always. The held face only where the
  tray declares `ties`, since there straps hold the cable and not gravity, or
  through a ring standing on it, since a hanging ring holds a cable on its
  lower band (section 3.1). A tray with no tie slots and no ring on that face offers no held face. The
  FHD-CMP5DR declares sixteen, so it offers both.
- **Lying on the held face.** On a tray mounted the usual way, the
  underside, the cable lies against the plate. (On a tray turned over, the
  held face is its top, and a hanging ring holds the cable on its lower band,
  about 31.5 mm below the plate on the FHD-CMP5DR: section 3.1.) Between two
  straps it sags a little, by the drape of its type over that span, and never
  below the **strap line**, the bottom of the strapped stack at that point.
  The stack gathers where the straps are: under the pair of slots a strap
  passes through, 89.7 to 98 mm forward of the rail on the FHD-CMP5DR, an
  8.3 mm strapped width, so a held face lays few cables side by side and
  stacks the rest; a position wider than that, such as a bundle, is centred
  on it. A
  stretch of the held face that passes no tie slot cannot be held: the
  automatic route never uses one, and a stretch pinned there by hand warns
  (`unheld`, with the cable and the tray).
- **The tie slots it uses** are every slot along its stretch on the held face.
  They are marked: outlined in 3D, and listed per support in the `rests` of
  `inspect` (section 8).
- **Straps on the held face are counted**, one per tie slot used, whatever
  number of cables pass under it: a strap goes round the stack. The count is
  per tray, and the BOM notes and the cable schedule list it (5.5). **They are
  not drawn in 3D.** Decision 3 leaves loose straps undrawn because their form
  is chosen in the field (hook-and-loop or a tie, one turn or two), no library
  part describes one, and a drawn strap would be geometry no source gives; the
  number is a fact the route fixes, and the marked slot shows where each one
  goes. **Straps on the resting face are neither drawn nor counted**
  (decision 3): gravity holds the cable there, and a strap is optional
  dressing.
- **Slack is stored on the resting face only**, which on a tray mounted the
  usual way is the top. A loop on the held face would need straps no count
  could know. `cable.slack` on a tray where the cable lies on the held face
  is refused with a sentence: "c7 lies on the held face of mgr-1 tray; slack
  is stored on the resting face: pin it there, or use another tray."
- **Fill** is worked per face (4.4). The held face has no lip, so its stack
  is bounded by the opening the resting face has (the height of the ring
  opening above its sill, or the lip, or the envelope, as 4.4 sets out). That
  is an estimate: no source states how much a strap holds.

**Which face the automatic route uses.** The face nearer the port the cable
reaches the tray from: a port above the plate takes the face that looks up, a
port below it the face that looks down, where that is offered. On a tray
mounted the usual way that is the top for a device above and the underside
for a device below. The plate height decides, not the U: the ports of the
device the tray is fixed to (the panel behind a lacer) are above a floor 3 mm
from the bottom of the unit, so they reach the top. A cable lies on one face
of one tray; a through cable in two trays chooses in each, and may lie on the
top of one and the underside of the other. **A cable with both ends in one
tray whose ends want different faces** (a side-to-side patch: a switch below
cabled to the panel) lies on the resting face, and the end that wanted the
held face comes round the front edge (1.3, rule 1), as it does today: one
face per tray keeps the lay a single order, and the panel end can reach only
the top.

**A face pinned by hand** is saved in `lay` (section 7) as `face`, with or
without a position. A crossing that exists only because a face was pinned is
counted apart, as a crossing made by hand (4.1), and named with that cable.

## 3. Resting

**Recommendation: a supported cable lies on its support, lifted by its own
radius; only a free span sags, and it never sags below a surface under it.**

- **Supports** are a tray floor, the sill of a ring, the floor of a duct
  channel, and any solid the cable would otherwise sag into, and, on the held
  face of a tray (2.3), the plate the straps hold the cable against. A port
  is not a support; it is an end.
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
cable lies across the tray (its position, section 4) is not seen there. No plan view is added
for this (decision 1); the 3D view shows it. A cable on the held face runs
below the plate, at the plate less its radius where it lies against it, or at
the rest line of a hanging ring (3.1), so the elevation shows which face it
is on.

### 3.1 In an item turned over

Resting and lay order are worked **in the frame of the item as mounted**: its
own frame, turned by its `roll` (section 7.1), with gravity down the rack. For
an item that is not turned over nothing changes.

- **A ring.** `sill` is measured in the frame of the part, from its base (the
  face it is fixed to) to the near inside edge of the opening, and `aperture`
  gives the opening its height. A cable rests on the inside edge that is
  lowest once the part is turned. Upright, that is the sill. **In a ring
  hanging upside down** it is the band now below the cable, the far inside
  edge: `sill` plus the opening height from the base, measured downward. The
  cable centre is that edge plus its radius, and the layers (4.2) stack up
  from it toward the base. The opening and so the capacity of the ring are
  unchanged. Turned 90 or 270 degrees, the ring runs up the rack and its
  cables run along gravity, which is the CMH-6DR1U end ring of section 4: they
  do not rest.
- **A tray.** Its two faces swap roles (2.3): the top is held, the underside
  rests. A cable on the held top of a turned tray passes through its hanging
  rings on their lower bands; between two rings the straps of its tie slots,
  where it has them, hold it at the rest line of the rings, the strap line of
  that face, and it sags a little between them and never below it. A turned
  tray with no tie slots holds such a cable only at its rings, and the span
  between two rings sags by its drape as any free span does.
- **Lay order** in a turned item is the order of 4.1 with its ends read in
  the frame as mounted: what comes from above and what from below follows
  gravity, and the host side stays the host side, since a turn about the
  depth axis does not move the back of a tray to the front. The turn mirrors
  left and right across the item, and the interleaving test does not change
  under a mirror, so the forced set is the same whichever frame it is read in.

## 4. Lay order

**Recommendation: cables that share a tray, ring or duct each get a position
across it, chosen so that two cables cross only where their ends force it;
flat in a tray, round in a bundle; kept through the run; stacked when a layer
is full, and a full tray warns.**

**A position** is a place across a pathway in the lay: the slot one cable (or
one bundle) takes side by side with the others, counted from 1. The word is
kept apart from a **lane**, which in this note and in the rack file is only
the gutter beside a post (`{lane, ru}`).

**Where position 1 is.** Positions are counted outward from the part the
pathway is fixed to:

- a tray running along x (a lacer, the floor of an enclosure drawer): from
  the host side, the back of the tray at the rail, toward the front edge;
- a ring with no tray under it, on a vertical plate (the 1U D-ring panels):
  from the plate outward, along the side of its opening that stands out of the
  plate;
- a ring that runs along y (the CMH-6DR1U end ring): from the plate outward in
  the same way; its cables run along gravity, so they do not rest, and a
  second layer is the next row across x, starting from the side nearer the
  centre line of the rack;
- a duct: from its base plate outward, across the channel.

Each face of a tray (2.3) counts its own positions, both from the host side
toward the front edge. On the held face the cables lie only within the
strapped width (2.3), so position 1 there is the cable at the back edge of
that width, the one nearest the rail of those the strap holds (89.7 mm
forward of the rail on the FHD-CMP5DR), against the plate; it is not at the
back edge of the floor.

### 4.1 The order

**In plan each face of a pathway is a disc and each cable a chord.** A ring,
a duct, and a tray that offers only its resting face are one disc; a tray
that offers its held face as well is two, one each side of the plate, each
with its own lay order and its own forced set. Walk round the edge of a face
seen from above: its left end (the left gutter), its back edge from left to
right, its right end, its front edge from right to left. Every cable on that
face has two ends on that edge:

- a **rail-side end**, where it reaches the face at the back, at the rail
  plane: on the resting face from the host behind the tray or down from a
  device above, whose ports are at the rail plane; on the held face up from a
  device below;
- a **front-edge end**, where it comes round the front edge (section 1.3,
  rule 1): on the resting face up and over from a device below; on the held
  face down and under from a device above;
- a **gutter end**, at the left or right end of the tray, for a cable that
  runs on to a gutter (a through cable).

Two chords in a disc must cross exactly when their ends **interleave** round
the edge (one end of each between the two ends of the other), and any set of
chords no two of which interleave can be laid with no crossing. So the rule
is: **two cables cross only when their ends interleave, and then once.** That
pair is a **forced crossing**. Two ends at one point (two through cables
leaving by the same gutter) do not interleave.

**The front-edge group with two faces.** It still exists, but under the
automatic route it is now rare. The automatic face is the one nearer the port
(2.3), so a device above reaches the resting face at the rail and a device
below reaches the held face at the rail: both are rail-side ends. A
front-edge end is left only where the held face is not offered (a tray with
no tie slots, as every tray is today), where a cable with both ends in the
tray wants both faces (a side-to-side patch, which lies on the resting face),
and where a face is pinned by hand against its port.

**A cable on the resting face and a cable on the held face never cross.** They are
chords of two discs, and the discs are the two faces of one plate, which is
solid (section 1): no chord of one disc meets a chord of the other, because
the plate lies between every point of the two. What is left is where the two
discs share an edge, and there:

- **a gutter end** is a single point of each disc; two cables, one on
  each face, that leave by the same gutter meet only in the lane beyond it, which is a pathway of its own and not part of either face;
- **a front-edge end** of one face is a free span outside the other disc,
  not a chord in it. A cable from below that comes over the front onto the
  resting face runs forward from its port and **passes under the footprint of
  the held face**, below its strap line (2.3), then rises only in front of the
  plate, clear of it by `CLEAR` (1.3). In plan it can lie across a cable on
  the held face (b across d in plan, in fixture 1 of 4.5); in 3D b passes
  under d.
  What keeps it clear is the detour rule: the stack on a held face, down to
  its strap line, is solid to every cable that does not lie in it (1.3, rule
  1), so a run from a high row of ports drops below the strap line before it
  runs forward, and one that cannot is a `crosses-body` finding with the
  tray as its `part` and the held face as its `face` (1.4). A cable from above that comes under the front onto
  the held face drops in front of the resting face and comes back in below
  the plate, in the same way;
- **a rail-side end** of one face reaches its own side of the plate from its
  own side of the rack (the resting face from above, the held face from below), and
  never passes the edge of the other face at all.

So the claim is per disc, in 3D, not in a plan projection: a pair of cables
can be a forced crossing only when both lie on one face,
and moving a cable to the other face can only take pairs out of its forced
set. The worked fixture of 4.5 shows one going.

The positions that realise it, in the cases a rack has:

- **Rail-side through cables** take the **inner** positions, ordered by how
  far their port is from the gutter they take: the one nearest the gutter
  innermost, each one further away one position further out. A cable then
  drops into its position without passing any cable already laid, because
  every rail-side cable already there comes from further along and lies
  further out.
- **Front-edge through cables** take the **outer** positions, the other way
  round: the one nearest the gutter outermost, each one further away one
  position further in.
- **Local patches.** Today the automatic route picks the gutter from the x of
  end A alone (`route.js autoRoute`), and when both ends leave through the
  same manager it goes out to the gutter and back through the same rings (a
  patch from a switch port at x -150 to a panel port at x -20 runs ring 1,
  left-front U12, U11, ring 1, ring 2). **A patch whose two ends share one
  manager runs along the tray directly, port to port, through the rings
  between them, with no gutter.** A local patch with both ends rail-side lies
  in the rail group, inside every through cable that passes its stretch; one
  with both ends front-edge lies in the front group, outside them. Of two such
  patches the shorter lies nearer its side, so patches that nest never meet.
- **Side-to-side patches** (one end rail-side, the other front-edge: a switch
  below cabled to the panel) take a **middle band**, between the rail group
  and the front group. Two of them interleave only when their port orders
  disagree; in consistent order (the switch ports in the same order as the
  panel ports they reach) they interleave with nothing in the band. Within the
  band, a patch whose rail-side drop falls inside the stretch of another
  takes the inner position, so it drops in behind the one already there.
- **Equal distances.** Cables at the same distance from their gutter, or at
  the same x on the same edge (one port above another), take the lower U at
  the inner position, in every group: the kit already sends a higher row of
  ports further out from its face (`cable-geometry.js reaches`, `REACH_STEP`),
  so the higher cable is the outer one where both turn into the tray. Then the
  lower cable id is the inner.

**Opposite ways.** A through cable has one gutter, and both of its ends use
it. Step 5 chooses the gutter for each cable from both ends, not from end A
alone: when both ports stand on the same side of the centre line in their
trays, that side; when they stand on opposite sides, the side that gives the
shorter path. Through cables that each run toward their own port side then
use separate stretches of a tray and never meet. **A through cable whose ends
sit on opposite sides of the centre in two trays runs against its port in one
of them**, and there it is a forced category of its own: its gutter end is on
the far side of every cable it passes, and the interleaving test counts each
crossing that makes.

**The forced crossings, exactly.** A forced crossing is a pair of cables in
one pathway whose ends, taken as above (rail-side, front-edge, and the gutter
end of a through cable), interleave round its edge. That covers a through
cable whose port lies inside a local patch, a side-to-side patch against a
through cable from further along, two patches whose ends interleave, and a
cable running against its port. **Such a cable passes over, never through:**
it steps over the other by one layer at the one point where it must and back
after, away from what holds it: up off a floor or the band of a ring, down
off a plate it is strapped to. The
kit counts the forced crossings per pathway and names each pair, and the order
above makes no other crossing: every crossing drawn is one the ends force. A
hand lay (4.3) can make more; those are counted apart, as crossings made by
hand, and named with the cable that was pinned.

### 4.2 Flat and round

- **Single cables lie flat**, side by side across the floor, each position as
  wide as its cable. The layer is as wide as the narrowest opening on the
  shared stretch: through an FHD-CMP5DR ring that is the 32.0 mm across the
  opening, not the 61.2 mm of the strip.
- **A layer that is full starts the next** on top of it, in the same order.
  For the snap-in ring that is five 6 mm Cat6 cords a layer and four layers
  under its 29.5 mm, twenty cables, against the theoretical 30 the datasheet
  states for the panel: the figure the vendor gives assumes a pack tighter
  than square layers.
- **A bundle takes one position.** Its members pack round inside it, as the
  bundle model (#922) and the member packing of portrayal-site#142 already
  draw them, and the bundle takes a position of its own diameter among the
  single cables, as one chord, in the order of its first member.

### 4.3 Across a run

- A position is **kept along the shared stretch**: it is assigned where the
  cable first shares a pathway and held through every pathway it shares with
  the same neighbours.
- **A cable joining** takes the position its order gives; the cables already
  there do not move, which is what the order of 4.1 guarantees.
- **A cable leaving** (at its own pathway, or at a bundle peel point) gives up
  its position, and the positions outside it close up only after the next
  support, so no cable is drawn sliding sideways inside a ring.
- **A turn keeps the order on the same side:** a flat run turning from a tray
  into a gutter keeps its outermost cable outermost, so it never twists over
  itself.
- **A hand lay** pins one cable to one position in one pathway (`lay`, section
  7); the others are laid round it in order.

Positions and faces are computed, not stored, except a hand lay. Where each
position is across the pathway is part of `routePath`, so it moves the
measured length by millimetres and agrees in every view. The face moves it by
more, the difference between rising to the held face and coming over the
front edge onto the resting face, tens of millimetres a tray.

### 4.4 A full tray

A tray holds, at the fill share rings already use (`FILL_LIMIT`, 0.4), the
area of its narrowest opening on the stretch, or of its floor width by its
`lip` where no ring bounds it, and a tray with neither a lip nor a ring takes
its envelope height. Over that, or over the cable count the device states, it
**warns, and draws the layers as they fall**, above the lip if need be: as for
rings and bundles, a device moving can fill a tray without a cable command,
so it must be able to sit over the limit and say so. Storing slack into a
full tray warns the same way and is not refused (decision 4). Each face of a
tray is filled apart, the held face against the bound 2.3 gives it.

### 4.5 The fixtures, worked

Three fixtures hold the lay order (step 5 of section 10). Ports are given by
x, mm from the centre line of the rack, positive to the right seen from the
front; the figures are illustrative, chosen so each case occurs once. The
FHD-CMP5DR tray spans x -224.2 to 224.2. Ends are listed round the edge of a
face as 4.1 walks it: the left gutter L, the back edge left to right, the
right gutter R, the front edge right to left.

**Fixture 1, the one #949 names.** An FHD panel P at U12 with an FHD-CMP5DR
lacer on it (tray T), a switch S-up at U13 above and a switch S-dn at U11
below, and a second panel P2 at U20 with a lacer of its own.

| cable | from | to | in T |
|---|---|---|---|
| a | S-up -150 | P bay 2, -60 | a local patch, both ends rail-side |
| b | S-dn -140 | P bay 4, 120 | side-to-side, its S-dn end over the front edge |
| c | S-dn -100 | P bay 3, 30 | side-to-side; with b, a pair whose port orders disagree |
| d | S-dn -120 | a device lower in the rack, by the left gutter | a through cable |
| e | S-up -100 | a device lower in the rack, by the left gutter | a through cable whose port lies inside the stretch of a |
| f | S-up 60 | P2, -150 | the opposite-way cable: its ends sit on opposite sides of the centre in T and in the lacer of P2, the left gutter is the shorter (358 mm across the two trays against 538), so in T it runs against its port |

*As the note stood before the two faces*, every cable lies on the top, with
the S-dn ends of b, c and d over the front edge. Round the edge:
L (d, e, f), a -150, e -100, a -60, c 30, f 60, b 120, R, c -100,
d -120, b -140. The forced set is **a-e, b-c, c-f and b-d**: e drops in
inside the stretch of a; b and c disagree; f runs left past the drop of c;
and d leaves leftward over the front edge inside the stretch of b.

*With the two faces*, the tray offers its underside (it declares sixteen tie
slots). a, e and f come from above and lie on the top. b and c each have one
end above the plate (the panel) and one below (S-dn), so each lies on the
resting face, the top, with its S-dn end over the front edge as before. d has
one end in T, from below, so it lies on the underside, rail-side at -120, and
uses the tie slots between its port and the left end (the first at part x
54.85), one strap each in the BOM note. **The heights that keep b clear of
d.** S-dn has one row of ports at the middle of its unit, port centres 22.2
mm below its top, and b, c and d are 3 mm fibre cords. Heights are in mm
from the top of S-dn, which is the bottom of U12. The floor top of T is at
3.0 and its sheet is 1.5 thick, so its underside is at 1.5; d, one 3 mm
layer, puts the strap line at -1.5. b must pass with its centre at or below
-8.0 (the strap line, less its 1.5 radius and the 5 of `CLEAR`). Its port
centre is at -22.2, so it clears by 14.2 with no drop at all. So fixture 1 has **no
`crosses-body` finding**, and b runs below the strap line of d. Round the top: L (e, f), a -150,
e -100, a -60, c 30, f 60, b 120, R, c -100, b -140; round the underside:
d -120 and L. **The forced set is a-e, b-c and c-f on the top and none on
the underside: three, where it was four.** b-d is gone, because d no longer
shares a face with b. Pinning d to the top by hand brings b-d back, counted
as a crossing made by hand and named with d.

**Fixture 2, a manager per device.** Fixture 1 moved up one unit, so that
U11 is free for the variant below, without P2, which this fixture does not
use, and with a rack-face lacer on each switch as well: S-up at U14 with
lacer M1 on it, P at U13 with T, S-dn at U12 with lacer M2 on it. Every cable from a switch to the panel is then a
through cable: from its port through the rings of the switch lacer, out to a
side lane, along the lane and into T, then to its port. Every end is
rail-side on the top of its own tray, since each port is on the device its
lacer is fixed to.

| cable | from | to | gutter, from both ends |
|---|---|---|---|
| g | S-up -150 | P bay 2, -60 | left: both ports left of centre |
| h | S-up -100 | P bay 3, 30 | left: 378 mm against 518, so in T it runs against its port |
| i | S-dn -140 | P bay 4, 120 | left: 428 mm against 468, so in T it runs against its port |
| j | S-dn 150 | P bay 4, 130 | right: both ports right of centre |
| k | S-up 100 | P bay 2, -50 | right: 398 mm against 498, so in T it runs against its port |

Round the top of T: L (g, h, i), g -60, k -50, h 30, i 120, j 130, R (k, j).
k leaves rightward from -50 past the drops of h and i, which leave leftward.
In M1, g and h leave left from -150 and -100 and k right from 100; in M2, i
leaves left from -140 and j right from 150; neither interleaves. **The forced
set is h-k and i-k, both in T.** With every end rail-side, a forced crossing
is exactly a pair whose gutters disagree with the order of their ports, so
this fixture checks the gutter rule of 4.1 on its own, apart from local and
side-to-side patches.

**Which manager each end takes.** `route.js managerOf` looks first for a
manager hosted on the item of the end, on its face. M1 is hosted on S-up, M2
on S-dn and T on P, so each end finds its own lacer, and `autoRoute`, given
two different managers, already runs manager, lane, manager. **For this
fixture `managerOf` picks the right managers as it stands.** It does not when
the manager of a device is a 1U part in a unit of its own and not hosted on
the device. **The variant** is fixture 2 with M1 and M2 removed and two
D-ring panels such as the CMH-5DR1U added, standing alone: D1 at U15 over
S-up and D2 at U11 under S-dn, with P and T at U13 between the switches and
the same five cables. `managerOf` then tries the unit above before the unit below, and
takes a manager carried by a neighbour device as readily as a neighbour that
is a manager: S-up finds D1 above it, which is right, but S-dn finds P
first, takes T, and its cables never reach D2 under it. So the note requires, with step 5 and as a variant of
this fixture, that `managerOf` rank its candidates:

1. a manager hosted on the item of the end, on its face (as today);
2. an adjacent part that is itself a manager, serving no port of its own (a
   D-ring panel, a lacer standing alone in its unit); where there is one
   above and one below, the one nearer the port row of the end (a row in
   the upper half of the device takes the one above, a row in the lower half
   the one below), then for a row at the middle the one no other device
   adjoins on that face, then the one above;
3. a manager hosted on an adjacent device, above before below;
4. an adjacent device that declares guides of its own, above before below.

The variant asserts that S-up takes D1 and S-dn takes D2, through rank 2
over the T of rank 3. The tie-break of rank 2 matters in a stack with a
manager under each switch, a second rack in the same fixture, since it
reuses the units of the variant (Ma at U13, S1 at U14, Mb at U11, S2 at
U12): S2
has a manager on both sides, so its upper row of ports takes Ma, which it
shares with S1, and its lower row takes Mb; a single row at the middle of S2
takes Mb, the one only S2 adjoins. Without the tie-break, S2 would take Ma,
above, for every port. The test gives S2 two rows of ports in that rack
and one row at its middle in a copy of it, and asserts all three: upper row
to Ma, lower row to Mb, middle row to Mb. Fixture 1 is unchanged by the ranking, since it has no standalone
manager.

**Fixture 3, a manager pair back to back.** S-up at U14; an FHD-CMP5DR Mu
standing alone at U13, mounted the usual way; a second, Md, at U12 with
`roll: 180` (section 7.1); S-dn at U11. Mu has its floor 3 mm above the
bottom of U13 and its rings standing up; Md has its floor 3 mm below the top
of U12, facing down, and its rings hanging below it. The two plates are back
to back across the line between the units, and the pair has D-rings on both
sides. `managerOf` takes Mu for S-up (the unit below it) and Md for S-dn (the
unit above it), as it does today and under the ranking. In Md the face that
looks down is its top, so the cables of S-dn lie on its held face, through
its hanging rings.

| cable | from | to | gutter, from both ends |
|---|---|---|---|
| m | S-up -150 | S-dn -150 | left |
| n | S-up -100 | S-dn 60 | left: 408 mm against 488, so in Md it runs against its port |
| o | S-up 150 | S-dn 20 | right: 278 mm against 618 |

Round the held face of Md, read in rack x: L (m, n), m -150, o 20, n 60,
R (o). **The forced set is n-o in Md, and none in Mu** (m -150 and n -100
leave left, o 150 leaves right). Read in the frame of Md, mirrored, every x
changes sign and L and R swap; the pair is the same, since interleaving does
not change under a mirror. The test also asserts the resting of 3.1: in each
hanging ring of Md a cable rests on the lower band, the sill plus the 29.5 mm
opening below the plate (with the estimated 2 mm sill of the snap-in ring,
34.5 mm below the top of U12), its centre a radius above that, its layers
stacking up toward the plate, and no cable between two rings below that line
where a tie slot holds it. The upward face of Md, its underside, is a resting
face with 3 mm of its envelope above it, so slack stored there warns at once
as a full tray (4.4), and slack stored in Mu does not.

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
  waypoint that no longer resolves is kept and reported (`gone`). The slack
  lies on the resting face of the tray (2.3), and the cable must lie there
  too.
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
  leaves at its position.
- **2D**: a marked loop, an ellipse in the colour of the cable at the tray,
  with the stored length in its tag ("1.2 m slack"), since an elevation sees a
  flat coil only edge on (decision 1).

### 5.5 Exports

- **Cable schedule**: a `slack` column **appended after the last column**
  ("1.2 m in mgr-1 tray"), so no column a reader takes by position moves.
  #923 moved three columns for `bundle`; this does not need to. After it, a
  `straps` column, appended in the same way, names for a cable on the held
  face of a tray the tray, the face it lies on and the tie slots it passes
  ("mgr-1 tray, held face (underside), ties 1 to 3"; on a tray with
  `roll: 180`, "held face (top)"). The role says where the cable is in the
  rack and the name which side of the part, so the text is right on a tray
  turned over. It names slots and not a count, because a strap round the
  stack serves every cable under its slot, and a count per cable would add up
  to more straps than there are.
- **BOM**: the cable lines are unchanged in shape; the length bought already
  counts the slack, and a note per cable that stores some says where. A note
  per tray with cables on its held face counts its straps, one per tie slot
  used ("mgr-1 tray: 3 straps on the held face (underside), ties 1 to 3",
  with the face named as in the schedule). The straps are
  a note and not a line: no library part describes one, so there is nothing
  to name a line by.
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

Two cable keys and one item key, read and written by the kit:

| key | where | what |
|---|---|---|
| `slack` | cable | a list of `{item, via, value?, unit?, form?}` (section 5.2) |
| `lay` | cable | a list of `{item, via, position?, face?}`: the hand lay in one pathway, its position counted from 1 as section 4 sets out, and for a tray the face it lies on, `top` or `underside` (2.3); an entry states at least one of the two, and `face` is refused on a ring or a duct |
| `roll` | item | how the item is turned about the axis out of its face: `90`, `180` or `270` degrees; absent is upright (section 7.1) |

`face` needs no key of its own: a face is chosen per tray, as a position is,
so it belongs in the same entry, and a cable with no hand lay keeps no face
and takes the automatic one.

An older reader **keeps both cable keys** (a cable keeps keys `readCables`
does not know) **and misreads them**: its `withRoutedLengths` measures the
path without the stored slack, rewrites the routed length shorter, may drop a
stock size and saves that; and its route editor takes a tray off a route and
leaves the slack naming it. That is the case version 2 was raised for (a part
an older page would mishandle), so a bump is needed. **It drops `roll`**
(`readItem` rebuilds an item from the keys it knows) and erases it on its
next save, drawing a manager mounted upside down as upright meanwhile: the
case #921 bumped for.

**They join rack file version 4,** with the keys the rack products note
gathers for it (frame `width`, `startU`, round holes, `setback`, `options`,
item `setback` and `heldBy`, zero-U `channel`), with the rack entry `states`
and `readings` of #934, which the PDU note gives no version and this note
proposes for version 4 with section 9 of the rack products note, and with the
PDU bracket key of #939, and with the item key `roll` of 7.1: one bump, published
under `/schemas/v3/`, an identity migration from 3. **Both cable keys are reserved
in version 4 whenever it ships**, with the hosting step of the rack products
note: its schema defines them and its `parseDoc` keeps them from the first
build of version 4, before anything consumes them. Slack (step 4 of section
10) and lay order (step 5) then only start reading keys version 4 already
carries, so neither needs a version 5. Section 9 of the rack products note
now lists these keys as proposed for version 4, and its version-4 table gains
`states`, `readings`, the PDU bracket key, `slack`, `lay` and `roll` when
version 4 lands. The reserved `lay` is the shape above, with `position` and
`face` each optional, from the first build of version 4: a schema that
required `position` would refuse a face pinned on its own, and loosening it
later is a change to a published schema.

**Reserving `slack` is not enough on its own.** A version-4 reader that keeps
the key without understanding it would still load the file, re-measure the
routed length without the slack, drop a stock size and save. So **the first
version-4 reader**, the version-4 step itself, wherever it lands, must, for a
cable that carries `slack` it does not yet act on:

- keep the stored routed length and stock size as written, and not
  re-measure them (`withRoutedLengths` leaves the cable alone), saying once
  that its slack is not yet read by this page;
- refuse a route edit that takes off the route a tray the slack names, with a
  sentence naming the tray.

This is a requirement of the version-4 step here and of the version-4 plan of
the rack products note, which section 9 there now states. A `lay` that a reader does not act on is harmless: the
cable is laid in its computed position instead of the pinned one, which moves
it across the pathway and its length by millimetres, and the key is kept for
the next page that reads it. A `face` it does not act on is harmless in the
same way: the cable lies on the automatic face, its length moves by the
difference between the two paths (tens of millimetres, which can move a
stock size, said once as any re-measure is), and the key is kept.

**`roll` is not harmless to ignore.** Turned 90 or 270 degrees an item takes
other units, so a reader that kept the key and fitted the item upright would
let another device into units it fills. So the first version-4 reader fits a
rolled item by its rolled box, as 7.1 sets out, and if it cannot yet draw the
face turned it draws the rolled outline with the label, says once that the
face is not drawn turned on this page, and keeps the key. Routes through a
rolled manager wait for step 5, and until then the page routes its cables as
if it were upright and says so.

### 7.1 An orientation key: `roll`

**Recommendation: one item key, `roll`, for every way an item is turned in
its face plane: `180` for a manager mounted upside down, and `90` or `270`
for the vertical mounting of #550. The rack products note already reserves
the name for #550; this note proposes it for version 4 with a third value.**

A vertical flip and a quarter turn are the same movement, a turn about the
axis out of the face of the item, by different angles. Two keys for them
would let one item carry both and leave a reader to decide which applies
first; one key with four angles cannot disagree with itself.

- **The values** are `90`, `180` and `270`, degrees clockwise as the item is
  seen in the elevation of the rack face it is mounted on. Absent means
  upright, and `0` is not written, so an upright item is unchanged. The
  sense is that of a `rotate` on a library placement (clockwise as drawn),
  so a reader of both reads one convention. Which of `90` and `270` the
  FX-8 takes is settled by #550 from its installation figures; this note
  settles only the convention.
- **How it composes.** `face` puts the item on the front or the rear of the
  rack; `turned` puts its rear panel toward the viewer of that face (a turn
  of 180 degrees about the vertical); then `roll` turns what that viewer sees
  about the centre of its box, in the plane of the face. Read in that order,
  every combination names one mounting. A manager upside down with its rings
  toward the room is `roll: 180`; the same manager turned over front to back,
  which puts its rings toward the rack, is `turned: true, roll: 180`, since
  a half turn about the vertical followed by a half turn in the face is a
  half turn about the horizontal. The order matters only for `90` and `270`,
  which is why it is fixed here.
- **Fit.** Fit takes the rolled box. At `180` the box is the same box: a 1U
  manager still occupies its U and only it, its width is held to the opening
  and its depth to the rails as before, a hosted one keeps its `on` and
  `unit`, and a one-rail part keeps its `side`, which names a rail of the
  rack and not a side of the part. The ear holes of a whole-U part need no
  new check: the three holes of a U are symmetric about its middle (EIA-310:
  6.35, 22.225 and 38.1 mm up), so a part turned 180 degrees meets the same
  holes. At `90` and `270` the width and height swap: the item takes its
  width over 44.45 mm in units, rounded up, standing on its `ru`, and its
  height must pass between the rails; #550 settles where across the opening
  a turned box stands and what its mount kit adds.
- **Drawing and routing.** The elevation turns the face of the item about the
  centre of its box. The guides, trays and ties of the item are turned with
  it, so `pointOf` and every ring or tray position are read through the roll,
  and resting and lay order are worked in the frame as mounted (3.1).
- **Exports.** A rolled item adds a note, as a turned one does ("Mounted
  upside down.", or for a quarter turn "Mounted rotated 90 degrees
  clockwise, as seen from its face." or "Mounted rotated 90 degrees
  anticlockwise, as seen from its face."), worded apart
  from the existing note for a turned item, which says it is mounted
  turned. Neither DCIM has a field for
  it, so it goes in the comment lines.

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
- **`cable.lay {id, at: {item, via}, position?, face?}`**, with
  `position: null` or `face: null` to unpin either; an entry with neither
  left is removed. `face` is `top` or `underside`, refused on a ring or a
  duct, and refused on a held face the tray does not offer (no `ties` and no
  ring on it), with a sentence naming the tray.
- **`patch` gains `roll`** beside `turned`, `90`, `180`, `270` or `null`,
  refused where the rolled box does not fit (7.1). The names keep the lay apart from the gutter lanes: a waypoint is
  already `{lane, ru}`, and `inspect` already returns `lanes`, the gutter
  lanes of the frame.
- **Routing into a tray** needs nothing new: `cable.route` takes `{item, via:
  'tray'}` as it takes a ring, and the refusal that lists what exists lists
  trays too.

And the reads:

- **`inspect` of a cable**: its route output, which has `rings` today, gains
  `crosses` (each finding of 1.4, with the two waypoints it lies between) and
  `rests` (each support it lies on, its position there, the face for a tray,
  and on a held face the tie slots it uses). `slack` keeps one
  meaning, the spare length: it stays `{metres}` and gains `stored`, the
  stored entries of section 5.2, each with the length it holds.
- **`inspect` of a device**: each tray, per face, with its fill, the cables
  on it, the slack it holds on the resting face and the straps counted on
  the held one; and its `roll` where it has one, as `turned` is shown.
- **`describe`**: one line of totals for the findings ("2 cables cross a
  body; 1 tray is full"), so an agent that only describes the rack still
  sees fault 1, as the session behind #949 did not.

The site prints these in `cableText`, as it prints `routed` and `slack`; that
is the site check of step 2, a test that an agent reading `inspect` on a cable
through the tray floor is told so and told what to do.

## 9. What this does not do

- Straps through `ties` are not drawn for single cables, and on the resting
  face they are not counted either; on the held face they are counted and
  not drawn (2.3). The bundle straps of #921 are unchanged (decision 3).
- Slack on the held face of a tray.
- The vertical mounting of #550 beyond the `roll` key and its convention:
  where a turned box stands across the opening, its mount kit, and the facts
  that differ with the mounting (lug size, cable exit) are that issue.
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
   finding for a hand route through the tray; the same on fixture 2 of 4.5 (a
   lacer on each switch, cables running manager, lane, manager), with no
   crossing on its automatic routes; the `rack.json` test for
   `solids`; the site routing checks re-run; a changelog fragment that says
   routed lengths change.
3. **Trays and resting.** The `tray` and `trays` schema, ring `depth`, `sill`
   and `aperture.at`, lint, the compiled `data-class="tray"`, `trays` in
   `rack.json`; the FHD-CMP5DR tray and the snap-in ring stated (a minor
   each); rule 7 narrowed in the modelling guide; then resting and `DRAPE` in
   the kit. Gate: `./build.sh --device fhd-cmp5dr`; `devicelock.py` checked
   against the lock on main, with the versions bumped, before `--update`; a review
   page of source against render, and kit tests that a cable on the tray runs
   at floor height plus its radius and that no span passes below a surface;
   that a cable on the held face runs at the plate less its radius, sags
   between two used tie slots and never below the strap line, and crosses no
   solid; and that a leg from above straight onto the held face is still a
   `crosses-body` finding.
4. **Slack storage**, on rack file version 4. The `slack` and `lay` keys are
   reserved in the version-4 schema by the hosting step of the rack products
   note (section 7), with `lay` in its shape of section 7 (`position` and
   `face` each optional) and `roll`, which that step fits by its rolled box
   (7.1); if that step has not landed, this step brings version 4 with all
   its keys. Then `cable.slack`, the length, the 2D loop and 3D coil, the
   `slack` and `straps` schedule columns and the BOM notes, slack refused on
   a held face. If version 4 has already landed, its
   guard of section 7 (stored length kept, tray removal refused) is replaced
   here by the real reading. Gate: a version-4 round trip, a version-3 page refusing
   a version-4 file, the export tests, and the PR naming its one-way doors.
5. **Lay order**, after #922 and portrayal-site#142 have settled: positions
   by entry side, local patches along the tray, side-to-side patches in the
   middle band, the gutter chosen from both ends, layers, bundles as one
   position, `cable.lay` with `face`, the two faces of a tray and the
   automatic face, the held-face straps counted, the forced-crossing count,
   the full-tray warning, the ranking of `managerOf` (4.5), and `roll: 180`
   drawn, fitted and routed through, with resting in the frame as mounted
   (3.1), if #550 has not already built it. Gate: kit tests on the three
   fixtures of 4.5 (the fixture of #949, one FHD panel with an FHD-CMP5DR
   lacer, a switch above it and a switch below it, cabled to bays 2 to 4;
   a lacer on each switch as well, with its variant of D-ring panels
   standing alone over and under the switches and its stack with a manager
   under each switch; and a pair of FHD-CMP5DR back to
   back, the lower one with `roll: 180`) and on a grid of ports, in which
   **the test computes the forced set itself**, per face of each pathway,
   from the face each cable lies on and its ends there (rail-side,
   front-edge and gutter) by the interleaving rule of 4.1, without the kit;
   asserts that the kit count and pairs EQUAL that set (for the fixtures, the
   sets 4.5 gives: a-e, b-c and c-f; h-k and i-k; n-o); and asserts that the
   laid cables cross exactly at those pairs and nowhere else, per face: two
   cables on one face meet only at a forced pair, and in 3D no two tubes on
   different faces meet. The test does not project to a plan, where a run
   passing under a held face lies across it (b across d in plan, in fixture 1). Every
   fixture has forced crossings, and the test asserts each count is not zero,
   so an empty count cannot pass. Fixture 1 also asserts that d lies on the
   underside, that pinning it to the top adds b-d as a crossing made by
   hand, that it gives no `crosses-body` finding, and that b runs below the
   strap line of d by its radius and `CLEAR`. **The case that cannot drop**
   is a copy of fixture 1 with three changes: d is a bundle of twelve 3 mm
   cords taking one position (11.6 mm across at `BUNDLE_PACK` 0.8, well
   inside the fill bound of 2.3, so no full-tray warning); b is a Cat6A cord
   (7.5 mm, R 30 mm, four times its diameter) from a port 6 mm below the top
   of S-dn; and S-dn has `setback: -70`, its face 70 mm proud of the rail.
   Worked by hand, in mm from the top of S-dn: the strap line is 1.5 - 11.6
   = -10.1; b needs its centre at or below -10.1 - 3.75 - 5 = -18.85, a drop
   of 12.85 from its port at -6; g is 89.7 - 70 = 19.7, so a single arc of
   R 30 allows 30 - sqrt(900 - 388.1) = 7.37. It falls 5.48 short, so the
   test asserts exactly one `crosses-body` finding for b, with T as `part`
   and `underside` as `face`, and the new obstacle is exercised. Fixture 2
   asserts that each end takes its own manager; its variant that S-up takes
   D1 and S-dn takes D2; and its stack that the upper row of S2 takes Ma,
   the lower row Mb, and a middle row Mb. Fixture 3 asserts the resting in
   the hanging rings and the fit of the rolled manager in its one U. A
   browser check does the same in 3D.
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

Three additions were made on 2026-10-09, after those decisions, and this note
was amended to carry them:

1. **Underside routing.** The underside of a tray can carry cables, held by
   straps through its tie slots; a tray with no tie slots offers no
   underside. The automatic route uses the face nearer the port of the
   cable, a face can be pinned by hand and is saved in `lay`, and each face
   has its own lay order. Underside straps are counted, one per tie slot
   used; top-face straps are still not drawn; slack goes on the top face only
   (2.3, 3, 4.1, 5, 7 and 8). The addition speaks of trays mounted the usual
   way, so this note reads its top as the face that looks up, the resting
   face, and its underside as the face that looks down, the held face; on a
   tray turned over (addition 3) the two names and roles part, and the rules
   follow the roles.
2. **A cable manager per device**, one in front of each switch, with cables
   running manager, lane, manager, is a second fixture for the lay order
   beside the fixture of #949 (4.5, and steps 2 and 5 of section 10).
3. **A flipped manager.** Two managers back to back, one mounted upside
   down, give D-rings on both sides. That needs a vertical-flip orientation
   for rack items, a rack file version 4 key designed with the rotated
   mounting of #550, and resting and lay order worked in the flipped frame,
   so a cable in an upside-down ring rests on the band now below it (3.1,
   4.5 and 7.1).

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
| cable `slack` (`item`, `via`, `value`, `unit`, `form` with `coil`, `serpentine`, `spool`) and cable `lay` (`item`, `via`, `position`, `face` with `top` and `underside`, at least one of the last two) | rack file version 4 | saved rack files carry them; an older page refuses a version-4 file, and the schema label is never reused |
| the word position, and position 1 counted outward from the part a pathway is fixed to (the host side of a tray, the plate of a ring or a duct; for a ring along y, a second layer from the side nearer the rack centre line) | rack file (`lay`), kit, `inspect` | a saved hand lay names a position by this count |
| the forced crossing: a pair whose ends (rail-side, front-edge, gutter) interleave round the pathway, and the count of them per pathway | kit, `inspect`, agent output | agents and tests read the count and the pairs |
| item `roll` with `90`, `180` and `270`, clockwise as seen in the elevation of its face, applied after `face` and `turned`, fitted by its rolled box (7.1) | rack file version 4, kit fit and drawing | saved rack files carry it; #550 builds its quarter turns on the same key and convention |
| `top` and `underside` named in the frame of the part, the resting and held roles following the item as mounted, the held face offered only with `ties` or a ring on it, and the automatic face the one nearer the port (2.3) | kit, rack file (`lay`), `inspect` | a saved face pin names a face by this name, and routed lengths depend on the choice |
| held-face straps counted one per tie slot used, the face named by role and name in the export text, the `straps` column of the cable schedule after `slack`, and the strap note per tray in the BOM | exports | a reader takes the column by its header and matches the note |
| the export note and the DCIM comment line of a rolled item ("Mounted upside down.", "Mounted rotated 90 degrees clockwise, as seen from its face." or the same with anticlockwise) | BOM notes, DCIM exports | a reader of the notes and an imported comment match the text |
| the ranking of `managerOf` (hosted, then a standalone manager, with its tie-break by port row, then a manager on a neighbour, then a neighbour with guides) | kit | automatic routes of saved racks follow it, and their routed lengths with them |
| the version-4 table of the rack products note gaining `states`, `readings`, the PDU bracket key, `slack`, `lay` and `roll` | `docs/rack-products-design.md` section 9, rack file version 4 | one bump carries them all; a key left out needs a version 5 |
| the stored slack counting in the routed length | kit | a saved routed length and stock size depend on it |
| routed lengths changing on saved racks: detours, cables resting at the floor and at the ring sill, positions in the lay, the face of each tray, slack | kit | stored routed lengths and stock sizes move on the next measure; an ordered stock length may no longer match |
| `crosses-body` (with `part` and, for a held-face stack, `face`), `unheld` and the tray findings, `bodyFindings` | kit API, agent output | agents and pages read the kinds |
| `cable.slack`, `cable.slack.clear`, `cable.lay` (with `face`), and `roll` on `patch` | kit commands, offered to agents | agent sessions and saved prompts call them by name |
| `inspect` fields: `crosses` and `rests` (with `face` and the tie slots used) on a cable route, `slack.stored`, the tray block of a device per face, and `roll` on a device | kit queries, agent output | agents and the site read them by name |
| the crossing and tray lines in the export notes | exports | a reader of the notes matches them |
| the `slack` column of the cable schedule, after the last column | export | a reader takes it by its header |

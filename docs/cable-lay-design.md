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
  expanded into the faces a cable enters and leaves by (#930), from each
  plug's reach point since kit 0.13.0 (1.5), and since kit 0.17.0 with room
  at each turn for the cable's bend radius (3.4). The routed
  length is that polyline plus the end allowance of its media at each end
  (1.6; 0.15 m for every cable before kit 0.16.0), rounded up to a stock
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
  ears) and each web, as boxes. A cable passes its rings through their
  openings (1.2); since #968 the loop round an opening is solid where the
  ring's contract says what of it is (3.3).
- **A zero-U part that carries a lane** (a vertical duct, #926) is a pathway,
  not a solid: a lane waypoint at a U it spans runs through its channel, so
  only its walls and back are solid, derived as a sheet part is. A zero-U part
  that carries no lane (a PDU) is its envelope, as the fit check already takes
  it. **It stands in the gutter, so the lane moves outboard of it:** at the
  units it spans, the lane beside that upright runs in a gutter as wide as the
  usual one just outside the part, and a cable runs beside it, not through it
  (1.3). Outboard, because inboard of it is the rail and the ears of every
  device fixed there, and moving the lane in front of it would take it off the
  rail plane every port leg and every front-to-back crossing is measured in
  (and, for a rear PDU, outside the back of the rack). The rule assumes the
  part stands `where: outside` (against the upright's outer face, as every
  zero-U part does today; rack products note section 3); a part in a
  cabinet's `inside` channel, between the posts, needs its own rule, made with
  the hosting step of that note.

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
  On a zero-U part (#992) the tube must also fit: the hole's box is taken
  less the cable's radius across the hole, so a centre line 2 mm inside the
  edge is a crossing for a 6 mm cable. The box is not shortened along the way
  through the plate.

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
tolerance it uses for every surface a cable rests on. The tube touching a
plate the cable rests on is contact, not a fault (1.4); a plate it does not
rest on is left to the lay work (#986).

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
   clear, and its leg is left and reported (1.4) with the held face named.
   The clearance is measured vertically at g; `CLEAR` absorbs the small tilt
   of the arc there. This obstacle lands with step 5 of section 10, not step 2:
   it needs cables laid on a held face, which step 5 brings.
2. **Round the end.** A leg that would cross a body side to side goes past its
   end, into the gutter, which is where the automatic route already goes.
3. **Front to back by a side lane.** A cable whose ends are on opposite faces
   goes through the lane beside a post, as the automatic route does today.

The lane beside a zero-U part that carries none runs outboard of it (1.1).
**A leg that lands on the outward face of a zero-U part (P-0037)** is the one
into a PDU outlet's reach point: an end of the leg stands out in front of the
face and over the part, and the other is inboard. It is gone round first past
the part's side that faces the rails, in one plane at the outlet's height (the
plane stands the bend room from the reach point), so the cord arrives at the
outlet from beside it; the ways below are the fallbacks, and a leg that lands
on no face keeps them as they were. The crossing finding (1.4) does not count
the body of the part a cable ends on, at the plug leg of that end. A four-post
offers a lane for a route by hand on the upright's centre line, `left-rear-inner`
and its three, between a rail and such a part (`route.js` `INNER`): the automatic
route and the detours take the four gutters alone, and the lane has no depth, so
the turn into the plug from it is judged as it is for any lane.
**A zero-U part is gone round on its back first**, the side that faces into
the rack, where the side channel is; a cable from a port inboard of it turns
the corner there (along the rack to the gap beside the part, back past it,
across, and out). That corner's leg into the rack passes through the footprint
of the upright the part stands against: a known approximation, since the
uprights are not solid to the router and the part stands against the
upright's outer face with no gap (`STANDOFF` 0, no source dimensions it).
4. **Over its outward face**, where a PDU's plugs stand outside the frame, is
   a fourth way, for a zero-U part only, and the last resort: tried only when
   the three above do not clear it.

A detour that meets a second body goes round it the same way, to a bounded
depth, and the result is pulled taut.

**A detour leaves its turns room (#973, kit 0.17.0).** A way round turns the
cable where each end's move meets the plane, and where that move starts when
the end is itself a corner, so a move shorter than two bend radii leaves
neither turn its radius: on the reference rack the cord came back in from in
front of the tray's edge to its ring's approach point along 42.8 mm, shared
by two right angles that need 25 mm each. So a plane an end reaches by a
shorter move stands two installed bend radii from that end (`detour`'s
`room`), further out than the cable's radius and `CLEAR`; an end already
beyond the plane, and a plane a side lane sets, are left alone. Where a
detour is pulled taut its turn can be wider than a right angle, and a corner
at a detour point still short of room is offered two and a half and three
radii (3.4). The plane only moves away from the body, so what it cleared it
still clears; and in each tier the ways with room are tried first and the
ways as they were only when none resolves, so a body that leaves no room is
still gone round by the same preferred way, and the short leg is a finding
(3.4), not a different route. Two further offers came with #1026 (3.5): a
detour round a plate that is not pulled taut, and the way up behind a tray
for a plug that ends behind its back edge.

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

**Contact is not a fault where the cable rests (#992).** A tube that touches
a plate the cable rests on is contact, and the check does not fail on it: a
tray floor's resting face, where the cable lies on the plate, and its held
face, where it lies against it from below (2.3). That is the same contact
1.2 calls lying against a plate. A tube inside a plate it is not resting on
is not accepted by this rule: whether the lay should keep it clear is the
question of #986, and nothing here settles it. The check lives outside this
repository; this note is the rule it is held to.

### 1.5 The plug's reach

Decided 2026-10-09 for #960; built in kit 0.13.0.

A cable leaves the far end of its plug, not the port face, and runs straight
out of the face for the plug's depth before it can turn. Before 0.13.0 the
kit started each route at the port face, so a cord from a switch below a
tray rose to the tray's ring straight from its port, behind the floor's
front edge, while the 3D drawing started its tube at the plug's end, in
front of that edge, and took it round. Drawn and measured disagreed, and a
cord measured just under a stock break could be ordered short.

- **Each route's first and last leg starts at the reach point**: the port's
  point moved out of the face it is seen from, along the face's normal (+z
  at the front, -z at the rear, whichever rail plane or far panel the port
  is on), by the plug's reach. `routePath` puts it after the port and before
  the far port as a point `at: 'reach'`, with its `end`. A reach of 0 adds
  no point.
- **The reach** is the page's `ctx.plugReachOf(end, cable)`, in mm, when it
  gives a number of 0 or more. The page reads it from the seated plug: the
  `z` of relief.js `cablePoints`, which is the far end of the plug's boot or
  stub, measured from the face of the part the plug seats in, plus whatever
  that part stands out (an optic in a cage). Otherwise it is `PLUG_REACH` by
  media, the cable's own plug and boot as the library models them standing
  out of the face they seat in: LC fibre 27.6 mm (generic/lc-plug@2 `out`
  12.5 and common/lc-boot@1 15.1), copper 39.4 (generic/rj45-plug@1 13.0 and
  common/rj45-boot@1 26.4; it assumes the boot abuts the plug's rear, and an
  overlapping boot reaches less: the boot's 11.9 x 8.13 opening slides over
  the 11.68 x 7.93 plug body, so the figure likely errs long by a few mm), a
  DAC or an AOC 64.8 (generic/qsfp-cable@1, whose cable point is the far end
  of its 30 mm stub, the straight run before the first allowed bend, a
  drawing figure; generic/sfp-cable@1 gives 68.7, but its stub is an
  estimated reading, a gap to re-read before it is relied on), and a cable
  with no media the copper figure, as
  its diameter takes the copper one. The kit does not know what a port
  holds, so the default leaves out an optic's standing-out; only the page
  can add it.
- **A cable can run on past it.** The reach is the least a cable runs
  straight out of a face. Where its first turn needs more of a leg than the
  plug gives (3.4), it runs on straight to a lead point, `at: 'lead'` with
  its `end`, and turns there; the reach point stays where the plug ends.
- **Detours and ring passes are measured from there.** The legs out of the
  reach points are legs like any other: section 1.3 takes them round what
  they cross, so a cord that must clear its plug and then turn up past a
  tray's front edge is measured that way, and a ring's pass and hold
  (section 13 of the managers note) count a reach point as its port, which
  it shares the x and y of. A leg from a port to its reach point that
  crosses a body (a plug behind a deep shelf) is a `crosses-body` finding at
  that port.
- **The plug outside the face is counted once.** (In 0.13.0 the end
  allowance, 0.15 m an end, stayed as it was, as dressing slack; since
  0.16.0 it is the part of the plug inside the port and the maker's short
  tolerance, with a temporary dressing allowance beside them, section 1.6,
  which this paragraph's reasoning still holds apart from the plug
  outside.) The plug was
  always in the path: before, the first leg ran straight from the port face
  to the first waypoint, and the plug lay along the start of it. The reach
  does not add the plug's length; it bends that leg into a dog-leg, straight
  out of the face for the plug and only then toward the waypoint, so a
  length grows by what the dog-leg adds over the straight leg (11 to 28 mm
  a cord on the reference rack, not two whole plugs), and by any detour the
  new leg needs. Nothing adds the reach a second time: the length is the
  path's points and the two allowances, and a test holds it to that.
- **What a drawing does.** A drawing that starts its routed tube at the
  kit's reach point, and runs its first and last legs from there, follows
  the kit's legs; taking those legs round the bodies again finds nothing to
  add. The site's 3D scene today starts each tube at the plug's own cable
  point and runs a further `LEAD` (40 mm) and `REACH_STEP` per row straight
  out before its first bend, and its `clearLegs` takes those legs round the
  bodies; it is a site follow-up to start the bend at the kit's reach point
  (path point 1 and the one before last) and pass the page's cable-point `z`
  as `plugReachOf`, so drawn and measured agree.

On the reference rack of #949, every automatic route grows by 11 to 28 mm, and
seven cords pass the 0.5 m break: c7, and c9 to c14 from the lower leaf. With
a QSFP-LC optic in each leaf port (a reach of 47.6 mm), the lower leaf's
eight cords go round the tray's front edge and measure 0.63 to 0.67 m.

### 1.6 The end allowance

Decided 2026-10-10 for #962; built in kit 0.16.0.

The kit added 0.15 m at each end of every routed cable before rounding it
up to a stock length. The figure came from the site's early routing spec,
with no stated purpose and no source, and on the reference rack it was most
of each measured length: fifteen of sixteen OM4 cords rounded up to 1 m
where a 0.5 m cord leaves about a quarter of a metre spare.

**The allowance covers only what is physically there and not in the path,
by media.** A routed path runs from port face to port face, the plug
outside the face included (1.5). A stock cord's nominal length takes in its
plugs, tip to tip, unless its maker measures it otherwise. So each end adds
the part of the plug inside the port, where the nominal length includes it,
and half of how much shorter than nominal the maker allows a cord to be.
A plus tolerance only adds slack, and adds nothing. Service loops, dressing
slack and re-termination headroom are not in the table: they are explicit
slack held in a tray (#949 step 4, section 5), where they can be seen. Bends
were never in it: a polyline corner is longer than the radiused bend a real
cable makes.

**Until a tray can hold slack, a dressing allowance of 0.1 m an end is added
on top, for every media.** Step 4 is not built, so the table alone would
size every cord with nothing to dress it by. The dressing allowance is
temporary and is not a measured figure: no maker's document gives it, and it
is there by the decision of 2026-10-10. It is one named constant in
`rack/route.js`, `DRESSING_ALLOWANCE`, apart from the table and not
exported, so that the table stays what the sources say; step 4 removes the
constant and its one use, and every routed length drops by 0.2 m again.

`END_ALLOWANCE_BY_MEDIA` in `rack/route.js` is the table, in metres an end
(named so from kit 0.18.0, so that it cannot be taken for what a length adds).
`endAllowance(cable)` is what a length adds at an end, the cable's figure
from the table and the dressing allowance; `routePath` returns it as
`allowance`, and `pathLength` adds it at each end (a path built by hand
without one takes a cable with no media's). The table:

| media | an end | inside the port | short tolerance |
|---|---|---|---|
| LC fibre (`os2`, `om3`, `om4`, `om5`) | 13.1 mm | 13.1: generic/lc-plug@2, whose rear stands 25.6 behind the housing's front with 12.5 out of the bore (an estimate within the 12.2 to 13.97 that SENKO's DS-LC-000004 drawing allows) | none: the FS Fiber Patch Cables Datasheet, Cable Length Tolerances, states every duplex and simplex length +x/-0 (+10 cm/-0 cm from 0.5 m, +15 cm/-0 cm from 5 m) |
| copper (`cat6`, `cat6a`), and a cable with no media | 34.5 mm | 9.5: generic/rj45-plug@1, 22.48 long (CommScope 2843005) with 13.0 out of the jack (an estimate resting on the latch) | 25, half of 1 per cent of a 5 m cord. FS, Panduit and Siemon state no copper cord tolerance. Belden's CAT6+ modular cord (C601106001) states +0.2/-0 m to 2 m and Brand-Rex's 10GPlus Cat6A patchcord (GD056534v18) a bracketed length of +/- 1 per cent; the sources disagree, and the one that allows a short cord is taken, at 5 m, the longest cord a rack's own routes come to as a rule |
| DAC (`dac`) | 25 mm | none: the FS 10G SFP+ DAC datasheet dimensions L between the two heads, so the heads, the part in the cage included, come with the cord; the head's 19.8 out of the cage, which the path counts, is left as margin | 25, half of the +/-5 cm that datasheet states for lengths to 5 m (section VII, the L / TOLERANCE table) |
| AOC (`aoc`) | 52.4 mm | 52.4: generic/qsfp-cable@1, the head's stop in the cage (SFF-8661 Figure 5-1), the same head the reach reads. No maker held says how it measures an AOC (FS's AOC drawing gives no L), so tip to tip is assumed | none: L-com's AOCQSP28100 drawing states +x/-0 at every length |

With the dressing allowance, an end adds 113.1 mm for LC fibre, 134.5 for
copper and a cable with no media, 125 for a DAC and 152.4 for an AOC.

What the table does not see. The kit does not know what a port holds: an LC
cord into an optic's receptacle is taken to enter it as it would an
adapter's, and an SFP head (47.5 in the cage, SFF-8432) at the QSFP
figure. MPO cords have no media of their own in the kit yet; when they do,
the FS MTP/MPO jumper datasheet states no length tolerance, and one has to
be found.

**What rests on an estimate, or on no source.** Read the figures with this
list beside them:

- The LC figure, 13.1 mm, is a drawn length less an estimate: the 12.5 mm
  of generic/lc-plug@2 that stands out of the bore is not dimensioned by
  any source held, only bracketed (12.2 to 13.97, SENKO DS-LC-000004).
  Across that bracket the figure is 11.6 to 13.4.
- The copper figure's 9.5 mm inside the jack is the CommScope plug's 22.48
  less 13.0 out of the jack, and the 13.0 is an estimate that rests on
  where the latch sits, not a dimension.
- The copper figure's other 25 mm is a reading, not a statement about the
  cord bought: half of a 1 per cent tolerance that one maker (Brand-Rex)
  states, taken at 5 m, where three makers state none and one states no
  minus tolerance at all.
- The AOC figure assumes its length is measured tip to tip; no maker held
  says so.
- An SFP head is taken at the QSFP head's depth (52.4 for 47.5).
- The dressing allowance, 0.1 m an end, has no source at all.

When the library's plug parts are measured, the table follows them.

**Lengths change on saved racks.** Against 0.15 m an end, a routed length
is 73.8 mm shorter for LC fibre, 31 for copper and a cable with no media,
and 50 for a DAC; an AOC's is 4.8 mm longer. (By the table alone, without
the dressing allowance, they would be 273.8, 231, 250 and 195.2 shorter.)
On the reference rack of #949 every cord is 73.8 mm shorter: c1 to c8 measure
0.422 to 0.495 m and are 0.5 m cords (seven of them were 1 m cords; c4 was
0.5 already), and the lower leaf's c9 to c16 measure 0.547 to 0.592 and stay
1 m cords. Seven of the sixteen change stock size. On the generated racks of
#960 and #968 (3,120 cables of mixed media, four-post and two-post, with and
without zero-U PDUs), 221 move down a stock size and one, an AOC, moves up;
by the table alone 1,326 would move down. A stored routed length and stock
size move the next time a page measures them; an entered length is never
touched.

The stock size is the first that holds the measured length, so a cord can
round up with little to spare over its measure: 218 of the 3,120 have under
50 mm (217 did at 0.15 m an end), and five of the reference rack's (c1 39.5, c2
48.7, c5 35.0, c6 29.7, c7 5.0). The measure has the dressing allowance in
it, so each of those still has 0.2 m and more over its path and plugs; when
step 4 takes the allowance away, what is spare is what a tray is given to
hold.

A cord up to 10 mm short of full end play keeps its stock size
(`BREAK_TOL_M`, 0.01 m): one twentieth of the end play, and more than the
spread of the LC plug depth estimate at two ends (1.8 mm each). Its source
and the figure's confirmation, 2026-10-18, are in decision 5 of
`rack-file-v4-design.md`; the rule is written against end play, not the
dressing allowance, in the same note's section on lengths.

When the dressing allowance is removed, the 10 mm tolerance at a stock break
stays, and it applies to the bare length: the measured length with no
dressing allowance in it. Decided 2026-10-18.

### 1.7 A span in front of other ports (#1013)

With no horizontal manager, a cable runs from its side lane to its port as a
free span across the faces of the devices between, over their ports. It
crosses no body, since only envelopes are solid (1.1) and the span is in
front of the face, so `bodyFindings` and `ringFindings` say nothing: on a
rack of twelve switches and no manager, with eleven cords bundled down one
lane, every cord crossed a face diagonally and nothing was reported.

**The finding.** A path's `covers` lists each port a span passes in front of,
as `{kind: 'port-behind-span', cable, item, path, view, between: [from, to],
at: [x, y, z], judged, estimated?}`; `coverFindings(rack, ctx, nameOf)`,
beside `bodyFindings` and `bendFindings`, gives one finding a cable, `{kind:
'span-over-ports', cable, count, ports: [{item, path, view}], between,
judged, estimated?, text}`, with a sentence (`coverFindingsOf` in
`kit/rack/route.js` writes it). It has three parts: the ports by device ("c10
crosses in front of port-2 and port-4 on MGMT-SW1"), the stretch of the route
the span is ("between left-front U42 and its port on MGMT-SW1"), and the
advice (below).
A device with more than six ports covered has its first five named and the
rest counted. It **warns and never refuses**: on a rack with no manager it
is the truth about the rack. The two codes are a port (on the path) and a
span (the finding), and share no word but `port`.

**Which spans.** Only a span with no pathway at either end is judged: from a
port to a lane, or from port to port (a short jumper that hangs). That is the
span no manager carries, and the one the advice fits. A leg into or out of a
ring, a duct or a tray is not judged: it is where the cord is meant to run,
and a cord between a port and the first ring of its manager crosses a port or
two on any rack. A plug is not judged either, and a cable's own two ports are
never listed.

**Which ports.** A span covers a port when, seen square to the panel, it
passes through the port's box grown by the cable's radius, while it stands in
front of that panel and no further out than 100 mm. That figure is an
estimate: the longest plug the kit knows stands 64.8 mm out of its cage, and
the rest is room to hold it; no source states one. The spans judged stand
within a plug and a bend radius of the panel, well inside it. A port on a
neighbouring device counts as one on the cable's own: a span that sags into
the face below covers the ports there.

**Beside its own port is not in front of another.** A cable leaves its plug
straight and turns within its bend radius, so whichever way it goes it passes
over the ports that stand within that radius of its own. The stacked partner
of its port is always one: the same column, the other row, 11 to 14 mm away
on the faces modelled so far. A neighbour or two along the row are the
others. No manager moves a cord off them, so reporting them is noise: on two
48-port switches patched port for port, one above the other, every one of the
48 jumpers was reported for the other-row port of its own column and told to
add a manager. The rule:

> a port on the same panel of the same device as one of the cable's own two
> ports, whose box comes within the cable's installed bend radius of that own
> port's centre, is not listed.

The distance is from the centre of the cable's own port to the nearest point
of the other port's box, in the plane of the panel. The radius is the one the
lay turns the cable in (`ctx.bendOf(cable)`, else its media's): 24 mm for a
Cat 6 cord, which takes in the stacked partner and one column either side at
a 14.6 mm pitch; a stiffer cable turns wider and is beside more. A span that
passes only such ports is not reported at all. What is left is a span that
runs on across a face to reach its port, which is what a manager cures.

Counted, before the rule and with it (cables reported, of those routed):

| rack | before | with the rule |
|---|---|---|
| the reference rack of #949 (a lacer between its leaves) | 0 of 16 | 0 of 16 |
| the 60 generated racks of 3.4 | 69 of 1,803 | 67 of 1,803 |
| eleven cords down one lane, no manager, cabled ports only | 9 of 11 | 6 of 11 |
| the same, every port listed (`portBoxesOf`) | 11 of 11 | 11 of 11, ten of them over 13 to 15 ports |
| two 48-port switches port for port, one above the other | 48 of 48 | 0 of 48 |

The same 48 patched one column along are not reported either (each is still
beside its own ports); four columns along, 20 of the 40 are, for the columns
the hop crosses; and with the switches three units apart, so that every cord
goes to the gutter, 20 of the 48 are.

**The advice fits the span.** One that runs between a lane and a port is told
to "add a horizontal cable manager above or below" that port's device "to
carry it to the gutter". One that hangs from port to port has no gutter to go
to, and is told to "route its hop from A to B through a horizontal cable
manager beside either".

**What was judged.** A finding says which ports were there to judge: `judged`
is `all` when the page listed every port of every device (below), and
`cabled` when only the ports that hold a cable were known. With `cabled` the
sentence ends "Only ports that hold a cable were judged.", and the findings
line of `describe` says the same in its bracket, so a reader does not take a
short list for a clear face. `estimated: true` marks a finding that rests on
a port taken at the estimated box; it is a field and not a clause, since the
sentence is long enough.

**What the context carries.** The routing context places a port only when it
is asked for one (`portX`, `portY`, by a cable end), so the kit knows where
the cabled ports are and nothing of the others. Two sources, then:

- every port that holds a cable, from `portX` and `portY`, with a box of 12
  by 10 mm (an estimate, about the opening of an RJ45 jack or an SFP cage);
- **`ctx.portBoxesOf(itemId)`**, a new reader, optional and additive:
  `[{path, view, x, y, w?, h?}]`, every port of the device, cabled or not,
  `x` and `y` the centre of its box where `portX` and `portY` put a port, `w`
  and `h` its size in mm (the estimated box when left out). A page that reads the
  compiled faces has these boxes already. A reader that throws, and an entry
  it cannot place, are left out.

Without the reader a finding is still true and can miss a port with no cable
in it; a cable that covers only such ports is then not reported. The list is
read once per rack and context, as the solids are.

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
  35.1 mm below the plate on the FHD-CMP5DR: section 3.1.) Between two
  straps it sags a little, by the drape of its type over that span, and never
  below the **strap line**, the bottom of the strapped stack at that point.
  The stack gathers where the straps are: under the pair of slots a strap
  passes through, 89.7 to 98 mm forward of the rail on the FHD-CMP5DR, an
  8.3 mm strapped width, so a held face lays few cables side by side and
  stacks the rest; a position wider than that, such as a bundle, starts at
  the back edge like any other and overhangs forward. A
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

### 3.2 As built

Step 3 of section 10 is built in kit 0.14.0. Where this note did not say how,
the build chose as follows; each is in `kit/rack/resting.js` or
`route.js routePath`.

- **Where the kit reads a ring's opening.** rack.json carries the openings of
  the rings that stand on a tray's floor under that tray, as `rings` (each
  `{via, run, box}`, the clear opening in the frame of `solids`), derived
  from the compiled plan as the floor is: a ring's `sill` and `aperture.at`
  compile to `data-guide-sill` and `data-guide-aperture-at`, and the height
  it stands on is the floor's. A ring that stands on no tray (the 1U D-ring
  panels of section 6) carries no opening yet and keeps the point its drawing
  gives; placing those is for step 6, with their data.
- **Across the opening.** A cable on its own lies at the side of the opening
  nearer the rail the part is fixed to, position 1 of section 4, and on the
  held face at the rail side of the strapped width. The positions of several
  cables are step 5.
- **How far a free span sags.** The 3D drawing's catenary, `20 + 0.3 L` for a
  span L mm across the face, scaled by `DRAPE`, and no deeper than
  `CURVE L^2 / (R / DRAPE)`, with R the installed bend radius and `CURVE` the
  catenary's own (0.078): the tightest bend of the curve, at its ends, is
  then no tighter than R over the drape, so a stiff cable takes a wider
  curve. Where it would pass below a surface it drops onto it from each end
  in two bends of that radius (a straight fall between two quarter bends
  where the drop is deeper than twice the radius) and lies on it, and so a
  stiff cable lands further along. A span shorter than the two drops leaves
  room for keeps its catenary, clipped onto the surface where it would pass
  below it. **Since kit 0.17.0 (3.4) no hang is laid tighter than the cable
  may bend**: the catenary is sampled evenly along its arc, a drop is laid
  as the two points where its bends' tangents meet, with a level lead before
  it, and a hang that would leave a corner short of the bend radius, one of
  its own or one where the span meets what holds it, is offered shallower
  and then not laid. Until then the clip could turn tighter than the radius,
  and the samples, evenly spaced across the face, stood 0.3 to 15 mm apart
  along the cable.
- **What is not a free span.** A plug (port to reach point), a ring's inside,
  a lane's run along the frame (lane point to lane point), a tray's stretch,
  and a leg into or out of a detour point: a cable taken round an edge is
  dressed round it by hand (1.3) and stays taut, clear by what the detour
  keeps. A sag that would carry a cable into a body its straight leg did not
  cross is not laid; since kit 0.17.0 a shallower one that clears the body
  is, and only where none does the leg keeps its chord.
- **The held face in this step.** Nothing in a version-3 rack file can pin a
  face, and the automatic face is step 5, so a cable lies on the held face
  only where the page pins it, through `ctx.trayFaceOf(cable, {item, via})`,
  and the tray has a tie slot along the stretch. The slots that hold a cable
  along the run are the ones long along it, a strap going down one of a pair
  and up the other; a cable on its own is its own stack, so between two
  straps it sags at most its own radius.
- **Configurations.** rack.json reads trays off the default configuration's
  plan, as it reads `solids`, so `traysOf` places those trays for every item
  whatever its configuration, as `solidsOf` places its solids; a
  configuration whose top face is drawn as a differently named view cannot
  declare `trays`, and `cable.route` refuses a tray waypoint on a configured
  item when the page gives its guides (rack.json lists no pathway of a
  configuration but the default; without the page's guides such a waypoint
  is not judged, as no pathway of a configured item is).
- **What `inspect` says.** A cable's route gains `rests` (section 8): each
  ring whose sill holds it, each tray it runs along or lands on (with the
  face, its role, and on a held face the tie slots it uses) and each body a
  free span comes to rest on. Positions are step 5's.
- **The snap-in ring's sill** was read off the ring-profile view at 5.6 mm,
  where 2 mm had been estimated: a cable in a ring hanging from the
  FHD-CMP5DR rests 5.6 + 29.5 = 35.1 mm below the plate, 38.1 below the top
  of U12, the figures section 2.3 and fixture 3 of 4.5 now give.

### 3.3 Rings are solid (#968)

Built in kit 0.15.0. Until then a ring was an opening and nothing else: its
legs, hook and bar were in no list of solids, so a route could run through
them and nothing saw it. On the reference rack every upper cord came down into
its ring through the rear leg, and every lower cord, taken round the tray's
front edge to the ring's face, ran along the face and grazed both legs.

- **What of a ring is solid.** A ring's `guide` gains three optional keys,
  read off the ring-profile view: `wall`, how thick each leg is beside the
  opening in the plane of the loop; `height`, the top of the loop over its
  base; and `slit`, `[from, to]` out of the base, the gap in the far leg of
  an open loop. They compile to `data-guide-wall`, `data-guide-height` and
  `data-guide-slit`, and L138 holds each inside the part. Where a ring states
  them with `sill`, `depth` and `aperture.at`, rack.json's `solids` carry its
  loop as up to five boxes, each the band along the run: the leg either side
  of the opening, the bar over it, the seat under it up to the sill, and,
  where the far leg has a slit, the leg below it and the hook above it. Each
  is named `ring/<id>/<part>` (`rear-leg`, `front-leg`, `hook`, `bar`,
  `seat`; `left-leg` and `right-leg` for a loop that stands across the
  device), so a finding says which part was hit. A ring that does not state
  them is open, as before. Only a sheet part's rings are added: a box
  device's envelope is solid whole until step 6.
- **The slit is not a way through.** On the snap-in ring it is 2.2 mm, less
  than a cord: a cable is pressed in through it by flexing the hook, and
  then lies in the opening. The solids leave the gap open, as drawn; no
  route is laid along it.
- **A ring's parts are met by the tube.** A cable passes a ring close by on
  purpose, so `legCrossings` takes each part grown by the cable's radius, and
  a leg that would graze one crosses it; `detour` goes round the grown part.
  A cable on the sill against the rail-side leg runs along the faces of the
  grown parts and crosses nothing. A zero-U part is met by the tube as well:
  with the approach point a few mm further along than the ring's face, a leg
  from a lacer's end ring to the lane beside a zero-U PDU cleared the PDU's
  corner by a fraction of a millimetre with its centre line and ran its tube
  across the outlet face, which rule 4 of 1.3 keeps for the last resort.
  Every other body is met by the centre line, as in 1.2. Meeting every body
  by the tube was measured on a sample of 3,120 generated cables: it
  lengthened routes on racks with no PDU by up to 276 mm, and reported every
  cable as crossing a body, since a plug leaves its port on the face of the
  device it is plugged into.
- **The approach point.** Every pass through a ring whose opening is placed
  starts from a point on the run outside the band, the cable's radius and
  `CLEAR` past it (since kit 0.17.0 at least that: the installed bend radius
  where the route turns there, 3.4), at the opening's height and across
  position, and ends at another past the far face (`at: 'approach'`). The legs between them and the
  ring are not free spans. A detour, a hang or a leg from behind or below ends
  at the approach point, so a cable reaching a ring from behind goes over the
  ring or round it, as the detours of 1.3 find, and enters through the
  opening along the run. A tray stretch through a ring takes the same two
  points, and a ring a route would double back at (a finding) is gone to as
  far as its approach point, not its face: the path's `face` point stands
  back from the ring's own `face` (in `rings`), which stays on the band. On a
  tray stretch the approach points are not clamped to the floor, so a ring at
  the floor's end keeps its approach point outside its band.
- **The relief agrees with the guide.** The snap-in ring's relief drew each
  leg 6.8 mm thick in the plane of the loop, so its opening was 30.0 where the
  guide's is 32.0, and the sill point stood 1 mm inside the rear leg. The
  drawing reads the wall 8 px, 6.0 mm, and the plan's 43.6 less the 32.0
  opening leaves 5.8 a side: the relief's legs are 5.8 since
  fs/d-ring-snap-in 1.3.0. The slit, re-read at the same time, is 2.2 mm
  (28.6 to 30.8 over the tray), where 3.8 had been read.
- **Open question.** The round twist-lock seat, 32.3 mm across under each
  ring, is drawn 2 mm high, an estimate, and is not solid: only the band's
  seat under the opening is. A cable lying on the floor across it would rest
  2 mm higher than the kit lays it.

### 3.4 Room for the bends (#973)

Built in kit 0.17.0. With a drawing that follows the kit's own points, the
path is the cable, and its corners are its bends. On the reference rack 86
corners of the sixteen paths had less room than the 25 mm an OM4 cord may be
bent to once installed, and almost none was a bend a hand would make: they
came from where the kit put its points.

**The measure** is the one the bundle check uses, `cornersOf` (bundles note
5.2), which now lives in `rack/route-path.js`: a point is a corner where the
path turns by more than 1 degree from the leg it is on, a bend of radius r
uses `r tan(θ / 2)` of each leg, and a corner's room is the largest radius
its legs leave it. The walk starts at end a and measures each turn against
the leg from the last corner, so that many slight turns add up; which point
of a slow curve becomes the corner therefore depends on the end it starts
from, and the same points read the other way round can give other corners.
Room is given to 0.1 mm and compared as given (as in the bundle check), so
a corner with 24.96 mm of room passes at 25. A leg between two corners is
shared. The bundle check
gives each corner half of it, which is safe and coarse: a slight turn takes
half of a leg it needs a tenth of. A cable's own path is judged with the leg
shared **by need** (`cornersOf(points, {share: 'need'})`): the largest
radius both corners of a leg L can take is `L / (tan(θ1 / 2) + tan(θ2 /
2))`, and a corner's room is the smaller of its two legs' figures. It is the
same model worked exactly, never stricter than the halves (what passes at a
radius by halves passes by need), and no looser where the halves are right:
two right angles on one leg take half each either way. A leg
to the path's end, the plug included, is all the corner's, as in the bundle
check: the reach of a plug counts as the leg its first turn bends in.

**The radius** is the cable's own, never a constant: `ctx.bendOf(cable)`
where the page gives it (the installed radius of its named type, #919),
else its media's (`resting.js BEND`, held to the cable types table).

**What made the corners, and what was done.** Counted on the reference rack by
`spec/tests/js/bend-corners-probe.mjs`, before and after, by what the corner
is a point of:

| cause | before, by halves | before, by need | after, by need | what changed |
|---|---|---|---|---|
| a rest sample of a free span | 22 | 32 | 0 | spans sampled evenly along the arc; drops as tangent points; no hang that leaves a corner short |
| a ring's approach, entry or exit | 32 | 32 | 0 | the approach point stands the bend radius out; the cable is led square where it comes from behind |
| a detour point | 13 | 16 | 0 | each move to a detour's plane is two bend radii long; the approach point stands to the side of the port |
| a plug's end (beside a rest sample) | 19 | 7 | 0 | follows from the three above |
| all | 86 | 87 | 0 | |

By halves 23 corners of the new paths are still short (15 at an approach
point, 1 at a rest sample, 2 at a lead point, 5 at a plug's end; 16 at an
approach point and none at a rest sample until #987, 3.5): each is a turn that shares a
leg with a slighter one. That is the difference between the two ways of
sharing, and why a path is judged by need.

- **Free spans.** A span's samples stood evenly across the face, so along a
  steep end they were several times closer than in the middle, and where a
  span landed a sample and a break of its profile could fall a quarter of a
  millimetre apart. Any curve through such points turns tighter than the
  span does. The catenary is now sampled evenly along its arc, and points
  nearer than 1 mm are one. A drop onto a surface is laid as the two points
  where the tangents of its two bends meet, so the line through them
  touches each arc and has exactly the bend radius of room, with a level
  lead of nothing, one radius or two before it. And a hang is judged before
  it is laid: with every other span straight, it may leave none of its own
  points short of the bend radius, and no corner of the path less room than
  the straight span leaves it (or than it needs, where it has more). It is
  offered at its full sag, a half and a quarter, each sampled at 15 mm, at
  the bend radius and at twice it, and the first that fits is laid; where
  none fits the span is straight. A cable with no room to turn where it is
  held does not also sag. A landing is laid only where the stretch that lies
  level reaches the surface it lands on: a span is not said to rest on a rib
  it only passes over. Where two spans meet at a point, each fits alone
  and together they leave the point short, neither hangs.
- **Approach points.** The radius and `CLEAR` of 3.3 (6.5 mm for an OM4
  cord) left a turn onto a ring's run a fifth of the leg it needs. On each
  side of a ring where the route turns, the approach point now stands the
  installed bend radius from the band; a side the route passes straight
  through keeps the radius and `CLEAR`, and no approach point stands in or
  past the band of another ring of the same part (where two rings of a
  route follow each other on one run, no further than half way between).
- **Coming from behind.** A stop that stands back along the run from the
  approach point, on the ring's side of it, makes the cable turn back on
  itself to face the ring: two bends, which share a leg. Where a corner
  there is short of room the approach point is moved out to stand two bend
  radii past that stop along the run, and where the leg then runs straight
  to it the cable is **led square**: along the run, level with that stop,
  to a lead point (`at: 'lead'`, with the ring's `item` and `via`) beside
  the approach point, and from there square onto the run, so that one turn
  of more than a right angle is two right angles, each with its leg.
- **Detours.** 1.3 gives each move to a detour's plane two bend radii. Where
  a detour comes back beside itself (out past a tray's edge, up and back
  in), the leg between its two turns is as long as the port and the approach
  point are apart, along the run and across it, and needs two radii: the
  approach point stands just far enough along the run to one side of the
  port, and there it may stand nearer the band than the bend radius, never
  nearer than the radius and `CLEAR`.
- **The stretch through a ring** is the leg its two approach turns share.
  Where they need more of it than it is, the other side's approach point
  moves out by what is missing.
- **Back at the radius and `CLEAR`.** A stop that stands almost over the
  approach point turns onto the run with its own leg for room, and a point
  moved out past it would make the cable come back for it: the approach
  point may go back to the radius and `CLEAR` where that leaves the corners
  less short.
- **A plug.** Where a cable's first turn has too little of the plug's reach
  for a leg (a fibre cord's 27.6 mm, turning back past a right angle to a
  lane on the rail plane), it runs on straight out of the plug, half a bend
  radius, one or one and a half, to a lead point (`at: 'lead'`, with its
  `end`), and turns there.

**How a change is chosen.** Each path starts with its approach points at the
bend radius. While a corner is short, every change the rules above offer is
tried by laying the path with it, and the best is made: the one that leaves
the path's corners least short of room in all, then the shortest. A change
is taken only if it leaves them less short than they were, puts no leg newly
through a body or in front of a zero-U part (below), and either gives the
stretch it is for its room or makes the path no longer: a cable is not sent
a longer way round to make a short corner less short. The best of all the
offers is taken each round, whichever end of the cable it is nearer, for at
most six rounds; a path still short after six keeps what it has, and its
corners are findings. The result is kept per rack, context and cable, as
the side of a route is, so a page builds a new context when what the
context reads changes: one changed in place gives the path laid for what it
read before (since kit 0.25.0 the whole lay is kept, and by what it read, so
a new context that answers as the last one did lays nothing again).

**A radius no lay is opened out for.** Points are placed for a bend radius
up to 100 mm (`ROOM_MAX`, internal: twice a power cord's 42.6). A cable that
needs more is laid as one of 100 mm and judged by its own.

**In front of a zero-U part.** 1.3 keeps the space a PDU's outlets look into
for the last way round it, but only a leg that would graze the part is taken
behind it; one that clears it by more than the cable's tube is not a
crossing. An approach point 18 mm further out freed the leg from a lacer's
end ring to the lane beside a PDU to run across the outlet face, a fraction
of a millimetre clear of the part. So no point moved for room (an approach
point, a lead point, a run-out, a detour's plane) may put a leg through
that space that was not there with every approach point at the radius and
`CLEAR`, and no hang may sag into it. The space is as high as the part: a
span that passes just over a short PDU's top, in front of its face, is
clear of it straight and would hang down into it (22 mm over the top, 83 mm
of cable in front of the outlets, on one generated rack), and only the
hang's own check sees that, since every other check reads the taut path.
For a point moved: where one would, that side of the ring keeps the radius
and `CLEAR`, and its corner is a finding. The rule of 1.3 itself is no
stronger than it was.

**The finding.** What the kit's rules find no room for is still routed, and
is said: `routePath` returns `bends`, each corner of the path with less room
than the cable's radius, as `{kind: 'tight-bend', cable, point, between:
[from, to], at: [x, y, z], angle_deg, legs_mm: [in, out], room_mm, need_mm,
short_mm}` (`point` the path point's `at`, `between` as for a crossing), and
`bendFindings(rack, ctx, nameOf)`, beside `bodyFindings`, gives them
rack-wide with a sentence in the words of the bundle check. It says where
("c9 turns 129.7 degrees between its port on LEAF-B and CM-01 ring 3") and
then by how much ("with room for a 19.2 mm bend; the cable (aoc) needs 30
mm, 10.8 mm short."). It warns and never refuses. A page that draws the kit's points can show these as they are.
`inspect` of a cable carries them as `route.bends` (each finding less its
`kind` and `cable`, with its sentence), `describe` counts the cables that
have one and names the cable shortest of its radius, and
`cableScheduleRows(..., {bends})` writes one sentence into the notes of each
such cable: the finding, or how many bends and the tightest of them
(#1007). Corners at one point, to a tenth of a millimetre, are one finding, and so are two turns on one short leg (3.5). A cable is told them wherever it has a path, a loose end
or not; one whose port is not found has no path and is told nothing.

**What is left.** On the reference rack, nothing. On one sample of 60
generated racks (1,803 cables of mixed media, four-post and two-post, with
and without a zero-U PDU 200 to 1700 mm tall and up to 20 units off the
floor, panels with an FHD-CMP5DR lacer between switches;
`spec/tests/js/bend-room-sample.mjs` builds them from a fixed seed and
prints every figure here) the corners short of room fall from 22,910 to
959, on 361 cables: 25 of 883 fibre cords, 9 of 242 Cat 6, 57 of 204 Cat
6A, 97 of 248 DACs and 173 of 226 AOCs. A finding is a bend the kit's rules
found no room for. It is not proof that no lay has room: the rules are the
ones above and no more, and a cable can be clean read from one end and
report a bend read from the other (below). Those looked at were of these
kinds:

- **a plug that reaches almost to the ring's line.** A DAC's or an AOC's
  head ends 64.8 mm out of the face and the lacer's rings stand 73.7 mm
  out: 9 mm to turn onto the run at a radius of 23 or 30. A Cat 6A boot ends
  39.4 out, 36.6 short of the line, for a turn that needs 30 each way. No
  rule here moves a point to make that room;
- **a detour that comes back beside itself with no room to the side.** A
  port 32 mm below a tray and between two of its rings: the approach point
  cannot stand two radii to either side without standing in the next ring;
- **a cord that leaves a ring and comes straight back** to a port beside
  it, where the next ring or a wall of the part (the lacer's web) leaves no
  way round with room;
- **a lane a unit long between two turns**: a jumper to the next unit by
  the gutter, 44.45 mm for two right angles;
- **a ring a route doubles back at** (already a `doubles-back` finding).

**What this does not do.**

- **A lane has no depth.** It runs on the rail plane, so a cable from a plug
  to a lane turns back toward the rail. The run-out gives that turn its
  leg; it does not put the lane where a gutter's cables are.
- **A plug is a leg, except where it is known to be rigid (#985).** A plug
  body does not bend and a boot does, and the kit tells them apart only
  where a cited drawing gives the split (`PLUG_SPLIT`, beside `PLUG_REACH`
  in `kit/rack/route.js`):
  - **DAC and AOC: all rigid.** Amphenol C-NDAAFR-0099, view RADIUS FROM END
    OF DIECAST, gives 45 MIN required to bend the cable, measured from the
    diecast rear and *including the boot*. The head stands 19.8 out of the
    cage (`generic/qsfp-cable@1`) and 19.8 + 45 is the 64.8 mm reach, so the
    whole reach is rigid and the boot adds none. The reach point is flagged
    `rigid_mm: 64.8`; a corner at it has no leg in the plug and no room, and
    `cornersOf` measures the first leg from where the rigid part ends. So
    the cable runs on straight past the reach point to a lead point (the
    run-out of 3.4, half a radius to three for a rigid plug) and turns
    there. Where no run-out gives the turn its room, the corner at the reach
    point is a finding with no room (`room_mm` 0).
  - **LC, copper RJ45 and power: not split yet**, so the whole reach is a
    leg, as before. LC: the boot's 15.1 mm is from SENKO DS-LC-000023 A
    p.3, but the plug's 12.5 mm is an estimate (bracketed 11.6 to 13.4 by
    DS-LC-000004), and no cited drawing gives a boot bend radius. Copper:
    the boot's 26.4 mm is from EASE J0072 A, the plug's 13.0 mm is an
    estimate, and no cited drawing gives a boot bend radius. Power: no cited
    drawing gives a boot figure. A split needs the boot's length and
    bend radius from a drawing, and the plug's rigid length from one too.
    No figure here is estimated, and no boot bend radius is written.
  - **A reach the page gives as a number** (`ctx.plugReachOf`, from the
    part's `cablePoints`) cannot say how much of it is rigid, so it is
    measured as before: the whole of it a leg. A page that gives the reach of
    a DAC or an AOC measures it as before until the part can say.

  A turn at a DAC's or an AOC's plug end that the old measure passed on the
  plug's 64.8 mm now needs a lead point, or is a finding, on every saved
  rack with such a cord: routed lengths, stock sizes and bend findings change
  at the next measure (#985, one-way).
- **A tray stretch** (2.1) keeps its rings' approach points at the radius
  and `CLEAR`: a cable along a tray passes its rings straight, and rises
  onto each sill by a drop's tangent points. A stretch pinned to the held
  face, coming round the tray's edge to a port above, can still report
  bends.
- **The same cable written the other way round** measured the same on the
  reference rack and not everywhere, as #973 left it. Two causes were there
  before it: the way through a ring that both ports stand to one side of,
  and which body a detour meets first, are read from end a. Two came with
  it: the measure reads a path from end a (above), so the corners an offer
  or a hang is judged by can differ with the end; and a span at a plug's end
  can hang read one way and not the other. On the generated racks 38 of
  1,803 cables measured differently from the other end (19 before #973),
  and 9 reported a different number of bends, some none from one end and up
  to three from the other.

  **#986 closes it without changing any of the four rules.** `routePath`
  lays a cable from both ends, as written and as its twin (its ends
  exchanged, on the same route reversed, the result turned round), and
  keeps one lay by a rule that does not know which end was written first:
  the one that crosses fewer bodies, then the one whose corners are less
  short of room in all, then the shorter, and on a tie the one laid from the
  end whose port sorts first (by item, view and path). The same cable
  written end for end now has the same points in the other order, the same
  rings, marks and findings; on the sample none of the 1,803 measures
  differently and none reports a different number of bends. No cable is laid
  worse, by that rule, than it was from its end a. Against the lay before:
  seven of the 1,803 change length, five shorter (by up to 128.3 mm) and two
  longer (15.2 and 82.3 mm, each for fewer corners short of room); one
  goes up a stock size and none down; corners short of room fall from 959
  to 955, on 359 cables (23 of the 883 fibre cords). The reference rack is
  the same to a tenth of a millimetre. Where the two lays are equal the one
  kept can be the twin, so a path's points can differ where its length does
  not: a ring that only holds a cord reaching just into it (3.3) is passed
  the way the lay from the first-sorted end passes it.

  What it costs: a cable is laid twice the first time it is read. Since kit
  0.25.0 both lays are kept, by what they read of the rack and the context,
  and so is which of them was kept: neither is made again for a context made
  anew or after an edit to another cable (the kit README, "New in 0.25.0",
  says what lays a cable again). The page's readers are handed the twin when the twin is laid (the same
  id, media and type, `a` and `b` exchanged). `cornersOf` still reads a
  polyline from its start, so the bundle check's corners are as they were;
  the automatic route's own ties (a manager's rings in order from end a,
  end a's side on a tie) are not part of this and are as they were.
- **A lead point can mark no turn.** c8 runs on out of its panel plug to a
  lead point that its detour then reaches in line, so the path passes
  straight through it. It is left in: the path is the kit's stops and its
  detours between them, and a drawing rebuilds the detour from that point.
  (c8 no longer does so: since #987 it takes ring 4, 3.5.)

**Lengths change on saved racks.** On the reference rack every cord is longer,
by 10.9 to 179.2 mm, none shorter, and seven of the sixteen change stock
size: the upper leaf's c1 to c3 and c5 to c8 pass the 0.5 m break again and
are 1 m cords (c2 by 0.02 mm), c4 is still a 0.5 m cord, and the lower
leaf's eight are still 1 m cords.

| cord | before, mm | after, mm | change | stock, m |
|---|---|---|---|---|
| c1 | 460.5 | 514.8 | +54.3 | 0.5 to 1 |
| c2 | 451.3 | 500.0 | +48.7 | 0.5 to 1 |
| c3 | 430.1 | 502.9 | +72.8 | 0.5 to 1 |
| c4 | 422.2 | 491.6 | +69.4 | 0.5 |
| c5 | 465.0 | 522.2 | +57.2 | 0.5 to 1 |
| c6 | 470.3 | 515.2 | +44.9 | 0.5 to 1 |
| c7 | 495.0 | 505.9 | +10.9 | 0.5 to 1 |
| c8 | 440.2 | 619.4 | +179.2 | 0.5 to 1 |
| c9 | 590.5 | 611.1 | +20.6 | 1 |
| c10 | 589.3 | 613.2 | +23.9 | 1 |
| c11 | 591.2 | 616.1 | +24.9 | 1 |
| c12 | 592.0 | 623.4 | +31.4 | 1 |
| c13 | 558.1 | 645.7 | +87.6 | 1 |
| c14 | 564.8 | 617.4 | +52.6 | 1 |
| c15 | 546.9 | 648.2 | +101.3 | 1 |
| c16 | 552.6 | 575.8 | +23.2 | 1 |

c8 grows most: it leaves ring 5 and comes straight back to a panel port 13.4
mm short of the ring, with the lacer's web between, so it goes round the
front of the tray and straight in to its plug (until #987 gave it ring 4,
3.5: 547 mm). On the generated racks a
length moves by -113 to +297 mm, median +14; 93 cables move up a stock size
and 34 down. 668 of the 1,803 are shorter: a span that hung to its full
depth whatever held its ends now hangs only as deep as the corners beside
it have room for. No path crosses a body it did not cross before (none
does, before or after). No cable has a point in front of a zero-U part's
outward face that had none before: eight do, the same eight before and
after, each where a lane's own run comes to the end of a short PDU and is
taken over its face, the last way round of 1.3. A stored routed length and stock size move the next
time a page measures them; an entered length is never touched.

### 3.5 Room to turn into a ring (#1026)

Built in kit 0.27.0. Until then the automatic route sent every lead through
the ring of its manager nearest its port, whatever stood between. A lead is
the stretch of a cable from the far end of its plug to the first thing that
holds it. Where a lacer is hosted on the unit its ports are in, the nearest
ring is so close that the lead has nowhere to turn. On a rack of thirteen 2U
switches, each with an FHD-CMP5DR on its top unit, the rings stand 73.7 mm
out of the rail and their sill 7 and 20 mm under the two rows of ports above
it; an AOC's plug ends 64.8 mm out, 8.9 mm short of the line it has to turn
onto, and needs 30 mm to turn. A port 6 mm to one side of a ring's face had
two turns to make on 20 mm.

**The rule: a lead enters the first ring along its way that it has room to
turn into.** The rings on its way are the ones the route already listed,
from the port out toward the gutter it takes. One that is too close to turn
into is passed over, and the lead runs on to the next: over the tray, or
through the opening of the ring it passed without lying in it. The choice is
by room, not by distance.

**What room is.** The lead is laid on its own, taut, by the rules of 3.4:
from the plug's reach point to the ring's approach point, round whatever
body stands between (1.3), and on through the ring. It has room when no
corner of that has less than the cable's installed bend radius, a leg
between two corners shared by need (3.4). The approach point is tried where
3.4 may put it (at the bend radius from the band, at the radius and
`CLEAR`, two radii past the plug with the lead led square or not, and to
either side of a detour that comes back beside itself), and the plug's
run-outs are tried where its own turn is what is short. One of these with
room is room. So what decides is what stands in the rack: how far the plug
reaches (1.5), how far out and how high the ring's sill is, the ring's own
legs and the tray under it, which unit the manager is mounted on, and how
far back the device is set. No distance is written into the rule; the 30 to
40 mm at which a ring starts to leave an AOC room on this lacer comes out of
those.

It is a test of one lead, not the whole path: it lays no hang and none of
the rest of the route, so it can call room where the path then reports a
bend, or the reverse. The path's own `bends` are what is reported. A port
the drawings do not place, and a ring they do not place, are taken as
having room, so nothing is passed over for what cannot be measured.

**Where no ring leaves room** the lead takes the nearest, as before, and its
bend is a finding (3.4). The finding then also says why ("Lacer EDGE-0
stands too close to the port of c1 on EDGE-0 for the cable to turn into any
ring on its way") and what would help ("set EDGE-0 back from the rail, mount
the manager on another unit of EDGE-0, or leave EDGE-0 without a manager").
That is a field of its own, `advice`; the finding's `text` is the bend and
no more, so the advice lengthens no sentence a page reads, clips or joins,
and a schedule's note says it once for each end's device (a cable short of
room at both ends has two). The second remedy is
offered only for a manager hosted on a device of two units or more, and a
manager that is a rack item of its own is to be moved away, not left out.
`bendFindingsOf` and `bendFindings` carry `advice` and mark the finding
`tooClose: {manager, device}`; the path's `bends` are unchanged. The lead is
not sent straight to the gutter instead: with the plug ending 0.1 mm behind
a ring's leg, the straight run clears the ring only on paper, and a lead
that skips its device's manager is a span in front of other ports (1.7)
with advice to add the manager it skipped.

**A route made by hand is never overridden.** The rule is the automatic
route's. A ring a hand route names is gone through, room or none, and its
finding carries no advice about the manager: the ring was chosen. Its
waypoints are kept; the lay between them is the kit's, and can move as any
lay does (a detour round a tray, a span's point at an edge).

**A lead goes round a tray's floor, and round nothing else.** The detour
rules of 1.3 will take a leg over the top of a ring that stands in its way,
or round a wall, and such a way can have all its room: 60 mm up in front of
the device above, across, and down again. No lead is dressed so. The test
stops at anything a leg meets that is not a plate met from above or below: a
ring whose legs stand between the plug and the next ring leaves that next
ring no room. A leg that clears a ring, through its opening or beside it,
meets nothing and is not stopped.

**Run out past a ring in the way.** Where a ring stands between a plug and
the ring its lead takes, the path's own way round it can be a loop with all
its room (out, under the tray and back, 320 mm, in the fixture), and since
no corner of it is short nothing of 3.4 offers anything else. Run on 15 mm
out of its plug, the same cable clears that ring through its opening. So
where a detour stands in a plug's own leg, the run-outs of 3.4 are tried
before any offer, and the shortest is taken that leaves the leg no detour,
no corner shorter of room in all and nothing newly crossed.

**The gutter is chosen before the rings are.** A cable whose ports stand on
opposite sides of the centre line takes the gutter that measures the
shorter (4.1). Measured through the rings chosen by room, and with the
detours of this section, the two sides' lengths moved, and cables changed
gutter: one into a bend it did not have, and a member of a bundle away from
its trunk, where it hung free. So each side is measured as it was before
this kit: through the ring nearest each port, by a lay with none of the
offers of this section (a **plain** lay; one that took none of them is the
plain lay, and is not made twice). The rings are then chosen by room on the
side taken. This change moves no cable to another gutter.

**Which leads are left without room** on that rack, at no setback: a port
within some 35 mm inboard of the end ring, which has no ring after it; a
port under a ring, or just past one, whose plug ends 1.6 mm behind that
ring's rear leg; and a port in the lower row beside a ring, level with the
ring's seat, whose way to the next ring is through that seat. All three are
the manager standing where the ports are.

**Round a tray's front edge, with room.** A port under a tray reaches its
ring by rule 1 of 1.3: out past the front edge, across, and back in to the
approach point. That is three right angles, and 3.4 gives each its leg. But
a detour is pulled taut (1.3), and taut the point where the cable turns
back in toward its plug is not needed: the cable runs straight from the
point in front of the ring to the plug's end, and that one turn is then
wider than a right angle on the same 60 mm it shares with the turn before
it (139 degrees and 16 mm of room for a 30 mm cable, in the fixture). So a
detour round a plate met from above or below is offered **not pulled taut**:
a point stays where the way without it would leave a turn less than the
bend radius and less than the way with it does, each end of the way taken
as a right angle (`detour`'s `loose`). It is an offer of 3.4, tried only
where a corner at a detour point is short, so a path with room is as it
was. A way over a ring's leg is never kept loose: that is the hump above.

**Behind a tray's back edge.** Rule 1 takes the front edge first because a
port at the rail plane ends its plug under the floor. A device set back
from its rails ends its plug behind the floor's back edge instead (the
FHD-CMP5DR's floor starts 48.8 mm out of the rail; an AOC's plug on a
switch set back 50 mm ends 14.8 mm out), and the near edge is then that
one. So the same offer of 3.4 also gives a detour its way **up behind the
plate**: one point on the floor's back plane (the back edge less the
cable's radius and `CLEAR`), as far clear of the plate on the far end's
side, and along the run where a taut line from end to end crosses that
edge (`detour`'s `rear`). It is offered only to a floor one of whose ends
stands at or behind the back plane, and taken only where it leaves the
path's corners less short than the front edge does: at 25 mm of setback the
plug ends 2.5 mm behind the plane and the cable would have to stand almost
upright there, so the front edge is kept. In the fixture a bottom-unit
port 54 mm along from its ring's face, which turned twice on 53.3 mm round
the front edge with room for a 26.6 mm bend, comes up behind the tray with
room and is 247 mm shorter.

**The stretch through a ring** (3.4) could be lengthened only by moving the
other side's approach point out. Where that point stands beside a port and
has no room to move, this side's now moves out instead; and an approach
point already moved in beside a detour may go back to the radius and
`CLEAR`. Both are offers, judged as every offer is.

What is chosen is still the cable's whole path, laid from both ends
(3.4), so no cable written the other way round lays differently.

**A patch along one manager (#987).** Two ends that leave through one
manager run along it through the rings between their ports (4.1). The rule
above is applied there too: of the rings between, the first from end a that
a's lead has room to turn into and the last that b's has are the ends of
what is taken; where an end has room at none its nearest stands, and where
the two ends would pass each other's ring all are kept.

With no ring between, the ring nearest the middle of the two ports was
taken, of those the cord passes through. On the reference rack that sent c8
through ring 5, which stands 6.6 mm past its panel port: the cord left the
ring and came back to the port round the front of the tray, 619.2 mm, with
every corner its room and nothing crossed. Nothing in the lay was wrong; the
ring was. Room cannot tell the two rings apart (the loop has all its room),
and the test of 4.1 for whether a cord passes a ring reads the ports and the
ring's centre, not the sill the cord lies on, and calls ring 4 a hook where
the lay passes it. So here, and only here, the choice is made by laying:
**the nearest ring on each side of the stretch is laid as a route through
that one ring, with the ring taken before, and the best lay is taken**:
fewer rings entered and left by one face, fewer bodies crossed, the
tightest corner less short of room, corners less short in all, then the
shorter; on a tie the ring taken before. The tightest corner is weighed
before the sum because three corners 23 to 26 mm short add up to more than
one that doubles back with no room at all, and the one is the worse cable. c8 takes ring 4: led square from the leaf above,
straight on to the panel, 547 mm. The other fifteen cords keep their ring.
The choice is the same whichever end is written first, which the tie on end
a's side was not. It costs two more lays for such a cable, kept as the
path's are; a manager with a ring on only one side of the stretch is as it
was. A route made by hand through ring 5 is laid as before, with no finding.

A first attempt at this was withdrawn because c8, through ring 4, failed
the check that no point of a cord lies below a support it is over. That was
a fault of the hang, not of the choice, and c8 was the first cord to show
it: a span that lands on a surface and leaves it over its edge had one
sample on the surface and the next past the edge and lower, and the straight
leg between them was inside the plate for the rest of the way to the edge
(0.2 mm into the tray's floor, over 8 mm). **A span now has a point where
it passes the edge of a surface it lies on, at the height a cable lies on
it:** level to the edge, and down from there (`resting.js`).

**Two turns on one short leg are one finding.** A lead that jogs from its
plug's end to a ring's line turns one way and then the other on the leg
between (an S-bend); a way out past an edge and back turns twice the same
way on the leg across. The measure gives each turn the same room, what
that leg leaves the two, and until now each was a finding: one fault read
as two, with the same room and the same shortfall, and a rack's count of
tight corners was near twice what a person would find. A person fitting the
cable makes such a bend with one movement of the hand, calls it one bend,
and puts it right in one place, the leg between the turns. So it is one
finding, and the finding says plainly that it is two turns: "c1 turns twice
within 22.8 mm between its port on EDGE-0 and Lacer EDGE-0 ring 1 (67.1 and
63.2 degrees)", and then the room and the shortfall as for any bend ("with
room for a 17.9 mm bend; the cable (aoc) needs 30 mm, 12.1 mm short."). Two tight corners are paired when they are next to each
other on the path, have the same room, and that room is what the leg
between them leaves the two. A corner that is short for its other leg stays
a finding of its own, as does one that doubles back. A pair's sentence is
longer than any bend's was (182 characters at the longest, where it was
150), and on a rack with lacers most findings are pairs. The finding has
`turns`, the two of them (`point`, `at`, `angle_deg`), and `apart_mm`; its
`at` is the middle of the leg, so a page that rings a finding rings the
bend once; `point` is the first turn's, `angle_deg` the wider of the two,
`legs_mm` the leg into the first and out of the second. `inspect` carries
the same; `describe` counts cables, as before, and a schedule's note counts
bends ("c7 has 2 bends with less room than the cable needs"). Nothing is
laid differently for it: where two lays of a cable are compared (3.4), a
finding of two turns still counts as two corners short.

**What is left.** Counted on racks of the shape the issue was measured on
(`spec/tests/js/ring-room-shape.mjs`, which builds them and prints these
figures beside another tree's): thirteen 2U switches, each with an
FHD-CMP5DR hosted on it, a vertical manager at each front upright, 275
cables of which 264 are AOC. Corners short of room, and the cables that
have one, before and after; a corner is counted as before, so a finding of
two turns is two:

| lacer on | setback 0 | 25 mm | 50 mm | 100 mm |
|---|---|---|---|---|
| the top unit, before | 518 on 193 | 249 on 101 | 58 on 27 | 12 on 5 |
| the top unit, after | 252 on 107 | 90 on 40 | none | none |
| the bottom unit, before | 152 on 70 | none | none | none |
| the bottom unit, after | 20 on 9 | none | none | none |
| no lacer | none, before and after | none | none | none |

With the lacer on the top unit and no setback the 252 corners are 130
findings, and 128 of them say the manager is too close: the three kinds of
lead above. No leg crosses a body, before or after, and no cable changes
gutter. Across the twelve racks 639 of the 3,300 routed lengths move, by
-575 to +61 mm, median -3; 423 are shorter; 10 cables go up a stock size
and 77 down. With no lacer nothing moves.

On the sample of 60 generated racks of 3.4 (1,803 cables) the corners short
of room fall from 955 to 422 (every corner of every path, by `cornersOf`;
counted from the findings, where corners at one point are one, 953 to
420), on 171 cables where it was 359: 14 of 883
fibre cords, 7 of 242 Cat 6, 29 of 204 Cat 6A, 45 of 248 DACs and 76 of 226
AOCs. 332 of the 1,803 lengths move, 187 shorter and 145 longer, by -340 to
+121 mm; 4 cables go up a stock size and 30 down. None measures differently
written the other way round, and none reports a different number of bends.
No path crosses a body, and no cable has a point in front of a zero-U
part's outward face that had none before. On the reference rack one cord
moves: c8, to 547 mm from 619.2, still a 1 m cord.

**Lengths change on saved racks.** A routed length and its stock size move
the next time a page measures them, for a cable whose automatic route takes
another ring or whose detour is laid another way. An entered length is
never touched, and a route made by hand keeps its waypoints (5 of the
hand-routed cables on the kit's test racks measure differently, by their
lay). Everything read off a routed length
moves with it: the cable schedule, the BOM's cord sizes, the spare and what
is to store, a sheet, and the length a DCIM cables file gives a cable (and
a note of that file that depends on it: Nautobot's, that 1.5 m is written
as 2 m). A cord already bought at the size the kit chose before can read as
too short where its path grew (the longest growth measured is 121 mm);
none does of the 7,210 cables on the racks above, the sample and the kit's
other test racks.

**What is kept.** The choice is part of a cable's route, and a lay is kept
under its route written out (3.4), so a lead that takes another ring is
another lay. The test of a lead is itself made in two steps, as a lay is:
what it reads of the rack and the context, and the answer from that and the
world; the answer is kept under the text of what was read, so a context made
anew judges nothing again. `spec/tests/js/speed-goldens.json` is recorded
again from this kit, since this change is meant to move numbers: 75 of its
91 racks have an answer that moves. A first read of 300 cables takes half
as long again as it did (0.68 s for 0.44 s on one quiet machine, where the
kit before 0.25.0 took 35 s). Most of that is the run-outs tried first
where a detour stands in a plug's own leg: they are tried at 1,202 lead
ends, three trial lays each, and taken at 34, and the trial lays inside
the lays rise from 9,199 to 15,554. The room tests cost about 40 ms. The
plain measure of the gutter is cheap, about 30 ms: of 500 asks 450 are
answered by the lay already made, and 50 plain lays are made. A read after
one device is moved lays every cable again and is slower by the same
ratio (873 ms for 559 ms at 300 cables); a read after one cable is moved,
and one in a context made anew (21 ms for 18 ms), are about as before.
Trying the run-outs at fewer lead ends is the known saving, and is left
for a later change.

**Worse than before, and left so.** Every cable of those racks was compared
with the kit before on bends, bodies crossed, rings entered and left by one
face, ports covered and its gutter. One is worse: on a generated rack with
no vertical managers, a 445 mm span from a port to its gutter hangs to its
full depth and comes to rest on the tray of the lacer below, across the
front of 11 ports, where before it was laid at half its sag because the
full one cut the tray's edge. That is the hang being laid as the model
says, now that a span can lie to an edge; it is 85 mm longer and a new
finding. One has three corners short where it had two, each less short
than before (8.7 and 8.7 mm, to 0.4, 4 and 4).

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
- **Local patches.** Before kit 0.12.0 the automatic route picked the gutter
  from the x of end A alone (`route.js autoRoute`), and when both ends left
  through the same manager it went out to the gutter and back through the
  same rings (a patch from a switch port at x -150 to a panel port at x -20
  ran ring 1, left-front U12, U11, ring 1, ring 2). **A patch whose two ends
  share one manager runs along the tray directly, port to port, through the
  rings between them, with no gutter** (built early, in kit 0.12.0: a ring is
  between when its centre is; with none between, the ring nearest the middle
  of the two ports holds it, never a direct run; a ring just past a port holds
  a cord that reaches into it without a doubles-back finding,
  [cable-managers-design.md](cable-managers-design.md) section 13). A local patch with both ends rail-side lies
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
it. The automatic route chooses the gutter for each cable from both ends, not
from end A alone (built early, in kit 0.12.0): when both ports stand on the
same side of the centre line in their trays, that side; when they stand on
opposite sides, the side that gives the shorter path. Through cables that
each run toward their own port side then use separate stretches of a tray and
never meet. **A through cable whose ends
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
opening below the plate (with the snap-in ring's 5.6 mm sill, 35.1 mm below
the plate and 38.1 mm below the top of U12), its centre a radius above that, its layers
stacking up toward the plate, and no cable between two rings below that line
where a tie slot holds it. The upward face of Md, its underside, is a resting
face with 3 mm of its envelope above it, so slack stored there warns at once
as a full tray (4.4), and slack stored in Mu does not.

## 5. Slack storage

**Built as rack file version 4, and narrowed there.** [rack-file-v4-design.md](rack-file-v4-design.md) section 3 is what
the kit follows. The spare of a cable is recorded and listed, not drawn or
placed by the kit; the stored length does not count in the routed length,
since the stock length already holds it; and the schedule has two columns,
`spare` and `stored`, where 5.5 planned one named `slack`.

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
  **These two figures are withdrawn.** They are floor area times height, and
  no cord fills that area at its bend radius: stacked in turns the same tray
  takes about 2.2 to 3 m of 3 mm cord (the version 4 note, section 3.4).
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
| `fs/d-ring-snap-in` | `depth`, `sill`, `aperture.at` | the band along the run (6.8 mm, drawn); the sill under the opening (5.6 mm, read off the ring-profile view in step 3; 2 mm had been estimated) | the same datasheet, the ring-profile view |
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

**Built as rack file version 4.** [rack-file-v4-design.md](rack-file-v4-design.md) sections 3.3, 3.9 and 6 have the
keys as the kit reads them: `slack` gains an entry for spare left at an end,
`{end, value?, unit?}`; the `face` of a `lay` entry is acted on and its
`position` kept; `roll` is section 6 there.

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
- **Bends** (3.4) and **spans in front of other ports** (1.7) are in all
  three reads (#1007). `inspect` of a cable gains `route.bends`, each tight
  corner with its sentence, and `route.covers`, `{count, ports, between,
  judged, estimated?, text}`;
  each key is there only when there is something to say. `describe` puts
  them on the findings line with the bodies, each part only when it counts
  something (`findingsText` in `kit/rack/queries.js`). After "Findings:"
  come up to three parts, joined by semicolons: "2 cables cross a body";
  "3 cables have a tight bend (the worst c9, 10.8 mm short)"; and "9 cables
  cross in front of other ports", with the cable that covers most and its
  count in a bracket. That bracket also says that only ports that hold a
  cable were judged, when the page listed no ports. The exports take the two lists as they take `bodies`:
  `cableScheduleRows(..., {bends, covers})` adds a sentence for each to a
  cable's notes, and `layNotes(rack, {bends, covers})` gives one line a
  cable for a file with no row for one (a BOM, a drawing). The columns are
  the same.

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
   Beyond those changes the fixture needs S-dn to have a second row of ports
   6 mm below its top, of a type a Cat6A cord fits, and twelve ports for the
   members of d.
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
| ring `guide.wall`, `guide.height`, `guide.slit`, and `data-guide-wall`, `data-guide-height`, `data-guide-slit` (#968) | component contracts, drawings | parts state them; rack.json derives a ring's solids from the compiled attributes |
| a ring's solids in rack.json `solids`, named `ring/<id>/<part>` with `rear-leg`, `front-leg`, `left-leg`, `right-leg`, `hook`, `bar`, `seat` (#968) | the rack catalogue, kit, findings | the kit reads them, findings and pages name the parts by them |
| a ring's part, and a zero-U part, met by the cable's tube in `legCrossings` and `detour`, the approach point (`at: 'approach'`) clear of the band by at least the radius and `CLEAR` (#968; the installed bend radius where the route turns there, #973) | kit API | a page checking its tubes and the routed lengths of saved racks follow it |
| room for the bends (3.4, #973): the measure a path is judged by (`cornersOf` with `share: 'need'`, the plug's reach a leg), the approach point at the bend radius, the lead point (`at: 'lead'`, with a ring's `item` and `via` or a plug's `end`), a detour's `room` of two bend radii, the evenly sampled hang that leaves no corner short, and `ROOM_MAX` | kit API, routed lengths | a page reads the points by these names, and every routed length and stock size of a saved rack follows the rules; changing one moves them again |
| `tight-bend` in a path's `bends` (`point`, `between`, `at`, `angle_deg`, `legs_mm`, `room_mm`, `need_mm`, `short_mm`), `bendFindings`, and its sentence ("turns N degrees between A and B with room for an R mm bend; the cable (type) needs M mm, S mm short.") | kit API, agent output | a page and an agent read the kind and the fields, and match the sentence |
| `port-behind-span` in a path's `covers` (`item`, `path`, `view`, `between`, `at`, `judged`, `estimated`), `coverFindings` with `span-over-ports` (`count`, `ports`, `between`, `judged`, `estimated`) and its sentence (`coverFindingsOf`: "crosses in front of P on D", the stretch, the advice, and "Only ports that hold a cable were judged."), the rule that a port within the bend radius of the cable's own is not listed, and the optional reader `ctx.portBoxesOf(itemId)` giving `[{path, view, x, y, w?, h?}]` (1.7, #1013) | kit API, the routing context, agent output | a page supplies the reader and reads the findings by these names; agents match the sentence |
| one lay whichever end is written first (3.4, #986): a cable laid from both ends and one kept by crossings, room, length, then the first-sorted end; `ctx` readers handed the twin | kit API, saved racks | routed lengths and paths on saved racks follow the lay kept; a page whose reader tells the ends apart by `cable.a` sees them exchanged on a twin |
| `cornersOf` and `STRAIGHT_DEG` in `rack/route-path.js` (still exported from `rack/bundles.js`), and `cornersOf`'s `share` option with `half` (the default, the bundle check's) and `need` | kit API | a consumer imports them by these names from either path |
| a doubled-back ring's path `face` point at its approach point, apart from the ring's own `rings[].face` on the band (#968) | kit API | a page that draws the face point, or compares the two, reads them by these names |
| the ring advice in `bodyFindings`, "route it into the ring along its run, through its opening", and a ring's part named as "ring N front leg" (#968) | kit API, agent output, exports | agents and the export notes match the sentence |
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
| routed lengths changing on saved racks: detours, the plug's reach (1.5) and a DAC's or an AOC's plug taken as rigid (1.5, #985), cables resting at the floor and at the ring sill, ring passes from approach points and solid rings and zero-U parts met by the tube (3.3), room for the bends (3.4), the end allowance by media (1.6), positions in the lay, the face of each tray, slack | kit | stored routed lengths and stock sizes move on the next measure; an ordered stock length may no longer match |
| the lane moving outboard of a zero-U part that stands in the gutter and carries no lane (a zero-U PDU), and routed lengths changing beside one | kit (`laneXAt`), drawings | every route on that lane is longer, and a saved length moves on the next measure; a drawing that places lanes itself must follow |
| the reach point (`at: 'reach'` with `end`, and `rigid_mm` on a DAC's or an AOC's, #985) in `routePath`, `ctx.plugReachOf`, `PLUG_REACH` and `PLUG_SPLIT` (the helpers that compute them stay internal), with the plug outside the face in the path (1.5) | kit API | a page passes `plugReachOf` and reads the points by these names; moving the plug into the allowance later would change every length again |
| the end allowance by media, `END_ALLOWANCE_BY_MEDIA` (the table: the plug inside the port and the maker's short tolerance, never slack), `endAllowance(cable)` and the path's `allowance` (what a length adds an end: the table's figure and, until #949 step 4, the temporary dressing allowance of 0.1 m, which is not exported) (1.6); `END_ALLOWANCE_M` is gone | kit API | a page reads the table by these names, and every routed length and stock size depends on the figures; removing the dressing allowance shortens every routed length by 0.2 m |
| a zero-U part's pass-through hole judged on the tube (1.2, #992) | kit | a route through a pass-through hole, and its length, can change on saved racks |
| `crosses-body` (with `part` and, for a held-face stack, `face`), `unheld` and the tray findings, `bodyFindings` | kit API, agent output | agents and pages read the kinds |
| the public subpath `@portrayal/kit/rack/solids` (`solidsOf`, `legCrossings`, `detour` with its `room`, `CLEAR`) | kit package exports | a consumer imports it by that path and those names; a rename or removal is a breaking kit release |
| `cable.slack`, `cable.slack.clear`, `cable.lay` (with `face`), and `roll` on `patch` | kit commands, offered to agents | agent sessions and saved prompts call them by name |
| `inspect` fields: `crosses` and `rests` (with `face` and the tie slots used) on a cable route, `slack.stored`, the tray block of a device per face, and `roll` on a device | kit queries, agent output | agents and the site read them by name |
| the crossing and tray lines in the export notes | exports | a reader of the notes matches them |
| the `slack` column of the cable schedule, after the last column | export | a reader takes it by its header |

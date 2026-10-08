# Cable bundles: bundles, Velcro straps and bend radius in the rack kit

Status: agreed 2026-10-08 (#920). Nothing is built. Cable management piece 3,
tracked in roc-ops/portrayal-site#143. Builds on the rack core in `kit/rack/`
and on two changes in flight that touch the same files: the rack agent commands
(kit 0.4.0: `inspect`, `selectCables`, `fit`, `field`, a `describe` window and a
per-call `ctx`), and #926 (zero-U parts and `side` moving into the kit). The
decisions already taken come from two designs in roc-ops/portrayal-site,
`2026-10-07-rack-face-managers-design.md` (section 1.1, D6 and D7) and
`2026-10-07-cable-routing-pathways-design.md`, and from the bend-radius research
on #897.

Section 10 records the decisions taken on the questions this note left open,
each with its reasoning.

## 1. What a bundle is

Cables leaving a switch through a lacer panel's rings and running to a patch
panel are combed into a bundle and held with hook-and-loop (Velcro) straps. In
the Rack Builder today every cable routes on its own: through rings, ducts and
pass-throughs (pathways), and up or down the lanes beside the posts. A bundle
groups cables that share part of their route into one dressed run with:

- a **number** and an optional **label**, for the tags at each end;
- a **trunk**: the run its members share, as waypoints;
- **straps** along the trunk at a spacing, 12 in by default;
- a **size**, estimated from its members, checked against the pathways on the
  trunk;
- a **bend radius**, the largest of its members' radii, checked against the
  trunk's corners.

Already decided, and not reopened here:

- Velcro straps are drawn every 12 in by default, and the spacing is
  configurable.
- A bundle's maximum diameter is the smaller of 2.5 in (63.5 mm) and the
  tightest aperture on its route.
- A bundle's minimum bend radius is the largest of its members' radii, so one
  fibre makes the whole bundle as strict as fibre.

## 2. The bundle in the rack document

### 2.1 The record

A rack gains an optional `bundles` array. A bundle is:

```json
{"id": "b1", "number": 1, "label": "",
 "members": [{"cable": "c1"}, {"cable": "c2"},
             {"cable": "c7", "b": {"lane": "left-front", "ru": 24}}],
 "route": [{"item": "i9", "via": "guide-5"}, {"lane": "left-front", "ru": 20},
           {"lane": "left-front", "ru": 30}, {"item": "i12", "via": "guide-1"}],
 "straps": {"every": {"value": 12, "unit": "in"}}}
```

- `id`: `b1`, `b2`, ..., from `nextId(bundles, 'b')`. It is the address
  commands use and is never shown as the bundle's name.
- `number`: a whole number from 1, unique within the rack. `bundle.create`
  gives the next one past the highest in use; `bundle.update` can change it.
  It is what a tag prints when there is no label.
- `label`: free text, possibly empty. The bundle's name is its label, else
  "Bundle <number>".
- `members`: the cables, in combing order. Each is `{cable}` with an optional
  `a` and `b`, the trunk waypoint where the member leaves the bundle for that
  end (section 4.3). A cable is in at most one bundle.
- `route`: the trunk, as waypoints of the two shapes a cable's route already
  uses (`{item, via}` and `{lane, ru}`). It is always stored (section 4.1).
- `straps`: optional. Absent means every 12 in. `every` is `{value, unit}` with
  `unit` `in` or `mm`, as a length is stored with its own unit. `{"every":
  null}` means no straps (a bundle held some other way, such as a lacing bar).

Membership lives on the bundle and only there. A cable does not carry a
`bundle` key, so the two can never disagree; `inspect` and `selectCables`
derive a cable's bundle from the bundles (section 5.3).

### 2.2 Keeping it consistent

- `parseDoc` reads shapes only, as for cables: a bundle with no usable `id` or
  a duplicate one gets a fresh id; a member that is not `{cable: <string>}` is
  dropped from the array; `number` that is not a whole number from 1 is
  renumbered past the highest in use; `route` is read with `readRoute`, so an
  unreadable entry keeps the route as written in `routeAsWritten`, as on a
  cable. Unknown fields are kept.
- `settleBundles(rack)`, beside `settleManagers` in the editor's `loadDoc`,
  checks references and returns a note per repair: a member naming no cable is
  dropped; a cable named by two bundles stays in the first; a number used twice
  is given to the first and the second is renumbered. Nothing else is dropped,
  and a bundle left with no members is kept (section 4.5).
- **Removing a cable removes it from its bundle in the same step.** Cable ids
  come from `nextId`, which takes one past the highest, so a removed `c9` can
  be handed to the next cable; a bundle that still named `c9` would pick it up.
  `cable.remove`, `remove {cables: 'remove'}` and anything else that drops a
  cable go through one helper that does both, and the summary says so.

### 2.3 The schema, and the document's version

`spec/schemas/rack.schema.json` gains `bundles` on `rack`, and `$defs`
`bundle`, `member` and `strapSpacing`. `member.a` and `member.b` and
`bundle.route` reuse `$defs/waypoint`. `docs/format-stability.md` gets one
line.

**The rack document's `version` rises from 2 to 3** (decision 1). The migration from 2 is the identity, as 1 to 2 was. The reasons:

- `parseDoc` rebuilds each rack from the keys it names (`id`, `name`, `frame`,
  `items`, `zeroU`, `cables`, `dcim`). A page from before bundles would open a
  version-2 file holding `bundles`, drop them, and erase them on its next
  autosave. A cable kept with unknown keys would survive, but a bundle is a
  rack key.
- Even if the key survived, an older page would edit a member's route alone,
  so the file would hold a bundle whose members no longer follow it.
- This is the reason the document went to version 2 for rack-face managers: an
  older page refuses the file instead of mishandling it.

Under `docs/format-stability.md`, a new rack version publishes its schema
under the next unused schema label, and `/v1/` stays as published. **#921 is
therefore a one-way door**: a version-3 file is refused by every page and kit
from before it, and the schema label it takes is never reused. Its pull
request says so.

#926 adds `side` and the zero-U entry without a bump, because no kit release
has been published yet. Bundles bump anyway: a bundle is a rack key that an
older `parseDoc` drops, where `side` is an item key.

## 3. The commands

Five commands join `COMMANDS` in `kit/rack/commands.js`. Like the others, each
is pure: the rack, its arguments and `ctx` go in, and a new rack or an
`{error}` sentence comes out. Each is one undo step through `apply`; the
history stores whole racks, so undo needs nothing new. Each follows the 0.4.0
rules: a description of 500 characters or less that names no function or page,
argument descriptions of 150 characters or less that state their defaults, and
`findings` for what changed underneath.

Batches: `resolve` swaps `"@name"` for an id in `id` and in a cable end's
`item` today. It also swaps the `cable` argument and each entry of `cables`, so
one batch can add cables and bundle them.

| command | arguments | does |
|---|---|---|
| `bundle.create` | `cables` (two or more ids), `label`, `number`, `route`, `straps`, `as` | makes a bundle of those cables |
| `bundle.add` | `id`, `cables` | adds cables; a member named again rides the whole trunk again |
| `bundle.peel` | `id`, `cable`, `at`, `end` | takes a cable out, or out from a waypoint on toward one end |
| `bundle.update` | `id`, `label`, `number`, `straps`, `route`, `summary` | renames, renumbers, sets the spacing, or reroutes the trunk |
| `bundle.remove` | `id` | dissolves the bundle; the cables stay as they are |

### 3.1 `bundle.create`

Description: *"Bundle two or more cables that share part of their route. The
bundle runs where they run together, unless a route is given, and gets the
next number. Refused for a cable already in a bundle."*

- `route` left out: the trunk is worked out from the members' own routes
  (section 4.1). If they share no waypoint or lane run, it is refused: "c3 and
  c7 share no pathway or gutter, so there is nothing to bundle. Give the bundle
  a route."
- `route` given: checked as `cable.route` checks a route in 0.4.0 (the shapes,
  then each waypoint against the rack's pathways and lanes).
- Refusals: a cable that is gone (`CABLE_GONE`); a cable named twice; "c3 is
  already in Bundle 2. Peel it off first."; "Bundle 4 is already b2's number."
- Summary: "Bundled 12 cables as Bundle 3." `created: {id}`.

### 3.2 `bundle.add`

Description: *"Add cables to a bundle. A cable already in it rides the whole
bundle again. Refused for a cable in another bundle."*

- A cable in this bundle has its peel points cleared; if it had none and every
  cable named is already a member, nothing changes.
- The trunk is not rerouted. A new member whose own route never meets the
  trunk runs to it directly (section 4.2), and a finding says so.

### 3.3 `bundle.peel`

Description: *"Take a cable out of a bundle. With at, it stays in the bundle up
to that waypoint and runs on its own from there to one end."*

- `at` left out: the cable leaves the bundle and follows its own route again.
- `at` given: a waypoint on the trunk, or a lane U within a lane run of the
  trunk. Anything else is refused with the trunk in words: "left-front U24 is
  not on Bundle 2's route, which runs mgr-1 ring 5 > left-front U20-U30 >
  pp-1 ring 1."
- `end` (`a` or `b`) is the end the cable heads for after it leaves. When left
  out, it is the end whose port is nearer `at` by the rack's own measure, and
  the summary names it: "c7 leaves Bundle 2 at left-front U24 for its b end."
- A peel point that would leave the cable no run in the bundle (its `a` point
  at or past its `b` point along the trunk) is refused.

### 3.4 `bundle.update`

Description: *"Change a bundle's label, number or strap spacing, or route it by
hand. A route of null works the route out again from its cables."*

- `straps: {every: {value, unit}}`, or `{every: null}` for none. The value is
  above 0. A spacing under 50 mm or over 1 m is accepted with a note, since
  either is more likely a unit slip than intent.
- `route: [...]` replaces the trunk and is checked as in `bundle.create`.
  `route: null` works it out again (section 4.1). Peel points no longer on the
  new trunk are cleared, with a note naming the cables.
- `summary`, as on `cable.route`: the page names its own edits.

### 3.5 `bundle.remove`

Description: *"Dissolve a bundle. Its cables are kept and follow their own
routes again."*

Cables are never removed by it. A member's own route, automatic or edited, is
what it follows afterwards.

### 3.6 Commands that already exist

- `cable.remove`, and `remove` with `cables: 'remove'`: remove the cable from
  its bundle too (section 2.2).
- `cable.route` on a member: accepted. While the cable is bundled, its own
  route decides only its lead-in and lead-out (section 4.2), and the finding
  says so: "c3 follows Bundle 2 from mgr-1 ring 5 to pp-1 ring 1; this route
  applies outside it."
- `cable.update` re-pointing an end (0.4.0): the cable stays in its bundle,
  with a note if the new end's port is on another device.
- `frame` shrinking the rack: a trunk lane waypoint past the new top no longer
  resolves and is skipped, with the existing "waypoint is gone" note.

## 4. The trunk, the members' routes, and peel-off

### 4.1 The trunk

The trunk is **stored**: worked out once, at `bundle.create` or `bundle.update
{route: null}`, and then kept (decision 7). A bundle is dressed once, and
should not move when a device does. This matches the site's rule for an edited
cable route: moving a device never rewrites a stored route.

Working it out:

1. Take each member's own route, as `resolveRoute` gives it with no bundle in
   play.
2. A lane run counts by its U interval, so two cables going up `left-front`
   from U20 and from U22 to U30 share `left-front` U22 to U30.
3. The trunk is every waypoint and lane interval that two or more members
   share, in route order, joined into one path.
4. If the shared parts branch (some members go one way past a point and some
   another), it is refused, naming where: "c3 and c9 part at left-front U24.
   Bundle them separately, or give the bundle a route."

### 4.2 A member's route

`resolveRoute(rack, cable, ctx)` becomes bundle-aware, so the 2D and 3D
drawings, routed length, fill, `inspect` and the cable schedule all follow the
bundle with no change of their own. A member's route is:

> its own route up to where it joins the trunk, then the trunk to where it
> leaves, then its own route on to its far port.

- **Join and leave.** By default, a member joins where its own route first
  meets the trunk and leaves where its own route last does. A member going to a
  device at U24, in a trunk up to U30, therefore leaves at U24 by itself, with
  no peel point stored.
- **Peel points.** A member's `a` or `b` overrides that end: it leaves the
  trunk there, at the trunk waypoint or lane U named.
- **No meeting point.** A member whose own route never meets the trunk (added
  later, or after a reroute) rides all of it, and runs from each port straight
  to the trunk's nearer end. A finding says so.
- **Orientation.** The order of a member's on-trunk waypoints tells which trunk
  end its `a` end is at. With none, the trunk end nearer its `a` port is.
- **After it leaves,** a member runs from its leave point to the next waypoint
  of its own route that is not on the trunk, then along its own route. With
  none, it runs straight to its port.

`resolveRoute` reports a member's `bundle`, `join` and `leave` with its
waypoints, so a drawing can tell the bundled part from the leads.

**A member's routed length changes** when its bundle's trunk differs from its
own route, because the length is measured along the route it follows. This is
intended: the cable has to reach along the bundle.

### 4.3 What peel-off means at a waypoint

Peeling a cable at a waypoint means it is strapped in the bundle up to that
waypoint, and from there it is loose and on its own. Past the peel point:

- it is not counted in the bundle's size or bend radius;
- it is not under the bundle's straps;
- it is drawn as its own cable;
- it is counted in a pathway's fill, as it always was.

A bundle's size and bend radius therefore vary along the trunk. Each check
counts only the members present at that point.

### 4.4 Pathways, including zero-U ducts

The size check asks a pathway two things, as the site's routing design says
(section 1.1 there): where it is, and its aperture. One lookup,
`pathwaysOn(rack, trunk, ctx)`, returns each pathway the trunk passes, with its
`aperture` (`{w, h}`, or none) and a `radius` if it states one. Rings and ducts
come from `ctx.guidesOf` and pass-throughs from their rect, as for fill.

#926 runs a lane through a vertical duct's centre line where a zero-U duct
stands beside the rails. The lookup then also returns that duct for the lane
interval it covers, with the duct's aperture, so a bundle through a vertical
manager is checked without changing the bundle code. Until #926 lands, lanes
have no aperture and do not limit a bundle.

### 4.5 A bundle of fewer than two cables

It is kept, listed, not drawn, and has no straps. Each command that leaves it
so says "Bundle 2 now holds one cable." `describe` and `inspect` show it
(decision 5).

## 5. The checks

Both checks **warn and never refuse** (decision 2). Like fill, they depend
on things outside the bundle commands: a device moving, a cable's media
changing, or a route being edited can each push a bundle over. So a bundle
must be able to sit over the limit, and the warnings must be shown. That
follows the site's routing design, D4: a full pathway warns, never refuses.

Both run in a pure `bundleChecks(rack, ctx)` in `kit/rack/bundles.js`.
`ctx.route` (the routing readers 0.4.0's `inspect` takes) is needed, and for
the bend check so is `ctx.bendOf` (section 5.2). Without them, the commands
skip the checks, and `inspect` reports `checked: false` rather than a pass.
A bundle command's `findings` include the checks for the bundle it changed.

### 5.1 Size against apertures

**The bundle's diameter** at a point is estimated from the members present:

```
D = sqrt(sum(d_i^2) / BUNDLE_PACK)        BUNDLE_PACK = 0.8
```

`d_i` is each member's outside diameter. `BUNDLE_PACK` is the share of the
bundle's circle the cables fill, one named constant in `bundles.js` so it can
be tuned (decision 4). At 0.8 it assumes a tightly combed bundle: slightly
tighter than a perfect hexagonal pack of equal round cables, which fills 7/9,
19/25 and 37/49 of its circle for 7, 19 and 37 cables (0.78 down to 0.76). So
seven 6 mm cables come to about 17.7 mm, against 18 mm (3d) for the perfect
pack. Diameters come from #919's `od_mm` for the
member's type once it is published, and until then from `route.js`
`DIAMETERS`. A member of unknown type counts as 6.0 mm, the value fill uses,
and the result says it is an estimate and names the cable.

**The limit** at each pathway is the smaller of 63.5 mm and the aperture's
smaller side, `min(w, h)`: a round bundle has to pass the narrow way. A
pathway with no aperture limits only to 63.5 mm. Each pathway is checked with
the members present there.

Worked example: FS's D-ring opening is 32.0 x 29.5 mm, so a bundle through it
is held to 29.5 mm, which is 19 Cat6 cables at 6 mm (29.5^2 x 0.8 / 6^2 =
19.3) or 12 Cat6A at 7.5 mm (12.4). The 2.5 in limit alone allows 89 Cat6
(89.6).

A finding: "Bundle 2 is about 31 mm across at mgr-1 ring 5, whose opening is
29.5 mm across." A bundle over 63.5 mm anywhere also says so on its own line.

Fill (`route.js fill`) is unchanged and still counts each member as a cable.
The two checks answer different questions: fill asks whether everything
through a pathway fits, and size asks whether this bundle passes it.

### 5.2 Bend radius against corners and pathways

**The bundle's radius** at a point is the largest installed minimum bend
radius of the members present there, resolved by #919's kit helper (a multiple
of the type's typical outside diameter, or a fixed figure). Each multiple
applies to the member's own diameter, not the bundle's. With #897's researched
figures (placeholders until #919 publishes them), a bundle of Cat6 UTP
(4 x 6 mm = 24 mm) with one inside-plant two-fibre cable (25 mm) needs 25 mm.
The loaded radius is data only, as #897 says, and is not checked.

`ctx.bendOf(cable)` returns millimetres, or null when the cable has no type
or its type has no radius. The rack's cables carry `media` today, and each
media value names one of #919's types. #897's named types refine this later
without changing the check.

**What a corner allows.** The check measures the trunk the way routed length
does, in rack coordinates (`route.js pointOf`), so it agrees with the length
and with every view. At an interior trunk waypoint with turn angle θ, and the
adjoining straight runs `L_in` and `L_out`, the largest radius that fits is:

```
r_max = min(L_in, L_out) / 2 / tan(θ / 2)
```

A bend of radius `r` uses `r * tan(θ / 2)` of each adjoining run, and each run
is shared with the corner at its other end, so each corner may use half of it.
A straight pass (θ = 0) is not a corner. A right angle 60 mm from the next
corner allows 30 mm. The front-to-rear crossing at the top of a four-post rack
is two corners in depth, and is checked the same way.

**Pathways.** A pathway that states a radius (`radius` from section 4.4) is
also checked: a radius a bundle must keep through it, such as a waterfall or
bend-radius fingers. No guide states one today; the hook is there for when
one does (decision 8).

**Unknown types are unchecked, not passed.** At each point:

- every member present has a radius: checked;
- some have one: checked against those, and the result lists the rest as
  unchecked: "Bundle 2's bend is not checked for c5 and c9, which have no
  cable type.";
- none has one: the point is unchecked, never reported as passing.

A finding: "Bundle 2 turns at mgr-1 ring 1 with room for an 18 mm bend; c7
(OM4) needs 25 mm, 7 mm short." Each violation gives the location, the radius
needed, the room there, the shortfall, and the member that sets the need.

Single cables, and members' lead-ins and lead-outs, are not checked here. That
is the per-cable bend warning #919 leaves to a follow-up in the Rack Builder,
which can reuse `r_max`.

### 5.3 What an agent reads

- `inspect(rack, 'b1', ctx)`:

  ```js
  {kind: 'bundle', id, number, label, name,
   members: [{cable, a?, b?, join, leave}],
   route: {waypoints, text}, length: {metres} | null,
   size: {max_mm, at, limit_mm, limitBy, estimated: [ids]},
   bend: {radius_mm, by, unchecked: [ids]},
   straps: {every, count},
   warnings: [text], checked: bool}
  ```

- `inspect` of a cable gains `bundle: {id, join, leave}` when it is a member.
- `selectCables` gains `{bundle: 'b1'}`. A blank or non-string value is
  refused, as the other name selectors are.
- `describe` gains a `bundles` section beside `items` and `cables`, with the
  same window, and a total on its first line ("6 items, 40 cables, 3
  bundles"). One line per bundle: "b1 Bundle 1: 12 cables (c1-c12), about
  24 mm, straps every 12 in, 1 warning."

## 6. Straps along the route

`straps(rack, bundle, ctx)` in `bundles.js` places them along the trunk where
two or more members ride together:

- Each such run, of length `L`, gets `n = ceil(L / every)` straps, evenly
  spaced at `(k + 0.5) * L / n` for `k = 0 .. n-1`. Straps are then never more
  than the spacing apart, and none sits on the run's ends. A 30 in run at
  12 in gets 3 straps, 10 in apart (decision 3).
- A strap that falls inside a ring or a pass-through moves along the run until
  it is clear of it. Straps inside a duct stay.
- `L` uses the same rack measure as routed length, so the count agrees in
  every view and the BOM.

Each strap comes back as `{segment, t, along_mm}`: which trunk segment it is
on and how far along (0 to 1), plus its distance from the trunk's start. It is
not a coordinate, because 2D and 3D draw the same waypoints at their own
positions (2D at ring ends and gutter centres, 3D at guide anchors and
40 mm-offset lane points). Each view puts the strap on its own segment at `t`.

- **2D** (portrayal-site#142): the bundle's members are drawn combed side by
  side in member order, through each pane's waypoints, with corners drawn at
  least at the bundle's radius where the room allows. A strap is a short bar
  across the bundle. A segment in depth (front to rear) is seen in neither
  elevation, so its straps are counted but not drawn in 2D.
- **3D** (portrayal-site#142): the members are packed inside the bundle's
  diameter, in the grid the site already uses for cables sharing an opening. A
  strap is a band around the pack, its diameter the bundle's size at that
  point.

## 7. The cable list and the exports

| Where | Shows |
|---|---|
| Cable list (site, #142) | cables grouped by bundle, with the bundle's name, size and warnings; a peeled cable shows where it leaves |
| Rack JSON | `bundles` as stored (version 3) |
| Cable schedule CSV (#923) | a `bundle` column (the bundle's name); `route` is the route the member follows; one note per bundle: "Bundle 2 (b1): 12 cables; 2.4 m run; 8 straps every 12 in; about 24 mm across, limit 29.5 mm at mgr-1 ring 5; bend radius 25 mm (c7)" and its warnings |
| BOM (#923) | one line for hook-and-loop straps, with the quantity the sum of every bundle's count; no manufacturer (decision 6) |
| SVG / PNG sheets (#142) | bundles and straps as drawn; a note per bundle, and its warnings |
| GLB / USDZ (#142) | bundles and straps, as the scene |
| draw.io | unchanged, as for routes; a note says bundles are not drawn there |
| NetBox cables file (#923) | membership in the cable's `description`, after its purpose ("uplink. Bundle 2."), within the length the export already enforces |
| Nautobot cables file (#923) | no column for it, since the file writes no description; the export notes say membership is in the cable schedule |

The kit's import files have no field for a bundle. Membership goes in
NetBox's cable description, not in tags (decision 9). #923 checks NetBox's and
Nautobot's own models and records what each one can hold.

## 8. The child issues

| issue | builds | needs |
|---|---|---|
| #920 | this note | nothing |
| #919 | `cable-types.json`: per-type `od_mm` and minimum bend radius `{installed, loaded}`, sourced; the kit helper that resolves a type's installed radius in mm | nothing; the first slice of #897 |
| #921 | the bundle record and schema (version 3), `settleBundles`, the five commands, numbering and labels, the bundle-aware `resolveRoute`, the size check, strap positions, and `describe`, `inspect` and `selectCables` for bundles | #920, and kit 0.4.0 merged |
| #922 | the bend check (section 5.2): worst member against trunk corners and stated pathway radii, with unknown types unchecked; tests with mixed copper and fibre | #921 and #919 |
| portrayal-site#142 | bundles and straps drawn in 2D and 3D, the cable list grouped by bundle, the controls through the commands, size and bend warnings shown, and the bundle commands as WebMCP tools | #921 re-vendored; #922 for the bend warnings |
| #923 | bundles in the exports: schedule, BOM strap line, sheets notes, DCIM | #921 |

#926 is not a child, but bundles route through what it adds: a lane inside a
vertical duct is a pathway with an aperture (section 4.4). Whichever of #921
and #926 lands second takes the other's `pathwaysOn` and `describe` changes.

## 9. Out of scope

- A cable in two bundles one after the other, and bundles inside bundles.
- Bundles between racks; slack loops and service loops; lacing bars drawn as
  parts.
- Strap colour, length and width.
- The bend check on single cables and on members' lead-ins and lead-outs (the
  follow-up #919 names).
- #897's type pickers, colours and mismatch checks.

## 10. Decisions

Decided 2026-10-08, on the questions this note first left open.

1. **The rack document goes to version 3.** Decided: yes. An older `parseDoc`
   drops the `bundles` key and its next autosave erases the bundles, and an
   older page would route members alone. A refusal is better than silent loss,
   as for managers at version 2. #921 is therefore a one-way door (section 2.3).
2. **Over the limits: warn only.** Decided: the size and bend checks warn and
   never refuse, 2.5 in included. A member's media changing or a device moving
   can push a bundle over without any bundle command, so a bundle must be able
   to sit over the limit and say so; this matches fill, which also only warns.
3. **Straps evenly spaced.** Decided: evenly along each run, never more than
   the spacing apart, none on the run's ends. Strict 12 in steps from one end
   would leave an odd gap at the other.
4. **Packing share 0.8.** Decided: `BUNDLE_PACK = 0.8`, one named constant so it
   can be tuned. Bundles are drawn and checked as tightly combed; a looser
   figure would warn sooner (section 5.1).
5. **A bundle of fewer than two cables is kept, not drawn.** Decided: kept,
   listed and noted, with no drawing and no straps. Nothing the user made is
   removed as a side effect of another command.
6. **One BOM line for straps.** Decided: one generic hook-and-loop strap line
   with the total count. Strap length and width are left to the buyer.
7. **The trunk is stored at creation.** Decided: worked out once, at
   `bundle.create` or `bundle.update {route: null}`, then kept. A bundle is
   dressed once and should not change shape when a device moves.
8. **A guide radius key upstream: later.** Decided: not proposed now. The bend
   check keeps the hook (section 4.4), and the key is added when a part that
   needs it is modelled.
9. **DCIM: NetBox's cable description.** Decided: membership is written in
   NetBox's cable description, not as tags, which would have to be created
   before the import. Nautobot's file has no description, and its export notes
   say so.
10. **Strap spacing per bundle only.** Decided: each bundle has its own
    spacing, 12 in when unset. There is no rack-wide default.

# Cable bundles: bundles, Velcro straps and bend radius in the rack kit

Status: agreed 2026-10-08 (#920). #921 built the record, the commands, the
size check and the straps in kit 0.7.0 (section 11 says how); the bend check
(#922), the drawings (portrayal-site#142) and the exports (#923) are to come. Cable management piece 3,
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

- `parseDoc` reads shapes, as for cables: a bundle with no usable `id` or
  a duplicate one gets a fresh id; a member that is not `{cable: <string>}` is
  dropped from the array; `number` that is not a whole number from 1 is
  renumbered past the highest in use; `route` is read with `readRoute`, so an
  unreadable entry keeps the route as written in `routeAsWritten`, as on a
  cable. Unknown fields are kept.
- `settleBundles(rack)` checks references. It needs no catalogue (it reads
  only the rack's own cables, items and bundles), so **`parseDoc` runs it** on
  every rack, after reading the cables. A reader that only calls `parseDoc`
  therefore gets the same consistent rack as the editor. It is pure and
  idempotent, so running it again changes nothing, and gives no notes. The
  notes therefore come from the `parseDoc` call and travel with the document:
  - `parseDoc(input, {notes})` pushes each repair's sentence onto the `notes`
    array the caller passes. None is kept in the document. A document can hold
    several racks, so each sentence names its rack ("Rack 2: c9 is in
    Bundle 1 and Bundle 3, so it stays in Bundle 1.").
  - The editor's `loadDoc` gains the same option, `loadDoc(next, {notes})`, and
    returns those sentences in its `findings`, as notes, ahead of the
    `settleManagers` notices it already returns. `loadDoc` receives a document
    that is already parsed, so it does not run `settleBundles` again.
  - The page passes the array it gave `parseDoc` on to `loadDoc`. A reader that
    calls only `parseDoc` reads its own array.

  The repairs:
  - a member naming no cable is dropped;
  - a cable named by two bundles stays in the first;
  - a number used twice stays with the first, and the second is renumbered;
  - a bundle whose id is also an item's or a cable's id gets a fresh id, so an
    id names one thing (section 5.3).

  **A fresh bundle id** is `nextId` with the prefix `b` over every id in the
  rack: the items', the cables' and the bundles'. `settleBundles` and
  `bundle.create` both take it that way, so a new bundle can never take an id
  an item or a cable has.

  Nothing else is dropped, and a bundle left with no members is kept
  (section 4.5).
- **Removing a cable removes it from its bundle in the same step.** Cable ids
  come from `nextId`, which takes one past the highest, so a removed `c9` can
  be handed to the next cable; a bundle that still named `c9` would pick it up.
  `cable.remove`, `remove {cables: 'remove'}` and anything else that drops a
  cable go through one helper that does both, and the summary says so.
- **Ids in use count the bundles.** As `itemIdsInUse` counts the item ids a
  cable end names, a new `cableIdsInUse(rack)` counts every cable id a bundle
  member names, and `withCable` takes the next id past them. `itemIdsInUse`
  also counts every item id a bundle's trunk or peel point names
  (`{item, via}`), so a removed manager's id is not handed to the next device
  while a trunk still names it (section 4.6). The loader's repairs count the
  same ids, from the file as written:
  - `readItems`' `taken` list, which already holds the items' ids and the ids
    cable ends name, also holds the item ids of every trunk and peel point;
  - `readCables` is passed the bundles as written, `readCables(list,
    bundles)`, and its repair takes a fresh cable id past the ids their
    members name.

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

The bump takes effect as soon as a page is updated: `parseDoc` migrates every
document it opens and `serialize` writes `VERSION`, so the new page saves each
document it opens as version 3. After one visit, an older page still cached in
another tab refuses that document rather than reading it.

#926 adds `side` and the zero-U entry without a bump. `@portrayal/kit` 0.1.0
and 0.2.0 are on npm, but no published release contains `kit/rack` (0.3.0 and
later are unpublished), so no outside reader of the rack document exists yet.
Bundles bump anyway: a bundle is a rack key that an older `parseDoc` drops,
where `side` is an item key. The bump also protects #926's `side`: a version-2
page, whose `readItem` drops `side`, refuses a version-3 document instead of
opening it and erasing `side` on its next save.

## 3. The commands

Five commands join `COMMANDS` in `kit/rack/commands.js`. Like the others, each
is pure: the rack, its arguments and `ctx` go in, and a new rack or an
`{error}` sentence comes out. Each is one undo step through `apply`; the
history stores whole racks, so undo needs nothing new. Each follows the 0.4.0
rules: a description of 500 characters or less that names no function or page,
argument descriptions of 150 characters or less that state their defaults, and
`findings` for what changed underneath.

### 3.1 The context

Every bundle command and query reads one context shape, the one 0.4.0's
`inspect` already takes:

```js
ctx = {chassisOf,   // the editor's own; always present
       route,       // the routing readers: {chassisOf, guidesOf, portX, portY?}
       bendOf}      // cable => installed minimum bend radius in mm, or null
```

- `ctx.route` is the routing context that `resolveRoute`, `pointOf`,
  `portPoint`, `fill` and `routedLength` take as their own `ctx` argument.
  Nothing in the bundle code reads a flat `ctx.guidesOf`: `pathwaysOn`,
  `bundleChecks` and `straps` take `ctx` and read `ctx.route`.
- `ctx.bendOf` wraps #919's helper over the published cable types
  (section 5.2).
- **Neither exists in the editor.** The editor holds only `{chassisOf}`. The
  routing readers come from the page's drawings, so they exist only after a
  render has fetched the faces (the site's `route-context.js`,
  `routeFacts(...).ctx`). The caller passes both through 0.4.0's per-call
  context, `ed.apply(cmds, {ctx: {route, bendOf}})`, and the same way to
  `preview`. `inspect` and `describe` are module functions in `queries.js`,
  not editor methods, so their caller builds the whole `{chassisOf, route,
  bendOf}` itself and passes it. **portrayal-site#142 passes the last
  render's `route` and `bendOf` on every bundle command and query**, from the
  page's own controls and from its WebMCP tools alike. Tests build them from
  fixtures.
- A reader that throws counts as missing, as in 0.4.0's `inspect`: not
  measured, never an error.
- **Waypoint checks.** 0.4.0's `waypointError` reads a flat `guidesOf` from the
  context it is given. The bundle commands call it with `{chassisOf, guidesOf:
  ctx.route?.guidesOf}`. #921 changes `cable.route` to do the same, reading
  `ctx.route.guidesOf` and keeping a flat `ctx.guidesOf` as a fallback for
  0.4.0 callers, so a `cable.route` and a bundle command in one batch check
  waypoints against the same readers.

What needs the routing readers, and what each command does without them:

| command | without `ctx.route` |
|---|---|
| `bundle.create` with no `route` | refused: "The cables' routes are not known here, so the bundle needs a route." |
| `bundle.create` with `route` | made; its waypoints are checked as 0.4.0's `cable.route` checks them without `guidesOf` (against the catalogue's pathways) |
| `bundle.add` | made; membership needs no route |
| `bundle.peel` with no `at` | made |
| `bundle.peel` with `at` | `at` is checked against the stored trunk, which needs no readers. `end` is then required, and refused when left out: "Say which end c7 heads for, a or b: the routes are not known here." Whether `at` is at or past the member's peel point for its other end depends on which way the member runs along the trunk, which needs its route, so when it has one the peel is refused: "c7 already leaves Bundle 2 at pp-1 ring 1 for its a end; the routes are not known here to check this against it." |
| `bundle.update {route: null}` | refused, as `bundle.create` with no `route` |
| `bundle.update`, any other argument | made |
| `bundle.remove` | made |

When `ctx.route` is missing, a command that changes a bundle adds one finding
in place of the checks: "Bundle 2 is not checked for size or bend: the routes
are not known here." With `ctx.route` but no `ctx.bendOf`, size is checked and
every member is unchecked for bend ("the cable types are not loaded").

`describe(rack, ctx, window)` takes the same `ctx`. `SECTIONS` becomes
`['items', 'cables', 'bundles']`, and the refusal for any other section reads
"There is no section X. Ask for items, cables or bundles, or leave it out for
all three." A bundle line gives size and warnings only when `ctx.route` is
given, and otherwise ends "not checked" (section 5.3).

### 3.2 The five commands

Batches: `resolve` swaps `"@name"` for an id in `id` and in a cable end's
`item` today. It also swaps the `cable` argument, each entry of `cables`, and
the `item` of every waypoint in a `route` and in `at`. So one batch can place a
manager, add cables, and bundle them through the manager's rings. The same
waypoint swap applies to `cable.route`.

| command | arguments | does |
|---|---|---|
| `bundle.create` | `cables` (two or more ids), `label`, `number`, `route`, `straps`, `as` | makes a bundle of those cables |
| `bundle.add` | `id`, `cables` | adds cables; a member named again rides the whole trunk again |
| `bundle.peel` | `id`, `cable`, `at`, `end` | takes a cable out, or out from a waypoint on toward one end |
| `bundle.update` | `id`, `label`, `number`, `straps`, `route`, `summary` | renames, renumbers, sets the spacing, or reroutes the trunk |
| `bundle.remove` | `id` | dissolves the bundle; the cables stay as they are |

Every command that takes a bundle `id` refuses a missing one with
`BUNDLE_GONE`, "That bundle is no longer in the rack." (section 5.3).

### 3.3 `bundle.create`

Description: *"Bundle two or more cables sharing part of their route. It runs
where they run together, unless given a route. Refused for a bundled cable."*

- `route` left out: the trunk is worked out from the members' own routes, with
  the refusals section 4.1 lists (a fork, leaving and rejoining, groups that
  share nothing, a member that shares nothing). Without `ctx.route` it is
  refused (section 3.1).
- `route` given: checked as `cable.route` checks a route in 0.4.0 (the shapes,
  then each waypoint against the rack's pathways and lanes).
- Refusals: a cable that is gone (`CABLE_GONE`); a cable named twice; "c3 is
  already in Bundle 2. Peel it off first."; "Bundle 4 is already b2's number."
- Summary: "Bundled 12 cables as Bundle 3." `created: {id}`.

### 3.4 `bundle.add`

Description: *"Add cables to a bundle. A cable already in it rides the whole
bundle again. Refused for a cable in another bundle."*

- A cable in this bundle has its peel points cleared; if it had none and every
  cable named is already a member, nothing changes.
- The trunk is not rerouted. A new member whose own route never meets the
  trunk runs to it directly (section 4.2), and a finding says so.

### 3.5 `bundle.peel`

Description: *"Take a cable out of a bundle. With at, it stays bundled up to
that waypoint, then runs on its own to one end."*

- `at` left out: the cable leaves the bundle and follows its own route again.
- `at` given: a waypoint on the trunk, or a lane U within a lane run of the
  trunk. Anything else is refused with the trunk in words: "left-front U24 is
  not on Bundle 2's route, which runs mgr-1 ring 5 > left-front U20-U30 >
  pp-1 ring 1."
- `end` (`a` or `b`) is the end the cable heads for after it leaves. When left
  out, it is the end whose port is nearer `at` by the rack's own measure, and
  the summary names it: "c7 leaves Bundle 2 at left-front U24 for its b end."
  That measure needs `ctx.route`; without it, `end` is required (section 3.1).
- A peel point that would leave the cable no run in the bundle (its `a` point
  at or past its `b` point along the trunk, in the direction the member runs)
  is refused. The direction comes from the member's route, so it needs
  `ctx.route`; without it, a peel for one end of a member that already has a
  peel point for its other end is refused (section 3.1). A pair in the wrong
  order from a file is stale (section 4.6).

### 3.6 `bundle.update`

Description: *"Change a bundle's label, number or strap spacing, or route it by
hand. A route of null works the route out again from its cables."*

- `straps: {every: {value, unit}}`, or `{every: null}` for none. The value is
  above 0. A spacing under 50 mm or over 1 m is accepted with a note, since
  either is more likely a unit slip than intent.
- `route: [...]` replaces the trunk and is checked as in `bundle.create`.
  `route: null` works it out again (section 4.1). Peel points no longer on the
  new trunk are cleared, with a note naming the cables.
- `summary`, as on `cable.route`: the page names its own edits.

### 3.7 `bundle.remove`

Description: *"Dissolve a bundle. Its cables are kept and follow their own
routes again."*

Cables are never removed by it. A member's own route, automatic or edited, is
what it follows afterwards.

### 3.8 Commands that already exist

- `cable.remove`, and `remove` with `cables: 'remove'`: remove the cable from
  its bundle too (section 2.2).
- `cable.route` on a member: accepted. While the cable is bundled, its own
  route decides only its lead-in and lead-out (section 4.2), and the finding
  says so: "c3 follows Bundle 2 from mgr-1 ring 5 to pp-1 ring 1; this route
  applies outside it."
- `cable.update` re-pointing an end (0.4.0): the cable stays in its bundle,
  with a note if the new end's port is on another device.
- `frame` shrinking the rack: a trunk lane waypoint past the new top no longer
  resolves and is skipped. `frame` itself says nothing of it, as today for a
  cable's route. The export notes say it: `fillNotes` in `export-data.js`
  already writes "Cable c4: waypoint ... is gone, so the route skips it.", and
  gains the same line for a trunk ("Bundle 2: waypoint left-front U44 is gone,
  so the route skips it."). `inspect` of the bundle lists it under `gone`.

## 4. The trunk, the members' routes, and peel-off

### 4.1 The trunk

The trunk is **stored**: worked out once, at `bundle.create` or `bundle.update
{route: null}`, and then kept (decision 7). A bundle is dressed once, and
should not move when a device does. This matches the site's rule for an edited
cable route: moving a device never rewrites a stored route.

Working it out needs `ctx.route` (section 3.1):

1. **Own routes.** Take each member's own route, as `resolveRoute` gives it
   with no bundle in play, as a sequence from its `a` port to its `b` port.
2. **Elements.** A pathway waypoint (`{item, via}`) is one element. A lane run
   is cut into U intervals at every U where any member's run on that lane
   starts or stops, and each interval is one element. So two cables going up
   `left-front`, one from U20 and one from U22, both to U30, both use the
   element `left-front` U22-U30.
3. **Shared elements** are those used by two or more members.
4. **Joins.** Two shared elements are joined where they are next to each
   other on some member's route, counting only its shared elements. The joins
   are a set with no direction: a join that another member has already made
   adds nothing, and is never a loop. A member **goes directly** between two
   joined elements when nothing lies between them on its own route; when
   unshared elements lie between them (it passes A, then X used by no other
   member, then B), it **detours**. The shape is judged in this order, and the
   refusals name no single cable as the culprit when the parting is mutual:
   - **A detour means parting and meeting again.** A member that detours
     between two shared elements leaves the others at the first and meets them
     at the second. Refused, naming it and the other members that pass both elements, directly or through other shared elements:
     "c4 parts from c1, c2 and c3 at mgr-1 ring 3 and meets them again at
     left-front U20.", then "Bundle them separately, or give the bundle a
     route." The
     same holds with only two members: with c1 through ring 3, ring 4, ring 5
     and the lane, and c2 from ring 3 straight to the lane, the trunk would be
     c2's straight run and c1 would be pulled off its rings, so it is refused
     ("c1 parts from c2 at mgr-1 ring 3 ..."). If every member making a join
     detours, and the two elements are joined by no other route through shared
     elements, the join is a run no cable takes, and it is refused for the
     reason step 6 gives.
   - **A loop means parting and meeting again without a detour:** a member
     goes directly between two elements that others reach through further
     shared elements. Refused, naming the member that makes the loop's join
     with the fewest members; a tie goes to the join that comes first in path
     order, and those it parts from, so the blame does not
     depend on the order the cables were named. Example: c1, c2 and c3 run
     ring 3, ring 4, ring 5, then the lane L; c4 runs ring 3, then straight to
     L. The loop is ring 3, 4, 5, L and back to ring 3; its join ring 3 to L is
     made by c4 alone, and every other join by three cables, so the message
     is "c4 parts from c1, c2 and c3 at mgr-1 ring 3 and meets them again at
     left-front U20", whichever cable was named first. (If c4 passes an
     element of its own between ring 3 and L, it is the detour above.)
   - **A fork:** with no loop, an element joined to three or more others, so
     the members go on different ways from it. Refused, listing the cables on
     each branch as found: "Bundle members part after left-front U30: c1 and c2
     go on to pp-1 ring 1; c3 and c4 go on to left-rear U30.", then "Bundle
     them separately, or give the bundle a route."
   - Otherwise the shape is **one simple path**, and each member's shared
     elements are an unbroken stretch of it (a gap would have been a detour or
     a loop). Members may join the path and leave it anywhere along it:
     fan-in at a lacer's successive rings, and fan-out to devices along a
     lane, are both legal.
5. **Direction.** The path is oriented by the first cable named that meets
   two or more of its elements: it runs the way that cable runs, from its `a`
   end to its `b` end. Each other member's direction is read off the order in
   which its route meets the path. A member that meets the path at one
   element only joins and leaves there.
6. **Disconnected groups are refused.** "c1 and c2 share mgr-1 ring 5, and c3
   and c4 share pp-1 ring 9, but the two groups share nothing.", then "Bundle
   them separately, or give the bundle a route." Joining across the gap would
   invent a run that none of these cables takes, which changes their lengths
   and puts straps where no cable goes. Two groups that share nothing are two
   bundles, and the refusal says so. A given `route` remains the way to make
   one bundle of them on purpose.
7. **A member sharing nothing** with any other is refused: "c7 runs with none
   of the others. Leave it out, or give the bundle a route."
8. **The trunk** is the path, as waypoints in order. Lane intervals are
   written back as `{lane, ru}` waypoints at their ends, merged where they
   meet.

### 4.2 A member's route

`resolveRoute(rack, cable, ctx.route)` becomes bundle-aware, so the 2D and 3D
drawings, routed length, fill, `inspect` and the cable schedule all follow the
bundle with no change of their own. A member's route is:

> its own route up to where it joins the trunk, then the trunk to where it
> leaves, then its own route on to its far port.

- **Meeting the trunk** is defined on the elements of section 4.1. A member
  meets the trunk at a pathway waypoint both pass through, and on a lane where
  its own run on that lane overlaps the trunk's in U. On a lane, the meeting
  point is the first overlapping U in the direction the member is running, and
  it leaves the lane run at the last overlapping U.
- **Join and leave.** By default, a member joins where its own route first
  meets the trunk and leaves where its own route last does. A member going to a
  device at U24, in a trunk up to U30, therefore leaves at U24 by itself, with
  no peel point stored.
- **Peel points.** A member's `a` or `b` overrides that end: it leaves the
  trunk there, at the trunk waypoint or lane U named.
- **No meeting point.** A member whose own route never meets the trunk (added
  later, or after a reroute) rides all of it, and runs from each port straight
  to the trunk's nearer end. A finding says so. This is accepted as a sketch,
  even when a port is on the other face and the straight run goes through the
  rack's depth: the length is measured along that run, and the finding names
  the member so it can be routed by hand.
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

**At the peel point itself,** and likewise at a member's join point, the
member is in the pathway there, so it **counts in the size** at that point. It
does **not count in the bend** at that point: it does not follow the bundle's
turn there but makes its own, which is its lead's turn and is checked per
cable, not here (section 5.2).

### 4.4 Pathways, including zero-U ducts

The size check asks a pathway two things, as the site's routing design says
(section 1.1 there): where it is, and its aperture. One lookup,
`pathwaysOn(rack, trunk, ctx)`, returns each pathway the trunk passes, with its
`aperture` (`{w, h}`, or none) and a `radius` if it states one. Rings, ducts
and pass-throughs come from `ctx.route.guidesOf`, as for fill: a ring's
aperture is its component's, and a pass-through's is its rect.

A duct's aperture is not stated by any part today, so it is estimated, and an
estimate must be told apart from a stated aperture. The site's
`guidesFromRects` (`route-context.js`) gives every duct guide `{w: r.h,
h: r.h}`, a square on its drawn height. That changes, in portrayal-site#142:
- each guide also carries its `run` (`x` or `y`), read from `data-guide-run`;
- an estimated aperture carries `estimated: true`;
- the square on the drawn height is given only to a duct that runs along `x`
  (a horizontal duct). A duct that runs along `y` gets no estimate from the
  site; the kit makes its own (below).

#926 runs a lane through a vertical duct's centre line where a zero-U duct
stands beside the rails. The lookup then also returns that duct for the lane
interval it covers, so a bundle through a vertical manager is checked without
changing the bundle code. The square estimate does not work there, because a
vertical duct's drawn height is its length. Its cross-section is taken as:

- `w`: the duct guide's width across its run, from its `guide--<via>` rect on
  the compiled face (the channel between the finger rows);
- `h`: the part's depth, `d` in its catalogue entry. That is the overall depth,
  fingers and cover included, so it is an upper bound, and the result is
  marked estimated.

An aperture without `estimated` is stated by the part, and wins over either
estimate. A check against an estimated aperture says so in its finding. Until
#926 lands, lanes have no aperture and do not limit a bundle.

### 4.5 A bundle of fewer than two cables

It is kept, listed, not drawn, and has no straps. Each command that leaves it
so says "Bundle 2 now holds one cable." `describe` and `inspect` show it
(decision 5).

### 4.6 Edge cases

- **A stale peel point,** one no longer on the trunk (from a hand-edited file,
  or on a trunk waypoint that no longer resolves), or either of a pair whose
  `a` point is at or past its `b` point, is ignored with a note: "c7's
  peel point left-front U24 is not on Bundle 2's route, so it rides to the
  end." It is kept in the file, as a waypoint that no longer resolves is kept
  on a cable, and the next `bundle.peel` or `bundle.add` for that cable
  replaces it. `bundle.update {route}` clears the peel points the new trunk
  does not hold (section 3.6), since that edit is the one that made them
  stale.
- **A trunk waypoint whose device was removed** stays in the trunk and is
  skipped, with the gone-waypoint note (section 3.8). Its id is not reused
  while the trunk names it (section 2.2), so it can never resolve to a
  different device placed later.
- **A member at its peel or join point** counts in the size there and not in
  the bend there (section 4.3).
- **A member with no meeting point** runs straight to the trunk, as a sketch
  (section 4.2).

## 5. The checks

Both checks **warn and never refuse** (decision 2). Like fill, they depend
on things outside the bundle commands: a device moving, a cable's media
changing, or a route being edited can each push a bundle over. So a bundle
must be able to sit over the limit, and the warnings must be shown. That
follows the site's routing design, D4: a full pathway warns, never refuses.

Both run in a pure `bundleChecks(rack, ctx)` in `kit/rack/bundles.js`, with
the context of section 3.1: the size check reads `ctx.route`, and the bend
check reads `ctx.route` and `ctx.bendOf`. Without them, the commands skip the
checks with the one finding section 3.1 gives, and `inspect` reports
`checked: false` rather than a pass. A bundle command's `findings` include the
checks for the bundle it changed.

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
does, in rack coordinates (`route.js pointOf` on `ctx.route`), so it agrees
with the length and with every view.

1. **The polyline** is the trunk's waypoints, in order, as points.
2. **Straight passes are merged.** Walking the polyline, a waypoint is a
   straight pass, not a corner, when the next segment's direction is within 1
   degree of the leg's direction: the direction from the last corner (or the
   trunk's start) to this waypoint. Measuring against the leg, not the
   previous segment, means many small turns add up to a corner instead of
   passing one by one. A row of rings in line, then a turn into a lane, is one
   straight leg and one corner.
3. **Corners** are the remaining interior points. θ is the turn angle there,
   from 0 (straight on) to 180 degrees (back on itself).
4. **Legs.** `L_in` and `L_out` are the distances along the trunk to the
   neighbouring corner on each side, through any straight passes, or to the
   trunk's end where there is no further corner. Peel and join points do not
   cut a leg: they do not change the trunk's shape.
5. **The share of a leg.** A leg between two corners is shared, so each corner
   may use half of it: `a = L / 2`. A leg that ends at the trunk's end has no
   other bend of the bundle on it (the members' turns there are their leads'),
   so the corner may use all of it: `a = L`.

The largest radius that fits is:

```
r_max = min(a_in, a_out) / tan(θ / 2)
```

A bend of radius `r` uses `r * tan(θ / 2)` of each leg. A right angle with
120 mm to the next corner on each side allows 60 mm: half of 120, over
tan 45° = 1. As θ approaches 180 degrees, `tan(θ / 2)` grows without bound and
`r_max` falls to 0, so a trunk that doubles back on itself is always reported:
a bundle cannot fold back at a point. The front-to-rear crossing at the top of
a four-post rack is two corners in depth, and is checked the same way.

The need at a corner is the largest radius among the members present there,
not counting a member whose peel or join point the corner is (section 4.3).

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

  It also lists `gone`, the trunk waypoints that no longer resolve.
- `inspect` looks an id up as an item, then a cable, then a bundle. Since
  `settleBundles` gives a bundle a fresh id when an item or cable already has
  its id (section 2.2), only one of them can match. A missing id is refused as
  today, with `BUNDLE_GONE` ("That bundle is no longer in the rack.") for an id
  of the form `b<number>`, exported beside `GONE` and `CABLE_GONE`.
- `inspect` of a cable gains `bundle: {id, join, leave}` when it is a member.
- `selectCables` gains `{bundle: 'b1'}`. A blank or non-string value is
  refused, as the other name selectors are.
- `describe` gains a `bundles` section beside `items` and `cables`, with the
  same window, and a total on its first line ("6 items, 40 cables, 3
  bundles"). One line per bundle. With `ctx.route`: "b1 Bundle 1: 12 cables
  (c1-c12), about 23 mm, straps every 12 in, 1 warning." Without it: "b1
  Bundle 1: 12 cables (c1-c12), straps every 12 in, not checked." (Twelve 6 mm
  Cat6 come to the square root of 12 x 36 / 0.8, 23.2 mm.)

## 6. Straps along the route

`straps(rack, bundle, ctx)` in `bundles.js` places them along the trunk,
reading `ctx.route`:

- **A run** is a longest stretch of the trunk along which two or more members
  ride together. It goes on through rings, straight passes and corners, and is
  not cut at each waypoint. A bundle usually has one run, the whole trunk; it
  has more only where fan-out leaves fewer than two members for a stretch.
- Each run, of length `L`, gets `n = ceil(L / every)` straps, evenly spaced at
  `(k + 0.5) * L / n` for `k = 0 .. n-1`. Straps are then never more than the
  spacing apart, and none sits on the run's ends. A 30 in run at 12 in gets 3
  straps, 10 in apart (decision 3).
- **Rings and pass-throughs.** A ring or pass-through takes up a stretch of
  the trunk, from its guide's `box` (which `ctx.route.guidesOf` already gives
  each guide):
  - The box is in the face's own coordinates. It is mapped to rack
    coordinates as the guide's `x` already is: offset by half the face's
    width, and mirrored for a panel seen from the rear, which a turned item
    swaps. Its height maps as the routing context's `portY` maps a port: the
    face is drawn centred, unscaled, in the item's U span, so a face `y` is at
    height `(ru - 1 + u) * RU - ((u * RU - faceH) / 2 + y)` above the floor,
    where `u` is the item's height in U and `faceH` the face's drawn height.
  - Its extent along the run is the box's width for a run along `x`, and its
    height for a run along `y`. A ring drawn as a group has `h: 0` and `y: 0`
    in its box, so only its width is known: it has an extent on a run along
    `x` and none otherwise.
  - A segment in depth (front to rear) passes no ring, so it has no such
    stretch.
  - Each stretch is widened each side by half a strap's width (`STRAP_W`,
    20 mm, a drawing figure). At a lacer's tight ring pitch the widened
    stretches overlap; overlapping stretches are merged into one first.
  - A strap that falls in a stretch moves to its nearer edge. Straps inside a
    duct stay.
- **A moved strap may widen a gap past the spacing,** by at most that
  stretch's length. The count is not raised for it: the count is what the BOM
  buys, and it stays `ceil(L / every)` whatever the rings do.
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
| Cable schedule CSV (#923) | a `bundle` column (the bundle's name), straight after `route`; `route` is the route the member follows; one note per bundle: "Bundle 2 (b1): 12 cables, 2.4 m, 8 straps every 12 in; 23 mm, limit 29.5 mm at mgr-1 ring 5; bend 25 mm (c7)" and its warnings |
| BOM (#923) | one line for hook-and-loop straps, with the quantity the sum of every bundle's count; no manufacturer (decision 6) |
| SVG / PNG sheets (#142) | bundles and straps as drawn; a note per bundle, and its warnings |
| GLB / USDZ (#142) | bundles and straps, as the scene |
| draw.io | unchanged, as for routes; a note says bundles are not drawn there |
| NetBox cables file (#923) | membership first in the cable's `description`: "Bundle 2. uplink. Length measured along its route." The export cuts an over-long description from its end (`cutTo`), so the bundle's name is what survives; a name longer than the whole limit is itself cut. The existing over-limit note, which says "its purpose is N characters", is reworded for the whole description: "Cable c3: its description (bundle, purpose and length note) is N characters and NetBox takes M, so the description is shortened to that." |
| Nautobot cables file (#923) | no column for it, since the file writes no description; the export notes say membership is in the cable schedule |

The kit's import files have no field for a bundle. Membership goes in
NetBox's cable description, not in tags (decision 9). #923 checks NetBox's and
Nautobot's own models and records what each one can hold.

**#923 is an export change.** The new `bundle` column moves `length_source`,
`status` and `notes` one place right in the cable schedule, and NetBox's cable
descriptions change. A consumer reading the schedule by column position, or
matching descriptions, gets a different file, so #923's pull request states
that as its merge danger.

## 8. The child issues

| issue | builds | needs |
|---|---|---|
| #920 | this note | nothing |
| #919 | `cable-types.json`: per-type `od_mm` and minimum bend radius `{installed, loaded}`, sourced; the kit helper that resolves a type's installed radius in mm | nothing; the first slice of #897 |
| #921 | the bundle record and schema (version 3, a one-way door), `settleBundles` in `parseDoc` with its notes through `loadDoc`, the context of section 3.1, the five commands, numbering and labels, the bundle-aware `resolveRoute`, the size check with the kit's vertical-duct estimate, strap positions, and `describe`, `inspect` and `selectCables` for bundles. Until #922 lands, `inspect` returns `bend: null`, and `bundleChecks` gives size findings only | #920, and kit 0.4.0 merged |
| #922 | the bend check (section 5.2): worst member against trunk corners and stated pathway radii, with unknown types unchecked; tests with mixed copper and fibre | #921 and #919 |
| portrayal-site#142 | bundles and straps drawn in 2D and 3D, the cable list grouped by bundle, the controls through the commands with the render's `route` and `bendOf` passed on each, size and bend warnings shown, the bundle commands as WebMCP tools, and `route-context.js`'s guides carrying `run` and marking an estimated duct aperture (section 4.4) | #921 re-vendored; #922 for the bend warnings |
| #923 | bundles in the exports: schedule, BOM strap line, sheets notes, DCIM. The schedule's per-bundle note leaves out the bend radius until #922 and #919 have landed | #921 |

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

## 11. As built in #921

What the build settled that the sections above leave to it:

- **Elements.** A lane run is cut at every U (a node at each U and a segment
  between each two), which shares exactly what cutting at every member's start
  and stop shares (section 4.1). The trunk is written back as a waypoint at
  each pathway and wherever a lane run starts, stops, turns or jumps.
- **A bundle of fewer than two cables** does not change its member's route:
  it is not drawn, so its cable is drawn and measured on its own route.
- **A peel point past the far end** of a member's run, not only a pair out of
  order, is stale and ignored with the same note.
- **Diameters.** `ctx.diameterOf` (`loadCableTypes(dist).diameterOf`, #919's
  `od_mm`) is read when the caller passes it; without it the figures are
  `route.js DIAMETERS`, then 6 mm, named as an estimate.
- **`pathwaysOn(rack, trunk, ctx)`** takes the trunk's resolved waypoints. A
  duct beside the rack is estimated from the channel width
  `ctx.route.zeroUAperture(entry)` reports and the part's catalogue depth,
  always marked estimated, since no zero-U part states an aperture today. A
  duct guide on a rack-face part with `run: 'y'` is estimated from its `box.w`
  and the part's depth.
- **Straps on rings.** A ring's stretch is centred on its waypoint's point
  (`route.js pointOf`), since a guide carries no face height to map its box's
  `y` from (section 6). Its extent is the box's width on a run along x and its
  height on one along y, each side from its own segment.
- **`describe`** keeps #926's `zeroU` section: `SECTIONS` is `items`, `zeroU`,
  `cables` and `bundles`, and the totals line counts bundles only when the rack
  has any, as it counts parts beside the rack.
- **A reader that throws** during a bundle command's waypoint check falls back
  to the catalogue's pathways, as a command without the readers does.

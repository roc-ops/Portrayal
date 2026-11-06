# Optical paths: modelling the glass, not the mapping

Design note for the FS.com FHD patch-panel line and the Smartoptics PPM family.
Written 2026-09-12 against `main` at 82811725. Nothing here is built yet.

## What is wrong

The library can draw a passive optical module and cannot say what it does.

`smartoptics/ppm-ocu-97-3@2` is a C-band tap. Its function - 97% of the light
carries on, 3% is bled to a monitor port - lives in an attr as the string
`coupling-ratio: '97/3'`, and the fact that one of its four bores terminates
nothing lives in a sentence:

> THE SECOND BORE IS DEAD. It is captioned NA and terminates nothing.

Neither is checkable. `ppm-ad1-1510@1` tags three adapters `role: osc / edfa /
line` and nothing says that OSC adds onto Line at 1511 nm while EDFA passes
through. The four DCMs are two-port pass-throughs whose entire purpose is an
attr. The A22 is a carrier full of the same.

The FS FHD line makes this unavoidable rather than merely untidy. **62 cassettes
and 15 adapter panels**, and the cassette is *internal fibre*: strands running
from front adapter positions to specific fibre positions in a rear MPO ferrule.
A port-to-port mapping table cannot express what any of them do:

| family | count | what a mapping table misses |
|---|---:|---|
| plain MTP->LC/SC/MDC breakout | 22 | nothing - this is the case a table handles |
| TAP | 14 | the split: one path in, live and monitor out, at 50/50 or 70/30 |
| splice | 11 | there is no rear connector at all; strands are spliced |
| custom (configure-to-order) | 7 | no fixed face; not modelled as concrete parts |
| conversion | 4 | fibres REGROUPED between MPO connectors, 4x6, 2x3, 1x3, 2x6 |
| MTP-to-MTP mesh | 4 | 8x8 and 4x4 crossovers |

**Plain breakouts are 35% of the catalogue.** A design that treats sequential
mapping as the case and everything else as an exception gets a third of the line
right.

## What this replaces

Three approaches were proposed and rejected before the fibre model was reached,
and they are recorded because the reasoning matters more than the conclusion:

1. **Derive the map from the hardware's numbering**, with explicit rows as an
   escape hatch. Compact, and optimised for the 35%.
2. **Explicit rows always.** Honest, and ~12 rows x 77 parts of data whose only
   content is "1,2,3,4...".
3. **Hang the relation off `connection-points`.** They already exist per
   connector and already carry `direction: front|rear`. Rejected because they are
   GEOMETRY - where a connector sits on a face - and hanging topology there makes
   every consumer of a position ignore a relation.

All three treat the mapping as the primary object. The hardware's primary object
is the glass, and the mapping is what you get when you ask where a strand
surfaces. Modelling the glass gets all 62 in one vocabulary, and it dissolves a
limitation the port-table approach had accepted: **polarity becomes derivable**.
Type A is straight-through, Type B is reversed, AF flips one end. Those are
statements about which rear fibre each front fibre reaches - unmodelable as an
attr, checkable as a graph.

## Decisions

Taken 2026-09-11/12, in this order:

| # | decision |
|---|---|
| 1 | The cassette rear is DRAWN, not merely declared - components gain a second face |
| 2 | Mapping, faces and the view they render into are designed as ONE architecture |
| 3 | The optical model is a GRAPH: a path may split, so taps and couplers are the same object as a breakout |
| 4 | The vocabulary covers optical paths generally, and the PPM family is retro-fitted in the same work |

## A. The optical model

**Fibre capacity lives on the connector, stated once.** `common/lc-duplex-adapter@6`
presents 2 fibre positions; an MPO-12 presents 12; an ST simplex presents 1. No
module restates it, and every module inherits a correction.

**The glass lives on the part that contains it**, as a new top-level `optical:`
block. Positions are addressed `<part-id>.<n>`, where the part id is the composed
`parts:` id already written and `n` is 1-based within that connector:

```yaml
optical:
  media: os2
  polarity: A                 # checked against the paths, or expanded into them
  paths:
    - {from: mtp-1.1, to: lc-1.1}
    - {from: mtp-1.2, to: lc-1.2}
```

**A path may split**, which is what makes the 14 TAP cassettes and the 2 OCU
couplers the same kind of object as a breakout:

```yaml
    - from: mtp-1.1
      to:
        - {at: live-1.1, ratio: 70}
        - {at: tap-1.1,  ratio: 30}
```

**A path may be wavelength-conditioned**, which is what makes `ppm-ad1-1510` and
`ppm-ad1-1625` expressible:

```yaml
    - {from: line.1, to: osc.1,  band: {centre-nm: 1511, width-nm: 13}}
    - {from: line.1, to: edfa.1}        # no band: carries the rest
```

**A path may combine**, which is the opposite of a split: several sources
landing on one destination. It is declared, with `combine` in place of `from`,
so that two strands in one bore stay an error everywhere else:

```yaml
    - combine:
        - {at: osc.2, band: {centre-nm: 1511, width-nm: 13}}
        - {at: edfa.2}                  # no band: carries the rest
      to: line.1
```

A combine is one of two kinds, and each source says which. A WAVELENGTH
combine is a filter: every source but at most one carries a `band`, and no two
carry the same one. A POWER combine is a coupler run backwards: every source
carries a `ratio`, the share of the coupler that leg owns, and the ratios sum
to 100. The two do not mix in one path. A combine has one destination, no
path-level `band`, and names no source twice (L171).

**A path states the way the light travels, and the glass does not care.** A
passive part is reciprocal. A split read from its far end is a power combine
with the same shares, and a wavelength combine read from its far end is the
banded legs of a drop. So `from`/`to` and `combine`/`to` record the direction
the vendor draws, and nothing downstream depends on it: every consumer asks
`optical.legs` for a path's legs and gets the same undirected pairs either way.
What direction decides is only which form is honest. One input feeding many
outputs is a split; many inputs feeding one output is a combine; an add/drop
filter is one of each, because its two line fibres carry light in opposite
directions.

**A position with no path is a declared dead end**, not a silence:

```yaml
  unused:
    common.2: three-port coupler in a four-bore faceplate
```

That is `ppm-ocu-97-3`'s sentence, promoted to a claim lint can test against the
paths in both directions - an unreached position without an entry is an error,
and an entry for a position a path DOES reach is also an error.

**Front versus rear is not declared.** A connector is rear because the rear face
composes it. That coupling is why decision 2 is right: pieces that look separable
share their most important fact.

## B. Faces

The library already solved "a part seen from another direction", and this
generalises it rather than inventing beside it.

Today a component says `plan: {ref: ...}` - *"this part seen from above, as
another component"* - and a bay says `plan: {view, at, in, under, mirror}` for
where that projection lands. The renderer emits it carrying `data-of` and no
data-path, so the part stays one part - selecting it marks its projections - and
the 3D kit builds nothing from it. Each face's tree still lists what that face
draws: a projected path the face does not also draw as a part is a row under
what it is drawn in - a cassette's back and its MTPs under the rear cutout they
are seen through - and a click on it selects it.

A bare `rear:` sibling handles one more direction and then stops scaling. So:

```yaml
faces:
  plan: {ref: dell/riser-card-14g@1}     # what `plan:` means today
  rear: {ref: fs/fhd-1mtp6lcd-rear@3}
```

with `plan:` kept as sugar for `faces.plan`. Blast radius is small - 13
components use `plan:`, 3 devices project one - and nothing has to change to keep
working.

### Where a rear face renders, and why not an interior view yet

A view's `face:` key is an enum of exactly the six box faces, and a view is
either NAMED after a face or declares itself a VARIANT of one (`front-lff-12` is
`face: front`). An interior view is neither.

**AN EARLIER DRAFT SAID THAT MADE IT EXPENSIVE, AND CHECKING SAYS OTHERWISE.**
View names are unconstrained - `views.propertyNames` is a bare `segment` and only
`front` is required - and the tools that care about faces iterate the canonical
names and IGNORE anything else. `capability.py` sizes a view from its own `size:`
first and only falls back to chassis dimensions for front/rear; its consistency
sets iterate the six by name; its level-2 check asks only that front and rear be
drawable. `dcim_export.py` reads ports from `("front", "rear")` and no other.
lint walks `views` generically. So an interior view would need no new schema
marker and no exclusions: a name, its own `size:`, and bays projecting into it.

What remains true is that it is UNPRECEDENTED - all 86 devices use the six
canonical names plus one declared variant, so a view that is neither would be the
first, and "nothing rejects it" is not the same as "something has exercised it".

The rear face therefore renders as a **component preview** for now, on its own
merits rather than on a cost that turned out not to exist: every component already
renders standalone, that is where a modeller looks, and it delivers the rear art
without this spec acquiring a second unproven mechanism. The interior view becomes
its own piece, with the FS drawer-open renders already staged as its evidence and
a smaller bill than first quoted.

## C. The DCIM projection

Researched against both platforms' issue trackers rather than invented. **Nothing
here needs inventing; both cases have upstream answers.**

| finding | state |
|---|---|
| netbox#20564 many-to-many pass-through mappings | **CLOSED/COMPLETED, milestone v4.5.0.** Replaces the FrontPort->RearPort FK+position with a bidirectional M2M. Stated use case: "crossover fiber modules... in datacenter Clos fabrics" - our conversion and mesh cassettes |
| netbox#21830 front ports without rear ports | CLOSED/NOT_PLANNED. We do not get to omit rear ports |
| netbox#10992 PON-tree multipath trace | CLOSED/NOT_PLANNED. Tracing THROUGH a split is unsupported |
| nautobot#1743 simplex fibres and breakout cables | **CLOSED/COMPLETED (epic).** Covers simplex strands, fibre splitters, breakout cables, tracing through them |
| nautobot#6911 PON splitter support | CLOSED/COMPLETED |

**`splice` is a real rear-port type**, shipping today in the devicetype-library's
ADC `PPP-SC-SM` module-type as `rear-ports: [{name, type: splice, positions: 1}]`.
That is upstream's own convention for our 11 splice cassettes.

The port-type enum covers **every connector in the catalogue**: `lc-upc`,
`lc-apc`, `sc-upc`, `sc-apc`, `mpo`, `st`, `fc-apc`, `lsh-apc`, `mdc`, `splice`.

So:

- **C1. Per-fibre granularity.** A rear MPO-12 exports as one rear port,
  `type: mpo`, `positions: 12`. Each front fibre exports as a front port named
  for its own number - which matches the vendor's 1..12 front labelling and the
  `1-12` stamped on the rear, and makes the projection LOSSLESS for the 22
  breakouts, 4 conversions and 4 mesh cassettes.
- **C2. Splice cassettes take `type: splice` on the rear port.**
- **C3. Taps export their ports; the ratio does not.** Live and monitor are both
  front ports, the trunk is the rear port, and the M2M model permits several
  front ports against one rear position. The ratio has no field in the type
  format, so it goes in `description` - the same place the vendor puts it.

  **Which end is the trunk is stated where no rear face says it.** A rear face
  is the trunk by construction. A single-faced module - a PPM coupler, a DCM,
  an add/drop filter, a tap with every connector on its front - names its
  common, network-side positions in `optical.trunk`, in `front-order`'s item
  grammar (a bare part id is all its positions, `dcm.2` is one). The projection
  puts them on rear ports exactly as it puts a rear-face connector there: one
  rear port per trunk part, named `<PART>-1` like `MTP-1`, its positions the
  part's trunk positions in order. The front ports keep the faceplate's own
  count, so an OCU's legs export as `3` and `4` beside the gap its common
  adapter leaves. Neither a part id (`common`, `split`) nor a path's direction
  could have answered this: a cassette's paths run from the front and a
  coupler's from the trunk. L129-L131 hold it (#246).

  **That list is the endpoint role, and there are two roles.** A position is a
  TRUNK when a rear face carries it or `optical.trunk` names it, and a BRANCH
  otherwise. There is no per-endpoint role key and no `branch` list: a second
  spelling of one fact is two answers waiting to disagree. The vendor's own
  words map onto the two, and the part's source decides how: a coupler's
  `common` port is its trunk and its `split` legs are branches, and a filter's
  line port is its trunk and its add, drop and express ports are branches. A
  tap lid that prints `IN`, `OUT` and `TAP` is read the same way when one is
  modelled, from the lid. A module with a rear face states nothing and
  projects as it always has.

- **C4. A combine exports as a split does.** Each source of a combine is one
  leg to its destination, so it is one row of the fibre map, carrying that
  source's `band` or `ratio`. A row is a binding between a front port and a
  rear position, not a direction, so a combine onto a trunk position and
  banded legs off it write the same rows. NetBox gets several front ports
  against one rear position, as for a split. Nautobot cannot spell that, so
  its type states no ports and points at the NetBox type and the fibre map.
  A combine's legs obey L130 like any other: each runs between the front and
  the trunk. Its fan may sit on either side. Sources on the front and the
  destination on the trunk is an add filter. Sources on the trunk and the
  destination on the front puts several rear positions on one front port.

### The mapping is a third export

**A NetBox front port carries no binding of its own.** The `front-port` schema
is `{name, type, positions}` with no `rear_port` key, consistent with #20564
having removed the FK. NetBox >= 4.6 keeps the binding in the module type
instead, as `port-mappings` (PortTemplateMapping): a list of `{front_port,
front_port_position, rear_port, rear_port_position}`. The NetBox module type
states one mapping per row of the fibre map below, in the map's order, so an
import of the type is self-contained. `ratio` and `band` have no field in a
mapping, so the fibre map stays the full record. A NetBox older than 4.6 has no
such key. The fibre map is also what a script applies there.

**Nautobot is the exception, and it was found by importing.** Its
FrontPortTemplate still has a non-null rear port and rear-port position, and its
library's front-port schema is `{name, type, rear_port, rear_port_position}`
with no `positions`. A NetBox-shaped front port fails the Nautobot import, so
the Nautobot document is written with the binding, read from the same rows as
the fibre map. One front port reaches one rear position there, which holds
every breakout, conversion, mesh and splice cassette as it stands. It does not
hold an MPO front connector against an MPO rear one; that pair is written as a
single position, and the fibres stay in the map. A split - several front ports
on one rear position, declared by a `ratio` or a `band` on the shared rows - has
no Nautobot spelling at all, so its Nautobot type states no front or rear ports
and says that they, and the split, are in the NetBox type and the fibre map. Two
front ports on one rear position with neither is a collision rather than a
split, and the export still stops on it rather than writing a file that cannot
load.

So it ships beside `exports/netbox/` and `exports/nautobot/` as a fibre map,
carrying the rows the M2M wants:

```yaml
model: FHD-1MTP6LCDOS2A
media: os2
polarity: A
rows:
  - {front: '{module}/1', front_position: 1, rear: '{module}/MTP-1', rear_position: 1}
  - {front: '{module}/2', front_position: 1, rear: '{module}/MTP-1', rear_position: 2}
```

with a `ratio` column where a path splits. The names are the module type's own,
`{module}` included, so a row is resolved against an installed module exactly as
its ports were: `{module}` becomes the position of the bay it sits in.

**There is no upstream schema for this artefact, so we are defining it.** It is
therefore GENERATED ONLY and never hand-edited, so the contracts stay the single
source and the file stays a projection; and it is deliberately boring - a flat
row list, no nesting - so feeding it to a script or the API is a five-line job.

### A cable in a rack names these ports (#1020)

A cable in a rack file lands on a PART: `bay-1/module/lc01` on the front
panel, `bay-1/module/b01` on the rear one. The module type does not name a
fibre port by its part, so a row of the DCIM cables file has to be given the
names above. The build publishes them per part, beside the fibre graph, as
`optical.ports` in `components.json`:

```json
"lc01":     {"front-ports": ["1", "2"]},
"rear:b01": {"rear-ports":  ["B01-1", "B01-1"]}
```

One entry for each position of the part, position 1 first, `null` where that
position is not in that list. The key is the part id, or `rear:<id>` for a
part of the rear face, as an endpoint spells it. `optical_ports.ports`, which
writes the type file, and `optical_ports.part_ports`, which writes this, are
two views of one walk, and the key is written only for a module whose glass is
projected, so a name here is a name in the type file. The kit reads the key
(`rack/ports.js` `fibrePorts`) and derives no name. It then looks each name up
in the type file of the target, as it does every other port, so a type that
Nautobot was given without its ports leaves the cable out with that reason.

| the end is on | it lands on | example, in `bay-1` |
|---|---|---|
| a duplex adapter on a front | two front ports, one a fibre | FHD-FAP12LCDXSMF `lc01`: `bay-1/1` and `bay-1/2` |
| a simplex adapter on a front | one front port | XMI1041CA `sc03`: its front port `3` |
| an MPO adapter on a front | one front port, a position a fibre | FHD-FAP12MTPHA `mtp02`: `bay-1/2` |
| an adapter on the back of a panel | one rear port; a duplex cord takes both positions of it | FHD-FAP12LCDXSMF `b01`: `bay-1/B01-1` |
| the trunk connector of a cassette | one rear port, every position | FHD-1MTP6LCDOS2A `mtp`: `bay-1/MTP-1` |
| a stated trunk part of a single-faced module | its rear port | a PPM coupler `common`: its rear port `COMMON-1` |
| a part that is a front port and a rear port at once (a DCM adapter) | nothing: the cable is left out, with the reason | |
| an optic in a cage, a jack, a port of a device | as before: the interface or port of that name | `port-1` |

A cable terminates on a port, never on a position of one, in both platforms.
So a duplex cord on a rear adapter and a twelve-fibre trunk on an MTP are each
one name, and nothing is said about positions.

**What each file writes for an end on two front ports.**

- **NetBox: one row a cord.** The name column holds both names, separated by
  a comma, under the one type `dcim.frontport`. The import form splits the
  cell on commas, wants one kind of port a side and one device or one a name,
  and asks no equal count of the two sides (NetBox v4.7.2, `251458b8`,
  `dcim/forms/bulk_import.py` `CableImportForm._clean_side` and
  `dcim/models/cables.py` `Cable.clean`). So an interface against two front
  ports is one row, and so is a rear port against two front ports. No cable
  profile is written.
- **Nautobot: one termination a side, so one row a fibre.** Where both ends
  have two ports the cord is two rows, first port to first port and second to
  second. Each row has the type, status, length and unit of the cord, and its
  label followed by ` (1/2)` or ` (2/2)`, which is what ties the rows: a
  Nautobot cable has no description to say it in. No two cords share that
  label: one too long for the suffix, or one that another such cord already
  has, is cut and given the id of its cable before the suffix, and a note
  says so.
- **Nautobot, a single port against two.** An optic is one interface and a
  rear adapter one rear port, and either can take one cable. The cord is
  written as one row, to the FIRST of the two front ports, and the README
  names each second port as having no cable in the file. **The trace then
  holds between like ends and not across unlike ones.** Two panels, or two
  cassettes of one type, bind the first front port to the same trunk
  position, and Nautobot traces the link end to end. A Type A cassette binds
  front port 1 to trunk position 1 and a Type AF one binds front port 1 to
  position 2 (`FHD-1MTP6LCDOS2A.yaml` and `FHD-1MTP6LCDOS2AF.yaml`), which is
  what a Method A link is made of. Across that pair the fibre arrives on
  front port 2 of the far cassette, which has no cable, and the trace stops
  there. The README says so beside the list of those ports; the second port
  is cabled by hand on such a link.
- Ends on two different counts of several ports have no such reading: NetBox
  takes the row, and the Nautobot file leaves the cord out and says why. No
  part in the library gives such an end today, a fibre part being one port
  or two; the rule is held by a test with a resolver of its own.

**First port to first port is an order, not a polarity.** The rack file does
not say whether a cord is crossed, so the two Nautobot rows pair the ports in
position order and claim nothing more.

**Nautobot could hold the cord as one cable, and the kit does not write it
so.** Nautobot 3.2.6 has cable types with several connectors a side
(`dcim/models/cables.py` `CableType`, `3dc554b4`), and front ports, rear ports
and interfaces may all end one. Such a type must exist before a cable names
it, and the script the Nautobot file is read by makes one termination a
side. The rows above need neither.

**Tried on running instances**, NetBox 4.7.2 and Nautobot 3.2.6, with the
type files of this repository, an enclosure holding an FHD-FAP12LCDXSMF panel
and an FHD-1MTP6LCDOS2A cassette, a second enclosure the same, and two
switches:

| the cable | NetBox 4.7.2 | Nautobot 3.2.6 |
|---|---|---|
| an optic to a panel front, duplex | accepted; the interface, and front ports 1 and 2 | accepted; the interface and front port 1 |
| a panel rear to an optic | accepted; rear port `B01-1` and the interface | accepted, the same |
| a cassette front to an optic | accepted; front ports 1 and 2, and the interface | accepted; front port 1 and the interface |
| an MTP trunk between two cassettes | accepted; `MTP-1` to `MTP-1` | accepted, the same |
| a panel front to a panel front | accepted; two front ports a side | two rows accepted, 3 to 3 and 4 to 4 |
| a panel rear to a panel front | accepted; one rear port and two front ports | accepted; the rear port and front port 5 |
| a second cable on a fibre already used | refused: "is already connected" | refused: "already has a cable attached" |

The NetBox file went through the cable import form, each row alone and then
the file whole, and every row was accepted. Read back, each cable sat on the
ports its row named. NetBox showed the far port of each cable and no path
beyond the panel: its module types carry no front-to-rear binding (above).
The Nautobot rows were made one termination a side through the cable model
in the application shell, with its validation, since the script that reads
the file needs an API token and none was used: so the script itself is NOT
tried on these rows. Read back, each cable sat on its ports, and Nautobot
traced the first switch through the panel to the second, and through both
cassettes and the trunk, on the first fibre. Both cassettes were Type A; an A
to AF pair was not tried, and by the type files it does not trace (above).

## D. What the model makes checkable

A mapping table cannot be verified. A fibre graph can, and verification is the
reason to prefer it:

| rule | what it catches |
|---|---|
| endpoints are real | `mtp-1.13` on an MPO-12, instead of a silently ignored row |
| no position claimed twice | two strands landing on one bore, unless a declared split or a declared `combine`; two plain paths into one destination are still an error |
| a combine is well formed | a combine with a ratio list for a destination, a source named twice, shares that do not sum to 100, or bands and ratios mixed |
| every position reached or declared `unused` | the OCU dead bore, in both directions |
| fibre counts balance | what arrives at the rear equals what leaves at the front, allowing declared taps and terminations |
| declared polarity agrees with the paths | a transposition inside a 24-fibre cassette |
| split ratios sum to 100 | a 70/40 tap |
| rear connectors sit on the rear face | the two halves of a two-faced part drifting |

Plus library sweeps in pytest: every module with `optical:` exports ports whose
count matches its graph; every fibre-map row's endpoints exist in the exported
ports; no exported front port is left without a rear port.

## E. Order of work

1. **Schema and vocabulary** - `optical:`, `faces:`, connector fibre capacity.
2. **Connector components.** These come BEFORE any module and carry the capacity
   fact from A. What the catalogue needs:

   | connector | modules | status |
   |---|---:|---|
   | LC duplex | 42 | have `common/lc-duplex-adapter@6` |
   | MTP/MPO -8/-12/-16/-24 | 48 | **missing entirely** |
   | SC duplex | 5 | missing - `common/sc-apc` is a device-specific moulded bay off an HLX-TGV, not a panel-mount adapter |
   | MDC | 3 | missing |
   | ST simplex | 2 | missing |
   | FC simplex | 1 | missing |
   | LSH / E2000 simplex | 1 | missing |
   | keystone clips | 1 | missing |

3. **Lint rules and tests** - section D, landing WITH the schema so nothing is
   built unverified.
4. **Exporter** - front/rear ports, `splice`, per-fibre, and the fibre map.
5. **FS build** - FHD-1UFCE, then 62 cassettes and 15 panels.
6. **PPM retro-fit** - nine PPMs plus the A22, converting prose and attrs to real
   optical paths, with the version cascade that implies.

**This is much the largest thing the library has taken on**: ~10 new connector
components, ~78 FS components, a schema change, an exporter change, a new export
format, seven lint rules, and a retro-fit. The architecture is specified whole
because designing 1-4 without 5-6 in view is how a vocabulary ends up not
fitting. The IMPLEMENTATION PLAN should stage it so 1-4 land and prove themselves
on a handful of modules before the bulk build.

**The staging turned out to be eight plans, not six.** Steps 1-4 landed as plans
1-5 (PRs #236, #237, #239, #240, #242) and proved themselves on one cassette, as
this section asked. Step 5 is then plan 6 (the enclosure and one cassette
per two-faced shape) and the bulk build that follows it; step 6, the PPM retro-fit,
owed two things this document recorded as undesigned - a `combine` syntax, and a
way to name which optical endpoint is a trunk. **The trunk is designed and built**
(`optical.trunk`, #246, section C3), ahead of the bulk build as this section
argued: the eight path-bearing PPMs state one and export front and rear ports,
including both AD1 add/drop filters, retrofitted with their glass in the same
change, and the 19 single-faced TAP cassettes have the vocabulary they were
waiting on. `combine` followed it (section A, C4, L171), and the two AD1
filters now write their add direction as one.

## Open questions

Recorded rather than decided, because both need evidence we do not have:

**The LC pitch** was settled in plan 4: `standards.yaml`'s `fhd-lc-cassette`
entry records the measured 12.92 floor off FS SKU 57016, and
`common/lc-duplex-v-adapter@6` is the 9.28-wide stacked adapter FS actually
ships, so the 13.2-wide shared adapter is no longer composed at a 12.90 pitch.

**The FMT-N's 16.93".** The fixed enclosure's render carries a fourth dimension,
430.0 mm, that is not in its spec table and cannot be the depth (11.17" = 283.6
is). It must be a width - presumably the top cover, inset from the body - but
four cassettes need 435.86 mm side by side, which is wider. It does not threaten
the 1UFCE, whose 448.0 comes from a dimensioned orthographic drawing in its own
datasheet, but it is unexplained.

**Which end is the trunk was the other open question, and it is settled**
(section C3, #246).

**Combines were the last undesigned piece, and they are settled** (section A,
C4, #246). The form is a distinct `combine` keyword on the path, beside the
ratio list a split uses. A ratio list on the destination side was the other
candidate. It was passed over because a destination that is a list already
means a split, and a reader could not tell the two apart by shape.
`ppm-ad1-1510` and `-1625` used to write their add direction as banded legs
off the line port, which was the same glass read from the wrong end. They now
state it as a combine onto Line Tx, and their exports did not move.

**The single-faced TAP cassettes are not built.** They have the vocabulary: a
trunk for the live input, a split for the tap, and nothing further to design.
What they lack is parts. None of the 19 is in the library yet.

## Sources

Held locally, not in this repository: a sources ledger, a coverage note, a
product catalogue, five converted PDFs, 139 product images, and a Visio stencil
that turned out to be perspective marketing art with no connection points.
Read `COVERAGE.md` before modelling: the module envelope came from product
imagery, not from FS's family documentation, which dimensions no cassette
anywhere in 73 pages.

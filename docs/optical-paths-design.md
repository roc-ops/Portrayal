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

### The mapping is a third export

**The device-type YAML no longer carries the front-to-rear binding at all.** The
current `front-port` schema is `{name, type, positions}` with
`additionalProperties: false` and no `rear_port` key, consistent with #20564
having removed the FK. The mapping is now per-INSTANCE M2M.

**Nautobot is the exception, and it was found by importing.** Its
FrontPortTemplate still has a non-null rear port and rear-port position, and its
library's front-port schema is `{name, type, rear_port, rear_port_position}`
with no `positions`. A NetBox-shaped front port fails the Nautobot import, so
the Nautobot document is written with the binding, read from the same rows as
the fibre map. One front port reaches one rear position there, which holds
every breakout, conversion, mesh and splice cassette as it stands. It does not
hold an MPO front connector against an MPO rear one; that pair is written as a
single position, and the fibres stay in the map. A tap - several front ports on
one rear position - has no Nautobot spelling at all, and the export stops on one
rather than writing a file that cannot load.

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

## D. What the model makes checkable

A mapping table cannot be verified. A fibre graph can, and verification is the
reason to prefer it:

| rule | what it catches |
|---|---|
| endpoints are real | `mtp-1.13` on an MPO-12, instead of a silently ignored row |
| no position claimed twice | two strands landing on one bore, unless a declared split. A COMBINE HAS NO SYNTAX YET - two sources into one destination is an error today, full stop; see Open questions |
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
owes the two things this document still records as undesigned - a `combine` syntax,
and a way to name which optical endpoint is a trunk. **The trunk is now the larger
of the two and is not only the PPMs' problem:** every one of the 19 TAP cassettes
carries its live and monitor ports on a single face, so 29 parts in all are waiting
on that vocabulary, and it should be designed before the bulk build rather than
after it.

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

**Combines are undesigned.** The vocabulary can express a split - one path,
one `from`, a ratio list of destinations - and L79 can verify its ratios. It
cannot express the opposite: two sources landing on one destination, which is
what `ppm-ad1-1510`'s add/drop direction and the add/drop filters of plan 6
will need. Today's parts dodge this by writing add/drop as a split off the
line port instead, and L79 treats any real collision on a destination as a
flat error with no declared-combine escape hatch the way a declared split has
one. What the syntax should look like - a ratio list on the destination side,
a distinct `combine` keyword, something else - needs plan 6's own evidence
before it is worth deciding; recorded here so it is not mistaken for settled
by section D's table, which used to claim it.

## Sources

Staged in the maintainer's gitignored `working/intake/fs/fhd/` - `SOURCES.md`, `COVERAGE.md`,
`CATALOGUE.tsv`, five converted PDFs, 139 product images, and a Visio stencil
that turned out to be perspective marketing art with no connection points.
Read `COVERAGE.md` before modelling: the module envelope came from product
imagery, not from FS's family documentation, which dimensions no cassette
anywhere in 73 pages.

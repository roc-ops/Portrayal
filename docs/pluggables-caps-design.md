# Pluggables B3: dust caps and the connector slot

Status: design agreed 2026-09-22. Extends
[pluggables-connectors-design.md](pluggables-connectors-design.md) (B), and uses
the slotting of [pluggables-slotting-design.md](pluggables-slotting-design.md) (C)
and the 3D rules of [pluggables-3d-design.md](pluggables-3d-design.md) (D). Part of
[pluggables-design.md](pluggables-design.md).

## Goal

Every fibre port in the library - LC, SC, MPO - ships the way the product ships,
with its dust cap in it, and one swap takes the cap out and puts a connector in.
The cap and the connector are the same kind of thing in the same place: an
occupant of the port's one connector slot. Showing cables means changing the
occupant, never editing the adapter.

## What is wrong today

A dust cap is drawn as part of the adapter it plugs: a `class: cap` element in the
adapter's skin, raised in 3D by a `relief` feature. Nothing can remove it, put a
plug in its place, or leave the port empty, and it covers the bores that A built
for plugs to seat in. Three adapters carry one:

| adapter | cap as drawn | how it stands |
|---|---|---|
| `common/lc-duplex-adapter@3` (Smartoptics DCP) | two simplex caps, `cap-tx`, `cap-rx`, 4.7 x 4.7, white, inset 0.9 | `out: 9.525` on a bezel at `lift: 3.175`, photo-measured |
| `common/lc-duplex-v-adapter@2` (FS FHD LC cassettes) | ONE duplex cap over both stacked bores, 5.85 x 12.25, white, two insets 0.6 deep | `out: 5.5` on a bezel at `lift: 1.2`, estimated off FS's oblique photograph |
| `common/sc-duplex-adapter@2` (FS FHD SC cassette) | two caps, 8.8 x 11.45, black, a raised grip 3.9 x 7.0 | `out: 3.3` on a frame at `lift: 1.0`, grip `out: 3.8`, estimated |

The MPO adapters draw no cap at all, although FS photographs the MTP cassettes'
grey caps. The figures above and their photo readings live in each adapter's
`provenance` and `relief.features[].source`. They move with the caps; they are not
re-derived.

## Decisions

Taken 2026-09-22.

| # | decision |
|---|---|
| 1 | A DUST CAP IS A CONNECTOR. It mates the interface a plug mates, seats at the plug's mate point, and occupies the plug's slot. Replacing a cap with a plug is one swap of one occupant, not a remove and an insert |
| 2 | ONE SLOT PER CONNECTOR INTERFACE. Every part that presents a connector interface is a slot, the way every part presenting a pluggables family is a cage. Slots and cages are one mechanism with two registries |
| 3 | A DUPLEX ADAPTER IS ITSELF A HOST. It presents `lc-duplex` at the midpoint of its two bores. A duplex cap or a duplex plug mates the adapter; a simplex cap or plug mates a bore. No occupant ever spans two hosts |
| 4 | THE SHIPPED CAP IS DECLARED ON THE ADAPTER, as `default:`, the vocabulary a bay's shipped blank already uses. A composer may override it, a configuration overrides that, the explorer overrides last |
| 5 | Decision 2 of the umbrella is AMENDED, not bypassed: a default occupant is the shipped state of the product, like a bay's blank. Portrayal still ships no configured optic, plug or cable |
| 6 | EVERY FIBRE TYPE HAS A CAP AND A CONNECTOR FROM DAY ONE: LC simplex, LC duplex, SC, MPO. The SC plug and the MPO plugs move here from B's second batch |
| 7 | CAGE DUST PLUGS AND RJ45 COVERS use the same mechanism but are NOT defaulted. A switch still draws its cages empty unless a device states that its product ships plugged |
| 8 | THE KIT SEATS AT A LIFT. The refusal of a lifted seat is removed and replaced by the build's own rule, held to it by a parity test. Mirror and group-states stay refused |
| 9 | Removing the drawn caps from the three adapters is being done separately. This work checks before its adapter step; if the caps are still drawn then, it removes them itself |
| 10 | A shutter is not a cap. A spring door inside a shuttered adapter stays in the adapter's art; it may later be a state (open when occupied), never an occupant |

## Parts

| part | mates | seats in | source |
|---|---|---|---|
| `common/lc-dust-cap` | `lc` | `std/lc-bore@3` | the Smartoptics cap figures, moved from `lc-duplex-adapter@3` |
| `common/lc-duplex-dust-cap` | `lc-duplex` | a duplex LC adapter | the FS FHD cap figures, moved from `lc-duplex-v-adapter@2` |
| `common/sc-dust-cap` | `sc` | `std/sc-bore@1` | the FS FHD SC cap and grip, moved from `sc-duplex-adapter@2` |
| `common/mpo-dust-cap` | `mpo` | `std/mpo@2` | new: FS's MTP cassette photographs |
| `generic/lc-duplex-plug` | `lc-duplex` | a duplex LC adapter | two `generic/lc-plug` bodies at the `lc-duplex-receptacle` pitch, on a clip, each turned latch-up (see "Seated plugs") |
| `generic/sc-plug` | `sc` | `std/sc-bore@1` | new intake (below) |
| `generic/mpo12-plug` | `mpo` | `std/mpo@2` | new intake (below) |
| `generic/mpo24-plug` | `mpo` | `std/mpo@2` | as mpo12; its own part for the two-row ferrule (umbrella decision 10) |

Caps are `common/` by the rule B gives the boots: no standard governs a cap's
shape, only the interface it plugs. Each is `behaviour: occupies`, `class: cap`,
with a body at its own depth and the `out` figures above carried as its own relief,
not as the adapter's.

`generic/lc-duplex-plug` is `generic/` because what it fixes is standard: the
6.25 pitch its clip holds is `lc-duplex-receptacle`'s, set by IEC 61754-20 / TIA-604-10
FOCIS 10 (`pitch-confidence: verified`). The clip's own outline is not, and the part
says which of its figures are the standard's and which a vendor's.
It composes two `generic/lc-plug` rather than redrawing one, so each half keeps
the plug's own rear point and a boot can seat behind either.

An MPO-16 plug is not in this work. It has a different key and so a different
interface (umbrella decision 10), and no part in the library presents it; a plug
with nowhere to seat is a part nothing checks.

### Intake the parts need

Nothing is estimated into a measurement. Each part states which of its figures are
drawn, measured or estimated, the way `generic/lc-plug` carries no `d` because
the class fixes none.

- **`generic/sc-plug`.** The opening it enters is drawn: `sc-simplex-receptacle`,
  7.5 x 9.0 with a 0.89 x 2.1 keyway, off SENKO DS-SC-000010 and DS-SC-000011.
  SENKO DS-SC-000006 gives the plug's side silhouette and a 40 mm overall length,
  and no front view. The intake looks for a dimensioned front view first (a TE,
  Huber+Suhner or Corning SC connector drawing); failing that, the front profile is
  the drawn opening less a stated clearance, marked `estimated`, and the key is the
  drawn keyway.
- **`generic/mpo12-plug`, `generic/mpo24-plug`.** No MPO plug source is held. The
  intake fetches a vendor MPO/MTP connector drawing (US Conec MTP, SENKO MPO, or
  FS) with a front view. `std/mpo@1`'s own aperture is itself estimated
  (`mpo-adapter`: `confidence: estimated`), so the plug fits the aperture and says
  which of the two figures governs.
- **The caps.** The three existing caps move with their figures. The MPO cap is
  read off FS's cassette photographs, checked orthographic first.

### The MPO opening

The MPO plug intake found the connector printed at 12.5 x 7.6 (US Conec C20044
rev B, C20851 rev D), and `std/mpo@1`'s opening - 7.8 x 5.6, estimated off an FS
render - could not take it. The opening was the weaker reading, so it moved:
`std/mpo@2` is 12.9 x 8.0, still `estimated`, because no adapter drawing held
puts a callout on the mouth. It is the printed plug plus the clearance an LC
adapter's opening runs over its plug (SENKO DS-LC-000010 against DS-LC-000004,
0.16-0.40 per tier, the upper end taken), and it admits the largest plug IEC
61754-7-1 allows (12.59 x 7.7). `common/mpo-adapter@2` composes it, centred where
`@1`'s opening was. A test holds both plugs inside the opening on a build, in the
device frame.

## The connector slot

### What is a slot

`cage_entry` (render.py) answers "is this placement a cage, and what does it
accept" by looking the presented interface up in `spec/schemas/pluggables.yaml`.
Its core is generalised to take a registry, and it is called with two:

- `pluggables.yaml` families, exactly as today, for cages;
- a new `connectors:` registry of the connector interfaces `lc`, `lc-duplex`, `sc`
  and `mpo` (`rj45` joins when its covers do).

A slot's accept list is every part whose `mates:` is the slot's interface - caps
and plugs alike. Boots never appear: they mate `lc-plug`/`rj45-plug`, which name no
port. There is no ladder; a connector interface either intermates or it does not.
`std/mpo@1` presented no interface and no `mate` point; it gained both
(`interface: mpo`, a `mate` at the aperture centre) as a minor. Its opening was
then corrected as a major, `std/mpo@2` (see "The MPO opening" below).

Slots are published where cages are: a device view's `cages[]` gains `kind: cage`
or `kind: connector` on each entry, and `components.json` carries each component's
own slots in its frame, computed by the same core. One list, one reader, one
seating path.

### The duplex host

`lc-duplex` is a new interface, and a duplex LC adapter presents it at the midpoint
of its two bores, with the adapter's `mate` there. Its `lc-duplex-receptacle`
pitch is 6.25. Lint holds the adapter's two composed bores to that pitch, by the
adapter's own `rotate`; a duplex adapter whose bores are not on it does not present
`lc-duplex`, and so offers no duplex connector.

An adapter slot and its two bore slots are mutually exclusive. When the adapter's
slot is occupied, its bore slots are not offered and a configuration naming one is
an error; when either bore slot is occupied, the adapter slot is not offered.
The build enforces it and the kit follows it; the explorer shows the free level.

A spanning slot also carries the AXIS its pair runs on, because a duplex connector
is one moulding with two ferrules and cannot turn itself. The two LC adapters do
not agree: one puts its bores side by side, the other stacks them - "the same
duplex pair stood on end" - so a single part drawn on one axis would be right on
one host and wrong on the other. The canonical drawing axis is ACROSS, the pair
running in x from the part's own `mate`, and every spanning part is drawn on it;
a slot publishes the turn that carries that axis onto its own bores, derived from
the bores' composed mate points and added to the placement's own `rotate`, and the
existing seat arithmetic applies it to the occupant. Lint holds both ends: a host's
bores to the pitch, and a part mating a spanning interface to the canonical axis.

The registry says which interface takes the place of which, rather than a rule
naming `lc-duplex` in code: the entry carries `spans: {interface: lc, count: 2}`,
and the pitch the spanned parts sit at is the interface's own `standard`. A
published slot entry names the parts it spans, so a reader offers one level or
the other; `[]` where a slot spans nothing. "Occupied" is read after defaults
and the configuration resolve, which is why the table below says a Smartoptics
port's two bores must be emptied before a duplex connector seats in it.

So the two LC adapters come out differently, as the products do:

| adapter | ships with | the swap menu offers |
|---|---|---|
| `lc-duplex-v-adapter` (FS FHD) | the adapter slot filled by `common/lc-duplex-dust-cap` | on the adapter: duplex cap, `generic/lc-duplex-plug`, empty; empty opens the two bores to simplex parts |
| `lc-duplex-adapter` (Smartoptics) | each bore filled by `common/lc-dust-cap` | on each bore: cap, `generic/lc-plug`, empty; both bores empty opens the adapter slot to a duplex connector |

### Seated plugs

Added 2026-09-23, after the review page showed the plug and its bore disagreeing.

**A keyed occupant is drawn in its host bore's unrotated convention.** A seat
turns an occupant by exactly its host's turn (`render.solve_seat`), so the two
parts only agree on every host if they agree unturned. `std/lc-bore@3` is drawn
tongue down and `generic/lc-plug@1` was drawn latch up, so every simplex LC plug
seated with its latch on the side opposite the keyway. `generic/lc-plug@2` is
drawn latch down. The SC pair already agreed (both key-left), and a test holds
them to it.

**The library draws a plug seated, so its latch is compressed.** An LC latch is a
spring the adapter presses down on insertion. SENKO DS-LC-000004's 10.43 front
silhouette is the plug in the hand; seated, the latch lies within the keyway. The
plug is drawn with its tab at the bulkhead keyway's end, 5.71 from the ferrule
axis. The tier widths stay SENKO's dimensioned ones. The tier heights are the
free ones scaled in proportion, which is a modelling choice and the contract says
so. The seated state is the plug's only drawing, not a state its host switches
on. A loose plug in a catalogue therefore also shows the latch compressed; a
free-state variant would be additive.

**Two LC bores: the transceiver receptacle and the bulkhead aperture.**
`std/lc-bore@3` is the transceiver receptacle, and its 1.60 keyway is cut short to
fit an 8.5 module face. `std/lc-bulkhead-bore@1` has the same square, widths and
mate, with the 3.36 keyway measured off the vector line art of SENKO's LC Premium
Adapter (DS-LC-000010). A panel adapter composes the bulkhead aperture unless its
own outline cannot hold it. The FS FHD adapter (`lc-duplex-v-adapter@5`) does, and
so does the Smartoptics one since its `@5` moved its ferrule axis (see "The
Smartoptics axis" below). A seated plug in a transceiver receptacle runs past the
drawn keyway, which is that receptacle's understatement showing.

**Duplex parts stay on the canonical axis, latches up.** `generic/lc-duplex-plug@2`
composes its two halves at `rotate: 180`, so the pair runs across with both latches
up. Each host's derived axis then carries the latches onto its bores' keyway
side: 0 on the Smartoptics adapter (bores turned tongue-up), 270 on the FS one
(bores turned tongue-left).

### The Smartoptics axis

Added 2026-09-23, when the review page showed a seated plug running past the
Smartoptics adapter's outline.

**The Smartoptics adapter composes the bulkhead aperture, and its ferrules moved
to hold it.** `common/lc-duplex-adapter@4` drew its axis at y 5.5, the middle of
its 11.0 outline, on the transceiver receptacle; the bulkhead keyway reaches 5.71
from the axis and would have run 0.21 past the edge. `@5` composes
`std/lc-bulkhead-bore@1` with the axis at 5.82 from the latch-side edge.

**The axis figure is the stencil's direct ferrule reading, and it is an
estimate.** The DCP-R stencil master R-34D-CS, raster art at 8.86 px/mm, draws the
ferrule 5.79 from the latch-side edge of each adapter. Re-read across its 34
cross-connect adapters that figure spans 5.75 to 6.03, depending on the adapter and
on which pixel counts as the housing's edge. A second figure, 6.33, can be inferred
by standing SENKO's keyway on the end of the art's own keyway. It was rejected: the
art's keyway is the draftsman's, reaching 5.11 from its ferrule rather than
SENKO's 5.71, so it says nothing about where the ferrule sits.

**The last 0.03 is a drawing constraint, not a reading.** The bezel outline now
runs on the body's own box, as the shuttered adapter's does. `@4` drew it inset
0.1, a seam with no source. Its 0.2 stroke covers the top 0.10 of the part, and at
5.79 the keyway would cut into that by 0.02. At 5.82 the keyway ends 0.01 clear of
the stroke. Moving the outline is a drawing change, and so is the extra 0.03; the
part says both.

**Keep what the source measured, and move what it did not.** Moving the axis
inside the part moves one of two things on a face: the fibre or the body. Which
one moves depends on what each composer's source measured. The first cut kept
every placement and moved every fibre. The second moved every body. Both were
reversed the same day in favour of this rule.

- Where the source is the fibre, the fibre stays and the body moves. On the
  DCP-R units that source is the stencil ShapeSheet connection points; on the
  DCP-M32 it is the photograph's channel positions. The A22 carrier is treated
  the same way. Each of those placements moved 0.32 toward its own latch side:
  up on an unturned row, down on a row at `rotate: 180`. Each device's panel
  cutout moved with its adapter. That is 119 placements, and every optical point
  and mate on them is where `@4` had it. A test holds them to those figures on
  real builds.
- Where the source is the body, the body stays and the fibre moves. The eight
  PPM modules measured the adapter block on five renders, so their 14 placements
  keep `@4`'s position and their ferrules sit 0.32 further from the latch inside
  it. A test holds those placements to `@4`'s.
- The Tx/Rx caption frames on the DCP-R units obey the same rule. They were
  generated from each adapter's placement, not measured, and they stood about 2
  closer to the ferrule than the stencil draws them. Once the bodies moved, they
  met. So the frames, their dividers, their Tx/Rx text and the port names above
  them moved onto the stencil's own positions.

A source that fixes the axis would move the bodies again; the two stencil
readings lie 0.54 apart.

### The shipped default

A slot's default is declared on the part that presents it, in the component that
composes it:

```yaml
# library/components/common/lc-duplex-adapter/v5/contract.yaml
parts:
  - {ref: std/lc-bulkhead-bore@1, id: tx, at: [1.125, 0.11], lift: 3.175, rotate: 180,
     default: common/lc-dust-cap@1}
```

and a duplex adapter's own slot by a top-level `default:` beside its `interface:`.
Precedence, lowest first: the adapter's `default:`; a composer's `parts:` entry
(`default: none` for, say, a plate that ships one port open); a configuration's `occupants:`
(`none` empties it); the explorer's swap. Lint rejects a `default:` that the slot's
accept list does not contain.

### The shuttered adapter

Added 2026-09-23, when the FS 36-fibre cassettes arrived with
`common/lc-duplex-shuttered-adapter@1`.

**A shuttered adapter is a slot whose shipped state is empty.** Its spring
shutters are the dust protection, and FS ships those plates with no caps, so
nothing on it declares a `default:` - not the adapter's own duplex slot, not
either bore - and no composer needs `default: none` to empty it. It is still a slot at both levels: `@2` composes two
`std/lc-bulkhead-bore@1` (turned 180, keyways up, as the Smartoptics adapter
turns its bores) and presents `lc-duplex` with a `mate` at their midpoint, so a
plug can be swapped in, simplex in a bore or duplex across the pair, and the
exclusion and the spanning-geometry lint apply to it as to any duplex host.
`@1` had no bores and no interface, so there was nothing to seat.

**The shutter stays the adapter's art (decision 10).** It is what an empty port
looks like. The bores are composed `behind: true`, so the shutter drawn over each
bore paints in front of it; a plug seated in a bore is an occupant, drawn after
its host, so it covers the shutter as the real plug pushes the doors aside. In 3D
the shutter is a solid door standing in front of the bore's ferrule and behind
the raised face - how far behind is a modelling choice, since FS's renders do not
show it. Nothing switches the shutter on occupancy; an open-when-occupied state
remains the later option decision 10 leaves.

**The bulkhead keyway fits, by 0.09.** The ferrule axis sits 5.8 into the 11.6
body, where `@1` placed the bore square, and the keyway reaches 5.71 from it. The
bezel outline moved out to the body's box to make room: `@1` drew it inset 0.1 as
a seam, and the keyway would have cut through that.

## Deep addressing

A cassette's bore is three levels down: device bay, cassette, adapter, bore. #484
addressed a cage one level into a seated module (`front-6/xg0`). The same rule
extends to any depth: a slot's key is the path of part ids from the device's
placement to the slot, with the `module` of each seated bay dropped, as nested
`bays:` keys already are. So `bay-1/lc01/tx` is the TX bore of adapter `lc01` in
the cassette in `bay-1`, and `bay-1/lc01` is that adapter's duplex slot.

One resolver maps a key to its slot, and the build, L12 and the kit all call it: it
generalises `manifest.nested_key_host`, which today stops at one level, and
`chained_occupant_ref` stays the rule for a key that names an occupant rather than
a part. An occupant is drawn inside the innermost group that holds its slot, at
`<slot-path>-occupant` with each `module` segment restored, so it inherits every
transform above it and nothing is solved twice.

## The kit

- **Lifted seating (decision 8).** `seatOccupant` stops refusing a non-zero lift.
  It applies the build's rule: the occupant's own `data-z-lift` is the host's
  presented lift plus the composed lifts above it, and every `data-z-out` inside
  the occupant is left as the build writes it (`out` is absolute, `lift` is
  summed). The 7 DCP card cages refused at lift 44 are seated by the same change.
- **Slots in the inspector.** `nestedCages` becomes `nestedSlots`, reading each
  seated component's slots from `components.json` at any depth. Clicking a slot
  offers its accept list plus `empty`, the default marked. The choice is kept in
  `swap=`, survives a reload, and reaches 3D through the override map.
- **Exclusion and pruning.** The kit offers only the free level of a duplex adapter
  (above). Replacing or emptying a carrier drops every occupant keyed under it, in
  2D state, `swap=` and the 3D map - a cap cannot outlive its cassette.
- One home: all of it lives in `kit/swap.js`.

## 3D

A cap is a small body standing proud of its adapter, at the `out` its figures give.
Two lessons from building the caps as the adapter's relief carry over:

- **Paint order.** A bore painted over a cap in 2D until the bores took
  `behind: true`. An occupant is drawn after its host, so a cap seated as an
  occupant paints over the bore without it; the bores keep `behind: true` only
  while an adapter still draws its own cap.
- **Nested lift.** A cap's inset or grip is a child of the cap and its lift is
  relative to the cap, not summed a second time. Nothing in the suite holds a
  composed child's lift to that today, for a solid or for a pocket; this work adds
  the test for both, and for a pocket inside a cap standing behind the cap's face.

## Lint

- L12 accepts slot keys at any depth through the one resolver, and checks a cap or
  plug's `mates:` against the slot's interface, as it checks an optic in a cage.
- A new rule: a `default:` must be in the slot's accept list, and an occupant may
  not fill an adapter slot and one of its bore slots at once.
- A new rule: an adapter presenting `lc-duplex` has its two bores on the
  `lc-duplex-receptacle` pitch.
- The same rule's latch-side arm: the axis a duplex host derives from the ORDER of
  its bores must turn a duplex connector's latches (drawn up) onto the side the
  bores' keyways face (drawn down, turned by the bores' shared `rotate`), and the
  bores must share one `rotate`. It catches, from the geometry, a pair composed in
  the wrong order. The FS adapter's upper-bore-first order before #496 was that
  mistake, and at the time it was found by reading FS's port numbers.
- A census: every part presenting a connector interface is a slot, and the census
  asserts the count it measured is greater than zero.

## Order of work

1. The connector registry and the generalised slot core, with the `kind` on each
   entry; `std/mpo@1` gains its interface and `mate`. Byte-identical `cages[]` for
   every cage before and after.
2. Deep addressing: the resolver, the build seating a configured occupant three
   and four levels down, L12 on the same keys.
3. `default:` on a part and on an adapter, and its precedence, in the build and
   lint. Umbrella decision 2 amended in its own document.
4. The duplex host: `lc-duplex`, the pitch rule, mutual exclusion.
5. The caps: `common/lc-dust-cap`, `common/lc-duplex-dust-cap`,
   `common/sc-dust-cap`, `common/mpo-dust-cap`.
6. Intake, then the connectors: `generic/lc-duplex-plug`, `generic/sc-plug`,
   `generic/mpo12-plug`, `generic/mpo24-plug`.
7. The adapters (decision 9): if they still draw caps, remove them as majors
   (`lc-duplex-adapter@4`, `lc-duplex-v-adapter@3`, `sc-duplex-adapter@3`),
   declare the default caps, and repoint the 18 components that compose them. No
   library part presents an `mpo` slot yet - the FHD cassette rears use flanged
   adapters that draw the plug's end face and compose no `std/mpo` - so the MPO
   default waits for a host. Until this step, a bore under a
   drawn cap declares no default, so no port is ever capped twice.
8. The kit: lifted seating with its parity test, `nestedSlots`, the swap, exclusion
   and pruning.
9. A review page - the product photographs beside the rendered caps and plugs, 2D
   and 3D, close-ups - signed off before the rebuild and the gates.

## Tests

- The slot census, and byte-identical `cages[]` against the tree before step 1.
- The resolver at depth three and four, a dangling key and a cycle, each shown
  failing first.
- Default precedence: adapter, composer override, `none`, configuration.
- Mutual exclusion both ways, in the build and in lint.
- Kit against build: a cap and a plug seated by the kit on a lifted Smartoptics
  bore and on an FHD adapter in a cassette in a bay match the build's transform,
  parent and `data-*` to 1e-6, composed through every ancestor, on a real build.
- 3D: each cap stands at its `out`; a pocket inside a cap is behind the cap's face.

## Open questions

- Whether a patch cord's two ends are ever one part. `generic/lc-duplex-plug` is the
  connector end; the cord between two ports is the cabling side's.
- Whether an empty cage's dust plug is shown by default on the devices whose
  datasheet photographs show it. Decision 7 says no until a device states it.

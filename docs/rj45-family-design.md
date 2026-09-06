# The RJ45 family: two bare jacks, two lamped ones

Design note for #125, absorbing the decision #80 is waiting on and the RJ45 half
of #61. Written 2026-09-05 against `main` at 468af23f. Nothing here is built yet.

## What is wrong

The library has nine RJ45 components across three namespaces, and they answer the
same three questions differently.

| component | placements | what it draws | lamps |
|---|---|---|---|
| `std/rj45-ganged@1` | 540 (225 on devices, 315 inside cards) | a 12.7 x 11 dark hole with a two-box cavity floating in it | none |
| `std/rj45@1` | 87 | the 16 x 14 IEC panel cutout, same floating cavity | none |
| `common/rj45-hd@1` | 83 | silver bezel plate over the ganged hole | two, in the outer corners |
| `common/rj45-shielded@2` | 19 | a 15.8 x 12.5 shell with a recessed cavity | two, in the shell corners |
| `common/rj45-port@4` | 17 | silver bezel plate over `std/rj45` | two, in bezel tabs |
| `common/rj45-bezel@2` | 14 | the same plate, no lamps | none |
| `dell/rj45-port-14g@1` | 4 | nothing; composes `rj45-port` and attaches Dell's lamp meanings | inherited |
| `common/rj45-hd-plain@1` | 3 | the ganged bezel, no lamps | none |
| `common/rj45-jack@2`, `rj45-shielded@1` | 2 | older housings | none |

Three things are wrong with this, and #125 names all three.

**The shape.** Every cavity is two boxes, an 11.89 x 6.85 body and a 4.0 x 2.6
keyway. The plug that goes in it has three tiers: the body, a narrower shoulder
where the latch lever meets the plug, and the latch tab. The body figure comes from
a TE CAD drawing and is trusted; the keyway is recorded as "conventional, not
measured"; the middle tier does not exist.

**The sides.** The standard parts draw an aperture, a hole in the panel with the
cavity hanging inside it. A real jack has a housing with solid sides that grip the
plug. The housing only appears when a `common` bezel plate is layered over the
hole, which is the layering #125 calls extraordinary.

**The lamps.** Nearly every Ethernet jack has link and activity lamps in its
housing, and console, aux and timing jacks have none. The library expresses this
five different ways: lamps drawn in a bezel component (`rj45-port`, `rj45-hd`),
lamps drawn in a shell component (`rj45-shielded`), 556 separate `common/led-dot`
placements pointed at a bare jack with `for:` (60 devices, after the #80 sweep),
lamps deliberately left undrawn (the S6301 pair's stated position), and lamps
absent because nobody decided. #80 is waiting on which of these is right.

## Decisions

Three questions were put to Jason on 2026-09-05 and answered:

1. **`std/rj45` is the jack housing**, with its cavity recessed into solid walls,
   not the panel aperture. The registry's `rj45` entry became the housing itself,
   and a single jack's panel cutout is the housing's 15.8 x 13.2; the 16 x 14
   figure was the registry's unsourced aperture and is retired (#61 §3).
2. **The ganged form is a second bare cell, `std/rj45-ganged`.** 540 placements sit
   in 2xN blocks on a 13.97 mm pitch where a 15.8 mm housing cannot fit. One
   per-port cell with shared walls keeps every anchor where it is.
3. **The lamped jack's default vocabulary is `off / link / activity` with no
   colours asserted, split across the pair: led-a is the link lamp and led-b the
   activity lamp.** A device that documents green, amber, a blink, or a split by
   speed rather than by function overrides with `states:` on the placement, as
   `dell/rj45-port-14g` already does.

## The family

Four components replace nine.

| component | is | lamps | used for |
|---|---|---|---|
| `std/rj45@2` | a single modular jack housing, 15.8 x 13.2, three-tier cavity | none | console, aux, serial; ToD, BITS, 1PPS, sync; telemetry; any RJ45 with no link lamp |
| `std/rj45-ganged@2` | one cell of a shared-wall 2xN block, ~12.7 x 11, same cavity | none | the same roles inside a ganged block |
| `common/rj45-eth@1` | `std/rj45@2` plus two lamps in the housing corners | `led-a`, `led-b` | every single Ethernet jack: data, mgmt, OOB, service |
| `common/rj45-ganged-eth@1` | `std/rj45-ganged@2` plus two lamps in the outer corners | `led-a`, `led-b` | every Ethernet jack in a ganged block |

`dell/rj45-port-14g@1` stays. It draws nothing and exists to attach ISM table 11's
meanings once; it composes `common/rj45-eth@1` instead of `rj45-port@4`.

The rule for choosing is the placement's role, and it is mechanical. A jack whose
role, id or **media** says console, aux, serial, ToD, BITS, PPS, sync, PTP, 1588,
ICS or telemetry takes the bare part, and so does one on a card whose **name** says
T1, E1, DS1 or RJ48 - a channelized card numbers its RJ48c jacks `port-*` like any
other card, and they carry DS1, not Ethernet. Everything else that carries Ethernet
takes the lamped one. This is the same test `sweep_jack_lamps.py` already applies to
decide where a lamp belongs.

### Geometry and sources

Every dimension in the family carries a confidence, and the note says which are
settled and which this work has to acquire.

The acquisition happened on 2026-09-05. Four public manufacturer documents are
staged under `working/intake/standards/rj45/` (gitignored, with a README naming
each and its sha256): TE customer drawing **1734264 rev A2**, an RJ45 8P8C side
entry jack whose front view dimensions the plug opening in three tiers; TE
customer drawing **6368011 rev L**, a stacked 2x1 shielded RJ45 with integral
LEDs; the **Amphenol Canada modular jack catalogue** (RJHS, RJESE, RJSAE, RJE88
series, each with a dimensioned front view); and TE 1775675, a 6-position jack
kept for comparison only. The IEC text was never needed.

| figure | value | confidence | source |
|---|---|---|---|
| housing face, single jack | 15.8 wide (body 15.6 ±0.3) x 13.2 high | drawing | TE 1734264 front view; Amphenol RJHSE-508X and RJESE-808X read 15.75 x 13.21, agreeing to 0.05 |
| housing depth | 18.6 | drawing | TE 1734264 side view (low profile; taller families run to 21) |
| cavity body (tier 1) | 11.91 wide x 6.83 high | drawing | TE 1734264 front view; the library's 11.89 x 6.85 from the 2497310-1 CAD agrees to 0.02 |
| latch shoulder (tier 2) | 6.30 wide x 1.69 high | drawing | TE 1734264: the opening is 8.52 high through the shoulder, so 8.52 less 6.83 |
| latch slot (tier 3) | 4.06 wide | drawing | TE 1734264; the library's 4.0 was conventional and is right |
| latch slot height | 2.6 | conventional | not dimensioned on 1734264 or the Amphenol views; the slot runs to the housing's lower edge in every drawing, so the skin draws it to the face and the figure stays flagged |
| contact pitch | 1.02, eight contacts over 7.14 | drawing | TE 1734264 detail C |
| panel cutout, single jack | 15.8 x 13.2 | drawing | the housing is the standard the panel is cut for (TE 1734264); the 16 x 14 the registry carried was unsourced and is retired; L39 checks a cutout against its occupant's standard at 0.3 mm, which is why the two are one figure |
| ganged cell | 12.7 x 11.0, 13.97 pitch | measured | ES1010 photo, TE 2497310-1 CAD autocorrelation; unchanged |
| stacked pair with LEDs | 19.6 wide, two ports in a 27.19 face, LEDs in the four corners | drawing | TE 6368011 front view; a different family from the magjack block, recorded so a stacked-with-LED device has a source |
| lamp window | 2.0 wide, 1.2 in from each side, 0.27 from the keyway edge | derived | the S9600-72XC's own management jack; the Amphenol and TE LED windows sit in the same corners |

So the three-tier profile is: 11.91 x 6.83 body, a 6.30 wide shoulder 1.69 high
beneath it, and a 4.06 wide latch slot running from the shoulder to the housing's
lower edge. Two of the three figures the library already carried were right to
within 0.02 mm; the shoulder is the tier it never had.

### What the skins draw

The bare housing is a solid face the colour of jack plastic with the cavity
punched through it as one evenodd path, three tiers, pins drawn inside the body
tier. `relief.cavity` names that path and `relief.wall` gives the walls their
colour, so the 3D view extrudes a socket with sides rather than a flat patch. The
housing does not draw a panel hole; the panel's own `cutouts:` punches the
15.8 x 13.2 opening it sits in, derived from the placement as today.

The ganged cell is the same face clipped to the cell size, with the shared walls
implied by abutting cells at the block pitch. Rows mirror, not translate: the
upper row is the same part rotated 180, and which way the keyway points is a
per-device fact set at placement. That convention already exists and does not
change.

The lamped variants compose the bare part `behind: true` and add two lamp
rectangles in the two corners on the keyway side, so `rotate: 180` moves the
lamps with the keyway the way it does on the metal. led-a declares
`states: ['off', link]` and led-b `states: ['off', activity]`, with no colour. The
component says what the two lamps are; the device says what they mean.

### Lamps move into the component

The 556 `common/led-dot` and `led-rect` placements that currently sit inside a
bare RJ45's footprint on 60 devices are removed, and their jacks become the lamped
part. Where one of those placements carried `states:` or a `function` attr, that
vocabulary moves onto the jack placement as a per-element mapping,
`states: {led-a: [...], led-b: [...]}`, which `apply_states` already reaches into
composed parts for. Three UfiSpace devices write exactly this form today on
`rj45-port`.

**This is the expensive part, and it is a version cost rather than a drawing
cost.** Those 556 lamps have ids (`led-mgmt-link`), and removing an id is a major
bump under the lock's rules, because something outside this repository may hold
it. Sixty devices take a major. The alternative, keeping the separate lamp
placements and making the lamped component a housing with no lamps, would leave
the lamp decision exactly where #80 found it. The recommendation is to take the
majors: this is the case the version discipline exists for, and the lock will
name every id that vanished.

Silkscreen legends that point at a removed lamp id with `for:` are re-pointed at
the jack. L13 already exempts an indicator that declares its part with `for:`,
and L39 already exempts a lamp that "sits wholly inside the RJ45"; both clauses
become dead once the lamps are components, and are removed with a note.

### Rules

- **L39** loses its in-jack lamp exemption once no lamp is placed inside a jack.
- **A new census rule, warning only:** an RJ45 placement whose role is in the
  Ethernet set and whose part carries no lamps, or the reverse. It fires on the
  day it lands and shrinks to zero as the sweeps go through; it is what stops the
  five conventions growing back.
- **`standards.yaml`** `rj45` gains the housing face and the three cavity tiers,
  each with its confidence and source; `rj45-ganged` gains the same tiers.

## Migration

| today | becomes | placements | note |
|---|---|---|---|
| `std/rj45@1` | `std/rj45@2` or `common/rj45-eth@1` by role | 87 | 29 have no role attr and are read individually |
| `std/rj45-ganged@1` | `std/rj45-ganged@2` or `common/rj45-ganged-eth@1` by role | 540 | 132 `port` and 21 `mgmt` become lamped; 29 console and the timing set stay bare; 10 unroled are read |
| `common/rj45-hd@1` | `common/rj45-ganged-eth@1` | 83 | bezel plate art is dropped; anchors re-centred on the cell |
| `common/rj45-hd-plain@1` | `std/rj45-ganged@2` | 3 | |
| `common/rj45-port@4` | `common/rj45-eth@1` | 17 | anchors move from the 17 x 14.9 plate to the 15.8 x 13.2 housing, centre held (+0.6, +0.85) |
| `common/rj45-bezel@2` | `std/rj45@2` | 14 | |
| `common/rj45-shielded@2` | `common/rj45-eth@1` | 19 | Casa SMM cards and Smartoptics; the shell IS the housing |
| `common/rj45-shielded@1`, `rj45-jack@2` | `std/rj45@2` | 2 | |
| `dell/rj45-port-14g@1` | unchanged, composes `common/rj45-eth@1` | 4 | |
| 556 in-jack `led-dot` / `led-rect` placements | removed; states move onto the jack | 556 on 60 devices | major bump per device |

Every anchor move holds the jack's centre, the way the lc-bore collapse did, so
the plug interface does not move on any faceplate. The old components are
deleted once nothing references them, following the `rear-bay-blank-14g` and
`lc-bore` precedent that a superseded directory nothing references still answers
a version probe wrongly.

## Sequence

Four PRs, each green on its own.

1. **Source and the two bare parts.** The drawings are staged; transcribe the
   tiers into `standards.yaml` with their sources; build `std/rj45@2` and
   `std/rj45-ganged@2` with skins and relief. Old parts untouched, nothing placed
   yet. Tests: the cavity path has three tiers and matches the registry to the
   millimetre; L9 conformance passes.
2. **The two lamped parts and the Dell carrier.** `common/rj45-eth@1`,
   `common/rj45-ganged-eth@1`; `dell/rj45-port-14g` moves onto the new part; the
   census rule lands, firing on everything. Tests: lamp windows sit where the
   S9600-72XC derivation puts them; the default vocabulary is exactly the three
   names; a per-element `states:` override reaches both lamps.
3. **The sweeps, by vendor.** UfiSpace (the bulk), then Edgecore and Celestica,
   then Juniper (mostly inside cards), then Cisco, Casa, Smartoptics, Dell. Each
   PR moves placements, removes the in-jack lamps, carries states across, bumps
   and relocks. The census count in the PR body says how far there is to go.
4. **Delete the seven retired components** and the two dead lint clauses.

## Out of scope

The optical apertures in #61 (OSFP, SFP-DD, XENPAK, CPAK); `std/qsfp-dd`'s
unverified size; PoE lamps beyond what a device's guide tables; a keystone or
field-terminated jack, which is a different housing this library has no device
for.

## Done

Landed 2026-09-05 across PRs 131, 132, 133, 134, 135, 136, 137, 138, 139 and
this PR. Four components replace nine; every RJ45 in the library is one of
them; L76 counts zero over **devices and components alike** - the census reads a
component contract's `parts:` as well as a device view's placements, which is
where 368 of the library's 762 RJ45 placements actually live. What stayed
flagged: the latch slot height (2.6, conventional) and the housing top wall
(2.0, read at scale).

**Four departures from the note as approved.**

1. The panel cutout follows the housing (15.8 x 13.2) rather than staying at
   16 x 14, decided in the plan's first task and verified in every review after.
2. **The L13 and L39 clauses stay.** The note said both become dead once the
   lamps are components and are removed with a note; they are not dead.
   `edgecore/as5912-54x` draws mgmt-eth's two lamps BESIDE the jack under `for:`
   and needs L13's exemption; the MX204's BITS jack keeps two lamps inside it
   and needs L39's. What was removed is the RJ45 justification from the two
   comments, not the code.
3. **Two of the 556 in-jack lamps were not lifted.** 554 were. The MX204's
   `led-bits-act` and `led-bits-link` sit inside its BITS jack, which is a timing
   role - bare part, by decision 3 - that nonetheless has lamps, and the family
   has no bare-with-lamps member. They stay as separate placements naming the
   jack with `for:`, the shape as5912-54x already uses, and the device carries a
   `bits-lamps` provenance entry saying so. One jack does not earn a fifth
   member; if a second arrives, the family gains one.
4. **The two lamps split link and activity.** The lamped parts shipped at 1.0.0
   with `off / link / activity` on BOTH lamps, as the retired `common/rj45-port@4`
   had. Review of the merged result found that unreadable - a jack whose two lamps
   each claim link and activity - so 1.1.0 splits the pair: led-a link, led-b
   activity. The 27 UfiSpace jacks whose guides split the lamps by speed keep their
   own mapping; three that had copied the both-on-each default were split.

**The version rule the sweep answered two ways:** a composed-part swap that
removes no id is a minor bump.

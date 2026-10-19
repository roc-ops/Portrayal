# DC power: an inventory, and a proposed model for DC ends and feeds

Status: **proposed, 2026-10-15, for approval. Nothing here is built.** The inventory
([dc-power-inventory.md](dc-power-inventory.md), written by `spec/tools/dev/dc_inventory.py`) is
the only code in this change. The fix is the next order and starts only after the model in
sections 5 to 8 is approved. Section 11 lists what needs a yes, and which published schemas it
would republish.

Builds on [cable-ends-design.md](cable-ends-design.md) (a cable lands on a part of class `port`, or on a
connector slot that takes one), [connectors-power-design.md](connectors-power-design.md) (AC),
[connectors-dc-terminal-design.md](connectors-dc-terminal-design.md) (lugs, plugs and studs) and
[power-outlets-design.md](power-outlets-design.md) (what a panel hands on).

## 1. What went wrong

Wiring a rack's DC feeds with the assistant's tools, every feed was accepted, then flagged loose at both
ends. Four parts showed it; the library's data for each:

| part, in the build tried | what it draws | what is in the data | why the end is loose |
|---|---|---|---|
| `supermicro/psu-pws-601s-1r@1` | two elements, `terminal-rtn` and `terminal-48v`, class `inlet`, and a ground screw | the pole of each is in the element id and its description; the manual (MNL-2570 section 2.8) gives -48 V negative (battery), +Return positive, ground; 12 AWG | an element is not a slot. "has no port terminal-48v" is true |
| `nokia/lpwr-f@1` | one element, `connector-block`, class `terminal` | BAT at the left and RET at the right, each a two-stud terminal for a dual-hole lug, in a provenance sentence | the same, and the block is one element for two terminals |
| `amphenol-ns/nrg300cb08-sens` (`populated`), output `output-a1` | `amphenol-ns/output-terminal@1`: elements `batt` and `rtn` | BATT over RTN, `#10-32`, from the guide; `fed-by: input-a`, `through: breaker-a1` | `output-a1/batt` is an element id and an end names a slot. "is not on this panel" |
| `ufispace/s9701-82dc` (`dc`) | `ufispace/psu-132-dc@1`: one element, `terminal-block` | "Two poles (-48V and return)" in a sentence; no order, no side | nothing says which post is -48 V and which is return |

The parts DO state their terminals. They state them as art and as prose, which no tool reads as a cable end.

## 2. The inventory

`python3 spec/tools/dev/dc_inventory.py --out docs/dc-power-inventory.md` reads the source files (no
build, seconds), lists every component contract that carries a DC end, and says for each what it draws,
whether a cable lands on it today by the kit's own rule (`cableEndsOf`: a registered interface that a
class `port` part mates, on the part or on a part it composes), the polarity a source states and the
words that state it, and the source. It lists candidates by signal (`attr`, `interface`, `element`,
`part`, `name`, `hvdc`, `protector`) and the reader of the output rejects what is wrong. Its test pins the logic on a
small library and the real library on invariants only, so the fix does not have to rewrite it.

Counts, 2026-10-15 (library of 1,499 component contracts and 258 devices):

| | |
|---|---|
| component contracts that carry a DC end | **85** |
| a cable lands on it today | **8 yes** (the P40 output, the two pluggable headers, the barrel jack, three terminal screws, the SR-1 pole pair), **12 through the parts it composes** (9 of them HVDC supplies that land on their AC inlet), **63 no**, 2 not applicable (protectors) |
| devices that place, offer or are fed by one | **146**: 27 land a cable, 103 do not, 16 are DC builds that draw their terminals as no part at all |
| placements of a DC end on a device face | **225**: 128 land (112 of them the P40 output), 5 through parts, 92 do not (64 are `output-terminal`) |
| polarity stated | structured 10 parts, in a sentence only 40, nowhere 35 |

By kind: 22 supplies drawing a terminal block, 21 supplies whose DC end is not drawn at all, 6 supplies with a
"DC inlet" of unspecified connector, 2 with a plug, 9 HVDC-capable supplies on their AC inlet, 6 terminal
blocks, 3 screw terminals, 3 lug pairs, 2 pluggable headers, 3 plugs drawn already seated, 2 bus-bar inputs, one connector block, one
barrel jack, one P40 output, 2 protectors, one other.

By vendor (parts): ufispace 12, nokia 10, common 10, edgecore 9, amphenol-ns 7, cisco 7, telco-systems 7,
dell 6, juniper 6, commscope 3, casa 2, oscilloquartz 2, celestica 1, maiaedge 1, smartoptics 1, supermicro 1.
By vendor (devices): ufispace 43, edgecore 27, telco-systems 13, amphenol-ns 11, nokia 11, aurcore 10,
juniper 8, cisco 7, oscilloquartz 4, then eight vendors with one to three.

What it found that shapes the model:

- **The shapes are few.** A pluggable connector with poles (P40, the 5.08 headers, the barrel jack, the
  telco plugs), a terminal block of screws or studs (one lug per conductor), a stud pair for one two-hole
  lug, and a bus-bar blade. The library already has a seat and a lug or plug for the first three.
- **Polarity is already in the data, in the wrong place.** Ten parts state it in element ids or part ids
  (`terminal-48v`, `a-neg`, `batt`, `wire-1` BATT), 39 in a sentence. Where the source is silent the library
  already declares it: the fuse panel's input says in a `gaps` entry (`input-polarity`, `vendor-silent`)
  that its two terminals are `terminal-1` and `terminal-2` "by position, not by polarity". That is the
  stand-in of section 5.6, found in use.
- **One DC terminal block is already modelled the way section 5 asks.** `nokia/sr-1-dc-terminal-block@1`
  composes four poles `a-neg`, `a-rtn`, `b-neg`, `b-rtn`, each a slot (`stud-pair-5-8`) that a two-hole lug
  lands on, and the printed legend and the guide name each. The model generalises it; it does not replace it.
- **Nothing in the library is a rectifier, a battery shelf or an Anderson-style connector.** Searched by
  name and description. The 2-pin DC connector is the pluggable terminal (`common/dc-terminal-plug-2@1`, the
  telco plugs). The sources of a DC feed in the library are fuse and breaker panels and a chassis bus bar.
- **What it cannot see:** a DC terminal that a device draws as panel decor, with no part (the inventory
  lists 16 such builds with the device's own gap note where it has one), and polarity printed on a
  photograph that no sentence reports.
- **Known limits, from a 20-part check by a reviewer:** a supply that states HVDC only in its provenance
  (a few) is not listed; the `+ - earth` wording of a header is read as "ground" only; the 2-position
  header is left out because its description calls it a relay output, which is a signal and not power; a
  PoE-on-coax data port is not a power end under this definition.
- **HVDC supplies take the AC inlet** (9 parts), so they already land by a C14 or C20 and polarity does not
  arise. They are listed and left out of the model.

## 3. How AC power is cabled today

The pattern the DC model follows, in the order a cable meets it:

1. **An end is a connector slot.** A part that states an `interface` registered in `connectors.yaml` is a
   slot on every device that places it (`iec-c14`, `iec-c20`, `iec-c13`, `iec-c19`, `saf-d-grid`,
   `nema-5-20r`, `eaton-c39`); the registry entry cites a `standards.yaml` entry for the figures. A part with no
   interface is art, whatever its class.
2. **A cord end is a part.** `generic/c13-plug@1` and its siblings are class `port`, `mates` the interface,
   and carry the `cable` point. The slot takes a cable end when a class `port` part mates it
   (`takesCableEnd`, `kit/rack/cable-rules.js`). The plug is derived from the slot and never stored;
   an end states `plug` only where the slot takes several (`endPlug`, ordered by `rating-a`).
3. **An end is a path.** `{item, path, view}`; `psu-1/module/inlet`, `outlet-rear-3`. A zero-U PDU's
   outlets and a card's ports are answered from the catalogue (`zeroUEnds`, kit 0.38, 0.44).
4. **What the part IS comes from its attrs.** `receptacleOf` reads `attrs.outlet` (hands power on),
   `attrs.input` (takes it), `ac` or `dc` where stated; `couplerRole` reads IEC numbering where nothing
   else does. `spec/schemas/power-roles.yaml` decides watts per CLASS: `inlet` is passive ("the supply
   behind it is what draws", and its note names `dell/dc-terminal-6ryj9`), `psu` and `power` are
   supplies with `power-output-w`, `breaker` is passive.
5. **A cable is one row.** `media: power` is a cord or a DC feed, its type says which. `power-c13` and
   `power-c19` in `cable-types.yaml` give a conductor, an outside diameter and a bend radius, flagged
   unverified where one maker is the only source. A cord set pairs its ends (C13 to C14).
6. **Checks warn and refuse nothing** (`mismatch`): data cable into a power end, AC against DC where both
   state it, two outlets or two inlets. A DC feed is the same warning at the same level.
7. **A panel states its wiring as data.** `fed-by` and `through` on an outlet or an output
   (`pdu-model-design.md` section 5; `power-outlets-design.md`): `output-a1` is `fed-by: input-a`,
   `through: breaker-a1`, the breaker's `rating` is a bay attribute. DCIM exports a power outlet and
   its `power_port`.
8. **The cables file leaves power out by reason** (`cable-ends-design.md` section 7, item 8). Unchanged by this note.

## 4. What AC has and DC lacks

| AC has | DC has |
|---|---|
| a registered interface per receptacle, so a slot | 8 of 85 parts; the rest are art or a supply that lands on its AC inlet |
| a cord end part per interface | a ring lug, a two-hole lug, three terminal plugs, one barrel plug, one P40 plug; none for a terminal drawn as art |
| one slot per conductor group (a cord has 3 conductors and one inlet) | one slot per SCREW; a feed lands on "the first free screw" (`cable-ends-design.md` section 3), so the end is not the terminal and a polarity cannot be asked of it |
| a direction (`attrs.input`, `attrs.outlet`) | a direction only where `attrs.input` or the name says it; polarity as no field at all |
| a cord type per connector pair | no DC cable type: no conductor roles, gauge, ampacity or colour |
| the voltage in the connector (C14 vs C20 rating is the plug's) | the voltage in prose |
| `fed-by` and `through` on PDU and panel outlets | `fed-by`, `through` on the fuse panel outputs only; load sides ("PS0 from feed A") in prose |
| nothing to check beyond family and direction | the checks of section 6 all need the facts above |

## 5. The proposed model

### 5.1 Pole and role

A **pole** is one conductor's landing: a screw, a stud, a stud pair a two-hole lug spans, a contact in a
connector. Its **role** says which conductor of a DC circuit lands there, from a closed list kept in a
registry file (`spec/schemas/dc.yaml`, vocabulary like `connectors.yaml`):

| role | what a source writes | note |
|---|---|---|
| `batt` | BATT, BAT, -48V, "negative (battery)", NEG | the supply-side conductor of a negative-ground plant, at the end's stated voltage |
| `rtn` | RTN, RET, return, "+Return", "positive (battery return)" | the return |
| `pos`, `neg` | +, - | for a DC circuit with no battery wording (a 12 V or 24 V supply, the barrel jack) |
| `gnd` | the earth symbol, PE | a bonding conductor; stays `media: ground` and is not a pole of a feed |

`batt` matches `batt`, `rtn` matches `rtn`, `pos` matches `pos`, `neg` matches `neg`; and `batt` matches
`neg`, `rtn` matches `pos` on an end whose stated voltage is negative, because the Supermicro manual
itself pairs them ("-48 Vdc negative terminal (battery)", "+Return positive terminal"). That table is data in
`dc.yaml` with the source beside it. The sign is the end's voltage; the role is never a voltage.

### 5.2 A DC port: the thing a feed lands on

A part that takes or hands on DC states its **DC ports**, a new optional block on the contract:

```yaml
dc:
  ports:
    - id: input                              # the end; its path is the part's path + id when the part has several
      direction: input                       # input | output
      voltage: {nominal: -48, range: [-44, -65]}
      rating-a: 18                           # a supply's input current, a panel output's breaker comes from the bay
      awg: [12]                              # the conductor range the end takes, where a source gives one
      side: null                             # a | b where the part is one half of an A/B pair
      poles:                                 # ordered, one per conductor
        - {role: rtn,  slot: terminal-rtn}
        - {role: batt, slot: terminal-48v}
      source: {poles: terminals}             # the provenance key that says it; stand-in: see 5.6
```

A pole's `slot` names what the conductor lands on, in the part's own terms: a child part that presents a
slot (a screw, a stud pair), a `wire-N` or cavity point of a pluggable connector (the P40 plug already has
`wire-1` BATT and `wire-2` RTN), or, for a terminal drawn as art, an element that the fix turns into a
seat part. Each DC port is published beside `cages[]` as `dc-ports[]` in `components.json` and each
device's `configs.json` (path, direction, voltage, rating, awg, side, poles with their roles and slot
paths). A device placement may override `side`, `voltage`, the roles of its poles and the `rating-a`, because
the same part is the A feed in one place and the B feed in another (`input-a`, `input-b`) and a panel
output takes its rating from the breaker in its bay.

**A DC port takes a cable end when each pole's slot does** (a pole slot takes a ring lug or a two-hole lug,
a connector slot its plug). That is the existing rule, applied to the group; no pole needs a new
cable-end part, and the P40, header and barrel cases are already done.

### 5.3 The shapes, in the library's words

| shape | pole is | cable end at each pole | exists today |
|---|---|---|---|
| terminal block of screws or studs | a screw (`terminal-stud`) | `generic/ring-lug@1` | the lug and two blocks; the SR-1's poles |
| stud pair for a two-hole lug | a pair host (`stud-pair-5-8` and its siblings) | `generic/two-hole-lug-*@1` | yes (#828), the SR-1, the Nokia LPWR-F fits it |
| pluggable connector with poles | a contact (`wire-N`) | the connector's plug | P40, 508-2/5/6, barrel |
| bus-bar blade | a blade | none held | no: `common/orv3-busbar-connector@1` and the fuse panel's `input-feed-busbar` need a blade end |

### 5.4 A DC feed: one cable, or one per conductor

**Recommendation: one cable per feed, N conductors in its type, landing on a DC port at each end.** This keeps
the decision `cable-ends-design.md` section 3 already made ("a DC feed is ONE cable of two conductors,
landing on one terminal at each end and exported as one row"), and the reasons it gives hold:

1. An installer runs, routes, labels and lengths a feed as one thing: "A feed to PSU-0". The route, the
   lay, the bundle, the fill and the label are per cable; two cables per feed double every figure and
   split what the installer reads as one.
2. A fuse panel has 16 outputs; per-conductor cables would make 32 cables to name, route and fill.
3. The DCIM power cable joins two power ports; a feed is one row.

How the other reading shows: **each conductor is still a landing.** Each end draws a lug (or a plug
contact) per pole, and the cable's last stretch fans into the conductors (section 8). A conductor that
runs alone (a return to a bus bar common to many loads, or a single-pole run to one terminal of a panel)
is a **feed of arity 1**: the end names a pole, `output-a1/batt`, which is the failing address of section 1
and is valid in this model, because a pole is a child slot of its port. A cable type states how many
conductors it has; a two-conductor feed lands on a port (all poles), a one-conductor feed on a pole. A
ground wire stays `media: ground`. The rack file needs no new key.

Landing rules:

- A feed's end addresses the **port path** (`psu-0/module/input`) or a **pole path** (`.../batt`).
  Today's rule, "the first free screw in natural order" (`cable-ends-design.md` section 3), goes away:
  the port is the end and its poles are taken together.
- Conductor k of the cable lands on pole k, in the order the cable type gives them. Where both ends
  state their roles the kit matches by role; a feed whose roles cross is a polarity finding (section 6).
- A port is free when no cable lands on it or on any of its poles. One pole taken by a single-conductor run
  makes the port partly used; a two-conductor feed to it is refused as `taken`, as a taken port is today.

### 5.5 Cable types

`cable-types.yaml` gains DC feed types in the family `power` (same `media: power`, so no rack key changes):

```yaml
dc-feed-2x14awg:
  label: DC power feed, 2 x 14 AWG, ...
  media: power
  family: power
  dc: true
  conductors: [{role: batt, awg: 14}, {role: rtn, awg: 14}]
  ampacity-a: ...                     # from a table that is cited, or marked estimated
  od_mm: ...
  min_bend_radius: {installed: {xOD: ...}}
```

A type gives the conductor roles and the colour of each ONLY where a source does (the AC entries mark
unverified what one maker states; the same rule). Gauges to start: those the library's ends state (12 AWG,
14 to 10 AWG, #6, 1.5 mm2). The kit reads `od_mm` and the bend radius as it does for every type. A cable
with `media: power` and no type keeps its defaults (7.1 mm), as now.

### 5.6 A part whose source states no polarity

**A declared stand-in, never a guess.** The pole's role is written `unstated`, with:

```yaml
- {role: unstated, slot: terminal-1, stand-in: {order: left-to-right}}   # on the port, not the pole: order is the port's
```

and the device carries a `gaps` entry (`what: dc-polarity`, `reason: vendor-silent` or `needs-drawing`,
with `wanted`) exactly as the fuse panel's input does today. Lint refuses a role that has no `source` key
and an `unstated` role with no gap. The surfaces show it as "?" on the pole and a note
("polarity of `terminal-1` is not stated; checked by position"). The checks run by position and say so;
nothing is warned as crossed on a stand-in, because the library does not know. A stand-in is never
promoted to a role by a convention that merely sounds right ("BATT is on the left"): only a source does.

### 5.7 Sides and ratings

- **Side.** An output or an input is `side: a` or `b` where its part is one half of an A/B pair: the fuse
  panel's two input feeds and the outputs they feed (`fed-by`), a chassis's feed A and feed B terminals
  (the Nokia SR-1 `a-neg`, the UfiSpace "two independent power circuits"), a load's `PS0 from feed A`
  (today a prose `input` attribute). On a load with a supply per feed the side is a property of the supply
  bay.
- **Rating.** A source output's rating is the breaker or fuse in its bay (`through:` and the bay's `rating`
  or `fuse-rating`, already in the fuse panel's examples). A load's is its input current
  (`current-max-a`, `input-voltage`, already attributes on a dozen parts) or its maximum draw over the low end
  of its voltage range. A cable's is the type's `ampacity-a`.

## 6. The checks

All warnings, none a refusal, at the level of `mismatch`; each is said only where both sides state what it
reads, and says what is missing otherwise. A polarity warning is first in the list.

| check | reads | says |
|---|---|---|
| polarity matched end to end | each pole's role on both ends | "A is BATT where B is RTN": the feed is crossed. `batt` to `batt`, `rtn` to `rtn` (5.1 for the pairs) |
| the feed is to the right voltage | each port's `voltage`: sign, nominal against the other's range | "-48 V into a +24 V input"; "source nominal -48 V is outside the load's -40.5 to -57" |
| conductors against poles | the type's `conductors` against the port's `poles`; the type's `awg` against the port's `awg` | "a two-conductor feed to a three-pole port"; "14 AWG where the end takes 12" |
| A and B kept to their sides | `side` on source and load, and the load's two supplies | "both supplies of X are fed from side A"; "feed A lands on a B terminal" |
| a protector against the load | the breaker or fuse rating, the load's current, the cable's ampacity | "30 A breaker on a 40 A load"; "60 A breaker on a 14 AWG feed". Quiet where either side is not stated |
| direction | `direction` of each port | "both ends are outputs", as outlet to outlet is warned today |
| AC against DC | as today | unchanged |

## 7. Schema, standards and cable types

| file | change | published? |
|---|---|---|
| `spec/schemas/component.schema.json` | the optional `dc` block of 5.2 (ports, voltage, rating, awg, side, poles with roles, the `stand-in` marker); additive, `format` unchanged | **yes**, `/schemas/v1/`: needs a yes |
| `spec/schemas/device.schema.json` | an optional per-placement `dc` override (side, voltage, rating, the roles of poles); additive | **yes**, `/schemas/v1/`: needs a yes |
| `spec/schemas/rack.schema.json` | **none.** A feed is `media: power`; an end is a path; the port path or a pole path are paths. Only the `end.path` and `media` descriptions get a sentence | the text change republishes it if the sentence is wanted; skipping it costs nothing |
| `spec/schemas/connectors.yaml` | none for the shapes that exist; the bus-bar blade needs one entry when its end is drawn | no (tooling vocabulary) |
| `spec/schemas/standards.yaml` | entries only where a figure is sourced: -48 V plant range, the terminal-block figures a vendor prints; nothing invented. Candidate sources to read and cite in the fix: the ETSI and ATIS documents for -48 V telecom plants | no |
| `spec/schemas/dc.yaml` (new) | the role vocabulary and the match table of 5.1, each pair with its source | no |
| `spec/schemas/cable-types.yaml` | the DC feed types of 5.5 | no (compiled into `cable-types.json`) |
| `spec/schemas/power-roles.yaml` | none. `inlet` and `breaker` stay passive; DC ports are not a class | no |
| lint (`lint.py`) | new rules, next free numbers: a role is in the vocabulary and has a source; a pole's slot resolves; a port's poles are all slots or all points; an `unstated` role has a gap; a voltage has a sign where it is negative | no |
| DCIM exports | none. A DC output remains a power outlet, an input a power port, as today; the cables file keeps leaving power out | no |
| `kit/` | section 8; a minor version of the kit | the kit is published |

If no schema republish is preferred, the fallback is `attrs` on the part and the placement
(`dc-poles: 'rtn,batt'`, `dc-side: a`): no schema change, and unstructured; the library's experience with
`stud-size` is that a text attribute is a fact "nothing reads". The recommendation is the schema.

## 8. How the surfaces show and offer DC ends

- **2D (the panel).** A DC port is drawn as it is: the lugs or plug on the poles. Each pole's role is a
  legend on the pole (`-48V`, `RTN`, `?` for a stand-in), taken from the data and not from a colour. The
  port's hover reads "output-a1, BATT / RTN, -48 V, 30 A (breaker-a1), side A".
- **3D.** The lug seats already draw on `terminal-stud`, and the plug's `wire-N` points are the cable's
  landing (#805 is the pending work for routing to them). A feed ends at the port's `mate` and fans into its
  conductors over the last 10 to 30 mm (the stub lengths the plugs already use) to each pole's lug.
- **The cable editor.** A free port is one row per DC port, not one per screw ("output-a1, -48 V BATT/RTN,
  30 A") with its poles under it; `freePorts` gains `ports` and drops the `of`/`first` of 5.4. A DC
  feed shows its two ends' roles side by side and the findings of section 6 beside them; a crossed feed is
  red. The cable type picker offers the DC types when the first end is DC (the way `proposeMedia` offers
  `power` today).
- **The assistant's tools.** `ports.free` lists DC ports with direction, voltage, side, rating and poles.
  `cable.add` accepts a port path or a pole path, resolves `output-a1/batt` and states which. `cable.update`
  and `apply` return the findings of section 6 in the same `findings` list. The failing messages of
  section 1 change from "has no port terminal-48v" to either the end it is or, for a part not yet modelled,
  "terminal-48v is drawn on this part but it declares no DC port; its poles are RTN and -48V in its
  provenance" (the part is named, and so is what is missing).
- **Parts not yet modelled keep working as now.** An end on a part with no DC port is loose with the sentence
  above; nothing a rack file already holds is rewritten.

## 9. The four failing cases under the model

| case | what the contract gains | the end |
|---|---|---|
| `supermicro/psu-pws-601s-1r@1` | one input port, `-48 V` (-44 to -65), 12 AWG, poles `rtn` on `terminal-rtn` and `batt` on `terminal-48v` (MNL-2570 section 2.8); the terminals become seats. The manual's supplied cable uses a Positronic CBD connector, so the plug is a connector, not a lug; the ground is `media: ground`, as it is | `psu-0/module/input` or `.../terminal-48v` |
| `nokia/lpwr-f@1` | one input port, -40.5 to -72 V, 80 A; pole `batt` on a `stud-pair-5-8` seat (BAT, left) and `rtn` on another (RET, right), UDS p96 and USIM p265 | `<bay>/module/input`; each pole lands one dual-hole lug |
| `amphenol-ns/output-terminal@1` | an output port; poles `batt` (screw) over `rtn` (screw), `#10-32`, lug up to 0.5 in; the side from the placement's `fed-by`, the rating from the breaker in the bay | `output-a1`, or `output-a1/batt` for a single conductor. The input pair is a stand-in: its terminals are `terminal-1`/`terminal-2` "by position" and the existing `input-polarity` gap is its declaration |
| `ufispace/psu-132-dc@1` | one input port, -40 to -75 V, 40 A (the s9701-82dc device attribute), two poles whose roles are `unstated` until the guide's connecting-power figure is read; the device gap `dc-polarity` says so | `psu-0/module/input`; the cable editor shows `?`/`?` and the note |

## 10. The fix's plan, with sizes

Sizes: S under a day of work, M a few days, L a week or more; counts are from the inventory.

| step | what | size |
|---|---|---|
| 1. Registry, schema, lint (landed: the `dc` blocks and lint rules L187 to L191; no library part carries a `dc` block yet, so this inventory, which reads `interface` and `attrs`, is unchanged) | `dc.yaml`; the `dc` block in `component.schema.json` and the placement override in `device.schema.json` (after the yes); lint rules; tests with synthetic parts. No library part changes yet | M, one PR |
| 2. Build | publish `dc-ports[]` in `components.json` and `configs.json` (`render.py`, `components_index.py`, the device index); the device lock treats a port as an export fact (a minor on a device that places one) | M, one PR |
| 3. Cable types | the DC feed types, each sourced or marked estimated; `cable-types.json` | S, one PR |
| 4. Kit 0.48.0 (the kit on main now; the next minor if another has merged) | `cableEndsOf` for a DC port, pole addresses, the DC free-port rows, the checks of section 6, the plug derived per pole, the assistant tools' text; every `check_rack_*` | L, one or two PRs |
| 5. Viewers | the pole legends in 2D, the fan-out in 3D, the editor rows | M, one PR |
| 6. Library by vendor, each terminal with its source | in this order (parts are the part's namespace; devices are those that place or offer one of those parts): **(a) amphenol-ns and common**: 17 parts, 36 devices, 221 placements; polarity already structured, the P40, headers and barrel already slots: S to M, two PRs. **(b) supermicro and nokia**: 11 parts, 10 devices, sources in hand: M. **(c) ufispace**: 12 supplies, 40 devices (+3 DC builds with no part); polarity mostly unstated, so mostly stand-ins plus a re-read of the guides: L, split by supply, the PSU-132 first because it is the S9701's. **(d) edgecore, juniper, cisco**: 20 parts, 29 devices (+4): L, three PRs. **(e) telco-systems, dell, commscope, casa, oscilloquartz, smartoptics, celestica, maiaedge**: 16 parts, 15 devices (+9): M to L. (The 9 HVDC supplies are out, section 11.) Each device takes a minor bump from the lock, and each PR is one vendor so its merge danger names one family. The 16 DC builds that draw their terminals as no part need a part drawn first: a separate list, S each | M to L each, about nine PRs |
| 7. A regression fixture | the failing scenario of section 1 as a synthetic rack built from library parts: a panel's A and B outputs to two loads, one crossed and one not | S |

Order, not parallel: 1 before 2, 2 and 3 before 4, 4 before 6. 5 can follow 4 beside 6(a).

## 11. What needs a yes

1. The recommendation of 5.4: one cable per feed, poles as child slots, arity 1 for a single conductor.
2. The two schema changes of section 7: `component.schema.json` and `device.schema.json`, additive, each a republish of
   `/schemas/v1/`. Or the `attrs` fallback.
3. The role vocabulary and its match table (5.1), in particular `batt` matching `neg` and `rtn` matching
   `pos` on a negative-voltage end.
4. Stand-ins (5.6): a pole with no sourced role is `unstated` with a gap, and no check calls a feed crossed on it.
5. HVDC through the AC inlet stays out of the model.
6. A sentence on the rack schema's `end.path` and `media` (optional).

## 12. What this note does not do

It changes no part, device, schema, kit file or export. It does not read the standards it names as
candidates; it cites no figure it did not find in a library file. It does not decide the 16 devices that
draw their terminals as decor.

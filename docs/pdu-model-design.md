# Rack PDUs: capability, outlet state, input, phases and mounting

Status: proposed, 2026-10-08. Issue #934. Extends
[power-outlets-design.md](power-outlets-design.md) (#806), which made a power
outlet an export, and builds on
[vertical-cable-managers-design.md](vertical-cable-managers-design.md) section 8
(#926, zero-U parts in the kit), the rack mounting note of #904 (ears and
kits) and the AC connectors of #933.

The first rack PDU, the Eaton EVMI2130X, is built. It answered several of the
questions this note was opened for, and its answers are taken here as precedent
unless a section argues otherwise. Three more PDUs follow it (section 9).

## 1. What the pilot settled

| question | the EVMI2130X answer | this note |
|---|---|---|
| sections | a `region` per section, naming its outlets, its label strip and its breaker | kept |
| section colours | a field (`section-color`) on the label strip and the breaker, set per placement | kept |
| breakers | fixed parts (`eaton/g4-breaker-20a-2p@1`), not bays, so no `through` | **changed**: `through` may name a fixed breaker (section 5) |
| phases | the one-line diagram in prose, on the breaker descriptions and region labels | kept as prose, and stated once as data (section 5) |
| `feed_leg` | not written: every outlet is line to line | kept, and made a rule (section 5) |
| outlet names | as printed (A1 to C42), through the device `interfaces:` rules | kept |
| mounting | `mount: rack-side`, `ru: 39`, two `eaton/g4-mounting-button@1` on the rear | kept for now (section 6) |
| the C39 | `eaton/c39-outlet@1`, an Eaton part, exported as `eaton-c39` | kept |
| input | a fixed-cord part (`eaton/g4-cord-l21-30p@1`) exported as a `nema-l21-30p` power port | kept |
| input rating | `attrs.power` prose and four numbers | given structured keys (section 4) |

The pilot also left two findings that this note has to answer. Its capability
assessment reports `specified: false`, because the `power` profile asks for
`input-ac` and for a draw figure, and the pilot states neither (section 4). And
the EVMI2130X is a metered-input PDU, so none of its outlets can be switched:
the outlet state #934 asks for is a question for the next
three devices, not for the pilot (section 3).

## 2. Capability

### 2.1 What the vendors sell

The G4 installation and setup guide (P-164001156, section 1.1 and its Table 1)
names six topologies by what they meter and whether they switch:

| topology | input metering | branch metering | outlet metering | outlet switching |
|---|---|---|---|---|
| Basic (BA) | - | - | - | - |
| In-line metered (IL) | yes | - | - | - |
| Metered input (MI) | yes | yes | - | - |
| Metered outlet (MO) | yes | yes | yes | - |
| Switched (SW) | yes | yes | - | yes |
| Managed (MA) | yes | yes | yes | yes |

The Tripp Lite series sells basic, metered, monitored and switched PDUs. Its
switched units meter the input and each bank and switch each outlet, which is
the G4 SW row.

So a capability is two facts and not one ladder: how far down the metering
goes, and whether an outlet can be switched. Switched and metered outlet are not
ordered; each has what the other lacks.

### 2.2 Decision

**Two keys in `attrs.management`**, and the class name derived from them:

```yaml
attrs:
  management:
    metering-scope: branch      # none | input | branch | outlet
    outlet-switching: false
```

- `metering-scope` is the finest level metered. Every vendor in scope meters
  each level above the one it names, so one word carries the three columns.
- `outlet-switching` is a boolean.
- The class (`basic`, `metered-input`, `metered-outlet`, `switched`,
  `managed`) is DERIVED and published in `configs.json` and `devices.json`, so a
  catalogue can filter on it and no manifest can state a class that its two
  facts contradict. `in-line` is `metering-scope: input`.
- **Per outlet, the vocabulary is the statement.** An outlet that can be
  switched carries the outlet state vocabulary (section 3.3); one that cannot
  carries none. Lint ties the two: with `outlet-switching: true` every outlet
  declares it (a warning naming each outlet that does not, because a PDU with a
  few unswitched outlets exists), and with `false` none does (an error).
- Per-outlet metering is not stated per outlet. None of the four devices varies
  it, and the device key holds until one does.

Rejected: one enum (`pdu-class`) as the stored fact, which a PDU whose vendor
names its own classes would have to translate into ours and which hides the two
facts a consumer filters on; a boolean per column, which can state outlet
metering without input metering, which nothing sells.

### 2.3 What DCIM can carry

Read from each project at the commits named: NetBox `dcim/choices.py` and
`dcim/models/device_component_templates.py` at `2b3f4b48`; Nautobot
`dcim/models/device_components.py` at `c77e4255`.

- **A device type has no capability field** in either target. The export writes
  the derived class and the two facts in the device type `comments`, as it
  writes other facts neither schema can hold.
- **An outlet template has no switched flag** in either. A NetBox power outlet
  INSTANCE has a `status` (`PowerOutletStatusChoices`: `enabled`, `disabled`,
  `faulty`), which a template cannot set; Nautobot has no outlet status at all.
  So capability is not exported per outlet, and outlet state is not a device
  type fact (section 3.1).

## 3. Outlet state

### 3.1 Where it lives

Whether an outlet is on is a fact about one PDU in one rack at one time, not
about the model. Three homes were weighed.

| home | for | against |
|---|---|---|
| `states` alone, set in a marks document | the machinery exists: a part declares a vocabulary, the drawing emits `data-states`, `kit/marks.js` puts `state-<name>` on whatever a mark selects, and `kit/states.js` answers which states paint | a marks document is one drawing; a rack holds forty PDUs and needs the state on the rack entry |
| a field | fields are already carried by a marks document and by a rack item | a field is text written ON the hardware (a label, a wattage on a supply); on/off is not printed anywhere, and a field cannot reach the state stylesheet |
| a Rack Builder layer | the rack file is where an installed PDU lives, beside its `swaps` and `fields` | it would invent a second vocabulary unless it reuses the first |

**Decision: the vocabulary is the library's, the value is the document's.**

1. **The device declares what an outlet can be,** with the existing `states`
   key on the outlets group (or a placement): `[on, off]`. The vocabulary only
   appears where `outlet-switching` is true (section 2.2).
2. **A marks document sets one,** as it sets a lamp state today:
   `{select: "[data-path='outlet-a1']", state: off}`. No new key.
3. **A rack entry sets many.** A rack item gains `states`, a map of part path
   to state name, beside its `swaps` and `fields`, with the same entry-by-entry
   normalising that `fields` has; a `zeroU` entry gains `swaps`, `fields` and
   `states` together, because a zero-U PDU has a network module to swap and
   section labels to fill as much as a rack item does. The kit applies the map
   with one function shared by the marks document and the rack file, as
   `shell.setFields` is shared today.
4. **An instance export maps it:** `on` to NetBox `enabled` and `off` to
   `disabled`, when a rack export writes power outlet instances. The device type
   export writes nothing.

### 3.2 How an outlet that is on is drawn

The sources settle more than the question assumed.

- The G4 guide (section 1.3) says the metered-outlet, switched and managed
  models carry an LED per outlet, and the G4 brochure (BR155056EN) says the LED
  is green when the outlet is powered and red when it is not. The EVMA8365X
  drawing shows the lamp as a small bump above each outlet.
- The Tripp Lite switched manuals (the multi-model monitored and switched
  manual, and the PDUMH15NET/PDUMH20NET manual) say each outlet has an LED that
  lights when the outlet is live, and say nothing of a second colour.
- The metered-input EVMI2130X has no outlet LED because it has no outlet
  switching: there is no state to show.

So **every PDU that can switch an outlet in scope has a lamp for it**, and the
state is drawn on the real lamp:

- **The lamp is its own part, placed beside the outlet with `for:`** naming
  the outlet: `eaton/g4-outlet-led@1` on the G4, a Tripp Lite lamp part on the
  other two. `for:` already means "this lamp annotates that", L76 already
  exempts a lamp drawn beside its jack, and the outlet stays the plain
  `std/c13-outlet@1` that `PART_OUTLET` exports. A composed outlet-with-lamp
  part was rejected: it would make a standard C13 an Eaton part, with a
  `PART_OUTLET` row of its own, to carry a lamp the outlet does not contain.
- **The state is addressed by the outlet, and follows `for:` to the lamp.** A
  user switches off A1, not the lamp beside it, and the rack file keys by the
  outlet path. The kit, applying `state-off` to a path, also applies it to each
  element whose `data-for` names that path. This is the one kit change outlet
  state needs; today a mark reaches only what its selector matches.
- **The colours are the device statement:** `states: [{name: on, color:
  '#22c55e'}, {name: off, color: '#ef4444'}]` on the G4 lamps, and on and an
  unlit off on the Tripp Lite lamps, unless a photograph shows otherwise. An
  `off` that is LIT (red) is new: `kit/states.js` treats `off` as the absence of
  a state and `kit/marks.js` skips a custom lamp colour on `off`. Both still
  work, since a declared off colour reaches the drawing as a scoped rule; the
  comment in `states.js` that says `off` is unlit becomes "unlit unless the
  device declares a colour".

**A switched outlet with no lamp** is not in scope, and the fallback is stated
so the first one does not invent a lamp: the base stylesheet dims an outlet
whose state is `off` (as `absent` does, at a different opacity) and draws `on`
as shipped. Nothing is drawn that the hardware does not have.

**A dead outlet behind an open breaker** is the state a metered-input PDU does
have. The G4 breaker already declares `states: [on, off]` on its rocker. With
`through` naming the breaker (section 5), the kit can dim every outlet whose
breaker is `off`, which is the true picture of a tripped branch on any PDU,
switched or not. This needs `through` emitted as `data-through` (it is not
emitted today) and is a second, optional kit step.

### 3.3 The state vocabulary

`on` and `off`. NetBox has a third instance status, `faulty`; no PDU in scope
documents an outlet fault state, so none is declared, and a later PDU that
documents one adds `fault` to its own vocabulary and maps it to `faulty`.

### 3.4 Load per outlet

Load is a reading, not a state: a number that changes, with a unit. It is not
printed on the hardware, so it is not a field; it is not a choice among names,
so it is not a state.

**Decision: a `readings` map, carried as `fields` and `states` are.**

```yaml
readings:
  outlet-a1: {current-a: 1.8, power-w: 372}
  breaker-a: {current-a: 11.2}
  input: {current-a: 19.6}
```

- The key is a part path, so the same map reads a branch (a breaker path) and
  the input (the cord) as well as an outlet.
- Three reading names to start: `current-a`, `power-w` and `energy-kwh`, each a
  number. They are the three quantities the G4 MA and MO models meter per
  outlet.
- **The device declares what can be read where,** from `metering-scope`:
  `input` admits readings on the input, `branch` on the breakers or banks too,
  `outlet` on every outlet. The kit refuses a reading where the PDU meters
  nothing, with a sentence, as it refuses a swap a slot does not accept.
- **The kit draws a reading as an annotation,** a small badge beside the part
  in the legend ink and not in the hardware palette, with the reading time in
  the legend. A static export says what it shows and when.
- A PDU display that shows a load (the Tripp Lite ammeter) can show the input
  reading; it is a display with `characters` (section 9), and the kit writes
  the rounded figure into it.

Carried by a marks document (a new top-level key, beside `fields`) and by a
rack entry. Rejected: a mark `label` (prose, not typed, and drawn only in the
legend), and a field (section 3.1).

## 4. Input rating

### 4.1 What the profile asks

`spec/schemas/profiles.yaml` gives the `power` profile two `attrs.power`
requirements: one of `input-dc` or `input-ac`, and one of the `power-max-w`
spellings, the unit's own draw, with the warning that the power it carries is
not a draw. The pilot states `input-voltage`, `input-current-a`,
`plug-rating-a` and `capacity-kw`, which match neither, so `specified` is
false.

### 4.2 Decision

```yaml
attrs:
  power:
    input-ac: '200-240 V three-phase delta, 3W+PE, 40 A, 50/60 Hz'  # prose, as 70 devices write it
    input-plug: cs8365c            # the input power port type: a PART_POWER value
    input-cord: fixed              # fixed | detachable
    input-phase: three             # single | three
    input-wiring: delta            # wye | delta; absent when single-phase
    input-voltage-v: 208           # nominal, as a source states it; line to line when three-phase
    input-current-a: 40            # the rated input current, derated
    plug-rating-a: 50              # what the plug is rated for, when it differs
    capacity-kw: 14.4              # the load it can hand on; never a draw
```

- **`input-ac` stays the prose key.** Seventy devices write it, the profile
  reads it, and it holds what no number can (a range, a frequency). Every PDU
  states it; the pilot gains one.
- **`input-plug` is a slug, not prose,** and it is the type the input part
  exports: lint checks that it equals the `PART_POWER` value of the part the
  outlets are `fed-by`. The pilot prose (`NEMA L21-30P on a fixed 10 ft cord`)
  splits into `input-plug`, `input-cord` and the provenance.
- **`input-current-a` and `plug-rating-a` are both kept,** because the SKU
  titles give the plug rating (30 A, 50 A) and the drawings the input rating
  (24 A, 40 A), and a reader who sees one figure will assume the other.
- **`capacity-kw` keeps its pilot spelling,** with the pilot
  `capacity-scope` sentence where a source qualifies it.
- **The draw requirement is not weakened.** A PDU with a network module does
  draw power; no held source states how much. The unstated draw stays the
  visible `specified` gap it is. Accepting `capacity-kw` in its place would be
  the carried-for-drawn confusion the profile warns against.

### 4.3 What DCIM can carry

Neither target has an input rating on a device type: a power port template
carries a type and two draws in watts, and the amperes, volts and phase are
fields of a power FEED, an instance. The export writes the rating into the
input power port `description` (NetBox keeps it; whether a Nautobot import
keeps a power port description is to be checked as #806 checked the outlet)
and into the device type comments, and leaves `maximum_draw` empty.

## 5. Phases, breakers, sections and `feed_leg`

### 5.1 What the four devices have

| device | input | outlets wired | breakers |
|---|---|---|---|
| EVMI2130X | 120/208 V three-phase wye, L21-30P | line to line, 208 V | 3, each across a line pair, each feeding 2 sections |
| EVMA8365X | 200-240 V three-phase delta, CS8365C | line to line (delta has no neutral) | 6, one per section, each across a line pair |
| PDUMV20HVNETLX | 208/230 V single-phase, C20 inlet, L6-20P cord | line to line | 2, one per bank, positions undrawn |
| PDUMH20NET | 120 V single-phase, L5-20P | line to neutral | none stated |

### 5.2 `feed_leg`

`feed_leg` names ONE leg of a three-phase feed (NetBox and Nautobot
`PowerOutletFeedLegChoices`: `A`, `B`, `C`). **It is written exactly when the
input is three-phase wye and the outlet is wired line to neutral,** and it is
that line: L1 is `A`, L2 `B`, L3 `C`.

- A line-to-line outlet sits on two legs and has no honest single answer: the
  EVMI2130X and EVMA8365X write none.
- A single-phase PDU is on whatever leg its plug is on, which is a fact of the
  installation, not of the device type: the Tripp Lite pair write none.
- None of the four devices writes one. The rule is stated now so that the first
  230/400 V wye PDU (C13s line to neutral) does not reopen the question.

### 5.3 Stating the wiring once, as data

The pilot states its one-line diagram in prose, three times over: on each
breaker description, each region label and the provenance. The rule above needs
it as data, and so will the Rack Builder when it sums load per line.

- **`lines` on the protecting placement:** a new placement key on a part of
  class `breaker` (or, where an outlet has no breaker, on the outlet), a list
  of one to three of `L1`, `L2`, `L3` and `N`. `[L1, L2]` is line to line;
  `[L1, N]` is line to neutral. The pilot breaker A says `lines: [L1, L2]`.
- **`through` may name a fixed breaker.** #806 made `through` the bay a circuit
  runs through and the pilot did not write it, because its breakers are fixed
  parts. Widening it costs little and buys three things: the outlet description
  in both targets says which breaker protects it (as the 300CB08 outlets do), an
  outlet reaches its `lines` through its breaker instead of restating them, and
  the kit can dim the outlets of an open breaker (section 3.2). L133 then
  accepts a bay OR a placement of class `breaker`, and L135 (one position, one
  circuit) applies only when `through` names a bay, since a PDU breaker feeds
  fourteen outlets by design.
- **Sections stay regions.** A region is a drawing grouping and carries no
  power semantics; the export does not read it.
- **Without either key,** an outlet takes its lines from the input: single-phase
  input, no `feed_leg`; three-phase with no `lines` anywhere, no `feed_leg` and
  a warning that the wiring is unstated.

Stating `through` or `lines` is a minor version, as `fed-by` is, and changing
one is a major: both move an imported outlet description or `feed_leg`.

## 6. Mounting a zero-U PDU

### 6.1 Today

`mount: rack-side`, `ru` the height it is sold for, and its buttons as
placements on the rear view. The kit places it with `zerou.place` at an
attachment point (`left`, `right`, or the four `left-front` to `right-rear` of a
four-post), fits it by `ru`, and declares no guides, so no cable lane runs
through it. This stays the mount until racks are products (#935).

### 6.2 The mounting interface: a proposed vocabulary

#939 (a bracket the PDU hangs on) and #935 (a cabinet zero-U channel) both need
to check a PDU against what it hangs on, and #939 says whichever lands first
sets the vocabulary. This note proposes it.

- **A mount point** is a feature of the hanging part that engages the frame:
  a button, a stud. On the PDU it is already a placement, so its position is
  data the drawing holds.
- **A slot** is the feature that takes it: a keyhole in a bracket or a channel.
- **A mounting interface** names the pair, as a connector interface names a
  plug and its socket, in a `mounting:` block of
  `spec/schemas/connectors.yaml`, so the turns and `mates` machinery is not
  reinvented. The G4 guide (2.11) gives the first: a shoulder button for
  keyhole slots 11.5 to 12.5 wide in 1.5 to 2 mm sheet, or 14 wide in 3 mm.
  Proposed id: `pdu-button`. The Tripp Lite buttons are checked against it
  when that PDU is modelled.
- **Pitch** is the centre-to-centre distance of two mount points along the
  length, in millimetres: 1555.8 on both G4 PDUs (each drawing dimensions it),
  1556 on the PDUMV20HVNETLX. The pitch is NOT a new manifest key. It is
  derived from the button placements, which already sit 1555.8 apart on the
  EVMI2130X rear view, and published per configuration in `configs.json` as
  `mount-points: [{interface: pdu-button, at: <mm from the bottom>}, ...]`. A
  second statement of a number the drawing already holds is a number that can
  disagree with it.
- **The button part declares the interface:** `eaton/g4-mounting-button@1`
  gains `interface: pdu-button`, a patch.
- **The other side** (#939 bracket, #935 channel) declares its slots with the
  same interface and either their positions or a slot spacing. The kit refusal
  `fitsZeroU` does not make yet (#926 section 8) is then: every mount point
  lands on a slot of its interface, within a stated tolerance, or the placement
  is refused with a sentence naming the point that misses.

### 6.3 The zero-U channel against rack-side

`rack-side` says the part stands beside an upright, outside the rails. A G4 in
a cabinet stands in the zero-U channel inside the side panel, and the G4 guide
(2.9, Figure 7) shows one or two PDUs a side. #926 section 8 left the channel
as a key on the zero-U entry, from the product frame. This note agrees and adds
nothing to the device: the same `rack-side` PDU is placed on an attachment
point of a generic frame, on a bracket (#939), or in a named channel of a
product frame (#935). Where it hangs is the rack file, never the device. A
`zero-u-channel` mount value was considered and rejected: the PDU is the same
part in all three.

### 6.4 Two PDUs a side, and L154

Two lab placements of `rack-side` parts on one side of a rack overlap in height
whatever their `face` (L154, an error), because a lab `face` on a rack-side
part says which way its working face looks, not which upright it is on. Two
39U PDUs a side, front and rear, therefore fail the lab check. The kit is
already more permissive: two parts on different attachment points (`left-front`
and `left-rear`) never meet.

**Decision:** a lab rack-side placement takes the kit attachment point names,
and L154 claims per attachment point, as `fitsZeroU` does. On a two-post rack
there is one point a side and the rule is unchanged; on a four-post, front and
rear are two points. When channels arrive, both claim per channel. Duct sections
that stack keep stacking, since they share a point. This changes the lab format
(`labs.json` gains the point), so it is a step of its own, after the devices.

## 7. A 1U or 2U PDU (PDUMH20NET)

A horizontal PDU is an ordinary `mount: rack` device and needs nothing new:

- **Ears** through `chassis.ears` (#904): `{positions: [{name: flush, default:
  true}]}`, with the generic L-bracket ear drawn from it (#909). The spec sheet
  says the ears are reversible, front- or rear-facing; a rear-facing mount is a
  `rear` position if the ears move, or a rack item `turned: true` if the unit
  turns, and the photographs decide which.
- **Outlets front AND rear** are placements on both views, each `fed-by` the
  one input, named by `interfaces:` rules if the unit prints numbers and by
  placement id if it does not.
- **The rear cord** is a fixed-cord part on the rear view, as the G4 cord is on
  the end view, exported as `nema-l5-20p`. The 5-20P adapter in the box is not
  modelled.
- **The network card slot** is a module bay, as the eNMC is.

## 8. The export

Nothing in the #806 block changes shape. Rows gain:

```yaml
power-ports:
  - name: input
    type: cs8365c
    description: '200-240 V three-phase delta, 40 A input (50 A plug)'
power-outlets:
  - name: A1
    type: iec-60320-c13
    power_port: input
    description: Through breaker A, lines L1-L2
```

`feed_leg` is written only under the rule of section 5.2. Comments gain the
capability (section 2.3) and the input rating.

## 9. The remaining devices, in order

### 9.1 EVMA8365X (G4 managed, 0U)

Reuses: `std/c13-outlet@1`, `eaton/c39-outlet@1`, `eaton/g4-outlet-labels@1`
(the letters D, E and F are fields), `eaton/g4-breaker-20a-2p@1` (six),
`eaton/g4-mounting-button@1` (the first 124.0 from the cord end, against 72.0;
the same 1555.8 pitch), `eaton/g4-enmc@1` (to be checked against this drawing,
which lists a power redundancy port, an EMP port and two USB-C), and
`common/ground-screw-m6@1`.

Needs new:

- `eaton/g4-outlet-led@1`, the lamp bump above each outlet, read off drawing
  9001-22312, with `on` green and `off` red (section 3.2), 42 placements with
  `for:`;
- `eaton/g4-cord-cs8365c@1`, the fixed cord at the end cap, in `PART_POWER` as
  `cs8365c` (the slug #933 verified); the plug face is #933
  `generic/cs8365c-plug@1`;
- the 1829 x 52 x 65 chassis, which is not the pilot chassis;
- `lines` on six breakers and `through` on 42 outlets, from the one-line
  diagram read at zoom: the pairing of A to F onto L1, L2 and L3 is not yet
  stated by any held text;
- `metering-scope: outlet`, `outlet-switching: true`, so the outlets group
  declares `[on, off]` and the outlets admit readings.

Its gallery is mostly the shared CHASSIS_424 shots and close-ups of its
metered-input sibling; cite those as sibling evidence.

### 9.2 PDUMV20HVNETLX (Tripp Lite series switched, 0U)

Reuses: `std/c13-outlet@1`, `std/c19-outlet@1` (#933), `std/c20-inlet@1` as
the input power port (`iec-60320-c20`, already in `PART_POWER`), and common
RJ45, USB and lamp parts for the LX interface.

Needs new:

- the Tripp Lite namespace and its vendor entry (the vendor registry deferred
  it to the first Tripp Lite part); whether these parts are `eaton/` or a
  `tripplite/` namespace is an open question (section 11);
- a mounting button (1556 pitch, 134.01 from the top) with `interface:
  pdu-button` if it fits the interface, and the removable brackets of drawing
  details A to E as decor or parts;
- an outlet lamp part, `on` lit and `off` unlit;
- the digital load meter as a display with `characters`;
- the cord retention bracket at the inlet;
- two bank breakers, whose positions the submittal drawing does not show: a
  `gaps:` entry until the manual figures or a photograph place them;
- `input-cord: detachable`, `input-plug: iec-60320-c20` with the L6-20P cord
  in the provenance and prose, `metering-scope: branch`, `outlet-switching:
  true`.

### 9.3 PDUMH20NET (Tripp Lite series switched, 1U)

Reuses: `std/nema-5-20r@1` (#933), the D-sub receptacle for the DB9 config
port, the outlet lamp and mounting vocabulary of 9.2, and #904 ears.

Needs new:

- a fixed L5-20P cord part on the rear (`nema-l5-20p`);
- the WEBCARDLX network card as a module, in a bay;
- the two-digit ammeter as a display;
- every position from photographs (a front and a rear, both near straight-on),
  each checked as orthographic before it is measured, and stated as
  `photo-measured`;
- `metering-scope: input`, `outlet-switching: true`.

## 10. Order of work

1. This note, and the one-way items of section 12 settled.
2. Schema and lint: `metering-scope`, `outlet-switching` and the input keys
   (section 4), with the lint that ties `outlet-switching` to outlet states and
   `input-plug` to `PART_POWER`; `lines`; `through` widened (L133, L135).
3. The pilot brought up to it: `input-ac` and the structured input keys,
   `lines` on three breakers, `through` on 42 outlets. A minor version.
4. Export: the `feed_leg` rule, the descriptions, the comments; `mount-points`
   in `configs.json`.
5. Kit: state follows `for:` to the lamp; `states` and `readings` on rack
   entries and `readings` in the marks document; `zeroU` entries gain `swaps`,
   `fields` and `states`; the reading badge.
6. EVMA8365X, then PDUMV20HVNETLX, then PDUMH20NET.
7. Later, with #939 and #935: `pdu-button` slots on brackets and channels, the
   fit check, and L154 per attachment point.

## 11. Open questions

- **Outlet state home.** This note puts the vocabulary in the device and the
  value in the marks document and the rack entry. A live source (SNMP or the
  vendor API) writing the rack entry is the obvious next step and is not
  designed here.
- **Off colour.** The G4 off lamp is lit red. Whether a drawing of a PDU with
  no state set shows its lamps as shipped (unlit) or as a powered unit would
  (green) is a presentation choice; this note says unlit, the default for every
  lamp in the library.
- **Readings in a static export.** A badge carries a time; whether an export
  that has readings must state their source as well is open.
- **Tripp Lite namespace.** `eaton/` (the seller) or `tripplite/` (the series
  name on the unit and on the manuals).
- **Two PDUs a side.** Whether L154 moves to attachment points before #935, or
  waits for channels.
- **The G4 draw.** No held source gives the PDU own draw; until one does, the
  pilot and the EVMA8365X stay `specified: false`.

## 12. One-way items

Each is additive, and each becomes hard to change once a library device, an
export or a saved document uses it.

| item | where | why it is one-way |
|---|---|---|
| `metering-scope`, `outlet-switching` | `attrs.management` | attrs are flattened to `data-*` on every drawing; a rename moves every consumer |
| `input-ac` (prose), `input-plug`, `input-cord`, `input-phase`, `input-wiring`, `input-voltage-v`, `input-current-a`, `plug-rating-a`, `capacity-kw` | `attrs.power` | the same |
| the derived class names `basic`, `metered-input`, `metered-outlet`, `switched`, `managed` | `configs.json`, `devices.json`, DCIM comments | published for filtering |
| `lines`, and `through` naming a fixed breaker | placement keys | they change an imported outlet description and `feed_leg`; changing one is a major |
| the `feed_leg` rule (section 5.2) | DCIM export | a DCIM that imported a leg holds it |
| outlet states `on`, `off`, and their map to NetBox `enabled`, `disabled` | device `states`, rack file, marks documents | saved documents and share URLs carry the names |
| `readings` and the reading names `current-a`, `power-w`, `energy-kwh` | marks document (`additionalProperties: false` at v1, so a v1 validator refuses the key) and rack entries | saved documents carry them |
| `states` on rack items; `swaps`, `fields`, `states` on `zeroU` entries | rack file | saved rack files carry them |
| `pdu-button`, the `mounting:` block, `mount-points` | connectors registry, `configs.json` | #939 and #935 build on the names |
| outlet names as printed (already shipped by the pilot) | DCIM export | a renamed outlet is a new outlet to a DCIM |

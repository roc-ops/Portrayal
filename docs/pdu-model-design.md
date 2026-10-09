# Rack PDUs: capability, outlet state, input, phases and mounting

Status: decided 2026-10-08, not yet built. Issue #934. Extends
[power-outlets-design.md](power-outlets-design.md) (#806), which made a power
outlet an export, and builds on
[vertical-cable-managers-design.md](vertical-cable-managers-design.md) section 8
(#926, zero-U parts in the kit), the rack mounting note of #904 (ears and
kits) and the AC connectors of #933. The decisions are listed with their dates
in section 11.

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
| mounting | `mount: rack-side`, `ru: 39`, two `eaton/g4-mounting-button@1` on the rear | kept (section 6) |
| the C39 | `eaton/c39-outlet@1`, an Eaton part, exported as `eaton-c39` | kept |
| input | a fixed-cord part (`eaton/g4-cord-l21-30p@1`) exported as a `nema-l21-30p` power port | kept |
| input rating | `attrs.power`: `input-plug` and `input-voltage` as prose, and three numbers (`input-current-a`, `plug-rating-a`, `capacity-kw`) | given structured keys; `input-plug` becomes a slug (section 4) |

The pilot also left two findings that this note has to answer. Its capability
assessment reports `specified: false`, because the `power` profile asks for
`input-ac` and for a draw figure, and the pilot states neither (section 4). And
the EVMI2130X meters its input and branches and switches nothing, so none of
its outlets has an on/off state: the outlet state #934 asks for is a question
for the next three devices, not for the pilot (section 3).

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

The Tripp Lite series sells basic, metered, monitored and switched PDUs. The
PDUMV20HVNETLX meters its input and each bank and switches each outlet, which
is the G4 SW row; the PDUMH20NET meters its input only and switches each
outlet, which no G4 row describes.

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
- **The class is DERIVED** and published in `configs.json` and `devices.json`,
  so a catalogue can filter on it and no manifest can state a class that its
  two facts contradict. Every combination has a name:

| `metering-scope` | `outlet-switching: false` | `outlet-switching: true` |
|---|---|---|
| `none` | `basic` | `switched` |
| `input` | `metered-input` | `switched-metered-input` |
| `branch` | `metered-branch` | `switched-metered-branch` |
| `outlet` | `metered-outlet` | `managed` |

  The names are ours and say what is metered, so they part from vendor names
  where a vendor name is loose: the G4 "metered input" (MI) meters each branch
  too, so the EVMI2130X is `metered-branch`; the G4 "in-line metered" (IL) is
  `metered-input`; the G4 and Tripp Lite "switched" units are
  `switched-metered-branch` (the PDUMV20HVNETLX) and `switched-metered-input`
  (the PDUMH20NET); `managed` is the G4 MA, the EVMA8365X. The vendor name
  stays in the description and the provenance.
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
   to state name, beside its `swaps` and `fields`; a `zeroU` entry gains
   `swaps`, `fields` and `states` together, because a zero-U PDU has a network
   module to swap and section labels to fill as much as a rack item does. The
   loader normalises the map entry by entry, as `kit/marks.js fieldsOf`
   normalises a field map (the rack loader, `kit/rack/model.js readItem`, clones
   `fields` whole today and would not do for a state map). No kit/rack code
   applies a rack entry to a drawing yet (nothing there calls
   `shell.setFields`), so applying `states` from a rack entry is new code, and
   it is shared with the marks document path (section 3.2).
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
- The EVMI2130X has no outlet LED because it has no outlet switching: there is
  no state to show.
- A metered-outlet (MO) model has outlet LEDs but no switching, so its outlets
  declare no state vocabulary and what its lamps show is undecided. None of
  the four devices is MO; the first one settles it.

So **every PDU that can switch an outlet in scope has a lamp for it**, and the
state is drawn on the real lamp:

- **The lamp is its own part, placed beside the outlet with `for:`** naming
  the outlet: `eaton/g4-outlet-led@1` on the G4, a Tripp Lite lamp part on the
  other two. `for:` already means "this lamp annotates that", and the outlet
  stays the plain `std/c13-outlet@1` that `PART_OUTLET` exports. A composed
  outlet-with-lamp part was rejected: it would make a standard C13 an Eaton
  part, with a `PART_OUTLET` row of its own, to carry a lamp the outlet does
  not contain. (L76, the RJ45 census, is not a precedent here: it asks every
  Ethernet jack whether it has lamps and says nothing of power outlets.)
- **The state is addressed by the outlet, and follows `for:` to the lamp.** A
  user switches off A1, not the lamp beside it, and the rack file keys by the
  outlet path.
- **The colours are the device statement:** `states: [{name: on, color:
  '#22c55e'}, {name: off, color: '#ef4444'}]` on the G4 lamps, and on and an
  unlit off on the Tripp Lite lamps, unless a photograph shows otherwise. An
  `off` that is LIT (red) is new to the library.
- **A lamp with no state set draws unlit,** as every lamp in the library does,
  whatever the colour of its declared `off`.

**What the kit must change.** Following an outlet state to its lamp is not one
change; the state passes through four places that each key by one path.

1. **The 2D marks path** (`kit/marks.js apply`) puts `state-<name>` only on
   what a selector matches. Applying a state to an outlet path must also apply
   it to every element whose `data-for` names that path AND that declares a
   state vocabulary (`data-states`): a lamp. Other elements carry `data-for`
   too, a seated occupant (a `generic/c14-plug@1` in the outlet) and silkscreen
   marks among them, and the expansion leaves them alone; "an outlet with a
   bound lamp" below means exactly this test. A `for:` value is
   written as a placement id, and `data-for` carries it bare (a cross-view
   target gets a leading slash), so the binding reaches top-level placements
   only: an outlet inside a module bay would need its full path, and no PDU in
   scope has one.
2. **The 3D path** keys by path too: `viewer3d.js applyStatesNow` hands its map
   to `relief.js setNodeStates`, which keys each class by `data-path`, and
   re-renders only faces whose text contains a changed path. A lamp at its own
   path does not follow the outlet. The fix is one expansion, from an outlet
   path to the outlet and its `for:` lamps, run before both the 2D and the 3D
   application, so the two cannot disagree.
3. **The Explorer chips** (`kit/index.html chips`) treat `off` as clearing
   every state, and never set `state-off`. That was right while `off` meant
   unlit; with a declared off colour it cannot show the G4 red, and the cleared
   state is what `pushStates` sends to 3D. The chip must set `state-off` when
   the element declares a colour for it, and clear only when it does not.
   The chips also bypass `kit/marks.js`: `chips` writes `state-<name>` on the
   clicked element itself, `liveStates` reads the classes back off the 2D
   drawing, and `pushStates` hands them to `viewer.setStates`. So a chip on an
   outlet with bound lamps applies the same outlet-to-lamp expansion in 2D,
   writing the class on each lamp as well, and `liveStates` then picks up the
   lamp paths; without it a chip on A1 would light nothing, or 2D and 3D would
   disagree.
4. **`kit/states.js`** says `off` is the absence of a state (its `paints`
   answers true for `off` without asking). The comment and the shortcut become
   "unlit unless the device declares a colour for it", so a declared red off is
   reported as painting. `kit/marks.js` keeps skipping a custom lamp colour on
   `off`, and so does `kit/relief.js` where it writes custom lamp colours into
   the 3D textures, which is still right: a custom colour is for a lamp nobody
   documented.
5. **The rack file** carries `states` on items and `zeroU` entries, and the
   kit applies them through the same expansion (section 3.1, point 3).

**A switched outlet with no lamp** is not in scope, and the fallback is stated
so the first one does not invent a lamp: for an outlet that declares the state
vocabulary and has no lamp bound to it by `for:`, the base stylesheet dims the
outlet when it is `off` (as `absent` does, at a different opacity) and draws
`on` as shipped. An outlet with a lamp is never dimmed; its lamp says it.

**A dead outlet behind an open breaker** is the state a metered-input PDU does
have. The G4 breaker already declares `states: [on, off]` on its rocker. With
`through` naming the breaker (section 5), the kit can dim every outlet whose
breaker is `off`, which is the true picture of a tripped branch on any PDU,
switched or not. This needs `through` emitted into the drawing as a new
`data-through` attribute (it is not emitted today), and is an optional kit
step after the five above.

### 3.3 The state vocabulary

`on` and `off`. NetBox has a third instance status, `faulty`; no PDU in scope
documents an outlet fault state, so none is declared, and a later PDU that
documents one adds `fault` to its own vocabulary and maps it to `faulty`.

### 3.4 Load per outlet

Load is a reading, not a state: a number that changes, with a unit. It is not
printed on the hardware, so it is not a field; it is not a choice among names,
so it is not a state.

**Decision: `readings` on a rack entry,** beside `states`. The marks document
does not take it yet; whether and how it does is a later decision of its own.

```yaml
readings:
  source: SNMP poll of the PDU network module   # what the figures came from
  at: '2026-10-08T14:05:00Z'                    # when
  values:
    outlet-a1: {current-a: 1.8, power-w: 372}
    breaker-a: {current-a: 11.2}
    input: {current-a: 19.6}
```

- **`source` and `at` are required.** A reading without its source and its time
  is a number a reader cannot weigh, and every drawing or export that shows a
  reading states both.
- The `values` key is a part path, so the same map reads a branch (a breaker
  path) and the input (the cord) as well as an outlet.
- Three reading names to start: `current-a`, `power-w` and `energy-kwh`, each a
  number. They are the three quantities the G4 MA and MO models meter per
  outlet.
- **The device declares what can be read where,** from `metering-scope`:
  `input` admits readings on the input, `branch` on the breakers or banks too,
  `outlet` on every outlet. The kit refuses a reading where the PDU meters
  nothing, with a sentence, as it refuses a swap a slot does not accept.
- **The kit draws a reading as an annotation,** a small badge beside the part
  in the legend ink and not in the hardware palette, and the legend names the
  source and the time.
- A PDU display that shows a load (the Tripp Lite ammeter) can show the input
  reading; it is a display with `characters` (section 9), and the kit writes
  the rounded figure into it.

Rejected: a mark `label` (prose, not typed, and drawn only in the legend), and
a field (section 3.1).

## 4. Input rating

### 4.1 What the profile asks

`spec/schemas/profiles.yaml` gives the `power` profile two `attrs.power`
requirements: one of `input-dc` or `input-ac`, and one of the `power-max-w`
spellings, the draw of the unit itself, with the warning that the power it carries is
not a draw. The pilot states `input-plug`, `input-voltage`, `input-current-a`,
`plug-rating-a` and `capacity-kw`, which match neither, so `specified` is
false.

### 4.2 Decision

```yaml
attrs:
  power:
    input-ac: '200-240 V three-phase delta, 3W+PE, 40 A, 50/60 Hz'  # prose, as 80 devices write it
    input-plug: cs8365c            # the input power port type: a PART_POWER value
    input-cord: fixed              # fixed | detachable
    input-phase: three             # single | three
    input-wiring: delta            # wye | delta; absent when single-phase
    input-voltage-v: 208           # nominal, as a source states it; line to line when three-phase
    input-current-a: 40            # the rated input current, derated
    plug-rating-a: 50              # what the plug is rated for, when it differs
    capacity-kw: 14.4              # the load it can hand on; never a draw
```

- **`input-ac` stays the prose key.** Eighty devices write it, the profile
  reads it, and it holds what no number can (a range, a frequency). Every PDU
  states it; the pilot gains one.
- **`input-plug` changes from prose to a slug,** the type the input part
  exports: lint checks that it equals the `PART_POWER` value of the part the
  outlets are `fed-by`. The pilot prose (a NEMA L21-30P on a fixed 10 ft cord,
  10 AWG, five conductors) splits into `input-plug: nema-l21-30p`,
  `input-cord: fixed` and the provenance. Only the pilot writes `input-plug`
  today, so the change of meaning reaches one device.
- **`input-voltage` stays where it is and a PDU does not write it.** It is the
  prose voltage key of 40 devices and 31 component contracts, most of them
  boxes with an AC and a DC build, and it is not moved. A PDU states its
  voltage in `input-ac` (prose) and `input-voltage-v` (the number); the pilot
  moves its `input-voltage` prose into `input-ac`. Lint warns on a device of
  the `power` profile that states `input-voltage` beside `input-voltage-v`.
- **`input-current-a` and `plug-rating-a` are both kept,** because the SKU
  titles give the plug rating (30 A, 50 A) and the drawings the input rating
  (24 A, 40 A), and a reader who sees one figure will assume the other.
- **`capacity-kw` keeps its pilot spelling,** with the pilot
  `capacity-scope` sentence where a source qualifies it.
- **The draw requirement is not weakened.** A PDU with a network module does
  draw power; no held source states how much. The unstated draw stays the
  visible `specified` gap it is, and the G4 PDUs stay `specified: false` until
  a source gives the figure. Accepting `capacity-kw` in its place would be the
  carried-for-drawn confusion the profile warns against.

### 4.3 What DCIM can carry

Neither target has an input rating on a device type. A power port template
carries a type and draws in watts (`maximum_draw` and `allocated_draw` in both;
Nautobot adds `power_factor`), and the amperes, volts and phase are fields of a
power FEED, an instance. The export writes the rating into the input power
port `description` (NetBox keeps it; whether a Nautobot import keeps a power
port description is to be checked as #806 checked the outlet) and into the
device type comments, and leaves the draws and the power factor empty.

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
  parts. Widening it buys three things: the outlet description in both targets
  says which breaker protects it (as the 300CB08 outlets do), an outlet reaches
  its `lines` through its breaker instead of restating them, and the kit can
  dim the outlets of an open breaker (section 3.2). L133 then accepts a bay OR
  a placement of class `breaker`, and L135 (one position, one circuit) applies
  only when `through` names a bay, since a PDU breaker feeds fourteen outlets
  by design.
- **Sections stay regions.** A region is a drawing grouping and carries no
  power semantics; the export does not read it.
- **Without either key,** an outlet takes its lines from the input: single-phase
  input, no `feed_leg`; three-phase with no `lines` anywhere, no `feed_leg` and
  a warning that the wiring is unstated.

Stating `through` or `lines` is a minor version, as `fed-by` is, and changing
one is a major: both move an imported outlet description or `feed_leg`. The
EVMI2130X takes a minor bump when it states them.

## 6. Mounting a zero-U PDU

### 6.1 Today

`mount: rack-side`, `ru` the height it is sold for, and its buttons as
placements on the rear view. The kit places it with `zerou.place` at an
attachment point (`left`, `right`, or the four `left-front` to `right-rear` of a
four-post), fits it by `ru`, and declares no guides, so no cable lane runs
through it. This stays the mount until racks are products (#935).

### 6.2 The mounting interface: mount point, slot and pitch

#939 (a bracket the PDU hangs on) and #935 (a cabinet zero-U channel) both need
to check a PDU against what it hangs on, and #939 says whichever lands first
sets the vocabulary. This note sets it.

- **A mount point** is a feature of the hanging part that engages the frame:
  a button, a stud. On the PDU it is already a placement, so its position is
  data the drawing holds.
- **A slot** is the feature that takes it: a keyhole in a bracket or in a
  channel.
- **A mounting interface** names the pair, through the mechanism every
  connector already uses. A component `interface` says the part IS a receptacle
  that accepts parts naming that interface in `mates:`
  (`spec/schemas/component.schema.json`), so **the slot carries `interface`
  and the button carries `mates`**:
  - the keyhole part of a bracket (#939) or a channel (#935) declares
    `interface: pdu-button`;
  - `eaton/g4-mounting-button@1` declares `mates: pdu-button`;
  - `pdu-button` is an entry of `interfaces:` in
    `spec/schemas/connectors.yaml`, where every interface resolves, with a note
    citing the G4 guide (2.11): a shoulder button for keyhole slots 11.5 to
    12.5 wide in 1.5 to 2 mm sheet, or 14 wide in 3 mm. Whether it also needs a
    `standards.yaml` entry follows that file's own rules for an interface no
    standard governs, as `saf-d-grid` does. The Tripp Lite buttons are checked
    against it when that PDU is modelled.
- **Pitch** is the centre-to-centre distance of two mount points along the
  length, in millimetres: 1555.8 on both G4 PDUs (each drawing dimensions it),
  1556 on the PDUMV20HVNETLX. The pitch is NOT a new manifest key. It is
  derived from the button placements, which already sit 1555.8 apart on the
  EVMI2130X rear view, and published per configuration in `configs.json` as
  `mount-points: [{mates: pdu-button, at: <mm from the bottom>}, ...]`. A
  second statement of a number the drawing already holds is a number that can
  disagree with it.
- **Both sides gain a `mate` connection point,** because L11 asks for one
  beside every `interface` or `mates`: the button on its axis, the keyhole at
  the point the button seats.
- **The button gains `mates` and `mate`, which is a minor version of it, not a
  patch:** both are additive, and the part newly offers itself to every slot
  that presents `pdu-button`. No
  device that places it moves, and the devicelock check settles what the four
  devices that compose it take.
- **The fit check.** The refusal `fitsZeroU` does not make yet (#926 section 8)
  is: every mount point lands on a slot whose interface it mates, within a
  stated tolerance, or the placement is refused with a sentence naming the
  point that misses.

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

**Decision:** a lab rack-side placement names its point with the kit
attachment point names, and **the names alone decide.** A lab `rack` states
only `height-ru` and `rails-only` and no post count, and no key is added for
one:

- a rack-side `side` takes any of the six names, `left`, `right`,
  `left-front`, `left-rear`, `right-front` and `right-rear`, and `labs.json`
  publishes the name as written;
- L154 checks overlap per point, as `fitsZeroU` does, so `left-front` and
  `left-rear` never meet and two placements at `left` still stack;
- a lab that uses a two-post name (`left`) and a four-post name (`left-front`
  or `left-rear`) on the same side is a lint error, since the two describe
  different racks and their overlap cannot be judged;
- no library lab places anything with `side` today, so nothing migrates.

When channels arrive, both claim per channel. Duct sections that stack keep
stacking, since they share a point.

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
- `metering-scope: outlet`, `outlet-switching: true` (`managed`), so the
  outlets group declares `[on, off]` and the outlets admit readings.

Its gallery is mostly the shared CHASSIS_424 shots and close-ups of its
metered-input sibling; cite those as sibling evidence.

### 9.2 PDUMV20HVNETLX (Tripp Lite series switched, 0U)

Reuses: `std/c13-outlet@1`, `std/c19-outlet@1` (#933), `std/c20-inlet@1` as
the input power port (`iec-60320-c20`, already in `PART_POWER`), and common
RJ45, USB and lamp parts for the LX interface.

Needs new:

- its parts in the `eaton/` namespace (section 11), named for the series where
  a name would otherwise collide with a G4 part;
- a mounting button (1556 pitch, 134.01 from the top) with `mates:
  pdu-button` if it fits the interface, and the removable brackets of drawing
  details A to E as decor or parts;
- an outlet lamp part, `on` lit and `off` unlit;
- the digital load meter as a display with `characters`;
- the cord retention bracket at the inlet;
- two bank breakers, whose positions the submittal drawing does not show: a
  `gaps:` entry until the manual figures or a photograph place them;
- `input-cord: detachable`, `input-plug: iec-60320-c20` with the L6-20P cord
  in the provenance and prose, `metering-scope: branch`, `outlet-switching:
  true` (`switched-metered-branch`).

### 9.3 PDUMH20NET (Tripp Lite series switched, 1U)

Reuses: `std/nema-5-20r@1` (#933), the D-sub receptacle for the DB9 config
port, the outlet lamp and mounting vocabulary of 9.2, and #904 ears.

Needs new:

- a fixed L5-20P cord part on the rear (`nema-l5-20p`), in `eaton/`;
- the WEBCARDLX network card as a module, in a bay;
- the two-digit ammeter as a display;
- every position from photographs (a front and a rear, both near straight-on),
  each checked as orthographic before it is measured, and stated as
  `photo-measured`;
- `metering-scope: input`, `outlet-switching: true`
  (`switched-metered-input`).

## 10. Order of work

1. This note.
2. Schema and lint: `metering-scope`, `outlet-switching` and the input keys
   (section 4), with the lint that ties `outlet-switching` to outlet states,
   `input-plug` to `PART_POWER`, and warns on `input-voltage` beside
   `input-voltage-v`; `lines`; `through` widened (L133, L135). `lines` is a
   placement key, so devicelock must fingerprint it: it joins
   `PLACEMENT_ADDRESSING` beside `fed-by` and `through`, and
   `test_lock_sees_placement_keys` holds the sets to the schema.
3. The pilot brought up to it: `input-ac`, the structured input keys,
   `input-plug` as a slug, `lines` on three breakers, `through` on 42 outlets.
   A minor version.
4. Export: the `feed_leg` rule, the descriptions, the comments, the derived
   class; `mount-points` in `configs.json`.
5. Kit: the five outlet-state changes of section 3.2; `states` and `readings`
   on rack entries; `zeroU` entries gain `swaps`, `fields` and `states`; the
   reading badge with its source and time.
6. Lab format and lint: attachment points in rack-side lab placements and
   `labs.json`, and L154 per point.
7. EVMA8365X, then PDUMV20HVNETLX, then PDUMH20NET.
8. With #939 and #935: `pdu-button` in the connectors registry, slots on
   brackets and channels, `mates` on the buttons, and the fit check.
9. Later and separately: whether the marks document takes `readings`.

## 11. Decisions

Each was decided 2026-10-08, as this note recommended.

1. **Outlet state:** the vocabulary is the device statement and the value lives
   in documents; `on` and `off` map to NetBox `enabled` and `disabled`.
2. **A lamp with no state set draws unlit.**
3. **`readings` goes in the rack file first;** the marks document is a later,
   separate decision.
4. **An export that shows readings states their source and time.**
5. **`through` widens to fixed breakers, with a `lines` key;** the EVMI2130X
   takes a minor bump.
6. **The mounting vocabulary is mount point, slot and pitch,** with the pitch
   derived and published as `mount-points` (the mechanism is section 6.2).
7. **L154 moves to attachment points now,** and within that the
   attachment-point names alone decide: all six are accepted, a side may not
   mix two-post and four-post names, and no post-count key is added to a lab
   (section 6.4).
8. **The Tripp Lite series models and their parts go under `eaton/`.**
9. **The G4 PDUs stay `specified: false`** until a source gives their draw.
10. **The eight class names of section 2.2 are accepted as tabled,** including
    where they part from vendor names (the EVMI2130X is `metered-branch`).

Still open:

- whether a Nautobot import keeps a power port `description` (section 4.3);
- the pairing of the EVMA8365X breakers onto L1, L2 and L3 (section 9.1);
- a live source (SNMP or the vendor API) writing a rack entry `states` and
  `readings`, which is the obvious next step and is not designed here.

## 12. One-way items

Each is additive, and each becomes hard to change once a library device, an
export or a saved document uses it.

| item | where | why it is one-way |
|---|---|---|
| `metering-scope` (`none`, `input`, `branch`, `outlet`), `outlet-switching` | `attrs.management` | attrs are flattened to `data-*` on every drawing; a rename moves every consumer |
| the eight class names: `basic`, `switched`, `metered-input`, `switched-metered-input`, `metered-branch`, `switched-metered-branch`, `metered-outlet`, `managed` | `configs.json`, `devices.json`, DCIM comments | published for filtering |
| `input-ac` on a PDU, `input-cord`, `input-phase`, `input-wiring`, `input-voltage-v`, `input-current-a`, `plug-rating-a`, `capacity-kw` | `attrs.power` | flattened, as above |
| `input-plug` changing from prose to a slug | `attrs.power` | a consumer that read the prose reads a slug |
| `lines`, and `through` naming a fixed breaker | placement keys | they change an imported outlet description and `feed_leg`; changing one is a major |
| `data-through` | a new drawing attribute | consumers of the drawing read it |
| the `feed_leg` rule (section 5.2) | DCIM export | a DCIM that imported a leg holds it |
| outlet states `on`, `off`, and their map to NetBox `enabled`, `disabled` | device `states`, rack file, marks documents | saved documents and share URLs carry the names |
| the Explorer meaning of `off`: a state that can be lit, not the absence of one | `kit/index.html`, `kit/states.js` | a saved state set as `off` reads differently |
| `readings`, its `source`, `at` and `values`, and the reading names `current-a`, `power-w`, `energy-kwh` | rack file entries | saved rack files carry them |
| a share-URL codec slot for readings, if the marks document takes them | `kit/marks.js` encode and decode | a slot, once given out, is held by every link written with it |
| `states` on rack items; `swaps`, `fields`, `states` on `zeroU` entries | rack file | saved rack files carry them |
| the six rack-side `side` names `left`, `right`, `left-front`, `left-rear`, `right-front`, `right-rear`, and the rule that a side may not mix two-post and four-post names | lab placements, published in `labs.json` | saved labs and the published index carry them |
| `pdu-button` as an interface, and `mount-points` | connectors registry, `configs.json` | #939 and #935 build on the names |
| outlet names as printed (already shipped by the pilot) | DCIM export | a renamed outlet is a new outlet to a DCIM |

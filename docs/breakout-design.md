# Breakout: a structured field, and who states it

Status: proposal. Nothing here is built, and nothing in the schemas, the library
or the exporters changes with this note. It answers #536 ("a structured breakout
field, so that supports-breakout can be filtered without hand-seeding") and
records one ruling, decided 2026-10-18: "both netbox and nautobot should show
this, but typically would be added by the NOS for disaggregated devices".

So: breakout is shown in both the NetBox and the Nautobot exports, and on a
white-box device it is usually stated by the NOS, not by the hardware. That
agrees with #512's rescope ("breakout belongs to the NOS layer",
`spec/DESIGN.md`, Architecture, layer 2), and the library already has a NOS-layer
home for it.

Every count below was taken with `git grep` or `grep` on `main` at 60b08a88f.
#536's counts are from 2026-09-23; where they differ, both are given.

## What exists

### The NOS-layer rule

A listing's `interfaces:` rule may carry `breakout: {modes, child-name}`
(`spec/schemas/listing.schema.json`, `interfaces[].breakout`; the same shape is
in `spec/schemas/device.schema.json`, top-level `interfaces[].breakout`, for the
maker's own NOS on its own box). `modes` is a list of strings and `child-name` a
pattern with `{i}` for the child index. Nothing checks the spelling of a mode:
the schema says `string`, and `lint.py` mentions breakout only in a comment.
Every mode on `main` happens to be written `<count>x<speed>` (`4x25g`, `1x400g`).

Which ports is already said by the rule that carries it: `physical` with `{n}`
over `range`, or one rule per port. `sonic/dcs500` writes sixteen single-port
rules (even ports 0 to 30); `sonic/s9301-32db` writes two ranges with different
modes (`0-23` and `24-31`). A port with no `breakout` is a port the NOS does not
break out. No separate `ports` list is needed.

`modes` includes the unbroken modes. SONiC's `s9300-32d` lists `1x400g` and
`1x100g` beside `4x100g` and `8x50g`, because the NOS's platform file lists every
mode a port can be put in. "Supports breakout" is therefore "some mode has a
count above 1", not "has a `breakout` rule".

`docs/listing-a-nos.md`, "What the NOS calls each port", is the written contract.
`interfaces` on `device.schema.json` explicitly says "Not breakout: breakout is
a MODE a port is configured into and stays a description on one interface".

### What the export writes

`dcim_export.py` `listing_names` returns each physical id's NOS name and its
breakout rule. `breakout_note(breakout, n)` turns the rule into prose
(`Breakout: 1x100g, 2x50g, 4x10g, 4x25g`, plus `; children swp7s{i}` when a
`child-name` is stated), cut to the 200 characters both DCIMs allow
(`fit`). The port-building loop sets it as the interface's `description`
(`dcim_export.py`, `if breakout: iface["description"] = breakout_note(...)`).
The device type lists the ports the metal has; the children a breakout makes are
a device's configuration, so they are not exported as interfaces.

The two targets get the same text. On `main`, 23 NetBox files and 23 Nautobot
files under `library/exports/*/device-types/` carry a `Breakout:` interface
description (`grep -rl -E "description: .*Breakout( capable|:)"`):

| vendor | NetBox | Nautobot |
|---|---|---|
| SONiC | 16 | 16 |
| Arrcus | 4 | 4 |
| DriveNets | 3 | 3 |

No other vendor's export carries one. Fifteen listings carry a `breakout:` rule
(`git grep -n "breakout:" -- library`): `arrcus/as7726-32x`, `drivenets/cor550`,
`drivenets/s9700-53dx`, and under `sonic/`: `dcs500`, `ds2000`, `ds3000`,
`s7801-54xs`, `s8901-54xc`, `s9110-32x`, `s9300-32d`, `s9301-32d`, `s9301-32db`,
`s9311-64d`, `s9321-64e`, `s9321-64eo`. A device's own `interfaces:` carries none.

Separately, a device's `attrs` text reaches both DCIMs inside the device type's
`comments` (`features.breakout: ...` in the exports of the UfiSpace, IP Infusion,
Arrcus, DriveNets and Celestica types), and a component's `breakout` attr reaches
the module type's comments (Cisco `A9K-4X100GE` and Nokia `LBNT-A`, both
targets). That is prose in a comment, not on a port, and not the NOS's.

### The free-text keys on the hardware

By `git grep` over `library/devices` and `library/components`, with the
`layout.yaml` copies of an Edgecore device's `attrs` not counted twice:

- **`breakout`**: 11 devices, up from #536's 5. The five in #536 are still there
  (`ufispace/s9600-28dx`, `s9600-32x`, `s9600-64x`, `s9700-23d`, `s9700-53dx`);
  six Celestica boxes were added since (`ds3000`, `ds3001`, `ds4000`, `ds4001`,
  `ds4100`, `ds5000`). Of the eleven, **three are lane sharing, not breakout**
  (the three S9600s: SFP28 ports that share QSFP28 port 0's lanes). Two components
  carry `breakout` too (`cisco/a9k-4x100ge`: `16 x 10GE`; `nokia/lbnt-a`).
  `ufispace/s9600-32x` also has a `breakout:` key at line 842 that is a
  configuration named `breakout`, not a fact.
- **`port-modes-*` that name breakout**: six devices, as in #536 (`port-modes-qsfp28`
  on `edgecore/as7326-56x`, `as7726-32x`, `cor550`, `dcs500`; `port-modes-qsfpdd`
  on `cor580`, `dcs510`), plus `port-modes-osfp224` "with breakouts" on
  `celestica/ds6000` and `ds6001` (new).
- **Other spellings that carry a mode**: `juniper/mx204` `rate-selectability`
  (`4x10GbE`); `edgecore/csr310` `optics-qsfp28` ("4x 10/25 GbE or 2x 50 GbE per
  port"); `4x25G breakout by cable` inside `celestica/ds3000` `optics-qsfp28`.
  #536 also lists `dcs201`, `dcs202`, `s9710-76d` and the `port-leds-qsfp28` of
  `agr110`, `agr130`; those were not re-read for this note.
- **Lane sharing, a different fact**: `sfp28-sharing` on `ufispace/s9600-56dx`,
  `s9610-46dx` and `s9610-48dx`, with the three `breakout` keys above.
  `zr-ports`, `op2-option-ports` and `op2-disabled-ports` on `s9610-36d`,
  `s9700-23d` and `s9710-76d` are port-set qualifiers, not modes.

**Speed vocabulary.** `spec/schemas/speeds.yaml` is the closed set (`10m ... 1.6t`,
ascending). Every mode on `main` is `<count>x` plus a member of that set. PR #1165
(open) adds `speeds` / `data-speeds` for a multi-rate cage's native rates, and says
in its own text that those are "native rates only, no breakout". This note changes
none of its files and follows its vocabulary.

### Where the NOS layer is silent but the hardware speaks

Listings that exist, name ports, and carry no breakout though the hardware's
`attrs` state modes: `sonic/as7726-32x` (hardware: `1x 100G, 2x 50G, 4x 25G, 1x
40G, 4x 10G`; the Arrcus listing for the same box states them), `sonic/dcs510`
(hardware: `4x 100G / 4x 25G`). So the same box shows breakout under Arrcus and
not under SONiC.

## What the two DCIMs can hold

Read at `netbox-community/netbox` `4b034ea21986` (`main`),
`netbox/dcim/models/device_component_templates.py`, and `nautobot/nautobot`
`1efddad00a00` (`develop`), `nautobot/dcim/models/device_component_templates.py`.
Both were read through a page-fetching tool that summarises rather than as raw
files, so field names and types are firm and line numbers are not given.

- **NetBox `InterfaceTemplate`**: `name`, `label`, `type`, `enabled`, `mgmt_only`,
  `description` (inherited, 200 characters), `channels` (the number of channels the
  interface is channelized into), `channel_id`, `parent`, `bridge`, `poe_mode`,
  `poe_type`, `rf_role`. Nothing is named breakout. `parent` and `channels` are
  the nearest structured fields: they describe a *configured* channelized
  interface and its children, which is what the exporter chose not to emit (a
  type that lists 96 children the faceplate has not got).
- **Nautobot `InterfaceTemplate`**: `name`, `label` ("Physical label"),
  `description`, `type`, `port_type`, `mgmt_only`, `speed`, `duplex`. No
  breakout, parent or channel field (`parent` is a property, not a stored one).

So neither DCIM has a field for "this port can break out into 4x25G". The
interface `description` is the only per-port place both have, and it is already
what the export uses. A structured upstream field does not exist to be targeted;
nothing in this design depends on one appearing.

**After an import** a user sees, on each interface of the device type, the text
`Breakout: 1x100g, 2x50g, 4x10g, 4x25g` in its description column, in NetBox and
in Nautobot alike. They can read it per port. Searching or filtering on it is a
text match on that column; whether each UI offers a description filter was not
checked here.

## Where breakout is stated, and by whom

| who | file | its source | what the export writes |
|---|---|---|---|
| **A NOS vendor's listing** (usual; decided 2026-10-18) | `library/devices/<nos>/<box>/listing.yaml`, `interfaces[].breakout` | the NOS's own platform file or documentation, cited in the listing's `source` (the SONiC listings cite `platform.json` in `sonic-net/sonic-buildimage` at a named commit) | `Breakout: ...` on each interface, in the NetBox and the Nautobot document of that listing's type. 23 files each today |
| **The maker's own NOS on its own box** | the device's own `interfaces:` (`device.schema.json`) | the maker's documentation | the same description on the hardware's own device type. No device uses `breakout` here today. And because `name` is required, a breakout statement needs a NOS name for every port it covers |
| **The maker's datasheet, no NOS listing** | the device's `attrs`, free text (`features.breakout`, `port-modes-*`, and the other spellings above) | the datasheet, cited in `provenance` | nothing on a port. The prose lands in the device type's `comments` only |

The third row is the gap #536 describes. The first row is where the ruling puts
the answer, and it is already structured.

## The shape

### 1. The existing rule is the structured field

`interfaces[].breakout.modes` with `child-name` **is** the structured field #536
asks for. Its `modes` are #536's `modes`. A second field on port groups would
state the same fact in two places (the thing `listing_names` was rewritten to
stop, #63 and #56), and the drawing is the wrong home: #512's rescope decided
there is no `data-breakout`.

### 2. "Which ports" stays the `interfaces` rule

#536's `ports` list (`["port-0", "port-1"]`, omitted when every port breaks out)
is what `physical` and `range` already say, with the physical ids the drawing
uses. A rule per run of ports with the same modes is enough
(`sonic/s9301-32db`). **Not adopted:** a `ports` list, because it would let a rule
name one set of ports twice.

### 3. Modes are `<count>x<speed>`, checked against `speeds.yaml`

Write a mode as `<count>x<speed>` with `<speed>` a member of
`spec/schemas/speeds.yaml`, so `4x25g`, never `4 x 25GE` or `4x25`. Today nothing
enforces it. A lint rule would (see the first slice); it rejects no mode on
`main`. `modes` keeps the unbroken modes, as the NOS lists them.

### 4. Lane sharing is not breakout and stays apart

The S9600 SFP28 cages that share QSFP28 port 0's lanes are a constraint between
two cages: using one disables the other. It has no mode and no child. It stays in
prose under a key that names it (`sfp28-sharing`, which three boxes already use).
The three S9600s that call it `breakout` should be renamed. No structured field
is proposed for it. The ordered lanes are a second piece of data that nothing
reads yet.

### 5. A maker's statement with no NOS listing

Two ways, neither is chosen yet:

- **A.** Let the device's own `interfaces:` rule omit `name` (the export already
  names a port by its faceplate id "where no rule does"), so a datasheet's
  `breakout` is a rule on the hardware: `{physical: 'port-{n}', range: '1-32',
  breakout: {modes: [4x25g, 4x10g]}}`. The export then writes the same description
  as a listing would. One schema relaxation, no new key.
- **B.** Add nothing. The hardware keeps the prose; a box gets structured breakout
  when a NOS lists it.

**Proposal: A, later.** It removes the third row's gap with the shape that exists
for the first two. B alone leaves a Celestica DS4100 (hardware states "8 x 100GbE,
4 x 200GbE or 2 x 400GbE per 800G port", no NOS listing) invisible to a filter.

## What becomes of the free-text keys

**Kept as the source, not moved.** They are transcribed from a datasheet with
provenance, and the NOS statement is a second, independent source (a platform
file) that may disagree; two statements that agree are a cross-check. A key moves
only when it is not breakout:

- `breakout` on `s9600-28dx`, `s9600-32x`, `s9600-64x` becomes `sfp28-sharing`
  (lane sharing). A key rename in `attrs`; the exports' comments change for those
  boxes' types.
- The rest stay. Where a listing exists, the listing states the modes and the
  hardware's prose is the datasheet's cross-check; the two should agree and a
  test could compare them (not proposed for the first slice).

The prose keys are not harvested into a canonical fact in `facts`/the comparison
layer here: #112 asked for that and warned that `port-modes-*` already belongs to
L40 ("this rule harvests; it does not design"). A canonical comparison fact for
breakout would read the structured rule, never the prose.

## Recommendation (a proposal, to accept at merge)

1. **Breakout is the listing's `interfaces[].breakout`**, modes `<count>x<speed>`
   in the speed vocabulary, ports by the rule's `physical` and `range`. No new
   published key and no `ports` list.
2. **The exports keep the interface description in both targets**, unchanged.
   Neither DCIM has a structured field.
3. **Lane sharing stays prose, named `sfp28-sharing`.**
4. **The free-text `attrs` keys stay as the source**, except the three S9600
   `breakout` keys, renamed.
5. **A maker-stated breakout with no listing is slice 2** (option A above), after
   the choice is made (open question 1).

**One-way when built:**

- Option A relaxes `name` to optional in `device.schema.json` `interfaces[]`. A key
  made optional is published; consumers may then see a rule with no name, and
  tightening it again would break whoever wrote one.
- Any change to the description text (adding the port range, say) re-exports every
  file above and changes what an importing user has stored. Not proposed; listed
  because it is the cheap-looking change that is not cheap.
- Adding a mode to or removing one from an existing listing changes a published
  export; the lock (`listing.lock.json`) decides the bump.
- The lint rule for mode spelling is not one-way: it can be loosened.
- Renaming `breakout` to `sfp28-sharing` changes three devices' `attrs` and so
  their exports' comments and the lock.

## First build slice

Not built by this note. Small, and none of it one-way:

- **Lint**: a new rule that every `interfaces[].breakout.modes` entry (in a listing
  and in a device) matches `^[1-9][0-9]*x<speed>$` with `<speed>` in
  `speeds.yaml`. Files: `spec/tools/portrayal/lint.py`, `docs/lint-rules.md`, the
  recorded lint-catalogue fixture, and a test `spec/tests/test_breakout_modes.py`
  (a good mode passes; `4 x 25GE`, `4x25`, `0x25g` and an unknown speed each fail;
  every mode on `main` passes). Read the speed set from `speeds.yaml`, as L110
  does; this waits on or rebases over #1165, which edits `lint.py` and
  `speeds.yaml`.
- **Two listings that are silent**: `sonic/as7726-32x` and `sonic/dcs510` gain
  `breakout` for their QSFP ports. Source for each: the platform's own file in
  `sonic-net/sonic-buildimage`, at a commit named in the listing's `source`,
  the way the existing SONiC listings cite it. It has to be read, not copied from
  the hardware's prose; the hardware's `port-modes-qsfp28` / `port-modes-qsfpdd`
  is the cross-check. Each listing needs its lock bump and an export regeneration
  (`dcim_export.py --device <id>`), and the new descriptions appear in the
  NetBox and Nautobot files of that type.
- **Rename** the three S9600 `breakout` keys to `sfp28-sharing`, with their
  provenance unchanged.
- **Test**: `Breakout:` appears in the exported interface description of both
  targets for the same listing (the existing `test_dcim_listings.py` covers only
  the note function).
- Changelog fragment, devicelock, preflight.

## Open questions

1. **Is a hardware-only breakout statement worth a field (option A), or does the
   filter only need NOS-stated breakout (option B)?** The ruling says "typically"
   the NOS. A: removes the gap for boxes with no NOS listing, costs one schema
   relaxation. B: nothing to build, and the Celestica DS3000 to DS5000 and the
   S9700s stay prose-only.
2. **What does "supports breakout" mean in a filter?** Any mode with a count above
   1 (this note's reading), or any `breakout` rule at all? Changes: whether a port
   listing only `1x100g, 1x40g` (`sonic/ds2000`, `ds3000`) counts. It does not
   break out, yet it has a rule today.
3. **May the three S9600 `breakout` keys be renamed to `sfp28-sharing`?** Changes
   three devices' exports' comments and their lock bump.
4. **Should the description say which ports?** Today each interface says its own
   modes only. Adding more changes 46 files and every importing user's stored
   text (one-way above).
5. **Should the two sources be compared by a test** (a listing's modes against the
   hardware's prose)? Needs the prose parsed, which #112 rules out for now. Changes
   whether a disagreement is ever caught.
6. **Does a canonical comparison fact for breakout (#112) read only the structured
   rule?** This note assumes yes; it changes whether devices without a listing
   appear in the comparison at all.

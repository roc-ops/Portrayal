# Power cords: what #1045 still wants

Status: **proposed, 2026-10-18, to be accepted at merge. Nothing here is built.** A
design note only: no code, no library part, no schema, no export changes with it.
The start of this note was decided 2026-10-18. Every recommendation below is a
**proposal**, and every choice that would be one-way when built says so.

This is not a second landing note. Most of #1045 is built, and the rules for it are in
[cable-ends-design.md](cable-ends-design.md) (where a cable lands, plug and lug
derivation, the `power` and `ground` media, what is warned and what is refused).
DC feeds are designed in [dc-power-design.md](dc-power-design.md), whose step 1 is
merged. Neither is repeated here; this note points to them. It designs what #1045
still wants and nothing on `main` designs yet. Facts about the kit are read from
`main` at 713499fab, not from the status lines of those notes.

## 1. What is open

Section 2 audits #1045 against `main`. Four things come out of it that no note
designs:

| open | section |
|---|---|
| A cord is one `power` media with no named plugs. A type cannot say "a C13 and a C14", no saved key names a type, a stock length is one list for every media, and a cord's bill-of-materials line cannot be ordered from. | 4 |
| The DCIM cables file writes no power row a person can use: an outlet's path (`outlet-9`) is not the name its type file prints (`9`), and the cable type column is blank for `power`. | 5 |
| Nothing says which feed a supply is on, so nothing can check that a device with two supplies is on both. | 6 |
| A cable has two ends inside the rack. A branch circuit, or the far end of a fixed input cord, has no end to land on. | 7 |

A load's draw against its breaker (section 8) is the last item of #1045, and is not
needed for cords.

## 2. The audit

Read from the code on `main`, not from status lines. "Done" names the pull request
or commit and the file that shows it. #1045 is the issue and its comment of
2026-10-12; "7.n" and "8.n" are the items of sections 7 and 8 of
[cable-ends-design.md](cable-ends-design.md).

### 2.1 #1045: the eight "Wanted" and the four "Added" items

| # | item | state | evidence |
|---|---|---|---|
| W1 | A design note: a connector slot of a power class as an end, a cord as two plugs, a `power` media, zero-U ends, DC feeds, A and B | **done**: the note settles the first three and lists zero-U, A and B as later steps (7.1, 7.4); DC is in dc-power-design.md. A and B are designed here (section 6) | `docs/cable-ends-design.md`, PR #1047 (4360f8efa) |
| W2 | One exported predicate for "a cable can land here" | **done** | `cableLandsOn`, `kit/rack/cable-rules.js:345`; kit 0.30.0, PR #1047 (e1f5b617d) |
| W3 | `power` media, a power family for the mismatch check, plug rows, diameters, colours, end allowance | **done** | `MEDIA` and `mediaKind` (`kit/rack/cable-rules.js:225`), `DIAMETERS`, `PLUG_REACH`, `END_ALLOWANCE_BY_MEDIA` (`kit/rack/route.js:1125, 1245, 2803`); the `ground` figures are estimates and say so |
| W4 | A page uses the kit's predicate | **partly**: the kit half is done (`ctx.drawnAt`, `freePorts`, `cableEndPaths`); the page is in another repository and was not read | `kit/README.md` "New in 0.30.0" |
| W5 | DCIM: outlet path to printed name; a power cable type; proven against NetBox and Nautobot imports | **partly**: a power cable whose two ends resolve is written, with a blank type; `CABLE_TYPE` has no `power` row; no path-to-name mapping for an outlet; no import was run | `kit/rack/dcim-rules.js:367-373, 497-498`; `resolveEnd` `:206-218` looks up the path itself |
| W6 | Library: interfaces for 5-15R, 5-20R, C39; `mates` as one or a list; 5-15P and 5-20P cord ends; `interface` on the outlets that lack one | **partly**: `nema-5-20r` and `eaton-c39` present and landable, `mates` a list, both cord ends exist (as `-cord`, not `-plug`); `nema-5-15r` is registered and no part presents it; `amphenol-ns/output-terminal` and the three input parts (`input-feed-studs`, `input-stud-pair`, `input-feed-busbar`) state no `interface` (`output-p40` states `p40`) | PR #1050; `spec/schemas/connectors.yaml:60-62`; `library/components/generic/nema-5-15p-cord/v1/contract.yaml`, `nema-5-20p-cord` |
| W7 | A zero-U part as a cable end | **done** | kit 0.38.0 and 0.44.0; `kit/README.md` "New in 0.38.0", `zeroUEnds` in `kit/rack/ports.js` |
| W8 | Cord types with two named ends, stock lengths, bill-of-materials lines | **not started** | `power-c13` and `power-c19` name a `conductor` and no plug (`spec/schemas/cable-types.yaml:294-315`); `cable_types_index.py` refuses an unknown key; `STOCK_M` is one list (`kit/rack/route.js:1191`); `cableBomRows` keys a line on media, length and connector family (`kit/rack/export-data.js:1274-1288`) |
| A9 | Lug seats on the Amphenol output terminals and input studs; DC wire and ground wire cable types | **not started** | `output-terminal` and the three input parts state no `interface` (no lug seat); `cable-types.yaml` has two `power` types and no DC or ground type; `cable_types_index.py` `FAMILIES` has no ground |
| A10 | The DC terminal as a part on `psu-132-dc`, `pws-601s-1r`, `lpwr-f` | **not started** | none of the three states an `interface` |
| A11 | DCIM: each end publishes the name its type file prints | **partly**: `configs[].names` exists for the paths of `states` only (a switchable outlet) and only `configFacts` reads it; the cables file does not | `render.py` `config_names` (`:4922`); `docs/format-stability.md:300`; `kit/rack/catalog.js:77` |
| A12 | Later: side and bottom views as an end's view; a load's draw against its breaker | **not started** | a side-view end is still refused (`kit/rack/cable-rules.js:498`); a breaker has a `rating`, nothing records a draw |

### 2.2 Section 7 of cable-ends-design.md: eight later steps

| # | step | state | evidence |
|---|---|---|---|
| 7.1 | A zero-U part as an end | **done** | kit 0.38.0, 0.44.0 (as W7). The status line of that note does not say so. |
| 7.2 | Ends on side, top and bottom views | **not started** | `kit/rack/cable-rules.js:498` |
| 7.3 | A feed end outside the rack | **not started** | no kit file reads a feed; `dcim-rules.js` `MEETS` has no `dcim.powerfeed` |
| 7.4 | A and B feeds, and a check | **not started**: `side` is in the component schema from PR #1090, and nothing reads it | `spec/schemas/component.schema.json`; no `side` in `kit/rack` |
| 7.5 | Named cord types with two ends | **not started** | as W8 |
| 7.6 | Load | **not started** | as A12 |
| 7.7 | Two wires on two screws | **not started**: `dc-power-design.md` 5.4 takes the port as the end, so the screws are not a separate step | |
| 7.8 | The DCIM cables file | **partly** | as W5 |

### 2.3 Section 8 of cable-ends-design.md: nine things the library owes

| # | item | state | evidence |
|---|---|---|---|
| 8.1 | Interfaces to register, each with the part that presents it | **partly**: `nema-5-20r` and `eaton-c39` done; `nema-5-15r` registered, presented by nothing; no lug seat on `output-terminal` or the three input parts (`output-p40` presents `p40`) | PR #1050 |
| 8.2 | `mates` as one interface or a list, and every reader | **done** | PR #1050; `manifest.mates_of`; `fitsHang` in `kit/rack/zero-u.js` |
| 8.3 | Cord ends `nema-5-15p` and a slot-seating 5-20P, class `port` | **done**, named `generic/nema-5-15p-cord@1` and `generic/nema-5-20p-cord@1`, each with `rating-a` | PR #1050 |
| 8.4 | `attrs.outlet` and `attrs.input` on every part that hands power on or takes it | **partly**: the four AC outlets state `outlet` and `media: ac`; `amphenol-ns/output-p40` and `output-terminal` state neither | their contracts |
| 8.5 | Cable types: NEMA cords, DC feed pairs, ground wires | **not started** | `cable-types.yaml` |
| 8.6 | Three supplies compose a part that presents a lug or plug interface | **not started** | as A10 |
| 8.7 | Nested slots of a part fixed to a chassis | **not started**: `cage_entries` publishes one entry for each placement of the device (`render.py:5613`), and no commit names the nested case. Not run on a build. | |
| 8.8 | The power and ground ends still refused | **partly**: the `std/nema-5-20r` (16) and `eaton/c39-outlet` (36) placements now land; every other part in the list is unchanged | PR #1050 |
| 8.9 | The name each end prints, published beside its path | **partly** | as A11 |

### 2.4 Count

| | done | partly | not started |
|---|---|---|---|
| #1045, 12 items | 4 (W1, W2, W3, W7) | 4 (W4, W5, W6, A11) | 4 (W8, A9, A10, A12) |
| section 7, 8 steps | 1 | 1 | 6 |
| section 8, 9 items | 2 | 4 | 3 |
| **29 rows** | **7** | **9** | **13** |

Many rows are one fact counted again (W8 is 7.5, A12 holds 7.2 and 7.6). The note
designs the open ones once, in sections 4 to 8.

### 2.5 Pull requests open beside this note

Read, and nothing of theirs is touched here.

- **#1159** (NetBox cable bundles) changes `kit/rack/dcim-rules.js` and
  `kit/rack/export-data.js`: the cables file becomes `5-cables.csv` and gains a
  `bundle` column behind `dcim.netbox`. The first slice of section 10 edits the
  same function (`cableImportRows`), so it starts after #1159 merges.
- **#1158** (the FS-PDUBK bracket a zero-U PDU hangs on) changes the library and
  `rack-pdu.mjs`, no kit file. A cord to an outlet of a PDU on such brackets
  already ends as W7 describes; nothing in this note depends on it.

## 3. Facts the design rests on

Read in the code, and cited again where used.

- **A cable carries `media` and no type.** `withCable` writes `media` and nothing
  that names a type (`kit/rack/cable-rules.js:77-81`), the rack schema's `cable`
  has no `type` property, and the command takes no `type`
  (`kit/rack/commands.js:1364`). The kit does read `cable.type` when a file has one
  (`cableTypeOf`, `kit/rack/cable-types.js:44`), the loader keeps it, and
  `docs/rack-file-v4-design.md` 14.6 says "nothing in the kit writes that key yet".
- **A cable type is a row of `spec/schemas/cable-types.yaml`**, compiled to
  `cable-types.json`. `cable_types_index.py` refuses a key it does not know, and the
  file says a removed or renamed key raises `format` and a new type is a minor.
- **A cord's end is derived from the slot** (`endPlug`, `cable-rules.js:413`), and
  a slot that takes two plugs pairs with the plug at the other end (`pairedWith`).
  The plug is stated on an end only where a slot takes several.
- **The bill-of-materials line of a cable** is keyed on media, length and the
  connector family of its two ends (`cableBomRows`), so a C13-to-C14 cord and a
  5-15P-to-C13 cord are one line, "Power cable, power at both ends".
- **The DCIM cables file** resolves an end by looking its path up in the device's
  or the module's type file (`resolveEnd`, `kit/rack/dcim-rules.js:206`). Its own
  comment says a name is never built by convention alone.
- **The type files print other names than the paths.** `PDUMH20NET` lists its
  outlets `1` to 16 and the drawing's paths are `outlet-1` to `outlet-16`
  (`library/devices/eaton/pdumh20net/device.yaml:448` is the rule
  `outlet-{n}` to `{n}`). `LPWR-F` and `PSU-132-DESR` list a module port
  `{module}/Inlet`, where the drawing's element is `connector-block` and
  `terminal-block`. A module port that is named as its path resolves today:
  `psu-1/module/inlet` finds `{module}/inlet` in the module type
  (`library/exports/netbox/module-types/Dell/psu-1100w-ac-14g.yaml`).
- **A fixed input cord is already data on a PDU**: `attrs.power.input-plug` and
  `input-cord: fixed` (`spec/schemas/device.schema.json:300-304`, in use on
  `eaton/pdumh20net`), and the DCIM export writes the plug as the input power
  port's type.

## 4. Cord types with two named ends

### 4.1 What a type says about its plugs

`power-c13` is "IEC 60320 C13/C14 power cord, H05VV-F 3G1.0" and says it only in its
label. Its keys are `media`, `family`, `conductor`, `od_mm` and the bend radius.
Nothing reads the plugs.

| choice | what it is | what it changes |
|---|---|---|
| **(a) plug refs on the type** | `ends: [generic/c13-plug@1, generic/c14-plug@1]`, an unordered pair of component refs of class `port`, in the words the library already uses | `cable-types.yaml`, a new optional key in the published `cable-types.json` (the file says a new key is additive and `format` stays 1); `cable_types_index.py` validates each ref against the components; `kit/rack/cable-types.js` reads it. No rack key, no export. **One-way when built**: a published key. |
| (b) interface names | `receptacles: [iec-c14, iec-c13]` | Same files. Cannot tell a 5-15P cord from a 5-20P one: `nema-5-15p-cord` mates `[nema-5-15r, nema-5-20r]` and `nema-5-20p-cord` mates `nema-5-20r`, so a 5-20R accepts both. Rejected. |
| (c) leave it in the label | parse "C13/C14" | Nothing reads text; rejected. |

**Proposal: (a).** The pair is unordered because the rack file's A and B ends carry
no meaning of their own. Which plug is at which end comes from the slots (4.2).
The cord's DC and ground cousins (`dc-power-design.md` 5.5) would state `ends` too,
or `[ring-lug, ring-lug]`, so one key serves all of `power` and `ground`.

### 4.2 Finding a cord whose plug an end does not accept

With a type named, each end is checked against the type alone, which keeps
[cable-ends-design.md](cable-ends-design.md) section 3's rule that two receptacles
are never compared with each other.

1. For each end, the plugs its slot takes are `cableEndsOf(slot)`.
2. The type's two plugs are assigned to the two ends so that each is a plug its end
   takes. If one assignment exists, it is the derived plug at each end. This also
   answers a C39 outlet (it takes a C14 and a C20) without reading the far end, so
   `pairedWith` stays for a cable that names no type.
3. If none exists, a warning names the cord and the end: "power-c13 is a C13 to C14
   cord; end B is a C14 inlet, which takes a C13 plug, and A is also a C14
   inlet." Never a refusal (cable-ends-design.md section 5).
4. A plug stated on an end still wins and is checked against the type: a stated plug
   that is not one of the type's two is a warning.

The picker gains a use: once the first end is chosen, the types offered are those
with a plug that end's slot takes (`cordTypesFor(slot)`). Two-way when built: a
warning and a list, no saved key beyond 4.3.

### 4.3 The saved key

| choice | what it is | what it changes |
|---|---|---|
| **(a) store `type` on the cable** | The id of a row of `cable-types.json`, beside `media` | The rack schema's `cable` gains an optional `type` string (the published rack schema); `cable.add` and `cable.update` take it; `withCable` writes it; the rack file stays version 4. The kit already reads the key and falls back to the media where an id is not in the table (`spec/tests/js/rack-cable-types.mjs`). **One-way when built**: a saved id. A removed or renamed id in `cable-types.yaml` is a major of that file, so ids are kept. |
| (b) derive the type, never save it | A cord's type is the one whose plugs fit the two ends | No saved key. Cannot record a gauge, a colour or a locking cord, and a DC feed's gauge (`dc-power-design.md` 5.5) has nowhere to live. |
| (c) save the two plug refs | `plug` on both ends, always | Redundant with the slots, and drifts from them. |

**Proposal: (a), built in the second slice (section 11), not the first.** The first
slice needs no saved key (section 10). `type` is needed the moment a person picks
between two cords that fit the same ends (14 AWG and 12 AWG, a DC feed), and a DC
feed cannot be chosen without it.

### 4.4 Stock lengths

`STOCK_M` is one list for every media (`kit/rack/route.js:1191`: 0.5 to 30 m).
`chooseStock` tries it in order. No maker's list of power-cord lengths is held, and
this note does not invent one.

| choice | what it changes |
|---|---|
| (a) the shared list | nothing |
| **(b) an optional `stock_m` on a type** | `cable-types.yaml`, a new optional key (**one-way when built**: a published key); `chooseStock` takes the cable's type's list where it has one. Sourced per type, like `od_mm`. |
| (c) a list for each media in the kit | a second table of what a type table should state |

**Proposal: (b), and no type states one until a maker's list is read and cited.**
Until then (a) holds. Nothing in the first two slices needs the key.

### 4.5 The bill-of-materials line a cord makes

`cableBomRows` writes "Power cable" with "2 m; power at both ends". That is not
orderable. [cable-ends-design.md](cable-ends-design.md) section 3 says a derived
plug "is never a bill-of-materials line"; that stays: the plugs belong to the cord
and are not lines. The change is to the cord's own line.

| choice | line | what it changes |
|---|---|---|
| (a) as now | "Power cable; 2 m; power at both ends" | nothing |
| (b) name the plugs | "Power cable; 2 m; C13 to C14" | `cableBomRows` keys on the two derived plugs (`info.plug` of each settled end), named by their `attrs.connector`, in one order as `connectorText` does for the families |
| **(c) a typed cord names its type, an untyped one (b)** | "IEC 60320 C13/C14 power cord, H05VV-F 3G1.0; 2 m" or "Power cable; 2 m; C13 to C14" | (b), plus the type's `label` when the cable names a type |

**Proposal: (c).** Rows of existing racks change text where they hold a power cord;
nothing is saved. Two-way when built. A consumer that parses the BOM text sees a
new description. The derived plugs come from `attrs.connector` of each plug
contract (`c13`, `c14`, `nema-5-15p`, checked on four contracts).

## 5. The DCIM cables file for power

### 5.1 What the file does today

`cableImportRows` (`kit/rack/dcim-rules.js:456`) leaves a ground wire out by
name, and sends a power cable through the same steps as a data cable: both ends
must resolve in the type files, the two kinds of end must be ones a DCIM joins
(`MEETS` has `powerport` with `poweroutlet`), and no port may already have a cable
in the file. The type is `cableType(media)`, and `CABLE_TYPE` has eight rows and none
for `power`, so a power cable is written with a blank type and the note "its
media (power) has no NetBox cable type, so its type is blank".

Two things stop a power cord being useful:

1. **An outlet's end does not resolve.** A cord from a server's inlet to
   `outlet-9` of `PDUMH20NET` reaches `resolveEnd` with the path `outlet-9`, and the
   device type lists `9`. The reason written is "the device type PDUMH20NET lists no
   port named outlet-9", and the cable is left out. The inlet end resolves.
2. **The type is blank.**

### 5.2 The name an end prints

| choice | what it is | what it changes |
|---|---|---|
| **(a) publish the names** | The build writes, for every connector slot a name rule covers, `{path: printed name}`: `configs[].names` widened from the paths of `states` to every slot the device's `interfaces:` names; and a `names` entry on a module component for a port whose printed name differs from its path (`terminal-block` prints `Inlet`). The kit's `endResolver` reads them. | `render.py` `config_names` (one function with the exporter's `listing_names`, so the file and the export cannot disagree, the principle `config_names` already states); the published `configs.json` and `components.json` gain entries (**one-way when built**: published keys, additive); `dcim-rules.js` reads them in `resolveEnd`; no contract, so no device version bump (the lock fingerprints contracts: to be confirmed by `devicelock.py` when built). |
| (b) strip the prefix | `outlet-9` is `9`, `outlet-front-1` is `Front 1` | A convention the kit would guess; refused by the rule in `resolveEnd`'s comment and wrong for `outlet-a2` (`A2`). Rejected. |
| (c) read the path out of the type file | The exporter writes the path into each outlet's `description` | A path in free text for a reader to parse. Rejected. |

**Proposal: (a).** It extends a mechanism that exists (A11) rather than adding one.
`names` has no entry for a part no rule names, so the kit keeps its present
behaviour there.

### 5.3 The cable type

Both targets have a `power` cable type: NetBox `CableTypeChoices.TYPE_POWER = 'power'`
and Nautobot `CableTypeChoices.TYPE_POWER = "power"` (sources, 5.6). The proposal
adds one row, `power: 'power'`, to `CABLE_TYPE`, which both targets share. A
typed cord's id (section 4) and a DC feed's conductors go in NetBox's description,
and in Nautobot's label and notes, because Nautobot's cable has no description
(5.6). A ground wire stays out: neither target has a ground termination.

Two-way when built: the cables file is regenerated, and a cable that was written
with a blank type is written with `power`. A DCIM that imported the older file holds
the blank type; the README says so.

### 5.4 One AC cord

A server's inlet to a PDU's outlet is one row for each target, ends in either order
(both targets pair a power outlet with a power port in both directions).

| column | NetBox cables file | Nautobot cables file (read by the kit's `import_cables.py`) |
|---|---|---|
| device, type, name, A | the PDU, `dcim.poweroutlet`, `9` | the same names |
| device, type, name, B | the server, `dcim.powerport`, the module type's name with its bay filled in (for example `PSU1/inlet`) | the same |
| `type` | `power` | `power` |
| `status` | `planned` | `Planned` |
| `label`, `color`, `length`, `length_unit` | as for any cable | as for any cable |
| description | the purpose, the length note, and the cord (`C13 to C14`) | no field: the cord goes in the label, and the README |

### 5.5 One DC feed

One cable with two conductors is **one row**, decided 2026-10-12 on #1045. The two
conductors are not two terminations: in both DCIMs a power outlet is one
termination and a power port is one, and the conductors are a property of the
cable. A breaker panel's output is a power outlet (`output-a1` of the
300CB08 is `power-outlets: - name: output-a1`, the same as its path), and a supply's
DC terminal is a power port. The row is that outlet to that port, type `power`; the
conductor count, the gauge and the colours go in the NetBox description (and the
label and README for Nautobot). Two cables, one for each conductor, would write two
rows to one pair of ports; the cables file allows one cable on a port
(`cableImportRows`) and a Nautobot termination is a one-to-one (5.6).

A DC row cannot be written until its ends land: the Amphenol output terminals and
the DC terminals of the three supplies are not slots (A9, A10, 8.8). That is library
work in [dc-power-design.md](dc-power-design.md) step 6, not part of the first
slice, and it needs the module port names of 5.2 (`{module}/Inlet`).

### 5.6 Upstream facts, and where each was read

Read on 2026-10-18 through the GitHub contents API, at the pins the kit already
cites in `dcim-rules.js`: NetBox `netbox-community/netbox` v4.7.2, commit
251458b89a5eb2f5fe0d20ecd1140ba08f141a9c; Nautobot `nautobot/nautobot` v3.2.6,
commit 3dc554b4304d3556461718bb71146b3f6a16b7c2.

| fact | file at the commit | what the file shows |
|---|---|---|
| NetBox: the cables import takes a power end by device and name | `netbox/dcim/forms/bulk_import.py`, `CableImportForm` | `side_a_type` and `side_b_type` are limited to `CABLE_TERMINATION_MODELS`; `side_a_device`, `side_a_name`, `side_a_power_panel`, `type`, `profile`, `bundle`, `color`, `length`, `length_unit` and `description` are in `Meta.fields` |
| NetBox: which models are ends, and which pair | `netbox/dcim/constants.py` | `CABLE_TERMINATION_MODELS` includes `poweroutlet`, `powerport` and `powerfeed`; `COMPATIBLE_TERMINATION_TYPES` has `poweroutlet: [powerport]`, `powerport: [poweroutlet, powerfeed]` and `powerfeed: [powerport]` |
| NetBox: `power` is a cable type | `netbox/dcim/choices.py`, `CableTypeChoices` | `TYPE_POWER = 'power'` |
| NetBox: the pairing is checked, and one side holds one kind | `netbox/dcim/models/cables.py`, `Cable.clean` | "Incompatible termination types" and "Cannot connect different termination types to same end of cable." |
| NetBox: the cable's fields | `netbox/dcim/models/cables.py`, `Cable` | `type`, `status`, `profile`, `label` (100), `color`, `length` (two decimal places), `length_unit`, `bundle` |
| NetBox: a feed has no A/B field | `netbox/dcim/models/power.py`, `PowerFeed` | `power_panel`, `rack`, `name`, `status`, `type`, `supply`, `phase`, `voltage`, `amperage`, `max_utilization`; `type` is `primary` or `redundant` (`choices.py`, `PowerFeedTypeChoices`); `PowerPanel` has `site`, `location`, `name` |
| NetBox: a feed is imported on its own | `bulk_import.py`, `PowerFeedImportForm` | `site`, `power_panel`, `location`, `rack`, `name`, `status`, `type`, `supply`, `phase`, `voltage`, `amperage`, `max_utilization` |
| Nautobot: `power` is a cable type, and the cable has no description | `nautobot/dcim/choices.py`, `CableTypeChoices`; `nautobot/dcim/models/cables.py`, `Cable` | `TYPE_POWER = "power"`; `Cable` has `cable_type` (a foreign key), `type`, `status`, `label`, `color`, `length` (a small integer) and `length_unit`, and no `description` |
| Nautobot: the pairing | `nautobot/dcim/constants.py` | `COMPATIBLE_TERMINATION_TYPES` has the same three entries as NetBox |
| Nautobot: a power end takes no multi-connector cable type | `models/cables.py`, `CableToCableTermination.clean`; `constants.py`, `BREAKOUT_COMPATIBLE_TERMINATION_TYPES` | `clean` raises for a termination model outside the breakout set when the cable's `CableType` is multi-connector; the set holds circuit terminations, front ports, interfaces and rear ports only. A power row names no Nautobot `CableType`, and the kit writes none. |
| Nautobot: one cable on a power end | `models/cables.py`, `CableToCableTermination` | `power_feed`, `power_outlet` and `power_port` are `OneToOneField`s |
| Nautobot: an A/B path exists | `nautobot/dcim/choices.py`, `PowerPathChoices`; `nautobot/dcim/models/power.py` | `PATH_A = "a"`, `PATH_B = "b"` ("Path A", "Path B"); `power_path` is a field of `PowerPanel` and `PowerFeed` |
| Nautobot: a feed's fields | `models/power.py`, `PowerFeed` | `power_panel`, `destination_panel`, `rack`, `name`, `status`, `type`, `power_path`, `supply`, `phase`, `voltage`, `amperage`, `max_utilization`; a panel has a required `location` |

**Not read: the Nautobot import script.** The Nautobot cables file is read by
`import_cables.py` (`KIT_SCRIPT`, `dcim-rules.js:616`), which is not in this
repository. Whether it accepts `dcim.powerport` and `dcim.poweroutlet` as `a_type`
is not known from here. The first slice reads it before claiming Nautobot works.

## 6. A and B feeds, and a check that a device is on both

### 6.1 What exists

Nothing in the kit reads a side. `dc-power-design.md` 5.7 defines `side: a | b` on a
DC port, and PR #1090 put it in the component schema; no part states it and no kit
file reads it. A load's feed is prose today ("PS0 from feed A",
dc-power-design.md 5.7). The DCIMs differ: NetBox's feed has `type` primary or
redundant and no path; Nautobot's panel and feed have `power_path` `a` or `b` (5.6).

### 6.2 Where a side lives

| choice | what it is | what it changes |
|---|---|---|
| **(a) on the feed** | A feed (section 7) has `side: a \| b`. A supply's side is traced: inlet, cord, PDU outlet, the PDU's input, its cord, the feed. | The check needs section 7's feed object. No key on a device. Where the chain stops (a PDU whose input is not cabled), the side is not known, and the check is quiet there, as the checks of dc-power-design.md section 6 are. |
| (b) on the placed item | `feed: a` on a rack item or a part beside the rack, a stated side of a PDU | A saved key on items (**one-way when built**). Can drift from the cords: a PDU stated `a` whose input cord runs to a `b` feed. |
| (c) read the cord colour | Red is A and blue is B (#897 lists it as a convention) | A cosmetic fact is not a feed. `dc-power-design.md` 5.6 refuses a stand-in promoted by a convention that sounds right. Rejected. |

**Proposal: (a), with (b) allowed only as the stated end of a trace that leaves the
rack's drawing** (a PDU whose feed is not modelled): `side` on a rack item, read
only where no feed is reached. Vocabulary `a | b`, as `dc.yaml` and the component
schema already have it; **one-way when built**, since it is a published value (a
third side would be a new value, which is additive).

### 6.3 The check

For a device whose built configuration has two or more supplies:

- **every side reached** → no finding;
- **two supplies that reach the same side** → a warning, "both supplies of X are
  on side A", the rule of dc-power-design.md section 6;
- **a supply with no cord, or a trace that stops** → the existing loose finding, and
  a quiet "side not known" for the supply.

A device with one supply gets no finding: it cannot be on both, and saying so on
every single-supply server is noise. With more supplies than sides (four on two),
each side must be reached. A warning, never a refusal. Two-way when built.
Kit only; no export. A findings line, so `inspect`, `describe` and the cable
schedule's notes follow.

### 6.4 In the DCIMs

A feed's side is written to Nautobot's `power_path` (`a` or `b`) and, for NetBox,
which has no such field, to the feed's `description` and `comments`. Both are
section 7's files, not the cables file.

## 7. A feed end outside the rack

A branch circuit, a fixed input cord's far end, a battery plant.

### 7.1 What a DCIM calls it

A cable end that is a feed is `dcim.powerfeed`, paired only with a power port
(5.6). In NetBox the cables import takes it with `side_a_power_panel` and the feed's
name; in Nautobot it is a `power_feed` termination. In both a feed is a row of its
own, on a power panel that must exist first, with a voltage, an amperage and a
status. The kit writes none of those files.

### 7.2 What a rack file says

| choice | what it is | what it changes |
|---|---|---|
| **(a) a feed list** | `rack.feeds[]`: `{id, label, side?, supply, voltage, amps, phase?, panel?, receptacle?}`. An end is `{item: <feed id>, path: 'out', view: 'rear'}`, the way a part beside the rack is an `item` of `rack.zeroU` today (`zeroUById`). | A new saved key in the rack file and its published schema (**one-way when built**), the end addressing, `endPaneIn` and `freePorts` for the new kind of item. `receptacle` is optional; stated, it is a registered interface, so the plug check runs against it. |
| (b) a library part | A branch circuit is a part beside the rack with one outlet (a 5-20R, a C39, an L21-30R) | No new key. The exporter writes every part beside the rack as a device (`zeroUImportItems`), which a branch circuit is not, so it would need an exception. Interfaces for L21-30R and L6-30R are not registered. |
| (c) a loose label | An end of `{label: 'Feed A1'}` | Checks nothing, exports nothing, and a cable with a text end is not a cable. |

**Proposal: (a).** A feed carries what a DCIM needs to write a power feed and its
panel, and the side of section 6.

### 7.3 The far end of a fixed input cord

`eaton/pdumh20net` states `input-plug: nema-l5-20p` and `input-cord: fixed`; the
DCIM export already writes its `input` as a power port of that type. The cord is the
PDU's own, so its near end is a plug with no slot (`generic/nema-5-20p-plug@1` is
class `inlet` and states no `mates`).

| choice | what it is | what it changes |
|---|---|---|
| **(a) the input port is an end** | A cable lands on the part a PDU's outlets are `fed-by`, when its device states `input-cord: fixed`, with the other end on a feed. The plug is `input-plug`. | `cableLandsOn` gains a second route (for a fixed plug), so a cable from the PDU to the feed has a length, a route and a colour like any cable. Needs the `fed-by` target and `input-cord` in a published file: neither `render.py` nor the kit names `fed-by`, so it is not known here whether `configs.json` carries it. **One-way when built**: a landing rule. |
| (b) the feed on the PDU | A key on the PDU's rack entry, `feed: 'f1'` | No landing rule. A second way to say a connection, with no length and no route. |

**Proposal: (a)**, built after 7.2. Where `fed-by` is not published, the build
publishes it first, additively.

### 7.4 In the cables file

Until a feed is written, a cable with a feed end is left out of the cables file
with its reason: "its far end is a feed, which a DCIM holds as a power feed on a
power panel; the kit does not write one yet" (never silently, as every cable left out
is). The file order grows by two files, power panels and power feeds, before the
cables, as #1159's bundles file does. The numbering is one list
(`netboxFiles(dcim)` in #1159), and the slice that writes feeds adds to it.

## 8. Load

#1045's item 12 asks for a load's draw checked against its breaker and summed per
PDU and line. It is not needed for cords, and **this note names it as a later step
(section 11) and designs nothing**. What it would stand on is in the library
already: `power-roles.yaml` says which classes draw (`power-draw-max-w`) and which
supply (`power-output-w`), a breaker states its `rating`, and a feed (section 7)
states a voltage and an amperage. What it lacks is the trace of section 6.2 (which
load is on which PDU, line and feed) and a draw for the parts that state none. It
follows sections 6 and 7.

## 9. Every one-way choice, together

A published key, a saved key, an end shape or a landing rule is hard to take back
once a file or a consumer holds it.

| one-way when built | proposal | section |
|---|---|---|
| `ends` on a cable type (a published key of `cable-types.json`) | (a) | 4.1 |
| `type` on a saved cable, and the ids it holds | (a), second slice | 4.3 |
| `stock_m` on a type | (b), no type states one yet | 4.4 |
| `names` published for every slot and on module components | (a) | 5.2 |
| the `side` vocabulary `a \| b` | as `dc.yaml` | 6.2 |
| `rack.feeds[]` and an end addressed to a feed | (a) | 7.2 |
| a landing rule for a fixed plug | (a), after 7.2 | 7.3 |

Two-way: the mismatch warning and the picker (4.2), the BOM text (4.5), the `power`
cable type column (5.3), the A/B check (6.3).

## 10. The first build slice

**The cables file writes a power cord, for NetBox and for Nautobot.** It needs no
saved key, no schema publish, no library part and no contract change, and it is the
one piece of #1045 (W5, A11, 7.8, 8.9) that is half done and blocked on nothing.

It starts after #1159 merges (2.5), because both edit `cableImportRows` and the
file numbering.

**Files**

| file | change |
|---|---|
| `spec/tools/portrayal/render.py` | `config_names` names every slot the device's `interfaces:` covers, not only the paths of `states`; a `names` entry on a module component for a port whose printed name differs from its path |
| `kit/rack/dcim-rules.js` | `CABLE_TYPE.power = 'power'`; `endResolver` hands `resolveEnd` the published names; the README text for power |
| `kit/rack/catalog.js` | `configFacts` and `loadSlots` carry the module names |
| `kit/README.md`, `docs/format-stability.md` | the two published keys |
| `changelog.d/` | one fragment; the kit's version is not bumped in the pull request (the repository's template) |

**Tests**

- `spec/tests/js/rack-dcim-import.mjs`: a rack with a server (two supplies) and a
  `PDUMH20NET`; the cord to `outlet-9` is a row with `9` and type `power` in both
  targets; a cord to a port no rule names is left out with its reason; a ground wire
  is still out; every row keeps the columns it had.
- A Python test for `config_names` over a device with an `interfaces:` rule, with the
  existing `states` case unchanged (the key's value for a path in `states` does not
  move).
- The lock: `devicelock.py --library library` should report nothing, since no
  contract changes. If it does, the slice is wrong.
- `names` read against the exporter: for every device that has outlets, the names
  `config_names` gives equal the names in the device-type export.

**Proof against a NetBox and a Nautobot import.** The kit's modules and cables files
were accepted by NetBox 4.7.2 and Nautobot 3.2.6 (`dcim-rules.js` comments); the
same two are the proof here.

1. A rack of `PDUMH20NET`, two dual-supply servers and a DC breaker panel is exported
   with a site and a role.
2. Load the library's device and module types for those models into a NetBox 4.7.2
   and a Nautobot 3.2.6.
3. Import the files in the README's order.
4. Expect: the cable count equals the file's rows; each cable's type is `power`;
   each terminates a power outlet and a power port with the names written; a trace
   of a server's supply reaches the PDU's `input`; the outlet reads as connected.
   What a second import of the same file does is seen and written down, not assumed.
5. For Nautobot, first read `import_cables.py` for the type names it takes (5.6).

A pull request carries the numbers it saw, and says so where it could not run an
import. The note's author could not.

## 11. Slices after the first

In order; each is its own pull request.

2. **Cord types with named plugs** (4.1 to 4.5): `ends` on the types, the SJT cords
   (a source for each: Belden 19348 and 19354 are cited by PR #1050 for 8.33 and 9.65
   mm; no 12 AWG sheet is held), `type` saved, the picker, the BOM line.
3. **Feeds and A and B** (6, 7.2): `rack.feeds[]`, the end addressing, the check, the
   power panel and power feed files for NetBox and Nautobot.
4. **The fixed input cord** (7.3).
5. **DC** (dc-power-design.md steps 2 to 6): the lug seats, the three supplies, the
   DC cable types; then 5.5's one row.
6. **Side views, and load** (A12, section 8).

## 12. Open questions

1. **Is the first slice the right one, and should it wait for #1159?** Answering no
   to the wait changes only the merge order and the conflicts in `dcim-rules.js`.
2. **Is `ends` as plug refs (4.1 a) accepted?** Interface names do not tell a 5-15P
   cord from a 5-20P. It publishes a key in `cable-types.json`.
3. **Is `type` the saved key (4.3 a), and in the second slice?** It adds a property
   to the published rack schema and a field to the commands.
4. **Is a feed a `rack.feeds[]` list (7.2 a)?** The alternative is a library part
   (b), which the exporter would have to exempt as a device.
5. **Sides: only `a` and `b`?** A rack with a third feed (an N+2 plant) has no word
   for it. It changes the value set `dc.yaml` and the schema already hold.
6. **Should a device with one supply say anything about redundancy (6.3)?** The
   proposal is silence. Saying "single supply" changes the findings line on every
   single-supply server.
7. **Who proves the import?** The slice needs a NetBox 4.7.x and a Nautobot 3.2.x,
   and the Nautobot script. If the author of the slice has no instance, the pull
   request says it was not proved, and whoever has an instance runs step 4.
8. **Power-cord stock lengths (4.4):** which maker's list should the first type that
   states one cite? None is held.

## 13. What this note does not do

It changes no part, device, schema, kit file or export, and bumps no version. It
does not design DC beyond pointing to dc-power-design.md, a load, side views, or an
Infrahub target (#1151, open and not read). It cites no figure for a cord, a stock
length or a DCIM field that it did not read; where something was not read (the
Nautobot import script, the page that calls the kit, `fed-by` in `configs.json`),
it says so where it is used.

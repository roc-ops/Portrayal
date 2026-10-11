# Power outlets: what a distribution panel hands on

Status: built, 2026-10-06. Issue #806. Builds on the power-port half of
`spec/tools/portrayal/dcim_export.py` (`PART_POWER`) and on
[connectors-dc-terminal-design.md](connectors-dc-terminal-design.md).

## 1. What existed, and what was missing

The exporter wrote `power-ports`: where a supply's cable is landed. It had no notion of a
power OUTLET, which is where a device hands power on.

The first device this bit is the Amphenol Network Solutions 300CB08, a breaker panel.
Two feeds come in, and sixteen circuits go out, each through one breaker position.

| on the device | exported before | exported now |
|---|---|---|
| `input-a`, `input-b` - one feed each, both poles | two `dc-terminal` power ports | the same |
| `breaker-a1` to `breaker-b8` - sixteen positions | sixteen module bays | the same, each naming the output it protects |
| `output-a1` to `output-b8` - sixteen output circuits | nothing; registered in `NOT_A_DCIM_PORT` | sixteen power outlets |

For a distribution panel the outlets are the fact a DCIM user most wants: which panel
output a router's supply is cabled to, and which feed stands behind it.

## 2. What both targets offer

Read from each project's source: NetBox `dcim/choices.py` at `64ce9e2d`,
`dcim/forms/object_import.py` at `743b0683` and the component template models at
`5707c0e9`; Nautobot `dcim/choices.py` at `3edb1fca`, `dcim/forms.py` at `6c1299e2` and
the component template models at `3606c7da`.

| | NetBox | Nautobot |
|---|---|---|
| outlet type for a DC screw terminal | `dc-terminal` | `dc-terminal` |
| outlet type for a connector upstream does not name | `other` | `other` |
| the import key naming the feeding port | `power_port` | `power_port`, mapped to `power_port_template` "for backwards compatibility" |
| how that key is matched | by name, among the same type's power ports | the same |
| an outlet's `description` on import | kept | **dropped**: not in the import form |
| `feed_leg` | `A`, `B`, `C` | `A`, `B`, `C` |
| an outlet template may belong to | a device type or a module type | a device type or a module type |
| the feeding port must belong to | the same device type or module type | the same device type or module type |

Consequences.

- **`dc-terminal` is in both, as an outlet type as well as a port type,** and `other` is
  in both. No slug is invented. `PART_OUTLET`'s values are checked against
  `OUTLET_TYPES`, that shared list, because Nautobot's component import turns an unknown
  type into `other` without a word.
- **One block serves both targets.** Both read `power_port` by name and import power
  ports before power outlets, so `for_target` does not rewrite outlets.
- **An outlet and the port that feeds it live on one type.** Both models' `clean()`
  refuse a port from another type, so an outlet on a breaker's module type could not name
  the panel's feed. The outlet is on the device type, which is also physically right: the
  BATT and RTN screws stay when a breaker is pulled, and a blank or fuse position keeps
  its terminals.
- **Nautobot loses the outlet's description.** Its module-bay import keeps one, so the
  breaker sentence is written on the bay as well.

`feed_leg` is a phase of a three-phase supply. A panel's side A and side B are two feeds,
not two legs of one, so `feed_leg` is not used for them. It would also collide by
accident: the legs are spelled `A` and `B`.

Neither target links an outlet to a module bay. That a circuit is live only through the
breaker in one position can be said in words and not as a relation.

## 3. Decisions

1. **An output circuit is a power outlet on the device type**, with `power_port` set to
   the feed of its side.
2. **The manifest says which feed, on each placement.** `fed-by` is stated per output and
   not on the group: nothing is inferred from a group or from an `-a`/`-b` in a name, and
   a panel whose outputs do not split cleanly by group needs nothing more.
3. **The manifest says which position, on the placement.** `through` names the breaker
   position a circuit runs through, and is carried into the outlet's description and the
   bay's.
4. **`feed_leg` is not written** for a two-feed DC panel.
5. **An outlet is named as its device's `interfaces:` rules name it, else by its
   placement id**, as every exported port is: `output-a1`. The rules name power
   outlets as they name interfaces, so an outlet a rule names takes its printed
   label (the Eaton EVMI2130X's `outlet-a1` exports as `A1`); an outlet no rule
   names keeps its placement id. A NOS listing that states its own
   `interfaces` does not apply these rules, so its export keeps every outlet's
   placement id.
6. **Outlets are a table row per part, as power ports are.** A part exports outlets
   because `PART_OUTLET` lists it, not because of its class.
7. **A connectorized output is `other`, labelled.** The 300CB08-C and -SC outputs are
   two-pole P40 receptacles, which neither target names; `amphenol-ns/output-p40` maps to
   `other` with `label: P40`, the treatment `OTHER_LABEL` gives an interface whose form
   factor upstream does not name.
8. **Stating `fed-by` or `through` is a minor version; changing either is a major.**

Rejected: `for:` (section 4), an `attrs` bag (nothing would check it), inferring the feed
from `-a`/`-b` names, one outlet per screw (the two screws are one circuit's two poles,
as a feed's two studs are one power port), outlets on the breaker's module type (section
2), and a hard-wired outlet type in the exporter instead of a table row.

## 4. The manifest

Two placement keys.

```yaml
views:
  rear:
    components:
      placements:
        - {id: input-a,   ref: amphenol-ns/input-feed-studs@1, group: feeds, rel-pos: 1}
        - {id: output-a3, ref: amphenol-ns/output-terminal@1, group: outputs-a,
           rel-pos: 3, fed-by: input-a, through: breaker-a3}
```

- **`fed-by`** names a placement on this device whose part exports a power port.
- **`through`** names the bay that the circuit runs through: its breaker or fuse
  position. It is optional; a panel with fixed, unprotected outputs has none.

Where `through` names a FIXED breaker placement rather than a bay (#934, a rack
PDU's branch breaker), the outlet description names that breaker as the unit prints
it, `Through breaker A`, and not by its placement id: the first of the placement's
`attrs.label` and `attrs.section` (the Eaton G4 tile letter) that is set, the id only
when neither is (owner decision, 2026-10-09; `dcim_export.breaker_name`). A bay
position keeps `Through breaker position <id>`, since a bay prints nothing of its own.

Both are bare ids resolved over the whole device, because both cross a face: the output
is on the rear and the position it runs through is on the front. A `for:` cannot say
this. `for:` is a UI binding, emitted as `data-for`, saying "this mark or lamp annotates
that", and it waives L13's overlap check between the two; it was not made for two parts
on different faces with no drawing between them.

## 5. The export

```yaml
# device-types/Amphenol Network Solutions/300CB08.yaml
power-ports:
  - {name: input-a, type: dc-terminal}
  - {name: input-b, type: dc-terminal}
power-outlets:
  - name: output-a1
    type: dc-terminal
    power_port: input-a
    description: Through breaker position breaker-a1
  # ... sixteen in all
module-bays:
  - name: breaker-a1
    position: breaker-a1
    description: 'Accepts: breaker-1ru, tpa-fuse-holder-307492, breaker-blank-1ru; protects output-a1'
```

- `PART_OUTLET = {"amphenol-ns/output-terminal": "dc-terminal", "amphenol-ns/output-p40":
  "other"}`, beside `PART_POWER`, keyed on the ref for the reason `PART_POWER` is;
  `OUTLET_LABEL` gives the P40 its label.
- A placement of a listed part becomes one outlet, and the rows are in natural order. Its
  `power_port` is the power port its `fed-by` names. A `fed-by` that names nothing
  exporting a power port stops the export (`NotExpressible`), because both targets
  reject a dangling reference at import. An outlet with no `fed-by` is written without
  `power_port`; it imports, and L134 counts it.
- The same block is written for NetBox and for Nautobot (section 2).
- `amphenol-ns/output-terminal` and `amphenol-ns/output-p40` have left
  `NOT_A_DCIM_PORT`; the register's stale-entry test insisted on it.
- The bay's added sentence does not move the module-type collision check:
  `dcim_significant` already reads a bay's description as a sentence about the drawing.

## 6. A module that carries outlets

Not needed by the 300CB08 and not built. It is the shape a rack PDU with a hot-swappable
outlet module would need, and both targets allow it: the outlet template belongs to the
module type. Its feeding port would have to be on the same module type, so it applies
only to a module that has an input of its own. `build_module` would read `PART_OUTLET`
the way it reads `PART_POWER`, and `MODULE_PORT_KEYS` would gain `power-outlets` with
each row's `power_port` tokenised as its name is.

## 7. Lint

- **L132, `fed-by` resolves.** It names a placement on this device whose part is in
  `PART_POWER`, and stands on a part in `PART_OUTLET`. An error.
- **L133, `through` resolves.** It names a bay on this device, or, since #934, a
  placement of a part of class `breaker` fixed to the unit (a rack PDU's branch
  breaker, [pdu-model-design.md](pdu-model-design.md) section 5.3). An error.
- **L134, a part in `PART_OUTLET` is fed.** Every placement of one states `fed-by`. A
  warning below `verified` and an error at it: an outlet with no feed is importable, and
  is the incomplete model this work exists to end.
- **L135, one position, one circuit.** Two placements do not name the same `through`. A
  warning, because a panel that parallels two outputs behind one breaker is possible. It
  reads bays only: a fixed PDU breaker feeds many outlets by design (#934).

## 8. Device locks

`fed-by` and `through` are in devicelock's `PLACEMENT_ADDRESSING`, beside `for`. They
change what is exported, not what is drawn. Stating one where there was none is a minor:
the export gains outlets and loses nothing. Changing or dropping one re-files an imported
outlet's feed and is a major. The three panels went to 1.1.0.

## 9. Tests

- `test_300cb08_power_outlets.py`: each of the three panels exports sixteen outlets,
  eight naming each feed, each naming a position that exists and whose bay names it back,
  from the build and in the committed files of both trees, and both trees carry the same
  outlets.
- `test_power_outlets.py`: an outlet whose `fed-by` names no power port stops the
  export; one with none is written without `power_port`; no `feed_leg`; the P40 label;
  `OUTLET_TYPES`.
- `test_silent_drops.py`: the census knows the outlet exit, and nothing listed in
  `PART_OUTLET` is in `NOT_A_DCIM_PORT`.
- `test_power_outlet_lint.py`: L132-L135.

## 10. Order of work

1. Schema: `fed-by` and `through` on a placement; devicelock files them as addressing.
2. Lint, section 7.
3. Exporter: `PART_OUTLET`, the `power-outlets` block, the failing case.
4. The 300CB08, 300CB08-C and 300CB08-SC: the two keys, the register entries removed,
   exports regenerated.

## 11. Open questions

- **AC.** A rack PDU's C13 and C19 outlets have types in both targets and would use the
  same table. Whether a three-phase PDU states `feed_leg` per outlet is a question for
  the first one modelled. [pdu-model-design.md](pdu-model-design.md) (#934) proposes
  the answer: only for an outlet wired line to neutral on a wye input.
- **An alarm contact.** The panel's Form C alarm relays have no port type in either
  target. They stay in `NOT_A_DCIM_PORT`.
- **Ratings.** An outlet template in either target carries a type and no current rating.
  A feed rated in amperes at one of three nominal voltages has no honest single wattage,
  so no draw figure is written on the power ports either.
- **An unfed outlet in Nautobot.** Its import form reads `power_port` from the submitted
  data before validating, so an outlet written without one has not been proved to import
  there. No device in the library writes one; L134 keeps it that way at `verified`.

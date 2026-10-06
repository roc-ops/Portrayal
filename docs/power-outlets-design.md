# Power outlets: what a distribution panel hands on

Status: design, 2026-10-06. Issue #806. Nothing here is built. Builds on the power-port
half of `spec/tools/portrayal/dcim_export.py` (`PART_POWER`) and on
[connectors-dc-terminal-design.md](connectors-dc-terminal-design.md).

## 1. What exists, and what is missing

The exporter writes `power-ports`: where a supply's cable is landed. It has no notion of a
power OUTLET, which is where a device hands power on.

The first device this bites is the Amphenol Network Solutions 300CB08, a breaker panel.
Two feeds come in, and sixteen circuits go out, each through one breaker position.

| on the device | exported today |
|---|---|
| `input-a`, `input-b` - one feed each, both poles | two `dc-terminal` power ports |
| `breaker-a1` to `breaker-b8` - sixteen positions | sixteen module bays |
| `output-a1` to `output-b8` - sixteen output circuits | nothing; registered in `NOT_A_DCIM_PORT` |

For a distribution panel the outlets are the fact a DCIM user most wants: which panel
output a router's supply is cabled to, and which feed stands behind it.

## 2. What both targets offer

Read from each project's `dcim/choices.py` and
`dcim/models/device_component_templates.py`, NetBox at `f95c567b59ea` and Nautobot at
`e49d8dc73953`.

| | NetBox | Nautobot |
|---|---|---|
| outlet type for a DC screw terminal | `dc-terminal` | `dc-terminal` |
| an outlet names the port that feeds it | `power_port` | `power_port_template` |
| `feed_leg` | `A`, `B`, `C` | `A`, `B`, `C` |
| an outlet template may belong to | a device type or a module type | a device type or a module type |
| the feeding port must belong to | the same device type or module type | the same device type or module type |

Two consequences.

- **`dc-terminal` is in both, as an outlet type as well as a port type.** No slug is
  invented.
- **An outlet and the port that feeds it live on one type.** An outlet on a breaker's
  module type cannot name the panel's feed. So an outlet that keeps its feed is on the
  device type.

`feed_leg` is a phase of a three-phase supply. A panel's side A and side B are two feeds,
not two legs of one, so `feed_leg` is not used for them. It would also collide by
accident: the legs are spelled `A` and `B`.

Neither target links an outlet to a module bay. That a circuit is live only through the
breaker in one position can be said in words and not as a relation.

## 3. Decisions

1. **An output circuit is a power outlet on the device type**, type `dc-terminal`, with
   `power_port` set to the feed of its side.
2. **The manifest says which feed, on the group.** A group of outputs is fed by one input
   and says so once. Nothing is inferred from a name.
3. **The manifest says which position, on the placement.** The breaker position a circuit
   runs through is stated per output and carried into the outlet's description.
4. **`feed_leg` is not written** for a two-feed DC panel.
5. **An outlet is named by its placement id**, as every exported port is: `output-a1`.
6. **Outlets are a table row per part, as power ports are.** A part exports outlets
   because `PART_OUTLET` lists it, not because of its class.

## 4. The manifest

Two keys, both on things that exist.

```yaml
groups:
  outputs-a: {term: Output, role: traffic, index-origin: 1, fed-by: input-a}
  outputs-b: {term: Output, role: traffic, index-origin: 1, fed-by: input-b}

views:
  rear:
    components:
      placements:
        - {id: input-a,   ref: amphenol-ns/input-feed-studs@1, group: feeds, rel-pos: 1}
        - {id: output-a3, ref: amphenol-ns/output-terminal@1,
           group: outputs-a, rel-pos: 3, through: breaker-a3}
```

- **`fed-by`** on a group names a placement that exports a power port. A placement may
  carry its own `fed-by`, which overrides its group, for a panel whose outputs do not
  split cleanly by group.
- **`through`** on a placement names the bay (or the placement) that the circuit runs
  through: its breaker or fuse position. It is optional; a panel with fixed, unprotected
  outputs has none.

Both cross a face: the output is on the rear and the position it runs through is on the
front. A `for:` cannot say this, because `for:` means "this mark or lamp annotates that",
and L14 asks the two to be near each other.

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
    description: 'Through breaker position breaker-a1'
  # ... sixteen in all
```

- `PART_OUTLET = {"amphenol-ns/output-terminal": "dc-terminal"}`, beside `PART_POWER`,
  keyed on the ref for the reason `PART_POWER` is.
- A placement of a listed part becomes one outlet. Its `power_port` is the id its
  `fed-by` resolves to; an outlet whose `fed-by` resolves to nothing that exports a power
  port fails the export, because both targets reject a dangling reference at import.
- The same block is written for NetBox and for Nautobot. Both read the device-type
  library's `power-outlets` list with `power_port` naming a port by its name.
- `amphenol-ns/output-terminal` leaves `NOT_A_DCIM_PORT`; the register's stale-entry test
  insists on it.

## 6. A module that carries outlets

Not needed by the 300CB08 and not built here. It is the shape a rack PDU with a
hot-swappable outlet module would need, and both targets allow it: the outlet template
belongs to the module type. Its feeding port would have to be on the same module type, so
it applies only to a module that has an input of its own. `build_module` would read
`PART_OUTLET` the way it reads `PART_POWER`.

## 7. Lint

- **`fed-by` resolves.** It names a placement on this device whose part is in
  `PART_POWER`. A device rule, an error.
- **`through` resolves.** It names a bay or a placement on this device. An error.
- **A part in `PART_OUTLET` is fed.** Every placement of one has a `fed-by`, its own or
  its group's. A warning at `modelled` and an error at `verified`: an outlet with no feed
  is importable, and is the incomplete model this work exists to end.
- **One position, one circuit.** Two placements do not name the same `through`. A
  warning, because a panel that parallels two outputs behind one breaker is possible.

## 8. Device locks

`fed-by` and `through` change what is exported, not what is drawn. Adding them to a
device that already exports is a minor: the export gains outlets and loses nothing.
Changing an existing `fed-by` re-files an imported outlet's feed and is a major.

## 9. Tests

- The 300CB08 exports sixteen outlets, eight naming each feed, each naming a position
  that exists.
- An outlet whose `fed-by` names a part with no power port fails the export.
- The register: `output-terminal` is gone from `NOT_A_DCIM_PORT`, and nothing listed in
  `PART_OUTLET` is in it.
- Both targets' written files carry the same outlets.

## 10. Order of work

1. Schema: `fed-by` on a group and a placement, `through` on a placement.
2. Lint, section 7.
3. Exporter: `PART_OUTLET`, the `power-outlets` block, the failing case.
4. The 300CB08: the two keys, the register entry removed, exports regenerated.

## 11. Open questions

- **AC.** A rack PDU's C13 and C19 outlets have types in both targets and would use the
  same table. Whether a three-phase PDU states `feed_leg` per outlet is a question for
  the first one modelled.
- **An alarm contact.** The panel's Form C alarm relays have no port type in either
  target. They stay in `NOT_A_DCIM_PORT`.
- **Ratings.** Both targets carry an outlet's type and no current rating; a power port
  carries `maximum_draw` and `allocated_draw`, in watts. A feed rated in amperes at one of
  three nominal voltages has no honest single wattage, so none is written.

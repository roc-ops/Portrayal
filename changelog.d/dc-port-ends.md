### Added
- The rack kit lands a cable on a DC port. A part that states a DC port
  (`dc-ports` in `components.json` and `configs.json`) is read for a rack item
  by `dcPortsOf` in `kit/rack/ports.js`: a placed part from its configuration,
  a part in a bay from the component the item's swaps, configuration and bay
  default seat there. A feed's end is the port's path (`psu-0/module/input`,
  `feed-a/input`); a single conductor's is a pole's slot path. The end reads as
  a power end (`family: power`, `mode: dc`, `inlet` or `outlet`) with a `dc`
  key: the port's direction, voltage, rating, awg and side, and its poles with
  a role and a plug each.
- One cable per port, across the port, its poles and its connector.
  `portFree` and `canCable` take an optional `dc` reader (`dcReader`); with it
  a cable on one pole makes the port partly used and a feed to it is refused
  as taken, two single-conductor runs to two poles of one port are both
  accepted, and a cable from a port to one of its own poles is refused. The
  `cable.add` and `cable.update` commands pass it.
- `freePorts` lists one row per free DC port, on the port's panel, with `dc`
  and the port's words; the pole slots and the connector slot under it are not
  rows of their own. A partly used port is no row, and each of its free poles is
  a row with `dc.pole`. `slotEnds` agrees. `configFacts` carries `dcPorts` for
  a configuration that states one.
- A contact of a pluggable DC connector is no end: it is loose, and `cable.add`
  refuses it, with the port path to give.

- What a consumer does: offer the DC row from `freePorts`, and keep an end at a
  pole path as it is. Nothing a rack file holds is rewritten and no key is
  added. An end saved on a screw is a feed of one conductor on that pole; an end
  saved on the slot of a pluggable connector that is the only DC port's
  connector reads as that port; the path of a terminal that is no slot stays
  loose and its reason names the port to give. A part that states no DC port is
  read exactly as before.

### Changed
- A port of a module in a bay reads the `role` the module's placement of it
  states, else the one its own component states, so a console port there is a
  console end and not a USB end (`seatedPort`, and `zeroUEnds` for the ports of
  a module in a bay of a part beside the rack).

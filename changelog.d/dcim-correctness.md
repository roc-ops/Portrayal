### Added
- Power outlets in the DCIM export, for a distribution panel's outputs
  (roc-ops/Portrayal#806). Two placement keys say what an outlet needs:
  `fed-by` names the placement whose power port the output hands on, and
  `through` names the bay - the breaker or fuse position - the circuit runs
  through. A placement of a part in `dcim_export.PART_OUTLET` exports as a
  `power-outlets` row on the device type, named by its placement id, with
  `power_port` set from `fed-by`; `through` is written as a sentence on the
  outlet's description and appended to the bay's (`; protects output-a1`),
  since Nautobot drops an outlet's description on import. Both targets read
  the same block. The ten Amphenol 300CB08 panels gain sixteen outlets each
  (`dc-terminal` on the 300CB08, the monitored nrg300CB08-CTRL and -SENS and
  the nrgILS300CB08; `other` labelled `P40` on the connectorized -C and -SC);
  nothing is renamed or removed. Stating `fed-by` or `through` is a minor
  device version, changing one a major. Lint L132 (`fed-by` names a placement
  that exports a power port), L133 (`through` names a bay), L134 (every outlet
  states `fed-by`: a warning, an error at `verified`) and L135 (no two
  outputs name one position: a warning). Design note:
  `docs/power-outlets-design.md`.
- **`optical.trunk`**, an optional component key (roc-ops/Portrayal#246): the
  positions that are a single-faced module's common, network-side end, in
  `front-order`'s item grammar. The DCIM projection puts them on rear ports
  as it puts a rear-face connector there - one per trunk part, named
  `<PART>-1` - so a module whose connectors are all on one face exports at
  last. Front port names keep the faceplate's count, so no published number
  changes meaning; components.json carries the key inside `optical` as it
  carries the rest. The eight path-bearing Smartoptics PPMs state one, and
  `ppm-ad1-1510` and `ppm-ad1-1625` gain their glass from ds-ppm-r4.0's
  signal-flow figures: add and drop written as banded legs off the line port.
  A fibre-map row on a banded leg carries its `band`.
- **New exports for the PPMs.** `exports/fibre-maps/Smartoptics/`, a fibre
  map for each of the eight; front and rear ports in the eight NetBox module
  types and the four DCM Nautobot types. Nautobot cannot put several front
  ports on one rear position, so the two OCU couplers' and two AD1 filters'
  Nautobot types state no ports and say the split is in the NetBox type and
  the fibre map.
- **A fibre adapter that exports nothing is named, not dropped**
  (roc-ops/Portrayal#204). Device and module types record the ones with no
  glass behind them in their comments - 117 on the three DCP chassis, two on
  the DCP-F-A22, and the LC adapters of seven CommScope CH3000 modules - as
  the decision #204 asked for: neither an interface nor a front/rear pair.
  Only `comments` changes on those types. `common/lc-duplex-adapter` leaves NOT_A_DCIM_PORT.
- Lint **L129**, **L130** and **L131**, on components (#246): `optical.trunk`
  is for a single-faced module and names no `unused` position by number
  (L129); every leg of a projected module runs between the front and the
  trunk (L130); and a module with `optical.paths` has a trunk, a rear face or
  `optical.trunk` (L131, an error). L78 checks trunk entries name a connector
  and a position it has, and L79 allows a source to start several paths when
  all but one carry a `band` and no two carry the same one - an add/drop
  filter, not a hidden split.

### Changed
- **BREAKING for DCIM data already imported.** Nautobot module types now
  carry their own module bays, and a module seated only in such a nested bay
  names its ports by the chain of bays above it. Nautobot copies a bay's
  position as written and renders no bay name, so its bays are written plain
  (`mic0` at `mic0`), and the parent goes into the port names of what seats
  there: `{module.parent}/{module}/port-1`, which Nautobot renders to
  `fpc3/mic0/port-1`, the name NetBox gives the same port. 47 Nautobot module
  types gain 95 bays; the Fibrain XCU10's drawer now seats its four adapter
  holders, so its 48 fibre ports are reachable in Nautobot as in NetBox.
  A bay accepting a model that is also seated directly in a chassis bay (the
  A9K MPAs, the 7750 MDA-e family, the MX MIC-3D family, Dell's E3.S carrier;
  35 models in all) is withheld, because that model's ports must keep
  `{module}/x`; 30 bays on 15 carriers, each named in the type's comments,
  wait for position templating upstream (nautobot/nautobot#5823). The renames
  are 934 component templates in 125 Nautobot module types, and every one of
  those types was offered no bay by any earlier Nautobot export, so no data
  imported through these exports holds the old names. Two caveats. A
  module ALREADY INSTALLED from an earlier import keeps the names it was
  created with, and re-importing its type does not update the templates. And
  a renamed type installed by hand directly in a device bay, against its
  `Accepts:` list, renders with the token left in: Nautobot's
  render_name_template leaves a token deeper than the bay chain as written,
  so its ports read `{module.parent}/slot1/x`. NetBox exports and fibre maps
  do not change (roc-ops/Portrayal#765, roc-ops/Portrayal#834).

### Fixed
- DCIM exports: a micro-USB console reaches the device type as a console port,
  `Console (Micro-USB)`, type `usb-micro-b`, beside the RJ45 `Console` the
  panel labels apart from it; and an RJ45 AUX serial port on a chassis is a
  console port named `AUX`, as a card's already was. 96 device types in each
  of `library/exports/netbox` and `nautobot` gain ports (31 devices with a
  micro-USB console, plus the ASR 9001, ASR 9901 and MX80 with AUX), and
  nothing already exported is renamed, retyped or removed. A USB storage or
  service port is still not exported, by the existing rule that a USB data
  port is not a console; every management-cluster port that is not exported is
  now named, with its reason, in `MGMT_NOT_A_DCIM_PORT`, and a test asks the
  exporter about each one (roc-ops/Portrayal#384).

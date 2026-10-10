# Changelog

What a consumer outside this repository can depend on, and every change to it.
That is four things:

- the **manifest format** (`format:` in every file, named by schema **v1**);
- the **published build** under `library/dist/`, whose `devices.json` carries a
  `contract` number;
- the **DCIM exports** under `library/exports/`, which carry no number of their
  own, so a change that re-files data already imported is marked **BREAKING
  for DCIM data already imported**;
- the **addresses** a manifest outside this tree holds: a component major it
  pins (`name@2`), and a lint code it waives.

A number goes up when something a reader depends on is **removed, renamed, or
changes meaning**. Adding a field does not move it: a consumer that ignores a
new key is unaffected, and one that wants it can look.
[docs/format-stability.md](docs/format-stability.md) states the rules in full.

The hardware itself is versioned per device (`device.lock.json` beside each
manifest) and per component (`version:` in each contract), and those versions
are not repeated here, except where a component major is removed: every removal
names the ref that replaces it.

## Unreleased

## 0.2.0 - power, rack furniture and cable lay

What does not move from 0.1.0: manifests are still **`format: 1`** and the
published build is still **`contract: 2`**. No lint code was renumbered or
reused; L125 to L172 are new. What a reader coming from 0.1.0 has to act on
is marked **BREAKING** or **ONE-WAY** in its entry, and every component major
that was removed is under Removed with the ref that replaces it.

The entries were written as each change merged, so some describe a state
that a later change in this release overtook. Such an entry is kept, and a
**Superseded** clause in it says what is true at 0.2.0.

Routed lengths on a saved rack changed in steps, and the entries under
Changed list them out of order. In order they are: through a D-ring
(`@portrayal/kit` 0.5.0), beside a duct (0.6.0), along a bundle's trunk
(0.7.0), round solid bodies and a zero-U PDU (0.11.0), along one manager
(0.12.0), from the plug's reach (0.13.0), at rest on trays and sills
(0.14.0), into a ring through its opening (0.15.0), the per-media end
allowance (0.16.0) and bend room (0.17.0). Each entry measures its change
against the kit before it. None of them reaches a consumer of 0.1.0: the
rack modules and the rack file are new in this release.

The kit versions this section names are versions of `kit/package.json` in
this repository. `@portrayal/kit` on npm is 0.2.0, which has no rack module.
`@portrayal/index` is not on npm at this tag, so `packageDist` and
`?dist=cdn` have no index to read until it is.

### Added
- `components.json` carries the catalogue's derived columns on each entry
  (one entry per component major, one row of `library/components/CATALOGUE.md`):
  `seats`, the number of devices that seat it (the page's `devices` column);
  `composed-by`, the number of other component majors that compose it (the
  page's `in parts` column, the reverse of `parts`); and the contract's
  `interface` and `mates`, beside `conforms`, when it states them. The page
  and the index are counted by the same functions in `components_catalogue.py`.
  Additive; the `contract` number does not move.
- The FS FHD-CMP5DR lacer panel (`fs/fhd-cmp5dr`), the first passive part
  that shares a rack unit with other equipment, and what it needs:
  `chassis.mount: rack-face` (a part bolted to the rail face that projects
  outward; it states `ru`, the units its ears span, and exports
  `u_height: 0`); `chassis.shell: sheet` with `chassis.thickness`, a bent
  sheet-metal body whose views are elevations and which builds in 3D only
  what its parts build (lint L127 holds a sheet to its gauge); and a
  `passive` profile for rack furniture, which owes only its weight. A
  `passive` device is exported to DCIM though it has no interfaces, console
  or bays. Design note: `docs/cable-managers-design.md`.
- Lint L128, on devices and listings: a `part-numbers` key has no stray
  whitespace. Whitespace other than a plain space (NBSP, a tab, a zero-width
  space) and leading or trailing whitespace are errors; a space splitting a
  run of capitals and digits between two hyphens (`9716-32D-O-A C-F-UK`,
  #720) is a warning a device can waive. Keys that mean their spaces, such
  as `AS7535-28XB-O-AC-F V2` and `7750 SR-12 (pre-2016 chassis)`, pass, and
  nothing in the library raises it (roc-ops/Portrayal#731).
- Fibrain's HD adapter holders for LC, and the multimode SC ones: ten LC
  duplex holders (`fibrain/xmi1021ca`, `-da`, `-ha`, `-ga` and `xmi1031ga`
  with 6 adapters; `xmn1021cb`, `-db`, `-hb`, `-gb` and `xmn1031gb` with 12)
  and six SC holders in OM3, OM4 and OM5 (`xmi1041ca`, `-da`, `-ha`;
  `xmn1041cb`, `-db`, `-hb`). The XCU10 gains XCU10-21IC and XCU10-31IC, its
  24-adapter LC and LC/APC variants, and its drawer's slots accept all twenty
  holders. **As with the SC holders, these seat in bays of the drawer's module
  type, which NetBox takes (4.5.7 or later) and Nautobot is not given: none of
  their ports can be placed in Nautobot yet** (roc-ops/Portrayal#834; superseded by
  the Nautobot entry under Changed, which gives the drawer its bays). The 12-port LC
  holders are the first modules to state `optical.front-order` by position:
  their lower row is turned over, and its ports still count left to right.
- `optical.front-order` may name one position of a part (`lc07.2`) as well
  as a part. A duplex adapter turned over, as in the lower row of a
  belly-to-belly holder, has its bore 1 on the other hand, and listing its
  positions in the order they are numbered (`lc07.2, lc07.1`) makes the
  exported front ports and fibre map count along the row. A part named bare
  counts 1 upward as before, so no existing module changes. Lint L78 holds
  such a part to naming every position once, together.
- MRJ21, VHDCI and RJ11 jacks are connector slots, and three cable plugs seat
  in them. `mrj21`, `vhdci` and `rj11` join `spec/schemas/connectors.yaml`, so
  every `std/mrj21@1`, `common/vhdci-receptacle@1` and `common/rj11-jack@1`
  publishes a `kind: connector` slot: nested on the Nokia M48-1GB-XP-TX MDA and
  on the three Oscilloquartz HD cards, and on the Halny HLX-TGV chassis.
  `common/vhdci-receptacle@1` and `common/rj11-jack@1` gain
  their interface, and the RJ11 jack a `mate` point; no drawing changed, and
  the three cards and five devices that carry them take a patch.
  `generic/mrj21-plug@1`, `generic/vhdci-plug@1` and `generic/rj11-plug@1` are
  the straight cable plugs that mate them, each with a 30 mm stub of cable
  sized by `cable-od` and coloured by `jacket-color`. The MRJ21 plug and the
  VHDCI hood are scaled from drawings that dimension neither; see
  `docs/connectors-mrj21-vhdci-rj11-design.md` (#790).
- Ground studs seat a ring lug. `common/ground-lug@1`,
  `common/ground-stud@1` and `juniper/mx-ground-stud@1` each gain
  `interface: terminal-stud` and a `mate` point on the stud axis, on top of
  what the part builds, so every placement of one is a slot of its device
  that offers `generic/ring-lug@1`. The three studs of
  `casa/c40g-ground-studs@1` are now `casa/shelf-ground-stud@1`, composed as
  `stud-tr`, `stud-bl` and `stud-br`, each a nested slot. No drawing changed.
  A placement states `stud-size` (`M4`, `M5`, `M6`, `10-32`, `1/4-20`,
  `1/4 in`) where a document for its device states the size of the stud or
  screw: 68 placements on 31 devices, each with its source in
  `provenance.ground-stud-size`. The 53 devices that place one of the four
  parts take a patch; their DCIM exports change in the drawing version line
  only. The lug is the one nominal lug and is not turned: where it overhangs
  a face, or two lugs on a pair overlap, is recorded in
  `docs/connectors-dc-terminal-design.md`, section 13, with a two-hole lug as
  later work (#789).
- Two more of the Amphenol Network Solutions 300CB08 family, the passive
  connectorized panels: `amphenol-ns/300cb08-sc` (stud inputs) and
  `amphenol-ns/300cb08-c` (horizontal busbar inputs). Each replaces the screw
  terminal outputs with sixteen `amphenol-ns/output-p40@1` receptacles; the -C
  takes its feeds on `amphenol-ns/input-feed-busbar@1`, whose landings stand
  147 mm behind the chassis (superseded: the -C panels under Fixed put them
  38.1 and 95.2 mm behind a 367.0 mm deep panel, #860). Front, top, bottom
  and sides are the 300CB08. In
  the DCIM exports each has two `dc-terminal` power ports, one per feed, and
  its outputs are not exported yet. Superseded: the power outlets entry in
  this section exports them, sixteen outlets labelled `P40` on each (PR
  #849). No existing device or export changes.
- The two monitored panels of the Amphenol Network Solutions 300CB08 family
  with the plain rear: `amphenol-ns/nrg300cb08-ctrl` (integrated nrgSMART
  controller: front display `amphenol-ns/nrg-oled@1`, MGMT and LAN RJ45s,
  RESET) and `amphenol-ns/nrg300cb08-sens` (sensor card, no network jacks).
  Both take the new rear centre `amphenol-ns/nrg-rear-block@1` (alarm headers,
  nrgNET IN and OUT, two temperature probe jacks), which the DCIM exporter
  skips as not a DCIM port. In the DCIM exports the CTRL has two management
  interfaces, `mgmt` and `lan` (100base-tx), and both have two `dc-terminal`
  power ports. No existing device or export changes.
- Fibrain, a new vendor: the XCU10 extendable HD patch panel (`fibrain/xcu`,
  0.5U, 48 SC), with XCU10-51ID and XCU10-41ID as configurations. Its front is
  one captive drawer (`fibrain/xcu-drawer@1`) whose four slots seat the HD
  adapter holders XMI1041GA and XMI1051GA (6 SC, 6 SC/APC), XMN1041GB and
  XMN1051GB (12 SC, 12 SC/APC) or the XBCS0 blind cover. `common/sc-simplex-adapter@1`
  is new: one SC port to a body, with no dust cap seated. These are the first
  parts to use `shape: ring` and `shows` on body pieces. **In the DCIM exports
  the holders seat in bays of the drawer's module type, which NetBox takes
  (4.5.7 or later) and Nautobot is not given: the Nautobot drawer has no bays,
  so the holders and their 48 ports cannot be placed there yet**
  (roc-ops/Portrayal#834; superseded by the Nautobot entry under Changed, which
  gives the drawer its four bays). Nautobot states `u_height: 1` for this
  0.5U panel.
- The explorer edits a part's fields. Selecting a part whose component
  declares `fields:` - a supply's wattage, a latch colour, a filter's channel
  numbers - shows one control per field in the inspector: a list for a
  `choice`, an input otherwise, starting from the value the configuration
  built. A change is written with `setFields`, in 2D and 3D, is kept across a
  view change, goes when the part is swapped out, and is carried in the page's
  location as `fields=<path>~<key>~<value>,...` beside `swap=`. A value the
  field does not take is not written, from the form or from a link. A link
  restores a field only for a part drawn on the view it opens; one set on
  another view is dropped on reload (roc-ops/Portrayal#818).
  `kit/fields.js` gains `fieldRows`, `fieldAccepts`, `encodeFields`,
  `decodeFields` and `drawnField`, and the shell gains `resetField` and
  `applyFields` (#811).
- Barrier terminal blocks seat a lug per pole. `terminal-stud` joins
  `spec/schemas/connectors.yaml` as one nominal connector: a screw or stud
  terminal a lug lands on, claiming no size. The terminal screws of
  `common/dc-terminal-24@1` and `common/dc-terminal-27@1` (1.0.1) are now
  parts of their own, `common/terminal-screw-34@1` and
  `common/terminal-screw-38@1`, composed as `lug-1` to `lug-3`; each presents
  the interface, so each pole is a nested slot (`psu1-input/lug-2`, or
  `psu-1/terminal/lug-2` on a Telco Systems DC supply). The blocks draw
  exactly as before and keep every id. `generic/ring-lug@1` is the one-hole
  insulated ring terminal that seats there, on a 10 mm stub of wire lying in
  the plane of the face; `wire-color` and `barrel-color` paint it. It is a
  nominal lug for 16 to 14 AWG wire, not the lug of any one device. The
  Edgecore CSR180 and CSR200 and the Telco Systems TM-8104 and TM-8106 take a
  patch. See `docs/connectors-dc-terminal-design.md`, section 12.
- Pluggable terminal headers are connector slots, and three screw-clamp plugs
  seat in them. `terminal-508-2`, `terminal-508-5` and `terminal-508-6` join
  `spec/schemas/connectors.yaml`. `common/terminal-header-508-2@1`,
  `common/terminal-header-508-5f@1` and `common/dc-terminal-header-6@1` (1.0.1,
  the five-position header 1.0.2) gain their interface and a `mate` point; no drawing changed, and the
  11 devices that draw one take a patch. Superseded for two of the three
  headers: `@1` of each was removed later in this release, and the majors to
  pin at 0.2.0 are `common/terminal-header-508-2@3` and
  `common/terminal-header-508-5f@2` (under Removed).
  `generic/terminal-508-2-plug@1`,
  `generic/terminal-508-5-plug@1` and `generic/terminal-508-6-plug@1` are the
  plugs that mate them, drawn from the wire side with one 30 mm stub of wire
  per pole and a `wire-1` to `wire-N` point on each. `wire-od` sizes every
  stub, `wire-color` paints every stub and `body-color` paints the body. Each
  stands 10 mm in front of the face its header presents; see
  `docs/connectors-dc-terminal-design.md`. `terminal-508-5` is the
  five-position mating face with or without flanges; the plug drawn is the
  screw-flange form (#789).
- The DC barrel jack is a connector slot, and a barrel plug seats in it. The
  library treats the jack as one nominal connector, `dc-barrel`: barrel
  diameters vary by product and no document held for a device that places one
  states its size. `common/dc-barrel@1` (1.0.1) gains the interface and a
  `mate` point beside `power`; its drawing is unchanged, and the four devices
  that place it take a patch. Each placement now states `input-voltage` and
  `current-max-a` from its device's documents. `generic/dc-barrel-plug@1` is
  drawn at the common 5.5 mm barrel from one manufacturer's drawing, with a
  30 mm stub of cable sized by `cable-od`; it states no rating and claims to
  be no device's own plug (#789).
- A component's body pieces (`body.boxes`) can be round and can carry a
  drawing. `shape: cylinder` or `ring` (with `axis`, and `wall` on a ring)
  builds a round piece in the envelope a box would fill; `shows: [plan]` or
  `[rear]` paints a box piece's top or back with the patch of the part's own
  `faces.plan` or `faces.rear` drawing it covers. `components.json` gains
  `body.drawings` and `body.face` on a part whose pieces show one. Lint L71
  checks the new keys. Nothing existing changes: a piece that states neither
  is the plain box it was.
- The Cisco Nexus 93180YC-EX (`cisco/n9k-c93180yc-ex`): 48 SFP28 and 6 QSFP28
  on the port side; two supplies, four fan modules, console, both management
  ports and USB on the other; port-side intake and port-side exhaust
  configurations. Two new parts seat in it, `cisco/nxa-pac-650w@1` and
  `cisco/nxa-fan-30cfm@1`, each covering both airflow part numbers through a
  latch-colour field.
- The Cisco Catalyst 4948E (`cisco/ws-c4948e`), the front-to-back build: 48
  10/100/1000 RJ-45 and 4 SFP+ on the front with the console and management
  jacks and the status lamps; two supplies and the fan tray on the rear. Two
  new parts seat in it, `cisco/pwr-c49e-300ac-r@1` and `cisco/ws-x4993@1`. Its
  export names ports as IOS does, `GigabitEthernet1/1` to `1/48`,
  `TenGigabitEthernet1/49` to `1/52` and `FastEthernet1`.
- The Smartoptics DCP-1203 (`smartoptics/dcp-1203@1`), three 100/400G
  transponders on one DCP-2 traffic unit: six QSFP28/QSFP-DD combo cages in
  three pairs, odd ports client and even ports line, each with its Tx and Rx
  lamps. The DCP-2 accepts it in both traffic slots and gains a `dcp-1203-x2`
  example configuration.
- A device can name its own interfaces. A top-level `interfaces:` block, in
  the shape a NOS listing's has, says what the maker's own operating system
  calls each port, and the hardware's own DCIM device type uses those names:
  the Nexus exports `Ethernet1/1` to `Ethernet1/54` and one `mgmt0`. An id no
  rule names keeps its faceplate id, and a listing's names still decide that
  listing's document. The lock records the names and asks a major bump when
  one changes; L105 refuses a rule that names nothing the device places.
- Amphenol Network Solutions, a new vendor (`amphenol-ns`, formerly Telect):
  the 300CB08 (`amphenol-ns/300cb08`), a 1RU dual-feed DC circuit breaker
  panel with sixteen plug-in positions, all six faces, and eleven
  `amphenol-ns/` parts. A position takes `amphenol-ns/breaker-1ru@1`, one
  module for every rating from 2 A to 60 A, set per position by its `rating`
  field and printed on its handle; `amphenol-ns/tpa-fuse-holder-307492@1`,
  which carries its fuse as a `fuse-rating` field; or the blanking cover. A
  breaker ships wearing `amphenol-ns/touch-guard-1ru@1`, a separate part
  seated on it that comes off: `spec/schemas/connectors.yaml` gains
  `breaker-1ru-guard`, marked `cover: true`, the first slot that is a cover
  mount and not a connector. It is the first power distribution device:
  `spec/schemas/profiles.yaml` gains a `power` profile, which owes an input
  rating, the panel's own draw and an operating temperature and no
  `performance` or `platform` section, and `spec/schemas/power-roles.yaml`
  gains the class `breaker` under `passive`, for any removable circuit
  protector. In the DCIM exports each feed is one `dc-terminal` power port
  (`input-a`, `input-b`) and each position is a module bay; the sixteen output circuits and
  the alarm contacts are not exported yet. No existing device or export
  changes. Superseded for the outputs: the power outlets entry in this
  section exports them as sixteen `dc-terminal` power outlets (PR #849). The
  alarm contacts are still not exported.
  The family is eleven panels at 0.2.0, seven of them with P40 outputs, and
  each exports sixteen power outlets. An entry in this section that counts
  ten panels, or six with P40 outputs, counts the family before the
  nrgILS300CB08-SC joined it.
- CFP, CFP2, CFP4 and CXP cages offer optics. `generic/cfp-lc@1`,
  `generic/cfp-sc@1`, `generic/cfp-mpo@1`, `generic/cfp2-lc@1`,
  `generic/cfp2-mpo@1`, `generic/cfp4-lc@1`, `generic/cfp4-mpo@1` and
  `generic/cxp-mpo@1` are the
  first parts to mate `cfp`, `cfp2`, `cfp4` and `cxp`, so the `accepts` list
  of every such cage in `components.json`, and in a `<device>.configs.json`
  that seats a card carrying one, goes from empty to these. Each publishes
  its receptacle as a connector slot. `common/cfp-thumbscrew@1` is the knob
  the CFP parts compose, and `std/mpo24-module-receptacle@1` the two-row MPO
  mouth the twenty-four-fibre faces compose. `spec/schemas/standards.yaml`
  gains `cfp-module`, `cfp2-module`, `cfp4-module` and `cxp-module`, each
  with the `head:` envelope its standard gives. No cage contract and no DCIM
  export changes.
  [docs/pluggables-cfp-cxp-design.md](docs/pluggables-cfp-cxp-design.md).
- OSFP and XFP cages offer optics. `generic/osfp-mpo16@1`, `generic/osfp-lc@1`
  and `generic/xfp-lc@1` are the first parts to mate `osfp` and `xfp`, so the
  `accepts` list of every OSFP and XFP cage in `<device>.configs.json` and
  `components.json` goes from empty to these. Each publishes its receptacle
  as a connector slot. `common/osfp-pull-tab@1` is the tab the OSFP parts
  compose. `spec/schemas/standards.yaml` gains `osfp-module` and
  `xfp-module`, each with the `head:` envelope its MSA gives. No cage
  contract and no DCIM export changes.
  [docs/pluggables-osfp-xfp-design.md](docs/pluggables-osfp-xfp-design.md).
- D-subminiature and VGA panel connectors are connector slots, and four hooded
  cable plugs seat on them. `db9`, `hd15`, `da15` and `db25` join
  `spec/schemas/connectors.yaml`, each naming the connector with the gender the
  library draws on a panel (the DE-9 male, the other three female), so every
  `std/db9@1`, `std/vga@1`, `std/da15@1` and `std/db25@1` publishes a
  `kind: connector` slot: on a chassis, on a card seated in a bay, and through
  `common/db9-receptacle@1` and `common/vga-receptacle@1`. No existing part or
  device changed. `generic/db9-plug@1` (female), `generic/hd15-plug@1`,
  `generic/da15-plug@1` and `generic/db25-plug@1` (male) are the cable plugs
  that mate them, drawn from the cable end with their two thumbscrews and a
  30 mm stub of cable sized by `cable-od` and coloured by `jacket-color`. The
  moulded VGA hood takes `hood-color`, blue by default as the port is. Each
  seats with its flange the mating dimension in front of the panel connector;
  see `docs/connectors-dsub-design.md` (#787).
- USB receptacles are connector slots, and three cable plugs seat in them.
  `usb-a`, `micro-usb-b` and `usb-c` join `spec/schemas/connectors.yaml`, so
  every `std/usb-a@1`, `std/micro-usb@1` and `std/usb-c@1` publishes a
  `kind: connector` slot: on a chassis, on a card seated in a bay, and through
  the `common/usb-a@2` and `common/usb-a-bezel@1` bezels. `std/micro-usb@1`
  (1.0.1) gains its interface and a `mate` point; its drawing is unchanged, and
  the 39 devices that draw it take a patch. `generic/usb-a-plug@1`,
  `generic/micro-usb-b-plug@1` and `generic/usb-c-plug@1` are the moulded cable
  plugs that mate them, drawn from the cable end at the largest overmould the
  USB specifications allow, with a 30 mm stub of cable sized by `cable-od` and
  coloured by `jacket-color`. Each seats to the insertion its USB drawing
  gives; see `docs/connectors-usb-design.md`. No receptacle's geometry changed
  (#786).
- AC power inlets are connector slots, and three cord ends seat in them.
  `iec-c14`, `iec-c20` and `saf-d-grid` join `spec/schemas/connectors.yaml`, so
  every `std/c14-inlet@1`, `std/c20-inlet@1` and `std/saf-d-grid@1` publishes a
  `kind: connector` slot, on a chassis and on a supply seated in a bay alike.
  `generic/c13-plug@1`, `generic/c19-plug@1` and `generic/saf-d-grid-plug@1` are
  the moulded cord connectors that mate them, drawn from the cable end with a
  30 mm stub of cord sized by `cable-od` and coloured by `jacket-color`. Each
  seats with its nose on the inlet's modelled cavity floor; see
  `docs/connectors-power-design.md`. No inlet's geometry changed (#785).
- Supermicro, a new vendor: the SuperServer SYS-111E-WR (`supermicro/sys-111e-wr`,
  1U, ten hot-swap 2.5 inch bays, two 860 W supplies), the SYS-111E-FDWTR
  (`supermicro/sys-111e-fdwtr`, 1U short-depth front I/O, two 600 W -48 V DC
  supplies) and its AC sibling the SYS-111E-FWTR (`supermicro/sys-111e-fwtr`,
  with the SYS-111E-FWTR-EU as its `eu` configuration), each with front, rear
  and a top view under a removable cover, and 23 `supermicro/` parts.
- A face's vents show from inside the chassis in 3D. Where an interior well
  (`relief: {walls: inside}`) has a side within 3 mm of a face, that side is
  painted with the face's declared air openings - decor that says `vent:` or
  `pattern: vent`, which the compiled drawing carries as
  `data-aperture="air"` - each in the place it has on the outside. Nothing is
  read off a colour: a dark rect that declares neither stays a plate.
  `dell/r660` and `supermicro/sys-111e-wr` declare their rear vents (a patch
  each). `relief.js` exports `faceFrame`, `wellWallCorners`,
  `wallsAgainstFaces`, `wallUV`, `ventWellWalls` and `WALL_REACH`.
- Supermicro SuperServer SYS-511E-WR (`supermicro/sys-511e-wr`): the 1U WIO
  server with four hot-swap 3.5 inch bays, front, rear and a top view under a
  removable cover, with its tray, control panel and cover parts; the Gold
  Series SKU SYS-511E-WR-01-G2 is its `gold` configuration.
- `supermicro/riser-wio-rhs-x13sew@2` replaces `@1`: slot 3's bracket bay moved
  2.6 mm so the riser plate no longer covers the edge of a card's first cage.
  Both X13SEW risers gain a housing over the bracket flanges in 3D.
- `supermicro/system-board-x13sew@2` replaces `@1`: the board is flat art on
  the floor of one interior well per chassis (`supermicro/interior-sc116b@1`,
  `-sc815b@1`, `-sc515b@1`), so supplies, risers, fans and DIMMs stand in the
  chassis as bodies under the cover and leave it empty when ejected. The fan
  (`supermicro/fan-0163l4@1`) is drawn as the top of its housing, not as
  rotors, and the SYS-111E-WR's five fans are at their photographed positions.
  All four servers gain an air shroud and a supply cage cover under the lid,
  and the X13SEW risers declare their bodies in pieces - bracket arm, riser
  card and a connector for each slot - so seated cards show, plugged in.
- 3D kit (`relief.js` `ejectTravel`): a pulled part's travel limit is never less
  than its own depth plus the margin. From above a 1U chassis the limit was the
  chassis height less 10, 33 mm, and a 40 mm fan or a 31 mm DIMM never came
  clear of the lid. Parts pulled from the front or rear are unaffected unless
  they are within 20 mm of the chassis depth.
- `plan: {rotate: 180}` on a device bay: the plan of a module seated in a
  FRONT bay is turned half a turn in the top view, and the occupants of its own
  bays are offset from the opposite corner. A plan is drawn face-at-the-top, as
  a rear-seated module lies; the first front-I/O server needed the other way.
- NetBox module types carry a module's own bays. A module that seats others -
  a riser with PCIe slots, an MPC with MIC bays - exports them as
  `module-bays`, each named and positioned `{module}/<bay id>`, which NetBox
  fills with the position of the bay the module itself sits in: a card in
  slot 2 of a riser in `riser-primary` names its port
  `riser-primary/slot-2/port-1`. Nothing already imported is renamed. **It
  needs NetBox 4.5.7 or later**: before that the install forms refuse a card
  in a nested bay, and the REST API names its ports after the outer bay alone.
  **The
  Nautobot module types are not given these bays**, so from here the two
  trees under `library/exports/*/module-types` are no longer the same text:
  Nautobot writes a bay's position as given and cannot fill `{module}` in it
  (roc-ops/Portrayal#765). Superseded by the Nautobot entry under Changed:
  most Nautobot module types carry their bays at 0.2.0, written plain, with the
  parent in the port names. The bays that entry lists as withheld (a carrier
  whose modules also seat directly in a chassis) are still not given.
- Five generic optics, a plug and a pull handle: `generic/qsfp-mpo@1` (a QSFP
  with one MPO receptacle), `generic/qsfp-dd-mpo16@1` (a QSFP-DD with one
  MPO-16 receptacle in a Type 2 nose), `generic/qsfp-lc-simplex@1` (a QSFP
  with a single LC bore), `generic/sfp-sc@1` and `generic/sfp-sc-key-up@1` (an
  SFP with an SC receptacle and a bail, key slot down and key slot up),
  `generic/mpo16-plug@1` (the sixteen-fibre MPO plug, key offset, mating
  `mpo16`) and `common/qsfp-dd-pull-tab-type2@1` (the shorter handle of a
  Type 2 QSFP-DD module). `std/mpo-module-receptacle@1` and
  `std/mpo16-module-receptacle@1` draw the MPO mouth as a module carries it,
  with the pinned ferrule, the key notch and one addressable node per fibre. Each optic's receptacle is a connector slot offering its plug and
  dust cap. A new registry entry, `mpo16-plug`. A host's own field default now
  reaches a part it composes when the two defaults differ. See
  [docs/pluggables-mpo-bidi-pon-design.md](docs/pluggables-mpo-bidi-pon-design.md).
- Nokia Lightspan MF-8 (`nokia/lmfs-f`) with its NT board (`nokia/lbnt-a`), 16-port
  Multi-PON LT board (`nokia/lwlt-c`), alarm module (`nokia/lalm-f`), power module
  (`nokia/lpwr-f`), fan module (`nokia/lfan-f`), the LT and NT dummy boards and the
  horizontal front cover; the Nokia XS-010X-R and XS-010XR-P XGS-PON ONTs; and the
  outdoor ONT enclosure 3FE54221AH.
- A device's built-in PON port now exports. A placement that states `pon` with a
  flavour both NetBox and Nautobot define leaves as that interface type; before, an
  ONT's SC/APC uplink exported nothing. This adds a `pon` interface (`xgs-pon`) to
  the four Halny HLX-TGV device types - an addition, so nothing already imported is
  re-filed.
- Lint L76 counts a lamp bound to a jack from another face (`for: rear/lan`), as it
  already counted one drawn beside the jack.
- ReadyLinks GL-12xB-240D (`readylinks/gl-12xb-240d`), the first device to seat
  a BNC jack: twelve ReadyLink ports on `common/bnc-jack@1` (impedance 75) on a new
  GL-x 12-port BNC line card in slot 1, a slot blank in slot 2, and two BNC sync
  jacks on the chassis, modelled from the vendor GLB. New components
  `readylinks/gl-x-lc-12xb@1`, `readylinks/gl-x-lc-blank@1`,
  `common/rocker-switch@1`, `common/dc-terminal-header-6@1` and
  `common/ground-stud@1`. `std/bnc@1` and `common/bnc-jack@1` are no longer
  `unplaced`.
- `chassis.mount` in the device manifest: `rack` (the default), `din-rail`,
  `wall` or `desktop`. Lint L125 warns on a rack device with no `ru` and
  refuses `ru` on a box that is not racked (roc-ops/Portrayal#734).
- `chassis.bevel` in the device manifest: edges named by the two faces that
  meet at them, cut back by `size` mm - one number at 45 degrees, or a pair
  `[a, b]` taking a different amount off each face. A bevelled face's
  `chassis-faceplate` is a `<path>` of the solid's outline, its bevel strips
  are drawn in `chassis-bevels`, and `<device>.configs.json` carries the
  solid's polygons as `chassis.solid` for the 3D viewer (`@portrayal/kit`
  exports `./bevel`). Lint L126 checks the bevel and keeps parts on the flat
  face (roc-ops/Portrayal#735).
- **Cables in the draw.io exports** (roc-ops/Portrayal#728): `rackDiagram`,
  `toDrawio` and `diagram` take `cables` (a rack plan's
  `{id, a: {item, path, view}, b, media, purpose, label, length}`) and write
  each as an edge between two port cells. A cable whose ends are on different
  pages becomes a labelled stub on each; one with an end not drawn is listed in
  a notes comment with the reason. `cableStyle` sets the colours, and
  `rackCables` returns the notes as a list. Without `cables` the output is
  unchanged.
- **An elements file beside every compiled face**:
  `<device>[.<config>].<view>.elements.json` lists each element the face
  draws, by its `path` (or `of` for a projection), with its `id`, `class`,
  `ref`, `media`, `speed`, `group`, `group-role`, `rel-pos`, `states`, `for`
  and `inner`, its box and connection points in the face's millimetres, the bay or cage it
  is seated in, and its `parent` in the Explorer's tree, under a header naming
  the device, configurations, view, viewBox, `source-sha256` and component
  versions. A server can read a face's tree without a DOM or a layout pass.
  The nesting rule moved out of `kit/shell.js` into `faceTree` in
  `@portrayal/kit/swap`, which the Explorer and the build both follow; the
  Explorer's tree is unchanged. Each device's npm package carries its faces'
  elements files. The file is new, so the dist `contract` number is unchanged
  at 2; [docs/format-stability.md](docs/format-stability.md) gives its shape
  (roc-ops/Portrayal#727).
- **Diagram exports in the kit**: `@portrayal/kit/drawio`,
  `@portrayal/kit/omnigraffle` and `@portrayal/kit/zones`, which were written
  for portrayal.dev and are now the kit's own. Each export is the face as a
  picture with one named, connectable shape per port and bay; draw.io gets a
  shape library, a rack elevation or a one-device `.drawio`, and OmniGraffle a
  `.gstencil`. `toDrawio(svgRoot, doc)` and `toGraffle(svgRoot, doc)` export a
  LIVE drawing - optics seated, lamps lit, marks and a crop applied - and leave
  out the ports a crop cuts away. A face whose viewBox does not start at 0,0
  (an optic's, or a crop) now has its draw.io ports where its picture is; they
  were offset by the viewBox origin.
- **Four more SONiC listings** (roc-ops/Portrayal#674): the Celestica DS1000,
  DS2000 and DS3000 and the Edgecore AS4630-54TE (EPS201). SONiC builds for all
  four in sonic-buildimage but its Supported Devices page predates them; the
  build tree is taken as SONiC's list. Port names come from each platform's
  table at the same pinned commit, joined by alias (`Eth33/1` is port 33).
- `npm_packages.py`: the build split into npm packages, one per device
  (`@portrayal/<vendor>-<device>`), one for the component skins and one index
  carrying `packages.json` (device → package and version, and a vendor →
  family → device tree). Each package is versioned from what npm last
  published, and only changed packages are published. Nothing in `dist/`
  changes; see `library/README.md` (roc-ops/Portrayal#528).
- **SONiC listings** (roc-ops/Portrayal#674). The 17 boxes on SONiC's Supported
  Devices and Platforms page that the library models are listed under
  `sonic/`, every one with SONiC port names: each platform's own table in
  sonic-buildimage (`port_config.ini`, or `platform.json` with its breakout
  modes), pinned to one commit and joined to the faceplate by the port's alias
  - which names the front-panel port where `index` does not. `eth0` is the
  management port. Celestica's rows use codenames (DX010, Silverstone,
  Seastone_2) no document here ties to a DS model, so they wait.
- **DNOS listings** (roc-ops/Portrayal#674). The 13 modelled boxes the DNOS CLI
  Reference Guide 26.2 accepts as NCP hardware (`system ncp model`) are listed
  under `drivenets/`, each named as DriveNets sells it - `model: NCP-40C` - and
  exported as `DriveNets/NCP-40C (<SKU>)`, because one NCP name covers boxes
  from several ODMs. A listing may now set `type-name`, a pattern with `{model}`
  and `{sku}`, for exactly that. Six single-speed boxes carry DNOS port names
  (`ge100-0/0/<n>`, `fab-ncp400-0/0/<n>`) for a standalone NCP 0; the
  mixed-speed boxes carry a `dnos-port-names` gap, and management jacks a
  `dnos-management-names` gap. The fabric boxes (NCF-48CD, NCF-64E) wait for a
  document that names their hardware.
- **OcNOS listings for the IP Infusion HCL** (roc-ops/Portrayal#674). Every box
  on the OcNOS 7.0.1 MR Hardware Compatibility List (July 2026) that the
  library models - 42 of 44 - is listed under `ipinfusion/`, with the edition
  that supports it (OcNOS SP or OcNOS DC) as its portfolio line. 14 UfiSpace
  boxes carry OcNOS port names: speed-class prefix (`ge`, `xe`, `ce`, `cd`) and
  one 0-based count across the panel, as IP Infusion's own S9510-30XC
  configuration shows and as the UfiSpace silkscreen already numbers them, with
  `eth0` for management. The rest carry an `ocnos-port-names` gap: Edgecore
  boxes do not all count the same way (the AS7316-26XB restarts per speed
  class), and no 800G prefix is documented.
- The other halves of the AC connectors, for rack PDUs (#933). Two outlet faces:
  `std/c19-outlet@1` (IEC 60320-3 sheet J, from SCHURTER 4710-5; its 3D well
  follows its R5 outline) and `std/nema-5-20r@1` (the T-slot receptacle, from
  Qualtek 739W-X2/30). Two jumper ends, drawn from the cable end like the C13 and
  C19 ones: `generic/c20-plug@1`, which mates the new `iec-c19` interface, and
  `generic/c14-plug@1`, which mates `iec-c13`, the interface `std/c13-outlet@1`
  presents. Four input plug faces: `generic/nema-l6-20p-plug@1`,
  `generic/nema-l5-20p-plug@1`, `generic/nema-5-20p-plug@1` (Leviton catalog
  drawings) and `generic/cs8365c-plug@1` (Hubbell M-6590).
- Registry entries for all eight parts, and the `iec-c19` connector interface.
- DCIM: `iec-60320-c19` and `nema-5-20r` join `OUTLET_TYPES` and `PART_OUTLET`;
  the four input plugs map in `PART_POWER` to `nema-l6-20p`, `nema-l5-20p`,
  `nema-5-20p` and `cs8365c`. Every slug is in both NetBox and Nautobot.
- The four monitored connectorized panels of the same family:
  `amphenol-ns/nrg300cb08-ctrl-c`, `nrg300cb08-ctrl-sc`, `nrg300cb08-sens-c`
  and `nrg300cb08-sens-sc`. Each is the CTRL or SENS front with the -C or -SC
  rear (sixteen `amphenol-ns/output-p40@1` outputs, busbar or stud feeds) and
  `amphenol-ns/nrg-rear-block@1` where the passive panel has its alarm card.
  Their DCIM exports are as the CTRL and SENS. No existing device or export
  changes.
- The Amphenol Network Solutions nrgILS300CB08-SC
  (`amphenol-ns/nrgils300cb08-sc`): the nrgILS300CB08 with the -SC rear,
  vertical stud feeds and sixteen `amphenol-ns/output-p40@1` outputs that
  accept `amphenol-ns/p40-plug@1`, with the nrgILS rear centre block. No figure
  draws this version; it is the ordering line's combination of two modelled
  halves, and says so. In the DCIM exports it has the nrgILS's two management
  interfaces, two `dc-terminal` power ports and sixteen P40 power outlets. No
  existing device or export changes.
- The Amphenol Network Solutions nrgILS300CB08 (`amphenol-ns/nrgils300cb08`),
  the load-shedding member of the 300CB08 family: the nrg300CB08-CTRL front
  on a chassis 42.4 deeper, read off its own bottom view, with the plain
  stud-and-screw rear and a new centre block,
  `amphenol-ns/nrg-ils-rear-block@1` (nrgNET IN and OUT as RJ45s, a probe
  jack, three unnamed headers), which the DCIM exporter skips as not a DCIM
  port. In the DCIM exports it has two management interfaces, `mgmt` and
  `lan` (1000base-t), and two `dc-terminal` power ports. No existing device
  or export changes.
- The P40 output plug, `amphenol-ns/p40-plug@1` (Amphenol PRM0400, 4 mm
  contacts), and the interface it mates, `p40`.
  `amphenol-ns/output-p40@1` presents it, so all sixteen outputs of the
  300CB08-C, 300CB08-SC and the four nrg300CB08 connectorized panels are
  connector slots that accept the plug. The plug is drawn from the wire side
  with a stub per pole (BATT, RTN), sized by `wire-od` and coloured by
  `wire-color`; no panel seats one by default.
- AurCore, a new vendor, with its ten AIS industrial DIN-rail switches (#744,
  #745, #748). They are the first devices to state `chassis.mount: din-rail`
  and `chassis.bevel`: a fanless finned housing, octagonal in section, that
  clips onto a 35 mm rail or screws to a wall. Each has one `base`
  configuration and exports to NetBox and Nautobot with `u_height: 0`.
  - The large housing, 83.8 x 145 x 110: `aurcore/ais4001p` and `ais4001`
    (8 GbE and 4 SFP+), `ais2003p` and `ais2003` (8 GbE and 4 RJ45/SFP combo
    ports, whose copper halves are `copper-9` to `copper-12`), `ais2004p` and
    `ais2004` (8 GbE and 12 SFP).
  - The small housing, 72.1 x 110 x 93: `aurcore/ais2001p` and `ais2001`
    (4 GbE and 2 SFP), `ais2002p` and `ais2002` (8 GbE and 2 SFP). Its console
    jack is on the top face, not the front.
  - A `p` model is the PoE+ build: two lamps to a jack and a 48-57 V feed,
    where the plain model has one lamp and 12-55 V.
  - Fronts are measured from each model's own product photograph. Tops and
    backs are estimates from an angled render, and each manifest says so in
    its gaps.
- The shared parts the AIS switches need, all in `common/` (the vendor has no
  component namespace of its own): `din-clip-ts35@1` (the TS35 rail clip),
  `wall-plate-keyhole-2@1` and `wall-plate-keyhole-2-42@1` (56 and 42 mm
  keyhole plates), `dip-switch-2@1`, `ground-screw-washer@1`, and the two
  pluggable headers, `terminal-header-508-5f` (power) and
  `terminal-header-508-2` (relay). The headers have since taken majors: pin
  `terminal-header-508-5f@2` and `terminal-header-508-2@3`.
- `common/rj45-ganged-link@1`, the ganged RJ45 cell with one lamp, for a jack
  that shows a single LINK/ACT window (#745). It joins the RJ45 family in lint
  and exports as `1000base-t`. Its `lamp-right` skin is for a column turned
  the other way, which keeps the lamp at the top.
- **A routed cable's tight bends are a finding** (`@portrayal/kit` 0.17.0,
  #973; `docs/cable-lay-design.md` section 3.4). `routePath` returns `bends`,
  each corner of the path with less room than the cable's own installed bend
  radius (`ctx.bendOf(cable)`, else its media's), as `{kind: 'tight-bend',
  cable, point, between, at, angle_deg, legs_mm, room_mm, need_mm,
  short_mm}`, and `bendFindings(rack, ctx, nameOf)` gives them rack-wide with
  a sentence. `cornersOf` and `STRAIGHT_DEG` move to `rack/route-path.js`
  (`rack/bundles.js` still exports both), and `cornersOf(points, {share:
  'need'})` shares a leg between its two corners by what each turn uses of
  it, not by halves; the bundle check keeps the halves. `detour` in
  `rack/solids.js` takes `room`. A path point can be `at: 'lead'`.
- The 1RU plug-in breaker (`amphenol-ns/breaker-1ru@1`, 1.1.0) has a `state`:
  `on`, `off` or `tripped` (#808). ON is up, toward the I of the printed I/O
  legend, as the product photograph shows; `off` and `tripped` carry the
  handle 5.8 down its slot, because the Airpax datasheet says a trip puts the
  handle at OFF. The face draws the toggle end-on and the handle is redrawn as
  that 8 by 8 end; the red-over-green mark beside it is redrawn as the printed
  legend it is. The eleven 300CB08-family panels draw their breakers ON as
  before and take a patch.
- `@portrayal/kit` 0.8.0: the bend check for cable bundles (#922,
  `docs/cable-bundles-design.md` section 5.2). With `ctx.bendOf`
  (`loadCableTypes(dist).bendOf`, #919), `bundleCheck` and every bundle
  command's findings check the bundle at each corner of its trunk, and at each
  pathway whose guide states a `radius`, against the largest installed radius
  among the members present there, so one fibre makes a bundle as strict as
  fibre. A corner's room is worked out from its legs, `min(a_in, a_out) /
  tan(theta / 2)`, and marked estimated; a pathway's stated radius is its
  room. Each miss is a warning, never a refusal, naming the place, the room,
  the member that sets the need and how far it falls short. A member with no
  radius is listed as unchecked, never passed. `inspect` of a bundle gives
  `bend: {radius_mm, by, unchecked, points, violations}` where it gave `null`,
  and `cornersOf` and `bendCheck` are exported from
  `@portrayal/kit/rack/bundles`. Cables outside a bundle are not checked.
  Superseded by kit 0.17.0 in this section: `routePath` reports the tight
  bends of every routed cable.
- `@portrayal/kit` 0.9.0: cable bundles in the exports (#923,
  `docs/cable-bundles-design.md` sections 7 and 13). `bundleExports(rack, ctx)`
  in `@portrayal/kit/rack/export-data` gives one record per bundle (number,
  label, members, length, strap count, size, bend, warnings), `bundleNotes`
  one line per bundle with its warnings, and `strapBomRows` the bill of
  materials' one hook-and-loop strap line, every bundle's straps summed.
  draw.io's notes say bundles are drawn there as separate cables.
- `@portrayal/kit` 0.7.0: cable bundles in the rack kit (#921,
  `docs/cable-bundles-design.md`). A rack's optional `bundles` holds cables
  combed into one run along a stored trunk, `{id, number, label, members:
  [{cable, a?, b?}], route, straps?}`; membership lives on the bundle only.
  `bundle.create`, `bundle.add`, `bundle.peel`, `bundle.update` and
  `bundle.remove` make and change them, each one undo step, with `{error}`
  refusals; with the routing context (`ctx.route`) `bundle.create` works the
  trunk out from where its cables run together and refuses a fork, a loop, a
  detour or groups that share nothing by name. `resolveRoute` follows a
  member's bundle and names its `bundle`, `join` and `leave`. A new module,
  `@portrayal/kit/rack/bundles` (with `@portrayal/kit/rack/bundle-route`),
  checks a bundle's size against the smaller of 2.5 in and each opening on
  its trunk (`bundleCheck`, `bundleChecks`, `pathwaysOn`; a duct running up a
  part and a duct beside the rack are estimated from their channel and depth),
  warning and never refusing, and places its straps every 12 in unless it
  says otherwise (`straps`). `inspect`, `describe` and `selectCables` know
  bundles; `BUNDLE_GONE` joins `GONE` and `CABLE_GONE`.
- `parseDoc(input, {notes})` repairs a file's bundles (an id another thing has,
  a member naming no cable, a cable in two bundles, a number used twice) and
  says so in `notes`, one sentence per repair naming its rack;
  `editor.loadDoc(doc, {notes})` returns them first in its `findings`.
- `chassis.full-depth: false` states that a rack device leaves the opposite
  face of its rack units free, and the DCIM export writes it as
  `is_full_depth: false`. A rack device that says nothing keeps the `true` it
  has always exported; this is stated rather than derived from `depth`, so no
  existing export changes. L125 refuses it on a device that is not `rack`
  mounted (#854).
- **Cable managers, pieces 2 to 4: brushes, pass-throughs, guides and lab
  placement** (`docs/cable-managers-design.md` sections 5 to 7).
  A `brush` panel-decor pattern with `bristle: vertical | horizontal` paints
  itself as a solid field, needs no backing rect and is never an air aperture
  (`data-kind="brush-field"`, `data-bristle`). On a sheet body a sunk decor now
  builds a plate at that depth with no walls, as a well does, which is how a
  brush is an opaque slab in 3D.
  `passes:` on a view declares where cables cross the face, each
  `{id, at, size, shape: rect | obround, cover: open | brush}`, compiled to
  invisible `data-class="pass"` outlines in a `--passes` group. Lint L136: a
  pass lies inside its face and overlaps no component but a well that holds it
  whole. Lint L137: a pass covered by a brush has a brush drawn over it, and a
  brush over a pass belongs to one whose cover is `brush`.
  `guide: {kind: ring, aperture: {w, h}, run}` on a component contract, and
  `guides:` (`kind: duct`, with `finger-pitch` and `finger-gap`) on a device
  view, compile to `data-guide*` attributes and an unpainted
  `data-class="guide"` rect; `components.json` carries a contract's `guide`.
  Lint L138: a ring's opening fits inside its part, seen along its run, and a
  duct lies inside its view with a gap less than its pitch.
  Nothing consumes passes or guides yet, and the DCIM exports ignore both; the
  device lock fingerprints them only where they are declared. Superseded for
  the first half: `rack.json` lists each device's guides and passes, and
  `@portrayal/kit/rack/route` routes cables through them. At 0.2.0, 30 devices
  declare at least one: 18 state passes, 24 a duct guide, and 6 place a ring
  that carries a guide. The DCIM exports still ignore both.
  `attrs.performance.cable-capacity` and `cable-capacity-basis` hold the
  vendor's one capacity figure per manager with its cable and fill basis
  (decision 9).
  A lab placement of a `rack-face` device takes `face` (`front` or `rear`)
  and is placed `on` a host placement at its `unit` (from 1 at the host's
  bottom unit), or at a rack unit by `ru`. Labs have a schema,
  `spec/schemas/lab.schema.json` (its `$id` is
  `https://portrayal.dev/schemas/v1/lab.schema.json`), checked by lint (L1)
  and by the build, and five rules: L139 (refs, ids and `on` resolve), L140
  (`face`/`on`/`unit` only on a rack-face part, placed by `on` or `ru` and
  not both), L141 (the host is a rack device and `unit` is within it), L142
  (everything fits the rack, no two rack devices share a unit, no two
  rack-face parts claim one unit on one face), all errors, and L143, a
  warning naming the host behind a rack-face part placed by `ru`.
  `labs_index.py` will not write a lab that fails L1 or L139-L142.
  `roadm-ring-demo` passes all of them. Every `labs.json` placement keeps its
  keys and gains its resolved `ru`, `face`, `mount`, `host` and `unit`; new
  fields only, `contract` stays at 2, and a site that reads none of them still
  draws a rack-face part on its unit.
  Two devices: `fs/cmh-4drb1u`, the FS CMH-4DRB1U (#68690), a 1U sheet tray
  with four steel D-rings and a brush strip behind five windows, from the
  vendor's dimensioned front and side views, with `fs/cmh-4drb1u-panel@1`,
  `-ring@1`, `-end@1` and `-flange@1`; and `fs/cmh-sfd1u`, the FS CMH-SFD1U
  (#29038), a 1U ABS finger duct built hollow as a sheet body: the base
  plate as the well (`fs/cmh-sfd1u-base@1`), two rows of thirteen fingers
  standing in it (`fs/cmh-sfd1u-finger@1`, `-finger-end@1`) with twelve
  gaps a side at 34.1 mm, and the cover across their tips
  (`fs/cmh-sfd1u-cover@1`), which comes off to open the channel; the channel
  and its ends are open, and a `duct` guide declares it.
- Solid bodies and the `crosses-body` finding, step 2 of the cable lay
  (#949; `docs/cable-lay-design.md` section 1). `rack.json` gains `solids`
  for a sheet part and for a zero-U part that carries a lane, derived by
  `rack_index.py` (through the new `rack_solids.py`) from the compiled faces of
  its default configuration and never stated in a manifest: a sheet part is
  its plates (the floor of each well and each node that stands proud of it;
  never a ring, never drawn decor, and never anything inside a duct's
  footprint or mounted on a duct); a lane duct is what is left, its walls and
  back. Each box is `{part, box: {x, y, z, w, h, d}, holes?: [{via, box,
  size}]}`, x from the device's left as seen from its front, y up from its
  bottom, z back from its front; a hole is a declared pass-through. Any other
  device carries none and is its envelope; a device with cable space inside
  its envelope (the FHD enclosures) waits for step 6 of the note. The
  FHD-CMP5DR and the FS D-ring panels, finger ducts and vertical ducts gain
  `solids`. `format` stays 1.
- `@portrayal/kit` 0.11.0: a new module, `@portrayal/kit/rack/solids`
  (`solidsOf`, `legCrossings`, `detour`, `CLEAR`), and `bodyFindings` in
  `rack/route.js`. `routePath` returns `crossings` and `detours`; `inspect` of
  a cable returns `route.crosses`; `describe` with a route context adds a line
  "Findings: N cables cross a body."; `cableScheduleRows` takes `{bodies}` and
  writes each finding's sentence into its cable's notes. A cable crosses a body
  only through a ring, a duct, or a pass-through whose smaller side fits its
  diameter (`ctx.diameterOf`, else its media's); a tie slot is never an
  opening, and a cable lying against a plate (its centre line a radius
  outside it, on either face) is not crossing it. The finding warns and never
  refuses.
- **Trays: a floor a cable lies on** (#949, `docs/cable-lay-design.md`
  section 2). A component contract declares `tray:` (its `floor`
  rectangles, the `height` of the floor's top above the bottom of the
  envelope, `lip`, `run`, the tie slots cut in it as `ties`, and `slack`,
  `area` or a `spool`), so every placement of the part carries it; a device
  plan (its top view, and no other) declares `trays:` by id. Each compiles to unpainted
  `data-class="tray"` and `data-class="tie"` rects, and `rack.json` carries
  each device's `trays` in the frame of its `solids`, with the openings of the
  rings standing on the floor. A route names a tray by its id, as it names a
  ring. L170 holds a floor inside its part or view, each tie slot on a floor,
  a tray's id to one pathway, its height to the depth of its well, and its
  ties to the slots the device draws on its bottom view. The schema's
  recorded shape is re-recorded: the component and device schemas now accept
  `tray` and `trays`.
- **A ring places its opening**: `guide` gains `depth` (along the run),
  `sill` (from the base it stands on to the lowest inside edge of the
  opening) and `aperture.at` (the opening's corner on the drawing). They
  compile to `data-guide-depth`, `data-guide-sill` and
  `data-guide-aperture-at`. L138 holds each inside the part.
- **fs/fhd-cmp5dr-tray@1 1.1.0** states its tray: the strip and its two arms,
  3.0 mm up the envelope, no lip, the sixteen slots as ties, slack as area.
  **fs/d-ring-snap-in@1 1.2.0** states its opening: 6.8 mm along the tray, its
  sill 5.6 mm above the floor (read off the ring-profile view, where 2 mm was
  estimated before), its corner at 12.75, 5.8. **fs/fhd-cmp5dr 1.1.0**.
- `cable-types.json` in the published build: named cable types (OM3, OM4,
  OM5, OS2 and its G.657.A1 and A2 cords, Cat 6 and Cat 6A U/UTP and F/UTP
  patch cords, passive DAC by gauge, AOC, and C13 and C19 power cords named
  by their cord), each with its media, a typical outside diameter and a
  minimum bend radius `{installed, loaded}` as a fixed figure or a multiple
  of the diameter, marked standard or convention, with its source. The
  source table is `spec/schemas/cable-types.yaml`. The bare type ids are the
  Rack Builder's cable media, so a cable's media names its type. The kit's
  new `@portrayal/kit/rack/cable-types` resolves a type's installed radius in
  millimetres (`radiusMm`, `installedRadiusMm`, `bendLookup`) and loads the
  file (`loadCableTypes`). A new file, so `contract` stays 2 (#919).
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
- The Dell PowerEdge R660 (`dell/r660`, `draft`), a 16th-generation 1U
  two-socket server, 434.0 x 42.8 x 773.5 (#721):
  - Five fronts as variant views: ten 2.5 inch bays (`front`), eight with a
    Smart Flow vent (`front-sff8sf`), no backplane (`front-nobp`), and
    sixteen or fourteen EDSFF E3.S (`front-e3s16`, `front-e3s14`).
  - A rear whose riser band takes riser configurations 0 to 9, and a top
    view of the interior into which seated supplies, risers, cards and front
    drives project. The bottom and sides are estimates.
  - 42 orderable configurations, named `<front>-rc<n>-<risers>`, and four
    examples. Its NetBox and Nautobot device types are named
    `PowerEdge R660 <configuration>`.
  - The riser slots accept the cards the R740xd slots accept: the generic
    brackets and cards and the NVIDIA ConnectX adapters, and on the
    full-height risers 1P and 4P the UfiSpace N3100-4C.
- The `dell/` parts the R660 needs, 71 component majors at 0.2.0, among
  them: the 60 mm AC supplies
  (`dell/psu-700w-ac-60mm@1`, `-800w-`, `-1100w-`, `-1400w-`); six OCP NIC
  3.0 cards and a blank (`dell/ocp3-*`); the LOM card, the MIC card and the
  rear I/O board; the BOSS-N1 module, its M.2 carrier and blank; the E3.S
  carrier, blank and fillers; twelve 16G risers (`dell/riser-1p-16g` to
  `riser-4p-16g`) and the cages they compose; the interior plan parts; and
  the 1U 16G bezel, drawn fitted.
- `std/drive-e3s@1` and the `drive-e3s` standard in
  `spec/schemas/standards.yaml`: the EDSFF E3.S drive, 76.0 x 7.5 x 112.75,
  which the E3.S bays accept beside `dell/e3s-carrier@1` (#721).
- **common/pan-screw-m5@1**, an ISO 7045 M5 cross-recessed pan head, 9.5 across
  and 3.5 high, drawn where a document shows one (#971).
- `chassis.ears` may be an object as well as the string `behind` (#906):
  `{behind?, h?, y?, positions: [{name, label?, at?, default?, racks?,
  part?: {kit, part}}]}`, where `name` is `flush`, `recessed`, `mid`, `rear`
  or `proud` and `at` is millimetres from the faceplate front back to the ear
  plane. `chassis.kits` lists the rail kits a device takes:
  `[{ref, supply: in-box|optional, variant?: reversed, depth?: {config,
  range}}]`. Both are optional, for a rack device only (L125), and documented
  in `docs/format-stability.md`. No device states either yet. Superseded
  for `chassis.ears`: four devices state it at 0.2.0, `eaton/pdumh20net`,
  `fs/fans1u2f`, `fs/fans1u4f` and `fs/uscmh-sfdabsb2u`. No device lists a
  kit, and no `kind: kit` contract is in the library.
- Lint L160 to L163 check them: at most one default position; each listed kit
  ref is a `kind: kit`, listed once; a position's `{kit, part}` names a listed
  kit and one of its part ids; a `depth` override names a configuration of the
  kit, in that configuration's shape, with min below max.
- A "Rack ears" toggle in the kit's Explorer (#909), off by default and shown
  only for a device that gets a generic ear. It turns the generic L-bracket
  ear on in 3D (`viewer.setEars`) and in 2D, where the published face has no
  ears and the kit draws them as an overlay. The choice is remembered per
  viewer, not written into the page's location. Ears built into a face are
  part of the drawing and always shown.
- `@portrayal/kit/ears2d` (kit 0.9.0, the version that also carries the bundle
  exports of #923; kit 0.8.0 is the bend check of #922 alone): `drawEars` and
  `clearEars` draw the generic ear over a published face as
  `render.py --with ears` draws it (the same shapes, ids and colours, and the
  viewBox grown to hold them), from
  `earPlan`, the plan the 3D viewer builds. The overlay is not a part: it
  carries no `data-path`, takes no pointer events, and an export of the live
  drawing carries it as picture. relief.js `EAR` gains `EDGE`, the outline
  colour ears.py draws with.
- `chassis.ears.color` (optional, additive): the colour the generic ear is
  drawn in. configs.json publishes it in `ears` where it is stated, and the
  plan from ears.py and relief.js `genericEars` carries it as `color`.
  devicelock hashes it with the rest of `ears` as chassis surface, so stating
  it is a patch.
- The Eaton EVMA8365X, a Rack PDU G4 managed (0U, 41U, 1829 x 52 x 65 mm): a
  CS8365C cord on a 208 V delta input (40 A, 50 A plug, 14.4 kW), 42 outlets (24
  C13, 18 C39) in six sections A to F, a 20 A two-pole breaker per section with its
  `lines` from the drawing's one-line diagram (A and D on L1-L2, B and E on L2-L3,
  C and F on L3-L1), the eNMC network module, and two mounting buttons 124.0 from
  the cord end at the 1555.8 pitch. Its capability is `metering-scope: outlet` and
  `outlet-switching: true`, so its class is `managed` and every outlet declares the
  `[on, off]` states (#934, docs/pdu-model-design.md section 9.1).
- `eaton/g4-outlet-led@1`, the G4 outlet status lamp, placed beside each outlet
  with `for:`; the device states its `on` green and `off` red. A lamp with no state
  set draws unlit.
- `eaton/g4-cord-cs8365c@1`, the G4 fixed input cord with a CS8365C plug, exported
  as a `cs8365c` power port.
- `eaton/evmi2130x`, the Eaton Rack PDU G4 metered input EVMI2130X and the first
  rack PDU in the library: a 0U strip mounted `rack-side`, a fixed NEMA L21-30P
  cord, 42 outlets (24 C13, 18 Eaton C39) in six colour-coded sections, three
  20 A two-pole breakers and a hot-swappable network module. Drawn standing,
  cord end down, from Eaton drawing 9001-22301.
- `std/c13-outlet@1`, the IEC C13 outlet face a PDU moulds (a well a C14 shroud
  enters, with the nose standing in it), and its `c13-outlet` entry in the
  standards registry.
- Six Eaton parts: `eaton/c39-outlet@1` (the proprietary C13/C19 combination
  outlet), `eaton/g4-outlet-labels@1` (section colour and outlet numbers are
  fields), `eaton/g4-breaker-20a-2p@1`, `eaton/g4-mounting-button@1`,
  `eaton/g4-cord-l21-30p@1` and the network module `eaton/g4-enmc@1`.
- `eaton` in the vendor registry.
- The DCIM export writes AC power outlets: `iec-60320-c13` and `eaton-c39` join
  `OUTLET_TYPES`, both in NetBox and Nautobot, and the PDU's cord exports as a
  `nema-l21-30p` power port. No outlet states `feed_leg`: every outlet on the
  EVMI2130X is line to line.
- A device's own `interfaces:` rules now name its power outlets as they name its
  interfaces, so the EVMI2130X's outlets export as A1 to C42, as the unit prints
  them. An outlet no rule names keeps its placement id, so no other device's
  export changes.
- `eaton/pdumh20net`, the Eaton Tripp Lite series switched PDU PDUMH20NET: a
  1U horizontal rack PDU with 16 NEMA 5-15/20R outlets, eight on the front and
  eight on the rear, named 1 to 16 as printed, each `fed-by` the fixed L5-20P
  input cord and each with a lamp bound to it by `for:`. Class
  `switched-metered-input`; every outlet declares `[on, off]`. The WEBCARDLX
  network card sits in a bay, the two-digit load meter on the front, and the
  ground screw and the factory DE-9 on the rear. The bolt-on brackets are
  `chassis.ears` with flush (default), recessed and rear positions. No drawing
  exists: every position is read off the two straight-on Eaton photographs,
  with the scale proved on the DE-9's standoffs and the outlet faces.
- Three Eaton parts for it: `eaton/webcardlx@1` (the network card module),
  `eaton/tripplite-ammeter@1` (the two-digit load meter) and
  `eaton/tripplite-cord-l5-20p@1` (the fixed input cord, exported as a
  `nema-l5-20p` power port).
- `eaton/pdumv20hvnetlx`, the Eaton Tripp Lite series switched PDU
  PDUMV20HVNETLX and the library's first switched rack PDU: a 0U strip mounted
  `rack-side`, a C20 inlet on the face (the detachable L6-20P cord is not
  drawn), 24 outlets (20 C13, 4 C19) in two load banks of twelve named 1 to 24
  as printed, a lamp bound to each outlet with `for:`, a two-digit load meter,
  the LX Platform interface (10/100 Ethernet, an RJ45 console, USB-A) and two
  toolless mounting buttons that publish `mount-points` 1556 apart. Class
  `switched-metered-branch`; every outlet declares `[on, off]`. Drawn standing,
  from the Tripp Lite submittal drawing 17-08-067. The two bank breakers are
  not placed: no held source shows where they are (a `breaker-positions` gap).
- Three Eaton parts for the Tripp Lite series: `eaton/tripplite-led@1` (the
  round lamp window beside each outlet), `eaton/tripplite-mounting-button@1`
  (mates `pdu-button`) and `eaton/tripplite-load-meter@1` (two seven-segment
  digits and the Select / Rotate button).
- FS.com blanking panels: FHU-BPS-1U-10, FHU-BPS-2U and FHU-BPS-4U (screw-on
  steel), FHU-BPSTL-1U-10, FHU-BPSTL-2U and FHU-BPSTL-4U (tool-less steel with
  ABS clips, the new `fs/bpstl-clip@1`), FHU-BPA-1U-10 (ABS, pegs and magnets)
  and FHU-BPAD-2U and FHU-BPAD-4U (ABS, wave-ribbed, snappable). Each is drawn
  as the whole plate, 482.6 mm (482 for the BPA), with its slots or clips.
- FS.com rack fans: FANP3U3F (3U panel, three fans behind stamped guards, a
  rocker switch, front-to-back airflow) and the FANS1U2F and FANS1U4F 1U fan
  trays, each with the new `fs/fan-temp-controller@1` (two-digit display,
  LOAD and SET lamps, four keys). All three take power through the new
  `fs/fan-cord-5-15p@1`, which exports as a `nema-5-15p` power port.
- FS.com cantilever shelves FS-CFS-1U, IWEP1U350 and IWEP1U550 as sheet bodies:
  a vented floor, side walls to their profile, a rear lip on the IWEP, and the
  built-in ears drawn on the full rack-width face. Each states its usable
  surface and static load in `attrs.physical`.
- FS.com DIN rail brackets DINRAIL2U and DINRAIL4U: two side brackets with
  built-in ears, a rail panel and a 400 mm TS35 x 7.5 rail
  (`fs/din-rail-ts35-400@1`), with the rail's profile, length, height and
  setback range in `attrs.physical`.
- `fs/cmh-sfd2u` 0.1.0, the FS CMH-SFD2U 2U single-sided ABS finger duct
  (#29039): the CMH-SFD1U fingers on an 86.5 mm base well with two 75 x 37.5
  pass-through holes, and its own pullable cover. Hollow, not full depth,
  Cat6 capacity 124 at 100% fill. New parts `fs/cmh-sfd2u-base@1` and
  `fs/cmh-sfd2u-cover@1`.
- `fs/cmh-dfd1u` 0.1.1, the FS CMH-DFD1U 1U dual-sided ABS finger duct
  (#29040), 174 mm deep: the four `fs/cmh-sfd1u` parts on the front view and
  again on the rear, two channels and two covers that pull separately, the
  joined bases between them closed by sunk plates. Not full depth: it bolts
  to the front rails and at 174 mm does not reach the rear rails. Cat6
  capacity 96 at 100% fill across both channels.
- `fs/uscmh-sfdabs1u`, `fs/uscmh-sfdabs2u` and `fs/uscmh-sfdabsb1u` 0.1.0,
  the FS USCMH ABS finger ducts (#317015, #317017, #317023): nine fingers a
  row on a 53.9 mm pitch, a hinged cover that pulls, pass-through windows,
  and the ribbed base behind the ears drawn as a straight box. Depths are the
  drawings' 97.0, 107.0 and 162.83 mm; the product selector's 71 and 127 mm
  for the 2U and the B1U are the projection in front of the ears. FS states
  no weight or cable capacity for this line, and each device records both as
  vendor-silent gaps. New parts `fs/uscmh-sfdabs1u-base@1`, `-cover@1`,
  `-finger@1`, `fs/uscmh-sfdabs2u-base@1`, `-cover@1`,
  `fs/uscmh-sfdabsb1u-base@1`, `-cover@1` and `-finger@1`.
- Four FS 1U D-ring cable managers, each a flat steel panel between the ear folds
  with its rings standing out of it, built as a sheet body so that the rings are open
  loops you can see between: `fs/cmh-5dr1u` (five detachable polycarbonate rings,
  `fs/cmh-5dr1u-ring@1`), `fs/uscmh-5dr1u` (five polycarbonate frames,
  `fs/uscmh-5dr1u-ring@1`, under a cover, `fs/uscmh-5dr1u-cover@1`, that the explorer
  can pull, and four windows through the panel), `fs/cmh-5dr1u-n` (five steel rings,
  `fs/cmh-5dr1u-n-ring@1`) and `fs/cmh-6dr1u` (four of the same steel rings). Every
  ring carries a `ring` guide. Each device states its cable capacity and is not full
  depth. The two end rings of the CMH-6DR1U stand outside the rack's width, beyond
  the ears, and are not drawn; the device records them.
- Six FS ABS high-density finger ducts, built hollow from their datasheet drawings, the
  only pictures FS publishes of them: `fs/cmh-uhd-sfdabs1u`, `fs/cmh-uhd-sfdabs2u` and
  `fs/cmh-uhd-sfdabs3u` (175 mm deep), `fs/cmh-hd-sfdabs3u` and `fs/cmh-hd-sfdabs4u`
  (112 mm deep), each a back plate with pass-through windows, two walls of ten T-shaped
  fingers and a hinged cover the explorer can pull; and `fs/cmh-bs-dfdabs2u`, a 2U
  dual-sided duct with a channel, fingers and a pullable cover on each side of a shared
  spine. Each states its cable capacity, `full-depth: false` and a vendor-silent weight.
  Where the drawing dimensions a cover taller than the rack unit, the device is that
  tall: `fs/cmh-uhd-sfdabs1u` 0.1.0 is 52 mm high over its 44 mm ears and
  `fs/cmh-bs-dfdabs2u` 0.1.0 is 93.5 mm over its 87 mm ears, the covers overhanging the
  units above and below; `ru` stays 1 and 2.
  The HD and UHD lines share one finger part each, `fs/cmh-hd-sfdabs-finger@1` and
  `fs/cmh-uhd-sfdabs-finger@1`; the other new parts are per model.
- The FS steel finger ducts, five horizontal cable managers built hollow like
  `fs/cmh-sfd1u`: a sheet body whose backbone is the floor of a well, two rows
  of fingers standing `in:` it, and a cover that can be pulled.
  `fs/cmh-sfds1u` (1U, cover 51 mm high), `fs/cmh-sfds2u` (2U) and
  `fs/cmh-bs-sfds1u` (1U, steel channel with ABS fingers) are single-sided and
  state `full-depth: false`. `fs/cmh-dfds1u` (1U, covers 57.8 mm high) and
  `fs/cmh-dfds2u` (2U) are dual-sided, with a channel and a cover facing the
  front and another facing the rear; they bolt to the front rails and, at 230.6
  and 232 mm, do not reach the rear rails, so they too state `full-depth: false`. Each brings its own
  base, finger and cover components (`fs/<model>-base@1`, `-finger@1`,
  `-cover@1`, and `fs/cmh-bs-sfds1u-finger-end@1`). Only CMH-BS-SFDS1U has a
  stated cable capacity; the other four carry a `vendor-silent` gap for it.
- A generic L-bracket rack ear, drawn from `chassis.ears` (#909): a flange each
  side reaching from the body to the 482.6 mm rack face, with a slot over each
  rail hole, and a 30 mm leg back along the body, `ears.h` tall and `ears.y`
  up (the chassis's height, and 0, where they are absent), its flange on the
  default position's `at`. `render.py --with ears` draws it on all six faces as
  `ear-left` and `ear-right`; the kit's viewer builds it in 3D with
  `createViewer(el, {ears: true})` or `viewer.setEars(true)`, from relief.js
  `genericEars`, and a GLB taken then carries it. A device that is not a
  `rack` device, states `ears: behind`, has a front as wide as the rack face or
  still places `common/rack-ear@1` gets none in 2D. The default build draws no
  ears, so no published face, export or device lock changes.
- Lint L164 warns when `chassis.ears` `y + h` is above the chassis, and L165
  when two ear positions have the same `name` and `label`.
- `common/ground-screw-m4@1` (ISO 7045 M4 pan head, 8.0 across, 3.1 high) and
  `common/ground-stud-pair-5-8-m4@1`, two of them on 5/8 in. (15.875) centres
  presenting `stud-pair-5-8`, so a `generic/two-hole-lug-5-8@1` seats across an
  M4 grounding pair (#830).
- `common/ground-screw@1`: the stud, washer and cap of `common/ground-lug@1`
  without its earth symbol, presenting `terminal-stud` at the same height, for
  the second screw of an unsized two-screw landing whose chassis prints one
  symbol (#830).
- `nokia/sr-1-dc-stud@1` and `nokia/sr-1-dc-pole@1`: one 10-32 stud of the
  7750 SR-1 DC terminal block, and a pole of two of them on 5/8 in. centres
  presenting `stud-pair-5-8` (#828). `nokia/sr-1-dc-terminal-block@1` (1.1.0)
  composes four poles, `a-neg`, `a-rtn`, `b-neg` and `b-rtn`, so a two-hole lug
  seats across each pole of the SR-1 DC (0.1.3) and a ring lug on each stud.
  The 45-degree lug the guide names is not built; the straight one stands in.
- A two-hole lug across a pair of studs (#828). Three connector interfaces,
  `stud-pair-5-8`, `stud-pair-3-4` and `stud-pair-1`, each spanning two
  `terminal-stud` seats at the pitch in its name (15.875, 19.05, 25.4), and a
  lug for each, `generic/two-hole-lug-5-8@1`, `-3-4@1` and `-1@1`, drawn
  across with the wire leaving along the pair. Pair hosts compose two studs at
  the pitch and present the pair at their midpoint, at the top of the studs:
  `juniper/mx-ground-stud-pair-5-8@1`, `juniper/mx-ground-stud-pair-3-4@1`,
  `common/ground-stud-pair-5-8-m6@1`, `-5-8-1-4@1`, `-3-4-1-4@1` and
  `-1-1-4@1`. A pair and its two studs are one level or the other (L115); each
  stud still takes the ring lug alone. docs/connectors-dc-terminal-design.md
  section 13.7.
- Sized ground screws (#830): `common/ground-screw-m6@1` (ISO 7045 pan head)
  and `common/ground-screw-1-4@1` (ASME B18.6.3 pan head), used only inside the
  pair hosts. `common/ground-lug@1` stays the nominal, unsized ground screw.
- HPE, a new vendor, with the ProLiant DL160 Gen10 (`hpe/dl160-gen10`), a 1U
  two-socket server (#759). It has two fronts as variant views, four LFF bays
  (`front`) and eight SFF bays with a media bay (`front-sff8`), over one
  rear, and a top view of the interior. Its seven configurations are `base`,
  the orderable `sff8`, and five examples. The NetBox and Nautobot device
  types are named for the two chassis option numbers, `878972-B21` and
  `878973-B21`.
- The `hpe/` component namespace, 42 parts at 0.2.0 (#759, #761, #778, #780):
  - drive carriers and blanks for both fronts, the 500 W and 800 W Flex Slot
    supplies and their blank, the fan, heatsink, system board and access
    panel;
  - the primary and secondary risers, `hpe/riser-primary-dl160@1` and
    `hpe/riser-secondary-dl160@1`, whose PCIe slots are bays behind a
    standard bracket window, so the cards the library already has seat in
    them;
  - the FlexibleLOM riser `hpe/riser-flom-dl160@1`, a second occupant of the
    primary riser bay, whose `flom` bay accepts `hpe/flom-blank@1` and twelve
    FlexibleLOM adapters, each named for its option number
    (`hpe/flom-817749-b21@1` is the 640FLR-SFP28);
  - `hpe/riser-blank-primary-dl160@1`, the plate fitted where no primary
    riser is ordered, seated by the `lff4-no-riser` example;
  - three Media Module adapters, the serial port option and their blanks.
    The adapters were renamed to their option numbers before any release, as
    the HPE entry under Removed records (#760).
- `common/rj45-eth-pinside@1`: a lamped RJ45 whose two lamps are in the side
  walls at the pin end, away from the latch notch (#781). It is
  `common/rj45-eth@1` with the lamps at the other end. It joins the RJ45
  family in lint and exports as `1000base-t` unless the placement states a
  speed. Three HPE adapters use it, the 562FLR-T, 535FLR-T and 533FLR-T.
- `kind: kit`, a third kind of component contract, for a rail, bracket or
  slide kit (#905). A kit has no `class`, no `size` and no skin, and admits
  only `format`, `kind`, `name`, `version`, `description`, `provenance`,
  `unplaced`, `superseded-by` and the kit keys: `motion`, `travel`, `install`,
  `parts` (`{ref, id, count}`), `configurations` (`{id, racks, parts, depth,
  preset, tolerance, rail-depth}`, `depth` one `[min, max]` or one per hole
  type) and `accessories` (`{kind: cma|srb, ref, rail-depth, sides}`). A
  component or module still requires `class` and `size` and takes none of
  them. No kit is in the library yet.
- Lint L155 to L159 check a kit: each part ref resolves to a component that is
  not a kit and part ids are distinct; a configuration names only the kit's
  own part ids and has an id of its own; every depth range has min below max;
  `travel` only with `motion: sliding`; each accessory ref resolves to a
  component that is not a kit.
- `library/dist/kits.json`: every kit as its contract states it, written by
  `components_index.py` on every build (`{"kits": []}` while there is none). A
  kit is never an entry of `components.json`, and the component catalogue lists
  kits in a table of their own, outside its component count. The keys are
  documented in `docs/format-stability.md`.
- The kit device picker offers the NOS vendors and the boxes each lists
  (#711). `createDevicePicker` in `@portrayal/kit/devsel` takes two optional
  inputs, `listings` (the build `listings.json`) and `listing` (the entry to
  start on). Choosing a listing loads the drawing of the hardware it lists
  and keeps the listing as the selection. Nothing an existing caller uses
  changes shape: `onchange(name)` still receives the device name, with
  `{listing}` as a second argument, and `picker.value` is still the device
  name, beside the new `picker.listing`. `pickerEntries(devices, listings)`
  is exported, and gives the entries the picker shows. The explorer writes
  `?listing=<ns>/<id>` beside `?device=`, so a reload lands on the same entry.
- `@portrayal/kit/nosnames`, a new export: what a listing says its NOS calls
  each port (#719). `listingNames(listing)` and `nosNameFor(listing, path)`
  give the names, `expandName(pattern, n)` expands one pattern, and
  `breakoutNote(breakout, n)` words a breakout. It is the grammar of the DCIM
  export, ported, and a test holds the two to identical names over every
  listing in the build. With a listing chosen, the explorer inspector shows
  the NOS name of a selected port. Only the top-level ports of a device are
  looked up, and a port the listing does not name is never guessed: the
  inspector names the listing gap that explains it.
- The kit reads a device from its npm package (#691). `createShell` and
  `createViewer` take `dist` as a function from a path in the build to its
  URL, or as a string, which still means a build directory, so an existing
  caller is unchanged. `@portrayal/kit/dist` exports the three that make one:
  - `flatDist(base)`, a build directory;
  - `distResolver(dist, fallback)`, which accepts either form;
  - `await packageDist({at, index})`, the published packages. A device file
    comes from that device package, a component skin from its components
    package,
    and every other file from `@portrayal/index`. Each is read at the exact
    version `packages.json` names, and `latest` is resolved to an exact index
    version first, so a page never mixes two releases. `at(name, version)`
    picks the server and defaults to `JSDELIVR`.
  The explorer reads the packages with `?dist=packages` (a local
  `library/packages/`) and `?dist=cdn`, with `&index=<version>` to pin one.
  Its default is the build directory, as before. The per-namespace components
  packages of the npm entry in this section are what `packageDist` reads
  at 0.2.0.
- `rackDiagram` in `@portrayal/kit/drawio` takes three optional keys (#724).
  A group may carry its own `faces`, so a page draws only the faces it names
  and a rack builder can make one page per face. A mounted device may carry
  its own `id`: cell ids are slugged from it and not from the name, so two
  devices of one model are two cells. A rack may carry its own `numDisp`, and
  `descend` prints U1 at the bottom. Without the three keys the output is
  what it was.
- The 3D viewer reports a lost WebGL context (#746). A viewer emits
  `contextlost` when the browser takes the context away and
  `contextrestored` when the scene is back, with the rebuild error or `null`,
  and `viewer.contextLost` says which state it is in.
- `<device>.configs.json` carries `chassis.kits`: each rail kit the device
  lists, resolved inline in the order listed - the device's `supply`,
  `variant` and `depth` override, and the kit's `version`, `description`,
  `motion`, `travel`, `install`, `configurations` (with the override applied),
  `parts` and `accessories`, each part and accessory with its `version`,
  `class`, `size` and `body` (#907). These are the refs devicelock's
  `composed` follows from `chassis.kits` (#906), and `render.py --if-stale`
  now rebuilds a device when a kit it lists, or a kit's part or accessory,
  changes. No device lists a kit yet.
- The DCIM exports say a device's ear positions and rail kits in the
  comments, beside the overhang line, since neither NetBox nor Nautobot has a
  field for either (#907).
- Every lint rule says why it exists: what it prevents, and for whom (#952).
  `docs/lint-rules.md` gains a why column and a severity column, saying
  whether a finding warns, fails, or warns until a device claims
  `maturity: verified`.
- `lint-rules.json` in the dist: the rule table as data for the site's rule
  page, written by `lint.py --list-rules --json` from the same table as the
  page. Each rule carries its code, scope, rule, why, fix, a severity token
  (`error`, `warning`, `at-verified`, `mixed` or `mixed-at-verified`), and
  `fails`, `warns` and `fails-at-verified` (#952). It ships in
  `@portrayal/index`.
- Lint L172 (error): whatever is named for a logo is a reserved place and
  paints nothing (#964). A contract element, a skin node or a device region
  whose id has the word `logo` in it is `logo-zone` (or `logo-zone-<n>`); the
  skin node is an empty `rect` with `fill="none"` and no stroke; the region
  states `at` and `size`; and no decor, cutout, silkscreen mark, bay or
  placement of a device carries the word. The library is clean under it and
  nothing was added to the lint baseline. The rule reads names only: a box
  standing for a mark under another name is not caught.
- A JSON Schema for the marked-up drawing document,
  `spec/schemas/marks.schema.json`, so a client that sends one (an MCP tool, a
  script) can be told what to send. `normalise()` in `kit/marks.js` is tested
  against it: whatever it returns is a valid document.
- `juniper/mx2000-lc-adapter@1`, the MX2000-LC-ADAPTER (ADC, 150 W). It
  seats an MX240-form MPC turned 90 in its one bay, `mpc`, as the MX960
  seats it. Its module type exports as `MX2000-LC-ADAPTER.yaml`.
  - In NetBox an MPC installed under the adapter names its components
    `fpcN/mpc/...`.
  - Nautobot is not given the adapter's `mpc` bay, because the same MPCs
    also seat directly in the MX240, MX480 and MX960. Superseded by the
    Nautobot entry under Fixed (#917): Nautobot has the bay at 0.2.0, with a
    blank position.
- A configuration can turn a seated occupant: an `occupants:` mapping takes
  `turn:`, in degrees, relative to the seat, one of the turns its host allows.
  An interface in `spec/schemas/connectors.yaml` lists the turns it allows
  (`terminal-stud`: 0, 90, 180 and 270, so a ring lug turns freely on a ground
  stud), and a component's presented connection point may narrow them with
  `turns:` (`common/terminal-screw-34@1` and `-38@1` allow 0 alone: the
  barriers fix the pole). An interface that names none allows 0, so no other
  seat changes (#829).
- Where a configuration states no turn, the build chooses one for a seat that
  turns: the wire goes down, toward the nearer side edge of the face, the other
  side or up, the first direction in which the whole lug crosses no part, bay or
  other seat; running past the edge of the face is allowed and a printed legend
  is avoided where it can be. Across the library's 155 ring-lug seats on 63
  devices that is 103 down, 24 left, 22 right and 6 up, none across a part, and
  the ring lug no longer lies across LAN1 on the Supermicro SYS-111E-FWTR and
  SYS-111E-FDWTR, the ESD jack on the Juniper MX150, a fan bay on the Edgecore
  DCS500 or the second stud of a pair. A two-hole lug on a stud pair (#828)
  turns 0 or 180 only, and its 51 seats on 25 devices lead 45 down, 4 left, 1
  right and 1 up; two of them, on the MX150 and the MX480, cross a part either
  way and are recorded. No library configuration seats a lug, so no drawing
  changes (#829).
- `<device>.configs.json` publishes `turns` on every slot entry (the angles an
  occupant may take on top of `rotate`, null where there is no choice) and
  `seat-turns`, `{view: {slot key: {ref: turn}}}`, the turn the build seats a
  part at where its configuration states none; a seated occupant on a seat
  that turns carries `data-seat-turn`. `components.json` cages carry `turns`
  too (#829).
- The explorer offers a turn for a seated lug in the inspector, seats it the
  same way in 2D, in the faces it holds and in 3D, and writes the reader's
  turns to the share link in a parameter of its own, `turn=<key>~<deg>`, so a
  link written before it keeps its swaps. `kit/swap.js` gains `seatTurn`,
  `seatRotate`, `encodeTurns`, `decodeTurns`, `acceptTurns`, `builtTurns` and
  `turnOverrides`; `occupantAt`, `occupantTransform`, `seatOccupant`,
  `applyOccupantOverrides`, `applyFaceOverrides`, `seatFace`, `seatViews` and
  `viewsToRewrite` take the turns as a further, optional argument (#829).
- Lint L146: an occupant's `turn` is one its host allows. L147: a connection
  point's `turns` is a subset of the turns its part's interface allows, and
  only the presented point states one (#829).
- **`combine` on an optical path**, an optional component key
  (roc-ops/Portrayal#246): several sources landing on one destination, the
  opposite of a split, written in place of `from` as a list of `{at}` entries
  with one `to` endpoint. Each source says how it joins - a `band` for a
  wavelength combine (the add side of a filter) or a `ratio` for a power
  combine (a coupler run backwards) - and the two do not mix. Two plain paths
  into one position are still an error; only a declared combine may share
  one. The DCIM projection writes one fibre-map row per source, carrying its
  `band` or `ratio`, exactly as it writes one per destination of a split, so
  a combine onto a trunk position and banded legs off it export the same
  rows. A contract written before this key reads as it did. A published
  build carries the shape: an entry of `optical.paths` in
  `library/dist/components.json` may now hold `combine` and no `from`, so a
  consumer that reads `from` on every path must allow for it.
- Lint **L171**, on components: a `combine` has one destination and no
  path-level `band`, names each source once, and its sources either all carry
  a `ratio` summing to 100 or carry bands, no two the same, with at most one
  source carrying what the bands leave. L78, L80 and L130 read a combine's
  sources as they read any other endpoint, and L79 allows several sources on
  one destination only inside a declared combine.
- `optical.legs` in the tools: the reader for the three path shapes.
  `optical.endpoints` is built on it, so the fibre map, the fibre-ends index
  and every lint rule that walks a path read the shapes in one place.
- `@portrayal/kit` 0.10.0: an outlet's state is shown on its lamp (#934;
  `docs/pdu-model-design.md` section 3.2). A state set on the path of an
  element that declares states - a switched PDU outlet - is applied to every
  lamp `for:` binds to it as well: by a marks document (`marks.js` apply), by
  the Explorer's chips, and in the 3D scene (`relief.js` applyNodeStates,
  `viewer3d.js` setStates), through one rule in `@portrayal/kit/states`:
  `boundLamps(svg)` (path -> the bound lamps) and `expandStates(map,
  bindings)`. A seated plug or silkscreen naming the outlet declares no states
  and is left alone, and a port declares none of its own, so no drawing
  already in the library changes. `relief.js` gains `noteLampBindings`,
  `clearLampBindings`, `lampBindings` and `expandedNodeStates`.
- A drawing marks an element a lamp is bound to with `data-lamped="true"`,
  and the base stylesheet dims a power outlet that is `off` and has no lamp
  (opacity 0.55); one with a lamp is never dimmed. No device in the library
  has a switched outlet yet. Superseded: three do at 0.2.0,
  `eaton/evma8365x`, `eaton/pdumh20net` and `eaton/pdumv20hvnetlx`.
- A rack PDU states its capability as two facts, `attrs.management.metering-scope`
  (`none`, `input`, `branch`, `outlet`) and `outlet-switching`, and the class is
  derived from them and published as `pdu-class` in `<device>.configs.json` and
  `devices.json`: `basic`, `switched`, `metered-input`, `switched-metered-input`,
  `metered-branch`, `switched-metered-branch`, `metered-outlet` or `managed`
  (#934, docs/pdu-model-design.md). Lint L166 states the two together and ties
  the outlet `[on, off]` states to `outlet-switching`.
- Structured input keys in `attrs.power`: `input-cord`, `input-phase`,
  `input-wiring`, `input-voltage-v`, `input-current-a`, `plug-rating-a` and
  `capacity-kw`; `input-plug` is now the `PART_POWER` slug of the input (L167),
  and a PDU states its voltage in `input-ac` rather than `input-voltage` (L168
  warns on both). The DCIM export writes the rating on the input power port's
  description and in the comments, beside the derived class.
- A placement key `lines` (`L1`, `L2`, `L3`, `N`) on a breaker, or on an outlet
  with no breaker, and `through` may now name a fixed breaker placement as well
  as a bay (L133 widened, L135 reads bays only, L169 new). An outlet's export
  description names its breaker and lines, and `feed_leg` is written only for a
  line-to-neutral outlet on a three-phase wye input.
- `pdu-button`, the rack PDU mounting interface, in the connectors registry, and
  `configs[].mount-points` in `<device>.configs.json`: each mount point a
  configuration draws, `{mates, at}`, derived from the button placements.
- A lab's rack-side `side` takes the kit's attachment points: `left-front`,
  `left-rear`, `right-front` and `right-rear` beside `left` and `right`. L154
  checks overlap per point and refuses a side that mixes `left` with a four-post
  name; `labs.json` publishes the point as written. A rack-face `side` stays
  `left` or `right` (L153).
- `spec/tools/portrayal/preflight.py`, one command a builder runs before
  asking for review (#924). Against the merge base with `--base` (default
  `origin/main`), working tree and untracked files included, it prints PASS or
  FAIL per check with the command that fixes it, and `--json` for an agent:
  the DCIM exports regenerated from the tree and compared with
  `library/exports` (no build: the exporter's dist is derived from the
  sources), added skip reasons against `spec/allowed-skips.txt`, private
  strings in added lines, the changelog fragment, `devicelock` (also against
  the base lock for a device the diff re-locked), lint on the touched devices
  and every device that seats a touched component plus the library-wide
  rules a `--device` run skips, with no warning beyond the baseline, and
  `npm test` with the kit behaviour tests that name a changed module when
  `kit/` changed. No build and no suite run.
- Preflight has an eighth check, `prose`, and it only warns (#114). It reads
  each `device.yaml` and `contract.yaml` the diff changes and reports a
  sentence of more than 25 words that the merge base does not have, in a
  `description` (device, configuration or component) or a string under
  `attrs`. That is the prose a DCIM export carries. Text the base already
  holds is never reported, words quoted from a vendor are not counted, and gap
  notes and `provenance` are not read. A WARN leaves the exit status and the
  `ok` field of `--json` unchanged; a check's `status` in `--json` can now be
  `WARN` as well as `PASS` or `FAIL`. `CONTRIBUTING.md` states the rule: new
  and changed prose follows Simplified Technical English, and existing text
  is not rewritten.
- `@portrayal/kit` 0.4.0: `@portrayal/kit/rack/*` has commands and questions
  an agent can use without reading the code
  (`docs/rack-agent-commands-design.md`). `fit` seats, empties
  or restores one bay or cage; `field` sets one setting of one seated part;
  `cable.update` takes `a` and `b` to move an end and keep the cable.
  `cable.route` refuses a waypoint the rack lacks and judges only the new ones.
  `inspect` reads one device's bays, cages and part settings, or one cable's
  ends, route, routed length, slack and loose ends (`unchecked: true` when the
  ends could not be read); `selectCables` turns "the cables on this device" or
  "every loose cable" into ids (saying when some ends could not be checked),
  and refuses a `purpose` or `media` that is not a name; `describe` takes a
  window (`section`, `offset`, `limit`, at most `MAX_WINDOW`, 50, lines a
  section) and refuses one it cannot read; `catalog` filters by `kind`.
  `loadSlots(dist, refs)` in `rack/catalog.js` loads the parts lists that
  `editor.apply(cmds, {ctx})` and `editor.preview(cmds, {ctx})` check against,
  for that call only.
- `rack.json` gives every device a `kind`, an advisory word for what it is
  (`switch`, `router`, `patch panel`, `cable manager`, `server`, `pdu`, ...)
  whose words may be refined without a format change, and `devices.json`
  carries each device's `profile`, which `kind` is read from. Both are
  additive: `rack.json` stays `format` 1 and `devices.json` stays
  `contract: 2`.
- `library/dist/rack.json`: the rack catalogue, written by `rack_index.py` after
  the compiled faces exist. Each device carries its rack units, size, airflow,
  default configuration and configurations, and, only when it has them, its
  `mount`, `shell`, stated cable `capacity`, and the `guides` and `passes` ids a
  cable route can pass through on each view. `format` is 1; the keys are
  documented in `docs/format-stability.md`.
- `@portrayal/kit` 0.3.0 carries the Rack Builder's rules as `@portrayal/kit/rack/<module>`:
  the rack file, fit rules, cable managers, cables, routes, the export and DCIM
  rules, the catalogue loader (`loadCatalog(dist)`, which reads `rack.json`
  through `flatDist` or `packageDist`), and the command core: every edit as a
  named, validated command (`commands.js`), undo and redo (`history.js`), a
  headless editor with change events (`editor.js`) and queries that read a
  rack (`queries.js`). `kit/README.md` has a "Racks" section with an example
  that `spec/tests/js/rack-readme-example.mjs` runs.
- `spec/schemas/rack.schema.json`, published at
  `https://portrayal.dev/schemas/v1/rack.schema.json`: the schema of a rack file
  (`format: "portrayal-rack"`, `version` 2). It is the Rack Builder's file
  format, not a manifest, so it does not carry format 1. Superseded: a 0.2.0
  rack file is `version` 3 and its schema is at `/schemas/v2/` (the rack
  file entry under Changed).
- `chassis.overhang: {left, right}` states how far a `rack` device's real parts
  reach beyond its rack face, in millimetres (#865). Such a device draws its
  front at the rack face with its ears, and a part beyond it is an ordinary
  placement at negative x or past the view's width. L150 refuses a placement,
  bay or cutout outside its face that the side's figure does not cover
  (optional placements and decor are not checked); L151 warns when no part
  reaches a stated figure. `<device>.configs.json` carries it as
  `chassis.overhang`, and the DCIM exports say it in the comments, since
  neither schema has a field for it. To devicelock it is a statement, like
  `mount`: the parts that reach past the face carry their own geometry.
- `chassis.ears: behind` states that a rack device's ear folds are behind its
  body, so a 482.6 mm front is the part and L43 stands down (#865).
  `<device>.configs.json` carries the statement under `chassis.ears`, in the
  object form #907 publishes; devicelock files it as surface.
- `fs/uscmh-sfdabsb2u` 0.1.0, the FS USCMH-SFDABSB2U 2U ABS finger duct, the
  width of the rack in front of its rails, from the FS Horizontal Single Sided
  Manager datasheet, with its parts `fs/uscmh-sfdabsb2u-base@1`, `-finger@1`,
  `-end-finger@1` and `-cover@1` (#865).
- `fs/cmh-6dr1u-end-ring@1` and `fs/cmh-6dr1u-ear@1`, the CMH-6DR1U's end
  ring, with a vertical `ring` guide, and its ear (#865).
- **A ring says what of its loop is solid** (#968, `docs/cable-lay-design.md`
  section 3.3): `guide` gains `wall` (each leg beside the opening), `height`
  (the top of the loop over its base) and `slit` (`[from, to]`, the gap in
  the far leg of an open loop). They compile to `data-guide-wall`,
  `data-guide-height` and `data-guide-slit`, and L138 holds each inside the
  part. A sheet part's `solids` in rack.json now carry each such ring's legs,
  bar, seat and hook as `ring/<id>/<part>`. The schema's recorded shape and
  L138's rule text are re-recorded.
- **fs/d-ring-snap-in@1 1.3.0** states them: legs 5.8, the loop 41 high,
  the slit 28.6 to 30.8 mm over the tray. **fs/fhd-cmp5dr 1.1.1**.
- The snap-in rocker (`common/rocker-switch@1`, 1.1.0) has a `state`, `off`
  or `on` (#808), and is the first part whose position SHOWS rather than
  moves. It is drawn as the see-saw it is: one surface tipped about its
  centre, a node for each position, rising toward the I end for `off` (drawn,
  as before) and toward the O end for `on`. In 3D each is a sloped `profile`,
  4.9 at the raised end and 2.2 at the low end, both read off the GL-12xB GLB.
  The ReadyLinks GL-12xB-240D and the Catalyst 4948E (through its AC supply)
  draw as before and take a patch. `common/power-switch-slide@1` is left
  without positions: no source says which end of its travel is ON or how far
  the slider moves.
- Seven parts that draw their own rocker take the same see-saw (#808): the
  Juniper JNP10K-PWR-AC2 and MX80 AC supplies and the Telco Systems TM-7124S
  AC supply (`state`), the Casa C40G AC inlet panel (`switch-1` to
  `switch-4`), the Casa PEM's rocker breakers (`breaker-1` to `breaker-4`),
  and the Nokia SR-7 and SR-12 PEM-3 (`breaker`, `power-switch`), each a
  contract minor with estimated heights. The devices that seat them draw as
  before and take a patch. Rockers whose art marks no ON end, and the SR-1 DC block whose
  lamp rides on its rocker, are left as drawn; the design note says why for
  each.
- Lint L144 (warning): members of one group that one configuration draws on
  one face hold one `rel-pos` each (roc-ops/Portrayal#414). Variant views of
  a face and bays that `only-in` scopes to different builds are alternatives
  and may share a position; a position reused on another face is not
  reported. Thirteen devices carry a clash and are in the lint baseline: the
  six Juniper MX chassis whose `grounding` group puts an ESD jack at position
  0 beside the first earthing stud or plate (mx80, mx150, mx204, mx240,
  mx304, mx480), `dell/r740xd` furniture, `ufispace/s8901-54xc` lane lamps,
  and the port lamps of `edgecore/agr110`, `agr130`, `agr560`, `csr310` and
  `ecs4120-28fv2-i`. Each cure renumbers or regroups placements, a major
  device version, and is left for a decision.
- Lint L145 (warning): a group is not named `ports`, which names no port
  family (#414). `dell/r660`, `dell/r740xd` and `maiaedge/port-extender` are
  in the baseline; renaming a group is a major device version.
- A position field may list `drawn-by-absence`: the options drawn by showing
  none of its SHOW nodes. Lint L148 now asks every other option of a field with
  SHOW nodes to show at least one node (#874).
- A position is a field (#808, docs/switch-positions-design.md). A `choice`
  field may now MOVE a skin node (`data-move-from` and a `data-move` table of
  `option: dx dy [deg]`) or SHOW one (`data-show-from` and the options listed
  in `data-show`). The build applies both, the kit's `paintFields` applies the
  same two rules at runtime and `unpaintFields` puts them back, and in 3D a
  change to such a field rebuilds the scene, because a moved node stands
  somewhere else. An option the field does not declare fails the build. A
  placement may say what each position means in `positions:`, carried into
  the drawing as `data-positions`. Lint L148 holds a position's table to its
  field's options and L149 keeps a moved node on its part; L73 counts both
  attributes as wiring. `common/dip-switch-2@1` (1.1.0) is the first user:
  `sw-1` and `sw-2`, `off` or `on`, drawn `off` as before, so the ten AurCore
  devices that place it draw as they did and take a patch.
- The 300CB08 family's alarm DIPs (`amphenol-ns/alarm-dip-8@1`, 1.1.0) are
  the second user: `sw-1` to `sw-8`, `up` or `down`, drawn up as before. The
  eleven panels that place them say in `positions:` what each switch does
  (the alarm for breaker position A1 to B8; on the nrgILS, whether a circuit
  is held on out of software control), and their `populated` and
  `with-fuses` configurations set the switch of every fitted position down,
  as the installation guide requires. Each panel takes a patch.
- **Two more FS vertical cable managers, both `rack-side`.**
  `fs/cmv-dfd45u5w`, the FS CMV-DFD45U5W (#63030), a 45U dual-sided ABS
  finger duct with hinged PVC covers on both faces, 2108 x 138.8 x 302 (the
  drawing; the table and the dimensioned render say 310, recorded as a
  `sources-disagree` gap), built hollow as two channels back to back across a
  25.6 mm spine. Its back and cover views are the CMV-SFD45U5W rasters byte for
  byte and its side view lands on the single-sided figures within half a
  millimetre, so every part is reused on both faces:
  `fs/cmv-sfd45u5w-base@1`, `-wall@1`, `-finger@1`, `-clip@1` and `-cover@1`.
  The middle is closed by plates sunk inside the side, top and bottom faces,
  as on `fs/cmh-dfd1u`. Capacity 5490 Cat6 (datasheet); the 16.80 kg product
  page weight is stated and flagged as suspicious, 3.5 times the single-sided
  4.75 kg.
  `fs/cmv-sfd42u9w`, the FS CMV-SFD42U9W (#188944), a 42U single-sided finger
  duct, 1866.9 x 88.9 x 152.6 in two 21U sections: a folded steel channel open
  at six rectangular windows (`fs/cmv-sfd42u9w-base@1`), two finger walls
  (`-wall@1`), 84 moulded T fingers at one rack unit (`-finger@1`) and a
  pullable cover a section (`-cover@1`), measured on the 600 dpi page render
  of its low-resolution drawing. The material (SPCC on the product page, ABS in
  the datasheet) and the cover (none in the specification, drawn and rendered)
  are `sources-disagree` gaps; the drawing and renders are modelled. No
  capacity is published for it.
- **The FS steel vertical finger ducts, CMV-SFDS45U5W (#220089) and
  CMV-DFDS45U5W (#220091)**, two `rack-side` 45U parts, 2000.25 (45 x 44.45)
  tall and 169 wide over their steel covers, from the four views of the FS
  steel vertical datasheet (portal id 6868). Both are built hollow as sheet
  bodies: a steel back plate (on the dual, a 2.4 spine) as a well open at its
  seven windows, two steel returns, 44 T-shaped fingers a row at one rack unit
  with the top unit empty, and two pullable steel covers a working face
  (976.45 or 976.95 upper, 1021.4 lower), each with six hinge clips, under a
  `duct` guide run down the 141.52 channel. `fs/cmv-sfds45u5w` is 152.63 deep
  with its seven back-plate openings declared as pass-throughs;
  `fs/cmv-dfds45u5w` is 307.66 deep with a channel, fingers and covers on its
  front and rear faces. New parts `fs/cmv-sfds45u5w-base@1`, `-wall@1`,
  `-cover-upper@1`, `-cover-lower@1`, the same four for `cmv-dfds45u5w`, and
  `fs/cmv-fds45u5w-finger@1`, the finger both ducts share. The covers reserve
  a logo zone. Neither part carries a cable capacity: no FS document states one
  (a `cable-capacity` gap).
- **Vertical cable managers, steps 1 and 2: `rack-side` mounting and `side`
  placements** (`docs/vertical-cable-managers-design.md`).
  `chassis.mount: rack-side` is a part that attaches to the side of a rack's
  upright and runs vertically beside the rack, outside the rails. It states
  `ru`, the rack units it runs beside (L125 warns without it, and
  `full-depth`, `overhang` and `ears` stay rack-only), and its DCIM export
  writes `u_height: 0` and `is_full_depth: false` with the comment line
  "Mounts on the side of a rack's upright, beside the rack; occupies no rack
  unit." Lint L152 (warning): a rack-side part's front is taller than it is
  wide, because it is drawn as it stands.
  A lab placement takes `side: left | right`. A rack-side part states it and
  is placed by `ru`, its bottom unit (default 1), on a `face` (default
  `front`); it takes no `on` or `unit`. A rack-face part narrower than the
  450 mm rack opening may state it too, and then claims its rack unit per face
  AND side, so a bracket on each rail shares a unit; any other rack-face part
  claims both sides (L142). Lint L153 (error): `side` only on those two, and a
  rack-side part has one. Lint L154 (error): a rack-side part fits the rack's
  height, and two on one side of the rack do not overlap. Every `labs.json`
  placement gains `side` (`left`, `right` or `null`); a new field only, and
  `contract` stays at 2.
  Two devices: `fs/cmv-sfd45u5w`, the FS CMV-SFD45U5W (#63033), a 45U
  single-sided ABS finger duct with hinged PVC covers, 2108 x 138.8 x 165.1
  (cover included; body 125.4), built hollow as a sheet body from the
  datasheet's back, side and cover views - the back plate as a well open at
  eight oval pass-throughs (`fs/cmv-sfd45u5w-base@1`), two finger walls
  (`-wall@1`), 92 fingers at one rack unit (`-finger@1`), 24 cover clips
  (`-clip@1`) and a pullable cover per 22.5U section (`-cover@1`), with a
  `duct` guide run down its height; and `fs/cmv-5u3w`, the FS CMV-5U3W
  (#64186), a 5U `rack-face` finger bracket 26 wide, 222 high and 84 deep on
  the rail face, from the datasheet's side and top views
  (`fs/cmv-5u3w-base@1`, `-fingers@1`).
- `@portrayal/kit` 0.6.0: parts beside the rack and parts on one rail are the
  rack kit's (#926; `docs/vertical-cable-managers-design.md` section 8). A
  zero-U part (`mount: rack-side`, a vertical cable manager or a zero-U
  PDU) is an entry of `rack.zeroU`, `{id, ref, cfg, label, at, offsetMm,
  between?}`, placed, moved and removed by `zerou.place`, `zerou.update` and
  `zerou.remove`, and fitted by the rack units it states, not its drawn height.
  A narrow rack-face part (under the 450 mm opening) goes on one rail with
  `side.place` and changes rail, or goes across both, with `side.set`. A new
  module, `@portrayal/kit/rack/zero-u`, says where each part stands; `describe`
  and `inspect` list them, and the export data says where each stands
  (`zeroUNotes`, `zeroUImportItems`, `rackNotes(rack, {zeroU: false,
  chassisOf})`). A cable lane runs through a duct beside its upright
  (`laneXAt`), and `fill` and `capacityOver` count the cables through it.
- `rack.schema.json` describes the `zeroU` entry and `side` on an item, and no
  longer calls `zeroU` reserved. Both keys are optional and unconstrained, so
  every file that validated still does; the rack file stays `version` 2
  (`docs/format-stability.md`). Superseded: it stayed 2 for this change
  only. Bundles made it `version` 3 (the rack file entry under Changed).

### Changed
- **Schemas: the device schema types ten keys that took any scalar at 0.1.0.
  BREAKING for a manifest outside this library** that already used one of
  these names with another spelling of the value: the schema refuses it now.
  Under `attrs.power`: `input-plug` (a lowercase slug, as `nema-l21-30p`),
  `input-cord` (`fixed` or `detachable`), `input-phase` (`single` or
  `three`), `input-wiring` (`wye` or `delta`), and `input-voltage-v`,
  `input-current-a`, `plug-rating-a` and `capacity-kw` (each a number above
  0). Under `attrs.management`: `metering-scope` (`none`, `input`, `branch`
  or `outlet`) and `outlet-switching` (a boolean). These are the keys the two
  rack PDU entries under Added introduce. At 0.1.0 `attrs.power` and
  `attrs.management` took any key with a string, number or boolean value,
  and they still do for every other key. No key was removed from any
  schema. All 1,226 manifests of the 0.1.0 library (170 devices, 1,027
  component majors and 29 listings) validate under the 0.1.0 schemas and
  under these. The component and listing schemas refuse nothing they
  accepted. `format` stays 1, and each schema keeps its `$id` under
  `/schemas/v1/`.
- `relief.profile` and `profile-y` now move with `out` when their part stands
  `in:` a well or is seated in a lifted bay, so the heights stay heights
  above what the part stands on. The schema used to say a profile was not
  shifted by `in:`; no part in the library before the FS FHD-CMP5DR met that
  case, so nothing already built changes.
- `chassis.ru` also means the rack units a `rack-face` part's ears span, not
  only units occupied; L125 asks a `rack-face` device for `ru`, and L43 (ears
  are not drawn) stands down for it.
- **The Nautobot export stops on a front port it cannot state truly**, instead
  of writing it: a one-fibre front port whose `rear_position` is missing or
  outside its rear port's positions, and a front port collapsed to one
  position that is not the whole of its rear connector, fibre for fibre. No
  export in the library changes (roc-ops/Portrayal#771).
- **A device's `pon` flavour types only a port**: an SC receptacle or a
  pluggable cage. A lamp or label in a group that states `pon` no longer
  exports as a second PON interface. No export in the library changes
  (roc-ops/Portrayal#772).
- Lint L39 counts a lamp as punched when the holes over it together cover
  more than half of it, not only when one hole does, and a lamp whose part
  declares several windows also when the holes cover more than half of those
  windows. A lamp seen through several windows could not be covered before,
  however honestly they were punched. `expand.py` still punches a lamp
  automatically only when its part declares one opening.
  `edgecore/ais800-32d` (1.1.0) punches its 128 lane windows as round
  cutouts (`led-port-N-lane-K`) and drops the L39 waiver it carried for
  want of this (roc-ops/Portrayal#395).
- `spec/schemas/standards.yaml`: the `sc-duplex-adapter` pitch floor is
  12.71, the narrowest of the five gaps it was measured from, not 13.0, their
  mean. L81 now accepts an evenly spaced SC adapter panel at 12.71 or wider,
  where it used to refuse anything under 13.0. `fs/fhd-1mtp12-sc-os2-a@3`
  (3.0.2) no longer undercuts the floor and drops the `pitch-note` that said
  it did; the seven FS FHD enclosures that seat it take a patch
  (roc-ops/Portrayal#245).
- **BREAKING for DCIM data already imported.** Telco Systems is listed as
  `BATM/Telco Systems`, the name the vendor asks to be listed under. The
  `manufacturer` of its fourteen devices changes, and with it every one of its
  NetBox and Nautobot exports: the `manufacturer` field of fourteen device
  types and thirteen module types, each device type's `slug`
  (`telco-systems-tm-8104` is now `batm-telco-systems-tm-8104`), and the
  directory they are written under, `Telco Systems/` to `BATM-Telco Systems/`
  (a slash in a manufacturer is written as a hyphen in the directory, as it is
  in a model's file name). A DCIM that imported the old files holds a
  manufacturer named `Telco Systems`: rename it there before importing again,
  or the new files create a second manufacturer beside it. The namespace
  `telco-systems`, every component and device ref, every port name and every
  drawing is unchanged, and so is the `@portrayal/telco-systems-*` package
  name of each device. `spec/schemas/vendors.yaml` keeps `Telco Systems` and
  `BATM Networks` as aliases.
- **The npm packages: the component skins ship one package per namespace**,
  `@portrayal/components-<namespace>`, and `packages.json` in `@portrayal/index`
  maps each namespace to its package and version under `components`. One
  package for every skin was the largest in the scope, grew with every
  component and moved whole with any one skin. `packageDist` in
  `@portrayal/kit/dist` reads the new map, and `@portrayal/kit` is 0.2.0 for it:
  0.1.0 reads the old single entry and cannot load an index published from
  here on.
  `@portrayal/components` 0.1.0, published before the split, is not updated
  again (roc-ops/Portrayal#526).
- The Nautobot exports are no longer a copy of the NetBox ones in two places,
  because Nautobot could not import 37 of them. Front ports under
  `library/exports/nautobot/` now carry `rear_port` and `rear_port_position`
  (read from the fibre map) in place of `positions`, which is the shape
  Nautobot's FrontPortTemplate requires; and a device that occupies a half
  rack unit states the next whole number, with the true height in `comments`,
  because Nautobot stores `u_height` as an integer. That is the 35 FS FHD
  cassettes and panels, the Juniper MX104 (3.5U, written as 4) and the Telco
  Systems TM-7124S (1.5U, written as 2). The four MPO-to-MPO adapter panels
  state each front and rear connector as one position there, since Nautobot
  binds a front port to a single rear position; the fibre map keeps every
  fibre. None of the 37 could be imported into Nautobot before, so no imported
  data changes. The NetBox exports and the fibre maps are unchanged.
- **A 3D export leaves the marks out** (roc-ops/portrayal-site#46): `exportData()` and
  `download()` hide every mark halo for the export, as they always hid the
  selection halo, and restore them after. A GLB or USDZ is the model; the marks
  stay on screen.
- **BREAKING for DCIM data already imported.** The DCIM exports no longer
  call every device without `ru` a 1U full-depth rack device. A box that is
  not racked exports `u_height: 0`, not full depth,
  with its mounting in the comments (ReadyLinks GL-8XEP, Halny HLX-TGV), and
  the Dell R740xd exports at its real 2U. A DCIM that imported these types
  holds the old height until they are re-imported (roc-ops/Portrayal#734).
- **`toDrawio()`'s `ports` is what a line can be drawn to** (roc-ops/Portrayal#730):
  every port and every empty bay. A bay holding a card is a container that
  takes no line, and counting it overstated a modular chassis by its seated
  cards. `connectable(ports)` in `drawio.js` gives the same count. `toGraffle()`
  is unchanged - every port and bay there is a magnetised shape - and its
  `ports` now says so.
- **BREAKING for DCIM data already imported.** The Edgecore DCS510's AC builds
  export as `9716-32D-O-AC-F-EU` and `9716-32D-O-AC-B-EU`, not
  `9716-32D-O-A C-F-UK` and `9716-32D-O-A C-B-UK`, under Edgecore and its
  Arrcus, IP Infusion and SONiC listings. Two UK part numbers carried a stray
  space, which sorted them first; with it removed the EU part number names
  the type, as for a build whose every part number has a cord. A DCIM that
  imported the old types keeps them under the old model; re-import under the
  new one (roc-ops/Portrayal#720).
- **The DriveNets names leave the UfiSpace hardware** (roc-ops/Portrayal#674).
  Twelve UfiSpace boxes carried their NCP name as an `oem` alias (#518) - the
  S9700-53DX's `NCP-40C` and so on. DriveNets' own listing now carries it
  (`drivenets/<box>/listing.yaml`, `model:`), filed under DriveNets and found
  by search and the picker, so the alias is removed and each box takes a patch
  bump. `aliases` in `devices.json` and `<device>.configs.json` drops those
  names, and the UfiSpace DCIM types lose "Also sold or listed as: NCP-...".
  The S9600-102XC loses `NCP-96X6C-S` too: the DNOS CLI reference accepts only
  the S9601-102XC for that model. The fabric boxes (S9705-48D `NCF-48CD`,
  S9725-64E `NCF-64E`) keep theirs until they are listed.
- `amphenol-ns/output-p40@1` is 1.1.0: it gains its interface and mate point,
  and its drawing does not change. The six panels that place it take a
  patch; their DCIM exports change in the drawing version line only.
- `cisco/asr-9902` and `cisco/asr-9903` (1.0.4) record the Fixed-Port Routers
  installation guide's dimensioned top views, Figures 18 and 19: 439.5 mm for
  the ASR 9902 and 439.9 mm for the ASR 9903, which settles the stencil-versus-
  data-sheet question in favour of the stencil (#374). The ASR 9902's
  `two-chassis-one-body-outline` gap is closed; the ASR 9903 carries a
  `chassis-width-sources-disagree` gap naming the rescale (0.99108 on every x)
  and the five parts it reaches, still to do.
- ASR 9000 route switch processors seat where a Cisco document names the
  chassis (roc-ops/Portrayal#262). `cisco/asr-9006` 3.1.0 takes the
  A9K-RSP-4G, RSP-8G, both RSP440s and both RSP5s in slots 0 and 1;
  `cisco/asr-9010` 1.1.0 adds the RSP-8G, RSP440s and RSP5s to slots 4 and 5;
  `cisco/asr-9904` 3.1.0 adds the RSP440s and RSP5s to slots 1 and 2; and
  `cisco/asr-9906` and `cisco/asr-9910` 1.1.0 add the RSP5s to their outer
  RSP slots. Sources: RSP datasheet c78-500699 Table 3, RSP440 datasheet
  c78-674143 Table 3, the IOS XR 64-Bit datasheet c78-737841 System
  requirements and the RSP5 datasheet c78-741128. Each chassis names its
  sources under `provenance.rsp-chassis-support`. Nothing is renamed or
  removed; the DCIM exports change in their bay descriptions only.
- The 1-port and 2-port 100GE MPAs seat in the modular line cards
  (roc-ops/Portrayal#262). `cisco/a9k-mod400-se@2` and `-tr@2` (2.1.0) take
  both in both bays, from the Ethernet Line Card Installation Guide list for
  the 400G card. `cisco/a9k-mod200-se@2` and `-tr@2` (2.1.0) take the 1-port
  in both bays and the 2-port in bay 0 only, which is what the guide states
  and is how the one-2-port-per-card limit of data sheet c78-735809 holds.
- The `unplaced:` sentence on the twelve ASR 9000 parts still seated by
  nothing now names what blocks each one: no compatibility statement in the
  corpus (four line cards), a double-height SPA, the ASR 9906 rear that has no
  fabric bays, power trays with no tray-level bay, and two parts with no
  document or part number.
- The two-position RELAY header on the ten AurCore AIS switches (`aurcore/ais2001`,
  `ais2001p`, `ais2002`, `ais2002p`, `ais2003`, `ais2003p`, `ais2004`, `ais2004p`, `ais4001`,
  `ais4001p`) is `common/terminal-header-508-2@2`, placed turned 90 at the same centre.
  Its two contacts now run parallel to the five of the power header, with the keyed side
  toward the RELAY legend, as the vendor's video and product images show. A seated
  `generic/terminal-508-2-plug@1` turns with it and overhangs the RELAY legend, as the
  five-position plug overhangs POWER. `@2` is 12.16 wide, the Phoenix Contact MSTBA 2,5/
  2-G-5,08 (1757242) width, with the contacts and the `mate` point (6.08, 6.05) 1.0 further
  in. Each of the ten devices takes a major, 0.1.x to 1.0.0. The header is still drawn 12.1
  high, which counts the solder pin; #873 asks whether it should be the installed 8.6 (#804).
  Superseded: #873 was answered in this release. `@2` is removed, and the ten switches seat
  `common/terminal-header-508-2@3`, drawn 8.6 high, at 2.0.0 (the entry on the two headers
  in this section).
- `kit/rack` no longer speaks as portrayal.dev's page (#895). A rack file newer
  than the kit is refused with "this reader supports up to version N" (no
  "Reload to get the newer page"); a system command sent without origin
  `system` is refused as "a system command, sent only by the caller"; the
  `COMMANDS` descriptions say "set by the caller" and "sent by the caller".
  `kitReadme` and `titleLines` name their maker as `source` (default
  `Portrayal`), `kitReadme` points a blank site or role at `settingsAt`
  (default: the rack's `dcim.site` and `dcim.role`), and the Nautobot script's
  address is named only when the caller passes `scriptUrl`: there is no
  portrayal.dev default. A host that wants its own sentences passes them; the
  Rack Builder passes `source: 'the Portrayal Rack Builder'`, its own
  `settingsAt` and its script URL to keep its README as it was.
- The rule and fix text of L18, L31, L45, L50 and L132 (`--list-rules`,
  `docs/lint-rules.md`, `lint-rules.json`) now say what each rule checks (#959).
  L18 asks a port on a family cage to state its media; L31 checks a distance a
  side or top region label states; L45 is cleared by drawing the face or by a
  gap whose `scope` names it, not by an `empty:` sentence (whose 40-character
  floor the schema holds); L50 is about printing off the part or covered by
  something drawn after it, not font size; L132 names both of its branches.
  What the rules raise is unchanged.
- The modelling guide and the pitfalls page state each lesson as a rule with
  its check, and no longer need the reader to know the device that taught it
  (#71). Measured tables keep their sources. A few cases stay as examples,
  each after its rule and marked *Illustration*. Both pages say how a new
  lesson is written, and the `portrayal-model-device` skill lists the gates
  in order.
- `docs/modelling-a-device.md`, Stage 2, says again that the pitch of a ganged
  block is read from `spec/schemas/standards.yaml` before it is measured off an
  image: an explicit `pitch` with its `pitch-kind` (`target` to use, `floor`
  to clear), the notes of an entry with no `pitch` key, and `row-pitch` for
  stacked rows. Device provenance already cited the guide for that rule.
- **A routed path leaves every turn room for the cable's bend radius**
  (`@portrayal/kit` 0.17.0, #973). On the reference rack of #949, 86 corners of
  the sixteen paths had less room than OM4's 25 mm, and almost none was a
  real bend. A free span is now sampled evenly along its arc, a landing is
  laid as the tangent points of its two bends, and no hang is laid that
  leaves a corner short of the radius; an approach point stands the bend
  radius from its ring's band where the route turns there, and a cable from
  behind it is led square to it through a lead point; each move to a
  detour's plane is two bend radii long; and a cable whose first turn needs
  more leg than its plug gives runs on straight out of it. None of the 86 is
  left. What the kit's rules find no room for is still routed, and reported.
  **ONE-WAY: routed lengths change on saved racks.** On the reference rack
  every cord is 10.9 to 179.2 mm longer and seven of the sixteen move from
  0.5 m to 1 m (c1 to c3 and c5 to c8; c4 stays 0.5 m, the lower leaf's
  eight stay 1 m). On one sample of 60 generated racks (1,803 cables of
  mixed media, `spec/tests/js/bend-room-sample.mjs`) a length moves by 113
  mm shorter to 297 mm longer, median 14 mm longer, 93 stock sizes up and 34
  down, and the corners short of their radius fall from 22,910 to 959, each
  a bend the kit's rules found no room for. A cable written the other way
  round does not always lay the same: 38 of those 1,803 measure differently
  from the other end (19 before), and 9 report a different number of bends.
  No cable runs in front of a zero-U part's outward face that did not
  before.
  A saved
  rack's routed lengths and stock sizes are re-measured the next time a page
  measures them; an entered length is never touched.
- The cable schedule has a `bundle` column straight after `route`, so
  `length_source`, `status` and `notes` move one place right, and its notes
  carry a line per bundle. NetBox's cables file names a member's bundle first
  in its description ("Bundle 2. uplink. Length measured along its route."),
  and its over-limit note now speaks of the whole description. Nautobot's
  cables file is unchanged; its notes list each bundle's cables.
- **The rack file is `version` 3, a one-way change.** Migration from 2 is the
  identity, so every version-2 file opens as it was, but a page saves every
  document it opens as version 3, and a page or kit from before 0.7.0 refuses
  a version-3 file rather than opening it and losing its bundles.
  `rack.schema.json` describes version 3 and is published at
  `https://portrayal.dev/schemas/v2/rack.schema.json`; the `/v1/` schema, which
  describes version 2, stays as published (`docs/format-stability.md`).
  This is the net result for 0.2.0: a rack file this release writes is
  `version` 3, and the schema that describes it is the one at
  `/schemas/v2/`. The two entries under Added that say `version` 2 and
  `/schemas/v1/` describe the file before bundles. No rack file existed at
  0.1.0.
- **Routed lengths change for a bundled cable**: it is measured along its
  bundle's trunk, not its own route, between where it joins and leaves.
- `cable.remove`, and `remove` with `cables: 'remove'`, take a cable out of its
  bundle in the same step and say so. A new cable's id, and a repaired one, is
  past every id a bundle still names, and an item id a trunk or peel point
  names is not handed to a new device. `cable.route` checks waypoints against
  `ctx.route.guidesOf` when given, and a flat `ctx.guidesOf` otherwise.
  `describe`'s refusal of an unknown section names `bundles`.
- `fs/cmh-4drb1u` 1.0.1 and `fs/cmh-sfd1u` 0.1.1 state `full-depth: false`;
  both export `is_full_depth: false` (#854).
- **A lab is validated** (`docs/cable-managers-design.md` section 6):
  `labs_index.py` used to pass any `lab.yaml` through. The lab schema is
  strict on the top level and on placements (`id`, `ref`, `cfg`, `label`,
  `ru`, `face`, `on`, `unit`, `turned`), so a lab carrying a key it does not
  know now fails the build. A lab `ref` is a device's bare `name`.
- `fs/d-ring-snap-in@1` 1.1.0 declares its ring guide, a 32.0 x 29.5 mm
  opening run along the tray. `fs/fhd-cmp5dr` 1.0.1 for that, and for stating
  its capacity of 30 as `cable-capacity` rather than in its description; its
  drawings gain only the guide attributes, and its DCIM exports change in
  their description and version only.
- Lint L127 reads a `chassis.thickness` that is not a number as a finding
  rather than raising.
- Lint L44 counts a view's declared pass-throughs as openings in the part
  that holds them, so a brush seen through a well's windows is not called
  buried; `fs/cmh-4drb1u` needs no waiver.
- **Routed lengths change** wherever a straight leg of a route would cross a
  solid body: `routePath` adds detour points there (over the near edge, a
  tray's front edge first; else round the end; else by a side lane; a detour
  that meets a second body goes round it too), which count in the measured
  length and are never stored. Most of the change is a cable from a port on a
  device's far panel, which now goes round its own device to the lane: on a
  two-post rack most rear routes, on a four-post few. A saved rack's routed
  lengths and stock sizes are re-measured the next time a page measures them;
  an entered length is never touched. A sheet part read from an older
  `rack.json`, without `solids`, is open, as every sheet part was before.
- **A zero-U part that stands in the gutter and carries no lane** (a zero-U
  PDU) moves the cable lane beside its upright outboard of it, at the units it
  spans (`laneXAt`): the lane runs in a gutter as wide as the usual one just
  outside the PDU, so a cable runs beside it and not through it, and a port
  leg to that lane goes round the PDU on its back, the side facing into the
  rack, never over its outlet face. Measured on one sample 42U rack (five
  switches and an FHD panel with an FHD-CMP5DR, four front and four rear
  ports each, every pair of ports, 780 routes) with a 52 x 65 mm zero-U PDU
  added: on a four-post with the PDU on a rear upright, 264 routes grew by 13
  to 164 mm (median 63); on a two-post, 349 routes changed by -13 to +421 mm
  (median +202). Those figures are the PDU's own share, the same rack with and
  without it.
- **Cables rest** (`@portrayal/kit` 0.14.0, #949, `docs/cable-lay-design.md`
  section 3). A ring on a tray holds a cable on its sill, its radius above
  the opening's lowest inside edge as mounted, at the side nearer the rail; a
  route through a tray lays the cable on the floor at its radius, or, where
  the page pins it (`ctx.trayFaceOf`) and the tray has tie slots, strapped
  under the plate, sagging between two straps no lower than the strap line;
  every other free span hangs by the 3D drawing's catenary scaled by the
  `DRAPE` of its family (fibre and AOC 1, twisted pair 0.5, DAC and power
  0.35) and no tighter than its installed bend radius allows, and lands on
  any surface it would pass below. `routePath` gains points `at: 'tray'` and
  `at: 'rest'` and a list of `rests`, which `inspect` gives as
  `route.rests`; `solids.js` gains `traysOf`. **ONE-WAY: routed lengths
  change on saved racks.** On the reference rack of #949 the upper leaf's cords
  grow 34 to 42 mm and the lower leaf's 125 to 144 mm (they now go round the
  tray's front edge to reach a ring on its sill), and thirteen of sixteen
  measure past the 0.5 m stock break where seven did; a free span to a
  gutter, or an unrouted jumper, grows by its hang. A saved rack's routed
  lengths and stock sizes are re-measured the next time a page measures
  them; an entered length is never touched.
- The `cable.route` refusal names trays among what a device offers ("has no
  ring, duct, pass-through or tray called ...").
- **Rule 7 of the modelling guide is narrowed**: cable management that is
  part of the product (a lacer and its rings, a tray, a spool, a bend-radius
  bracket) is declared, and drawn where it is a part, with the tie slots cut
  in a plate declared as `ties`; accessories added in the field (loose ties,
  straps, retainer bails) stay undrawn.
- The CXP, CFP, CFP2 and CFP4 cages are now the panel opening each standard
  prints, as `std/sfp@1` and `std/qsfp28@1` are: the box is the opening, `d`
  the bezel to the connector, `relief.size` the interior behind it, with the
  one 1.0 collar (#802). `std/cxp@2` is SFF-8642 Rev 3.3's 23.50 x 12.10
  cut-out, 28.96 deep, with the 21.60 x 10.20 snout opening behind it;
  `std/cfp@2` the CFP MSA Mechanical Layout's 82.8 x 14.8 opening, about
  126 deep (derived from a scaled figure); `std/cfp2@2` the CFP2 Baseline
  Drawing's 14.30-high opening at the 41.50 module width, about 87.5 deep;
  `std/cfp4@2` the CFP4 Baseline Drawing's 11.30-high opening at the 22.10
  faceplate width, about 67.9 deep. The `cxp`, `cfp`, `cfp2` and `cfp4`
  entries in `spec/schemas/standards.yaml` carry the same figures and a
  `cavity`; the CXP pitch floor is SFF-8642's printed 27.00 (was 30.0, an
  estimate) and the CFP2 floor the 42.50 faceplate (was 45.0, which the
  drawing's two modules per 86.35 opening contradicted). Every card that
  composes one (fourteen Juniper MICs and MPCs, five Nokia MDAs and NT cards,
  the Edgecore AMX-3200 sled) composes the second major, each port kept on
  its centre; the seventeen devices that seat those cards take a patch. A
  seated generic CXP, CFP, CFP2 or CFP4 optic sits where it did.
- `casa/ground-strap@2` composes `common/esd-jack@1` for its 4 mm wrist-strap
  jack instead of drawing its own circle, so the C100G's ESD point is the same
  part the Cisco and Juniper chassis place (#413). The skin keeps the marked
  plate and the earth symbol; the 1.x circle and its misnamed `bolt-hole`
  element are gone. `casa/c100g` 1.0.0 seats it, front and rear.
- A pull request records its change in a new file under `changelog.d/`
  instead of editing `CHANGELOG.md`, which every pull request used to edit at
  the same lines. Each file holds entries under `### Added`, `### Changed`,
  `### Removed` or `### Fixed`; `spec/tools/portrayal/changelog.py` checks
  them (a test runs it) and folds them into `## Unreleased` when a version is
  cut. Until then the unreleased record is that section followed by the
  fragments, and `changelog.py --show` prints the two together.
- `library/components/CATALOGUE.md` is no longer committed. `./build.sh`, and
  so `./publish.sh`, writes it at the same path, which is now gitignored, and
  `python3 spec/tools/portrayal/components_catalogue.py --library library
  --out library/components/CATALOGUE.md` writes it without a build. Its
  component total and its per-part device counts moved with nearly every pull
  request, so a committed copy conflicted as often as the changelog did. The
  test that compared the committed page with the generator now checks the
  generator: that it runs and that its page has a row for every component
  major.
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
- `dell/r660` took five majors between its first merge and 0.2.0, none of
  them in a release. Each is listed for a consumer of main or of the npm
  packages:
  - 1.0.0: riser 3 starts at x 270.6, where the cage of riser 2 ends, and
    slot 3 is back at 268.5 (#743). Before that, low-profile slots were
    re-handed (slot 1 turned over, slots 2 and 3 tip-left) and every riser
    gained its 3D boxes, as patches (#726, #729).
  - 2.0.0: the Gen5 riser print, riser configuration 9 and the redrawn E3.S
    blank, with the six removals listed under Removed (#749).
  - 3.0.0: the rears not yet drawn. `dell/riser-blank-full-16g@1` and five
    `<front>-rc0-none` configurations for no risers,
    `dell/rear-io-board-dlc-16g@1` for liquid cooling, and examples without
    a LOM card and with the MIC (#750).
  - 4.0.0: riser 2S, the liquid-cooling module `dell/dlc-module-1u-16g@1`
    and the PCH shroud in the top view. The heatsinks are `only-in` every
    configuration but the liquid-cooled example (#751).
  - 5.0.0: risers 2Q, 1P and 4P project into the top view, as estimates
    (`size-confidence: estimated`), and the gap that names them is renamed
    `risers-2q-1p-4p-from-above-estimated` (#753).
- `dell/r740xd` takes three majors, 24.0.1 to 27.0.0. No placement, bay or
  port id changes in any of them, and each major is one change:
  - 25.0.0 adds the example configuration `sff24-rc4-1a2a3a-connectx-100g`:
    the NVIDIA ConnectX-6 Dx MCX623106A in riser 2, `nvidia/mcx623106-fh@1`
    in slot 4 and `nvidia/mcx623106-lp@1` in slot 6 (#702). It joins six
    `only-in` lists, which the lock counts as a placement change. The device
    has 43 configurations.
  - 26.0.0 seats `common/drive-carrier-25@2` and `common/drive-blank-25@2`
    in every 2.5 inch bay, in place of the `@1` of each (#721). The bays keep
    their size and ids.
  - 27.0.0 states `chassis.ru: 2` (#741). The DCIM device types export 2U
    where they exported 1U, as the height entry in this section says.
- From 1.0, a retired component major is deprecated with the `superseded-by:`
  key the schema already has, naming the ref that replaces it, not with a new
  `deprecated:` marker as `spec/DESIGN.md` section 9 and
  `docs/format-stability.md` said. Nothing implemented the marker, so no
  manifest changes (roc-ops/Portrayal#448).
- **FS DINRAIL2U and DINRAIL4U 1.0.0: the rail panel meets its side
  brackets** (#971). The datasheet's 400 mm is the rail; the panel is the
  width between the brackets' inner faces, so it no longer stands about
  10 mm clear of each bracket in 2D and 3D. fs/dinrail2u-panel@2 (421.2 wide)
  and fs/dinrail4u-panel@2 (419.7) replace the @1 majors (see Removed).
  The joint is drawn as the side views show it: the brackets' edges are
  lowered between their ends, the panel's tabs lie on them, its flange shows
  through the slots and window, and two M5 screws a side stand over the
  slots, whole heads on the bracket's outer face, at the default setback (a
  new `screws` group, four placements).
- `common/drive-carrier-25@2` and `common/drive-blank-25@2` are the 2.5 inch
  carrier at its own face, 15.3 x 73.0 (#721). `@1` drew 17.868 x 79.4, which
  is the bay pitch and seam extent of the Dell R740xd and not the carrier.
  Four Dell drawings of the part agree on the new size. The art is the `@1`
  art rescaled onto that face, not redrawn, and the element ids are
  unchanged (`lamp-activity`, `lamp-status`, `features` on the carrier).
  `dell/r740xd` 26.0.0 keeps its measured 17.868 x 79.4 bays and seats `@2`
  centred in them; `dell/r660` seats the same carrier lying flat.
- A `kind: kit` placed in a view, accepted or defaulted by a bay (L5),
  composed as a part or seated in a component's bay (L10) is refused at lint
  instead of failing at render. A kit's `superseded-by` names a kit, and a
  component's names a component (L101). L43 stands down for
  `ears: {behind: true}` as for `ears: behind`.
- devicelock files `chassis.kits` as chassis surface beside `ears`, so stating
  either is a patch. A listed kit, its parts and its accessories join the
  device's `composed` digest, so a kit edited in place asks each device that
  lists it for a patch. L89 counts a kit a device lists as reached, with its
  parts, and `lint --device` lints the kits a device lists.
- The component catalogue and `composed-by` in `components.json` no longer
  count a kit as composing its parts or accessories.
- The generic rack ear is silver (`#c8cacc`, ears.py `SILVER`, relief.js
  `EAR.SILVER`) unless the device states otherwise, in `render.py --with
  ears`, the 3D viewer and the 2D overlay alike; it was drawn in
  `common/rack-ear@1`'s near-black, which relief.js `EAR.FILL` still names.
  Nothing published moves: no published face draws the ear.
- A DCIM outlet description names the fixed breaker it runs `through` as the unit
  prints it, `Through breaker A, lines L1-L2`, not by its placement id: the breaker
  placement's `attrs.label`, else its `attrs.section` (the G4 tile letter), else
  the id (decided 2026-10-09). The EVMI2130X re-exports with its outlet
  descriptions changed and takes a patch, 0.2.1.
- `common/ground-screw-m6@1` 1.0.1: its description no longer says it is never
  placed alone - the EVMI2130X places one as its M6 bonding screw. The four
  devices that compose it take a patch.
- `std/nema-5-20r@1` 1.0.1: its `unplaced:` sentence is gone, since the
  PDUMH20NET now seats sixteen of them. No other device composes it.
- `std/c19-outlet@1` 1.0.1: its `unplaced:` sentence is gone, since the
  PDUMV20HVNETLX now seats four of them. No other device composes it.
- Four Edgecore devices now record the AS number as `model` and the catalogue
  name as a `kind: marketing` alias, as the rest of the line does (#916):
  `edgecore/dcs500` is `AS7816-64X` (alias `DCS500`), `edgecore/dcs510` is
  `AS9716-32D` (alias `DCS510`), `edgecore/cor550` is `AS7926-40XKFB` (alias
  `COR550`) and `edgecore/cor580` is `AS9926-24D` (alias `COR580`). Each data
  sheet's ordering table names the base model by the AS number. Device slugs
  are unchanged. No DCIM export is renamed: device types are named by SKU, and
  those of these four boxes and of the Arrcus, DriveNets, IP Infusion and SONiC
  listings of them keep their file names and `model`; their comments now list
  the catalogue name under "Also sold or listed as". The AIS800 line keeps
  `AIS800-*` as its model: its current data sheets and quick starts print no
  AS number, and `AS9817-64O` is recorded as a superseded name.
- **The end allowance is per media, sourced, with a temporary dressing
  allowance beside it** (`@portrayal/kit` 0.16.0, #962;
  `docs/cable-lay-design.md` section 1.6). A routed length was the path plus
  0.15 m an end, a figure with no source. The sourced part is now a table,
  `END_ALLOWANCE_BY_MEDIA`, of what is physically there and not in the path:
  at each end, the part of the plug inside the port and half the maker's
  short tolerance. It is 13.1 mm for LC fibre (generic/lc-plug@2; FS fibre
  cords are +x/-0), 34.5 for copper and a cable with no media (9.5 of
  generic/rj45-plug@1, and half of the 1 per cent a Brand-Rex Cat6A cord may
  be short at 5 m), 25 for a DAC (half the FS SFP+ DAC's +/-5 cm; its length
  is measured between the heads) and 52.4 for an AOC (generic/qsfp-cable@1's
  head in the cage; L-com's AOC is +x/-0). The LC and RJ45 plug depths rest
  on estimates, which section 1.6 lists. Service loops and dressing slack
  belong in explicit tray slack (#949 step 4), which is not built yet, so
  until it is the kit adds a dressing allowance of 0.1 m an end on top, for
  every media: temporary, by decision, with no maker's source, and not
  exported. `endAllowance(cable)` gives the two together (113.1, 134.5, 125
  and 152.4 mm an end) and `routePath` returns it as the path's `allowance`,
  which `pathLength` adds (a path without one takes the copper figure);
  both, with `END_ALLOWANCE_BY_MEDIA`, replace `END_ALLOWANCE_M`. A routed
  length is 73.8 mm shorter for LC fibre, 31 for copper and 50 for a DAC,
  and 4.8 mm longer for an AOC. On the reference rack of #949 seven of the
  sixteen cords move from 1 m to 0.5 m; on a 3,120-cable generated sample
  221 move down a stock size and one moves up. A saved rack's routed lengths
  and stock sizes are re-measured the next time a page measures them; an
  entered length is never touched. BREAKING for a page that imports
  `END_ALLOWANCE_M`. Code that took the allowance back off a length,
  `measured - 2 * END_ALLOWANCE_M`, must subtract twice the path's
  `allowance` or `endAllowance(cable)`; `END_ALLOWANCE_BY_MEDIA[media]` is
  the table alone, and would leave the result 0.2 m long.
- **The per-media table is `END_ALLOWANCE_BY_MEDIA`** (`@portrayal/kit`
  0.18.0, #962). In 0.16.0 and 0.17.0 its name differed from
  `endAllowance(cable)` only by case, for figures 100 mm apart. No kit
  version after 0.2.0 is on npm, so no published kit carried that name. The
  table is the sourced part alone; `endAllowance(cable)` and a path's
  `allowance` are what a length adds an end, the table's figure and the
  dressing allowance. The old name is not kept as an alias. No figure and no
  routed length changes.
- L44 also reports decor whose box lies wholly outside its view's drawing - the face
  plus every placement the default build draws beyond it - where it is never seen (#878).
- Lint L43 stands down when the body itself is as wide as the rack face
  (`chassis.width` at or above the generic ear's 480 mm threshold,
  `ears.EAR_WIDE`): a blanking plate's ears are built into its face, so the
  face is the part (decided 2026-10-09). A body narrower than that,
  drawn with a rack-wide front and nothing seated in its ears, still warns. No
  existing device changes; L43 had no hits in the library.
- `chassis.airflow` takes `top-to-bottom`: air drawn in at the top face and
  pushed out of the bottom, as a rack fan tray blowing down through the rack
  does. It exports as `top-to-bottom`, NetBox's own value; Nautobot's device
  type has no airflow field. The FS FANS1U2F and FANS1U4F state it.
- `common/rocker-switch@1` (1.2.0) takes a `rocker-color` field that tints the
  rocker. Empty by default, so every existing rocker draws as before; its two
  surfaces' 3D sides now follow the painted art. The FANP3U3F's rocker is red.
  WS-C4948E (0.1.4) and GL-12xB-240D (0.1.5) take a patch for the new part.
- `fs/cmh-4drb1u-ring@1` 1.1.0 declares its ring guide, a 37.2 x 74.8 mm
  opening run along the rack, so every FS ring carries one. `fs/cmh-4drb1u`
  1.0.2 for the composed change; its drawings gain only the guide attributes.
- `fs/uscmh-sfdabs1u`, `fs/uscmh-sfdabs2u` and `fs/uscmh-sfdabsb1u` 0.1.1
  carry an ESTIMATED cable capacity (33, 116 and 70 Cat6 24AWG cables at
  100% fill), which FS states nowhere for these ducts: each channel's
  cross-section at 39.9 mm2 a cable, the ratio in the capacities FS does state
  for the CMH-SFD1U, CMH-DFD1U and CMH-SFD2U. `cable-capacity-basis` says it is
  an estimate, and the vendor-silent gap stays, noting the figure carried.
- devicelock keeps `chassis.ears.h` and `y` as surface now that an ear is drawn
  from them, since that ear is never in a published face; the reasoning is in
  `docs/format-stability.md`, which also now says a kit's missing
  `description` is published as an empty string, as the code always wrote it.
- UfiSpace grounding points are one M4 pair host where they were two
  `common/ground-lug@1` studs 11.0 or 13.0 apart (#830). The accessory lug is
  fixed with two M4 screws, and the flank figures of seven guides - three
  distinct drawings, one shared by four guides and one by two - read the holes
  15.6 to 15.9 apart, the 5/8 in. pattern; each landing is re-anchored where
  its own figure puts it, about 16.4 behind the front face. **Breaking for
  anything holding the old placement ids** `ground-1` and `ground-2`, now
  `ground-screws`; each device takes one major: M3000-14XC 4.0.0, S9500-22XST
  3.0.0, S9501-28SMT 4.0.0, S9502-16SMT 2.0.0, S9510-28DC 6.0.0 (its two
  stand-in cutouts and its unsourced flank GND legend are gone), S9510-30XC
  4.0.0, S9511-20CT 3.0.0. The second grounding location the 302 mm guides
  draw is recorded as a gap, not drawn.
- UfiSpace S9601-104BC (4.0.0): the grounding lug is on the LEFT flank at its
  rear end, as HIG Figure 20, the vendor render and the boss on the rear
  elevation show, not on the rear strip. `ground-1`, the upper hole of a pair
  drawn on the rear, is gone with the pad behind it; `ground-screws` is one M4
  pair host on the left view, its depth estimated and a gap saying so (#830).
- Edgecore grounding plates drawn as one stud are their two screws (#830):
  `common/ground-lug@1` on the screw the printed earth symbol sits by and
  `common/ground-screw@1` on the other, so each plate keeps one symbol. No pair
  host fits:
  - DCS500 (3.0.0): each plate is `ground-1` and `ground-1b`, `ground-0` and
    `ground-0b`, M5, 17.2 apart on the datasheet rear, which is no two-hole lug
    pattern, and a gap records it. The 14 x 7 cutouts are gone: the plates are
    plain;
  - EPS112 (2.0.0), EPS203 (2.0.0) and AGR560 (3.0.0): `ground` is now
    `ground-1` and `ground-2`, one above the other, 16.3, 16.2 and 16.1 apart as
    read off the rear photographs and datasheet elevations, unsized because no
    document names the screw. **Breaking for anything holding `ground`.**
- Ground points drawn as two studs, or as one stud standing for a pair, are one
  pair host at the pitch of the two-hole lug their documents call for (#828,
  #830). **Breaking for anything holding the old placement ids**; each device
  takes one major:
  - the eleven Amphenol 300CB08 panels (300CB08, -C, -SC, the six nrg300CB08
    CTRL and SENS versions, nrgILS300CB08 and its -SC), 2.0.0: each of the three
    landings is `common/ground-stud-pair-5-8-1-4@1` at 15.875 (was two
    `common/ground-stud@1` 15.9 apart), ids `ground-bottom`, `ground-left`,
    `ground-right`;
  - Edgecore AIS800-64D and AIS800-64O, 4.0.0: `ground-screws`, one
    `common/ground-stud-pair-5-8-m6@1` (was `ground-screw-1` and `-2`, 16.2
    apart). The 5/8 in. is inferred from the lug the guide names, and a gap
    says so. The earth symbol above the plate is drawn;
  - Nokia 7360 FX-16 (nfxs-d-ba), 1.0.0: `ground-left` and `ground-right` are
    `common/ground-stud-pair-1-1-4@1`; FX-8 (nfxs-e-bb) and FX-4 (nfxs-f-bb),
    1.0.0: `ground` is `common/ground-stud-pair-3-4-1-4@1`, stood on end;
  - Nokia Lightspan MF-8 (lmfs-f), 1.0.0: `ground-studs`, one
    `common/ground-stud-pair-5-8-m6@1` at 15.875 (was `ground-stud-1` and `-2`,
    16.3 apart): the manual's 16 mm (0.63 in.) is 5/8 in. rounded. Its ESD
    point moves out of `grounding` into its own group, `esd` (#866).
- Casa C40G (0.5.16): no change to the terminal. Its `ground-stud-count` gap
  records that the guide's lug points at 5/8 in. and at horizontal or vertical
  mounting, and why the pair waits.
- The Juniper MX ground studs are pairs a two-hole lug spans (#828), each
  device a major. `juniper/mx80` 2.0.0, `mx240` 2.0.0 and `mx480` 2.0.0 (a
  vertical pair, was 14.0 / 13.2 / 13.2 apart) and `mx104` 3.0.0 (was 16.0)
  place one `juniper/mx-ground-stud-pair-5-8@1` at the 0.625 in. their guides
  state; `mx150` 2.0.0 places `juniper/mx-ground-stud-pair-3-4@1` at 3/4 in.,
  inferred from the lug its guide names (was 13.0). The placements
  `ground-stud-0` and `ground-stud-1` are gone: the pair is `ground-studs`, its
  studs `ground-studs/1` and `/2`. `mx204` 4.0.0 seats
  `juniper/mx204-ground-plate@2`, two 10-32 screws on the guide's 0.75 in.
  (@1 drew 16.0, and is removed); the plate is the pair, its screws
  `ground-plate/1` and `/2`. `mx304` 4.0.0 seats
  `juniper/mx304-ground-plate@2`, two M6 screws one above the other on 5/8 in.,
  the guide's "0.63-in. (16-mm) centers" (@1 drew 16.0, and is removed); its
  screws are `ground-plate/1` and `/2`.
- ESD jacks on the MX80, MX150, MX204, MX240, MX304 and MX480 are in a group of
  their own, `esd` (Point, furniture), not `grounding` (#414). The MX204's laser label moved from `grounding` to a new
  `furniture` group. A placement moving group is breaking for anything that
  addressed it by group.
- L116's depth arm reads where a spanned part PRESENTS, its placed `lift` plus
  its own seat out, rather than its `lift` alone. Nothing the library placed
  before changes: an LC bore presents at its own face. A stud presents at its
  top, which is where a lug across a pair lies (#828).
- `<device>.configs.json` publishes `chassis.ears` as an object, always: the
  bare `ears: behind` is `{"behind": true}`, and an object is published with
  the keys it states, lengths as floats (#907). `fs/uscmh-sfdabsb2u`, the one
  device that states `ears`, publishes `{"behind": true}` where it published
  `"behind"`, and its NetBox and Nautobot exports gain one comment line saying
  its ear flanges fold back behind the body. The string form was never in a
  release. Documented in `docs/format-stability.md`.
- The L5 catalogue text says what the rule checks: no placement ref, and no
  bay's `accepts` or `default`, is a `kind: kit`.
- Lint L109 judges a polarity only at a width a held source draws it at
  (`POLARITY_WIDTHS`: Type A and AF at 12 and 24 fibres, universal at 12, all
  from the FHD MTP-12/24 Cassettes Datasheet). At any other width it warns
  "polarity not judged at this width" instead of passing or failing a
  generalisation (roc-ops/Portrayal#524). One library part is affected:
  `fs/fhd-fap12mtp16-a@1` declares Type A on twelve MTP-16 adapters, a width
  no held source draws Type A at, and now carries that warning where it used
  to pass.
- Every horizontal Juniper MIC is its own plate, 168.8 x 29.2, measured off
  the MX104 and MX80 front photographs (#261). It was the estimated 168 x 27
  "window". The 20 single-wide MICs take a major (`juniper/mic-3d-4xge-xfp`
  @2 to @3, the others @1 to @2) and their art is re-enveloped, not redrawn.
  The two dual-wide MICs, `juniper/mic-3d-40ge-tx@2` and
  `juniper/mic3-100g-dwdm@2`, are one 338.1 x 29.2 plate across both MIC
  slots, as the MX2010 photograph shows a dual-wide MIC.
- The MICs the photographs show are drawn from them:
  - `mic-3d-2xge-xfp@2` has its cages at 45.4 and 91.75 along the plate,
    where they were at 25.75 and 54.75.
  - `mic-3d-4xge-xfp@3` has its cages at 31.8, 65.9, 99.8 and 133.7, a 34.0
    pitch, read off the MX2010. The Figure 31 reading it replaces was about
    3% stretched.
  - `mic-3d-20ge-sfp@2` has its two five-cage blocks centred at 46.85 and
    121.4.
- `juniper/mpc1e-3d@3`, `mpc2e-3d@3` and `mpc3e-3d@3`: the two MIC bays are
  the measured plate, abutting at the card plate's centre (x 37.7 and 207.0,
  y 0.15).
- `juniper/mx104` 4.0.0: the MIC bays sit on the measured 169.3 pitch
  (x 17.8 / 187.1; it was 175.2) and at rows y 42.6 / 74.1, which were 6 to
  7 mm low.
- `juniper/mx80` 3.0.0: the MIC bays sit at x 28.7 / 198.3, y 6.5.
- `juniper/mx240` 4.0.0, `juniper/mx480` 4.0.0 and `juniper/mx960` 3.0.0
  seat the @3 carriers.
- `juniper/mx2008`, `juniper/mx2010` and `juniper/mx2020` 1.0.0:
  - Each LC slot seats the new adapter card. The slots are the adapter's
    43.18 x 449.8 on a 43.18 pitch, which three front photographs confirm.
    They were an estimated 41.0 x 425.0 on 41.0.
  - The native MX2K cards and the slot blank keep their estimated size,
    centred in the slot.
  - The MX2010 gains a `photographed` example configuration.
- `nokia/m2-oc192-xp-xfp` 1.0.1 names `juniper/mic-3d-1oc192-xfp` without
  the major it retires; `nokia/sr-7` and `nokia/sr-12` take the patch.
- Deprecated, not deleted: each part below stays in the library, marked
  `superseded-by:` its replacement and given a patch bump, so a manifest
  that pins it still resolves (#448). No device seats them any more.
  - The eleven MX2000 vertical card twins, `juniper/<base>-v2k@1` for
    `mpc-3d-16xge-sfpp`, `mpc1e-3d`, `mpc2e-3d`, `mpc3e-3d`,
    `mpc4e-3d-2cge-8xge`, `mpc4e-3d-32xge-sfpp`, `mpc5e-100g10g`,
    `mpc5e-40g10g`, `mpc7e-10g`, `mpc7e-mrate` and `ms-mpc`, each superseded
    by `juniper/<base>@2` (`@3` for the MPC1E/2E/3E), which the MX2000 slots
    seat inside `juniper/mx2000-lc-adapter@1`.
  - The twenty vertical MIC twins, `juniper/<mic>-v@1`
    (`mic-3d-4xge-xfp-v@2`), each superseded by the horizontal MIC's new
    major. `juniper/mx-mic-blank-v@1` is live, because the native MPC8E and
    MPC9E seat it.
  - The old majors of the 22 MICs, blank included (`@1`;
    `mic-3d-4xge-xfp@2`), and of the three carriers (`@2`), each superseded
    by its next major above.
- The DCIM module export leaves out a contract that carries
  `superseded-by:`. A retired major shares its successor's model, and
  exporting both wrote one file twice. `components.json` now carries the
  `superseded-by` field.
- The MPC1E, MPC2E and MPC3E carriers (`juniper/mpc1e-3d`, `mpc2e-3d`,
  `mpc3e-3d` and the `-v2k`/`-v960` form of each, 1.2.0) are each their base
  SKU and nothing else (#417). `power-draw-max-w` is the base row of the MX240
  guide's Table 93: MPC1E 175 -> 165 W, MPC2E 294 -> 274 W, MPC3E 440 W. Each
  bay's `accepts` is exactly that SKU's column of the Interface Module
  Reference Tables 10-12, so the MPC1E no longer takes the 4x10GE XFP, the
  10GE SFP-E, the ATM or the three channelized/CE OC3 MICs, the MPC2E no
  longer takes the 10GE SFP-E, the ATM or those OC3 MICs, and the MPC3E no
  longer takes the 4x10GE XFP, the 10GE SFP-E or the ATM MIC; the MPC3E now
  takes the OC192 XFP, both multirate OC3/OC12/OC48 MICs, the DS3/E3, the
  MACsec 20GE and the MS-MIC-16G. `model-variants` keeps only the SKU that
  shares the row and the column (MX-MPC1-3D, MX-MPC2-3D). The queuing, P and
  NG SKUs are not these contracts and will be their own parts. The MX240,
  MX480, MX960, MX2008, MX2010 and MX2020 take a patch.
- **BREAKING for DCIM data already imported:** the MPC3E module type is now
  named by its part number, `MX-MPC3E-3D`, not its component name `MPC3E`
  (#417). Its NetBox and Nautobot module-type file is renamed to match, and an
  import keyed on the old model creates a second module type rather than
  updating the first.
- **BREAKING for DCIM data already imported (Nautobot):** no carrier now
  takes `MIC-3D-10GE-SFP-E` (#417; it fits only the NG MPCs, which are not
  modelled yet), so its Nautobot module type names its ports
  `{module}/port-0-N` instead of `{module.parent}/{module}/port-0-N`. The six
  MICs no carrier takes say so in `unplaced:`.
- `juniper/mic-3d-4xge-xfp@2` and `mic-3d-4xge-xfp-v@2` (2.0.0): the four XFP
  cages are re-laid from the Interface Module Reference's Figure 31
  (g100580), measured on the embedded image and scaled on the 19.5 mm XFP
  opening, at a pitch of about 32.7 mm instead of the guessed 22.0 and 21.1
  mm (#238). The card keeps its size. The MPC2E carriers seat the new
  majors. The cage positions are ESTIMATED: photos of the MX104 and MX80 put
  the MIC plate at 168.6 mm and the XFP bezel at about 21 mm, which would
  make the figure's pitch about 35 mm; #261 re-measures this MIC from the
  MX104 photo.
- `generic/qsfp-mpo@1` and `generic/qsfp-dd-mpo16@1` (1.0.2) default the pull
  tab to the neutral grey `#6f6f6f`, not beige (#773). Beige is SFF-8679's code
  for 850 nm, and an MPO face is also the face of single-mode PSM4, DR4 and DR8
  optics, so the generic drew those as multimode. A vendor wrapper states the
  colour its wavelength calls for, as it does on `generic/qsfp-lc@2`; no
  wrapper in the library composes either generic yet.
- The MX240, MX480 and MX960 card is one part, drawn once: the 22 horizontal
  MX card contracts (`juniper/scb-mx`, `dpc-r-4xge-xfp`, `dpce-20ge-2xge`,
  `dpce-2xge-xfp`, `dpce-40ge-tx`, `dpce-q-20ge-sfp`, `dpce-r-40ge-sfp`,
  `mpc-3d-16xge-sfpp`, `mpc10e-10c-mrate`, `mpc10e-15c-mrate`, `mpc1e-3d`,
  `mpc2e-3d`, `mpc3e-3d`, `mpc4e-3d-2cge-8xge`, `mpc4e-3d-32xge-sfpp`,
  `mpc5e-100g10g`, `mpc5e-40g10g`, `mpc7e-10g`, `mpc7e-mrate`, `ms-dpc`,
  `ms-mpc`, `mx-dpc-blank`) are @2 at 413.5 x 29.5, the ejector-lever
  envelope of Juniper's Visio stencil, with a 396.0 plate centred in it,
  measured off the MX240, MX480 and MX960 front photographs (#261). Their art
  is re-enveloped, not redrawn. The levers, the model name and the OK/FAIL
  status group are re-placed from the photographs, and the MIC windows of
  `mpc1e-3d`, `mpc2e-3d` and `mpc3e-3d` from the MX2010 photograph's ratios.
  On the 13 layout-derived cards, the port layout moves 8.4 mm right to clear
  the lever. `mx-dpc-blank@2` draws the blank's own short knobs and its 0/1
  mark instead of card levers.
- `juniper/mx240` 3.0.0 and `juniper/mx480` 3.0.0: every card slot is the
  card's 413.5 x 29.5 envelope at x 28.5, centred on the measured plate, with
  a 396.0 x 29.5 `opening`. The slot pitch is 31.0 on the MX240 (was 30.45) and
  31.3 on the MX480 (was 31.86; the photograph reads 31.2-31.5). The grey
  slot-number tab strip the plates no longer cover is chassis decor, with the
  slot numbers on their tabs. The MX480's front scale note is corrected: the
  photograph is isotropic to 0.8%, not 5.1% anisotropic.
- `juniper/mx960` 2.0.0: its fourteen slots seat the same horizontal cards at
  `rotate: 90`, footprint 29.5 x 413.5 with a 29.5 x 396.0 `opening`, on a 31.0
  pitch (was 30.1). The SCB slots take `juniper/scb-mx@2` (superseded: `@3`
  at 0.2.0, #891), so an MX960 SCB now
  offers the RE-S-2000 as well as the RE-S-1300. The MX960 device type's `Accepts:`
  descriptions name the horizontal cards. Each module type's export comments
  now name one fewer author.
- `smartoptics/ppm-ad1-1510@2` and `ppm-ad1-1625@2` (2.2.0 to 2.3.0) state
  their add direction as a `combine` onto Line Tx, from the signal-flow
  figures of ds-ppm-r4.0. It was written as banded legs off the line port
  while the vocabulary had no combine. The glass is the same: every port and
  every fibre-map row is what it was, and the fibre maps do not change at
  all. `smartoptics/dcp-2` composes both and takes the patch the lock asks
  for (2.1.2 to 2.1.3). The only lines of any export that move are the
  version sentences in `comments`: the contract version on the two filters'
  module types and the drawing version on the DCP-2 device types.
- `docs/optical-paths-design.md` records the combine form, how a path reads
  in both directions, and that `optical.trunk` is the statement of an
  endpoint's role: a position it names, or a rear face carries, is a trunk,
  and every other routed position is a branch.
- Lint L108 now checks stacked OSFP cages, which it used to skip. A stacked
  OSFP cage is one connector that seats both modules heat sink up (OSFP MSA
  rev 5.22 section 7.1, Table 7-1, Figures 7-1 and 7-2), so an OSFP pair has
  to be turned alike: 0 over 0, 180 over 180 for a cage on the underside of
  the board, or both 90 or both 270 on a card drawn on its side. SFP, QSFP
  and QSFP-DD stacks are still belly-to-belly (upper 0 over lower 180). An
  OSFP pair turned 0 over 180 needs a recorded reading in
  `stack-exceptions:` (#799).
- `edgecore/ais800-32o` 2.0.0: the lower OSFP row is now drawn the same way
  up as the upper (rotate 0), as the quick start guide's elevation and its
  install render show. Two optics seated in one column no longer overlap
  nose to nose by 1.66 mm. 0.06 mm of overlap remains because the drawn row
  pitch is 14.54, against the MSA's 14.90. Its DCIM exports change in the
  drawing version line only (#799).
- `celestica/ds4100` and `celestica/ds4101` 0.1.1 keep their lower OSFP
  rows turned 180, and now say why: each install guide's elevation draws the
  lower cage as the upper turned over. Their 18.9 and 18.4 mm row pitches
  leave room for a board between the rows, so these are single cages on both
  faces of one board rather than stacked cages. Each pair is named in
  `stack-exceptions:` (#799).
- `celestica/ds5000`, `ds6000` 0.1.1, `ds6001` 0.1.2 and
  `edgecore/ais800-64o` 4.0.1 keep their OSFP turns for now. Each pair is
  named in `stack-exceptions:`, and a new `stacked-osfp-orientation` gap says
  what would settle it. Their drawings read as the lower bank turned over
  (0/0 over 180/180), which neither the current geometry nor the first #799
  proposal matches. `ufispace/s9321-64eo` 1.0.16 corrects a provenance note
  that still said OSFP stacks were not checked (#799).
- `off` in the Explorer is a state that can be lit, not only the absence of
  one: the `off` chip sets `state-off` on an outlet (so a G4 outlet lamp shows
  its declared red, or a lamp-less outlet dims) and on any element that
  declares a colour for `off`, and clears only a lamp or a plain element with
  none, as before. `states.js` `paints` measures a declared `off` rather than
  assuming it. A custom lamp colour is not shown on a lamp that is `off`
  however it came to be off - its own mark, another mark, or its outlet - in
  2D as in 3D.
- `juniper/mic-3d-4xge-xfp@4`: the four ports are named for the module
  reference's pic/port numbering (Figure 31: [0/2]0, [0/2]1, [1/3]0, [1/3]1),
  `port-0-0`, `port-0-1`, `port-1-0`, `port-1-1`, as `mic-3d-2xge-xfp` names its
  two; 3.x named them `port-0-0` to `port-0-3`. Each port gains its LINK lamp,
  `led-link-<pic>-<port>`, with the reference's states (off, green on link)
  (#887). `@3` is retired with `superseded-by` and stays accepted by
  `juniper/mpc2e-3d@3` (3.1.0), which now accepts `@4` too.
- `juniper/mx2010` 2.0.0: its vendor-photo configuration seats the new MIC in
  LC0 and LC6. **Breaking for DCIM data already imported**: the third and fourth
  port of each of those MICs is renamed. `mx2008`, `mx2020`, `mx240`, `mx480`
  and `mx960` take a patch for the carrier change.
- `juniper/dpc-r-4xge-xfp@3`: the four XFP ports sit on the 76.1 mm pitch the
  MX240 and MX480 photographs agree on (card x 105.55 to 333.8, y 18.85), with
  each port's TUNNEL and LINK lamps side by side to its left and its legends
  printed upward, as photographed; 2.x had them on a 53.4 pitch from x 95.5
  (#891).
- `juniper/scb-mx@3`: the Routing Engine bay is 271.9 wide, to the right end
  both photographs put the RE plate at (it stopped 9.5 mm short), and the SCB's
  two panel screws are where the photographs show them (#891).
  `juniper/re-s-1300@2` and `juniper/re-s-2000@2` take the same width and draw
  the plate's right captive screw.
- `juniper/dpce-r-40ge-sfp@2` 2.1.0: the card's own OK/FAIL lamp under its
  legend, with states ok, fail and absent from the module reference (#891,
  #899).
- `juniper/mx240` 5.0.0, `juniper/mx480` 6.0.0, `juniper/mx960` 4.0.0: their
  slots accept the new majors. Ports keep their ids.
- `juniper/mx104` 5.0.0: the fixed panel and the supply/Routing Engine band
  re-placed off the front photograph on its checked scale (#901). The four XE
  ports are discrete `std/sfp@1` cages on a 17.2 mm pitch at y 28.2 (they were a
  ganged row at 14.25, y 25.2); the ALARM connector, the ONLINE/OFFLINE button,
  the SYS OK lamp, the timing RJ45s and SMBs and their legends move to the
  photograph's positions; the band starts at y 105.5, the second supply moves
  8 mm left and both Routing Engines 36 mm left, with the side cover beside
  them. The fixed-panel decor stops at the MIC plates, y 42.4.
- `juniper/mx80` 4.0.0: the fixed XFP cages on the photograph's 31.3 mm pitch at
  y 71.4 (29.4 before), with their LINK lamps right of each cage; the console,
  AUX, Ethernet, USB and clock jacks, the status lamps and the button re-placed
  on the same scale; the USB jack lies horizontal, as photographed (#901).
- Both devices gain a gap for what the photographs show and nothing draws yet.
- MX2000 upper cages on the guides' 1.7 in slot (#902). `juniper/mx2010` 3.0.0
  and `juniper/mx2020` 2.0.0 place CB-RE 0, SFB 0-7 and CB-RE 1 as ten 43.18 x
  412.1 mm slots (1.7 x 16.225 in, the guides' physical tables) over the
  line-card slots, as the front photographs show; they were 55- and 40-wide
  estimates, 405 high. `juniper/mx2008` 2.0.0 does the same at the photograph's
  182 mm height, y 109-291 (it was 170 high at y 143); its guide's Table 98 rows
  for the MX2008 RCB (16.225 in) and SFB2 (16.23 in) carry the MX2010's heights,
  and the disagreement is recorded as a gap.
- New majors at the new size:
  `juniper/mx2000-cb-re-v@2`, `mx2000-cb-re-128g-v@2`, `mx2000-cb-re-1800-v@2`,
  `mx2000-sfb-v@2`, `mx2008-sfb-v@2` and `mx2008-rcb-v@2`. Their faces are
  re-centred, not re-read; port ids are unchanged.
- `juniper/mx480` 5.0.0: the front vent band and the front ESD point are
  re-placed on the photograph's body scale (#892). The band now runs x
  19.5-417.6, y 4.7-30.6 (it was 310 mm wide at x 20), and the ESD jack, its
  cutout and its mark move from (8, 20) to (16.1, 28.2). Both had been read at
  the ear-inclusive 3.379 px/mm scale the 3.0.0 slot rework retired.
- `juniper/mx960-blank@1` 1.1.0 carries `model: DPC-SCB-BLANK`, the MX960
  guide's Table 5 part number (#899). **Breaking for DCIM data already
  imported**: its module type is renamed from `mx960-blank` to `DPC-SCB-BLANK`.
- `juniper/mx960-craft@2`: the fourteen slot clusters sit where the MX960
  photograph puts them relative to the slots, at 16.65 + 31.40 k, instead of on
  the retired 30.1 slot pitch (#899).
- `juniper/mx960` 5.0.0: a new orderable `ac` configuration, the chassis as
  photographed (DPC 40xGE in slots 1 and 3, DPC 4x10GE in 7 and 9), so a seated,
  turned line card renders in the build and in CI (#899).
- `juniper/mx240` 5.0.1, `mx480` 6.0.1, `mx960`: a `slot-pitch` note on why the
  three chassis read 31.0, 31.3 and 31.0 for one card, and why the guides'
  1.25 in is the card's height and not a pitch (#899).
- `eaton/evmi2130x` 0.2.0: `metering-scope: branch` and `outlet-switching:
  false` (class `metered-branch`), the structured input keys with `input-plug:
  nema-l21-30p` and its voltage prose moved into `input-ac`, `lines` on its three
  breakers (A L1-L2, B L2-L3, C L3-L1) and `through` on its 42 outlets. Its
  exported outlets now say which breaker and lines they are on, and its input
  power port carries the rating. No outlet states `feed_leg`: every one is line
  to line.
- `eaton/g4-mounting-button@1` 1.1.0: `mates: pdu-button` and a `mate` point on
  its axis.
- **Routed lengths start at the plug's reach** (`@portrayal/kit` 0.13.0,
  #960; `docs/cable-lay-design.md` section 1.5). A cable leaves the far end
  of its plug, so each `routePath` now starts and ends with a straight
  stretch out of the port's face, to a new point `at: 'reach'` (with `end`),
  and its first and last legs, their detours included, run from there. The
  reach is the page's `ctx.plugReachOf(end, cable)` when it gives one, else
  `PLUG_REACH` by media: 27.6 mm for LC fibre (generic/lc-plug@2 and
  common/lc-boot@1), 39.4 for copper and a cable with no media
  (generic/rj45-plug@1 and common/rj45-boot@1, with the boot taken to abut
  the plug, so it may err long by a few mm), 64.8 for a DAC or an AOC
  (generic/qsfp-cable@1). The 0.15 m end allowance is unchanged at 0.13.0
  (kit 0.16.0 replaces it with a per-media allowance, #962): it is the
  dressing slack, and the plug was always along the first leg, which the
  reach turns into a dog-leg rather than lengthening by a plug. Almost every
  routed length grows, by what the dog-leg out of each plug adds (median about 43 mm on a
  780-cable sample) and by up to about 0.33 m where the reach puts a leg over
  a tray floor, so it goes round the tray's front edge; one cable in six
  to eight moves up a stock size. On the reference rack of #949, c7 and c9 to c14
  move from 0.5 m to 1 m stock (c9 to c12 measured 0.494 to 0.496 m from the
  port faces, 0.517 to 0.524 m now). A saved rack's routed lengths and stock
  sizes are re-measured the next time a page measures them; an entered
  length is never touched. A plug in a panel port behind a deep shelf is now
  a `crosses-body` finding ("at its port on ...").
- `patch` with a new `cfg` and no `swaps` or `fields` clears both; naming the
  default of a device whose file leaves `cfg` empty is no change. With parts
  lists loaded, `place` and `patch` refuse a configuration the device does not
  list, and `patch {swaps}` leaves out, and names, what a slot does not take.
- `describe` starts with a totals line (`Rack 1 (r1): 6 items, 40 cables.`);
  the frame follows on its own line.
- The command descriptions name no function and no page: `describe()`,
  `freePorts()`, `catalog()` and the Explorer are gone from them.
- `fs/cmh-6dr1u` 1.0.0 draws its front at the 482.6 mm rack face with its ears, and
  its two end rings 43 mm past each, where they were a gap; it states
  `overhang: {left: 43, right: 43}`. Its D-rings move 26.3 mm right on the
  wider face; the moved geometry takes the major. Its DCIM exports gain the
  overhang comment.
- `nokia/lmfs-f` 1.0.1 states `overhang: {right: 47}`, the reach of its horizontal
  front dust filter past the right flange, which it already drew in the
  front-cover configuration; nothing on the drawing moved. Its DCIM exports
  gain the overhang comment.
- A drawing bigger than its face (a part beyond it grows the viewBox) carries
  the face it declares as `data-face-w` and `data-face-h` on its root, and the
  3D viewer lays the face out on that rather than on the drawing's extent, so
  the face is centred and a part beyond it stands beyond the plate. A drawing
  that fits its face is unchanged. A sheet body's rack face builds no 25.4 mm
  plate (#865).
- The rule for a retired component major is stated the same way in
  `spec/DESIGN.md` section 9, `docs/format-stability.md` and
  `library/components/README.md`. While the package is at 0.x, a superseded
  major may be removed, and every removal is listed in `CHANGELOG.md` with the
  ref that replaces it. The deprecation mechanism is required before 1.0: the
  `superseded-by:` marker, a stated support window, and L89 telling a
  deprecated major from a dead one. No lint behaviour changes
  (roc-ops/Portrayal#448).
- `library/components/README.md` says that moving decoration nothing
  addresses, inside an unchanged part outline, is a minor bump, and names
  `fs/d-ring-snap-in@1` 1.3.0 as the precedent (#968).
- `@portrayal/kit` 0.5.0: a routed cable passes THROUGH a D-ring along the
  ring's `run`, not to a point inside it (#930). Each ring waypoint becomes
  the point where the cable enters, on the side of the point before it, and
  the point where it leaves, half the ring's `depth` either side of its centre,
  with a straight run between them. A ring that states no depth is taken as
  `RING_DEPTH`, 10 mm, marked estimated. The new `routePath(rack, cable, ctx)`
  is that path, and it decides each ring once, in the rack's frame: which way
  through, or not through at all. `routedLength` (`pathLength`), `fill`,
  `capacityOver` and `inspect` (`route.rings`) read it, and `ringMarks(rack,
  cable, ctx)` hands its decisions to the drawings: `routed2d` and
  `routePoints3d` take them as an optional last argument, draw each ring the
  way it was decided, and round their corners outside it (`throughRings` in
  `rack/route-path.js`). A mark's sense is in the rack's axes; a drawing that
  flips one turns its marks with `orientMarks` (a front elevation `{y: -1}`,
  the mirrored rear pane `{x: -1, y: -1}`), and `reverseMarks` serves a path
  drawn from its other end. A route that would enter and leave a ring by one face
  is not drawn through it, is counted neither in that ring's fill nor in its
  manager's capacity, and is reported by `ringFindings(rack, ctx)`. A point
  further off the run in the face than along it (a port well below the ring)
  stands on neither side; a manager's stand-off out of the face does not
  count. The automatic route takes only the rings on the way from the port to
  its gutter, no longer a ring behind the port.
  **Routed lengths change**: a ring adds up to its depth, and a cable whose
  automatic route used to double back through a ring is up to about 100 mm
  shorter. Stored routed lengths are re-measured the next time a page
  measures them; an entered length is never touched. Ducts and pass-throughs
  keep a single point. The Rack Builder's half (re-vendoring, passing `run`
  and the ring marks to the drawings, showing the findings) is listed in
  `docs/cable-managers-design.md` section 13.
- **A ring is solid, and a route enters it through its opening**
  (`@portrayal/kit` 0.15.0, #968). `solidsOf` places a ring's parts with the
  other solids; `legCrossings` and `detour` meet them with the cable's tube,
  the part grown by its radius, so a leg that would graze a leg or the bar is
  gone round. A zero-U part (a PDU in the gutter) is met by the tube too, so
  a leg to the lane beside it never runs across its outlet face. Every pass through a ring whose opening is placed starts and
  ends at an approach point on the run outside the band, the cable's radius
  and `CLEAR` past it (`at: 'approach'`), so a detour or a leg from behind or
  below ends there and the cable enters along the run; a ring a route would
  double back at is gone to as far as that point (the path's `face` point,
  where the ring's own `face` stays on the band). `bodyFindings` names the
  part ("ring 3 front leg") and says to "route it into the ring along its
  run, through its opening". **ONE-WAY: routed lengths change on saved
  racks.** On the reference rack of #949 the upper leaf's cords grow 10 to 38
  mm (five now go over their ring to the approach point on its far side) and
  the lower leaf's 2 to 6 mm; c2 and c3 pass the 0.5 m stock break. On
  generated racks lengths move by up to about a tenth of a metre either way,
  depending on the layout: one sample of 3,120 cables (one layout and seed)
  gave -89 to +131 mm, median +10, 67 stock sizes up and 67 down; an
  independent sample of 3,962 cables gave -94 to +94 mm, median +4.5, 67 up
  and 27 down. A saved rack's routed lengths
  and stock sizes are re-measured the next time a page measures them; an
  entered length is never touched.
- **Automatic routes and routed lengths change** (`@portrayal/kit` 0.12.0,
  #949; `docs/cable-lay-design.md` section 4.1, pulled forward from step 5).
  A cable whose two ends leave through the same manager on the same face runs
  along it, port to port, through the rings whose centres lie between its two
  ports, and no longer goes out to the side lane and back; with no ring
  between, through the ring nearest the middle of its two ports (of two as
  near, end a's side; the nearest one it passes through, when one does), so
  never direct. Any other automatic route takes the gutter both ports stand
  on, or, when they stand on opposite sides of the centre line, the side
  whose path is the shorter (end a's side on a tie, or when a port is not
  found); before, the side was end a's alone. On
  the reference rack of #949 every one of its sixteen cords changes, from 0.67
  to 1.04 m by the lane to 0.43 to 0.50 m along the lacer (stock 1 or 1.5 m
  to 0.5 m); on a sample of 780 cables between six devices, a fifth to a
  quarter change, every one shorter. A saved rack's routed lengths and stock
  sizes are re-measured the next time a page measures them; an entered
  length and a route edited by hand are never touched.
- **Fewer doubles-back ring findings** (#949, #930's rule): a cable whose
  route reaches only a short way past its port into a ring just beyond it is
  held by the ring and not reported. Short means the nearer neighbour along
  the run is a port, and the ring's near face is no further past it than the
  ring's depth plus the cable's diameter (the diameter counted at most up to
  the depth); a turn-back just past another ring or a lane point, or further
  off, is a hook-back and is still reported. Such a cable now passes the ring
  (`held: true` on `routePath`'s ring, `back: false` on its mark), is drawn
  through it, counts in its fill and its manager's capacity, and measures its
  reach through the ring longer (about 8 to 14 mm on the FHD-CMP5DR). The
  rule is in `throughRings`, so hand routes and automatic ones agree. Saved
  hand routes that were findings can lose them; the saved routes on
  the reference rack of #949 had none before or after.
- **An automatic route can carry a doubles-back finding.** A patch along one
  manager with no ring between its ports goes through the nearest ring even
  when it cannot pass it or be held by it: a cross-connect on one panel from
  bay 3 lc2 to lc5 behind an FHD-CMP5DR takes ring 3, 31.5 mm past lc2, and
  `ringFindings` reports it. Before, automatic routes never doubled back.
- The descriptions in the six JSON schemas say what each field is, what it
  takes and what it does, without citing repository paths, document sections,
  steps or issue numbers, and without the history of how a rule came about
  (#951). 132 of 553 descriptions changed; what validates did not. The reasons
  that history carried are in `spec/DESIGN.md`, under "Why some schema fields
  are shaped as they are". American spellings in the rack schema (millimeters,
  catalog) and in a few colour descriptions are now British.
- A test records each schema's shape with its descriptions removed
  (`spec/tests/fixtures/schema-shape.json`), so a change to what validates is
  re-recorded on purpose, with
  `python3 spec/tests/test_schema_descriptions.py --update`. Another rejects a
  description that cites a `.md` file, `spec/`, `docs/`, a section, a step or
  an issue number.
- Lint L19 also reads a bay in a group whose role is `indicator`: it states
  `for:` as a lamp placement does (#414).
- `common/terminal-header-508-2@3` and `common/terminal-header-508-5f@2` are
  drawn 8.6 high, the Phoenix Contact installed height, not the data sheets'
  `h` of 12.1, which counts the 3.5 solder pin under the board (#873). Both now
  claim their registry entries (`terminal-508-2-header`,
  `terminal-508-5-header`, whose `h` is now 8.6), and each `mate` sits at 4.3,
  on the axis the 508 plugs already assumed. The ten AurCore AIS switches seat
  the new majors (2.0.0), each placement moved 1.75 so the header's centre
  stayed put. The three 508 plugs take patch bumps for their provenance.
- **A `side` key on a lab placement is no longer refused by the lab schema**:
  it is checked by L153 instead. L142 claims a rack-face part's unit per face
  and side; a lab with no `side` anywhere resolves and checks exactly as
  before.
- **Routed lengths change beside a duct**: a lane waypoint at a unit a zero-U
  duct spans is measured at the duct's centre line, about 49 mm further out at
  each end beside a 138.8 mm duct. Stored `routed` lengths are re-measured the
  next time a page measures them.
- `parseDoc` keeps `side` on an item, and gives a `zeroU` entry with no id, or
  a repeated one, an id of its own.
- A rack-face part is judged on every unit it spans, not only its bottom one,
  and within the rack's height. `place` of a zero-U part is refused, naming
  `zerou.place`; `remove` and `move` given a zero-U id name the command that
  takes it. A `frame` change moves the parts beside the rack to their side of
  the new frame, or down to fit, and removes one that no longer fits, saying
  so. `fitsZeroU` takes `ru` as well as `offsetMm`, and refuses a part that is
  not a zero-U part.
- `describe`'s totals line counts the parts beside the rack when there are
  any, and a window takes `section: 'zeroU'`; `inspect` of an item carries
  `side`.
- The tools are 0.2.0: `version` in `pyproject.toml`, and the `generator`
  version the compiler stamps into the metadata of every compiled face and
  into each elements file. Nothing else in a face moves with it. Every device
  package on npm takes an update at the next release run for that stamp.
  `docs/maintainers.md` lists the strings that move at a release.

### Removed
- `nokia/3fe54221ah` 1.0.0: the `front-open` view is gone, with its two placements
  `front-open/placements/security-screw-open` and `front-open/placements/latch-screw-open`.
  The inside of the housing is now on the `front` view, as `nokia/3fe54221-interior@1`
  behind the removable door `nokia/3fe54221-door@1`; the screws are
  `front/placements/security-screw` and `front/placements/latch-screw`. The device has
  no DCIM export.
- **BREAKING for DCIM data already imported.** Five HPE parts are renamed, and
  the old refs are gone. The DL160 Gen10's Media Module adapters take their
  option numbers, as its supplies do: `hpe/media-module-872161@1` is now
  `hpe/media-module-866464-b21@1`, `hpe/media-module-872162@1` is
  `hpe/media-module-866467-b21@1` and `hpe/media-module-872163@1` is
  `hpe/media-module-866470-b21@1`; their NetBox and Nautobot module types are
  renamed with them. Two lamps that are shapes and not HPE products move to
  `common/`: `hpe/led-sq@1` is `common/led-sq@1` and `hpe/button-led-sq@1` is
  `common/button-led-sq@1` (roc-ops/Portrayal#760).
- Six Dell R660 component majors are superseded and removed, each replaced by
  its `@2`: `dell/e3s-carrier-blank@1` (redrawn as Dell's real E3.S blank),
  and the Gen5 risers `dell/riser-2p-16g@1`, `dell/riser-2r-16g@1`,
  `dell/riser-3p-16g@1`, `dell/riser-3q-16g@1` and `dell/riser-3r-16g@1` (now
  on the Gen5-printed cages). A manifest that pins an `@1` moves to the `@2`
  of the same name (roc-ops/Portrayal#749).
- Two Supermicro component majors are superseded and removed, each replaced by
  its `@2`: `supermicro/riser-wio-rhs-x13sew@1` (slot 3's bracket bay moved) and
  `supermicro/system-board-x13sew@1` (the board is now flat art on the floor of
  an interior well). A manifest that pins an `@1` moves to the `@2` of the same
  name. The DIMM bays of the SYS-111E-WR, SYS-111E-FDWTR and SYS-111E-FWTR are
  renamed as the board names them, `dimm-1`..`dimm-8` to `dimm-a1`..`dimm-h1`,
  in the drawings and in their NetBox and Nautobot device types. None of this
  was in a release (roc-ops/Portrayal#782).
- `edgecore/ais800-psu-dc@1`, replaced by `edgecore/ais800-psu-dc@2` (#397).
  Element ids are unchanged; `vent-field` moved and grew.
- `common/terminal-header-508-2@1`, which nothing places any more. Use
  `common/terminal-header-508-2@2` (#804). Superseded: `@2` was removed in turn
  (#873, below), and the major to pin at 0.2.0 is `common/terminal-header-508-2@3`.
- `std/cxp@1`, the 27.0 x 10.0 x 92.0 estimate; use `std/cxp@2` (#802).
- `std/cfp@1`, the 82.0 x 13.6 faceplate-on-body envelope; use `std/cfp@2`
  (#802).
- `std/cfp2@1`, the 41.5 x 12.4 module body; use `std/cfp2@2` (#802).
- `std/cfp4@1`, the 21.5 x 9.5 module body; use `std/cfp4@2` (#802).
- `casa/ground-strap@1`, replaced by `casa/ground-strap@2` (#413). Its
  `bolt-hole` element has no successor: the jack is the composed `jack` part.
- **fs/dinrail2u-panel@1**, replaced by fs/dinrail2u-panel@2 (#971): the @1
  panel was the rail's 400 mm wide and stood clear of both brackets.
- **fs/dinrail4u-panel@1**, replaced by fs/dinrail4u-panel@2 (#971), for the
  same reason.
- `common/drive-carrier-25@1`, replaced by `common/drive-carrier-25@2`
  (#721). A manifest that pins `@1` moves to `@2`; a bay drawn at the `@1`
  size shows 2.6 mm of chassis between carriers.
- `common/drive-blank-25@1`, replaced by `common/drive-blank-25@2` (#721),
  for the same reason.
- `juniper/mx204-ground-plate@1`, replaced by `juniper/mx204-ground-plate@2`
  (two 10-32 screws on the guide's 0.75 in. centres, presenting a
  `stud-pair-3-4`; @1 drew the holes 16.0 apart) (#828, #830).
- `juniper/mx304-ground-plate@1`, replaced by `juniper/mx304-ground-plate@2`
  (two M6 screws on 5/8 in. centres, presenting a `stud-pair-5-8`) (#828,
  #830).
- `MIC-3D-4COC3-1COC12-CE` loses `port-1-0` to `port-1-3`: `juniper/mic-3d-4choc3-1oc12@1`
  drew eight cages in two PICs, while the card has four OC3/STM1 ports,
  numbered 0 to 3. The module reference states it and the MX104 photograph
  shows it. `@2` has `port-0-0` to `port-0-3`, and the module type is
  written from it. **BREAKING for DCIM data already imported.**
- `juniper/mic3-100g-dwdm` leaves the MPC3E's MIC bays: it is dual-wide, and
  no bay can take a module that fills two (`unplaced`, as
  `mic-3d-40ge-tx`).
- Nautobot module types `MIC-3D-4XGE-XFP`, `MIC3-3D-10XGE-SFPP`,
  `MIC3-3D-1X100GE-CFP`, `MIC3-3D-1X100GE-CXP`, `MIC3-3D-2X40GE-QSFPP` and
  `MIC3-100G-DWDM` name their interfaces `{module}/port-...`. They were
  `{module.parent}/{module}/port-...`. The exporter writes the one-token
  name for a model seated at several depths or at none. The first five are
  now seated at two depths: in an MPC on the MX240 to MX960, and in an MPC
  inside the adapter on the MX2000. `MIC3-100G-DWDM` is seated nowhere,
  because no bay can take a dual-wide MIC (above). NetBox is unchanged.
  **BREAKING for DCIM data already imported** (Nautobot). Superseded for the
  first five by the Nautobot entry under Fixed (#917), which gives them
  `{module.parent}/{module}/port-...` again. Of the six, only
  `MIC3-100G-DWDM` keeps the one-token name at 0.2.0.
- `juniper/mic-3d-4xge-xfp@1` and `juniper/mic-3d-4xge-xfp-v@1`, whose cages
  were laid out from registry sizes rather than measured (#238). Pin
  `juniper/mic-3d-4xge-xfp@2` and `juniper/mic-3d-4xge-xfp-v@2` instead.
  Superseded: both of those are now kept only as deprecated majors
  (`superseded-by`, #448), and the major to pin at 0.2.0 is
  `juniper/mic-3d-4xge-xfp@4` (#887).
- The MX960 vertical card twins, each replaced by the horizontal card at
  `rotate: 90`: `juniper/dpc-r-4xge-xfp-v@1` by `juniper/dpc-r-4xge-xfp@2`,
  `juniper/dpce-r-40ge-sfp-v@2` by `juniper/dpce-r-40ge-sfp@2`,
  `juniper/scb-mx960-v@1` by `juniper/scb-mx@2`, and
  `juniper/<base>-v960@1` by `juniper/<base>@2` for `dpce-20ge-2xge`,
  `dpce-2xge-xfp`, `dpce-40ge-tx`, `dpce-q-20ge-sfp`, `mpc-3d-16xge-sfpp`,
  `mpc10e-10c-mrate`, `mpc10e-15c-mrate`, `mpc1e-3d`, `mpc2e-3d`, `mpc3e-3d`,
  `mpc4e-3d-2cge-8xge`, `mpc4e-3d-32xge-sfpp`, `mpc5e-100g10g`,
  `mpc5e-40g10g`, `mpc7e-10g`, `mpc7e-mrate`, `ms-dpc` and `ms-mpc` (#261).
  Superseded for five of them: `juniper/dpc-r-4xge-xfp@2` and
  `juniper/scb-mx@2` were removed in turn for `@3` (#891, below), and
  `mpc1e-3d@2`, `mpc2e-3d@2` and `mpc3e-3d@2` are kept only as deprecated
  majors whose replacement is `@3` (#448). Those five `@3` are the majors
  to pin at 0.2.0.
- `juniper/re-s-1300-v@1`, which only `scb-mx960-v` seated, is replaced by
  `juniper/re-s-1300@1` in `juniper/scb-mx@2`. Superseded: both were removed
  in turn (#891, below), and at 0.2.0 it is `juniper/re-s-1300@2` in
  `juniper/scb-mx@3`.
- `juniper/mx960-blank-v@1` is replaced by `juniper/mx960-blank@1`, drawn
  horizontally with the MX960 blank's own knobs. Its DCIM module type is
  renamed from `mx960-blank-v` to `mx960-blank`, so the export files
  `mx960-blank-v.yaml` are replaced by `mx960-blank.yaml`. **BREAKING for DCIM
  data already imported.** Superseded: the module type was renamed again, and
  at 0.2.0 it is `DPC-SCB-BLANK`, in `DPC-SCB-BLANK.yaml` (#899, under Changed).
- The 22 horizontal card majors at @1, each replaced by its @2 above. The
  major to pin at 0.2.0 is `@3` for `dpc-r-4xge-xfp`, `scb-mx`, `mpc1e-3d`,
  `mpc2e-3d` and `mpc3e-3d`, and `@2` for the other seventeen.
- `juniper/dpc-r-4xge-xfp@2`, replaced by `juniper/dpc-r-4xge-xfp@3`;
  `juniper/scb-mx@2`, replaced by `juniper/scb-mx@3`; `juniper/re-s-1300@1` and
  `juniper/re-s-2000@1`, replaced by `juniper/re-s-1300@2` and
  `juniper/re-s-2000@2` (#891). Nothing in the library seats them any more, so
  per #448 the superseded majors are removed rather than kept; a manifest that
  pins one moves to its replacement.
- The six upper-cage majors the new sizes replace (#902), per #448:
  `juniper/mx2000-cb-re-v@1` (now `@2`), `juniper/mx2000-cb-re-128g-v@1` (now
  `@2`), `juniper/mx2000-cb-re-1800-v@1` (now `@2`), `juniper/mx2000-sfb-v@1`
  (now `@2`), `juniper/mx2008-sfb-v@1` (now `@2`) and `juniper/mx2008-rcb-v@1`
  (now `@2`). Nothing in the library seats them any more.
- `juniper/mx960-craft@1`, replaced by `juniper/mx960-craft@2` (#899). Nothing
  seats it any more, so per #448 it is removed rather than kept.
- `common/terminal-header-508-2@2`, replaced by `common/terminal-header-508-2@3`,
  and `common/terminal-header-508-5f@1`, replaced by
  `common/terminal-header-508-5f@2` (#873). Element ids are unchanged.

### Fixed
- 3D kit: a `uhandle` standing `in:` a well rises from the well's floor, as
  `out`, `cyl` and `bar` already did, rather than from the face plane.
- `amphenol-ns/tpa-fuse-holder-307492@1` (1.0.1) keeps its fuse rating out of
  the drawing once the rating is set in a viewer. The rating is carried by the
  part and never printed, because the fuse is inside the holder; its text node
  was hidden by its own `display`, which `kit/fields.js` removes from a node it
  writes a value to. The node now sits in a group that is not displayed. The
  300CB08 takes a patch, 1.0.1.
- 3D kit (`swap.js` `viewsToRewrite`): a swap into a slot on a placed part
  that composes several slots and is no cage itself, such as a pole of a
  barrier terminal block (`psu1-input/lug-2`), now reaches the 3D scene. No
  bay and no cage of any view claims such a key, so no view was named, the
  face was never rewritten and the occupant showed in 2D only, with no
  warning. Every view is rewritten for such a key (#814).
- `@portrayal/kit`: the README's links to the Portrayal README and to the
  artifact contract are absolute GitHub URLs, so they work on the npm package
  page, where a relative link resolved against npmjs.com and broke. The
  package also names its `homepage` and where to report `bugs`. Neither is
  in kit 0.2.0 on npm, which was published before this change; both reach
  npm with the next kit publish (#716).
- `edgecore/ais800-psu-dc@2`: the vent lattice is 23.46 tall from y 13.56,
  measured module edge to module edge on the quick start's Connect Power
  figure, where 1.x drew it 20.12 from 15.01 (#397). `edgecore/ais800-32d`
  2.0.0 and `edgecore/ais800-32o` 3.0.0 accept it.
- The -C panels of the Amphenol Network Solutions 300CB08 family
  (`amphenol-ns/300cb08-c`, `nrg300cb08-ctrl-c`, `nrg300cb08-sens-c`) are
  367.0 deep, front of the metal to the tops of the output receptacles, as
  their own bottom view (installation guide Fig. 3-13) measures, not the stud
  panel's 330.8; their bottom is re-read off that view. Their busbar landings
  (`amphenol-ns/input-feed-busbar@1`, 1.0.1) now stand 38.1 and 95.2 behind
  that, the two lengths the drawing dimensions, where both stood 147, a figure
  that subtracted a depth without the front guards from one with them (#860).
  Each of the three panels takes a major (2.0.0): its geometry moved, though
  no id or slot did. Their DCIM exports change in the drawing version line
  only.
- The kit's `loadDevice` and `loadStage` (`kit/shell.js`) take a generation each
  call, and one that a newer load overtook stops after its await: it writes no
  device, configuration or view, mounts no drawing and emits no `load`, and its
  promise rejects with an error `isSuperseded(err)` (exported) recognises. The
  stage holds exactly one drawing after any overlap. A host that awaited a load
  sees the rejection instead of carrying on with a stale target (#929).
- A `fields=` entry for a part drawn only on a face other than the one the link
  opens (a supply's wattage on the rear, a link opening on the front) is kept on
  reload: the shell fetches the other faces before judging the entry, as
  `applySwaps` already does for a slot on another face, and paints it when that
  face is mounted. It used to be ignored and dropped from the location (#818).
- L132 resolves `fed-by` per configuration, as the export does: an output
  every configuration has, fed by an input that only some configurations have
  (`only-in`), is an error naming the configuration that lacks it, where it
  used to lint clean and stop `./publish.sh` with `NotExpressible` (#857).
- A breaker bay whose description is too long for its `; protects <outlet>`
  clause now leads with `Protects <outlet>; ` and shortens what it accepts
  after it. The clause is the only place Nautobot keeps the breaker-to-outlet
  link, and it used to be cut off. No bay in the library is that long, so no
  committed export changes (#857).
- L129 refuses an `optical.trunk` that names one position of a multi-position
  front connector exported as one port (an MPO adapter): the export shrank the
  port and kept each leg's original `front_position`, which both DCIMs refuse.
  Name the connector bare (#857).
- L39 asks each window a multi-window lamp declares to be more than half
  punched, where it summed them: a four-window lamp with three windows punched
  passed, and the missing window was never reported. Nothing in the library
  changes. Tests now pin the windows' turn at 90, 180 and 270 degrees on a part
  that is not symmetric (#845).
- L39 reads a composed leaf with no registry entry (no `conforms`, no parts of
  its own, a size, and not a lamp, latch or printing) as the opening of the
  part that composes it, as `_aperture_of` already did, so the C100G's strap
  plate is checked against its jack's cutout rather than reported 4.5 mm off
  it (#413).
- Every Casa lamp now declares the states it can show and is drawn off (#940).
  The STATUS, ACTIVE and ALARM lamps on the line cards (BDM, BDM2, BDM2m,
  DS 8x8/8x96/8x192, US 16x4/16x8, CSC 8x10G) and the SMMs (2x10G, 8x10G,
  300G, 300GM) take `ok`, `active` and `alarm`, from the front-installed module
  LED tables of the C100G and C40G installation guides; STATUS and ACTIVE are
  no longer painted permanently green. The port lamps on the CSC 8x10G and
  SMM300G/GM take `link` and `activity` (blinking), and the SMMs' management
  jacks colour their lamps green. The C100G fan and PEM lamps take `ok`,
  `alarm` and a blue `high-speed` (fan) or `on` (PEM, which the guide marks
  "Not used"). The C40G AC PSU's status lamp is now a declared element,
  `casa/c40g-psu-ac@1` `status`, with `ok` and `alarm`; it was art painted
  green that no state reached. No element id changed. Each of the sixteen
  components takes a minor, and the C100G and C40G a patch.
- `fs/dinrail2u` and `fs/dinrail4u` 0.1.1: the setback notes say the datasheet
  side views are embedded rasters (461 x 212 and 435 x 279 px, about 1.1 and
  1.2 mm a pixel) read on an upsampled render, not vectors; the 2U note says the
  slot's front end is hidden under the screw head drawn at 69.4, which is where
  the front stop is taken (64.4 + 2.6 would be 67.0). The 51.2 mm front setback
  stands. The configuration-level `airflow` description in the device schema
  and the `configs.json` airflow list in `library/README.md` name
  `top-to-bottom`.
- `eaton/pdumv20hvnetlx` 0.1.1: the front `logo-zone` moves to (19.0, 677.0),
  over the wordmark DT01 shows, and the left view gains a `logo-zone` for the
  upside-down EATON wordmark DT08 and DT01 show about 864 to 930 mm from the top end
  (the mark is not drawn). The side vent fields no longer carry a fill their
  `slots` pattern replaces; the drawing is unchanged.
- The device schema's `interfaces` description and power-outlets-design
  decision 5 say that a NOS listing that states its own `interfaces` keeps
  every outlet's placement id, since it does not apply the hardware's own
  naming rules.
- `generic/nema-5-20p-plug@1` 1.0.1: `provenance.pins` gives the blade
  centres 15.45 apart, as the Leviton drawing places them (6.31 + 9.14), not
  15.49. The drawing is unchanged.
- `components.json` publishes a turned bay with its `rotate` (#718). Each
  component entry lists its own bays with `at`, `size`, `accepts` and
  `default`, and left out the turn, so a consumer placing a card by the index
  landed it wrong in a turned slot. The two slots of `dell/riser-3a-14g@2`
  carry `rotate: 180`. A bay that is not turned states nothing, as before.
  Additive; the `contract` number does not move.
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
- `edgecore/eps122` 2.0.8 draws the orange bands that mark its 90 W ports 41-48: one
  behind the legend row above them and one behind the lamp row below, measured on the
  guide's front elevation at its native resolution and coloured from a pixel count. The
  single band it carried sat at x 601.74 on a 440 mm face, so it was never seen. The
  panel legend is transcribed as "1.65A Max/Port41-48", not 1.85 A, and the row under
  the ports is identified as the per-port lamp row (#878).
- `juniper/mx204` 4.0.2 no longer carries four ear-flange rects beside its front and
  rear faces. They lay wholly outside the drawing and were never seen, and the device's
  own provenance says the ears are not modelled (#878).
- `edgecore/exp800-16o` and `edgecore/exp100-32x` (2.0.0) print the white
  arrow beside each port numeral as silkscreen (`silk-arrow-N`), as the AIS800
  review ruled for the same glyph, and keep the dark triangular windows under
  it as lamps: the EXP800 quick start calls them out as the OSFP LEDs (#396).
  Both port strips were re-measured on their elevations: the numerals, which
  sat where the arrows are or past the windows, and the lamps, which sat
  between the two pairs of windows, now stand where the drawings put them; each
  lamp is its port's left window.
- The covers of the FS HD and UHD finger ducts show their four latches in 3D
  (#869): the plate and its clips are one raised group, so the clips are
  drawn on the face instead of left behind it, and the hinge rails end 0.1 mm
  behind the face. `fs/cmh-uhd-sfdabs1u-cover`, `-2u-cover`, `-3u-cover`,
  `fs/cmh-hd-sfdabs3u-cover` and `-4u-cover` 1.0.1; the five devices 0.1.1.
  The 2D drawings are unchanged.
- `fs/cmh-sfds1u` cites the FS quick start guide it takes its fixings from as a
  reference, and its capacity note and those of `fs/cmh-sfds2u`,
  `fs/cmh-dfds1u` and `fs/cmh-dfds2u` no longer label a missing figure
  `datasheet` (#869).
- Four FS finger-duct covers reserve a `logo-zone` where FS prints its mark
  (#869), so a renderer has the box without the library drawing a vendor
  logo. Measured on FS's straight-on renders for `fs/cmh-sfds1u-cover` and
  `fs/cmh-dfds2u-cover`, estimated from an angled close-up for
  `fs/cmh-sfd1u-cover`, and borrowed from the SFDS1U for
  `fs/cmh-bs-sfds1u-cover`, of which no image exists; all four 1.1.0.
  `fs/cmh-sfds2u-cover` and `fs/cmh-dfds1u-cover` claimed a mark that no
  render or drawing shows; their provenance now says so, 1.0.1. The devices
  cmh-sfds1u, cmh-sfds2u and cmh-bs-sfds1u 0.1.1, cmh-dfds1u, cmh-dfds2u and
  cmh-dfd1u 0.1.2, cmh-sfd1u 0.1.3. The 2D drawings are unchanged.
- `fs/cmh-sfd1u` 0.1.2: the back of the base is built inside the 87 mm
  envelope. 0.1.1 built its five rear plates 11.3 mm outward from the rear
  face, so in 3D the duct was 98.3 mm deep with an air gap behind the well
  floor; the plates and the base's side walls are now sunk just inside the
  faces. The 2D views and the DCIM exports are unchanged apart from the
  version.
- `devicelock` no longer calls a change minor because it added an id while
  something already there moved: the added placements are taken back out and
  the rest must still hash to the old shape, or the change is a major (#828).
- The faces of the HPE FlexibleLOM adapters are read from their own
  photographs (#764). `hpe/flom-817721-b21@1`, the 535FLR-T, was a copy of
  the 562FLR-T face: its P2 legend is between the jacks and it has no right
  vent field. The 640FLR-SFP28 has its features 1.0 mm further right, with
  ACT lamps that show activity only and LNK lamps that show link only.
- The IEC inlets' cavities are as deep as the cord ends that enter them.
  `std/c14-inlet@1` (1.4.0) is 17.0 deep, shroud face to cavity floor, with
  its pins rising 15.0, both dimensioned on Adam Tech drawing S00087C rev D,
  where it was 13.0 and 12.2 estimated. `std/c20-inlet@1` (1.4.0) is 19.0 deep
  with 17.0 pins, still estimated (the C19 nose less 1, as the C13/C14 pair
  stands; no held drawing sections a C20 cavity), where it was 15.0. The cord
  ends seated in them, `generic/c13-plug@1` and `generic/c19-plug@1` (1.1.0),
  stand 4.0 less proud: 47.0 and 57.0 in front of the inlet face. The 126
  devices whose supplies or chassis carry one of these inlets take a patch
  (97 C14, 30 C20, `dell/r740xd` both); their DCIM exports change in the
  drawing version line only (#793).
- `common/rj11-jack@1` (1.2.0) is drawn as the six-position jack it is: the
  opening is 9.88 wide (TE C-1775675 rev C) in three tiers (body, latch
  shoulder, latch slot) recessed into a solid housing, as `std/rj45@2` draws
  its own, where it was the 11.6 RJ45 width; two contacts are loaded (6P2C);
  and it is 20.57 deep with a built cavity, where it stated no depth. Its
  body is unchanged; its `mate` and `tel` points move from (7.0, 6.75) and
  (7.0, 6.7) to (7.0, 4.925), the centre of the 9.88 x 6.85 body tier, so a
  seated `generic/rj11-plug@1` (1.0.1, provenance only) sits centred in the
  tier and clears the opening by about 0.12 a side, where at the old point it
  stood 1.8 off it. Nothing on a device addresses either point, so
  `halny/hlx-tgv` takes a patch (#837).
- `dcim_export` refuses a listing name pattern that does not parse, by name,
  where it raised a bare `SyntaxError` (#719).
- The 3D viewer survives a lost WebGL context (#746). The view went blank
  with no message and never came back. The viewer now lets the browser
  restore the context, then rebuilds the loaded device or component with its
  configuration, overrides, states, pulled parts, selection and marks, and
  leaves the camera where it was. While the context is lost the explorer says
  that 3D is paused, and when the browser refuses a new context it says to
  reload the page or close other tabs with 3D open.
- Lint L109 judges a declared `optical.polarity` against the pattern for the
  trunk connector's own fibre count, read from its `optical.positions` as L80
  reads it, and compares only the ports actually wired (roc-ops/Portrayal#524).
  It used to count the paths, so an MTP-24 Type AF cassette with fibres
  declared `unused`, or wired to twelve ports, was judged as a narrower
  connector: its correct row-exchanged paths failed and the plain pair swap
  passed. A module whose trunk is stated in `optical.trunk` (#246) is now
  judged too; it used to be skipped without a word.
- L39 centres a part's composed opening on its cutout, not the part's whole
  footprint (#248). `common/qsfp28-cage@3` carries the chassis lamp band above
  the cage, so its `std/qsfp-ganged@1` opening sits 4.2 mm below its top edge;
  the TE 2322551-4 drawing has the cage itself centred on that opening. Every
  correctly punched AS7726-32X port, and its USB beside a printed symbol, read
  as 1.5 to 1.74 mm off. The 33 baselined warnings are gone and no component
  or device changed.
- L46 measures what composed parts draw, not their boxes (#684). A pair whose
  boxes collide is measured again on each part's skin shapes (rects, circles,
  ellipses, polygons, text; a skin with a path or a transformed group counts as
  its whole box), so the open middle of `common/qsfp-pull-tab@2` and
  `common/qsfp-dd-pull-tab-type2@1` no longer reads as covering the bores and
  inserts it frames. Seven baselined warnings are gone, and the provenance
  sentences that explained them are removed from `generic/qsfp-lc@2` 2.2.2,
  `generic/qsfp-dd-lc@2` 2.2.1, `generic/qsfp-lc-simplex@1` 1.0.1,
  `generic/qsfp-mpo@1` 1.0.1 and `generic/qsfp-dd-mpo16@1` 1.0.1.
- Vendor marks are reserved, not drawn or boxed, on fifteen devices and one
  component (#964). No DCIM export changes and nothing is renamed.
  - Edgecore: `edgecore/dcs240` 1.1.9 drops the grey `brand-badge` box that
    stood for the logotype and reserves its measured box as the region
    `logo-zone`; `edgecore/dcs511` 2.0.9, `edgecore/eps121` 2.0.8 and
    `edgecore/eps122` 2.0.9 gain the region where the logotype sits.
  - FS blanking panels: `fs/fhu-bps-1u-10`, `fhu-bps-2u`, `fhu-bps-4u`,
    `fhu-bpstl-1u-10`, `fhu-bpstl-2u`, `fhu-bpstl-4u` and `fhu-bpa-1u-10`
    (each 0.1.1) gain a `logo-zone` region at the mark measured on the
    straight-on render; `fs/fhu-bpad-2u` and `fs/fhu-bpad-4u` 0.1.1 gain one
    region per unit, `logo-zone-1` upward, inside the recess each unit
    already draws.
  - Casa: `casa/chassis-label@1` 1.4.0 no longer draws a black triangle where
    the vendor mark sits; the skin node `logo` is gone and the measured box is
    the element `logo-zone`, left empty. `casa/c100g` 1.0.2 and `casa/c40g`
    0.5.20 take the patch for the part they place.
- A card's USB jack is a console port only when its placement says so, as on a
  device. The module export filed every `std/usb-a` part as a `usb-a` console
  from the ref alone, and had no micro-USB or USB-C console row; it now asks
  the device path's own decision (`device_console_row`): a USB-A or USB-C jack
  needs `role: console`, and a micro-USB jack is a console when its id, role or
  function says so. The USB storage and service ports on 14 Cisco ASR 9000
  RSP/RP cards, 10 Juniper RE/RCB cards and the two Dell 16G rear I/O boards no
  longer export as consoles; eight CommScope CH3000 modules gain their
  micro-USB console (`usb-micro-b`), and the Eaton G4 ENMC its USB-C console.
  **BREAKING for DCIM data already imported.**
- The CommScope CX3003C and CX3033N (1.0.1; CH3000 3.2.4) no longer call their
  micro-USB a console: both datasheets reserve it, with the RS-232 jack beside
  it, for factory use, so it exports nothing.
- The MX chassis state the power their vendor publishes (roc-ops/Portrayal#113).
  `power-typical-w` on the MX80 (310 W, output side, Tables 14 and 20),
  MX240 (1860 W), MX480 (3470 W) and MX960 (6520 W) - the last three from
  the family datasheet with the DC figure in `power-typical-scope` and
  `power-envelope: unstated` - and on the MX10004 (7.5 kW), MX10008 (12 kW)
  and MX10016 (23 kW), typical and fully loaded per their datasheets.
  `power-max-ac-w` 600 and `power-max-dc-w` 625 on the MX104 (input side,
  Table 6); 1520 W typical and 4420 W at 55 C on the MX2008 for the base
  system only (`power-envelope: bare`); the MX10003's `typical-draw-w` is
  now `power-typical-w` 1676 beside `power-max-w` 2110 (Tables 24 and 25).
  Provisioning ceilings go under `thermal.max-thermal-output`, flagged as
  ceilings (MX80, MX480, MX960). The MX2010 and MX2020 carry no figure: their
  guides contradict themselves, recorded as a `sources-disagree` gap scoped
  to both power facts. Five records that called the vendor silent or the
  tables unextracted are corrected (MX80, MX104, MX960, MX10004, MX10008).
  Each device is a patch version; the DCIM device-type exports change only in
  their comments.
- Nautobot: the MX2000 line-card adapter (`MX2000-LC-ADAPTER`) exports its
  `mpc` bay, so an MPC can be installed in it in an MX2008, MX2010 or MX2020
  slot (#917). The bay has a blank position: Nautobot skips a blank position
  when it names ports, so an MPC in the adapter in `fpc3` names its ports
  `fpc3/port-0-0`, the names the same MPC takes in an MX960's `fpc3`. NetBox
  is unchanged and still says `fpc3/mpc/port-0-0`. A carrier's only bay that
  accepts a module also seated directly in a chassis bay is given this way;
  the adapter is the only one at 0.2.0.
- Nautobot: the MICs that only an MPC takes (`MIC-3D-4XGE-XFP` and the four
  `MIC3-3D-*`) name their ports `{module.parent}/{module}/x` again, as before
  #261 made the adapter count as a second depth for every MPC. **BREAKING for
  DCIM data already imported** from an export taken since #261 merged: those
  five module types need re-importing. Their bays on the MPC1E, MPC2E and
  MPC3E are still withheld from Nautobot (nautobot/nautobot#5823), as in an
  MX240, MX480 or MX960.
  This is where the three Nautobot entries of this section end up (#765,
  #261 and this one). Against an export taken at 0.1.0, those five types
  move from `{module}/x` to `{module.parent}/{module}/x`, once. On
  `MIC-3D-4XGE-XFP` the third and fourth ports are also renamed, in NetBox
  as in Nautobot: `port-0-2` and `port-0-3` are `port-1-0` and `port-1-1`
  (#887, under Changed).
- `juniper/mx480` 5.0.1: the weight comes from the hardware guide's Table 88,
  29.7 kg for the chassis with midplane, fan tray, air filter and cable
  management brackets and 100.26 kg for the maximum configuration
  (`weight-base-kg`, `weight-max-kg`). The "up to 163.5 kg" it carried was the
  guide's rack text, 163.5 lb (74.2 kg), read as kilograms; the false
  `weight-and-max-config` gap is gone (#886).
- The 300CB08-C, 300CB08-SC and the four nrg300CB08 connectorized panels
  (1.1.2) no longer list an `output-plug` gap: their P40 receptacles are
  connector slots and `amphenol-ns/p40-plug@1` seats in them. Their DCIM
  exports change in the drawing version line and the gaps comment only.
- The 3D front of `nokia/lmfs-f`'s front-cover configuration was laid out on
  the 528 mm drawing rather than its 481 mm face, so every part sat 23.5 mm
  left of where it is and the face was textured over a plate 528 wide (#865).
- **The snap-in ring's relief agrees with its guide**: each leg was built
  6.8 mm thick in the plane of the loop, which narrowed the drawn opening to
  30.0 mm against the guide's 32.0 and stood a route's sill point 1 mm inside
  the rear leg. The legs are 5.8, as the plan's 43.6 less the opening gives
  and the ring-profile view reads to a pixel. The slit, re-read, is 2.2 mm
  where 3.8 had been read, in the relief and in fs/fhd-cmp5dr-profile@1
  1.0.1's side view.
- L50 no longer reports printing as painted over by a node that is never on
  screen with it: a position's other option, drawn after it (#808).
- The craft interface bays of `juniper/mx960` (1.1.0), `mx2008`, `mx2010`
  and `mx2020` (0.3.0) state `for: chassis`, and their `craft` group's role
  is `management`, as it already was on the MX240 and MX480: the craft
  interface is where an operator reads and acts on the router's state, with
  LEDs for its components, buttons and an alarm cut-off. `dell/r660` (5.1.0) does the same for its left
  control panel, which the R660 Installation and Service Manual describes as
  holding the system health, system ID and status lamps (#414).
- In 3D, a part whose only SHOW node is hidden by default now rebuilds when
  that node should appear: each part group records its position fields as
  `data-position-fields` before hidden nodes are removed, and the viewer's
  rebuild check reads it (#874).
- A `data-move` entry whose number is not one (`.`, `1.2.3`) is refused by the
  kit as the build refuses it, instead of writing `NaN` (#874).
- The 3D viewer draws a part's fields on its first scene. `setFields` called
  before the first `load` - a host handing over a link's latch colour as it
  creates the viewer - was kept and never painted: the latch came up grey,
  and the same map again changed nothing. `build()` now loads the fields
  beside the lamp states and pulled parts, before any face is cut (#850).

## 0.1.0 - the first public release

What 0.1.0 promises, as [docs/format-stability.md](docs/format-stability.md)
states it in full:

- Manifests are **`format: 1`**, which schema **v1** names. The schemas were
  labelled `v0` until this release, which was the same format under a second
  name. Each schema's `$id` is `https://portrayal.dev/schemas/v1/<name>.schema.json`
  (`device`, `component`, `listing`), and the schemas are published there.
- The published build is **`contract: 2`**. The history below says what `1`
  and `2` each changed.
- At 0.x the tools read the current format only. Every change that raises
  `format` or `contract`, or re-files DCIM data already imported, is listed
  here, with what to change to move across, and it raises the package's minor
  version.
- At 0.x a superseded component major may be removed. Every removal is listed
  here with the ref that replaces it. From 1.0 a retired major is deprecated
  for at least one release before it is removed.
- Lint codes are never renumbered or reused, because a manifest waives a rule
  by its code. A deleted rule's code is retired, not reissued.
- From 1.0, a change that raises `format` or `contract` is a major version, and
  the previous format stays readable for one release.

### Pre-release history

Everything below changed before the first release, while every consumer was
inside this repository. It is kept because the build already carried `contract`
numbers through it, and because it is the record of what each major and each
breaking export change replaced.

One of these changes is one the promise above now rules out: during
pre-release the power rules were renumbered from L117-L119 to L118-L120
(commit 5f6417b7, roc-ops/Portrayal#513), because another branch had taken
L117 first. The move was made on the power rules' own branch, before they
merged, so no code on `main` ever named a power rule at L117-L119, but anything
written against that branch's numbers names a different rule. From 0.1.0 a
code is never moved; the lint catalogue test pins every code issued.

#### Added
- **ArcOS listings for the Arrcus HCL** (roc-ops/Portrayal#674). Every box on
  the Arrcus Hardware Compatibility List (June 2026, ArcOS 8.5) that the library
  models - 29 of the 30 from UfiSpace and Edgecore - is listed under
  `arrcus/`, with the HCL row as its source and Arrcus's own grouping
  (Switching (XGS), Routing (DNX), VDR line and fabric cards) as its portfolio.
  The AS7726-32X and AS7326-56X carry ArcOS port names from live units; the
  other 27 carry an `arcos-port-names` gap instead, because ArcOS's own
  documentation disagrees on whether a platform's first port is `swp0` or
  `swp1`. Listings may now carry `gaps`.
- **Listings** (roc-ops/Portrayal#674). A NOS vendor lists the hardware it
  supports: `library/devices/<nos vendor>/<id>/listing.yaml` points at one device
  and carries only what the NOS vendor changes - interface names, its own model
  name and catalogue family, and its own part numbers where it has them. This is
  how NetBox and Nautobot file a disaggregated box: one device type per
  manufacturer that sells it, with one copy of the metal behind them all.
  - `listings.json`: every listing, whole, keyed `<ns>/<id>`, with `ns` and the
    resolved `manufacturer` added.
  - `devices.json`: each device carries `listings`, the keys of the listings
    that list it, and its `search` blob gains each listing's vendor, NOS and
    names, so "arrcus" or "ocnos" finds the hardware.
  - `devices.lock.json`: a `listings` map beside `devices`. A listing is
    versioned (`listing.lock.json` beside it): a changed port name, model or
    part number is major, an added configuration override minor, wording a
    patch.
  - `vendors.json`: IP Infusion (OcNOS), DriveNets (DNOS) and SONiC join Arrcus
    as software vendors.
  - Lint L124: under one NOS vendor, no two listings export the same DCIM model,
    and an alias names one listing unless each claimant marks it `shared`.
- Lint L123, library-wide: one module, one bay size. Every bay that accepts a
  module, in any device or carrier, reserves the same size for it to within a
  millimetre, compared in the module's own frame so a turned bay matches an
  upright one. A warning; four remain - the A99-RP-F between the ASR 9902 and
  9903, and three outside Cisco.
- `presents` on a `components.json` entry for a part that mates into something:
  what it offers the next tier when it is itself seated - `interface`, `mate`
  and `lift` in its own frame (the point a boot or a plug stands on, and that
  point's `out`), `accepts`, `kind`, `rotate`, `bores` and `default`, in a slot
  entry's shape. A generic LC or RJ45 plug presents its boot point, and a
  single-bore optic its one bore. A consumer seating through slots can now
  seat the chained tier the build seats under `<key>-occupant`: carry `mate`
  through the seat's placement, take its turn, and add its lift to the lift of
  the slot it sits in. Omitted for a part that presents nothing, and for one
  whose presented interface nothing in the library mates (roc-ops/Portrayal#611).
- `data-rear-rotate` on a rear cutout a turned bay is seen through: how far
  a back drawn in it is turned, the bay's own `rotate` negated (a clockwise
  turn seen from the front reads anticlockwise from behind). The back's
  projection in that hole carries the same turn about its own centre, and
  `data-rear-at` is then its unturned top-left, as a placement's `at` is.
  Unturned holes are unchanged.
- Component groups: a component declares `groups:` in the device shape and a
  part joins one with `group:`. A port on a module seated in a bay, at any
  depth, now carries `data-group`, `data-group-role` and its group's attrs
  and description, with the part's own attrs winning. A cage on such a card
  publishes the group's side as `occupant-attrs`, and the build writes the
  same attrs on an optic seated there. `components.json` carries each part's
  `group` and the component's `groups`, and module-type exports type a card
  port from its group's attrs and mark a `management` group's ports
  `mgmt_only`. A component group's role takes the device group's six values,
  `fabric` included, and L110 reads a component group's `speed` as it reads a
  device group's (roc-ops/Portrayal#511).
- `data-inner="1"` on the inner part of a composed port, the `std/*` core that
  `common/rj45-eth@1`, `common/qsfp28-cage@3`, `common/sfp-plus-cage@2` and
  `common/rj45-ganged-eth@1` draw as a nested `data-class="port"` element.
  The core keeps its class. An audit that counts ports should skip it with
  `[data-class=port]:not([data-inner])` (roc-ops/Portrayal#511). The same mark
  covers a port component that draws a second `class: port` element inside
  its own skin, not only one composed as a separate part.
- Every `configs[]` entry in `<device>.configs.json` carries `airflow` —
  `front-to-back`, `back-to-front`, `side` or `passive`, or `null` where the
  device states none — resolved the way each drawing's `data-airflow` is (the
  configuration's value, else the chassis's). The `chassis` block carries the
  chassis's own `airflow`. A page filtering builds by airflow no longer parses
  it out of a configuration's name or description (roc-ops/Portrayal#513).
- A device states its supply feed as `power` - `ac`, `dc` or `hvdc` - on the
  chassis where the box has one feed, and on a configuration where its build
  differs, the way `airflow` is stated (lint L118). Every `configs[]` entry in
  `<device>.configs.json` carries the resolved answer as `power`, always a list
  (`["ac"]`; `["ac", "dc"]` for a build fed both ways; `[]` where nothing is
  stated), and each drawing's SVG root carries it as `data-power`,
  space-separated. The `chassis` block carries the chassis's own `power`.
- `options` in `<device>.configs.json` and on every entry of `devices.json`:
  `{"power": [...], "airflow": [...]}`, the union over a device's orderable
  and base builds. "Does this come in DC?" and "is there a back-to-front
  build?" are one lookup; an `example` or `model` build does not widen it, and
  a build the vendor sells that nobody has modelled is not in it.
- `comparable-facts.json` reads `airflow` from `chassis.airflow` and the
  configurations before any attrs prose (it read only attrs, so a device
  stating airflow properly compared as silent), and gains `power-feed`.
- All 84 Edgecore, UfiSpace and Celestica devices state `power` on every
  build. There were 85 when this landed, and the one without was the N3100-4C, a
  PCIe card fed by its host slot; it has since become a module (below), so the
  census has no exception. Four more state `airflow` (AS7946-30XB and
  AS7946-74XKSB front-to-back, S9511-20CT front-to-back, S9502-12SM passive).
  Lint L119 asks any other device with supplies for a feed, as a warning
  baselined for the 32 that do not say yet; L120 reports a build whose `power`
  contradicts the supply it seats (roc-ops/Portrayal#513).
- Back-to-front builds (`ac-b2f`, `dc-b2f`) on the UfiSpace S9300-32D, S9301-32D,
  S9301-32DB, S9311-64D and S6301-56ST, which each sold both directions but modelled
  only front-to-back. They seat the intake supplies and fans with blue latches,
  handles and "I" airflow tags, coloured from the vendor's back-to-front renders.
  The parts gained what that needs: `latch-finish` / `latch-edge` on
  `ufispace/psu-132-ac`, `psu-132-dc`, `psu-151-ac`, `psu-151-dc`, `psu-242-ac` and
  `psu-242-dc`; `handle-finish` on `ufispace/fan-402825`; and an `intake` skin on
  `ufispace/fan-405637`, `fan-402825` and `fan-805616`. Each part took a minor
  bump. The S9110-32X's existing back-to-front builds now use the `intake` skin
  too; they wore the red "E" tag.
- DC builds on the Edgecore COR550 (`dc-f2b`, 7926-40XKFB-O-48V-F) and CSR440
  (`dc`, AS7535-28XB-O-48V-F V2) and the UfiSpace S9620-32E (`dc`,
  PSU-322-DEJR-NN), and an AC build on the S9502-12SM (`ac`). No held document
  shows those supply faces, so each is drawn with the other feed's part and
  says so in its gap. Lint L120 is baselined for the three DC stand-ins, as
  for the COR580.
- Every device in `library/dist/devices.lock.json` carries `placement-attrs`: a
  digest of the `attrs` each placed port states for itself (`speed`, `media`,
  `usb`). Retyping one now asks for a patch bump, where before it asked for
  nothing (found on roc-ops/Portrayal#519).
- Every device in `library/dist/devices.lock.json` carries `placement-geometry`,
  `placement-addressing` and `placement-surface`, fingerprinting the placement
  and bay keys that were hashed nowhere: `inset`, `lift`, `in`, `under`,
  `only-in`, `optional` and `interfaces` (a major); `for` and `rel-pos` (a
  major when changed or removed, a minor for a `for` stated where there was
  none, nothing for a new `rel-pos` - recorded as a map, not a digest, so the
  cases can be told apart); `states`, `description`, `provenance`,
  `physical-context` and `frames` (a patch). Editing any of them used to ask for
  no bump at all.
- The same three keys now cover the keys only a bay states: `opening`,
  `floor`, `plan` and `rear` in `placement-geometry` (a major), and
  `interface` in `placement-addressing` (a major when changed or removed, a
  minor when stated where there was none). The eight devices whose bays state
  one - six Cisco ASR 9000s, the R740xd and the FHD 1U enclosure - were
  re-locked, and only their `placement-geometry` moved. No device version
  changed (roc-ops/Portrayal#537).
- `devices.json` carries `contract: 1` — the first version a consumer can check
  (roc-ops/Portrayal#185).
- `library/dist/devices.lock.json`: every device's fingerprint in one file,
  assembled from the per-device locks (roc-ops/Portrayal#182).
- Module types export SONET rates (`sonet-oc3`, `-oc12`, `-oc48`, `-oc192`) for
  the 27 SONET, ATM and channelized cards that had been exporting as Gigabit
  Ethernet (roc-ops/Portrayal#296), and CFP/CFP2/CXP at 100G for fourteen Juniper cards that
  exported nothing (roc-ops/Portrayal#254).
- Device types carry `power-ports` where the chassis holds the inlet, and RF and
  timing jacks as `other` interfaces with their connector or function as a label
  (roc-ops/Portrayal#286, roc-ops/Portrayal#285).
- `<device>.configs.json` and every `devices.json` entry carry `aliases`: the
  other names the box is sold or listed under - an AS number, a marketing name,
  a DriveNets name - as a list of strings, `[]` when there are none. `model`
  stays the canonical name and is never repeated there. The names are also in
  the `devices.json` search field, so a hardware compatibility list's AS9716-32D
  finds `dcs510` (roc-ops/Portrayal#514).
- `components.json` carries each part's `optical.ends`: for every fibre
  endpoint, `{to: string | string[], label: string | null}`, keyed `part.n` on
  the front and `rear:part.n` on the rear; a fan-out endpoint (a splitter's
  common port) has a list `to`, one entry per branch. A rear cutout a bay is
  seen through now also carries `data-rear-ref` (the seated occupant),
  `data-group` and `data-group-role` (the bay's own group), and `data-rel-pos`
  (its position within it) - so `[data-group='slots']`, or any group
  selector, now also matches these rear holes on a rear view, not only the
  fronts they used to match alone; a consumer counting bays should key off
  `[data-class=bay]` instead, and a document already selecting by group will
  now also hit the rear cutouts. In the explorer, a fibre's row says where it
  goes, selecting a fibre marks its far end on every loaded face, and a rear
  row reads as the slot it is, not the panel hole (roc-ops/Portrayal#535).
- Connector slots. A placement presenting a connector interface - `lc`,
  `lc-duplex`, `sc` or `mpo`, the new registry in
  `spec/schemas/connectors.yaml` - is now published where cages are: in each
  view's `cages[]` in `<device>.configs.json` and in each component's own
  `cages` in `components.json`, as an entry with `kind: connector` and
  `media: null`. Its `accepts` is every part whose `mates:` is the slot's
  interface, dust caps and plugs alike. Every entry, cage or connector, now
  carries `kind` (`cage` or `connector`), `default` (the ref the slot ships
  holding, or `null`) and `bores` (the ids of the slots a connector seated
  here takes the place of, `[]` where it spans nothing: `["1", "2"]` on a
  duplex LC adapter). A cage entry is otherwise unchanged; a reader that
  wants cages only filters on `kind: cage`. A configuration's `occupants:`
  now keys a slot at any depth, with every `module` step left out
  (`bay-1/lc01/1`, a bore of an adapter on a cassette in a bay), and lint
  L114, L115 and L116 hold the shipped default, the exclusion between a
  duplex slot and its two bores, and the duplex geometry.
- Every LC, SC and MPO port that ships capped now DRAWS ITS DUST CAP AS AN
  OCCUPANT: a group with `data-behaviour="occupies"`, `data-for` naming the
  slot and the id `<slot>-occupant` (`port-1510/1-occupant`), seated in every
  configuration that does not key the slot. The caps are
  `common/lc-dust-cap@1` (each bore of the Smartoptics
  `common/lc-duplex-adapter@6`, 72 on a DCP-R-34D-CS front),
  `common/lc-duplex-dust-cap@2` (the FS stacked adapter's own slot),
  `common/sc-dust-cap@1` (each opening of `common/sc-duplex-adapter@5`) and
  `common/mpo-dust-cap@2` (the FHD cassette rears' MPO bulkheads); the
  shuttered adapter ships none. AN AUDIT COUNTING OCCUPIED PORTS BY
  `data-for` / `data-behaviour="occupies"` NOW COUNTS CAPS: a capped port is
  occupied, by its cap. `configs[].occupants` still lists only what a
  configuration keys, and a slot's shipped cap is its `default`.
- New parts: the plugs `generic/lc-duplex-plug@2`, `generic/sc-plug@1`,
  `generic/mpo12-plug@1` and `generic/mpo24-plug@1`, which a connector slot
  offers beside its cap, and `std/lc-bulkhead-bore@1`, the panel adapter's
  keyed aperture, whose keyway runs 5.71 from the ferrule where the
  transceiver receptacle `std/lc-bore@3` stops short.
- The explorer swaps connector slots as it swaps cages - a cap, a plug or
  empty, one level of a duplex slot or the other - on a cassette's rear face
  as well as its front, and in 3D each seated cap and plug is its own part
  that pulls out. A device's lock now follows the components a module draws
  on its other `faces:`, so a change to a cassette's rear asks for a bump
  where it used to ask for nothing.
- A pluggable that `conforms:` to a module envelope declares `head:`, the box
  it occupies OUTSIDE its cage (contract key, plus the matching registry
  envelope on `sfp-module`, `qsfp-module` and `qsfp-dd-module`), and a `head`
  that exceeds its registry envelope may say so with `exceeds:` and a source.
  Lint L121 checks it. `components.json` carries a part's `head`, verbatim
  from its contract. See
  [pluggables-heads-design.md](docs/pluggables-heads-design.md).
- `generic/sfp-rj45@1`, the copper SFP generic, composing `std/rj45-ganged@2`
  in its head so a plug and boot can seat in it.
- `common/qsfp-pull-tab@2`: a real U-loop tab (two arms and a grip, measured
  off photographs and QSFP-DD HW 6.3 Appendix B) in place of the `@1` solid
  brick, composed again by the QSFP generics.
- `generic/qsfp-lc@2` and `generic/qsfp-dd-lc@2`, composing
  `common/qsfp-pull-tab@2` and declaring `head:`.
- A composed part now takes a field value from its host at build time when
  both declare the same field key (`render.py`'s `fill_from_attrs`); a part's
  own `parts:` entry `attrs` still win.
- Lint L73 counts a field as used when a composed part declares the same key
  as its host, matching the build-time rule above.
- Lint L76 (RJ45 jack lamps) skips a contract whose class is `transceiver`:
  a copper SFP's jack carries no link LEDs, so it is not asked for one.
- Cable ends: `generic/sfp-cable@1`, `generic/qsfp-cable@1`,
  `generic/qsfp-dd-cable@1` (Type 1, at the MSA maximum) and
  `generic/qsfp-dd-cable-type2@1`. Each is a module in the cage and a head,
  pull strap, strain relief and a short straight stub of cable outside it. The
  `cable` connection point sits at the stub's far end, so a downstream tool
  continues the run from there. The cage accept lists offer them beside the
  optics. See [pluggables-cables-design.md](docs/pluggables-cables-design.md).
- Vendor cable ends wrapping those generics, each with `cable-kind` (`dac`,
  `acc`, `aec` or `aoc`) and its own document's values:
  `molex/sfp-plus-passive-dac`, `amphenol/qsfp28-passive-dac`,
  `amphenol/qsfp56-linear-active`, `fs/qsfp28-aoc`, `siemon/qsfp28-aoc`,
  `volex/qsfp-dd-passive-dac` and `credo/hiwire-shift-qsfp-dd`, and the
  vendors `molex`, `amphenol`, `volex`, `credo` and `siemon`.
- A `cable-od` field (mm) on the cable ends, and a skin binding
  `data-r-from="<field>"` that sets a circle's radius to half a numeric field
  value, at build time and in the kit at runtime. Empty or absent leaves the
  drawn radius. Lint L122 keeps a `cable-od` (a field default or a composing
  part's attrs) between 2 and 15, and accepts only the plain decimal number
  the build and the kit read. Lint L73 counts `data-r-from` as wiring a field.
- A `cable` connection point may sit `on` a `cyl` relief feature; it leaves
  from the cylinder's far end (`lift` + `cyl`), in the build and in the kit.
- Six coax interfaces - `f-type`, `bnc`, `sma`, `smb`, `mcx` and `din-1-0-2-3`
  (spelled with hyphens; the schema's interface/mates pattern refuses a dot) -
  each citing its standard, so every existing coax port publishes a
  `kind: connector` slot alongside its cage. Two new jacks: `std/bnc@1` and
  `std/din-1-0-2-3@1` (cores), composed by the bezels `common/bnc-jack@1` and
  `common/din-1-0-2-3-jack@1`, following the existing SMA/SMB core-plus-bezel
  pattern. Six generic plugs, one per interface -
  `generic/f-type-plug@1`, `generic/bnc-plug@1`, `generic/sma-plug@1`,
  `generic/smb-plug@1`, `generic/mcx-plug@1` and `generic/din-1-0-2-3-plug@1` -
  each a coupling part, a crimp ferrule and strain relief, and a 30 mm cable
  stub sized by a `cable-od` field. A `seat-out` connection-point key: a
  number of mm a part seated at that point stands off, absolute from the
  part's own face, where no drawn feature's rear already sits at that plane;
  mutually exclusive with `on:` and read only on the presented point
  (`interface-at`, default `mate`; `manifest._seat_out`). Lint L106 refuses a
  point that carries both, a `seat-out` that is not a number at or above 0,
  and a `seat-out` on any other point. The kit now labels the coax media
  (BNC, 1.0/2.3, F, MCX) in its port rows. See
  [connectors-coax-design.md](docs/connectors-coax-design.md)
  (roc-ops/Portrayal#650).

#### Changed
- `juniper/mic-3d-8ds3-e3` and `mic-3d-8ds3-e3-v` (1.1.2): their 16 jacks
  state `impedance: 75`, and the description no longer calls 75-ohm
  mini-SMB an unmodelled interface. Mini-SMB is the 75-ohm SMB series, the
  SMB interface and intermateable with 50-ohm SMB, so the jacks were
  correctly SMB (roc-ops/Portrayal#672). The MX80, MX240, MX480, MX960,
  MX2008, MX2010 and MX2020 take a patch for the composed card.
- `common/qsfp-pull-tab@2` (2.2.0) models the strap's S-bend: each arm is six
  relief boxes along the reach (`arm-l`, then `arm-l-2` to `arm-l-6`, and the
  same on the right) that follow the side-view curve, down 1.5 into a dip
  about 31 from the nose front and back up to the grip, meeting end to end.
  The tab's vertical figures were read again on fitted body edges: the grip
  top is 1.23 above the module top (was 1.07) and the strap top 0.47 (was
  0.57), so the size is 19 x 8.56 and the risers end 7.33 below the module top,
  where they were measured. `generic/qsfp-lc@2` and `generic/qsfp-dd-lc@2`
  (2.2.0) compose the tab at `at: [-0.325, -1.23]`. The face-on drawing is
  unchanged apart from that 0.16 shift. No device seats these parts, so no
  lock moved (roc-ops/Portrayal#647, roc-ops/Portrayal#685).
- `std/c20-inlet` (1.3.1) lays all three blades along the long side of the
  recess, as IEC 60320 C19/C20 has them and the SCHURTER C20 front view it
  cites draws them: line and neutral 13.0 apart, earth 8.0 off their line, in a
  29.0 x 21.0 recess. It had drawn them across the long side. Ids, size and
  connection point are unchanged; the 27 devices that seat it take a patch.
- `generic/qsfp-lc@2` (2.1.0) draws its nose at the height the maintainer's
  photographs of a QSFP SR4 module show: 1.4 above and 1.4 below the 8.5 body,
  11.3 tall, so `head` is `at: [0, -1.4]`, `h: 11.3` in `components.json`, and
  the `body` outline and its 20 mm solid grow to match. `common/qsfp-pull-tab@2`
  (2.1.0) gains `riser-l` and `riser-r`, the posts at the arm roots (7.5 out
  from the nose front, 7.8 tall from the strap top), and its size grows from
  19 x 3.4 to 19 x 8.3. `generic/qsfp-dd-lc@2` (2.1.0) wears the risers through
  the tab; its head is unchanged, since no QSFP-DD module has been measured.
  Ids, connection points and placements are unchanged, and no device seats
  these parts, so no lock moved (roc-ops/Portrayal#646).
- In 3D, a solid painted from a field now takes its side colour from the
  field: the QSFP cable end's strap, ring and stub (so a wrapper's green or
  blue strap and the Siemon AOC's aqua jacket show on every face), every coax
  plug's cable stub, and the DCS201 and DCS240 fan handles. Their relief
  features stated a literal `color`, which the kit never overrides; the parts
  take a patch, and the DCS201, DCS202, DCS240 and DCS511 a patch for the
  fans. Lint L73 now refuses a relief `color` on a node a field paints
  (roc-ops/Portrayal#643).
- Lint L122 now also reads a `cable-od` a device sets on a placement (a
  cable end placed `mate-to` a jack or cage), with the same number and range
  check as a wrapper's (roc-ops/Portrayal#644).
- `siemon/qsfp28-aoc` (1.1.1) draws its pull tabs black (`latch-color:
  #090502`), read off the product photograph the aqua jacket came from, in
  place of the generic's neutral grey (roc-ops/Portrayal#645).
- **`contract: 2`. A drawing no longer embeds the device's source manifest.**
  Every face carried the same whole manifest in its `<metadata>`: 139 MB of a
  249 MB build, 107 KB in each of the R740xd's 252 faces. It is now published
  once per device as `<device>.source.json`, and the `source` key in a face's
  metadata is replaced by `source-sha256`, the digest of that file's exact
  bytes. A reader that took the manifest from any drawing reads the one file
  instead. What is published is unchanged; only where (roc-ops/Portrayal#665).
- **Each distinct drawing is written once.** Configurations that differ only in
  a part a face cannot see draw that face identically, and each wrote its own
  copy: the R740xd's 42 configurations wrote 252 faces holding 35 distinct
  drawings. A drawing is now written once, named after the first configuration
  (in manifest order) that draws it, and `configs[].files` in
  `<device>.configs.json` maps each configuration's faces to their files. **Find
  a face through `files`**; `<device>.<config>.<view>.svg` exists only for the
  configuration that names it. A face no longer carries its configuration's
  name: `data-config` on the root and `config` in `<metadata>` are gone, since
  a shared drawing belongs to several. The default configuration's
  `<device>.<view>.svg` copies are unchanged (roc-ops/Portrayal#665).
- **Also in `contract: 2`: `overlays.json` is gone;** `listings.json` replaces
  it (roc-ops/Portrayal#674). The NOS naming an overlay carried under the
  hardware (`devices/edgecore/as7726-32x/overlays/arcos.yaml`) now lives in the
  NOS vendor's listing (`devices/arrcus/as7726-32x/listing.yaml`), and the
  overlay's `identity:` block is retired - the listing's namespace is the
  vendor. Lint L56 now checks a listing: it lives under a software vendor and
  names only configurations, ports and components its hardware has.
- **BREAKING for DCIM data already imported.** The Arrcus device types are
  renamed from `Arrcus/ArcOS on <SKU>` to `Arrcus/<SKU>` - the hardware's SKU,
  under the NOS vendor, as NetBox's and Nautobot's own libraries file a
  disaggregated box - and they now carry the hardware's part number, which the
  identity export dropped. The metal is the same metal and its part number
  still orders it; a listing that publishes its own replaces it per
  configuration. `dcim_export.py --nos` is removed: every listing exports.
- **BREAKING for DCIM data already imported.** A module type names its ports per
  bay. Every interface, console, power, front and rear port name on a card
  starts with `{module}/`, which NetBox and Nautobot both fill with the position
  of the bay the card is installed in, and a device type's bay `position` is now
  the bay's whole id (`slot-1`, `psu-2`, `fan-1`) where it was the trailing
  number (`1`, `2`, `1`). A DCP-404 in the DCP-2's `slot-1` installs its client
  port as `slot-1/c1`: the drawing's path to that port (`slot-1/module/c1`) with
  `/module/` taken out. Before this, two identical cards in one chassis both
  made `c1`, and since a port name is unique on its device the second install
  was refused; and 167 of the 205 bayed device types put two bays at one
  position (Fan 1, PSU 1 and slot-1 all at `1`), so the token alone would not
  have been enough. The fibre maps name ports the same way.

  Re-importing the types does not update what a DCIM has already made from them.
  A DEVICE created before this keeps its old bay positions, because both DCIMs
  copy a device type's module bays onto the device when it is created: a card
  installed afterwards into that device's `slot-1` resolves to `1/c1`, not
  `slot-1/c1`, which still does not match the drawing, and it can still collide
  wherever Fan 1, PSU 1 and slot-1 all sit at `1`. On an existing device, edit
  each module bay's position to the bay's id (the `position` in the device type)
  before installing cards. A MODULE installed before this keeps its old port
  names until it is removed and installed again.
- THE ASR 9000 CARD STANDARD. Every full-size ASR 9000 card and every bay that
  takes one is 41.4 x 395.7 mm, with a 355.6 mm `opening`, so a card seats and
  draws the same in each chassis that accepts it. RSPs and RPs are no longer
  drawn larger than the line cards beside them (the RSP-880 was 46.0 x 428.5,
  32.8 mm past its slot on the ASR 9006). Majors, each a new directory with the
  old one removed, for the 48 cards whose size changed: `cisco/a99-10x400ge-x-se`, `cisco/a99-10x400ge-x-tr`, `cisco/a99-4hg-flex-se`, `cisco/a99-4hg-flex-tr`, `cisco/a99-rp3-se`, `cisco/a99-rp3-tr`, `cisco/a99-rsp-se`, `cisco/a9k-16t-8-b`, `cisco/a9k-24x10ge-se`, `cisco/a9k-2x100ge-se`, `cisco/a9k-36x10ge-se`, `cisco/a9k-400g-dwdm-tr`, `cisco/a9k-40ge-b`, `cisco/a9k-40ge-e`, `cisco/a9k-40ge-l`, `cisco/a9k-4hg-flex-se`, `cisco/a9k-4hg-flex-tr`, `cisco/a9k-4t-b`, `cisco/a9k-4t-e`, `cisco/a9k-4t-l`, `cisco/a9k-8t-4-b`, `cisco/a9k-8t-4-e`, `cisco/a9k-8t-4-l`, `cisco/a9k-8t-b`, `cisco/a9k-8t-e`, `cisco/a9k-8t-l`, `cisco/a9k-mod160-se`, `cisco/a9k-mod160-tr`, `cisco/a9k-mod200-se`, `cisco/a9k-mod200-tr`, `cisco/a9k-mod400-se`, `cisco/a9k-mod400-tr`, `cisco/a9k-mod80-se`, `cisco/a9k-mod80-tr`, `cisco/a9k-rsp-8g`, `cisco/a9k-rsp`, `cisco/a9k-rsp440-se`, `cisco/a9k-rsp440-tr`, `cisco/a9k-rsp5-se`, `cisco/a9k-rsp5-tr`, `cisco/a9k-rsp880-lt-se`, `cisco/a9k-rsp880-lt-tr`, `cisco/a9k-rsp880-se`, `cisco/a9k-rsp880-tr`, `cisco/a9k-sip-700-8g`, `cisco/a9k-sip-700`, `cisco/asr-9922-rp-se`, `cisco/asr-9922-rp-tr`, all @1 to @2.
  A ref naming an old major resolves to nothing; the dist `contract` number is
  unchanged. Their art keeps every port, lamp and legend at its drawn size and
  moves it in proportion. Bays on the ASR 9006, 9010, 9904, 9906, 9910, 9912 and
  9922 keep their centres; the ASR 9010 slots are evenly spaced again. Cards
  that had been left out of `accepts` only for size now seat: `a9k-2x100ge-se`
  and `a9k-400g-dwdm-tr` on the 9006 and 9922, `a9k-400g-dwdm-tr` on the 9912,
  and `a99-10x400ge-x-se`/`-tr` and `a9k-400g-dwdm-tr` on the 9904
  (roc-ops/Portrayal#16).
- The ASR 9001 MPA bays reserve the MPA envelope, 34.54 x 161.8, with the
  measured hole as their `opening`, matching the A9K-MOD carriers; both SIP-700
  cards reserve 167.87 for all four SPA subslots.
- Pluggable cage accept lists (`cages[].accepts`) now apply the rate ceiling
  to the vendor cable ends: a part is offered only in a cage at or above its
  rung. The seven cable-end wrappers (1.1.0) state that rung as `attrs.rate`;
  they said `media`, which the ceiling does not read, so every one was offered
  in every cage of its family - the 10G SFP+ DAC in 1G SFP cages, the 200G
  QSFP56 cable in 100G QSFP28 cages. Their exports list `rate:` where they
  listed `media:`.
- Ten SFP-class ports stated `media: sfp` (the 1G rung) for 10G SFP+ or 25G
  SFP28 ports their own descriptions name: the SFP groups of `edgecore/agr560`,
  `eps112`, `eps121`, `eps122` (now `sfp-plus`) and `eps201`, `eps202`,
  `eps203` (now `sfp28`), the `edgecore/dcs520` management SFP+ ports and the
  `juniper/mx304` PTP port (`sfp-plus`). Their `optics-sfp` prose follows the
  media to `optics-sfp-plus` / `optics-sfp28`. Exported interface types do not
  change.
- Lint L102 refuses a part that mates a pluggable family and names one of
  that family's rungs as `media` instead of `rate`. Lint L12 refuses a
  configuration that seats a part whose `rate` is above its cage's media on
  the part's own family ladder.
- Lint L12 now lets a configuration seat what a cage's accept list offers
  through its family's `also-accepts` (a QSFP part in a QSFP-DD cage), which
  it refused; a QSFP cage still refuses a QSFP-DD part. The rate check also
  covers a cage on a seated card, reading the card's own part and group
  media (#630).
- `generic/qsfp-lc@1` and `generic/qsfp-dd-lc@1` are superseded by `@2`
  (above); `@1` is kept for fixtures pinned to it.
- `common/qsfp-pull-tab@1` is superseded by `@2` (above); `@1` is kept, with
  its `white` and `blue` skins, for `common/qsfp-transceiver@1`, which still
  composes it.
- Lint L121 no longer holds a feature that starts at or behind the back of
  a part's `head:` (a cable end's strap and ring) to the head envelope.
- Lint L99 refuses `cable-kind` on a generic, as it refuses rate and reach.
- A component preview now also takes in the part's own relief features and
  the preview of each part it composes, so a wrapper's preview shows its
  generic's head, strap and ring.
- `common/qsfp-pull-tab@2` (2.0.3) labels its photograph readings
  `photo-measured`, not `measured`: the arm features, `size-confidence.h` and
  the `shape` provenance.
- The three component previews whose part declares an overhanging `head:`
  (`generic/sfp-rj45`, `generic/qsfp-lc`, `generic/qsfp-dd-lc`) are framed to
  include it, instead of clipping to the part's size box.
- The S8901-54XC management jack now renders its declared black finish
  (`#2b2f33`) on the composed `std/rj45@2` housing it seats, instead of the
  housing's own default; this is what the kit already painted at runtime.
- `ufispace/psu-132-ac` and `psu-132-dc` (1.1.0) describe and default to the
  EXHAUST units, PSU-132-AESR and PSU-132-DESR, which are front-to-back for a
  rear-mounted supply. They claimed the intake AISB1/DISB1 were front-to-back.
  The S9300-32D and S9301-32DB front-to-back builds named the intake parts and
  now name the exhaust ones, and their back-to-front builds name the intake
  ones. The reasoning is on the part's `airflow` provenance, and a
  `psu-airflow-sku-mapping` gap records that no document for these chassis
  states the pairing (roc-ops/Portrayal#513).
- The Edgecore CSR440's airflow is `front-to-back`, not `side`: every row of its
  datasheet ordering table says so, where the side-breathing CSR310 and CSR200
  say "Side-to-Side".
- The COR580 AC build and the DCS510 state `power: [ac, hvdc]`: their 1300 W AC
  supply is also rated 190-310 VDC. The DCS510's `input-dc` attr, which held
  that figure and read as a -48 V build it does not sell, is `input-hvdc`.
- The Edgecore, UfiSpace and Celestica devices spell their input ratings one
  way, `input-ac` and `input-dc` under `attrs.power`, so the SVG root's
  `data-power-input-ac`, `data-psu-ac-input`, `data-psu-input-ac`,
  `data-ac-input` and `data-system-input-rating-per-psu` (and their DC twins)
  are now `data-input-ac` / `data-input-dc`. A bare `input` that held both
  ("AC 100 to 240V...; DC -36 to -72V...") is split into the two keys, and
  the DCS510's `power-input-ac-current` is `input-ac-current`. Values are
  unchanged; each device took a patch bump (roc-ops/Portrayal#513).
- Every fibre a connector declares is now a node you can address: a bore or a
  `class: fibre` element numbered `1` through `optical.positions`, `X/n` on a
  port that carries more than one. Lint L112 holds it - a connector composes a
  bore for each position or draws its own fibre element, and a cassette's rear
  face reuses none of the front's ids. The three duplex adapters
  (`common/lc-duplex-adapter`, `common/lc-duplex-v-adapter`,
  `common/sc-duplex-adapter`) move to v5 for it: their two bores are `1` and
  `2`, not `tx` and `rx`, so a consumer addressing `.../tx` or `.../rx` on one
  of these adapters finds nothing where it used to find a bore (a
  transceiver's own tx/rx faces are unchanged). 29 parts that compose one of
  these adapters took a major bump, and the five devices that seat them
  followed: `fs/fhd-1ufce` 4.0.0, `smartoptics/dcp-2` 2.0.0,
  `smartoptics/dcp-m32-cso-zr` 3.0.0, `smartoptics/dcp-r-34d-cs` 4.0.0 and
  `smartoptics/dcp-r-9d-cs` 4.0.0. The MPO/MTP flange adapters
  (`common/mpo-flange-adapter`, `common/mpo24-flange-adapter`) carry a new
  `opening` element for the keyed bulkhead itself, `class: port` and marked
  `data-inner="1"` so `[data-class=port]:not([data-inner])` still counts one
  connector per adapter, and fibre elements `1..12` (the 24-fibre part
  `1..24`), numbered as the plug numbers them rather than as a viewer sees
  them. Both adapters took a minor bump, 1.1.1 to 1.2.0
  (roc-ops/Portrayal#533).
- A SPANNING SLOT'S `cages[].rotate` IS THE SUMMED TURN, not the
  placement's own. A duplex connector is one moulding and cannot turn
  itself, and the two LC duplex adapters run their pairs on different axes,
  so a slot that spans two bores publishes its placement's `rotate` plus the
  turn carrying the canonical across-axis onto its own bores: an unturned FS
  stacked adapter's slot publishes `270`. That is the turn the build seats
  its occupant at. Every other entry's `rotate` is its placement's as
  before, `null` included. `mate` is still taken through the placement's
  own `rotate` alone.
- Majors, each a new directory with the old one removed:
  `common/lc-duplex-adapter` and `common/lc-duplex-v-adapter` @5 to @6 (they
  compose `std/lc-bulkhead-bore@1`, and the Smartoptics adapter's ferrule
  axis moved 0.32 within its body, with its placements moved to keep every
  fibre where it was); `std/mpo` @1 to @2 (its opening corrected to what an
  MPO plug can enter), with `common/mpo-adapter`, which composes it, and
  `common/mpo-flange-adapter` and `common/mpo24-flange-adapter`, which take
  its opening and are now `mpo` slots, @1 to @2;
  `common/lc-duplex-shuttered-adapter` @1 to @2 (now a slot, with two
  bores); `generic/lc-plug` @1 to @2 (drawn latch down, in its bore's
  convention). A ref naming an old major resolves to nothing. The dist
  `contract` number is unchanged, as it was for roc-ops/Portrayal#533.
- `ufispace/n3100-4c` IS NO LONGER A DEVICE. The UfiSpace N3100-4C timing card
  left `devices.json`, and its `device-types/UfiSpace/N3100-4C.yaml` exports with
  it. It is now `ufispace/n3100-4c@1`, a full-height PCIe card module, exported as
  `module-types/UfiSpace/N3100-4C.yaml` with four 25G SFP28 interfaces and its
  SMB/SMA timing jacks, and accepted by every full-height slot of the Dell R740xd's
  risers (roc-ops/Portrayal#625).
- Majors, each a new directory with the old one removed, because the full-height
  PCIe bracket was drawn mirrored (its keyed flange steps up, seen from outside
  with the tip at the left): `std/pcie-bracket-fh` @1 to @2 (its body moved 3.17
  down inside an unchanged box, so its `opening` element is at y 6.35),
  `dell/pcie-filler-fh-14g` @1 to @2 and `common/pcie-card-fh` @1 to @2 (drawn in
  the bracket's frame, so they moved with it; the generic card also gained a body
  built from PCIe CEM 5.0), and the ten Dell risers whose bays seat it -
  `dell/riser-1-none-14g`, `riser-1a-14g`, `riser-1b-14g`, `riser-1d-14g`,
  `riser-2a-14g`, `riser-2d-14g`, `riser-2e-14g`, `riser-2f-14g`, `riser-3a-14g`
  and `riser-3b-14g` @1 to @2, their full-height bays moved to keep every opening
  where it was. A ref naming an old major resolves to nothing. The dist
  `contract` number is unchanged (roc-ops/Portrayal#625).
- Ten routing-engine, control-board and sled modules now group their ports:
  `juniper/jnp10k-re1@2`, `re-s-1300@1`, `re-s-1300-v@1`,
  `mx2000-cb-re-v@1`, `mx2008-rcb-v@1`, `jnp10003-rcb@1`, `jnp304-re@1`,
  `mx104-re@1`, `cisco/a99-rp-f@1` and `edgecore/amx-3200-sled400@1`.
  Management and timing jacks are role `management`, and the sled's CFP2 and
  QSFP28 ports are role `traffic` at 400g and 100g. Management Ethernet
  states 1g where a guide gives the rate; the RE-S-1300's sources disagree,
  so it has none. The port media are corrected: console and auxiliary ports
  `rj45-serial`, ToD `rj45-tod`, BITS `rj48` (all were `rj45`). Each module
  took a minor bump, and the fifteen devices that seat them took a patch
  bump. Part ids are unchanged (roc-ops/Portrayal#511).
- Timing and console jacks say what they carry in `data-media` instead of
  `rj45`: ToD and PPS/ToD jacks are `rj45-tod`, BITS and external-clock jacks
  `rj48`, stacking-sync jacks `rj45-sync`, the CSR440's alarm jack `rj45-alarm`,
  and consoles and AUX ports `rj45-serial` (roles `console` / `aux`). A selector
  for `[data-media='rj45']` now finds Ethernet only. 33 more device-level
  ports gained a `data-speed` their sources state - the MX150's ten copper
  access ports, management jacks across Cisco, Juniper, Edgecore, UfiSpace,
  Celestica and MaiaEdge, the ASR 9001's cluster ports (`10g`, media now
  `sfp-plus`), its and the ASR 9901's IEEE 1588 service LAN ports (`100m`),
  and three Smartoptics OSC cages (`1g`). Device types follow: those OSC cages
  and the ES1010 management SFP export as `1000base-x-sfp` (were
  `25gbase-x-sfp28`, a default), the ASR 9001 cluster ports as
  `10gbase-x-sfpp` (were `25gbase-x-sfp28`), the service LAN ports as
  `100base-tx` (were `1000base-t`), and 24 device types gain the
  `Console` console port they had been missing. Lint L113 holds it; 58 devices
  took a patch bump (roc-ops/Portrayal#511).
- `data-speed` is spelled from one closed set - `10m 100m 1g 2.5g 5g 10g 20g
  25g 40g 50g 100g 200g 400g 800g 1.6t`, in `spec/schemas/speeds.yaml` - and
  means the highest native rate the port runs at. **Values a consumer may filter
  on changed:** `100m-1g`, `1000base-t`, `100/1000base-t` and `10/100/1000` are
  all `1g`; `400g-capable` is `400g`; the MX304's GM/PTP port is `10g`, with its
  reserved-for-future-use caveat moved to the placement's description. USB
  generation left `speed` for its own `data-usb` (`2.0`, `3.0`; was `usb2`,
  `usb-2.0`, `usb3`, `usb-3.0`), and the HLX-TGV's PON port is `speed: 10g` with
  `data-pon="xgs-pon"` (was `10g-pon`). The MX304 LMIC16's twelve 100G-only
  ports now state `100g` (its module type still exports all sixteen by the
  cage, as `400gbase-x-qsfpdd`, as before). Lint L110 holds the set. 63 devices took a patch bump,
  and `juniper/mx304-lmic16`, `juniper/jnp304-re` and `smartoptics/dcp-f-a22` a
  patch each (roc-ops/Portrayal#512).
- Device types export the CSR180's and CSR200's four RJ45 traffic ports each as
  `1000base-t`; their `100/1000base-t` spelling had no interface-type row, so
  all eight exported nothing. For the same reason the management SFP on the
  DCP-2, DCP-R-34D-CS and DCP-R-9D-CS (`100m-1g`) now exports as a
  management-only `1000base-x-sfp`, and the MX304's GM/PTP SFP as a
  management-only `10gbase-x-sfpp` (roc-ops/Portrayal#512).
- `attrs.features.vendor-alias`, `attrs.features.marketing-name` and
  `attrs.platform.oem-alias` are gone from `configs.json` `attrs`, and from the
  facts list in the DCIM exports' comments. Their values moved to the
  top-level `aliases` above, with any caveat kept as the alias's note in the
  manifest; the exports' comments name the aliases on an "Also sold or listed
  as" line instead (roc-ops/Portrayal#514).
- `group-role` takes a sixth value, `fabric`: the cell or chassis interconnect
  ports of a distributed chassis. The 241 fabric ports on nine DDC boxes carry
  `data-group-role="fabric"` where they carried `traffic` (the S9700-53DX,
  S9701-82DC, S9705-48D, S9710-76D, S9720-56ED, S9725-64E, COR550 and COR580)
  or `service` (the S9700-23D), so a filter on `traffic` now sees fewer ports
  and `[data-class="port"][data-group-role="fabric"]` selects exactly the
  fabric. Group names and port ids are unchanged, and the NetBox and Nautobot
  exports list these ports as interfaces exactly as before. Fabric CARD slots
  stay `service` (roc-ops/Portrayal#510).
- A pluggable cage's `rotate`, and so `cages[].rotate`, has one meaning: 0 is a
  module seated upright, bail at the top and belly at the bottom. Every
  belly-to-belly SFP/QSFP/QSFP-DD stack is drawn upper 0 over lower 180, or left
  270 beside right 90 on a card drawn on its side, so an optic seated by its
  cage's turn has its bail outward; the std cage skins draw their lip at the
  bottom of the opening, `common/qsfp-cage@3` its flange, and lint L108 holds
  the rule. 62 devices took a major bump for turned or re-anchored placements
  and 85 cards a minor; OSFP stacks are left as drawn
  (docs/pluggables-3d-design.md, S1-S8).
- Exported `description` fields are cut at a word boundary with a trailing
  `...`, and bay `Accepts:` lists at a whole entry with `(+N more)`. 266
  descriptions used to end mid-word, and 62 were cut at a decimal point —
  the MX104's read `Juniper MX104 - a 3` (roc-ops/Portrayal#187).
- Module-type port lists are ordered by name rather than by where the jack is
  drawn, so a card and its rotated twin produce one document (roc-ops/Portrayal#267).
- The Edgecore 2RU fan tray is `edgecore/fan-2u-1x1sn@1` in `components.json`
  and in every bay that seats it; it was `edgecore/ais800-64-fan@1`, which named
  one of the three chassis that share the part. `AIS800-64D`, `AIS800-64O` and
  `AGR560` took a major bump for the changed bay addressing (roc-ops/Portrayal#420).
- Five Edgecore module types export under the ordering code Edgecore prints
  instead of a description of the part: `FAN-1U-1x1E` (was `AS5835-54X Fan
  Tray`), `FAN-1U-1x1N` (`AS9726-32DB Fan Tray`), `FAN-1U-1x1J-S` (`AS7315-27X
  Fan Tray`), `SPAACTN-03BG` (`AS7315-27X AC PSU`) and `CRXT-T0T12BS`
  (`AS7315-27X DC PSU`). Both the document name and the `model` field move, in
  `components.json` and in the NetBox and Nautobot module-type exports, so a
  consumer matching on an old name finds nothing where it used to find a module
  type (roc-ops/Portrayal#426).
- `dell/riser-lower-trim-14g@1` is retired and leaves `components.json`, and
  the R740xd's rear placement `riser-1-trim` (`rear/placements/riser-1-trim`)
  is gone from every configuration; the R740xd takes a major, 24.0.0. The
  strip hid the bottom riser-1 card's keyed flange, which
  `std/pcie-bracket-fh@1` drew stepping down past the plate; `@2` steps it up,
  and Dell's service model has no metal there in front of the rear sheet
  (roc-ops/Portrayal#623).

- A forwarding wrapper's presented depth now includes its composed core's own
  seat out, not only the wrapper's placement `lift`: `common/sma-jack@1`,
  `common/smb-jack@1`, `common/bnc-jack@1` and `common/din-1-0-2-3-jack@1` (and
  the library's other bezels) present as deep as their core stands bare.
  `std/mcx@1`'s mate moves `on: barrel` (2.0), so a seated MCX plug now stands
  proud of the panel by the barrel's height rather than at the panel plane;
  the MCX cages on `casa/c100g` and `casa/c40g` (104 placements) published
  lift 0 before this and 2.0 after, and both took a patch bump. `std/bnc@1`, `std/din-1-0-2-3@1`
  and `std/f-type@1` each carry a `seat-out` (3.7, 3.85 and 7.8 respectively),
  so a seated plug on those jacks now presents at the mated plane instead of
  the panel face.
- The Cisco T3/E3 SPAs `spa-2xt3e3`, `spa-4xt3e3`, `spa-2cht3-ce-atm`
  and `spa-4xct3-ds0` (1.1.0) draw their 1.0/2.3 jacks as real
  `common/din-1-0-2-3-jack@1` placements instead of skin art, so they now
  publish `kind: connector` slots; `cisco/asr-9010`, the only device that
  seats one of them, took the patch bump devicelock asked for.
- `juniper/mic-3d-8ds3-e3` and `mic-3d-8ds3-e3-v` (1.1.1) correct their
  description: the SMB-opening jacks are drawn because the hardware is
  75-ohm mini-SMB, not because "no BNC standard exists in the registry yet".
  The jacks and their placements are unchanged.
- Devices bumped for the coax jack and seat-out changes above:
  `casa/c100g`, `casa/c40g`, `cisco/asr-9010`, `commscope/ch3000`,
  `juniper/mx2008`, `mx2010`, `mx2020`, `mx240`, `mx480`, `mx80` and `mx960`
  (roc-ops/Portrayal#650).

The dist `contract:` number does not move for the pluggable-heads entries in
this section (the superseded QSFP generics and pull tab, the wider head
previews and the S8901-54XC finish correction): each is additive (a new key,
a new part, a superseded-not-removed part, a wider preview frame, a colour
correction), per this file's own rule. Nor does it move for the coax entries
above: the six interfaces, the new jacks, plugs and `seat-out` key are all
additions, and the moved SPA jacks and the corrected MIC description change
no field a reader already depends on.

#### Fixed
- A seated part turns with the aperture it is in when its host FORWARDS that
  aperture from a composed part (roc-ops/Portrayal#548). The composed part's
  own `rotate` was left out, so a plug seated in generic/sfp-lc-simplex@2 or
  generic/sfp-rj45@1 (each composes its one aperture at 180) was drawn 180
  degrees out, and an optic `mate-to` a card whose cage is a part at 90 was
  drawn crosswise. The drawn `rotate()` of such a seat changes, and so do
  those two parts' `presents.rotate` in `components.json` (now 180). No
  device in the library seats either case today, so no compiled face changes.
- `devices_index` fails when two devices share a name. Dist filenames carry no
  vendor, so they would otherwise render over each other in silence (roc-ops/Portrayal#185).

## Before this file

The build had no version, no tag and no changelog: a consumer could not tell a
breaking change from a Tuesday. Everything before `contract: 1` is unversioned
and should be re-fetched rather than diffed.

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

### Added
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
  (roc-ops/Portrayal#765).
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

### Changed
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
- The DCIM exports no longer call every device without `ru` a 1U full-depth
  rack device. A box that is not racked exports `u_height: 0`, not full depth,
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

## 0.1.0 (unreleased) - the first public release

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

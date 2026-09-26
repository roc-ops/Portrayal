# Changelog

What changed in the **dist contract** — the files under `library/dist/` that a
consumer outside this repository reads. `devices.json` carries a `contract`
number; this file says what each one meant.

The contract number goes up when a field a reader depends on is **removed,
renamed, or changes meaning**. Adding a field does not move it: a consumer that
ignores a new key is unaffected, and one that wants it can look.

The library itself is versioned per device (`device.lock.json` beside each
manifest) and per component (`version:` in each contract). This file is about
the *published build*, not about the hardware.

## Unreleased

### Added
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

### Changed
- **BREAKING for DCIM data already imported.** A module type names its ports
  per bay. Every interface, console, power, front and rear port name on a card
  starts with `{module}/`, which NetBox and Nautobot both fill with the
  position of the bay the card is installed in, and a device type's bay `position` is now the bay's whole id (`slot-1`, `psu-2`,
  `fan-1`) where it was the trailing number (`1`, `2`, `1`). A DCP-404 in the
  DCP-2's `slot-1` installs its client port as `slot-1/c1`: the drawing's path
  to that port (`slot-1/module/c1`) with `/module/` taken out. Before this, two
  identical cards in one chassis both made `c1`, and since a port name is unique
  on its device the second install was refused; and 167 of the 205 bayed device
  types put two bays at one position (Fan 1, PSU 1 and slot-1 all at `1`), so the
  token alone would not have been enough. The fibre maps name ports the same
  way.

  Re-importing the types does not update what a DCIM has already made from
  them. A DEVICE created before this keeps its old bay positions, because both
  DCIMs copy a device type's module bays onto the device when it is created: a
  card installed afterwards into that device's `slot-1` resolves to `1/c1`,
  not `slot-1/c1`, which still does not match the drawing, and it can still
  collide wherever Fan 1, PSU 1 and slot-1 all sit at `1`. On an existing
  device, edit each module bay's position to the bay's id (the `position` in
  the device type) before installing cards. A MODULE installed before this
  keeps its old port names until it is removed and installed again.
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

The dist `contract:` number does not move for the pluggable-heads entries in
this section (the superseded QSFP generics and pull tab, the wider head
previews and the S8901-54XC finish correction): each is additive (a new key,
a new part, a superseded-not-removed part, a wider preview frame, a colour
correction), per this file's own rule.

### Fixed
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

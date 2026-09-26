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
  build (the N3100-4C PCIe card, fed by its host slot, is the one without), and four more state `airflow` (AS7946-30XB and
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

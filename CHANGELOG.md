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

### Changed
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

### Fixed
- `devices_index` fails when two devices share a name. Dist filenames carry no
  vendor, so they would otherwise render over each other in silence (roc-ops/Portrayal#185).

## Before this file

The build had no version, no tag and no changelog: a consumer could not tell a
breaking change from a Tuesday. Everything before `contract: 1` is unversioned
and should be re-fetched rather than diffed.

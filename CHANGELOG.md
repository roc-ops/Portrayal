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
- Every `configs[]` entry in `<device>.configs.json` carries `airflow` —
  `front-to-back`, `back-to-front`, `side` or `passive`, or `null` where the
  device states none — resolved the way each drawing's `data-airflow` is (the
  configuration's value, else the chassis's). The `chassis` block carries the
  chassis's own `airflow`. A page filtering builds by airflow no longer parses
  it out of a configuration's name or description (roc-ops/Portrayal#513).
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

### Changed
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

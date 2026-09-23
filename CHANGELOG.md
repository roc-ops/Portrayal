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

### Changed
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

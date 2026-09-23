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
  `mgmt_only` (roc-ops/Portrayal#511).
- `data-inner="1"` on the inner part of a composed port, the `std/*` core that
  `common/rj45-eth@1`, `common/qsfp28-cage@3`, `common/sfp-plus-cage@2` and
  `common/rj45-ganged-eth@1` draw as a nested `data-class="port"` element.
  The core keeps its class. An audit that counts ports should skip it with
  `[data-class=port]:not([data-inner])` (roc-ops/Portrayal#511).
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

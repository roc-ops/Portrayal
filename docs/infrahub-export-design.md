# Infrahub export: which schema to target

Status: schema decided 2026-10-18. Issue #1115, part of #1111 (decided
2026-10-18: Infrahub is the next DCIM export target). This note is the issue's
first step, the choice of schema. The choice, C plus the two-attribute overlay
(section 4), was decided on 2026-10-18; section 6 records it. The exporter is
not built yet, and questions 3 to 9 in section 6 remain open.

Builds on `spec/tools/portrayal/dcim_export.py` (`build`, `build_module`,
`iface_type`), the NetBox trees under `library/exports/netbox/`, and the rack
import files written by `kit/rack/dcim-rules.js`.

## 1. Sources, and what was read

Read on 2026-10-18.

| Source | What was read |
|---|---|
| https://docs.infrahub.app/schema-library/reference/dcim | The DCIM reference page, read through a page-to-text tool. Cross-checked against `base/dcim.yml` below. |
| https://github.com/opsmill/schema-library at `main`, commit `26336e9026dff1907f2c58e81dd6ae7b5c3f763e` (committed 2026-10-09) | The raw YAML of `base/dcim.yml`, `base/location.yml`, `base/organization.yml`, `extensions/rack/rack.yml`, `extensions/cable/cable.yml`, `extensions/device_module/device_module.yml`, `extensions/module_port/module_port.yml`, `extensions/patch_panel/patch_panel.yml`, `extensions/location_site/location_site.yml`, `experimental/location_extended/location_extended.yml`, `extensions/transceiver/transceiver.yml`, `objects/base/02_dcim.yml`, `objects/extensions/rack/rack.yml`, and the repository `README.md`. |
| https://docs.infrahub.app/infrahubctl/infrahubctl-object | `infrahubctl object load` and `validate`. |
| https://docs.infrahub.app/infrahubctl/infrahubctl-schema | `infrahubctl schema load` and `check`. |

Not read, so nothing below rests on them: the Infrahub guides for the object
file format, object templates and `generate_template`, the GraphQL API, the
attribute kinds page, and the docs pages for the rack and cable extensions
(their YAML was read instead). `base/ipam.yml` and `extensions/location_minimal`
were listed but not read in full. Where a claim depends on a page not read,
it says so.

What the sources say, in short:

- The library's README says Infrahub ships without built-in schemas. Every
  instance runs a schema somebody loaded.
- The library calls itself "a collection of examples intended to serve as
  inspiration" and "experimental"; each file says it is "a starting point,
  not a finished production model". Its node names may change.
- `infrahubctl schema load SCHEMAS...` takes `--branch` and `--wait <seconds>`.
  `infrahubctl object load PATHS...` takes `--branch`. The object page does not
  say whether a path may be a directory, and says nothing of file format or
  load order. The format below is taken from the library's own
  `objects/**/*.yml` files (`apiVersion: infrahub.app/v1`, `kind: Object`,
  `spec: {kind, data}`).

## 2. What Portrayal holds, and what the library schema can take

Portrayal holds four things (#1111): device types with ports and bays, front
and rear drawings, racks with U positions, and cables.

At the commit above, the library has more than the DCIM page shows. The issue
said the page defines no Rack and no cable node, and it does not. But the same
repository has `extensions/rack`, `extensions/cable`, `extensions/device_module`,
`extensions/module_port` and `extensions/patch_panel`. The issue also said the
patch-panel extension could not be confirmed. It exists.

### The three choices

**A. The library DCIM schema plus Rack and Cable nodes of our own** (the issue's
first option). The user loads `base/*.yml` and a Portrayal schema file we
write and keep. We would be re-writing what `extensions/rack` and
`extensions/cable` already say, and would drift from them.

**B. The schema the user already runs** (the issue's second option). The export
would write against whatever node names and attributes the instance has.
Because Infrahub ships empty, no two instances need agree on a name: the library
itself names the device `DcimDevice`, its rack `LocationRack`, and
`experimental/location_extended` defines a second, different `LocationRack`
whose header says to load one or the other. An exporter for B needs a mapping
file the user writes, and cannot be tested against one known schema.

**C. The library DCIM schema plus the library's own extensions** (a third choice
the sources show). The user loads `base/organization.yml`, `base/location.yml`,
`base/dcim.yml` (and `base/ipam.yml`, since `dcim.yml` names `IpamIPAddress` as
a peer), then `extensions/location_site` (a `LocationSite`, which the rack
needs as its parent), `extensions/rack`, `extensions/cable`,
`extensions/device_module`, `extensions/module_port` (the only file that defines
`DcimModulePort`) and `extensions/patch_panel`. They also load one small
Portrayal overlay (section 3.9) for facts no library node has.

| Portrayal holds | A | B | C |
|---|---|---|---|
| Device types: manufacturer, part number, U, depth, weight | yes (`DcimDeviceType`) | only if their schema has them | yes |
| Device types: ports and bays | no node on a type; ports and bays hang off a *device* | unknown | same as A: only on a placed device, or on a type through the overlay |
| Modules and their bays | no | unknown | yes (`DcimModuleBay`, `DcimModule`, `DcimModuleType`); module ports only on an installed module |
| Front and rear drawings | no field | unknown | no field |
| Racks with U positions | position and face on `DcimPhysicalDevice`; the rack is ours | unknown | yes (`LocationRack`, `height`; device `position`, `rack_face`, `location`) |
| Cables | ours | unknown | yes (`DcimCable`) |
| Patch panels | ours | unknown | yes (`DcimPatchPanel`, front and rear interfaces) |
| What the user loads first | `base/*` plus our file | their own | `base/*`, six extensions, our overlay |
| Risk | drift from the library | exporter not testable | the library is experimental and can change |

## 3. The mapping, for choice C

The left side is what `dcim_export.py` and the rack kit already compute. The
right side is the node and attribute at the commit above. A fact with no field
says where it goes, or that it is left out.

### 3.1 Identity

| Portrayal | Infrahub | Note |
|---|---|---|
| `manufacturer` | `OrganizationManufacturer.name` (unique), and `DcimDeviceType.manufacturer` (required) | Written once per name, before the types. |
| `model` | `DcimDeviceType.name` | See below: the bare model is not unique. |
| `slug` | not carried | `name` is the key (`human_friendly_id: name__value`). |
| `part_number` | `DcimDeviceType.part_number` | Optional, as in the export. |
| `description` (first sentence, fitted) | `DcimDeviceType.description` | Text. |

`DcimDeviceType.name` is `unique: true` across every manufacturer. The NetBox
tree is unique only on manufacturer plus model: the same hardware is listed
again under each NOS vendor with the same model, for example `7726-32X-O-AC-B`
under Arrcus, Edgecore, IP Infusion and SONiC. Writing the bare model would make
the second load collide with the first. The name therefore has to be
`<manufacturer> <model>`, which is the same information as the `slug` and reads
better.

### 3.2 Height, depth and weight

| Portrayal | Infrahub | Note |
|---|---|---|
| `u_height` (`u_height()`, a multiple of 0.5; 0 for a box not in a rack) | `DcimDeviceType.height` (`Number`, required, default 1) | Half units cannot be held: see below. |
| `is_full_depth` | `DcimDeviceType.full_depth` (`Boolean`, required, default true) | One to one. |
| `weight` (kg, two decimals) | `DcimDeviceType.weight` (`Number`, "Weight (kg)", optional) | Whole kilograms only: see below. |
| `weight_unit` | not carried | The field is kilograms, which is what the export writes. |
| `chassis.depth` and the other dimensions | no field | Left out. `full_depth` is the only depth field. |

**Fractions.** The schema library says "Infrahub has no float attribute kind"
(a comment in `extensions/device_module/device_module.yml`, where it chooses
grams over kilograms for that reason, and the cable extension stores length in
centimetres for the same reason). I did not read Infrahub's attribute-kinds
page, so this is the library's statement and not a check against the
product. If it holds:

- A fractional `u_height` cannot be written. The NetBox tree has half-unit
  types, for example the MX104 at 3.5 U. The export has to round, and the
  choice matters: rounding up keeps a rack from being over-filled on paper.
  It is an open question (question 3).
- A fractional `weight` is common: a grep of the NetBox tree for a non-integer
  `weight` or `u_height` matches several hundred device-type files. Rounded to
  whole kilograms, a light device reads as 0 kg, which the module schema's own
  comment says "reads as data rather than as a missing value". The overlay adds
  `weight_grams` (section 3.9), following `GenericModuleType.weight_grams`.

### 3.3 Placement

A placed device is `DcimDevice`, which inherits `DcimPhysicalDevice`.

| Portrayal (rack file, `export-data.js`) | Infrahub | Note |
|---|---|---|
| device name | `DcimDevice.name` (unique) | Unique across the whole instance, not per rack. |
| the device's type | `device_type` (relationship to `DcimDeviceType`, optional) | Written by name. |
| lowest U, bottom-up | `position` (`Number`, "Lowest unit") | The Nautobot rows floor a half-unit position; the NetBox rows write it as is. `Number` cannot hold a half, so this floors too. |
| `face` | `rack_face` (`front` or `rear`, required, default `front`) | One to one. |
| the rack | `location`: a relationship to `LocationHosting`, written as `kind: LocationRack` plus the rack's name and site | There is no `rack` field. The rack *is* the location. |
| zero-U, DIN rail, wall boxes | `position` left empty | As in the NetBox rows (`position: ''`). |
| status | `status` (`active`, `reserved`, `provisioning`, `maintenance`, `deprecated`) | The kit writes NetBox `planned`; the nearest here is `reserved`. Open question 6. |

The library's own example (`objects/extensions/rack/rack.yml`) shows the shape: a
nested `location: {kind: LocationRack, data: {name, site}}` that repeats the
rack's mandatory fields so the upsert matches the rack made above it.

### 3.4 Racks

`LocationRack` has: `name` (not unique alone; unique with `site`), `facility`,
`status` (`active`, `available`, `reserved`, `planned`, `decommissioning`,
`deprecated`), `height` (U, default 42), `serial_number`, `asset_tag`, `tags`,
and a required parent `site` (`LocationSite`).

| Portrayal `frame` | Infrahub | Note |
|---|---|---|
| rack name | `name` | |
| `heightRU` | `height` | |
| site (the kit's NetBox rows already take a site name) | `site` | A `LocationSite` must exist; the export writes one if the user names it. |
| `numbering: top-down` | no field | Left out. Positions are written bottom-up, which is what `position` ("Lowest unit") says. A top-down rack's labels are then wrong in the DCIM; list it in the README. |
| `kind` (two-post, four-post), `holes`, `railDepth`, `usableDepth` | no field | Left out. |
| rack type (#935, not built) | no node | Left out. |

### 3.5 Interfaces and their type vocabulary

An interface is `InterfacePhysical` (inherits `DcimInterface`, layers 2 and 3,
`DcimEndpoint`). Its `device` is a required parent, so an interface exists
only on a device, never on a device type.

| Portrayal (`build`, `iface_type`) | Infrahub | Note |
|---|---|---|
| `name` | `name` | Unique with the device (`uniqueness_constraints: [device, name__value]`). |
| `type` (`IFACE_TYPE` slug) | **no attribute** | `DcimInterface` has no type. See below. |
| `mgmt_only: true` | `role: management` | The role dropdown has `management`. |
| `label` (for `other`) | `description` | Text. |
| breakout note | `description` | |
| the interface's state | `status` (default `active`) | Not carried; open question 6. |

**The type vocabulary is the largest gap.** The library's interface has
`name`, `description`, `status`, `role` and `mtu`, and no speed or medium. The
nearest thing in the library is `DcimModulePort.port_type`, which is `Text`,
and its comment says why: NetBox uses "well over a hundred type slugs", and a
`Dropdown` "would fail the load on every slug not enumerated". It holds the
NetBox slug as it is.

So the overlay adds a `port_type` `Text` attribute to `InterfacePhysical` and the
export writes the same slug it writes for NetBox (`25gbase-x-sfp28`,
`1000base-t`, `other`). No new vocabulary is invented. The cost is that Infrahub does not validate the
value.

Other ports on a device type:

| Portrayal | Infrahub | Note |
|---|---|---|
| `console-ports` | no node | Left out of the nodes; named in the type's description. |
| `power-ports`, `power-outlets` | no node on a device. `DcimModulePort` has `category: power` with `maximum_draw` but belongs to a module. | Left out for a device; for a PSU module, `DcimModulePort`. |
| `front-ports`, `rear-ports` | `DcimFrontPatchPanelInterface`, `DcimRearPatchPanelInterface`, only on a `DcimPatchPanel` | `connector_type` is a dropdown (`lc`, `mpo`, `sc`, `st` and so on, plus `splice`). It does not carry a copper jack. |
| port types the DCIM calls `other` | `port_type: other` | |

### 3.6 Module bays and modules

The extension `device_module` gives:

- `DcimModuleBay`: `name`, `position` (Text, so `F3` and `PSU-2` are fine),
  `bay_label`, `description`, `role` (`supervisor`, `line_card`, `power_supply`,
  `fan`), a required `device` (a `DcimPhysicalDevice`), and `installed_module`.
- `DcimModuleType`: `name` (unique), `part_number`, `weight_grams`, `description`,
  and a required `manufacturer`.
- `DcimModule`: `module_type`, `module_bay`, `serial_number`, `status`. A module
  exists only once it is installed in a bay.

| Portrayal | Infrahub | Note |
|---|---|---|
| `module-bays[].name`, `.position` | `DcimModuleBay.name`, `.position` | A bay is on a *device*, not a type. It is written per placed device. |
| bay accepts list (in `description`) | `DcimModuleBay.description` | There is no accepted-types relationship; stays prose. |
| what the bay is for (supervisor, line card, power supply, fan) | `role` | Left empty unless the first slice finds the contract states it. |
| module-type `model`, `manufacturer`, `part_number` | `DcimModuleType.name`, `.manufacturer`, `.part_number` | `name` is unique: same fix as 3.1. |
| module weight | `weight_grams` | Grams: matches the library. |
| module ports (`{module}/Inlet` and others) | `DcimModulePort`, on an installed module | The library keeps the NetBox `{module}` token verbatim and leaves resolving it to a generator. The export would not resolve it either. |
| nested bays, pass-through bays | no field | Left out: `DcimModuleBay.device` is a `DcimPhysicalDevice`, not a module. |
| the module placed in a bay (rack file) | `DcimModule` with `module_bay` | Its `computed_name` is computed from the bay and type. |

### 3.7 Cables

`DcimCable` inherits `DcimConnector`, whose `connected_endpoints` is a list of
`DcimEndpoint`. A physical interface and a patch-panel interface are endpoints.

| Portrayal (`cableImportRows`) | Infrahub | Note |
|---|---|---|
| side A, side B | `connected_endpoints` (two entries) | There is no side A and side B: order is the only trace. |
| port names on an end (`side_a_name`, comma-joined) | one entry per port | A multi-port end is several endpoints, and the pairing is then lost. |
| end type (interface, front port, rear port, console) | the endpoint's node kind | The library has no node for a console or power port, so a cable on one is left out. |
| `type` (`CABLE_TYPE`) | `cable_type` | `smf-os2`, `mmf-om3`, `mmf-om4`, `mmf-om5`, `cat6`, `cat6a`, `dac-passive`, `aoc` become `smf_os2`, `mmf_om3`, `mmf_om4`, `mmf_om5`, `cat6`, `cat6a`, `dac_passive`, `aoc`. All eight exist in the dropdown. |
| `status` (`planned`) | `status` (`connected`, `planned`) | One to one. |
| `label` | `label` (unique) | Two cables with one label collide, so the export must check labels are unique. |
| `color` (six hex digits) | `color` (a dropdown of 26 named colours) | The dropdown's values are names (`red`, `dark_green`); each choice carries a hex in its own `color` field. The name is written only when the cable's hex equals a choice's hex; otherwise it is left out. |
| `length`, `length_unit` (m or ft) | `length` ("Length (in cm)", `Number`) | Converted to centimetres and rounded up, as `importLength` already rounds up. |
| `description`, bundle name | no field | Left out. The cable schedule still lists bundles. |

How an object file names an interface as an endpoint was not read; the
library's example shows only a nested `kind` and `data` block. The first build
slice tests it against an instance (section 5).

### 3.8 Drawings, and what has no field at all

| Portrayal | Infrahub | Where it goes |
|---|---|---|
| `front_image`, `rear_image` | no field | Left out; the SVG stays in `library/exports`. The overlay could hold a URL (question 5). |
| `comments` (datasheet, maturity, power, ASIC, CPU, accepted modules) | no field | The first sentence into `description`; the rest left out unless the overlay adds a `comments` attribute. |
| `airflow` | no field | Left out. |
| ports on a *type* | none | See 3.5: on a placed device only, unless the overlay adds type-level nodes. |
| fibre maps (`fibre-maps` tree) | no node | Left out. |

### 3.9 The Portrayal overlay

One YAML file, loaded after the library files, with no new node:

```yaml
extensions:
  nodes:
    - kind: InterfacePhysical
      attributes:
        - name: port_type
          kind: Text
          optional: true
    - kind: DcimDeviceType
      attributes:
        - name: weight_grams
          kind: Number
          optional: true
```

Both extend a node the library defines, which is the mechanism
`extensions/transceiver` and `extensions/rack` themselves use (their
`extensions: nodes:` block). Whether an `extensions` block may add an attribute
to an existing node was not checked against the schema page; only
relationships were seen in the library files. If it cannot, the fallback is a
node of our own, `PortrayalInterface`. That is question 7.

Type-level ports and bays, and `comments`, are not in this overlay. They would
need new nodes (a port template that hangs off `DcimDeviceType`), and the
library's `Device` has `generate_template: true`, which probably covers the
instance-from-type case; its docs were not read.

## 4. Recommendation (decided 2026-10-18; see section 6)

**Target choice C: the library's DCIM schema with its own `rack`, `cable`,
`device_module`, `module_port`, `patch_panel` and `location_site` extensions, plus the
two-attribute Portrayal overlay.**

Reasons:

1. It takes racks with U positions (`LocationRack`, `position`, `rack_face`),
   cables (`DcimCable`) and the device types' bays and modules with no schema
   work of ours. Choice A would rewrite those files and drift from them.
2. It is one schema, so the export has one set of node names and can be tested.
   Choice B cannot be, and every user's mapping would differ.
3. The vocabulary the export needs has a precedent in the library itself
   (`DcimModulePort.port_type`, a `Text` holding the NetBox slug). The type
   gap is closed with an attribute, not a re-design.
4. It meets #1115's "Done when" (device types, placed devices and interfaces
   load into an Infrahub instance with the chosen schema) with a schema whose
   node names are fixed and checkable. A and B meet it too, with less to test
   against.

Risks: the library says it is experimental, so names can change; and a user
who already runs their own schema must either add these extensions or
wait for choice B as a later mapping option. B is not rejected, only
deferred: it costs a mapping file, and nobody has asked for it.

What C does not give, and the README of the export must say: device-type
ports on the type itself, drawings, console and power ports on a device, a
top-down rack's numbering, half units, bundle names, cable descriptions.

## 5. The first build slice

Files (new; no existing exporter changes):

- `spec/tools/portrayal/infrahub_export.py`: reads the same inputs as
  `dcim_export.py` (`build`, `build_module`, `iface_type`) and writes object
  files; it does not recompute types or port names.
- `library/exports/infrahub/`: `schema/portrayal-overlay.yml`, a `README.md`
  listing the schema files to load in order, and one object file per
  manufacturer for device types and module types (`objects/<manufacturer>.yml`).
  Racks, placed devices and cables are produced by the Rack Builder, as the
  NetBox files are, not committed.
- `kit/rack/infrahub.js`: the rack-side writer for `LocationRack`, `DcimDevice`,
  `DcimModule` and `DcimCable`, beside `dcim-rules.js`.

Tests (ordinary pytest, no Infrahub install):

- Each device type object has `name`, `manufacturer`, `height`, `full_depth`;
  names are unique across the whole tree (this is the collision in 3.1).
- Every `port_type` written is a key in `IFACE_TYPE`'s values, and the NetBox
  and Infrahub trees agree interface for interface.
- A fixture rack: every device has a `location` naming a rack in the file, a
  position inside the rack's `height`, and a face in `front` or `rear`; every
  cable has two endpoints that exist.
- The lossy steps are tested and named in the README: rounding of height and
  weight, cable length to centimetres, color dropped when not a dropdown value.
- Every file validates against the schema library's own attribute and choice
  lists, copied into the tests as a fixture with the commit named, so a
  library change shows up as a failing test.

"Loads into an Infrahub instance" is checked in two stages. In CI, against the
copied library files: every object's kind, attribute names, relationship names
and dropdown values exist. Then once, by hand, against a real instance:
`infrahubctl schema check` and `schema load --wait` for the library and
the overlay, and `infrahubctl object validate` and `object load` for the
files. That second stage is not in CI because it needs an Infrahub server, and
nothing in this note installs one. Whether the first slice should wait for a
person with an instance is question 8.

## 6. Open questions

1. **Which schema?** Decided 2026-10-18: the export targets OpsMill's schema
   library DCIM schema plus its extensions and the two-attribute Portrayal
   overlay (choice C, the recommendation in section 4). A would have written
   our own Rack and Cable and avoided the library's churn; B would have been a
   mapping file, and stays a later option.
2. **Is the overlay acceptable?** Decided 2026-10-18 with question 1: two
   attributes on library nodes. Without them interfaces carry no type and a
   25G port is only a name. Section 3.5 holds.
3. **Rounding a half unit.** Round up (safe for a rack, wrong for the
   catalogue), or leave `height` out for a half-unit type. Changes: 3.2.
4. **Type-level ports and bays.** Add nodes for them in the overlay now, or
   start with placed devices only as #1115 words it. Changes: whether a device
   type loaded alone shows a single port.
5. **Drawings.** Leave out, or a URL attribute pointing at the committed SVG.
   Changes: nothing in the data, but the user's view of a device.
6. **Status values.** The kit writes `planned`; a device has no such value, and
   an interface defaults to `active`. Changes: what a loaded rack looks like
   (everything `reserved` or everything `active`).
7. **Can an `extensions` block add an attribute?** Only relationships were seen.
   The first slice must find out; if not, the overlay becomes a node of our own.
8. **Who tests against a real instance?** Nothing here installs Infrahub. Changes:
   whether "loads into an instance" can be claimed at merge or only after a
   hand check.
9. **Name of a device type.** `<manufacturer> <model>` is proposed; the slug is
   the alternative. Changes: the key every later load upserts on.

## 7. One-way items

- A device type's `name` is its key once users load it, so the choice in
  question 9 cannot be changed without leaving duplicates in their instance.

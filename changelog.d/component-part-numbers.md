### Changed
- **A component can state the order codes it is sold under: `part-numbers`**
  (#70). The map is a device configuration's, `{<model>: {part: <part number>}}`
  without `power-cord`, and each key is one exported module type, named by the
  key, with `part_number` from `part`. One drawing with two order codes is two
  module types with the same ports. A component without the key exports as it
  did, under `attrs.model` or its `name`. The schema refuses a contract with
  both `part-numbers` and `attrs.model`, so the name has one source. The
  `components.json` entry carries the map, sorted like the rest of that file,
  and only where the contract has one. The rack kit opens the module type file
  of the first key in sorted order (`partNumber`, and the new `partNumbers`, in
  `kit/rack/export-data.js`); `moduleTypePath` takes a list of codes. L128 reads
  a component's keys as it reads a device's.
- **BREAKING for DCIM data already imported.** Three Casa module types are
  renamed to the code the C40G and C100G data sheets order them by, and one is
  split in two. In both `netbox/module-types/Casa Systems/` and
  `nautobot/module-types/Casa Systems/`: `BDM2m.yaml` becomes `BDM2M-W.yaml`
  (Open) and `BDM2M-N.yaml` (No Licenses), `6+12 IO2.yaml` becomes
  `BDM6-12-IO2.yaml`, and `SMM 300GM.yaml` becomes `SMM-300-GM.yaml`. Each
  carries `part_number`. A module installed under an old name is not the new
  type in the DCIM, so it has to be re-created or re-pointed there. The ports,
  bays and power ports of each are unchanged. Version bumps: `casa/bdm2m`,
  `casa/io-6p12-io2` and `casa/smm-300gm` 1.7.0, 1.7.1 and 1.7.0 to 1.8.0 each;
  `casa/c100g` 1.0.2 to 1.0.3 and `casa/c40g` 0.5.20 to 0.5.21, which seat them.
  The Casa device types are otherwise unchanged: a bay's `Accepts:` line names
  the component, not its code. Every other component's module type is
  unchanged and moves to `part-numbers` later.
- **BREAKING for DCIM data already imported: the exporter removes the
  module-type files it no longer writes.** `dcim_export.py --modules` removes a
  `.yaml` file under `<target>/module-types/<maker>/` that no component in the
  build writes, and prints `removed <path>` for each. Without it a renamed type
  stayed beside its replacement. A `--device` run removes nothing, and another
  kind of file in those folders, or a file outside `module-types/`, is never
  touched. Removed from both `netbox/` and `nautobot/` `module-types/Casa
  Systems/`: `BDM2m.yaml`, `6+12 IO2.yaml` and `SMM 300GM.yaml`. Added, in both:
  `BDM2M-W.yaml`, `BDM2M-N.yaml`, `BDM6-12-IO2.yaml` and `SMM-300-GM.yaml`.
- **The rack kit's explorer labels the three Casa cards by their component
  name** until its label readers learn `part-numbers`: they read
  `attrs.model`, which these three no longer state.

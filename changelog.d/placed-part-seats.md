### Changed
- A part placed straight on a device face that composes two or more connector parts (a pair of earth studs, a DC
  terminal block's lugs, an AC inlet panel's inlets) now has each of those seats in the device's `cages[]` in
  `<device>.configs.json`, under the key `<placement>/<part>` that `occupants:` and `seat-turns` already use
  (`ground-studs-rear/stud-tr`). Before, only the part's entry in `components.json` listed them, so a reader of the
  device's own list, the Rack Builder's catalogue among them, offered no cable end or lug on those seats. Each entry is
  the part's own slot (`interface`, `kind`, `accepts`, `turns`, `lift`) with its mate point carried into the device's
  frame by the placement. A placement that presents a slot of its own (a duplex adapter, a cage wrapper, a pair of
  studs) is unchanged, and no existing slot changes or goes. The 17 devices that place such a part publish 65 more
  slots between them. No drawing, export file, device version or lock changes. `contract` is not raised: `cages[]`
  gains entries and no key changes, and a slot's `id` is now a placement id or a `<placement>/<part>` key.
- The Explorer lists a seat once when the device's index and the drawing both give it (`faceCages` in `kit/swap.js`),
  keeping the drawing's entry, which names the part the seat belongs to. A page that loads the new device indexes with
  an older kit lists those seats twice.
- The port-usable records file loses the rows of seven parts whose seats are now published
  (`casa/c40g-ground-studs@1`, `casa/c40g-ac-inlet-panel@1`, `arista/7010tx-dc-terminal@1`,
  `juniper/ex3300-dc-terminal@1`, `nokia/sr-1-dc-terminal-block@1`, `common/dc-terminal-24@1` and
  `common/dc-terminal-27@1`), and its `cap:` is 197.

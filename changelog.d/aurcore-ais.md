### Added
- AurCore, a new vendor, with its ten AIS industrial DIN-rail switches (#744,
  #745, #748). They are the first devices to state `chassis.mount: din-rail`
  and `chassis.bevel`: a fanless finned housing, octagonal in section, that
  clips onto a 35 mm rail or screws to a wall. Each has one `base`
  configuration and exports to NetBox and Nautobot with `u_height: 0`.
  - The large housing, 83.8 x 145 x 110: `aurcore/ais4001p` and `ais4001`
    (8 GbE and 4 SFP+), `ais2003p` and `ais2003` (8 GbE and 4 RJ45/SFP combo
    ports, whose copper halves are `copper-9` to `copper-12`), `ais2004p` and
    `ais2004` (8 GbE and 12 SFP).
  - The small housing, 72.1 x 110 x 93: `aurcore/ais2001p` and `ais2001`
    (4 GbE and 2 SFP), `ais2002p` and `ais2002` (8 GbE and 2 SFP). Its console
    jack is on the top face, not the front.
  - A `p` model is the PoE+ build: two lamps to a jack and a 48-57 V feed,
    where the plain model has one lamp and 12-55 V.
  - Fronts are measured from each model's own product photograph. Tops and
    backs are estimates from an angled render, and each manifest says so in
    its gaps.
- The shared parts the AIS switches need, all in `common/` (the vendor has no
  component namespace of its own): `din-clip-ts35@1` (the TS35 rail clip),
  `wall-plate-keyhole-2@1` and `wall-plate-keyhole-2-42@1` (56 and 42 mm
  keyhole plates), `dip-switch-2@1`, `ground-screw-washer@1`, and the two
  pluggable headers, `terminal-header-508-5f` (power) and
  `terminal-header-508-2` (relay). The headers have since taken majors: pin
  `terminal-header-508-5f@2` and `terminal-header-508-2@3`.
- `common/rj45-ganged-link@1`, the ganged RJ45 cell with one lamp, for a jack
  that shows a single LINK/ACT window (#745). It joins the RJ45 family in lint
  and exports as `1000base-t`. Its `lamp-right` skin is for a column turned
  the other way, which keeps the lamp at the top.

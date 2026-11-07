### Added
- **`common/rj45-ganged-eth-plain@1`: a ganged RJ-45 cell for an Ethernet jack
  whose housing has no lamps** (#1041). It is `std/rj45-ganged@2` with the
  Ethernet claim of `common/rj45-ganged-eth@1` (`media: rj45`) and none of its
  lamps, and its skin is the bare cell's own housing outline, so the drawing is
  the bare cell's. L76 accepts an Ethernet jack on it without asking for lamps
  and still sends one on the bare cell to a lamped member; the DCIM export types
  it as an interface (`1000base-t`, the family's default for an Ethernet cell: the
  module datasheets give a cable category, Cat.5, 6 or 6A, which the export does
  not use).
- **The Fibrain HD copper slot parts: the six-way RJ45 holders `fibrain/xmu00@1`
  (XMU00, unscreened) and `fibrain/xms00@1` (XMS00, screened), and twelve RJ45
  connection modules** - `fibrain/xe100@1`, `xe110@1`, `xe200@1` and `xe210@1`
  (Cat.5), `xq100@1`, `xq110@1`, `xq200@1` and `xq210@1` (Cat.6), `xr100@1`,
  `xr110@1`, `xr200@1` and `xr210@1` (Cat.6A). In each part number the first
  digit after the letters is 1 for unscreened and 2 for screened, and the last
  is 1 where the module is sold with a keystone adapter. A holder fills one HD
  slot and its six positions, `pos-1` to `pos-6`, are bays measured on the
  maker's front elevation (six windows on a 16.02 pitch); each takes any of
  the twelve modules, and each module carries one RJ45 jack,
  `common/rj45-ganged-eth-plain@1`, so a cable lands on it as a copper port at
  `slot-N/module/pos-M/module/jack` and the DCIM export lists it as an
  interface and not a console port. The two holders differ in the screening
  springs the screened one draws. XR300 and XR310 are cable-end plugs and are
  not modules. `fibrain/xpu` takes both holders in each of its eight slots
  (0.1.1 to 0.2.0) and gains three example builds that fill all eight slots
  with a six-way holder and six modules each, 48 RJ45 ports in the one unit
  (DSH XPU00: "48 ports per 1U for copper"): `copper-mixed` (screened XMS00
  and unscreened XMU00 alternating, each with modules of its own screening;
  Cat.5, Cat.6 and Cat.6A, with keystone-adapter modules in every holder),
  `xpu00-copper` (eight XMU00) and `xps00-copper` (eight XMS00, with
  grounding). Illustrative: holders and modules are ordered separately, so the
  orderable `xpu00` and `xps00` stay empty, as their datasheets give them.
  The XCU10's drawer is unchanged, because the maker lists no copper for it.

### Changed
- **The Fibrain HD RJ45 modules draw a face of their own, and the frame's top
  reads in 3D** (art, patch bumps: the twelve modules 1.0.0 to 1.0.1,
  `fibrain/xpu-top-sheet` 1.0.0 to 1.0.1, `fibrain/xpu` 0.2.0 to 0.2.1). A
  screened module draws a shield rim round its frame, a keystone module a clear
  collar, a clear latch over the shell and a clear tab under the frame, so the
  four kinds of one category differ in shape and not only in colour; the widths
  of the rim, the collar and the latch are stand-ins, said so in each part's
  sources, because no sheet dimensions them. The dark shell strips of an
  unscreened module carry a thin outline in the kit's dim grey, so they read
  against the black holder on a light stage and a dark one. The top sheet draws
  its eight slots rimmed and its five screw heads raised 0.7 (the head height is
  the one estimated figure). The copper-mixed 3D preview that came out blank was
  not a renderer fault: the scene appears once its face textures are
  rasterised, six to eight seconds on a software renderer, and the shot had been
  taken at six. A test pins that every copper configuration compiles to six
  painted faces and 48 jacks.

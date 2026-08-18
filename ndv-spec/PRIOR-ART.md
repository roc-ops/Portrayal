# Prior-Art Research: Declarative, Component-Addressable SVG Device Visualization

Research date: 2026-08-14. Six parallel research threads: DCIM ecosystem, adjacent
component-library domains, hardware-model standards, SVG→3D pathways, SVG authoring
tooling, and diagramming-tool export targets. All claims below were verified against
primary sources (repos, specs, vendor docs) at research time; sources listed at the end
of each section.

## Verdict

**No existing open-source project combines a declarative, Git-versionable component
inventory of network/IT hardware with vendor-agnostic SVG renderings in which each
component is individually identified and addressable.** The niche is genuinely open,
the demand is documented, and the idea has been proven repeatedly — but only in
proprietary, per-vendor silos.

Evidence the gap is real and wanted:

- The netbox-community/devicetype-library maintainers were explicitly asked for
  port-to-image mapping (discussion #1759, Nov 2023) and declined it as out of scope.
- No standard anywhere — ENTITY-MIB, ietf-hardware (RFC 8348), OpenConfig platform,
  Redfish, DMTF CIM — expresses x/y position of a component on a faceplate. The
  closest is Redfish `PartLocation` ("Bay 3, Front, LeftToRight"), which is
  topological, not geometric.
- The "chassis view" (device image + addressable components + live status binding)
  has been reinvented proprietarily at least five times: CiscoView device packages
  (1990s), Cisco EPN Manager, Meraki Switch Port View, Juniper Mist front panels,
  Arista CloudVision. Always per-SKU, hand-maintained, closed formats.
- The only component-addressable vector stencils on the market are NetZoom's
  commercial "smart" Visio shapes (connection points at data/power ports) —
  proprietary format, subscription library.
- A W3C "SVG Connectors" proposal (Doug Schepers, ~2011) that would have standardized
  ports/attachment points in SVG died without adoption. Every domain since has rolled
  its own convention.

## 1. Closest prior art (DCIM/network space)

| Project | What it is | Gap vs. goal |
|---|---|---|
| [devicetype-library](https://github.com/netbox-community/devicetype-library) (CC0, very active) | Community YAML device definitions: interfaces, power ports, module bays, etc. Optional flat front/rear *raster* images; max two per device | No positional/visual component data; port-to-image mapping declined upstream. Natural **export target** for us |
| [netbox-device-view](https://github.com/peterbaumert/netbox-device-view) (MIT, active, small) | NetBox plugin; per-DeviceType YAML layout → schematic SVG panel; ports colored by live connection state | Grid cells not physical geometry; ports only (no PSU/fan/LED/ground); layouts in NetBox DB, not a portable library; NetBox-coupled. Proves concept + demand |
| NetBox core | Rack elevations as SVG via REST since v2.7 | Device = 1U-multiple box with optional flat image; no component model on faces |
| [RacksDB](https://github.com/rackslab/RacksDB) (MIT, active) | YAML-in-Git infrastructure DB with SVG/PNG rendering incl. axonometric | Equipment-in-rack granularity only; philosophically aligned |
| [Rackula](https://github.com/RackulaLives/Rackula) (MIT, very active, ~1.7k stars) | Homelab rack designer consuming devicetype-library **raster** images | Devices are pictures; ports not addressable. Shows third-party appetite for visuals on that data backbone |
| [WireViz](https://github.com/wireviz/WireViz) (GPL-3, active, 5.2k stars) | YAML → cable/harness SVG with every pin identified + auto-BOM | Adjacent domain; Graphviz-rendered so weak output-side SVG addressability. Strongest *pattern* validation |
| rackdiag / Rack-Visualization / ESnet react-network-diagrams / switch-config-render | Various rack/panel SVG generators | All schematic, niche, and dead or dormant |

Confirmed absent: any community library of structured (ID-bearing) SVG faceplates for
network hardware; any open schema for port positions on a device face; any vendor
publishing openly licensed component-structured vector faceplates.

## 2. Architectural templates from adjacent domains

Two proven linking architectures exist:

**(a) Manifest references SVG IDs** — the Fritzing model. A Fritzing part is an XML
manifest (`.fzp`) + per-view SVGs; each named connector declares `svgId` (the
clickable graphic) and `terminalId` (exact attachment point) per view, and `<buses>`
model internal connectivity. Shipped with a lint tool (FritzingCheckPart) that
cross-checks manifest↔SVG ID consistency — mandatory glue for this architecture.
Fritzing is alive (1.0.7/1.0.8 released 2026). Weaknesses: XML, connector-centric,
opaque ID conventions.

**(b) Annotations inside the SVG** — the VCV Rack model. Panel SVG in mm units with a
hidden `components` layer; **fill color encodes component type**, Inkscape label is
the component name, and `helper.py` code-generates from the SVG. Hundreds of
third-party module developers follow this convention — proof a plain-SVG convention
scales community-wide when tooling enforces it. Same family: MAX IV's synchrotron
synoptic tool (binds control-system devices via `model=...` in SVG `<desc>`),
Gingerbread/svg2mod (layer-name semantics).

**The live-data callout problem is already solved downstream**: the
[Grafana Flow panel](https://github.com/andymchugh/andrewbmchugh-flow-panel)
(Apache-2.0, active) binds a YAML panelConfig to SVG element IDs (thresholds, labels,
links) — it could likely consume our SVGs as-is given stable IDs. Also: ACE.SVG panel
(ID→name mapping layer), FUXA (MIT web SCADA with SVG widget library),
InteractiveHtmlBom (bidirectional BOM-row↔graphic highlight).

KiCad offers the counter-model worth knowing: geometry and typed pins live in one
plain-text s-expression document (no ID-sync problem at all), with SVG as export only.
Boardview formats similarly use coordinate-indexed hit-testing instead of SVG IDs.

## 3. Semantic backbone: the standards map

- **ENTITY-MIB (RFC 6933/4133)** is the right taxonomy anchor — the most widely
  implemented hardware-inventory standard in networking. `entPhysicalClass`
  (chassis, backplane, container, powerSupply, fan, sensor, module, port, stack,
  cpu; IANA later added battery, storage-drive), containment tree, and
  `entPhysicalParentRelPos` which SHOULD match the silk-screened label ("slot #3" →
  3). `entPhysicalVendorType` (vendor OID) is a precise lookup key into a visual
  library. `entAliasMappingTable` standardizes physical-port→ifIndex — the join
  needed to color ports by interface state.
- **ENTITY-SENSOR-MIB (RFC 3433)**: sensors locate themselves purely by containment.
  A diagram keyed to the entity tree inherits sensor placement automatically.
- **ietf-hardware (RFC 8348) + iana-hardware**: 1:1 YANG port of ENTITY-MIB (the RFC
  includes the mapping table) with derivable class identities — a ready-made
  extensibility mechanism. Real-world NOS support is thin.
- **OpenConfig platform**: what gNMI streaming actually delivers (Arista full tree,
  Juniper, SONiC via mgmt-framework; IOS XR). Richer where faceplates care:
  TRANSCEIVER and FAN_TRAY first-class, per-lane optics power under
  `physical-channels`. No parent-rel-pos; position implied by naming.
- **Redfish**: `PartLocation` (LocationType Slot/Bay/Connector/Socket + ordinal +
  Reference Front/Rear/… + Orientation LeftToRight/… + silk-screen ServiceLabel) is
  the best semantic stepping-stone between pure containment and pixel geometry —
  worth adopting as a mapping layer. `PhysicalContext` (51 values) for sensor zones.

Design implication: key the format to the IANA class set, carry standard identity on
each SVG element (class, name, parent path, rel-pos, optional vendor-type OID /
OpenConfig type / Redfish ServiceLabel), and any live entity tree from SNMP, NETCONF,
gNMI, or Redfish joins onto the drawing by name or (class, parent-path, rel-pos).
Components also need queryable attributes (port speed, media) so "select all 10G
interfaces" is a class query, not a hand-picked list.

## 4. Key technical constraints (SVG authoring)

- **The `<use>` shadow boundary is decisive**: sub-elements inside a `<use>` clone are
  not individually addressable by JS/CSS (only CSS custom properties pierce it), and
  external references are same-origin-only with no CORS story. Therefore: author
  components as a library, but **compile devices to flat SVG with stable hierarchical
  IDs** (build-time inlining), rather than runtime SVG-references-SVG.
- **Parameterized SVG has no standard** (W3C SVG Parameters dead; parametric-svg
  dead 2016). Parameterization lives in our source layer — as in WireViz/schemdraw.
- **Metadata belongs in the SVG**: `data-*` attributes are official SVG 2, universally
  supported, DOM-accessible (`data-class="port" data-speed="10g"`). Pattern to copy:
  Excalidraw and draw.io embed their full source document in exported SVG
  (`<metadata>`) for lossless round-trip. `<title>/<desc>` + ARIA graphics roles for
  humans/a11y.
- **Git hygiene requires a curated normalizer**: default SVGO *and* Inkscape "plain
  SVG" both strip the things we depend on (IDs, `data-*`, metadata,
  `inkscape:label`). A whitelisting svgo/scour config in pre-commit is mandatory.
  No mature semantic SVG diff tool exists; render-and-pixel-diff in CI (resvg +
  pixelmatch) is the practical pattern.
- **Healthy tooling shortlist**: svg.py (typed Python generation), schemdraw (anchor
  -point component API to imitate), svg-sprite, SVGO, resvg, D2 (DSL design
  reference), Annotorious (W3C annotation data model). Dead/avoid: svgwrite,
  leader-line, blockdiag, parametric-svg; pinout and drawthe.net are dormant but
  good design references.

## 5. 3D pathway

- **Identity survives SVG→3D** (verified in three.js source): `SVGLoader` attaches
  the original SVG DOM node to each parsed path (`path.userData.node`), so IDs,
  classes, and `data-*` flow through `ExtrudeGeometry` into meshes. The SVG stays
  the single source of truth; 3D is generated at runtime. Blender's SVG importer
  also preserves `id`→object-name for an offline glTF bake (names + `extras`
  metadata survive; loads in `<model-viewer>` for zero-code embeds + AR).
- **X3D — honest assessment**: live ISO standard (v4, 2023) with a philosophically
  perfect DOM model, but X3DOM has had no release since Aug 2023, X_ITE is excellent
  yet one-maintainer, no native browser support ever, and X3D can't reference SVG
  geometry (paths must be converted to Extrusion crossSections anyway). Treat X3D as
  an optional standards-checkbox **export**, not the pipeline.
- glTF is a build artifact (binary-ish; poor diffs) — never source. CSS 3D
  (six live-SVG faces, full DOM interactivity, zero deps) is an unexplored cheap
  "flip to rear / orbit-lite" mode — nobody in DCIM does it. Parametric CAD
  single-source (OpenSCAD/CadQuery/JSCAD) would demote SVG to output; rejected.
- **No project generates both semantic 2D SVG and 3D from one declarative device
  definition.** Confirmed white space. Commercial DCIM (Sunbird, netTerrain,
  Hyperview) treats 3D walkthroughs as a premium feature; open source has nothing.

## 6. Export targets (feasibility, verified)

| Target | Effort | Mechanism |
|---|---|---|
| **draw.io** | Low — best first target | mxlibrary JSON; cell with `shape=image;image=data:image/svg+xml;base64,...` + `points=[[0,0,0,x,y],...]` style gives pixel-exact snap points on our SVG art (syntax confirmed by draw.io team, issue #2199 / groups thread). ~100-line generator; no existing tool does it |
| **Inkscape symbol library** | Near zero | One SVG per vendor, each device a `<symbol>`; drop-in directory |
| **Visio .vssx** | Medium | OPC zip of documented XML; master = `ForeignData` image + `Connection` section rows (X/Y/DirX/DirY per port) + Shape Data. No Visio needed (proven by hoveytechllc/visio-stencil-creator); no OSS library writes connection points today — a gap we'd fill. Full SVG→Visio-geometry conversion: defer |
| **OmniGraffle** | Low-medium | m-radzikowski/omnigraffle-stencil already builds .gstencil from SVG with magnets |
| **Lucidchart** | Piggyback | Imports VSSX; custom connection points unsupported — test degradation |
| **PowerPoint** | Medium | PPTX embeds SVG natively, but recent builds flatten "Convert to Shape" — for reliable per-port highlight/animation, generate native DrawingML shapes from our metadata (python-pptx) instead |
| **NetBox devicetype-library YAML** | Low | Straight projection of our superset |
| **Excalidraw** | Skip/low value | No connection-point concept |

## 7. What to borrow (synthesis)

- **Fritzing**: manifest↔SVG-ID contract (`svgId`/`terminalId`), zip packaging,
  and above all the **ID-consistency linter**.
- **VCV Rack**: proof that in-SVG conventions (layers/labels/real units) + a codegen
  helper get community adoption; mm-based real-unit panels.
- **ENTITY-MIB/iana-hardware**: the component class taxonomy and containment/rel-pos
  semantics; Redfish PartLocation as the intermediate location vocabulary.
- **KiCad**: canonical plain-text formatting rules for Git; typed-pin vocabulary;
  the CC-BY-SA-with-use-exception library license model (also Fritzing parts
  CC-BY-SA; our art library should consider the same).
- **Grafana Flow panel**: external YAML binding keyed on SVG IDs — our first
  zero-effort integration story.
- **schemdraw/pinout**: Python component-with-anchors API design; leader-line
  callouts as first-class components.
- **Excalidraw/draw.io**: embed the source definition in the emitted SVG for
  round-trip.

## Suggested next step

Brainstorm and pin down the source-format architecture — the one decision everything
else hangs on. The research narrows it to a spectrum between:
(a) Fritzing-style: YAML manifest + hand-drawn per-component SVGs linked by ID, with
a linter; (b) VCV-style: annotated SVG *is* the source, tooling extracts the model;
(c) KiCad-style: single declarative document, SVG fully generated. The EN9000
workflow to date is closest to (b); the `<use>` constraint pushes final artifacts
toward compiled flat SVG regardless of which source model wins.

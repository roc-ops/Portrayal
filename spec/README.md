# spec

Schemas and tooling for **Portrayal** — declarative, Git-versioned hardware device
definitions compiled into SVG where every component is individually addressable
(ports, PSUs, fans, LEDs, regions), for monitoring callouts, documentation,
DCIM, and diagram-tool exports. Domain-neutral core; networking is profile #1.

- `DESIGN.md` — the architecture and the ten resolved design decisions
- `PRIOR-ART.md` — the research this project rests on (and the gap it fills)
- `DEPTH-AND-3D.md` — how depth, relief and module bodies turn the 2D drawing into 3D
- `schemas/` — JSON Schemas for component contracts, device manifests, NOS overlays
- `tools/portrayal/render.py` — compiles manifest + component skins → flat, addressable SVG
- `tools/portrayal/lint.py` — schema validation + contract↔skin consistency + ID grammar
- `tools/portrayal/visio_extract.py` — pull shape artwork out of Visio stencils for intake
  reference (see `VISIO-INTAKE.md`)
- `tests/` — walking-skeleton tests (lint green, deterministic render, addressability)

Quick start (paths are relative to this directory):

```sh
python3 tools/portrayal/lint.py --schemas schemas --library ../library
python3 tools/portrayal/render.py ../library/devices/edgecore/as7726-32x/device.yaml \
    --library ../library --out ../library/dist
(cd ../library && python3 -m http.server 8931)  # browse http://localhost:8931/dist/
```

Licensed Apache-2.0. See `../LICENSE`.

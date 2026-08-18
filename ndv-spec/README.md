# ndv-spec (working name)

Schemas and tooling for **NDV** — declarative, Git-versioned hardware device
definitions compiled into SVG where every component is individually addressable
(ports, PSUs, fans, LEDs, regions), for monitoring callouts, documentation,
DCIM, and diagram-tool exports. Domain-neutral core; networking is profile #1.

- `DESIGN.md` — the architecture and the ten resolved design decisions
- `PRIOR-ART.md` — the research this project rests on (and the gap it fills)
- `DEPTH-AND-3D.md` — how depth, relief and module bodies turn the 2D drawing into 3D
- `schemas/` — JSON Schemas for component contracts, device manifests, NOS overlays
- `tools/ndv/render.py` — compiles manifest + component skins → flat, addressable SVG
- `tools/ndv/lint.py` — schema validation + contract↔skin consistency + ID grammar
- `tools/ndv/visio_extract.py` — pull shape artwork out of Visio stencils for intake
  reference (see `VISIO-INTAKE.md`)
- `tests/` — walking-skeleton tests (lint green, deterministic render, addressability)

Quick start (with the `ndv-library` repo checked out as a sibling):

```sh
python3 tools/ndv/lint.py --schemas schemas --library ../ndv-library
python3 tools/ndv/render.py ../ndv-library/devices/edgecore/as7726-32x/device.yaml \
    --library ../ndv-library --out ../ndv-library/dist
(cd ../ndv-library && python3 -m http.server 8931)  # open http://localhost:8931/demo/
```

License: Apache-2.0 (LICENSE file with full text pending initial publication).

# spec

Schemas and tooling for **Portrayal** — declarative, Git-versioned hardware device
definitions compiled into SVG where every component is individually addressable
(ports, PSUs, fans, LEDs, regions), for monitoring callouts, documentation,
DCIM, and diagram-tool exports. Domain-neutral core; networking is profile #1.

- `DESIGN.md` — the architecture and the ten resolved design decisions
- `../PRIOR-ART.md` — the research this project rests on (and the gap it fills)
- `DEPTH-AND-3D.md` — how depth, relief and module bodies turn the 2D drawing into 3D
- `schemas/` — JSON Schemas for component contracts, device manifests, NOS overlays
- `tools/portrayal/render.py` — compiles manifest + component skins → flat, addressable SVG
- `tools/portrayal/lint.py` — schema validation + contract↔skin consistency + ID grammar;
  `--list-rules` prints every rule code, and [docs/lint-rules.md](../docs/lint-rules.md) is that table as a page
- `tools/portrayal/visio_extract.py` — pull shape artwork out of Visio stencils for intake
  reference (see `VISIO-INTAKE.md`)
- `tests/` — the suite: library-wide invariants every device must satisfy, plus unit
  tests of the tools. Build `dist/` first; several modules skip without it

Quick start (paths are relative to this directory):

```sh
python3 tools/portrayal/lint.py --schemas schemas --library ../library
#   last line: `LINT: ok (<files> files, <warnings> warnings in <rules> rules)` -
#   warnings are census rules and pass; add --strict to exit 2 on any, --device NAME for one device
python3 tools/portrayal/render.py ../library/devices/edgecore/as7726-32x/device.yaml \
    --library ../library --out ../library/dist
(cd .. && python3 tools/serve.py 8931)  # browse http://localhost:8931/library/dist/
```

Licensed Apache-2.0. See `../LICENSE`.

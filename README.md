# Portrayal

Declarative, Git-versioned hardware device definitions, compiled into SVG where
every physical thing is individually addressable — ports, PSUs, fans, LEDs, bays,
regions.

A device is a YAML manifest that places reusable component contracts. The compiler
resolves it into one flat SVG in real millimetres, where every element carries a
stable DOM id and a data-path. That drawing can then be driven: colour a port from
telemetry, highlight a failed PSU, link a region to a ticket, export the whole thing
to a DCIM or a diagram tool.

The core is domain-neutral. Networking is the first profile, not the only one.

```
spec/          schemas, compiler, linter, tests
library/       component contracts + skins, device manifests, NOS overlays
docs/          how the model works
```

## Try it

```sh
./build.sh                                    # lint, then compile every device
python3 tools/serve.py 8931                   # open http://localhost:8931/library/demo/
```

To compile one device:

```sh
python3 spec/tools/portrayal/render.py library/devices/edgecore/as7726-32x/device.yaml \
    --library library --out library/dist
```

The build and lint gates need only the Python standard library plus what
`build.sh` already assumes. **Preparing a new vendor line** additionally needs
[docling](https://github.com/docling-project/docling) to convert vendor PDFs
into the figure-and-caption sets modelling works from:

```sh
pip install -r spec/tools/intake/requirements.txt   # docling + pillow; GPU optional
python3 spec/tools/intake/extract.py <guide.pdf> --out working/images
```

The full intake process — what to hunt, where vendors keep it, staging rules,
and the conversion discipline that keeps docling from eating a machine — is
`.claude/skills/portrayal-vendor-intake/SKILL.md`. The modelling process that
follows it is `.claude/skills/portrayal-model-device/SKILL.md`.

## What makes it different

**Provenance is a first-class field, not a comment.** Every dimension records where
it came from and how confident that is — `datasheet`, `drawing`, `measured`,
`photo-measured`, `estimated`. A device declares a `maturity` level and the linter
holds it to that standard: `verified` forbids an estimated value anywhere in the
assembly, including inside the components it places. So "is this model trustworthy"
is a question the tooling answers rather than a question you ask the author.

**A faceplate is modelled the way it is made** — punched, then printed, then
populated. Chassis silkscreen paints *under* the components that cover it, because
that is what happens to the real panel. `--without silkscreen` gives you the bare
panel-and-components drawing to hand to whoever does the artwork.

**Physical ids follow the silkscreen.** What the NOS calls an interface is an
overlay, because two operating systems on the same hardware disagree and the
hardware does not care.

**No vendor material is redistributed.** Facts are transcribed and cited; the
source documents stay out of the repository. See `PRIOR-ART.md`.

## Documentation

- `spec/DESIGN.md` — the architecture and the design decisions behind it
- `spec/DEPTH-AND-3D.md` — how depth and relief turn the 2D drawing into 3D
- `docs/layers-and-conformance.md` — the canonical manifest, the layer model and the maturity gate
- `.claude/skills/portrayal-model-device/SKILL.md` — how to model a device from reference material, stage by stage with a check at each. Written for an agent; works for a person
- `PRIOR-ART.md` — the research this rests on, and the gap it fills

## Status

Early. The schemas are at `v0` and will change. Eleven devices are modelled across
seven vendors, at varying maturity.

## Licence

Apache-2.0. See `LICENSE`.

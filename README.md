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
kit/           portrayal-kit: the JS consumer — draw, inspect, export
docs/          how the model works
```

The split is a line about who reads what. `spec/` and `library/` are the source
of truth and the compiler; they read YAML. `kit/` reads only what `build.sh`
publishes into `library/dist/`, which is a documented contract — so a consumer
needs the artifacts, not a checkout of this repository.

## Try it

```sh
./build.sh                                    # lint, then compile every device
./publish.sh                                  # the same, plus the DCIM exports
python3 tools/serve.py 8931                   # browse http://localhost:8931/library/dist/
```

To compile one device:

```sh
python3 spec/tools/portrayal/render.py library/devices/edgecore/as7726-32x/device.yaml \
    --library library --out library/dist
```

The build and lint gates need Python 3.12 with `pyyaml` and `jsonschema`, plus
what `build.sh` already assumes (a POSIX shell, `xargs -P`). **Preparing a new vendor line** additionally needs
[docling](https://github.com/docling-project/docling) to convert vendor PDFs
into the figure-and-caption sets modelling works from:

```sh
pip install -r spec/tools/intake/requirements.txt   # docling + pillow; GPU optional
python3 spec/tools/intake/extract.py <guide.pdf> --out working/images
```

The full intake process — what to hunt, where vendors keep it, staging rules,
and the conversion discipline that keeps docling from eating a machine — is
`.claude/skills/portrayal-vendor-intake/SKILL.md`. The modelling process that
follows it is `docs/modelling-a-device.md`.

## What makes it different

**Provenance is a first-class field, not a comment.** Every dimension records where
it came from and how confident that is — `datasheet`, `drawing`, `measured`,
`photo-measured`, `registry`, `borrowed`, `estimated`, and `known-wrong` for a value
carried only because nothing sourced can yet replace it. A device declares a `maturity` level and the linter
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

- `CONTRIBUTING.md` — how to add a device in an afternoon, and what a reviewer asks for
- `spec/DESIGN.md` — the architecture and the design decisions behind it
- `spec/DEPTH-AND-3D.md` — how depth and relief turn the 2D drawing into 3D
- `docs/layers-and-conformance.md` — the canonical manifest, the layer model and the maturity gate
- `docs/modelling-a-device.md` — how to model a device from reference material, stage by stage with a check at each; `docs/modelling-pitfalls.md` for when a figure or a rule misbehaves
- `library/components/CATALOGUE.md` — every component on one page: size, what it conforms to,
  how many devices use it. Generated, and a test fails when it and the library disagree
- `PRIOR-ART.md` — the research this rests on, and the gap it fills

## Status

Early. The schemas are at `v0` and will change. The library covers white-box
switches and routers, Cisco ASR 9000, Juniper MX, Casa CCAP and Dell server
hardware at varying maturity; `library/dist/devices.json` is the current list.

## Licence

Apache-2.0, for everything in the repository: the compiler and tools, the
schemas, the device manifests, the component contracts and the skins. See
`LICENSE` and `NOTICE`.

One licence rather than a code/data split is deliberate. The library data
was CC-BY-SA 4.0 with an outputs exception until publication; it was unified
so that a rendered SVG never raises the question of whether it is a derivative
of the data it was compiled from. Under a single permissive licence it cannot
matter.

Contributions are accepted under the
[Developer Certificate of Origin](https://developercertificate.org/): by signing
off a commit (`git commit -s`) you certify that you wrote the change or have
the right to submit it under this licence. There is no CLA.

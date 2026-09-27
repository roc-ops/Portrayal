# library

Content library for Portrayal: component contracts + skins, device manifests, NOS
overlays, and sanitized device dumps. Compiled SVGs are build artifacts
(`dist/`, gitignored) — render with `spec`.

```
components/{std,common,<vendor>}/<name>/v<major>/{contract.yaml, skins/*.svg}
devices/<vendor>/<model>/{device.yaml, overlays/<nos>.yaml, dumps/}
```

Reference device: **Edgecore AS7726-32X** (32× QSFP28 Trident 3 white-box switch),
built from its datasheet facts (per-field provenance; no datasheet copies in-repo)
and a live ArcOS `show components` dump from a lab unit (serials/MACs redacted).

## What `dist/` publishes

Build artifacts, gitignored, rebuilt by `./build.sh`. They are also the PUBLIC
CONTRACT: a consumer holding only these files can draw a device, inspect it, and
export it to a DCIM without a checkout of this repository.

| file | what a consumer gets from it |
|---|---|
| `<device>.<config>.<view>.svg` | the drawing, with `--` DOM ids and `/` data-paths; its `<metadata>` names the source it was drawn from by `source-sha256` |
| `<device>.source.json` | the whole source manifest, every view of it — once per device; the digest in each drawing is of these exact bytes |
| `<device>.configs.json` | the device's configurations — each with its `kind` (base, orderable, example, model), its `airflow` (front-to-back, back-to-front, side, passive, or `null` where unstated), part numbers, bays and view bindings |
| `devices.json` | the portfolio index: identity (with `aliases`, the other names a box is sold or listed under), capability, gaps, search blob |
| `components.json` | the lean component index — identity, size, skins, attrs, parts (with each part's `group`), the component's own `groups` and `cages` |
| `components-detail.json` | the same refs with `provenance` and `relief`, split out because they were 88% of the bytes and no viewer reads them |
| `labs.json` | rack layouts |
| `gaps.json` | what this library admits it does not know |
| `vendors.json` | corporate lineage and NOS-vendor registry — what turns `arrcus` into "Arrcus" |
| `overlays.json` | the NOS overlays, whole: `identity`, `terms`, `interfaces`, `entity-map` |

The last two exist because the DCIM exporter used to read them off the source
tree, which made "export a NetBox document" a task that needed the development
environment rather than the artifacts. `spec/tests/test_artifact_sufficiency.py`
is what keeps them published and whole.

**Ports in the drawing.** Every port is a `<g data-class="port">`, and the
facts about it (`data-media`, `data-speed`, `data-group`, `data-group-role`)
sit on that element. A composed port, such as `common/rj45-eth@1` around a
`std/rj45` or `common/qsfp28-cage@3` around a `std/qsfp-ganged`, draws its core as a
second `data-class="port"` element nested inside the first. The core carries
`data-inner="1"`, and only the generic housing's attrs. To count or audit
ports, select `[data-class=port]:not([data-inner])`. A port on a module seated
in a bay carries the module's own group and role, from the component's
`groups:`.

Rules of the road (see spec/DESIGN.md for the full set):
- Real millimeters everywhere; origin top-left, y-down, per view.
- Physical IDs follow the silkscreen; NOS naming lives in overlays.
- No vendor logos in community skins (contracts may reserve a logo-zone).
- No datasheet copies or conversions — transcribed facts with provenance only.
- Dumps must be sanitized (serials, MACs, IPs, hostnames, communities).

Licensed Apache-2.0, same as the rest of the repository. See `../LICENSE`, and
the Licence section of `../README.md` for why the data is not under a separate
content licence.

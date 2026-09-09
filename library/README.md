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
| `<device>.<config>.<view>.svg` | the drawing, with `--` DOM ids and `/` data-paths — and the whole source manifest embedded in `<metadata>`, every view of it |
| `<device>.configs.json` | the device's configurations — each with its `kind` (base, orderable, example, model), part numbers, bays and view bindings |
| `devices.json` | the portfolio index: identity, capability, gaps, search blob |
| `components.json` | the lean component index — identity, size, skins, attrs, parts |
| `components-detail.json` | the same refs with `provenance` and `relief`, split out because they were 88% of the bytes and no viewer reads them |
| `labs.json` | rack layouts |
| `gaps.json` | what this library admits it does not know |
| `vendors.json` | corporate lineage and NOS-vendor registry — what turns `arrcus` into "Arrcus" |
| `overlays.json` | the NOS overlays, whole: `identity`, `terms`, `interfaces`, `entity-map` |

The last two exist because the DCIM exporter used to read them off the source
tree, which made "export a NetBox document" a task that needed the development
environment rather than the artifacts. `spec/tests/test_artifact_sufficiency.py`
is what keeps them published and whole.

Rules of the road (see spec/DESIGN.md for the full set):
- Real millimeters everywhere; origin top-left, y-down, per view.
- Physical IDs follow the silkscreen; NOS naming lives in overlays.
- No vendor logos in community skins (contracts may reserve a logo-zone).
- No datasheet copies or conversions — transcribed facts with provenance only.
- Dumps must be sanitized (serials, MACs, IPs, hostnames, communities).

Licensed Apache-2.0, same as the rest of the repository. See `../LICENSE`, and
the Licence section of `../README.md` for why the data is not under a separate
content licence.

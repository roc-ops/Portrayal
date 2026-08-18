# ndv-library (working name)

Content library for NDV: component contracts + skins, device manifests, NOS
overlays, and sanitized device dumps. Compiled SVGs are build artifacts
(`dist/`, gitignored) — render with `ndv-spec`.

```
components/common/<name>/v<major>/{contract.yaml, skins/*.svg}
devices/<vendor>/<model>/{device.yaml, overlays/<nos>.yaml, dumps/}
profiles/
```

First device: **Edgecore AS7726-32X** (32× QSFP28 Trident 3 white-box switch),
built from its datasheet facts (per-field provenance; no datasheet copies in-repo)
and a live ArcOS `show components` dump from a lab unit (serials/MACs redacted).

Rules of the road (see ndv-spec/DESIGN.md for the full set):
- Real millimeters everywhere; origin top-left, y-down, per view.
- Physical IDs follow the silkscreen; NOS naming lives in overlays.
- No vendor logos in community skins (contracts may reserve a logo-zone).
- No datasheet copies or conversions — transcribed facts with provenance only.
- Dumps must be sanitized (serials, MACs, IPs, hostnames, communities).

Content license: CC-BY-SA 4.0 with an outputs exception (renderings/exports made
with this library are unrestricted) — full text pending initial publication.

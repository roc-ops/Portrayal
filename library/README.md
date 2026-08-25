# library

Content library for Portrayal: component contracts + skins, device manifests, NOS
overlays, and sanitized device dumps. Compiled SVGs are build artifacts
(`dist/`, gitignored) — render with `spec`.

```
components/common/<name>/v<major>/{contract.yaml, skins/*.svg}
devices/<vendor>/<model>/{device.yaml, overlays/<nos>.yaml, dumps/}
profiles/
```

First device: **Edgecore AS7726-32X** (32× QSFP28 Trident 3 white-box switch),
built from its datasheet facts (per-field provenance; no datasheet copies in-repo)
and a live ArcOS `show components` dump from a lab unit (serials/MACs redacted).

Rules of the road (see spec/DESIGN.md for the full set):
- Real millimeters everywhere; origin top-left, y-down, per view.
- Physical IDs follow the silkscreen; NOS naming lives in overlays.
- No vendor logos in community skins (contracts may reserve a logo-zone).
- No datasheet copies or conversions — transcribed facts with provenance only.
- Dumps must be sanitized (serials, MACs, IPs, hostnames, communities).

Licensed Apache-2.0, same as the rest of the repository. See `../LICENSE`.

This previously read CC-BY-SA 4.0 with an outputs exception. It was unified to
Apache-2.0 so that a rendered SVG never raises the question of whether it is a
derivative of the library data — under a single permissive licence it cannot
matter. If share-alike on the measurement work turns out to be wanted after all,
this is the file that has to change, and it has to change before publication.

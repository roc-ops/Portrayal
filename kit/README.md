# portrayal-kit

The consumer half of [Portrayal](../README.md). It reads compiled artifacts and
does something with them — draws them, lets you inspect them, exports them.

**It never reads YAML.** That line is the whole point of this package: the
manifests, the component contracts and the schema live in `spec/` and `library/`
and are the compiler's business. Everything here works from what `build.sh`
publishes, which means a consumer needs the artifacts and not a checkout.

## What it reads

Everything in `library/dist/`, documented as a contract in
[`library/README.md`](../library/README.md). The short version:

- `<device>.<config>.<view>.svg` — the drawing. Addressable: `--` DOM ids, `/`
  data-paths. The **whole source manifest is embedded in `<metadata>`**, every
  view of it, so a page holding one SVG already knows the device's
  configurations, groups, attrs and chassis.
- `devices.json`, `components.json` (+ `components-detail.json`), `labs.json`,
  `gaps.json`, `vendors.json`, `overlays.json`.

## Modules

| module | what it does |
|---|---|
| `shell.js` | the explorer shell — device picker, view switching, tree |
| `viewer3d.js` | 2D→3D: rasterises each face onto a chassis-sized box, adds relief meshes |
| `relief.js` | turns `data-depth` / `data-z-*` annotations into geometry |
| `marks.js` | annotation and callouts |
| `states.js` | state toggling (LEDs, link states) |
| `share.js` | GLB and USDZ export |
| `gif.js` | GIF capture |
| `swap.js` | swapping a component into a bay |
| `devsel.js` | device selection and filtering |
| `dist.js` | artifact fetching and URL construction |

Plain ES modules. No bundler, no build step.

## three.js

`viewer3d.js` and `share.js` import `three` and `three/addons/` as bare
specifiers, and nothing here resolves them — supply either an import map:

```html
<script type="importmap">
{ "imports": {
  "three": "https://unpkg.com/three@0.161.0/build/three.module.js",
  "three/addons/": "https://unpkg.com/three@0.161.0/examples/jsm/"
}}
</script>
```

…or a bundler that can. It is a peer dependency, and an optional one: the 2D
half (`shell`, `marks`, `states`, `relief`) does not touch three.

## Status

Lives in the Portrayal repo for now. It has no dependency on anything outside
`dist/`, so it can move to its own repository whenever that is wanted — that is
what the artifact contract and `spec/tests/test_artifact_sufficiency.py` exist
to keep true.

Apache-2.0, same as the rest of the repository.

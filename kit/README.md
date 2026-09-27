# @portrayal/kit

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
  data-paths. Its `<metadata>` names the source it was drawn from by
  `source-sha256`. Configurations that draw a face identically share one file,
  so the kit finds a configuration's face through `configs[].files` in
  `<device>.configs.json` (`faceFile` in `dist.js`), never by its name.
- `<device>.source.json` — the **whole source manifest**, every view of it: the
  device's configurations, groups, attrs and chassis. One per device.
- `devices.json`, `components.json` (+ `components-detail.json`), `labs.json`,
  `gaps.json`, `vendors.json`, `overlays.json`.

## Where it reads from

`createShell` and `createViewer` take `dist`: either the base URL of a build
directory, or a function from a path in the build to its URL. `dist.js` makes
both:

```js
import { flatDist, packageDist } from '@portrayal/kit/dist';

// a build directory: library/dist, or a copy of it on your own server
createShell({ dist: flatDist('/portrayal/dist') });

// the npm packages, from jsDelivr: one package per device, fetched only
// when that device is opened
const dist = await packageDist();                   // @portrayal/index@latest
const pinned = await packageDist({ index: '0.3.1' });  // one release, exactly
createShell({ dist });
createViewer(el, { dist });
```

`packageDist` resolves `latest` to an exact version first, and then reads
every file at the exact version the index's `packages.json` names for it, so a
page never mixes two releases. `at(name, version)` changes where packages are
served from: another CDN, or `library/packages/` after `./publish.sh` to try
the packages locally. The explorer does that with `?dist=packages`, and reads
jsDelivr with `?dist=cdn` (and `&index=<version>`).

## Modules

| module | what it does |
|---|---|
| `shell.js` | the explorer shell — device picker, view switching, tree |
| `viewer3d.js` | 2D→3D: rasterises each face onto a chassis-sized box, adds relief meshes |
| `relief.js` | turns `data-depth` / `data-z-*` annotations into geometry |
| `marks.js` | annotation and callouts |
| `states.js` | state toggling (LEDs, link states) and what a display can read |
| `share.js` | GLB and USDZ export |
| `gif.js` | GIF capture |
| `swap.js` | swapping a component into a bay |
| `fields.js` | writing a field on a part at runtime - its text and its colour, the build's rule, for 2D and 3D alike |
| `devsel.js` | device selection and filtering |
| `dist.js` | artifact fetching, and where each file is: a build directory or the npm packages |

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

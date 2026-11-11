### Added
- **A built dist can be packed into a few files per device, on request** (`spec/tools/dev/dist_packs.py`,
  `kit/dist.js`). `dist_packs.py --dist <built dist> --out <new folder>` writes
  one pack for the faces a device's default configuration draws, a second pack
  for every other face a configuration names, and each namespace's skins in
  chunks of at most 1 MB with an index. The tool is not run by `build.sh` or
  `publish.sh`, refuses an `--out` inside the dist, and gives the same bytes on
  a second run: `library/dist/` and the npm packages are unchanged. The kit
  gains `fetchDist(url, init)`, which has the contract of `fetch` and answers a
  pack URL from its pack, and `async packedDist(base)`, which maps a path to a
  plain file or to a pack and resolves once its index has loaded.

### Changed
- **Every read of a dist URL in the kit goes through `fetchDist`** (`kit/shell.js`,
  `kit/relief.js`, `kit/zones.js`, `kit/rack/view/face.js`, `kit/index.html`,
  and `jdist`). A plain URL is passed to `fetch` as before.
- **`clearDistCache()` also forgets the packs.**

### Fixed
- **`svgSource` forgets a fetch that was rejected** (`kit/relief.js`). A network
  failure stayed in its cache for the page, so the face never loaded again. A
  missing face is still remembered as an empty drawing.

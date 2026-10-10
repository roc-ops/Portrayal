### Added
- The kit reads a device from its npm package (#691). `createShell` and
  `createViewer` take `dist` as a function from a path in the build to its
  URL, or as a string, which still means a build directory, so an existing
  caller is unchanged. `@portrayal/kit/dist` exports the three that make one:
  - `flatDist(base)`, a build directory;
  - `distResolver(dist, fallback)`, which accepts either form;
  - `await packageDist({at, index})`, the published packages. A device file
    comes from that device package, a component skin from its components
    package,
    and every other file from `@portrayal/index`. Each is read at the exact
    version `packages.json` names, and `latest` is resolved to an exact index
    version first, so a page never mixes two releases. `at(name, version)`
    picks the server and defaults to `JSDELIVR`.
  The explorer reads the packages with `?dist=packages` (a local
  `library/packages/`) and `?dist=cdn`, with `&index=<version>` to pin one.
  Its default is the build directory, as before. The per-namespace components
  packages of the npm entry in this section are what `packageDist` reads
  today.

// One fetch per dist JSON file per page load, shared by every caller.
//
// The Explorer mounts a shell and a 3D viewer in the same document, and both
// want the same two indexes. Before this they each fetched their own copy:
// components.json went over the wire twice on a load and a THIRD time from the
// component-mode branch, and <device>.configs.json twice - and because the
// viewer's guard was `first || !COMP_INDEX` where `first` means "the device
// changed", every device switch re-fetched components.json, which does not
// depend on the device at all.
//
// The memo is keyed on the RESOLVED url, so `../dist` and `../dist/` - the two
// spellings of DIST that shell.js and viewer3d.js default to - are one entry.
//
// `cache: 'no-store'` is deliberately NOT set. It was on every one of these
// call sites, which meant a browser could not reuse the file across page loads
// either; the flag was there to keep a rebuilt dist from going stale during
// development, and the memo below now does that job within a load. If you are
// iterating on the build and want the next load to see new bytes, hard-reload -
// that is the tool for it, not a permanent header on a 2 MB file.
const INFLIGHT = new Map();

/** Fetch and parse a JSON file, once. Later callers get the same promise. */
export function jdist(url) {
  const key = new URL(url, location.href).href;
  if (!INFLIGHT.has(key)) {
    INFLIGHT.set(key, fetch(key).then(r => {
      if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
      return r.json();
    }).catch(err => {
      // A failure must not be remembered, or one flaky load poisons the page.
      INFLIGHT.delete(key);
      throw err;
    }));
  }
  return INFLIGHT.get(key);
}

/**
 * The file that draws `view` of configuration `config`, from a loaded
 * `<device>.configs.json`. A drawing is written once and shared by every
 * configuration that draws it identically, so most configurations' faces carry
 * another configuration's name: look it up, never build it from `config`.
 *
 * A face the configuration does not draw falls back to the name it would have
 * had, which is not on disk: the fetch misses exactly as it always did, and
 * every caller already treats a miss as "no such face".
 */
export function faceFile(index, config, view) {
  const f = index?.configs?.find(c => c.name === config)?.files?.[view];
  return f || `${index?.device}.${config}.${view}.svg`;
}

// ---- where a dist file lives ------------------------------------------------
//
// Every file the kit reads is named by its path in a build: `devices.json`,
// `<device>.configs.json`, a face `configs[].files` names, `components/<skin>`.
// A build directory serves them all from one base. The npm packages (#528) do
// not: each device is its own package, each namespace's skins are another and
// the library-wide JSON a third. So the kit asks a function for a path's URL and
// never joins a base itself: `distAt(path)`.

/** path -> URL for one build directory (library/dist, or a copy of it). */
export function flatDist(base) {
  const b = base.endsWith('/') ? base : `${base}/`;
  return path => b + path;
}

/** `opts.dist` as a path -> URL function: a function is used as it is, a
 *  string (or nothing, then `fallback`) is a build directory's base. */
export function distResolver(dist, fallback) {
  // `||`, not `??`: an empty string meant "the default" before this function
  // existed (callers wrote `opts.dist || '../dist'`), and '' as a base would
  // put every file at the site root
  return typeof dist === 'function' ? dist : flatDist(dist || fallback);
}

/** An exact version (semver, prerelease and build allowed), a package this
 *  library publishes, and what `?index=` may name: `latest`, a dist-tag, or an
 *  exact version. None of them can hold a `/`. */
const SEMVER = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$/;
const PACKAGE = /^@portrayal\/[a-z0-9][a-z0-9-]*$/;
export const safeIndex = v => typeof v === 'string' && (/^[a-z][a-z0-9-]{0,63}$/.test(v) || SEMVER.test(v));

/** Where jsDelivr serves version `version` of npm package `name`. */
export const JSDELIVR = (name, version) => `https://cdn.jsdelivr.net/npm/${name}@${version}/`;

/**
 * path -> URL over the published npm packages.
 *
 * `at(name, version)` is the base a package is served from - jsDelivr by
 * default, or `library/packages/<dir>/` to rehearse against a local
 * `npm_packages.py` run. `index` is the `@portrayal/index` version to start
 * from: `latest`, or an exact one to pin the whole library, since the index's
 * `packages.json` names an exact version of every other package.
 *
 * `latest` is resolved to its exact version first, so every later file comes
 * from immutable URLs and one page never mixes two releases.
 */
export async function packageDist({at = JSDELIVR, index = 'latest'} = {}) {
  const INDEX = '@portrayal/index';
  // A NAME OR VERSION IS CHECKED BEFORE IT IS PART OF A URL. `index` comes from
  // the page's query string, and every other name and version from a file the
  // first request returned; unchecked, a crafted `?index=` with path segments
  // walks off the package onto other content the CDN serves, and the faces it
  // then names are parsed as markup.
  if (!safeIndex(index)) throw new Error(`not an index version or dist-tag: ${JSON.stringify(index)}`);
  const get = async url => {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
    return r.json();
  };
  const version = (await get(`${at(INDEX, index)}package.json`)).version;
  if (!SEMVER.test(String(version))) throw new Error(`${INDEX}: not a version: ${JSON.stringify(version)}`);
  const base = at(INDEX, version);
  const pk = await jdist(`${base}packages.json`);
  for (const [what, ref] of [
    ...Object.entries(pk.components || {}).map(([ns, r]) => [`components/${ns}`, r]),
    ...Object.entries(pk.devices || {})]) {
    if (!ref || !PACKAGE.test(String(ref.package)) || !SEMVER.test(String(ref.version)))
      throw new Error(`packages.json: ${what} names ${JSON.stringify(ref)}, not @portrayal/<name> at a version`);
  }
  // own keys only: a path is the page's to choose, and `constructor` or
  // `__proto__` would otherwise find something on every object
  const held = (map, key) => (map && Object.hasOwn(map, key) ? map[key] : undefined);
  const distAt = path => {
    // a skin is `components/<ns>--<name>--<major>--<skin>.svg`, and each
    // namespace's skins are a package of their own
    const skin = path.startsWith('components/') ? path.slice('components/'.length) : null;
    // a device's files all start `<device>.` and device names hold no dot
    const ref = skin !== null ? held(pk.components, skin.split('--')[0])
      : held(pk.devices, path.split('.')[0]);
    // a name no package holds falls to the index, where it misses as it
    // would in a build directory
    return ref ? at(ref.package, ref.version) + (skin ?? path) : base + path;
  };
  distAt.packages = pk;
  return distAt;
}

/** Forget everything fetched so far. For harnesses that rebuild dist in place. */
export function clearDistCache() { INFLIGHT.clear(); }

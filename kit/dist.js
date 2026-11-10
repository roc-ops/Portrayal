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
    INFLIGHT.set(key, fetchDist(key).then(r => {
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
 *  string (or nothing, then `fallback`) is a build directory's base, and a list
 *  of those is several builds read as one library (`layeredDist`). */
export function distResolver(dist, fallback) {
  if (Array.isArray(dist)) return dist.length === 1 ? distResolver(dist[0], fallback) : layeredDist(dist);
  // `||`, not `??`: an empty string meant "the default" before this function
  // existed (callers wrote `opts.dist || '../dist'`), and '' as a base would
  // put every file at the site root
  return typeof dist === 'function' ? dist : flatDist(dist || fallback);
}

// ---- several builds read as one library -------------------------------------
//
// AN OVERLAY LIBRARY (`build.sh --overlay-library`) is built into a dist of its
// own, and the kit loads it beside the public one: `dist: [publicDist,
// overlayDist]`. A later root ADDS devices and parts. An id in two roots is an
// error that names both and is never a replacement, so a private entry cannot
// shadow a public one - the build refuses the same thing first
// (spec/tools/portrayal/overlay.py), and this is the check for two dists that
// were built apart.

/** What a root is called in a sentence: its base, or its place in the list. */
export const rootName = (root, i) => (typeof root === 'string' ? root : `dist root ${i + 1}`);

/** The error for an id two roots both hold. */
export const clash = (what, id, a, b) =>
  new Error(`${what} ${id} is in both ${a} and ${b}; an overlay adds to the public library and never replaces an entry of it`);

/**
 * `roots` as one path -> URL function. Which root holds a file is learnt from
 * each root's `devices.json` and `components.json`, so `distAt.ready` settles
 * once that is known (it rejects on an id two roots hold); a path asked before
 * that goes to the first root. `readIndex` waits for it, and every index the
 * shell and the viewer read goes through `readIndex`.
 */
export function layeredDist(roots) {
  const layers = roots.map(r => distResolver(r, '../dist'));
  const names = roots.map(rootName);
  const device = new Map();     // device name -> layer
  const part = new Map();       // `ns--name--major` -> layer
  const distAt = path => {
    const skin = path.startsWith('components/') ? path.slice('components/'.length) : null;
    const i = skin !== null ? part.get(skin.split('--').slice(0, 3).join('--'))
      : device.get(path.split('.')[0]);
    return layers[i ?? 0](path);
  };
  distAt.layers = layers;
  distAt.names = names;
  distAt.ready = (async () => {
    const lists = await Promise.all(layers.map(async at => ({
      devices: (await jdist(at('devices.json'))).devices || [],
      // a root without parts of its own may have no components.json
      components: await jdist(at('components.json')).then(j => j.components || [], () => []),
    })));
    lists.forEach(({devices, components}, i) => {
      for (const d of devices) {
        if (device.has(d.name)) throw clash('device', d.name, names[device.get(d.name)], names[i]);
        device.set(d.name, i);
      }
      for (const c of components) {
        // as a skin file spells it: components.json's `major` is `v1`
        const k = `${c.ns}--${c.name}--${c.major}`;
        if (part.has(k)) throw clash('component', `${c.ns}/${c.name}@${String(c.major).replace(/^v/, '')}`, names[part.get(k)], names[i]);
        part.set(k, i);
      }
    });
  })();
  // a rejection nobody awaited yet is still reported where it is read
  distAt.ready.catch(() => {});
  return distAt;
}

// the list each merged index holds, and what names an entry in it
const MERGED = {
  'devices.json': {key: 'devices', id: d => d.name, what: 'device'},
  'components.json': {key: 'components', id: c => `${c.ns}/${c.name}@${String(c.major).replace(/^v/, '')}`, what: 'component'},
};

/**
 * One of the library-wide indexes, as `distAt` serves it. Over one build that
 * is the file; over `layeredDist` the devices.json and components.json lists
 * of every root, joined in order. Any other file is the first root's.
 */
export async function readIndex(distAt, file) {
  if (!distAt.layers) return jdist(distAt(file));
  await distAt.ready;
  const m = MERGED[file];
  if (!m) return jdist(distAt.layers[0](file));
  const seen = new Map(), all = [];
  let first;
  for (const [i, at] of distAt.layers.entries()) {
    const j = await jdist(at(file)).catch(err => { if (file === 'components.json') return {}; throw err; });
    first ??= j;
    for (const e of j[m.key] || []) {
      const id = m.id(e);
      if (seen.has(id)) throw clash(m.what, id, distAt.names[seen.get(id)], distAt.names[i]);
      seen.set(id, i);
      all.push(e);
    }
  }
  return {...first, [m.key]: all};
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
    ...Object.entries(pk.racks || {}).map(([key, r]) => [`racks/${key}`, r]),
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
    // a rack product is `racks/<vendor>--<name>.rack.json`, in the package of
    // that rack (#935); the package holds it at its root
    const rack = path.startsWith('racks/') ? path.slice('racks/'.length) : null;
    const rackKey = rack !== null && rack.endsWith('.rack.json')
      ? rack.slice(0, -'.rack.json'.length).replace('--', '/') : null;
    // a device's files all start `<device>.` and device names hold no dot
    const ref = skin !== null ? held(pk.components, skin.split('--')[0])
      : rackKey !== null ? held(pk.racks, rackKey)
      : held(pk.devices, path.split('.')[0]);
    // a name no package holds falls to the index, where it misses as it
    // would in a build directory
    return ref ? at(ref.package, ref.version) + (skin ?? rack ?? path) : base + path;
  };
  distAt.packages = pk;
  return distAt;
}

// ---- rack products (#935) ----------------------------------------------------
//
// A rack product is `kind: rack`: a frame or a cabinet the library models, read
// by the ref a saved rack file's `frame.ref` carries, `<vendor>/<name>@<major>`.
// Its compiled file is `racks/<vendor>--<name>.rack.json` in a build directory
// and at the root of its own `@portrayal/racks-<vendor>-<name>` package.

const RACK_REF = /^([a-z0-9][a-z0-9-]*)\/([a-z0-9][a-z0-9._-]*)@(\d+)$/;

/** The dist path of the file that holds a rack ref's product. The ref becomes
 *  part of a URL, so a malformed one is refused here and never reaches it. */
export function rackFile(ref) {
  const m = RACK_REF.exec(String(ref));
  if (!m) throw new Error(`not a rack ref: ${JSON.stringify(ref)}`);
  return `racks/${m[1]}--${m[2]}.rack.json`;
}

/** The product a rack ref names. The library holds one version of a product,
 *  so a ref to another major is not answered with it: the page is told, and
 *  offers to apply the product again. */
export async function readRack(distAt, ref) {
  const doc = await jdist(distAt(rackFile(ref)));
  const major = RACK_REF.exec(ref)[3];
  if (String(doc.version).split('.')[0] !== major)
    throw new Error(`${ref}: the library holds ${doc.name} ${doc.version}`);
  return doc;
}

// ---- device packs ------------------------------------------------------------
//
// A file server that limits the number of files can serve a build as packs instead of one file
// per drawing: `spec/tools/dev/dist_packs.py` writes them from a built dist, on
// request, and the published build and the npm packages do not change. A device
// has a pack of the faces its default configuration draws and, when any other
// configuration draws a face of its own, a second pack; a namespace's skins are
// packs of at most about 1 MB. A pack holds the drawings as text.
//
// The kit still asks for one drawing at a time, by a URL: a pack's URL with the
// drawing's path in the fragment. `fetchDist` is `fetch` for every URL the kit
// reads from a dist, and answers a pack URL from the pack, as a Response of its
// own, so a caller cannot tell a packed drawing from a loose file.
//
//   <base>packs/devices/<device>.json#<face file>
//   <base>packs/components/<namespace>.<k>.json#components/<skin>

const PACKS = new Map();   // pack url -> Promise of the parsed pack, or of null (no such pack)
const MISSES = new Set();  // pack urls with a fragment that no pack holds
const PACK_URL = /\/packs\/(?:devices|components)\/[^/?#]+\.json#/;
const DEVICE_PACK = /^(.*\/)packs\/devices\/([^/.?#]+)\.json$/;
const TYPES = {svg: 'image/svg+xml', json: 'application/json'};

/** A pack, fetched once and shared. A network failure or a 5xx is tried again
 *  once; a pack that is still not there then is not remembered, so a later call
 *  asks again. A 404 is: packs do not change during a page. */
async function loadPack(url) {
  let failed;
  for (let attempt = 0; attempt < 2; attempt++) {
    let r;
    try { r = await fetch(url); } catch (err) { failed = err; continue; }
    if (r.status === 404) return null;
    if (r.ok) return r.json();
    failed = Object.assign(new Error(`${url}: HTTP ${r.status}`), {packStatus: r.status});
    if (r.status < 500) break;
  }
  throw failed;
}

function pack(url) {
  let hit = PACKS.get(url);
  if (!hit) {
    hit = loadPack(url);
    PACKS.set(url, hit);
    hit.catch(() => { if (PACKS.get(url) === hit) PACKS.delete(url); });
  }
  return hit;
}

const held = (p, path) => (p?.files && Object.hasOwn(p.files, path) ? p.files[path] : undefined);

/** Which pack of a device holds `path`, from its configs.json when jdist has it
 *  (a read still on its way is waited for), else by trying the default pack and
 *  then the second. Resolves to the text, or undefined when no pack holds it. */
async function deviceText(base, device, path, defaultUrl) {
  const moreUrl = `${base}packs/devices/${device}.more.json`;
  const entry = INFLIGHT.get(new URL(`${base}${device}.configs.json`, location.href).href);
  const idx = entry ? await entry.catch(() => null) : null;
  const configs = idx?.configs;
  if (Array.isArray(configs) && configs.length && configs.every(c => c?.files && typeof c.files === 'object')) {
    const dflt = configs.find(c => c.name === idx.default);
    if (dflt) {
      if (Object.values(dflt.files).includes(path)) return held(await pack(defaultUrl), path);
      // a face no configuration names is not in any pack: no request
      if (!configs.some(c => Object.values(c.files).includes(path))) return undefined;
      return held(await pack(moreUrl), path);
    }
  }
  const first = await pack(defaultUrl);
  const text = held(first, path);
  return text !== undefined || !first?.more ? text : held(await pack(moreUrl), path);
}

const missing = () => new Response(null, {status: 404});

/**
 * `fetch`, for a file of a dist. A plain URL is passed to `fetch` as it is. A
 * pack URL (see above) answers the drawing from its pack: a new Response on
 * every call, typed by the file name, or a new 404 when no pack holds it. A
 * network failure rejects, as `fetch` does, and a 5xx is answered as itself,
 * after one more try.
 */
export async function fetchDist(url, init) {
  if (!PACK_URL.test(String(url))) return fetch(url, init);
  const u = new URL(url, location.href);
  const full = u.href;
  if (MISSES.has(full)) return missing();
  let path = u.hash.slice(1);
  try { path = decodeURIComponent(path); } catch { /* not encoded: as it is */ }
  const packUrl = full.split('#', 1)[0];
  let text;
  try {
    const dev = DEVICE_PACK.exec(packUrl);
    text = dev ? await deviceText(dev[1], dev[2], path, packUrl) : held(await pack(packUrl), path);
  } catch (err) {
    if (err.packStatus) return new Response(null, {status: err.packStatus});
    throw err;
  }
  if (text === undefined) { MISSES.add(full); return missing(); }
  return new Response(text, {headers: {'content-type': TYPES[path.split('.').pop()] || 'text/plain'}});
}

/**
 * path -> URL over a build directory whose drawings are read from packs
 * (`dist_packs.py` wrote them to `<base>packs/`). A device's configs.json and
 * source.json, the library-wide JSON and the racks are the plain files; a
 * device's drawing is its default pack's URL with the path as the fragment
 * (`fetchDist` routes it to the pack that holds it); a skin is the chunk of its
 * namespace that holds it, found by binary search in `components/index.json`.
 *
 * Resolves once that index has loaded, so no caller holds a `distAt` that is not
 * ready. Read what it returns with `fetchDist`: a bare `fetch` gets the pack.
 */
export async function packedDist(base) {
  const plain = flatDist(base);
  const b = plain('');
  const index = await jdist(`${b}packs/components/index.json`);
  return path => {
    if (path.startsWith('components/')) {
      const ns = path.slice('components/'.length).split('--')[0];
      // own keys only, as in packageDist: `constructor` is nobody's namespace
      const firsts = Object.hasOwn(index, ns) ? index[ns] : [];
      const skin = path.slice('components/'.length);
      let lo = 0, hi = firsts.length;
      while (lo < hi) {
        const mid = (lo + hi) >> 1;
        if (firsts[mid] <= skin) lo = mid + 1; else hi = mid;
      }
      return `${b}packs/components/${ns}.${lo + 1}.json#${path}`;
    }
    if (path.endsWith('.svg')) return `${b}packs/devices/${path.split('.')[0]}.json#${path}`;
    return plain(path);
  };
}

/** Forget everything fetched so far. For harnesses that rebuild dist in place. */
export function clearDistCache() { INFLIGHT.clear(); PACKS.clear(); MISSES.clear(); }

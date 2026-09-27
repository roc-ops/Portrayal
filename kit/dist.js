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

/** Forget everything fetched so far. For harnesses that rebuild dist in place. */
export function clearDistCache() { INFLIGHT.clear(); }

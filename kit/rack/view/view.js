// THE HANDLE EVERY RACK VIEW RETURNS (docs/rack-views-design.md §2.2) and the
// paths a pick names (§2.4). A view gives createView its own draw, its own
// selection paint and what it must free; this holds the rest, so the 2D and
// the 3D view cannot differ in what a host calls.

// What a path's key may start with: a mounted item, a part beside the rack, a
// cable, a bundle, a tie strap of single cables (`tie:<item>|<via>|<tie>`) and,
// in 2D only, an empty unit (`u:12` or `u:12.5`).
const KINDS = ['item', 'zeroU', 'cable', 'bundle', 'tie', 'u'];

/** `<key>` or `<key>/<part path>`; a part path has `/` in it, a key never. */
export const joinPath = (key, path = null) => (path == null || path === '' ? key : `${key}/${path}`);

/** The reverse: `{key, path}`, `path` null for a key alone. */
export function splitPath(text) {
  const s = String(text);
  const cut = s.indexOf('/');
  const key = cut < 0 ? s : s.slice(0, cut);
  if (!KINDS.includes(key.split(':')[0]) || !key.includes(':')) {
    throw new Error(`"${s}" is not a path: it starts with ${KINDS.map(k => `${k}:`).join(', ')}.`);
  }
  return {key, path: cut < 0 ? null : s.slice(cut + 1)};
}

const EVENTS = ['pick'];

/**
 * `parts`: `ready` (the first draw's promise), `update(doc, opts)`, `select(parsed)`
 * (`parsed` is splitPath's answer, or null), and `dispose()` (frees what the view made).
 * Returns `{handle, emit}`: `handle` is for the host, `emit` for the view's own
 * pick listener.
 */
export function createView({ready, update, select, dispose}) {
  const picks = new Set();
  let gone = false;
  const handle = {
    ready,
    update: (doc, opts = {}) => (gone ? Promise.reject(new Error('This view has been disposed.')) : update(doc, opts)),
    select(path) {
      if (gone) return;
      select(path == null ? null : splitPath(path));
    },
    on(name, fn) {
      if (!EVENTS.includes(name)) throw new Error(`There is no "${name}" event: a view emits ${EVENTS.map(e => `"${e}"`).join(', ')}.`);
      picks.add(fn);
      return () => picks.delete(fn);
    },
    dispose() {
      if (gone) return;
      gone = true;
      picks.clear();
      dispose();
    },
  };
  const emit = event => { if (!gone) for (const fn of [...picks]) fn(event); };
  return {handle, emit};
}

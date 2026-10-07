// WHAT A VIEWER HAS WRITTEN ON A PART, applied to a live document.
//
// A field is something a part's contract declares (`fields`, carried in
// components.json) and its skin is wired to: a `data-from` node whose TEXT is the
// value, a `data-fill-from` node whose FILL is, a `data-stroke-from` node whose
// STROKE is, a `data-stroke-derive` node whose stroke is a darker shade of it
// (below), a `data-r-from` node whose RADIUS is half of it (a diameter field).
// render.py's `fill_from_attrs` applies all five when a drawing is built; this
// applies the same rule when a viewer changes one afterwards.
//
// ONE HELPER FOR BOTH HALVES. shell.js paints the 2D drawing the page shows and
// relief.js the documents the 3D scene rasterises; they were near-copies that
// both wrote text and nothing else, so a latch colour set on a seated optic
// arrived as `data-latch-color` on the group and painted nowhere (#481). Two
// copies of a rule drift, and that drift is the bug - so the rule lives here,
// in a module with no DOM globals of its own and nothing of three in it.
//
// The rule, which is the build's:
//
//   text     a value replaces the node's text; an EMPTY value hides the node.
//   colour   a value sets `fill` / `stroke`; an EMPTY value leaves what was
//            drawn. A shape with no fill is not a quieter drawing, it is an
//            invisible one (render.py says it the same way).
//   size     a number sets `r` to half of it; empty or not a number leaves
//            what was drawn, as colour does.
//
// AND AN EMPTY VALUE HAS TO PUT IT BACK, which the build never has to do. A build
// paints once; a viewer sets red, then blue, then clears it, and "leave what was
// drawn" means the grey the skin shipped with - not the blue it was a moment ago.
// So the first paint stashes the drawn value on the node itself, as
// `data-portrayal-fill` / `data-portrayal-stroke`, and clearing restores it. On
// the node rather than in a map, because the 3D side keeps a document as TEXT
// and repaints from its own last output: an attribute survives serialising, and
// a WeakMap keyed by element would be gone the first time it was.
//
// A stash of the EMPTY STRING means the node had no such attribute, so restoring
// removes it rather than writing `fill=""`.

// AN OUTLINE DERIVED FROM ITS FILL (#482). `data-stroke-derive="<key>"` draws a
// node's stroke as a fixed darker shade of that key's colour, so a latch given
// any colour gets an edge that goes with it without a second field to keep in
// step. ONE EXACT RULE, the same as render.py's `stroke_shade` and held to it
// byte for byte by spec/tests/test_stroke_derive.py: each channel times 61/100,
// rounded half up, in integers - (c * 61 + 50) / 100, floored. #6f6f6f, the
// generic latch's grey, lands on #444444. Accepted: `#rgb` and `#rrggbb`, either
// case, with surrounding space; anything else has no shade (null), and the
// stroke is left as drawn. Always answers lowercase `#rrggbb`.
export function strokeShade(colour) {
  const m = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(String(colour ?? '').trim());
  if (!m) return null;
  let h = m[1];
  if (h.length === 3) h = [...h].map(c => c + c).join('');
  let out = '#';
  for (const i of [0, 2, 4])
    out += Math.floor((parseInt(h.slice(i, i + 2), 16) * 61 + 50) / 100)
      .toString(16).padStart(2, '0');
  return out.toLowerCase();
}

const esc = s => (typeof CSS !== 'undefined' && CSS.escape ? CSS.escape(s) : String(s));
// what `data-r-from` accepts as a number; render.py's R_FROM_NUMBER, spelled alike
const R_FROM_NUMBER = /^[ \t\n\r]*[0-9.]+[ \t\n\r]*$/;
const STASH = {fill: 'data-portrayal-fill', stroke: 'data-portrayal-stroke',
               r: 'data-portrayal-r', transform: 'data-portrayal-transform',
               display: 'data-portrayal-display'};

/** Set a colour attribute, remembering what was drawn the first time. */
function paint(node, attr, value) {
  if (!node.hasAttribute(STASH[attr]))
    node.setAttribute(STASH[attr], node.getAttribute(attr) ?? '');
  node.setAttribute(attr, value);
}

// A POSITION (docs/switch-positions-design.md): `data-move` is a table of
// "option: dx dy [deg], ..." and render.py's parse_moves reads it alike. A
// malformed entry throws, as the build raises: a table nobody can read must
// not quietly move nothing.
const MOVE_ENTRY = /^\s*([^:,\s]+)\s*:\s*(-?[0-9.]+)\s+(-?[0-9.]+)(?:\s+(-?[0-9.]+))?\s*$/;
export function parseMoves(spec) {
  const out = {};
  for (const part of String(spec || '').split(',')) {
    if (!part.trim()) continue;
    const m = MOVE_ENTRY.exec(part);
    if (!m) throw new Error(`data-move entry '${part.trim()}' is not 'option: dx dy [deg]'`);
    out[m[1]] = [Number(m[2]), Number(m[3]), Number(m[4] || 0)];
  }
  return out;
}
// Python's _num: an integer without ".0", anything else as JS writes it
const num = x => String(x);
function centre(node) {
  const tag = node.localName || node.tagName;
  const g = a => Number(node.getAttribute(a) || 0);
  if (tag === 'rect') return [g('x') + g('width') / 2, g('y') + g('height') / 2];
  if (tag === 'circle' || tag === 'ellipse') return [g('cx'), g('cy')];
  throw new Error(`data-move turns a <${tag}>; only rect, circle and ellipse can turn`);
}
/** The transform a move applies, the text render.py's move_transform writes. */
export function moveTransform(node, [dx, dy, deg]) {
  const parts = [];
  if (dx || dy) parts.push(`translate(${num(dx)} ${num(dy)})`);
  if (deg) { const [cx, cy] = centre(node); parts.push(`rotate(${num(deg)} ${num(cx)} ${num(cy)})`); }
  return parts.join(' ');
}

/** Put back what was drawn, if anything here ever changed it. */
function restore(node, attr) {
  const drawn = node.getAttribute(STASH[attr]);
  if (drawn === null) return;
  if (drawn === '') node.removeAttribute(attr); else node.setAttribute(attr, drawn);
  node.removeAttribute(STASH[attr]);
}

// WHAT THE BUILD DREW FOR A FIELD, read off a part's group: the `data-<key>` it
// carries, else the text of the node wired to that key. The build writes the
// attribute only for a field a configuration set, so a part drawn from its
// skin's own default has none and its text IS the default. Undefined for a
// field with neither - a colour field at its default, which has no text node.
// Here and not in the shell, so the `data-from` rule has one home.
/** The value a part's drawing holds for `key`, or undefined. */
export function drawnField(el, key) {
  return el?.getAttribute?.(`data-${key}`)
    ?? el?.querySelector?.(`[data-from="${esc(key)}"]`)?.textContent ?? undefined;
}

/**
 * Apply `vals` ({key: value}) to one part: `el` is the part's group (or its
 * projection on another face), and the nodes it is wired through are inside it.
 * `null` and `''` are both "empty". Each key also lands on `el` as `data-<key>`,
 * which is how a host reads back what is set.
 */
export function paintFields(el, vals) {
  for (const [k, v] of Object.entries(vals || {})) {
    const val = v == null ? '' : String(v);
    const colour = val.trim();
    el.setAttribute(`data-${k}`, val);
    const key = esc(k);
    for (const t of el.querySelectorAll(`[data-from="${key}"]`)) {
      t.textContent = val;
      // a node a position shows or hides is shown by that field alone
      if (t.hasAttribute('data-show-from')) continue;
      if (val) t.removeAttribute('display'); else t.setAttribute('display', 'none');
    }
    for (const n of el.querySelectorAll(`[data-fill-from="${key}"]`))
      if (colour) paint(n, 'fill', colour); else restore(n, 'fill');
    for (const n of el.querySelectorAll(`[data-stroke-from="${key}"]`))
      if (colour) paint(n, 'stroke', colour); else restore(n, 'stroke');
    // the build already drew the shade of the default, so "as drawn" is right
    // both for an empty value and for one with no shade
    const shade = strokeShade(colour);
    for (const n of el.querySelectorAll(`[data-stroke-derive="${key}"]`))
      if (shade) paint(n, 'stroke', shade); else restore(n, 'stroke');
    // A SIZE: `data-r-from` is a DIAMETER field and the circle takes half of it
    // (docs/pluggables-cables-design.md section 4). ASCII digits and a point
    // only, with ASCII blanks around them - render.py's R_FROM_NUMBER, which
    // lint L122 also asks, so "1e1", "1_0", "inf" and non-ASCII digits are junk
    // in all three - and junk, zero or empty puts back the radius the skin was
    // drawn with. Not \s: it takes Unicode blanks, which Python's pattern does not.
    const d = R_FROM_NUMBER.test(val) ? Number(val) : NaN;
    for (const n of el.querySelectorAll(`[data-r-from="${key}"]`))
      if (Number.isFinite(d) && d > 0) paint(n, 'r', String(d / 2)); else restore(n, 'r');
    // A POSITION. MOVE puts the option's offset in front of the transform the
    // node was drawn with; SHOW displays the node only for the options it
    // lists. Empty, or an option the table does not name, is as drawn - the
    // skin draws the default (render.py fill_from_attrs, the same two rules).
    for (const n of el.querySelectorAll(`[data-move-from="${key}"]`)) {
      const move = colour ? parseMoves(n.getAttribute('data-move'))[colour] : undefined;
      if (!move) { restore(n, 'transform'); continue; }
      if (!n.hasAttribute(STASH.transform))
        n.setAttribute(STASH.transform, n.getAttribute('transform') ?? '');
      const drawn = n.getAttribute(STASH.transform);
      const tf = [moveTransform(n, move), drawn].filter(Boolean).join(' ');
      if (tf) n.setAttribute('transform', tf); else n.removeAttribute('transform');
    }
    for (const n of el.querySelectorAll(`[data-show-from="${key}"]`)) {
      if (!colour) { restore(n, 'display'); continue; }
      const shown = String(n.getAttribute('data-show') || '').split(/\s+/).includes(colour);
      if (!n.hasAttribute(STASH.display))
        n.setAttribute(STASH.display, n.getAttribute('display') ?? '');
      if (shown) n.removeAttribute('display'); else n.setAttribute('display', 'none');
    }
  }
  return el;
}

/**
 * Put every colour, radius, transform and display this helper changed under
 * `root` back to what was drawn.
 * Text is not touched: a text node has no drawn value to return to that the
 * document does not already hold, and a part whose fields are cleared keeps
 * whatever its label last said, as it always has.
 */
export function unpaintFields(root) {
  for (const attr of ['fill', 'stroke', 'r', 'transform', 'display']) {
    if (root.hasAttribute && root.hasAttribute(STASH[attr])) restore(root, attr);
    for (const n of root.querySelectorAll(`[${STASH[attr]}]`)) restore(n, attr);
  }
  return root;
}

// ------------------------------------------------------------ the field editor
// What a host needs to offer a part's fields in a form (#811): the rows to draw,
// what a typed value is worth, and the string a location carries them in. Pure,
// like everything above - the explorer builds the controls, this says what goes
// in them.

/**
 * The rows of a field form: one per field the component declares, in the order
 * it declares them. `fields` is components.json's `fields` for the part;
 * `current` is what the drawing holds now ({key: value}, typically read off the
 * part's `data-<key>` attributes). A field nothing has set shows its contract
 * default. Values are strings, as the drawing holds them.
 */
export function fieldRows(fields, current = {}) {
  return Object.entries(fields || {}).map(([key, f]) => {
    const def = f?.default == null ? '' : String(f.default);
    const held = current?.[key];
    const value = held == null || held === '' ? def : String(held);
    const type = f?.type === 'choice' && Array.isArray(f.options) ? 'choice'
      : f?.type === 'number' ? 'number' : 'text';
    return {
      key, type, value, default: def,
      label: f?.label || key,
      unit: f?.unit || '',
      description: f?.description || '',
      options: type === 'choice' ? f.options.map(String) : [],
      pattern: typeof f?.pattern === 'string' ? f.pattern : '',
    };
  });
}

/**
 * Is `value` one this field takes? A choice takes its options and nothing
 * else; a number takes a finite number; a text field with a `pattern` takes
 * what matches the whole of it. An unreadable pattern refuses nothing.
 */
export function fieldAccepts(field, value) {
  const v = value == null ? '' : String(value);
  // a declaration is an object. `decl[key]` on a plain object finds a function
  // for `constructor` or `toString`, and that is not a field
  if (!field || typeof field !== 'object') return false;
  if (field.type === 'choice' && Array.isArray(field.options))
    return field.options.map(String).includes(v);
  if (field.type === 'number') return v.trim() !== '' && Number.isFinite(Number(v));
  if (typeof field.pattern === 'string' && field.pattern) {
    try { return new RegExp(`^(?:${field.pattern})$`).test(v); } catch (e) { return true; }
  }
  return true;
}

// `path~key~value`, comma-separated, each of the three pieces escaped on its own
// - the shape `swap=` has (swap.js encodeSwaps), with one more piece. Sorted, so
// one state is one string.
/** `{path: {key: value}}` as the string a location carries; '' for nothing. */
export function encodeFields(map) {
  // `~` is the one separator encodeURIComponent leaves alone
  const e = v => encodeURIComponent(v).replace(/~/g, '%7E');
  const out = [];
  for (const path of Object.keys(map || {}).sort())
    for (const key of Object.keys(map[path] || {}).sort()) {
      const v = map[path][key];
      if (v == null) continue;
      out.push(`${e(path)}~${e(key)}~${e(String(v))}`);
    }
  return out.join(',');
}

// What a location may carry: a link is not a place to hold a document, and a
// contract's pattern is tested against every value kept.
const MAX_ENTRIES = 256, MAX_VALUE = 256;

// NEVER THROWS, and one bad entry does not take the rest with it, for the
// reason decodeSwaps gives: the string is typed, pasted and truncated by people.
/** The reverse of encodeFields. Unknown shapes are dropped entry by entry. */
export function decodeFields(s) {
  if (typeof s !== 'string' || !s) return {};
  // GATHERED IN MAPS, NOT IN `{}`. The string is whatever a link carries, and
  // on a plain object `out['constructor']` is `Object` itself: the write
  // `(out[path] ||= {})[key] = value` then landed on a global
  // (`constructor~keys~x` replaced Object.keys with a string) or threw on a
  // read-only member (`constructor~prototype~x`), taking the page with it.
  // Object.fromEntries defines own properties, so a name every object inherits
  // is an ordinary key in what is returned.
  const got = new Map();
  for (const part of s.split(',').slice(0, MAX_ENTRIES)) {
    const bits = part.split('~');
    if (bits.length !== 3) continue;
    let path, key, value;
    try { [path, key, value] = bits.map(decodeURIComponent); } catch (e) { continue; }
    if (!path || !key || path === '__proto__' || key === '__proto__') continue;
    // no field's value is this long, and a pattern is run over whatever is kept
    if (value.length > MAX_VALUE) continue;
    if (!got.has(path)) got.set(path, new Map());
    got.get(path).set(key, value);
  }
  return Object.fromEntries([...got].map(([path, kv]) => [path, Object.fromEntries(kv)]));
}

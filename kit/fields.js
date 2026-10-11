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
    const v = [Number(m[2]), Number(m[3]), Number(m[4] || 0)];
    // '.' and '1.2.3' match the pattern and are not numbers; render.py's
    // float() raises on them, so the kit throws rather than write NaN (#874)
    if (!v.every(Number.isFinite)) throw new Error(`data-move entry '${part.trim()}' is not 'option: dx dy [deg]'`);
    out[m[1]] = v;
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
/**
 * The whole transform of a moved node, the text render.py's move_transform
 * writes: `translate(dx dy) <base> rotate(deg cx cy)`, so a turn pivots on the
 * node's own centre in its own frame and the offset lands in the parent's.
 */
export function moveTransform(node, [dx, dy, deg], base = '') {
  const parts = [];
  if (dx || dy) parts.push(`translate(${num(dx)} ${num(dy)})`);
  if (base) parts.push(base);
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
      // empty is "as built": whatever the build drew, a configuration's move included
      if (!colour) { restore(n, 'transform'); continue; }
      if (!n.hasAttribute(STASH.transform))
        n.setAttribute(STASH.transform, n.getAttribute('transform') ?? '');
      // THE SKIN'S OWN TRANSFORM is the base a move composes on. A node the
      // build moved for a configuration says what it was drawn with in
      // `data-move-base`; otherwise what was here first is the drawing. An
      // option the table does not list - the default - is that base alone.
      const base = n.getAttribute('data-move-base') ?? n.getAttribute(STASH.transform);
      const move = parseMoves(n.getAttribute('data-move'))[colour];
      const tf = move ? moveTransform(n, move, base) : base;
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

// ------------------------------------------------------- adjustable positions
// A PART THAT SLIDES (docs/adjustable-positions-design.md). A device declares
// it once, and the compiled drawing carries the declaration on the root of
// every face as `data-adjustments`: for each id its `axis`, `carrier`, `range`,
// `default`, `stops`, `label`, `datum`, and `at`, the position the file was
// built at. Each member node says `data-moves-with="<id>"` and
// `data-moves-by="dx dy dz"`: the mm it moves for each mm of position, `dx` and
// `dy` in the frame of its face and `dz` its depth behind that face.
//
// THE VALUE IS A FIELD, held at the path of the carrier under the id of the
// adjustment: `{'rail-panel': {'rail-setback': '271.2'}}`, the map every field
// reader already holds. It is not a component field, so a reader that tests a
// value against a component declaration asks here as well.

// What a typed number may look like: digits and one point. No sign and no
// exponent, as adjustments.py reads it, so the build and the kit refuse the
// same text. Not \s, for the reason R_FROM_NUMBER gives.
const POSITION_NUMBER = /^[ \t\n\r]*(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)[ \t\n\r]*$/;
// a number all the same, written with a sign or an exponent: refused, and told so
const POSITION_SIGNED = /^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$/;
// 0.1 mm, rounded half up: adjustments.py round01, the same arithmetic
const round01 = x => Math.floor(Number(x) * 10 + 0.5) / 10;
// THE ONE SPELLING OF A POSITION: `120` and `271.2`, never `120.0` or `271.20`
const spell = x => round01(x).toFixed(1).replace(/\.0$/, '');
const stopsByValue = a => Object.entries(a?.stops || {})
  .map(([name, value]) => ({name, value: Number(value)}))
  .sort((p, q) => p.value - q.value || (p.name < q.name ? -1 : p.name > q.name ? 1 : 0));
// attribute text, tolerant of one that is not JSON
const parsed = text => { try { const v = JSON.parse(text); return v && typeof v === 'object' ? v : {}; } catch (e) { return {}; } };

/**
 * The adjustments a drawing declares: `{id: {axis, carrier, range, default,
 * stops, label, datum, at, id, on}}`, or `{}`. `root` is a face's `<svg>` or
 * anything that holds one. Each entry also carries its own `id` and, as `on`,
 * the model the face names, so `adjustmentAccepts` can say the whole sentence.
 */
export function adjustmentsOf(root) {
  const svg = root?.hasAttribute?.('data-adjustments') ? root
    : root?.querySelector?.('[data-adjustments]');
  if (!svg) return {};
  const on = svg.querySelector?.('[data-path="chassis"]')?.getAttribute?.('data-model') || '';
  const out = {};
  for (const [id, a] of Object.entries(parsed(svg.getAttribute('data-adjustments'))))
    if (a && typeof a === 'object') out[id] = {...a, id, on};
  return out;
}

/**
 * Is `value` a position of this adjustment? Answers `{ok: true, value}` with
 * the ONE spelling to keep (a string: the number rounded to 0.1 mm, in
 * decimal, with no exponent, no sign and no trailing `.0`), or `{ok: false,
 * reason}` with a sentence saying what the adjustment takes.
 *
 * A stop name is input only: it answers with the number behind it. With a
 * `range` any number from min to max is a position, both ends included; with
 * stops and no range only the stop values are. `who` names the adjustment
 * (`id`) and the device (`on`) for the sentence, where the adjustment itself
 * does not carry them.
 */
export function adjustmentAccepts(adjustment, value, who = {}) {
  const a = adjustment && typeof adjustment === 'object' ? adjustment : {};
  const id = who.id ?? a.id ?? 'the position';
  const on = who.on ?? a.on ?? '';
  const name = on ? `${id} on ${on}` : String(id);
  const named = stopsByValue(a);
  // the four blanks adjustments.py takes off, and no others: trim() would take
  // a BOM the build keeps, and keep a unit separator the build takes
  const text = value == null || typeof value === 'boolean' ? ''
    : String(value).replace(/^[ \t\n\r]+|[ \t\n\r]+$/g, '');
  let n = null;
  if (Object.hasOwn(a.stops || {}, text)) n = Number(a.stops[text]);
  else if (POSITION_NUMBER.test(text)) n = Number(text);
  if (Array.isArray(a.range) && a.range.length === 2) {
    // `-20`, `+20`, `1e2`: a number, in a spelling a position never has
    if (n === null && POSITION_SIGNED.test(text))
      return {ok: false, reason: `${name} takes a number in mm written with digits and a point `
                                 + `only. ${text} is not.`};
    if (n === null || !Number.isFinite(n)) {
      const tail = named.length ? `, or one of: ${named.map(s => s.name).join(', ')}` : '';
      return {ok: false, reason: `${name} takes a number in mm${tail}.`};
    }
    const r = round01(n);
    if (r < round01(a.range[0]) || r > round01(a.range[1]))
      return {ok: false, reason: `${name} takes ${spell(a.range[0])} to ${spell(a.range[1])} mm. `
                                 + `${spell(n)} is outside it.`};
    return {ok: true, value: spell(n)};
  }
  if (n !== null && Number.isFinite(n) && named.some(s => round01(s.value) === round01(n)))
    return {ok: true, value: spell(n)};
  return {ok: false, reason: `${name} takes one of: `
                             + named.map(s => `${s.name} (${spell(s.value)})`).join(', ') + '.'};
}

/**
 * The rows of a position control: one per adjustment, in id order.
 * `adjustments` is what `adjustmentsOf` answers, or the `adjustments` of a
 * device's configs.json; `current` is the fields map a host holds,
 * `{path: {key: value}}`, in which a position sits at the path of its carrier
 * under its id. A row shows the position held when it is one the adjustment
 * takes, else the position the drawing was built at (`at`), else the default.
 * Positions are strings in the one spelling; `stops` is in order of position,
 * and `stop` names the stop the row stands at, or is ''.
 */
export function adjustmentRows(adjustments, current = {}) {
  return Object.keys(adjustments || {}).sort().map(id => {
    const a = adjustments[id] || {};
    const built = spell(a.at ?? a.default ?? 0);
    const held = current?.[a.carrier]?.[id];
    const got = held == null || held === '' ? null : adjustmentAccepts(a, held, {id});
    const value = got?.ok ? got.value : built;
    const stops = stopsByValue(a).map(s => ({name: s.name, value: spell(s.value)}));
    const ranged = Array.isArray(a.range) && a.range.length === 2;
    return {
      id, value, built,
      default: spell(a.default ?? 0),
      label: a.label || id,
      carrier: a.carrier || '',
      axis: a.axis || '',
      datum: a.datum || '',
      unit: 'mm',
      type: ranged ? 'range' : 'stops',
      min: ranged ? spell(a.range[0]) : '',
      max: ranged ? spell(a.range[1]) : '',
      stops,
      stop: stops.find(s => s.value === value)?.name || '',
    };
  });
}

/**
 * Does going from one fields map to another move a part that slides? True
 * when, for some adjustment, the value at the path of its carrier under its
 * id is not the same string in `was` and in `now` (both `{path: {key:
 * value}}`). `adjustments` is `adjustmentsOf(face)` or the `adjustments` of a
 * device's configs.json. The 3D viewer asks this to tell a change it must
 * rebuild the scene for from one it can repaint.
 */
export function positionsChanged(adjustments, was, now) {
  const held = (map, a, id) => { const v = map?.[a?.carrier]?.[id]; return v == null ? '' : String(v); };
  return Object.entries(adjustments || {})
    .some(([id, a]) => !!a && typeof a === 'object' && !!a.carrier && held(was, a, id) !== held(now, a, id));
}

const ADJUST = {transform: 'data-portrayal-adjust-transform', depth: 'data-portrayal-adjust-depth',
                lift: 'data-portrayal-adjust-lift', out: 'data-portrayal-adjust-out',
                profile: 'data-portrayal-adjust-profile', profileY: 'data-portrayal-adjust-profile-y'};
// a millimetre as the drawing writes one: to 0.1 um, never -0
const mm = x => { const r = Math.round(x * 1e4) / 1e4; return String(r === 0 ? 0 : r); };
/** `attr` of `node` as it was built, kept under `stash` the first time. */
function builtAttr(node, attr, stash) {
  if (!node.hasAttribute(stash)) node.setAttribute(stash, node.getAttribute(attr) ?? '');
  return node.getAttribute(stash);
}
/** Write `value`, or put `attr` back as built and forget the stash. */
function moveAttr(node, attr, stash, value) {
  const built = builtAttr(node, attr, stash);
  if (value === null) {
    if (built === '') node.removeAttribute(attr); else node.setAttribute(attr, built);
    node.removeAttribute(stash);
  } else node.setAttribute(attr, value);
  return built;
}
// a profile is `t:height,t:height`: every height moves, as render.py's
// _shift_heights moves them
const shiftProfile = (text, by) => text.split(',').map(pair => {
  const [t, o] = pair.split(':');
  return `${t}:${mm(Number(o) + by)}`;
}).join(',');

/** Move one member `delta` mm of position from where it was built. */
function moveMember(node, delta) {
  const by = String(node.getAttribute('data-moves-by') || '').trim().split(/\s+/).map(Number);
  const [dx, dy, dz] = [by[0] || 0, by[1] || 0, by[2] || 0];
  // IN THE PLANE OF THE FACE: an offset in front of the transform the node
  // was built with, in the frame of the face
  const x = dx * delta, y = dy * delta;
  const base = builtAttr(node, 'transform', ADJUST.transform);
  moveAttr(node, 'transform', ADJUST.transform,
           x || y ? `translate(${mm(x)} ${mm(y)})${base ? ' ' + base : ''}` : null);
  // ALONG THE DEPTH OF THE FACE (section 6). A projection is flat and has none.
  if (!dz || node.hasAttribute('data-projection')) return;
  const z = dz * delta;
  if (node.hasAttribute('data-depth') || node.hasAttribute(ADJUST.depth)) {
    // a well: its floor is its depth
    const built = Number(builtAttr(node, 'data-depth', ADJUST.depth));
    moveAttr(node, 'data-depth', ADJUST.depth, z ? mm(built + z) : null);
    return;
  }
  // anything else stands a lift off its face, the sign reversed, and its
  // absolute heights go with it, as they do for a part sunk in a well
  const lift = Number(builtAttr(node, 'data-z-lift', ADJUST.lift) || 0);
  moveAttr(node, 'data-z-lift', ADJUST.lift, z ? mm(lift - z) : null);
  const inside = [node, ...node.querySelectorAll(
    `[data-z-out],[data-z-profile],[data-z-profile-y],[${ADJUST.out}],[${ADJUST.profile}],[${ADJUST.profileY}]`)];
  for (const n of inside) {
    if (n.hasAttribute('data-z-out') || n.hasAttribute(ADJUST.out)) {
      const out = Number(builtAttr(n, 'data-z-out', ADJUST.out));
      moveAttr(n, 'data-z-out', ADJUST.out, z ? mm(out - z) : null);
    }
    for (const [attr, stash] of [['data-z-profile', ADJUST.profile], ['data-z-profile-y', ADJUST.profileY]])
      if (n.hasAttribute(attr) || n.hasAttribute(stash)) {
        const prof = builtAttr(n, attr, stash);
        moveAttr(n, attr, stash, z && prof ? shiftProfile(prof, -z) : null);
      }
  }
}

/**
 * Move every member of every adjustment under `root` to the position `fields`
 * holds for it: the value at the path of its carrier, under its id. `root` is
 * a face's `<svg>` or anything that holds one; `fields` is `{path: {key:
 * value}}`, as a plain object or a Map. An adjustment with no value, or with
 * one it does not take, stands where the drawing was built (`at`), exactly as
 * built: the first move remembers each attribute it changes on the node
 * itself, and a move back to the built position puts them back and forgets.
 * The same rule in 2D and in 3D, where the depth it writes is what is built.
 * Answers `{id: position}` for what it drew, as numbers.
 */
export function paintAdjustments(root, fields) {
  const svg = root?.hasAttribute?.('data-adjustments') ? root
    : root?.querySelector?.('[data-adjustments]');
  const drew = {};
  if (!svg) return drew;
  const at = path => (fields instanceof Map ? fields.get(path) : fields?.[path]) || {};
  for (const [id, a] of Object.entries(adjustmentsOf(svg))) {
    const held = at(a.carrier)[id];
    const got = held == null || held === '' ? null : adjustmentAccepts(a, held);
    const built = Number(a.at ?? a.default ?? 0);
    const value = got?.ok ? Number(got.value) : built;
    drew[id] = value;
    for (const n of svg.querySelectorAll(`[data-moves-with="${esc(id)}"]`))
      moveMember(n, value - built);
  }
  return drew;
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

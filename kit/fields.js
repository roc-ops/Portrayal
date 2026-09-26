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
               r: 'data-portrayal-r'};

/** Set a colour attribute, remembering what was drawn the first time. */
function paint(node, attr, value) {
  if (!node.hasAttribute(STASH[attr]))
    node.setAttribute(STASH[attr], node.getAttribute(attr) ?? '');
  node.setAttribute(attr, value);
}

/** Put back what was drawn, if anything here ever changed it. */
function restore(node, attr) {
  const drawn = node.getAttribute(STASH[attr]);
  if (drawn === null) return;
  if (drawn === '') node.removeAttribute(attr); else node.setAttribute(attr, drawn);
  node.removeAttribute(STASH[attr]);
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
  }
  return el;
}

/**
 * Put every colour and radius this helper changed under `root` back to what was drawn.
 * Text is not touched: a text node has no drawn value to return to that the
 * document does not already hold, and a part whose fields are cleared keeps
 * whatever its label last said, as it always has.
 */
export function unpaintFields(root) {
  for (const attr of ['fill', 'stroke', 'r']) {
    if (root.hasAttribute && root.hasAttribute(STASH[attr])) restore(root, attr);
    for (const n of root.querySelectorAll(`[${STASH[attr]}]`)) restore(n, attr);
  }
  return root;
}

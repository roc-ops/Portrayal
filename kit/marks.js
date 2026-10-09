// Markup as a document.
//
// A marked-up drawing is one JSON object of CSS selectors, not a pile of clicks.
// That is the whole reason the renderer bothers to emit stable ids and data-*:
// the drawing is addressable, so markup can be typed, written by a UI, carried
// in a URL, or POSTed by an MCP server without any of them inventing a private
// vocabulary. Everything here is a pure function over an SVG root and such a
// document - no UI, no globals, no shell.
//
//   {v:1, device, config, view, legend, crop, marks:[{select, color, state, label, lamp}],
//    swaps:{path: ref|null}, fields:{path: {key: value|null}}}
//
// `swaps` is what the reader changed in the drawing before marking it up: bay
// and cage paths mapped to the component seated there, null for one emptied.
// Only what differs from the configuration's build - the configuration already
// says the rest - so an un-swapped document carries `{}`.
//
// `fields` is what the reader WROTE ON the parts: an optic's `latch-color` and
// `label`, a supply's wattage - whatever a part declares in its contract's
// `fields`. The shape is the shell's own `state.cfgFields` and what the 3D
// viewer's `setFields` takes, so a host writes it from one and a reader replays
// it with `shell.setFields(path, vals)` per entry. A value of null is kept, as
// "cleared" - the shell reads it as empty. An unfielded document carries `{}`.
//
// `color` and `lamp` are both colours and they are not the same kind of thing.
// `color` is INK: a ring the reader is meant to notice, drawn around the part.
// `lamp` is what the HARDWARE is showing - the paint of the lamp itself. It
// exists because a lamp nobody documented renders `off`/`on` and the `on` is a
// stylesheet default, not a fact; somebody composing a picture of a device whose
// vendor never published a port-LED table has to be able to say what colour the
// lamp is in the picture they are drawing. It sits on the mark beside `state`
// rather than in a document of its own, because it is the same statement about
// the same part addressed by the same selector, and two parallel documents
// keyed by selector is two things to keep in step.
//
// Three rules learned the hard way and encoded below:
//
//   A selector from a human or a machine WILL be malformed, and querySelectorAll
//   throws on malformed. One bad row must never take the document with it, so
//   every query is wrapped and the failure is reported per mark.
//
//   getBBox() is in the ELEMENT's coordinate system. Anything drawn at the root
//   has to be carried through every transform between the two or a port's halo
//   lands several slots away. rootRect() is demo/hl.js's composition, unchanged.
//
//   A selector matches groups and leaves alike, and the compiled art nests them:
//   <g data-class="led"> contains <circle data-class="led">. Marking both draws
//   two rings around one lamp, so matches are collapsed to their outermost
//   members. Highlighting a group reads as highlighting the part.
//
// The export target is Microsoft Word: no external CSS, no script, no CSS custom
// properties, no filters. So toSvg() does not merely copy classes across - it
// resolves var(--led-color) to a literal paint and draws every halo as plain
// stroked geometry. The preview uses exactly the same geometry, so what you see
// on the stage is what lands in the document.
//
// And a fourth rule, which is the reason the behaviour section below exists:
//
//   A STATIC EXPORT OF A BLINKING LAMP DOES NOT LOSE THE BLINK, IT LIES.
//
// The animation is real and it is in the exported file, but only a browser
// holding that file as a DOCUMENT will run it. An <img>, Word, PowerPoint,
// Inkscape and every PNG rasteriser show one frame - and one frame of a blink is
// a picture of a different, documented, wrong state. On the S9510-28DC
// "Blinking Green" on the GNSS lamp is `learning`; the frame that renders solid
// is `survey-complete` and the frame that renders dark is `off` (not
// configured). Three rows of the same HIG table, and a reader has no way to know
// which one they are looking at. So every behaving lamp is ringed, the ring is
// plain geometry that survives print and greyscale, and the legend names the
// notation. See "behaviour" below for what the ring means.

import { boundLamps } from './states.js';

const NS = 'http://www.w3.org/2000/svg';

// Every element this module adds carries data-portrayal; every element it
// MODIFIES records what it was given and what was taken away. clear() can then
// undo itself precisely, instead of stripping state- classes a user set by hand.
const OWNED = 'data-portrayal';
const ADDED = 'data-pm-added';
const TOOK = 'data-pm-took';
const VIEWBOX = 'data-pm-viewbox';
const LIT = 'data-pm-lit';

const STATE_RE = /^[a-z0-9-]+$/;          // a state name is a token, not prose
// A lamp colour is written into an inline custom property and then read back out
// by getComputedStyle for the export, so it is the one field of the document
// that reaches a CSS value slot. Hex only: that is what a colour input produces,
// it is what Word's importer understands, and it is not a syntax that can carry
// `url(...)` into a drawing built from a share URL somebody else wrote.
const HEX_RE = /^#(?:[0-9a-f]{3}|[0-9a-f]{4}|[0-9a-f]{6}|[0-9a-f]{8})$/i;

// ------------------------------------------------------------------ document

/**
 * Coerce anything doc-shaped into the canonical document. Never throws: a
 * document that arrives half-formed from a URL or an MCP client should degrade
 * to "no marks", not to a stack trace.
 */
export function normalise(doc) {
  const d = doc && typeof doc === 'object' ? doc : {};
  const marks = Array.isArray(d.marks) ? d.marks : [];
  return {
    v: 1,
    device: str(d.device),
    config: str(d.config),
    view: str(d.view),
    // Carried through as given when it is an object. `legend: true` is the whole
    // of v1, but a legend with a title, a placement or a column count is an
    // object, and a normalise() that coerced one to `true` would eat those
    // fields silently - the worst way to reject a document. Everything here
    // tests it for truth, so an object reads as "yes, a legend" today and can
    // grow meaning without a second document shape. An ARRAY is not a legend
    // object (swaps and fields refuse one the same way), so it reads as true
    // rather than being carried through as a shape the schema does not allow.
    legend: d.legend && typeof d.legend === 'object' && !Array.isArray(d.legend) ? d.legend : d.legend !== false,
    crop: rect(d.crop),
    marks: marks.filter(m => m && typeof m === 'object').map(m => ({
      // Optional, never invented. Marks are otherwise positional, so "drop the
      // mark on psu-0" is index arithmetic or selector-string matching - fine
      // for a UI holding the array, hopeless for an MCP client editing a
      // document it was handed. An id given is an id kept, through the URL codec
      // and back; absent stays absent rather than becoming a synthetic name that
      // changes every time the document is round-tripped.
      id: str(m.id),
      select: str(m.select),
      color: str(m.color),
      state: str(m.state),
      label: str(m.label),
      // Dropped rather than kept-and-ignored when it is not a hex: a value that
      // survives normalise() is a value the URL codec will hand back and a UI
      // will show in its swatch, and a swatch showing something the drawing
      // never painted is worse than no swatch.
      lamp: HEX_RE.test(str(m.lamp)) ? str(m.lamp).toLowerCase() : '',
    })),
    swaps: swapsOf(d.swaps),
    fields: fieldsOf(d.fields),
  };
}

// A FIELD MAP is {path: {key: value}}, normalised the way a swap map is: entry by
// entry, so one bad entry does not take the good ones with it. A path or a key
// that is empty, or `__proto__`, names nothing; a part's entry that is not a
// plain object is dropped; a value that is a string is kept (control characters
// stripped, as for a label - but NOT trimmed, and an empty string is a value:
// it is how a reader hides a label), null is kept as "cleared", and anything
// else - a number, an object - is dropped. A part left with no keys is dropped,
// so an unfielded document is `{}` however it arrived.
function fieldsOf(f) {
  const out = {};
  if (!f || typeof f !== 'object' || Array.isArray(f)) return out;
  for (const [p, vals] of Object.entries(f)) {
    const path = str(p);
    if (!path || path === '__proto__') continue;
    if (!vals || typeof vals !== 'object' || Array.isArray(vals)) continue;
    const kept = {};
    for (const [k, v] of Object.entries(vals)) {
      const key = str(k);
      if (!key || key === '__proto__') continue;
      if (v === null) kept[key] = null;
      else if (typeof v === 'string') kept[key] = v.replace(/[\u0000-\u001f\u007f]/g, '');
    }
    if (Object.keys(kept).length) out[path] = kept;
  }
  return out;
}

// A SWAP MAP is {path: ref} with null for an emptied bay or cage - the own-key
// rule swap.js's applyOverrides states, so an emptied entry is KEPT as null
// rather than dropped. Anything else is dropped entry by entry: a value that is
// neither a string nor empty is not a component reference, and a key that is
// empty (or `__proto__`, which a plain object turns into its prototype) names
// no part of any drawing.
function swapsOf(s) {
  const out = {};
  if (!s || typeof s !== 'object' || Array.isArray(s)) return out;
  for (const [k, v] of Object.entries(s)) {
    const key = str(k);
    if (!key || key === '__proto__') continue;
    if (v == null || v === '') out[key] = null;
    else if (typeof v === 'string' && str(v)) out[key] = str(v);
  }
  return out;
}

/**
 * A crop rectangle in the drawing's OWN coordinate system - millimetres, the
 * same units as the viewBox - or null. Millimetres and not pixels for the same
 * reason px/mm is how the PNG is dimensioned: the drawing is hardware, and "the
 * management block" is a region of a faceplate, not a region of someone's
 * screen at whatever zoom they happened to be at.
 */
function rect(c) {
  if (!c || typeof c !== 'object') return null;
  const [x, y, w, h] = ['x', 'y', 'w', 'h'].map(k => Number(c[k]));
  if (![x, y, w, h].every(Number.isFinite) || w <= 0 || h <= 0) return null;
  return {x: round(x), y: round(y), w: round(w), h: round(h)};
}

// Control characters are stripped, not preserved. XML 1.0 cannot represent most
// of them at all, so a label carrying one would export a file no reader will
// open; and the URL codec below substitutes on \x01-\x0f, which a label
// containing those bytes would collide with. Neither is a loss worth keeping.
const str = v => (typeof v === 'string' ? v : v == null ? '' : String(v))
  .replace(/[\u0000-\u001f\u007f]/g, '').trim();

/** A stable download name for a document: as7946-30xb-dc-psu-rear-marked.svg */
export function filename(doc, ext) {
  const d = normalise(doc);
  const parts = [d.device, d.config, d.view].filter(Boolean);
  // A crop is a different picture of the same view, and two files an hour apart
  // in a downloads folder should not be told apart by their timestamps.
  return `${parts.join('-') || 'drawing'}-marked${d.crop ? '-crop' : ''}.${ext}`;
}

// ------------------------------------------------------------------ matching

/**
 * Run one mark's selector. The only place querySelectorAll is called.
 * @returns {{els: Element[], error: string|null}}
 */
export function match(svgRoot, mark) {
  const sel = str(mark && mark.select);
  if (!sel) return {els: [], error: 'empty selector'};
  let all;
  try {
    all = [...svgRoot.querySelectorAll(sel)];
  } catch (e) {
    return {els: [], error: `bad selector: ${e.message || e}`};
  }
  return {els: all, error: null};
}

// A selector that matches a group and its children should mark the part once.
// Ancestor-walking rather than pairwise containment: [data-path] matches ~1500
// elements on the AGR400 front, and the O(n^2) form is a visible stall.
function outermost(els) {
  if (els.length < 2) return els;
  const set = new Set(els);
  return els.filter(e => {
    for (let p = e.parentNode; p && p.nodeType === 1; p = p.parentNode)
      if (set.has(p)) return false;
    return true;
  });
}

// The union of data-states across the matches, for the row's state dropdown.
// Several contracts still put a DESCRIPTION where a state name goes - "Blue =
// all lanes linked, Red = not all lanes linked" - and splitting that on spaces
// offers the user "all", "lanes" and "not". An attribute containing '=' is
// prose, so drop the whole attribute rather than mine tokens out of it.
function statesOf(els) {
  const out = new Set();
  for (const el of els) {
    const raw = el.getAttribute('data-states') || '';
    if (!raw || raw.includes('=')) continue;
    for (const tok of raw.split(/[\s,]+/)) if (STATE_RE.test(tok)) out.add(tok);
  }
  return [...out].sort();
}

// A lamp, or a part with a lamp in it. The distinction matters for `lamp`: the
// colour is set on the matched part and INHERITS down to the lamp, so marking a
// whole rj45 jack whose left LED is the lamp is a legitimate way to say it.
const isLamp = el => el.getAttribute('data-class') === 'led' ||
                     !!el.querySelector('[data-class="led"]');

// ------------------------------------------------------------------ geometry

// demo/hl.js, verbatim in spirit: the bbox is in the element's own space and the
// halo is appended to the root, so compose the matrix between them.
function rootRect(svg, el) {
  let b, m;
  try {
    b = el.getBBox();
    const s = svg.getScreenCTM();
    m = s ? s.inverse().multiply(el.getScreenCTM()) : el.getCTM();
  } catch (e) {
    return null;                     // not rendered, or no geometry to speak of
  }
  if (!b || !m || (!b.width && !b.height)) return null;
  const pt = (x, y) => ({x: m.a * x + m.c * y + m.e, y: m.b * x + m.d * y + m.f});
  const cs = [pt(b.x, b.y), pt(b.x + b.width, b.y),
              pt(b.x, b.y + b.height), pt(b.x + b.width, b.y + b.height)];
  const xs = cs.map(c => c.x), ys = cs.map(c => c.y);
  const x = Math.min(...xs), y = Math.min(...ys);
  return {x, y, w: Math.max(...xs) - x, h: Math.max(...ys) - y};
}

function ring(svg, r, color, pad, width, opacity, tag) {
  const rect = document.createElementNS(NS, 'rect');
  rect.setAttribute(OWNED, tag);
  rect.setAttribute('x', round(r.x - pad));
  rect.setAttribute('y', round(r.y - pad));
  rect.setAttribute('width', round(r.w + pad * 2));
  rect.setAttribute('height', round(r.h + pad * 2));
  rect.setAttribute('rx', round(Math.min(0.9, pad)));
  rect.setAttribute('fill', 'none');
  rect.setAttribute('stroke', color);
  rect.setAttribute('stroke-width', width);
  if (opacity < 1) rect.setAttribute('stroke-opacity', opacity);
  rect.setAttribute('pointer-events', 'none');
  svg.appendChild(rect);
  return rect;
}

const round = n => Math.round(n * 1000) / 1000;

// The glow alone gets painted over by neighbours drawn later - touching cages
// lose the shared edge - so a highlight is two concrete rings appended last, the
// soft one for presence and the crisp one for the boundary. No filter: Word
// renders none of them, and this way the preview and the export agree.
function halo(svg, el, color) {
  const r = rootRect(svg, el);
  if (!r) return false;
  ring(svg, r, color, 1.35, 1.8, 0.28, 'halo-soft');
  ring(svg, r, color, 0.45, 0.7, 1, 'halo');
  return true;
}

// ----------------------------------------------------------------- behaviour

// render.py writes one of two animations onto a lamp whose state declares a
// `behavior`. Reading them back is how this module learns that a lamp is not
// showing what it appears to be showing.
const BEHAVIOR_ANIM = {'portrayal-blink': 'blinking',
                       'portrayal-alternate': 'alternating'};

// The word that goes beside a label in the legend. Deliberately the vocabulary
// of the device.yaml `behavior:` field and of the vendor HIG tables ("Blinking
// Green", "Flashing between Green and Red"), not a coinage of this module.
const BEHAVIOR_WORD = {blinking: 'blinking', alternating: 'alternating'};

// Which selectors in THIS drawing carry an animation, straight out of the
// compiled stylesheet. The alternative - getComputedStyle on every element with
// a state- class - is correct and unusably slow: `[data-class='led']` with a
// state on the AGR400 front is ~1500 elements, on every keystroke. The rules are
// a handful, their selectors are already exact about which lamps and which
// state, and querySelectorAll settles the class test for free.
const ANIM_RULE = /([^{}]+)\{\s*animation:\s*(portrayal-blink|portrayal-alternate)\b[^}]*\}/g;

function behaviorRules(svgRoot) {
  const out = [];
  for (const style of svgRoot.querySelectorAll('style')) {
    ANIM_RULE.lastIndex = 0;
    let m;
    while ((m = ANIM_RULE.exec(style.textContent || '')))
      out.push([m[1].trim(), BEHAVIOR_ANIM[m[2]]]);
  }
  return out;
}

/**
 * Every lamp in this drawing that is currently animating, with the paint it is
 * animating between. Needs a laid-out root: the colours are custom properties
 * resolved by the cascade, and a detached tree has no cascade.
 * @returns {Array<{el: Element, mode: string, color: string, alt: string|null}>}
 */
export function behaving(svgRoot) {
  if (!svgRoot || !svgRoot.isConnected) return [];
  const seen = new Map();
  for (const [sel, mode] of behaviorRules(svgRoot)) {
    let els;
    try { els = svgRoot.querySelectorAll(sel); } catch (e) { continue; }
    for (const el of els) if (!seen.has(el)) seen.set(el, mode);
  }
  const out = [];
  for (const [el, mode] of seen) {
    // The rule matched, but the cascade decides. A later rule for the same lamp
    // can have turned the animation off, and a lamp the document then marked
    // `off` should not be ringed for a behaviour it is not performing.
    const cs = getComputedStyle(el);
    if (BEHAVIOR_ANIM[(cs.animationName || '').split(',')[0].trim()] !== mode) continue;
    out.push({el, mode,
              color: cs.getPropertyValue('--led-color').trim() || '#8d939a',
              alt: cs.getPropertyValue('--led-color-alt').trim() || null});
  }
  return out;
}

// An odd dash count so the pattern cannot come to rest on the corners of a
// rectangular lamp and read as four ticks.
const RING_DASHES = 7;

/**
 * The static notation for a behaviour: a ring around the lamp.
 *
 * Why a ring, and why these two rings:
 *
 *   It is geometry, not colour, not opacity and not a filter. Word imports no
 *   filters, print has no opacity budget worth spending on a 2mm lamp, and a
 *   colour-coded notation is exactly the thing that dies in greyscale - which is
 *   how these drawings get photocopied into a runbook.
 *
 *   BROKEN ring = blinking. The gaps in the ring ARE the gaps in the light: the
 *   lamp goes dark, and the notation goes dark with it.
 *   CONTINUOUS two-tone ring = alternating. It never goes dark, because the lamp
 *   never goes dark - it swaps colour. So in greyscale, where the two colours
 *   collapse into one grey, the distinction that survives is the one that
 *   matters: a ring with holes in it means the lamp turns off, a ring without
 *   them means it does not.
 *
 *   The dash COUNT is fixed and the dash length is derived from the ring's own
 *   perimeter, so a 1.6mm status lamp and a 6mm PSU lamp both get seven dashes.
 *   A fixed dash LENGTH would have given the small lamp two dashes and a smear.
 *
 *   Each ring is laid over a dark backing ring, the same trick halo() uses: the
 *   lamp colours are saturated mid-tones and the chassis they sit on is a dark
 *   grey, so a bare green ring on a dark panel is legible and the same ring on a
 *   white-background crop is not.
 */
function behaviorRing(svg, el, mode, color, alt) {
  const r = rootRect(svg, el);
  if (!r) return false;
  const size = Math.min(r.w, r.h);
  // Tight. Status lamps are stacked on 2.9mm centres on the S9510-28DC and are
  // 2mm tall, so a ring with a generous margin reaches into the lamp above it
  // and the reader cannot tell which of the two it belongs to - which is a new
  // way of being wrong about the same fact.
  const pad = clamp(size * 0.22, 0.22, 0.45);
  const width = clamp(size * 0.18, 0.22, 0.45);
  const box = {x: r.x - pad, y: r.y - pad, w: r.w + pad * 2, h: r.h + pad * 2};
  // A round lamp deserves a round ring, and a long rectangular one a stadium.
  // It also keeps the notation clearly apart from halo()'s square mark ring.
  const rx = Math.min(box.w, box.h) / 2;
  const perim = 2 * (box.w - 2 * rx) + 2 * (box.h - 2 * rx) + 2 * Math.PI * rx;
  const dash = round(perim / (RING_DASHES * 2));

  const at = (stroke, w, dashes, offset, opacity, tag) => {
    const rect = document.createElementNS(NS, 'rect');
    rect.setAttribute(OWNED, tag);
    rect.setAttribute('x', round(box.x));
    rect.setAttribute('y', round(box.y));
    rect.setAttribute('width', round(box.w));
    rect.setAttribute('height', round(box.h));
    rect.setAttribute('rx', round(rx));
    rect.setAttribute('fill', 'none');
    rect.setAttribute('stroke', stroke);
    rect.setAttribute('stroke-width', round(w));
    if (dashes) rect.setAttribute('stroke-dasharray', dashes);
    if (offset) rect.setAttribute('stroke-dashoffset', offset);
    if (opacity < 1) rect.setAttribute('stroke-opacity', opacity);
    rect.setAttribute('pointer-events', 'none');
    svg.appendChild(rect);
  };

  const pattern = `${dash} ${dash}`;
  at('#14171a', width * 1.9, mode === 'alternating' ? null : pattern, 0, 0.5, 'beh-back');
  at(color, width, pattern, 0, 1, 'beh');
  // The second colour occupies the gaps, so the ring closes: two colours, no
  // darkness. `alt` is what the device.yaml wrote as `behavior: {mode:
  // alternating, color: ...}` - the S9510-28DC PSU flashing green/red.
  if (mode === 'alternating') at(alt || '#8d939a', width, pattern, dash, 1, 'beh');
  return true;
}

// ------------------------------------------------------------------ apply

// Later marks win on conflict, and so does a mark over a chip: a state is a
// replacement, not an accumulation. Two state- classes on one element would be
// settled by stylesheet order, which is nobody's idea of paint order.
//
// Only what the DOCUMENT did not put there is stashed for restoring. Two marks
// over one element - a broad `all LEDs off` then a narrow `this one faulted` -
// would otherwise have the second stash the first's class as if the user had
// set it, and clear() would faithfully hand back a state nobody asked for.
function replaceState(el) {
  const mine = new Set((el.getAttribute(ADDED) || '').split(' ').filter(Boolean));
  const present = [...el.classList].filter(c => c.startsWith('state-'));
  const took = present.filter(c => !mine.has(c));
  if (present.length) el.classList.remove(...present);
  if (took.length)
    el.setAttribute(TOOK, [...new Set(
      (el.getAttribute(TOOK) || '').split(' ').filter(Boolean).concat(took))].join(' '));
}

// Add classes and record them, so clear() takes exactly these off again.
function stamp(el, add) {
  el.classList.add(...add);
  el.setAttribute(ADDED, [...new Set(
    (el.getAttribute(ADDED) || '').split(' ').filter(Boolean).concat(add))].join(' '));
}

// Put a lamp colour a mark set back to what the drawing had (clear() does the
// same for every one at once).
function unlight(el) {
  const was = el.getAttribute(LIT);
  if (was) el.style.setProperty('--led-color', was);
  else el.style.removeProperty('--led-color');
  el.removeAttribute(LIT);
  if (!el.getAttribute('style')) el.removeAttribute('style');
}

/**
 * Apply every mark to a live SVG. Clears first, so calling it on every keystroke
 * is the intended usage.
 *
 * @param opts.legend  honour doc.legend and draw the strip (default true). The
 *                     strip grows the root viewBox, so a stage that fits-to-view
 *                     should refit afterwards.
 * @returns {Array<{index, select, count, total, states, error, warning}>} one per
 *          mark, in document order. `count` is parts marked (nested matches
 *          collapsed), `total` is raw selector hits. A row showing 0 is the
 *          feedback that makes a typed selector usable. `error` means the mark
 *          was skipped; `warning` means it was applied but is probably not what
 *          was meant.
 */
export function apply(svgRoot, doc, opts = {}) {
  clear(svgRoot);
  const d = normalise(doc);
  const report = [];
  let binds = null;           // outlet path -> its lamps, read once if a state needs it

  d.marks.forEach((mark, index) => {
    const {els, error} = match(svgRoot, mark);
    const parts = outermost(els);
    const row = {index, select: mark.select, count: parts.length,
                 total: els.length, states: statesOf(els), error, warning: null};

    if (mark.state && !STATE_RE.test(mark.state))
      row.error = row.error || `bad state name: ${mark.state}`;
    // The stylesheet paints any state- class it knows, whether or not the part
    // claims to have that state, so `state: 'fault'` on a link LED lights up red
    // and looks correct. It is still a claim the model does not support. Said
    // once here, a UI can show it and an MCP client can act on it.
    else if (mark.state && row.states.length && !row.states.includes(mark.state))
      row.warning = `no match declares state '${mark.state}' ` +
                    `(declared: ${row.states.join(', ')})`;

    // A lamp colour aimed at something that is not a lamp sets a custom property
    // nothing reads, and the picture does not change. The UI only offers the
    // choice on lamps, but a typed selector and a share URL can say anything.
    if (mark.lamp && parts.length && !parts.some(isLamp))
      row.warning = [row.warning, `no match is a lamp: a lamp colour paints ` +
        `--led-color, and nothing here reads it`].filter(Boolean).join('; ');

    const stated = mark.state && STATE_RE.test(mark.state);
    for (const el of parts) {
      const add = ['portrayal-marked', `pm-${index}`];
      if (stated) {
        replaceState(el);
        add.push(`state-${mark.state}`);
        // AN OUTLET'S STATE IS SHOWN ON ITS LAMP (#934): every lamp `for:`
        // binds to this part takes the same state, by the rule states.js
        // boundLamps states for the chips and the 3D scene too. The lamp gets
        // the state and nothing else - no ring, no label, not counted - and is
        // put back by clear() like any element a mark changed. A later mark
        // naming the lamp itself still wins, by order, as marks always do.
        const path = el.getAttribute('data-path');
        if (path) {
          binds = binds || boundLamps(svgRoot);
          for (const lamp of binds.get(path) || []) {
            if (parts.includes(lamp)) continue;
            replaceState(lamp);
            stamp(lamp, [`state-${mark.state}`]);
          }
        }
      }
      stamp(el, add);
      if (mark.label) el.setAttribute('data-mark-label', mark.label);
      // The skins paint every lamp fill="var(--led-color, <unlit>)" and the
      // state- rules work by setting that property on the part or an ancestor.
      // So a chosen lamp colour is the same mechanism, one specificity higher:
      // an inline custom property on the part, inherited by the lamp inside it.
      // It beats any state- rule for the same lamp, which is what "I am telling
      // you what this one shows" has to mean.
      //
      // `off` is the exception and it is not a special case so much as the
      // literal reading: a lamp the document says is off is not showing a
      // colour. The choice stays in the document so that turning it back on
      // does not ask for the colour again.
      if (mark.lamp && HEX_RE.test(mark.lamp) && mark.state !== 'off') {
        if (!el.hasAttribute(LIT)) el.setAttribute(LIT, el.style.getPropertyValue('--led-color'));
        el.style.setProperty('--led-color', mark.lamp);
      }
    }
    if (mark.color) for (const el of parts) halo(svgRoot, el, mark.color);
    report.push(row);
  });

  // A LAMP THAT IS OFF SHOWS NO CUSTOM COLOUR, whichever mark said it was off.
  // One mark's own `off` already skips its colour (above); this is the same rule
  // for a colour one mark gave and an `off` another mark - or an outlet's state
  // reaching its lamp (#934) - put on the same lamp. relief.js reads it the same
  // way in 3D (applyNodeLampColors asks the expanded state of the lamp), so the
  // two pictures agree.
  for (const el of svgRoot.querySelectorAll(`[${LIT}]`)) {
    if (!el.classList.contains('state-off')) continue;
    unlight(el);
  }

  // Every behaving lamp in the drawing, not only the ones a mark named. A lamp
  // put into a blinking state by a chip, by a share URL, or by the config the
  // drawing was compiled with misrepresents itself in a static file just as
  // badly as one this document lit, and neither carries a label to warn anyone.
  //
  // Drawn on the live stage too, where the lamp is genuinely blinking and the
  // ring is therefore redundant. That is the point: the stage is the preview,
  // and a preview that omits the notation the file will carry is a preview of a
  // different picture.
  if (opts.behavior !== false)
    for (const b of behaving(svgRoot)) behaviorRing(svgRoot, b.el, b.mode, b.color, b.alt);

  if (opts.legend !== false && d.legend) mountLegend(svgRoot, d);
  return report;
}

/** Remove everything apply() added, and put back everything it took away. */
export function clear(svgRoot) {
  if (!svgRoot) return;
  for (const el of svgRoot.querySelectorAll(`[${OWNED}]`)) el.remove();
  for (const el of svgRoot.querySelectorAll(`[${ADDED}]`)) {
    const added = (el.getAttribute(ADDED) || '').split(' ').filter(Boolean);
    if (added.length) el.classList.remove(...added);
    const took = (el.getAttribute(TOOK) || '').split(' ').filter(Boolean);
    if (took.length) el.classList.add(...took);
    el.removeAttribute(ADDED);
    el.removeAttribute(TOOK);
    el.removeAttribute('data-mark-label');
    // An element the drawing gave no style attribute gets none back. The
    // harness compares outerHTML before and after to prove clear() is exact,
    // and a leftover style="" is a difference (unlight sees to it).
    if (el.hasAttribute(LIT)) unlight(el);
    if (!el.getAttribute('class')) el.removeAttribute('class');
  }
  // The legend grows all three of viewBox, height and width - a label wider than
  // the drawing widens the strip - so all three come back. Restoring two of them
  // leaves the drawing printing at the wrong size with a viewBox that looks right.
  const vb = svgRoot.getAttribute(VIEWBOX);
  if (vb) {
    const [box, h, w] = vb.split('|');
    put(svgRoot, 'viewBox', box);
    put(svgRoot, 'height', h);
    put(svgRoot, 'width', w);
    svgRoot.removeAttribute(VIEWBOX);
  }
}

// An attribute the drawing did not have comes back as absent, not as empty.
function put(el, attr, value) {
  if (value) el.setAttribute(attr, value); else el.removeAttribute(attr);
}

// ------------------------------------------------------------------ legend

/**
 * The legend strip: one swatch and label per mark that carries a label, laid
 * out in the SVG's OWN millimetre coordinate system below the drawing, so it
 * scales with the drawing instead of with whatever is displaying it.
 *
 * @returns {{g: SVGGElement, height: number, width: number}|null}
 */
export function legend(svgRoot, doc) {
  const d = normalise(doc);
  // A label on a mark that reached nothing is not a legend row. The legend is a
  // key to the drawing beside it, and a row for a mark that matched nothing is
  // an export that confidently states something is highlighted when the reader
  // can see it is not - a typo'd selector, or the right selector on the wrong
  // view, turned into a false claim in a document that outlives this page. The
  // mark stays in the document and the panel still says it matched nothing; it
  // simply does not get to speak for the drawing.
  // What is animating right now, which for a legend built by apply() is what
  // this document just made animate. Consulted twice: to note the behaviour on
  // the row whose mark caused it, and to key the notation at the end.
  const beh = behaving(svgRoot);
  const behAt = new Map(beh.map(b => [b.el, b]));
  const modeOf = els => {
    for (const el of els) {
      if (behAt.has(el)) return behAt.get(el);
      // A mark usually names the part, not the lamp inside it - `psu-0`, not
      // `psu-0--led`. The behaviour is on the lamp, and the row is still a row
      // about a part that is blinking.
      for (const [el2, b] of behAt) if (el.contains(el2)) return b;
    }
    return null;
  };

  const items = d.marks
    .filter(m => m.label && match(svgRoot, m).els.length)
    // A lamp colour is ahead of the stylesheet's own idea of the state, because
    // it was chosen precisely where the stylesheet's idea is a default and not a
    // fact. It is behind `color`, which is the ring the row is a key to.
    .map(m => {
      const els = match(svgRoot, m).els;
      const b = modeOf(els);
      return {label: m.label,
              color: m.color || m.lamp || litColor(els, m.state) ||
                     stateColor(svgRoot, m.state) || '#8d939a',
              hollow: !m.color,
              // The note is a SEPARATE run of text, in the dim ink, rather than
              // an edit to the label. "Blinking Green - learning" is what the
              // legend has to end up saying, and the half of it the document
              // supplied is the half nothing here is entitled to rewrite.
              note: b ? BEHAVIOR_WORD[b.mode] : '',
              beh: b ? b.mode : '', behColor: b ? b.color : '', behAlt: b ? b.alt : ''};
    });

  // The key. Without it the ring is a mark the reader can see and cannot read,
  // and "the drawing looks slightly different" is not the same as being told
  // that this lamp is not showing a steady light. It is generated, so it is
  // appended after the document's own rows, and it appears whether or not any
  // mark carries a label - the lamps are ringed either way.
  const modes = new Set(beh.map(b => b.mode));
  const keys = [];
  if (modes.has('blinking'))
    keys.push({label: 'broken ring: blinking, not steady', color: '#22262a',
               hollow: true, note: '', beh: 'blinking', behColor: '#22262a', behAlt: ''});
  if (modes.has('alternating'))
    // Two inks that are both dark enough to read on the pale strip. The obvious
    // choice for "the other colour" is the dim grey used elsewhere here, and it
    // disappears against the panel - which makes the key chip look BROKEN, i.e.
    // it draws the notation for the other behaviour.
    keys.push({label: 'two-tone ring: alternating between two colours', color: '#22262a',
               hollow: true, note: '', beh: 'alternating', behColor: '#22262a',
               behAlt: '#767e86'});
  items.push(...keys);
  if (!items.length) return null;

  const vb = viewBox(svgRoot);
  // Type size follows the drawing, not the page: 3.6mm reads well across a
  // 440mm faceplate and is absurd across an 18mm module skin. Every other
  // measurement is derived from it, so the strip stays in proportion.
  const fs = clamp(vb.w / 122, 2.0, 3.8);
  const pad = fs * 0.65, sw = fs * 1.6, gap = fs * 0.5, sep = fs * 1.4;
  // Per-character rather than a flat 0.55em average. The average is fine for
  // wrapping a sentence and wrong for a short all-caps label: "PWR" measured at
  // 0.55em came out narrower than it prints, and the behaviour note that follows
  // it was laid down on top of the last letter.
  const est = t => fs * [...t].reduce((a, c) =>
    a + (/[A-Z0-9@#%&]/.test(c) ? 0.72 : /[ilj.,:;'!|()[\]]/.test(c) ? 0.31
                                       : /[mw]/.test(c) ? 0.82 : 0.55), 0);
  // The chip of a behaving row wears the same ring as the lamp does, so the key
  // is a picture of the notation and not a description of it.
  const rpad = fs * 0.34;

  // Flow into rows, wrapping at the drawing's width.
  const rows = [[]];
  let used = 0;
  for (const it of items) {
    const chipW = sw + (it.beh ? rpad * 2 : 0);
    const w = chipW + gap + est(it.label) +
              (it.note ? gap * 1.1 + est(it.note) : 0) + sep;
    if (used && used + w > vb.w - pad * 2) { rows.push([]); used = 0; }
    rows[rows.length - 1].push({...it, w, chipW});
    used += w;
  }
  const rowH = fs * 1.85;
  const height = pad * 2 + rows.length * rowH;
  // A label longer than the drawing is wide would otherwise run off the edge of
  // the panel. Widening the strip is the lesser evil: a legend that cannot be
  // read is not a legend.
  const width = Math.max(vb.w, ...rows.map(r => r.reduce((a, i) => a + i.w, 0) + pad * 2));

  const g = document.createElementNS(NS, 'g');
  g.setAttribute(OWNED, 'legend');
  g.setAttribute('id', 'portrayal-legend');
  g.setAttribute('transform', `translate(${round(vb.x)},${round(vb.y + vb.h)})`);

  // A pale panel rather than transparency: the same file has to read on a white
  // Word page and on the demo's near-black stage.
  const bg = document.createElementNS(NS, 'rect');
  bg.setAttribute('x', 0); bg.setAttribute('y', 0);
  bg.setAttribute('width', round(width)); bg.setAttribute('height', round(height));
  bg.setAttribute('fill', '#f6f7f8');
  bg.setAttribute('stroke', '#c3c8cd');
  bg.setAttribute('stroke-width', 0.25);
  g.appendChild(bg);

  rows.forEach((row, ri) => {
    let x = pad;
    const y = pad + ri * rowH;
    for (const it of row) {
      const cx = x + (it.beh ? rpad : 0);
      const ch = fs * 1.15, cy = y + (rowH - ch) / 2;
      const chip = document.createElementNS(NS, 'rect');
      chip.setAttribute('x', round(cx));
      chip.setAttribute('y', round(cy));
      chip.setAttribute('width', round(sw));
      chip.setAttribute('height', round(ch));
      chip.setAttribute('rx', round(fs * 0.2));
      chip.setAttribute('fill', it.hollow ? 'none' : it.color);
      chip.setAttribute('stroke', it.color);
      chip.setAttribute('stroke-width', round(it.hollow ? fs * 0.2 : 0.25));
      g.appendChild(chip);
      if (it.beh) chipRing(g, {x: cx - rpad, y: cy - rpad,
                               w: sw + rpad * 2, h: ch + rpad * 2},
                           fs, it.beh, it.behColor, it.behAlt);

      let tx = x + it.chipW + gap;
      const t = document.createElementNS(NS, 'text');
      t.setAttribute('x', round(tx));
      t.setAttribute('y', round(y + rowH / 2 + fs * 0.36));
      t.setAttribute('font-family', 'sans-serif');
      t.setAttribute('font-size', round(fs));
      t.setAttribute('fill', '#22262a');
      t.textContent = it.label;
      g.appendChild(t);
      if (it.note) {
        tx += est(it.label) + gap * 1.1;
        const n = t.cloneNode(false);
        n.setAttribute('x', round(tx));
        n.setAttribute('fill', '#5c646b');
        n.setAttribute('font-style', 'italic');
        n.textContent = it.note;
        g.appendChild(n);
      }
      x += it.w;
    }
  });
  return {g, height, width};
}

// The legend's copy of behaviorRing(), in the strip's own coordinates and around
// a chip rather than a lamp. Same dash count and the same "broken means it goes
// dark" rule, because a key that draws the notation differently from the drawing
// is not a key.
function chipRing(g, box, fs, mode, color, alt) {
  const rx = Math.min(box.w, box.h) / 2;
  const perim = 2 * (box.w - 2 * rx) + 2 * (box.h - 2 * rx) + 2 * Math.PI * rx;
  const dash = round(perim / (RING_DASHES * 2));
  const at = (stroke, offset) => {
    const r = document.createElementNS(NS, 'rect');
    r.setAttribute('x', round(box.x)); r.setAttribute('y', round(box.y));
    r.setAttribute('width', round(box.w)); r.setAttribute('height', round(box.h));
    r.setAttribute('rx', round(rx));
    r.setAttribute('fill', 'none');
    r.setAttribute('stroke', stroke);
    r.setAttribute('stroke-width', round(fs * 0.17));
    r.setAttribute('stroke-dasharray', `${dash} ${dash}`);
    if (offset) r.setAttribute('stroke-dashoffset', offset);
    g.appendChild(r);
  };
  at(color, 0);
  if (mode === 'alternating') at(alt || '#8d939a', dash);
}

/**
 * The paint the marked lamp is ACTUALLY showing, read off the lamp itself.
 *
 * stateColor() below probes a bare <g class="state-x"> at the root, and for the
 * device-wide palette that is right. It cannot see the per-instance palette,
 * which render.py writes as id selectors - `#led-sync.state-synced { --led-color:
 * #22c55e }` - precisely so that one instance's vocabulary beats the component's.
 * A detached probe matches no id, so every one of those rows drew a grey swatch
 * beside a green lamp: the legend disagreeing with the drawing it is a key to.
 *
 * Only consulted for a state-only mark. A mark with no state says nothing about
 * what the lamp shows, and inheriting whatever the drawing happened to be
 * painting would invent a claim the document never made.
 */
function litColor(els, state) {
  if (!state || !els.length || !els[0].isConnected) return null;
  for (const el of els) {
    const lamp = el.getAttribute('data-class') === 'led'
      ? el : el.querySelector('[data-class="led"]');
    const c = getComputedStyle(lamp || el).getPropertyValue('--led-color').trim();
    if (c) return c;
  }
  return null;
}

// A state-only mark has no colour of its own. The compiled stylesheet knows one:
// probe it rather than duplicating the palette here, so the legend cannot drift
// from what the drawing actually shows.
function stateColor(svgRoot, state) {
  if (!state || !STATE_RE.test(state) || !svgRoot.isConnected) return null;
  const probe = document.createElementNS(NS, 'g');
  probe.setAttribute(OWNED, 'probe');
  probe.setAttribute('class', `state-${state}`);
  svgRoot.appendChild(probe);
  const c = getComputedStyle(probe).getPropertyValue('--led-color').trim();
  probe.remove();
  return c || null;
}

// Appending the strip grows the drawing downwards, and sometimes sideways; the
// original box is stashed so clear() can put it back.
function mountLegend(svgRoot, doc) {
  const built = legend(svgRoot, doc);
  if (!built) return null;
  const vb = viewBox(svgRoot);
  if (!svgRoot.getAttribute(VIEWBOX))
    svgRoot.setAttribute(VIEWBOX, [svgRoot.getAttribute('viewBox') || '',
                                   svgRoot.getAttribute('height') || '',
                                   svgRoot.getAttribute('width') || ''].join('|'));
  svgRoot.setAttribute('viewBox',
    `${vb.x} ${vb.y} ${round(built.width)} ${round(vb.h + built.height)}`);
  grow(svgRoot, 'height', (vb.h + built.height) / vb.h);
  grow(svgRoot, 'width', built.width / vb.w);
  svgRoot.appendChild(built.g);
  return built;
}

// The root's width/height are millimetres with a unit; the viewBox is bare
// numbers. Scale one by the same factor as the other or the drawing prints at
// the wrong size.
function grow(svg, attr, factor) {
  const v = svg.getAttribute(attr);
  if (!v || factor === 1) return;
  const unit = v.match(/[a-z%]+$/i);
  svg.setAttribute(attr, round(parseFloat(v) * factor) + (unit ? unit[0] : ''));
}

function viewBox(svg) {
  const raw = (svg.getAttribute('viewBox') || '').trim().split(/[\s,]+/).map(Number);
  if (raw.length === 4 && raw.every(n => Number.isFinite(n)))
    return {x: raw[0], y: raw[1], w: raw[2], h: raw[3]};
  return {x: 0, y: 0, w: parseFloat(svg.getAttribute('width')) || 100,
          h: parseFloat(svg.getAttribute('height')) || 100};
}

const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n));

// The drawing's own box, ignoring a legend that may currently be mounted on it.
// A crop is a region of the HARDWARE, so it has to be measured against the
// faceplate rather than against the faceplate-plus-whatever-strip-is-showing;
// otherwise arming the crop tool with the legend on and again with it off gives
// two different rectangles for the same drag.
export function baseViewBox(svgRoot) {
  const stashed = (svgRoot.getAttribute(VIEWBOX) || '').split('|')[0];
  if (stashed) {
    const raw = stashed.trim().split(/[\s,]+/).map(Number);
    if (raw.length === 4 && raw.every(Number.isFinite))
      return {x: raw[0], y: raw[1], w: raw[2], h: raw[3]};
  }
  return viewBox(svgRoot);
}

/**
 * A crop rectangle intersected with the drawing, or null if they miss entirely.
 * Exported because a UI dragging a rectangle over the stage has to write a crop
 * the exporter will agree with, and "agree with" means one implementation.
 */
export function clampCrop(svgRoot, c) {
  const r = rect(c);
  if (!r) return null;
  const vb = baseViewBox(svgRoot);
  const x = clamp(r.x, vb.x, vb.x + vb.w), y = clamp(r.y, vb.y, vb.y + vb.h);
  const w = clamp(r.x + r.w, vb.x, vb.x + vb.w) - x;
  const h = clamp(r.y + r.h, vb.y, vb.y + vb.h) - y;
  return w > 0 && h > 0 ? {x: round(x), y: round(y), w: round(w), h: round(h)} : null;
}

// The crop is the viewBox, and width/height follow it: those two are the printed
// size in millimetres, so a third of the faceplate has to arrive in Word as a
// third of the faceplate's width and not scaled back up to fill the old one.
function crop(svgRoot, c) {
  const r = clampCrop(svgRoot, c);
  if (!r) return null;
  const vb = baseViewBox(svgRoot);
  grow(svgRoot, 'width', r.w / vb.w);
  grow(svgRoot, 'height', r.h / vb.h);
  svgRoot.setAttribute('viewBox', `${r.x} ${r.y} ${r.w} ${r.h}`);
  return r;
}

// A root viewBox already clips at the viewport, and every browser honours it.
// This is for the consumer that does not: Word has its own SVG importer, and a
// crop that silently kept the other 400mm of chassis would be discovered by
// someone else, in a document, after it was sent.
//
// The clip goes on a GROUP wrapped around the drawing, not on the root <svg>.
// clip-path on an outermost svg is resolved in the CSS box - Chrome clipped a
// 70mm crop to the top-left 70 CSS PIXELS of it, which is a nearly empty
// picture that still looks like a plausible drawing. On a group it is the
// group's own user space, which is millimetres, which is what the crop is in.
//
// Wrapped, not reparented one by one: the compiled stylesheet keys on ids,
// classes and descendant scope (`g[data-ref^='comp@'] .state-fail`) and never on
// structure, so an extra ancestor changes nothing it matches. The legend stays
// outside the wrapper - it is drawn BELOW the crop, and clipping the drawing
// must not cut off the key to it.
function clipToViewBox(svgRoot, box) {
  const cp = document.createElementNS(NS, 'clipPath');
  cp.setAttribute('id', 'portrayal-crop');
  cp.setAttribute('clipPathUnits', 'userSpaceOnUse');
  const r = document.createElementNS(NS, 'rect');
  r.setAttribute('x', box.x); r.setAttribute('y', box.y);
  r.setAttribute('width', box.w); r.setAttribute('height', box.h);
  cp.appendChild(r);

  const KEEP = new Set(['style', 'defs', 'clipPath', 'title', 'desc', 'metadata']);
  const kids = [...svgRoot.children].filter(n =>
    !KEEP.has(n.localName) && n.id !== 'portrayal-legend');
  if (!kids.length) return;
  const g = document.createElementNS(NS, 'g');
  g.setAttribute('clip-path', 'url(#portrayal-crop)');
  svgRoot.insertBefore(g, kids[0]);
  for (const k of kids) g.appendChild(k);
  svgRoot.insertBefore(cp, svgRoot.firstChild);
}

// ------------------------------------------------------------------ export

// Off-screen but LAID OUT. getBBox and getScreenCTM both answer nothing for an
// element that was never rendered, and display:none is exactly that, so the
// clone is parked out of frame rather than hidden.
function host() {
  const div = document.createElement('div');
  div.setAttribute('aria-hidden', 'true');
  div.style.cssText = 'position:fixed;left:-20000px;top:0;width:2000px;height:2000px;' +
                      'overflow:hidden;pointer-events:none;opacity:0';
  document.body.appendChild(div);
  return div;
}

/**
 * A self-contained SVG string. Deep clone, marks as concrete geometry and
 * classes, the compiled stylesheet already inline, legend appended if enabled.
 * Assume the consumer is Word: no external CSS, no script, and no CSS custom
 * properties - so var(--led-color) is resolved to a literal paint here.
 *
 * doc.crop narrows the export to one rectangle of the drawing - "I want the
 * management block, and this chassis declares no region for it". It is a field
 * of the document rather than an argument here so that a share URL reproduces
 * it and an MCP client can ask for it, which is worth more than the drag.
 *
 * @param opts.pxmm  emit width/height in pixels at this density instead of mm
 *                   (used by toPng; a rasteriser needs pixels, not millimetres)
 * @param opts.phase 0 (default) or 0.5 - which half of the blink to freeze every
 *                   behaving lamp at. toGif() asks for both; everything else
 *                   takes the lit half. The file never animates: see hold().
 */
export function toSvg(svgRoot, doc, opts = {}) {
  const d = normalise(doc);
  const clone = svgRoot.cloneNode(true);
  const box = host();
  try {
    box.appendChild(clone);
    clear(clone);                    // the source may already be previewing marks
    // Cropped BEFORE the marks go on, because the legend is laid out from the
    // viewBox: strip width, type size and the wrap column all follow the box the
    // reader will actually see, so a crop of the management block gets a legend
    // sized for the management block rather than for the whole faceplate.
    const cropped = d.crop ? crop(clone, d.crop) : null;
    apply(clone, d);
    if (cropped) clipToViewBox(clone, cropped);
    hold(clone, opts.phase);
    flatten(clone);
    clone.setAttribute('data-portrayal-markup', encode(d));
    if (opts.pxmm) {
      const vb = viewBox(clone);
      clone.setAttribute('width', Math.round(vb.w * opts.pxmm));
      clone.setAttribute('height', Math.round(vb.h * opts.pxmm));
    }
    const xml = new XMLSerializer().serializeToString(clone);
    return `<?xml version="1.0" encoding="UTF-8"?>\n` +
           `<!-- Portrayal ${[d.device, d.config, d.view].filter(Boolean).join(' ')} ` +
           `- ${d.marks.length} mark(s). Self-contained: no external CSS, no script. -->\n` +
           xml + '\n';
  } finally {
    box.remove();
  }
}

/**
 * Stop the clock on every behaving lamp and hold it at one phase of its cycle.
 * Phase 0 - lamp lit, first colour - unless asked otherwise.
 *
 * Two separate things are settled here, and the second is the reason the
 * animation does not survive an export at all.
 *
 * FLATTEN WAS BAKING AN ANIMATED VALUE. getComputedStyle reports the animated
 * value, and flatten() exists to write computed paint into attributes, so a
 * blinking lamp exported with `opacity="0.37"` and an alternating one with
 * whichever of its two colours the frame happened to be at. Arbitrary,
 * permanent, and not a state the device has.
 *
 * THE ANIMATION IS REMOVED, NOT KEPT. It is tempting to leave the @keyframes
 * running - it costs nothing and it is correct in a browser holding the file as
 * a document. Measured, it is worse than nothing: Chromium renders the same
 * exported file with the lamp LIT through a canvas and DARK in an <img>, and an
 * <img> is what a wiki, a ticket and a chat client all use. So the phase a
 * reader gets is decided by their viewer, and one of the phases they can get is
 * a picture of `off` - a documented, different, wrong state. An inline
 * `animation: none` takes that choice away from the viewer and gives the same
 * still to everyone. The blink is then carried by the ring in every static
 * export and by toGif() where it needs to actually move.
 */
const KEYFRAMES_RE =
  /\s*@keyframes\s+portrayal-(?:blink|alternate)\s*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}/g;

function hold(svg, phase = 0) {
  for (const {el, mode, alt} of behaving(svg)) {
    // The longhand, not the `animation` shorthand: the shorthand serialises as
    // `animation: auto ease 0s 1 normal none running none`, which is correct and
    // unreadable, and a reader opening the exported file should be able to see
    // at a glance that this lamp was deliberately stopped.
    el.style.setProperty('animation-name', 'none');
    if (phase < 0.5) continue;
    // The far half of the cycle, for a GIF frame. Blinking goes dark - opacity,
    // matching the keyframe, so whatever is behind the lamp shows through
    // exactly as it does on screen. Alternating takes the second colour, because
    // it never goes dark; that is the whole difference between the two.
    if (mode === 'alternating') { if (alt) el.style.fill = alt; }
    else el.style.opacity = '0';
  }
  // Nothing references them now, and they are the last var() in the file - the
  // export's standing promise is that a consumer with no CSS custom properties
  // (Word) sees exactly what a browser sees, and `fill: var(--led-color)` inside
  // a dead @keyframes block is a counterexample sitting in the evidence. Left
  // in, it also reads as an animated file to anyone who greps it, which is the
  // misunderstanding that took a day to measure the first time.
  for (const style of svg.querySelectorAll('style'))
    style.textContent = (style.textContent || '').replace(KEYFRAMES_RE, '');
}

// Word's SVG importer has no CSS custom properties and no filters. The compiled
// art paints every lamp fill="var(--led-color, #3a3f44)" and the state- classes
// work by setting that property on an ancestor - which means a straight copy of
// the classes exports a drawing where nothing lit up. Resolve the computed paint
// while the clone is still in a live document, and write it as an attribute.
function flatten(svg) {
  for (const el of svg.querySelectorAll('[fill*="var("], [stroke*="var("]')) {
    const cs = getComputedStyle(el);
    for (const prop of ['fill', 'stroke']) {
      const v = el.getAttribute(prop);
      if (v && v.includes('var(')) el.setAttribute(prop, hex(cs[prop]) || v);
    }
  }
  // .state-absent is opacity, not colour, and the same argument applies.
  for (const el of svg.querySelectorAll('[class*="state-"]')) {
    const o = getComputedStyle(el).opacity;
    if (o && o !== '1' && !el.hasAttribute('opacity')) el.setAttribute('opacity', o);
  }
}

function hex(paint) {
  const m = /^rgba?\(([^)]+)\)$/.exec(String(paint || '').trim());
  if (!m) return null;
  const [r, g, b] = m[1].split(/[\s,/]+/).map(Number);
  if (![r, g, b].every(Number.isFinite)) return null;
  return '#' + [r, g, b].map(n => clamp(Math.round(n), 0, 255).toString(16).padStart(2, '0')).join('');
}

/**
 * Rasterise the self-contained SVG at 4, 8 or 16 px/mm. Millimetres, not a
 * pixel width: the drawing is dimensioned hardware, so "8 px/mm" is a statement
 * about print resolution that holds across a 1RU switch and a 13RU chassis.
 * @returns {Promise<Blob>} image/png
 */
export async function toPng(svgRoot, doc, pxmm = 8, opts = {}) {
  const text = toSvg(svgRoot, doc, {pxmm});
  const canvas = await rasterise(text, opts);
  return await new Promise((ok, no) =>
    canvas.toBlob(b => (b ? ok(b) : no(new Error('canvas produced no PNG'))), 'image/png'));
}

// Take the size from the export itself, not from the live root: the live root
// may already be previewing a legend, and its viewBox is grown accordingly.
function pixelSize(text) {
  const w = Math.max(1, +(/\swidth="(\d+)"/.exec(text) || [])[1] || 0);
  const h = Math.max(1, +(/\sheight="(\d+)"/.exec(text) || [])[1] || 0);
  if (w * h > 1.2e8)
    throw new Error(`${w}x${h} is too large to rasterise; choose a lower px/mm`);
  return [w, h];
}

async function rasterise(text, opts = {}) {
  const [w, h] = pixelSize(text);
  const img = new Image();
  img.decoding = 'sync';
  // A data URL rather than a blob URL: the image must count as same-origin or
  // the canvas is tainted and toBlob throws.
  img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(text);
  await new Promise((ok, no) => {
    img.onload = ok;
    img.onerror = () => no(new Error('the exported SVG would not load as an image'));
  });
  const canvas = document.createElement('canvas');
  canvas.width = w; canvas.height = h;
  const ctx = canvas.getContext('2d');
  // Transparent by default - a dark chassis composites onto any page. opts
  // .background paints a flat colour under it for consumers that cannot.
  if (opts.background) { ctx.fillStyle = opts.background; ctx.fillRect(0, 0, w, h); }
  ctx.drawImage(img, 0, 0, w, h);
  return canvas;
}

// One blink is 1s at 50% duty - render.py writes `1s linear infinite` and the
// keyframes switch at 50% - so the honest animation is two frames of half a
// second. Not four or eight: nothing moves BETWEEN the phases, so extra frames
// are extra full-size raster images of a picture that has not changed.
const GIF_PHASES = [0, 0.5];
const GIF_DELAY_MS = 500;

/**
 * The drawing as an animated GIF, blink included.
 *
 * A GIF is a picture of a drawing, not the drawing: no data-path, no
 * data-states, nothing addressable, no text a reader can select and no
 * resolution beyond the one it was baked at. It is here because it is the only
 * format that shows a blinking lamp blinking to an audience - a slide, a ticket,
 * a chat message - and it belongs beside SVG and PNG rather than in front of
 * them. The SVG remains the interchange format and the thing worth keeping.
 *
 * Frames are cut down to the rectangle that actually changed, which for a
 * faceplate whose only motion is two 2mm lamps is a few hundred pixels against
 * a few million.
 *
 * @param opts.background flat colour under the drawing (default white - GIF
 *                        transparency is one bit, and a chassis with antialiased
 *                        edges composited against it fringes badly)
 * @returns {Promise<{blob: Blob, width, height, frames: number, delay: number}>}
 */
export async function toGif(svgRoot, doc, pxmm = 4, opts = {}) {
  const {encodeGif} = await import('./gif.js');
  const bg = opts.background || '#ffffff';
  // Both phases are built first and compared as strings: a drawing with nothing
  // behaving produces two identical files, and that is the cheapest possible
  // test for "this is a still picture" - no rasterising, no pixel diff.
  const texts = GIF_PHASES.map(phase => toSvg(svgRoot, doc, {pxmm, phase}));
  const still = texts[0] === texts[1];
  const frames = [];
  for (const text of still ? texts.slice(0, 1) : texts) {
    const canvas = await rasterise(text, {background: bg});
    frames.push(canvas.getContext('2d')
      .getImageData(0, 0, canvas.width, canvas.height).data);
  }
  const [width, height] = pixelSize(texts[0]);
  const bytes = encodeGif({width, height, frames, delay: GIF_DELAY_MS});
  return {blob: new Blob([bytes], {type: 'image/gif'}),
          width, height, frames: frames.length, delay: GIF_DELAY_MS, still};
}

// ------------------------------------------------------------------ URL codec

// The document, small enough to live in a location hash. Two steps: a positional
// form that drops keys and defaults, then a substitution table for the handful
// of selector prefixes that every Portrayal document repeats. Base64url last, so
// the result survives a hash without percent-encoding and a label in any script
// round-trips. Synchronous on purpose - a hashchange handler should not have to
// await a compression stream.
const TOKENS = [
  ['[data-path=\'', '\x01'],
  ['[data-class=\'', '\x02'],
  ['[data-speed=\'', '\x03'],
  ['[data-media=\'', '\x04'],
  ['[data-group=\'', '\x05'],
  ['[data-function=\'', '\x06'],
  ['\']', '\x07'],
  ['","', '\x0e'],
  ['"],["', '\x0f'],
];
const PREFIX = 'm1.';

export function encode(doc) {
  const d = normalise(doc);
  // trailing empties are dropped: most marks are a selector and a colour
  // Appended, like the crop below and for the same reason: a share URL written
  // before lamp colours existed decodes with m[5] undefined, which is exactly
  // "no lamp colour", and trimTail keeps the common mark at two slots.
  const marks = d.marks.map(m => trimTail([m.select, m.color, m.state, m.label, m.id, m.lamp]));
  // Appended, not inserted: a share URL written before either of these existed
  // decodes with a[6] undefined, which is exactly "no crop", and an object
  // legend rides in slot 4 where the boolean was.
  const cropped = d.crop ? [d.crop.x, d.crop.y, d.crop.w, d.crop.h] : 0;
  const a = [1, d.device, d.config, d.view,
             d.legend && typeof d.legend === 'object' ? d.legend : (d.legend ? 1 : 0),
             marks, cropped];
  // Slot 7, and ONLY WHEN THERE IS ONE - trimTail's convention for the marks,
  // applied to the document. A link written before swaps existed has no slot 7
  // and decodes to `{}`, and an un-swapped document encodes to exactly the bytes
  // it did before, so every link already shared stays the link it was. Keys are
  // sorted so one state is one string.
  const sorted = o => Object.keys(o).sort((x, y) => x < y ? -1 : x > y ? 1 : 0);
  const swapKeys = sorted(d.swaps);
  const fieldPaths = sorted(d.fields);
  // Slot 8, the fields, by the same rule. A document with fields and no swaps
  // still needs a slot 7 to stand in front of it, and it is 0 - the value an
  // un-cropped slot 6 already uses, which decode reads as no swaps - so every
  // link without fields keeps its bytes.
  if (swapKeys.length) a.push(Object.fromEntries(swapKeys.map(k => [k, d.swaps[k]])));
  else if (fieldPaths.length) a.push(0);
  if (fieldPaths.length)
    a.push(Object.fromEntries(fieldPaths.map(p =>
      [p, Object.fromEntries(sorted(d.fields[p]).map(k => [k, d.fields[p][k]]))])));
  const json = JSON.stringify(a);
  let packed = json;
  for (const [long, short] of TOKENS) packed = packed.split(long).join(short);
  return PREFIX + b64url(packed);
}

export function decode(input) {
  let s = str(input);
  if (s.startsWith('#')) s = s.slice(1);
  if (!s) return null;
  // A raw JSON document typed into the hash arrives percent-encoded - every
  // browser escapes the quotes - so the debugging path this branch exists for
  // never once worked from the address bar. base64url has no '%' in its
  // alphabet, so decoding here cannot damage the compact form.
  if (s.includes('%')) { try { s = decodeURIComponent(s); } catch (e) { /* leave it */ } }
  if (!s) return null;
  try {
    if (s.startsWith('{')) return normalise(JSON.parse(s));   // raw JSON, for MCP and debugging
    if (!s.startsWith(PREFIX)) return null;
    let packed = unb64url(s.slice(PREFIX.length));
    for (const [long, short] of TOKENS) packed = packed.split(short).join(long);
    const a = JSON.parse(packed);
    if (!Array.isArray(a) || a[0] !== 1) return null;
    const c = Array.isArray(a[6]) ? {x: a[6][0], y: a[6][1], w: a[6][2], h: a[6][3]} : null;
    return normalise({
      v: 1, device: a[1], config: a[2], view: a[3],
      legend: a[4] && typeof a[4] === 'object' ? a[4] : a[4] !== 0,
      crop: c,
      marks: (a[5] || []).map(m => ({select: m[0], color: m[1], state: m[2],
                                     label: m[3], id: m[4], lamp: m[5]})),
      swaps: a[7],                   // absent on an older link: normalise gives {}
      fields: a[8],                  // likewise; 0 in slot 7 when only fields are set
    });
  } catch (e) {
    return null;                     // a truncated or hand-edited hash is not fatal
  }
}

function trimTail(a) {
  const out = a.slice();
  while (out.length && !out[out.length - 1]) out.pop();
  return out;
}

function b64url(s) {
  const bytes = new TextEncoder().encode(s);
  let bin = '';
  for (let i = 0; i < bytes.length; i += 0x8000)          // apply() has an arg limit
    bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function unb64url(s) {
  const bin = atob(s.replace(/-/g, '+').replace(/_/g, '/'));
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new TextDecoder().decode(bytes);
}

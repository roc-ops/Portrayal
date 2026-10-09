// What does a compiled drawing say about its own indicators, and what does it
// fail to say?
//
// Everything here reads a drawing and answers questions about it. Nothing here
// builds HTML, touches `document`, or knows that a page exists - the drawing is
// always passed in, as an <svg> root or as an element inside one. That is the
// whole boundary: the annotate page asks these questions to decide which lamps
// get a colour picker, and the gaps register asks the same questions offline to
// decide which devices owe a `port-led-semantics` entry. Two consumers, one set
// of answers.
//
// Two answers here are expensive enough to cache - the scan of a drawing's
// stylesheet, and whether a given state changes a given element's computed
// style - and both are true only of the drawing they were measured on. In the
// page these were plain variables that annotate reset by hand on every `load`,
// which worked because annotate is one drawing at a time and remembered to. A
// library cannot ask that: a consumer holding two drawings, or one that never
// fires a load event, would be handed the first drawing's answers about the
// second, silently, and a wrong "no CSS" reads exactly like a real gap in the
// model. So the caches hang off the SVG ROOT in a WeakMap and cannot be asked
// the wrong drawing's question; a drawing that is dropped takes its cache with
// it, and nobody has to remember anything.

// ------------------------------------------------------------------ vocabulary

/** The stylesheet's own state names, for a state no rule declares here. */
export const GLOBAL_STATES = ['up', 'activity', 'ok', 'fault', 'fail', 'locate', 'absent'];

// Every LED component in the library declares `states: ['off','on']` and nothing
// else, because a lamp can only know that it is a lamp. What it MEANS is a
// per-device, per-function fact that lives in the device manifest.
const DEFAULT_VOCAB = ['off', 'on'];

const TOKEN = /^[a-z0-9-]+$/;

// `states:` accepts a bare string and several contracts have put a description
// where the name goes - "Green = OK, Amber = fault". Splitting that on spaces
// offers chips called "=" and "OK," that set classes nothing paints, so a value
// that is not a list of tokens gets no states rather than garbage ones.
/** The state vocabulary one element admits, or [] if it does not carry one. */
export function statesOfEl(el) {
  // dataset where the element has one (a consumer may hand a plain
  // {dataset} object, as messagesOfEl takes), the attribute where it does not
  const raw = (el?.dataset?.states ?? el?.getAttribute?.('data-states') ?? '').trim();
  if (!raw) return [];
  const toks = raw.split(/[\s,]+/);
  return toks.every(t => TOKEN.test(t)) ? toks : [];
}

// A DISPLAY IS NOT A LAMP. `states` answers "what colour can this be", and a
// four-character LED matrix reading INIT, BOOT or PSEQ answers "what can this
// say" - a vocabulary of strings, which no list of colours expresses. The two
// ride separate attributes for a reason visible right above: statesOfEl throws
// away a data-states that is not a list of tokens, so words put there would be
// dropped silently, and a display that knows twenty-eight readings would read as
// a display that knows nothing.
//
// A reading carries no whitespace - the schema enforces it - so one attribute
// holds the whole vocabulary and splitting on spaces is exact.
/** The readings one display admits, or [] if it does not carry any. */
export function messagesOfEl(el) {
  const raw = (el?.dataset?.messages || '').trim();
  return raw ? raw.split(/\s+/) : [];
}

// Capacity, which is what makes a reading checkable: a five-character string on
// a four-character matrix is a transcription error nobody can see by looking.
/** How many character cells a display has, or 0 where it does not say. */
export function charactersOfEl(el) {
  const n = Number.parseInt(el?.dataset?.characters ?? '', 10);
  return Number.isInteger(n) && n > 0 ? n : 0;
}

// ---------------------------------------------------------------- addressing

const rootOf = el => el?.ownerSVGElement || (el?.tagName === 'svg' ? el : null);

/** Resolve a selector to one element, or null if it matches nothing or is invalid. */
export function firstMatch(svg, sel) {
  try { return svg ? svg.querySelector(sel) : null; } catch (e) { return null; }
}

// one pass over the drawing rather than one query per tree row: the AS7946's
// front face is 3600 elements and its tree is 200 rows
/** data-path -> the first element carrying it. */
export function pathIndex(svg) {
  const byPath = new Map();
  if (!svg) return byPath;
  for (const e of svg.querySelectorAll('[data-path]')) {
    const p = e.getAttribute('data-path');
    if (!byPath.has(p)) byPath.set(p, e);
  }
  return byPath;
}

// ------------------------------------------------- an outlet and its lamps

// A STATE SET ON AN OUTLET IS SHOWN ON ITS LAMP (#934, docs/pdu-model-design.md
// section 3.2). A switched PDU's outlet declares `[on, off]`, and the lamp that
// says so is a part of its own, placed beside it with `for:` naming the outlet,
// because the outlet is the plain `std/c13-outlet@1` and contains no lamp. A
// user switches off A1, not the lamp beside it, and a rack file keys by the
// outlet's path - so a state applied to the outlet's path has to reach the
// lamp too, and it has to reach it the same way in every place a state is
// applied: the marks document (marks.js apply), the Explorer's chips, and the
// 3D scene (relief.js applyNodeStates, viewer3d.js setStates). This is the one
// rule they all ask, so the 2D drawing and the 3D scene cannot disagree.
//
// THE BINDING. An element follows a path when its `data-for` names that path
// AND it declares a state vocabulary of its own: a lamp. Other things carry
// `data-for` too - a seated occupant (a `generic/c14-plug@1` in the outlet
// names the outlet it occupies) and silkscreen marks - and they declare no
// states, so they are left alone.
//
// AND THE PATH IS AN OUTLET'S: the element named declares a state vocabulary
// itself. A port names no states (its lamps do), so a state written on a
// port's path - which already lights the jack's own lamps through the
// inherited --led-color - does not start reaching the lamps drawn beside it.
// Across the library on 2026-10-09 no element that declares states had a lamp
// bound to it, so this rule moves nothing that was already drawn.
//
// `for:` is written as a placement id and `data-for` carries it bare; a
// cross-view target gets a leading slash and names another drawing, which
// this one cannot apply anything to - and no data-path begins with a slash,
// so it finds nothing here. So the binding reaches top-level
// placements in the drawing at hand, which every PDU in scope is.
/**
 * Every lamp a drawing binds to an element that declares states.
 * @param root  an <svg>, or any element whose subtree is the drawing (a
 *              parsed face in 3D)
 * @returns {Map<string, Element[]>} the named element's data-path -> its lamps
 */
export function boundLamps(root) {
  const out = new Map();
  if (!root) return out;
  let owners = null;
  for (const lamp of root.querySelectorAll('[data-for][data-states]')) {
    if (!lamp.getAttribute('data-path') || !statesOfEl(lamp).length) continue;
    owners = owners || pathIndex(root);
    for (const t of (lamp.getAttribute('data-for') || '').split(/\s+/)) {
      const src = owners.get(t);
      if (!src || src === lamp || !statesOfEl(src).length) continue;
      if (!out.has(t)) out.set(t, []);
      if (!out.get(t).includes(lamp)) out.get(t).push(lamp);
    }
  }
  return out;
}

/**
 * The outlet-to-lamp expansion: a `{path: classes}` state map in which every
 * lamp bound to a stated path takes that path's classes - unless the map
 * states the lamp itself, which then wins. The one function the 2D chips, the
 * 3D scene and a rack entry's `states` apply a map through.
 *
 * @param map       {path: classes} or a Map of the same; empty values are dropped
 * @param bindings  what boundLamps returns, or a Map of path -> lamp paths
 * @returns {Object<string, string>} a new map; the input is not touched
 */
export function expandStates(map, bindings) {
  const entries = map instanceof Map ? [...map] : Object.entries(map || {});
  const out = {};
  for (const [p, c] of entries) if (c) out[p] = String(c);
  for (const [p, c] of entries) {
    if (!c) continue;
    for (const lamp of bindings?.get(p) || []) {
      const lp = typeof lamp === 'string' ? lamp : lamp?.getAttribute?.('data-path');
      if (lp && !(lp in out)) out[lp] = String(c);
    }
  }
  return out;
}

// WHAT `off` ON A CHIP MEANS (#934). `off` used to be the absence of a state,
// and a chip for it cleared the element: right while every lamp's off was
// unlit, and wrong for one whose device declares a colour for it - the G4
// outlet lamp is red when its outlet is off (the G4 brochure), and a cleared
// lamp draws unlit. So `off` is set as a state - `state-off` on the element -
// when that element is an outlet (it has a lamp bound to it, whose declared off
// colour, if any, then shows; or it is a power outlet with none, which the
// base stylesheet dims), or when the element declares a colour for `off`
// itself. Only a lamp or a plain element with no declared off colour is
// cleared, which is what it always was.
/**
 * Does the `off` chip on this element set `state-off` (true) or clear (false)?
 * @param el     the element the chip is on
 * @param lamps  the lamps bound to it (boundLamps(svg).get(path))
 */
export function offIsSet(el, lamps = []) {
  if (!el || !statesOfEl(el).includes('off')) return false;
  if (lamps.length) return true;
  if (el.getAttribute('data-class') === 'inlet') return true;
  return declaredHere(el, 'off');
}

// -------------------------------------------------------------- does it paint

// Which states does the drawing actually PAINT? Applying a state only changes
// what you see if the stylesheet has a rule for it, and several components
// declare states nobody wrote CSS for - the AGR400's port LEDs offer `link`,
// and `state-link` sets a class no rule matches. Rather than hardcode render.py's
// list (which per-component `palette:` extends anyway), ask the drawing.
//
// Asked the wrong way, this lies. The first version parked an empty <g> beside
// the element and put the class on THAT, which cannot answer for the rules
// render.py emits self-scoped:
//
//   #mgmt--led-left.state-link-1g { --led-color: #22c55e; }
//
// id and class on the same element. A stand-in with no id matches nothing of
// the sort, so it reported "no CSS" for states that work perfectly - and the
// asymmetry is invisible from here: a placement-level state emits both forms
// (`#led-gnss.state-learning, #led-gnss .state-learning`) while an element-level
// state inside a group override emits only the self form.
//
// So the question is put to the element itself. Its own state- classes come off
// for the two readings and go back on immediately, synchronously, before
// anything can observe them - there is no await between them and no layout is
// forced, only style. That is exact for both forms and for anything a future
// palette invents, where any stand-in is a guess about what the selector needed.
const PAINT_CACHE = new WeakMap();
const PROPS = ['--led-color', '--led-color-alt', 'opacity', 'fill', 'stroke',
               'filter', 'animation-name'];

/** True when applying `state-<st>` to this element changes what is drawn. */
export function paints(el, st) {
  if (!el || !st) return true;
  // `off` is unlit unless the device declares a colour for it (#934: the G4
  // outlet lamp is red when its outlet is off). Undeclared, it has no rule of
  // its own and needs none - an unlit lamp is what the skin's own fill
  // fallback already draws - so it is reported as painting without asking. A
  // declared off is a colour like any other and is measured below, so a red
  // off is reported as painting because it does.
  if (st === 'off' && !declaredHere(el, 'off')) return true;
  // Self-scoped rules are keyed on the id, so the id is the cache key wherever
  // there is one. Without an id the answer can only come from inherited scope -
  // `g[data-ref^='ufispace/psu-401-dc@'] .state-fail` - which varies by the
  // component and by the element's own class and nothing else.
  let ref = '';
  for (let p = el; p && p.nodeType === 1 && !ref; p = p.parentNode)
    ref = p.getAttribute('data-ref') || '';
  const key = el.id ? `${st}|#${el.id}`
                    : `${st}|${ref}|${el.getAttribute('data-class') || ''}|${el.tagName}`;
  const root = rootOf(el);
  let cache = PAINT_CACHE.get(root);
  if (!cache) PAINT_CACHE.set(root, cache = new Map());
  if (cache.has(key)) return cache.get(key);

  const read = () => {
    const cs = getComputedStyle(el);
    return PROPS.map(p => cs.getPropertyValue(p).trim()).join('|');
  };
  const mine = [...el.classList].filter(c => c.startsWith('state-'));
  el.classList.remove(...mine);
  const base = read();
  el.classList.add('state-' + st);
  const lit = read();
  el.classList.remove('state-' + st);
  if (mine.length) el.classList.add(...mine);
  const ok = base !== lit;
  cache.set(key, ok);
  return ok;
}

// ------------------------------------------------- documented vs. undocumented

// Which lamps does the model actually have something to say about?
//
// A lamp still carrying exactly off/on is one whose device said nothing: the
// S9510-28DC's HIG has LED tables for GNSS, SYNC, STAT, FAN, PWR, the PSU and
// fan FRUs and the management jack, and no table at all for the port lamps, and
// its thirty port lamps sit on that default as a result.
//
// That is the case a colour picker exists for, and the case it must be confined
// to. `led-pwr`'s off/ok/bmc-power-fail/cpu-power-fail was transcribed from a
// vendor table; offering to recolour it would turn a fact into a preference and
// put a false picture into an export.
//
// The literal pair is NOT the whole test, because a device may one day declare
// exactly off and on out of a real document. Two questions are asked:
//
//   1. Is the vocabulary anything other than the components' off/on default?
//      Any override - at the placement, at the group, or in the contract's own
//      element - lands in data-states, so a longer or different list is somebody
//      having written something down.
//   2. Failing that, does the drawing carry a rule that paints one of these
//      states FOR THIS LAMP IN PARTICULAR? render.py emits a declared colour as
//      `#lamp-id.state-on` or `g[data-ref^='common/led-dot@'] .state-on`; the
//      base stylesheet's own `.state-on { --led-color:#22c55e }` is the generic
//      fallback that every undocumented lamp in the library gets. A scoped rule
//      means a colour was declared, which means somebody read a table.
//
// Today no device in the library declares a coloured off/on, so (2) never fires
// and (1) carries the whole boundary. It is here because the day it does fire is
// the day the literal-pair test would start lying, silently, in an export.
const RULE_CACHE = new WeakMap();

/** The scoped state rules this drawing carries: [{state, sel}, ...]. */
export function stateRules(svg) {
  if (!svg) return [];
  const hit = RULE_CACHE.get(svg);
  if (hit) return hit;
  const found = [];
  for (const style of svg.querySelectorAll('style')) {
    let rules;
    try { rules = style.sheet && style.sheet.cssRules; } catch (e) { rules = null; }
    for (const rule of rules || []) {
      if (!rule.selectorText) continue;
      for (const part of rule.selectorText.split(',')) {
        const st = /\.state-([a-z0-9-]+)/.exec(part);
        // '#' and '[data-ref' are the only two scopes render.py emits for a
        // declared colour. Not any attribute selector: the base sheet's own
        // `.state-fail[data-class='psu']` is a drop-shadow every PSU gets, and
        // reading that as a declaration would call every default PSU documented.
        if (st && (part.includes('#') || part.includes('[data-ref')))
          found.push({state: st[1], sel: part.trim()});
      }
    }
  }
  RULE_CACHE.set(svg, found);
  return found;
}

// Does a rule declared for this element in particular paint `st`? Asked by
// putting the class on the element and letting the browser answer, for the same
// reason paints() does: a stand-in element cannot match a self-scoped selector.
/** True when this drawing declares a colour for `st` on this element. */
export function declaredHere(el, st) {
  if (!el) return false;
  const cands = stateRules(rootOf(el)).filter(r => r.state === st);
  if (!cands.length) return false;
  const had = el.classList.contains('state-' + st);
  if (!had) el.classList.add('state-' + st);
  const hit = cands.some(r => { try { return el.matches(r.sel); } catch (e) { return false; } });
  if (!had) el.classList.remove('state-' + st);
  return hit;
}

/** True when this element is a lamp whose meaning the model does not record. */
export function undocumented(el) {
  if (!el || el.getAttribute('data-class') !== 'led') return false;
  const sts = statesOfEl(el);
  if (sts.length !== DEFAULT_VOCAB.length ||
      !DEFAULT_VOCAB.every(s => sts.includes(s))) return false;
  return !sts.some(st => declaredHere(el, st));
}

// The interesting way to colour thirty undocumented lamps is not thirty pickers
// - it is one rule with one picker on it. "The same rule" has to mean the same
// rule, though. A selector reaching a mix - say [data-class='led'] on the S9510,
// which is thirty silent port lamps AND the PWR lamp whose four states came off
// a vendor table - is not a place the model is silent, and one control there
// would recolour the transcribed ones along with the rest. So a census, and the
// caller offers the control only where the whole selection is undocumented.
/** How many lamps a selector reaches, split by whether the model documents them. */
export function lampCensus(svg, select) {
  const c = {undoc: 0, doc: 0};
  if (!select || !svg) return c;
  let els;
  try { els = svg.querySelectorAll(select); } catch (e) { return c; }
  for (const el of els) {
    if (el.getAttribute('data-class') !== 'led' || !statesOfEl(el).length) continue;
    if (undocumented(el)) c.undoc++; else c.doc++;
  }
  return c;
}

/** True when EVERY lamp this selector reaches is one the model says nothing about. */
export function lampable(svg, select) {
  const c = lampCensus(svg, select);
  return c.undoc > 0 && c.doc === 0;
}

// ------------------------------------------------------------------- choices

// What a given lamp can be set to, as facts rather than as markup. The caller
// renders it - a <select>, a row of chips, a column in a report - and the split
// this returns is the part every caller needs identically: which states this
// selector's own model declares, which of those the stylesheet actually paints,
// which the stylesheet knows but this drawing never claimed, and whether the
// value in hand is in neither list.
//
// `cur` is included rather than filtered against, because a state typed into a
// share URL or sent by an MCP client has to remain visible as the current value
// even when it is unknown here. Silently dropping it would show the user a
// different state than the document holds.
/**
 * @param svg     the drawing
 * @param select  the selector the states will be applied to
 * @param states  the vocabulary declared for it (an element's data-states)
 * @param cur     the state currently set, if any
 * @returns {{declared: {name, paints}[], global: string[], unknown: string|null}}
 */
export function stateChoices(svg, select, states, cur) {
  const el = firstMatch(svg, select);
  const declared = (states || []).map(name => ({name, paints: paints(el, name)}));
  const names = declared.map(d => d.name);
  const global = GLOBAL_STATES.filter(s => !names.includes(s));
  const unknown = cur && !names.includes(cur) && !global.includes(cur) ? cur : null;
  return {declared, global, unknown};
}

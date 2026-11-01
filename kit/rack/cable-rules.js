// THE CABLE RULES. Pure: no DOM, no fetch, so the page, the side
// panel and `node --test` all read one definition. A rule that says no gives
// a sentence, in the style of fit.js.
//
// A cable is `{id, a, b, media, purpose, label, length?, color?, route}`; an END is
// {item, path, view}: the item's id, the port's data-path, and the device's
// OWN panel ('front' or 'rear') the port is on - not the pane that shows it.

import {nextId, positionOf, cableIdsInUse, withoutMembers, zeroUById, endPaneIn} from './model.js';
import {hexColor, cableColor} from './cable-geometry.js';

// ── ends ────────────────────────────────────────────────────────────────
export const endKey = end => `${end.item}|${end.view}|${end.path}`;
// One PORT, however its path is spelled: a click on a seated optic or its plug
// (`port-1-occupant/tx`) is a click on `port-1`. endKey stays exact.
const portKey = end => `${end.item}|${end.view}|${portPathOf(end.path)}`;
export const sameEnd = (a, b) => portKey(a) === portKey(b);

// WHICH PANE SHOWS A DEVICE'S PANEL: the inverse of elevation.js's panelFor.
// A device's front is on the face it is mounted on, unless it is turned.
const OTHER = {front: 'rear', rear: 'front'};
export const paneOf = (item, view) => (((view === 'front') !== !!item.turned) ? item.face : OTHER[item.face]);

// THE PORT A CLICKED PATH BELONGS TO. A seated optic and its plugs are drawn
// beside their cage, at `<port>-occupant` and below it, so a click on either
// is a click on the port: everything from the first `-occupant` on is dropped.
export const portPathOf = path => String(path).split('-occupant')[0];

const itemOf = (rack, end) => rack.items.find(i => i.id === end.item) || null;
// An end as a person reads it. Labels repeat (two "demarc"), so the U is in it:
// the device's POSITION (model.js positionOf), the U every export gives it.
// That needs the device's height, which the rack does not store: `uOf(item)`
// answers it in U. Without one, an item that carries its height (`u`, as
// fit.js itemsWithU's do) is read as it is, and any other counts as 1U.
export const carriedU = item => item.u ?? 1;
// An end on a part beside the rack (a zero-U PDU's outlet, P-0019) is named
// by the part and where it stands: "PDU-A (left-rear) outlet-a2".
export function endName(rack, end, uOf = carriedU) {
  const it = itemOf(rack, end);
  if (it) return `${it.label} (U${positionOf(rack.frame, it.ru, uOf(it) ?? 1)}) ${end.path}`;
  const z = zeroUById(rack, end.item);
  return z ? `${z.label || z.id} (${z.at}) ${end.path}` : `a removed device's ${end.path}`;
}
export const cableName = c => c.label || c.id;
const clip = (s, n) => { const cs = Array.from(s); return cs.length > n ? `${cs.slice(0, n - 1).join('')}…` : s; };
// A PORT AS A PERSON READS IT (#1032): its address without the spelling a
// reader of the file needs. A port on a seated part is `<bay>/module/<part>`,
// and `bay-1/module/b09` says no more to a person than "bay 1 b09"; a click on
// a seated optic or its plug is a click on the port. queries.js freePorts
// gives the same text as a port's `label`.
export const portLabel = path => portPathOf(path).split('/module/').join(' ').replace(/[-/]/g, ' ');
// The text of a cross-face tag: the far end, short enough for the side column.
export function tagText(rack, end) {
  const it = itemOf(rack, end) ?? zeroUById(rack, end.item);
  return clip(`→ ${it ? it.label || it.id : 'removed'} ${portLabel(end.path)}`, 32);
}

// ── one cable per port ──────────────────────────────────────────────────
// `uOf` is endName's: how tall a device is, for the U in the refusal.
// `dc` is the DC reader (ports.js dcReader), optional: end -> {key, pole, name}
// for an end on a DC port, a pole or the connector of a points port, else null.
// With it a port, each of its poles and its connector are one place
// (docs/dc-power-design.md section 5.4): a cable on the port takes every pole,
// a cable on one pole makes the port partly used, and two poles are two places.
// Without it, a port is its path alone, as it was.
export function portFree(rack, end, {ignoreId = null, uOf, dc = null} = {}) {
  const k = portKey(end);
  const other = (rack.cables || []).find(c => c.id !== ignoreId && (portKey(c.a) === k || portKey(c.b) === k));
  if (other) return {ok: false, reason: `${endName(rack, end, uOf)} already has a cable (${cableName(other)}).`};
  const mine = typeof dc === 'function' ? dc(end) : null;
  if (mine) for (const c of rack.cables || []) {
    if (c.id === ignoreId) continue;
    for (const e of [c.a, c.b]) {
      const o = dc(e);
      if (!o || o.key !== mine.key || !(o.pole === null || mine.pole === null || o.pole === mine.pole)) continue;
      // (naming the pole it is on where this end asks for the whole port)
      const where = o.pole !== null && mine.pole === null ? ` on its ${o.name}` : '';
      return {ok: false, reason: `${endName(rack, end, uOf)} already has a cable (${cableName(c)}${where}).`};
    }
  }
  return {ok: true};
}
export function canCable(rack, a, b, opts = {}) {
  if (sameEnd(a, b)) return {ok: false, reason: 'A cable needs two different ports.'};
  // a port and one of its own poles are the same place
  if (typeof opts.dc === 'function') {
    const x = opts.dc(a), y = opts.dc(b);
    if (x && y && x.key === y.key) return {ok: false, reason: 'A cable needs two different ports.'};
  }
  for (const e of [a, b]) { const f = portFree(rack, e, opts); if (!f.ok) return f; }
  return {ok: true};
}

// ── edits: each returns a new rack ──────────────────────────────────────
// An end keeps the plug it states (`plug`, below: THE PLUG AT AN END) and nothing else.
const endOf = e => ({item: e.item, path: e.path, view: e.view === 'rear' ? 'rear' : 'front',
  ...(typeof e.plug === 'string' && e.plug ? {plug: e.plug} : {})});
// `color` is the cable's own colour, as hexColor reads one; anything else is
// left off (the commands refuse a value that is no colour before this).
export function withCable(rack, {a, b, media = '', purpose = '', label = '', length = null, color = null}) {
  const cable = {id: nextId(cableIdsInUse(rack), 'c'), a: endOf(a), b: endOf(b), media, purpose, label,
                 ...(length ? {length} : {}), ...(hexColor(color) ? {color: hexColor(color)} : {}), route: []};
  return {rack: {...rack, cables: [...(rack.cables || []), cable]}, cable};
}
// `length: null` in the patch removes the length; anything else is merged.
// A patch that names the length at all - a value, or null - is the user
// setting or clearing it, and that replaces a length the loader kept as
// written (model.js `lengthAsWritten`); a patch that does not name it leaves
// both as they are.
// Similarly, a patch that names the route replaces what was written (model.js
// `routeAsWritten`); a patch that does not name it leaves both as they are.
// `color: null` removes the cable's own colour, and a patch that names the
// colour at all replaces one the loader kept as written (`colorAsWritten`).
export function updateCable(rack, id, patch) {
  return {...rack, cables: (rack.cables || []).map(c => {
    if (c.id !== id) return c;
    const next = {...c, ...patch};
    for (const [k, v] of Object.entries(patch)) if (v === undefined) delete next[k];   // undefined removes the key
    if (Object.hasOwn(patch, 'length')) delete next.lengthAsWritten;
    if (Object.hasOwn(patch, 'route')) delete next.routeAsWritten;
    if (Object.hasOwn(patch, 'color')) delete next.colorAsWritten;
    if (next.length == null) delete next.length;
    if (next.color == null) delete next.color;
    return next;
  })};
}
// A removed cable leaves its bundle too (model.js withoutMembers).
export const withoutCable = (rack, id) =>
  withoutMembers({...rack, cables: (rack.cables || []).filter(c => c.id !== id)}, [id]);
export const cablesOf = (rack, itemId) =>
  (rack.cables || []).filter(c => c.a.item === itemId || c.b.item === itemId);
export const withoutCablesOf = (rack, itemId) =>
  withoutMembers({...rack, cables: (rack.cables || []).filter(c => c.a.item !== itemId && c.b.item !== itemId)},
                 cablesOf(rack, itemId).map(c => c.id));

// ── length ──────────────────────────────────────────────────────────────
export const UNITS = ['m', 'ft'];
export function parseLength(text, unit = 'm') {
  const t = String(text ?? '').trim();
  if (!t) return {ok: true, length: null};
  const value = /^\d+(\.\d+)?$/.test(t) ? Number(t) : NaN;   // a plain decimal, not 0x10 or 1e3
  if (!Number.isFinite(value) || value <= 0) return {ok: false, reason: 'Enter a length above 0, or leave it empty.'};
  return {ok: true, length: {value, unit: UNITS.includes(unit) ? unit : 'm', source: 'entered'}};
}
// Value and unit as the cable has them: a unit this page does not offer (a
// file's 'cm' or 'yd') prints as itself.
// ONE rule for every file and screen: a usable length is a finite number above
// 0, with the unit it was given (m when none); anything else is not set.
export const lengthParts = l => (l && typeof l.value === 'number' && Number.isFinite(l.value) && l.value > 0
  ? {value: l.value, unit: l.unit || 'm'} : null);
export const lengthText = l => { const p = lengthParts(l); return p ? `${p.value} ${p.unit}` : ''; };

// ── colour (#1028) ──────────────────────────────────────────────────────
// A CABLE'S OWN COLOUR, as a form or a command gives it: empty or null is no
// colour of its own (the ends, the type or the media then decide), `#rgb` or
// `#rrggbb` is that colour, written `#rrggbb` in lower case, and anything
// else is refused with a sentence. Nothing here draws a value that is no
// colour: a name such as "red" is not guessed at, and never becomes black.
export const COLOR_REFUSED = 'A cable color is # and three or six hex digits, such as #2bb3c8, or empty for none of its own.';
export function parseColor(value) {
  if (value == null || (typeof value === 'string' && !value.trim())) return {ok: true, color: null};
  const color = hexColor(value);
  return color ? {ok: true, color} : {ok: false, reason: COLOR_REFUSED};
}

// WHAT DECIDES A CABLE'S COLOUR, as the keys cable-geometry.js cableColor
// reads, and only the keys that say something:
//   `color`    the cable's own, when it states one;
//   jackets    [end a's, end b's], when `jacketOf` is given and either end
//              states one: `jacketOf(end)` is the jacket colour the part
//              seated at that end states, or null (ports.js jacketsFor
//              makes it from the page's cable facts and the catalogue);
//   typeColor  its named type's, when `typeColorOf(cable)` gives one
//              (cable-types.js jacketLookup).
// A cable none of them speaks for has no key here, and is coloured by its
// media as it always was. Neither reader is asked for a cable that states
// its own colour: nothing they could answer would be drawn.
export function colorFacts(cable, {jacketOf = null, typeColorOf = null} = {}) {
  const own = hexColor(cable?.color);
  if (own) return {color: own};
  const jackets = typeof jacketOf === 'function' ? [cable.a, cable.b].map(e => hexColor(jacketOf(e))) : [];
  const typeColor = typeof typeColorOf === 'function' ? hexColor(typeColorOf(cable)) : null;
  return {...(jackets.some(Boolean) ? {jackets} : {}), ...(typeColor ? {typeColor} : {})};
}
// `{color, from}` of one cable of a rack, by the same order: what every drawing,
// list and export of it shows. `from` is 'cable', 'ends', 'type' or 'media'.
export const cableColorOf = (cable, readers = {}) =>
  cableColor({media: cable?.media || 'unset', purpose: cable?.purpose || '', ...colorFacts(cable, readers)});
// EVERY CABLE'S COLOUR AS ONE TEXT, for a view that draws the cables once and
// keeps them (the 3D scene): two racks that give the same text are drawn in
// the same colours. sameCables3d sees a cable's own colour change; a jacket
// set on a seated end, or a table of types loaded later, changes no cable, so
// a view that passes `jacketOf` or `typeColorOf` compares this as well.
export const colorsKey = (rack, readers = {}) =>
  (rack.cables || []).map(c => `${c.id}=${cableColorOf(c, readers).color}`).join(' ');

// ── the plan cables.js draws ────────────────────────────────────────────
// The rack's cables in the shape drawCables2d takes: an end is [item id,
// path, PANE]. An end whose device is gone is on no pane ('none'), so the
// drawer hangs the other end as an unplugged lead. A cable with no media is
// 'unset', which cables.js colours neutral.
// A LINK CARRIES WHAT DECIDES ITS COLOUR (colorFacts above): `color`,
// `jackets` and `typeColor`, each only when it says something, so that
// cable-geometry.js colorOf(link) answers the colour to draw. `readers` is
// `{jacketOf, typeColorOf}`; without them a link carries the cable's own
// colour and nothing else.
export function cablePlan(rack, readers = {}) {
  // an end on a part beside the rack is on the pane that part looks out of (model.js endPaneIn)
  const end = e => [e.item, e.path, endPaneIn(rack, e) ?? 'none'];
  return {links: (rack.cables || []).map(c =>
    ({id: c.id, media: c.media || 'unset', purpose: c.purpose || '', ...colorFacts(c, readers), from: end(c.a), to: end(c.b)}))};
}

// The same cables for the 3D scene (cables.js drawCables3d): there an end is
// [item id, path, the device's OWN PANEL]. The scene places a device by its
// face and its turn itself, so it asks which of the device's panels a port is
// on, not which pane shows it. An end whose device is gone names no mount,
// and the scene hangs the other end as an unplugged lead.
// A link carries what decides its colour, as cablePlan's does.
export function cablePlan3d(rack, readers = {}) {
  const end = e => [e.item, e.path, e.view === 'rear' ? 'rear' : 'front'];
  return {links: (rack.cables || []).map(c =>
    ({id: c.id, media: c.media || 'unset', purpose: c.purpose || '', ...colorFacts(c, readers), from: end(c.a), to: end(c.b)}))};
}

// WHAT THE 3D SCENE READS OF THE CABLES: which cables there are, in order,
// where each one's two ends are, its media (its colour; the showcase's
// 'copper' is coloured by purpose, so there the purpose counts too) and the
// colour it states of its own. Two racks
// that agree on those draw the same tubes and seat the same plugs. A label, a
// length, or the purpose of any other media changes nothing in the scene, so
// an edit to one of those need not rebuild it. An EDITED route does change
// it, and it is in the key so the rebuild is scheduled by the commit itself;
// an automatic route follows the items, and rack-page.js's routesSig (the
// resolved waypoints) rebuilds when render() finds them changed.
export function sameCables3d(a, b) {
  const ca = a.cables || [], cb = b.cables || [];
  if (ca === cb) return true;
  const key = c => JSON.stringify([c.id, endKey(c.a), endKey(c.b), c.media || '', c.media === 'copper' ? c.purpose || '' : '',
    JSON.stringify(c.routeEdited ? c.route : null), hexColor(c.color) || '']);
  return ca.length === cb.length && ca.every((c, i) => key(c) === key(cb[i]));
}

// ── media ───────────────────────────────────────────────────────────────
// `power` is a conductor that carries power: an AC cord and a DC feed, told
// apart by the cable's type and by its ends. `ground` is a bonding conductor
// (docs/cable-ends-design.md section 4). `stack` joins the stacking ports of
// two switches, `usb` is a USB link and `console` a console link.
export const MEDIA = ['os2', 'om3', 'om4', 'om5', 'cat6', 'cat6a', 'dac', 'aoc', 'power', 'ground', 'stack', 'usb', 'console'];
export const MEDIA_LABELS = {
  os2: 'OS2 single-mode fiber', om3: 'OM3 multimode fiber', om4: 'OM4 multimode fiber',
  om5: 'OM5 multimode fiber', cat6: 'Cat 6 copper', cat6a: 'Cat 6A copper',
  dac: 'DAC (twinax)', aoc: 'AOC (active optical)', power: 'Power cable', ground: 'Ground wire',
  stack: 'Stack cable', usb: 'USB cable', console: 'Console cable'};

const FIBER_SM = {family: 'fiber', mode: 'single-mode'}, FIBER_MM = {family: 'fiber', mode: 'multimode'};
const KIND = {os2: FIBER_SM, om3: FIBER_MM, om4: FIBER_MM, om5: FIBER_MM,
              cat6: {family: 'copper', mode: null}, cat6a: {family: 'copper', mode: null},
              dac: {family: 'dac', mode: null}, aoc: {family: 'aoc', mode: null},
              power: {family: 'power', mode: null}, ground: {family: 'ground', mode: null},
              stack: {family: 'stack', mode: null}, usb: {family: 'usb', mode: null}, console: {family: 'console', mode: null}};
const UNKNOWN = {family: null, mode: null};
// What a media IS: its connector family (`fiber`, copper, dac, aoc, power,
// ground, stack, usb, console) and, for fibre, its mode. A media this page
// does not know has neither.
export const mediaKind = media => (typeof media === 'string' && Object.hasOwn(KIND, media) ? KIND[media] : UNKNOWN);

// The interfaces (spec/schemas/connectors.yaml) whose cable is a stack, a USB
// or a power cable that is none of an AC cord: a stacking port, a USB
// receptacle, and the StackPower and redundant-power ports.
const STACK_IFACES = ['flexstack', 'stackwise-480', 'ex4200-vcp'];
const USB_IFACES = ['usb-a', 'micro-usb-b', 'mini-usb-b', 'usb-c'];
const POWER_IFACES = ['stackpower', 'cisco-rps2300', 'ex3300-rps'];

// What an END's connector is, from what is known about it: the attrs of the
// part seated in the port (an optic, a DAC end - null when nothing is), the
// port's own data-media, its slot's interface, and its `role`. Same shape as
// mediaKind.
// A USB END IS TOLD FROM A CONSOLE END BY THE PORT'S ROLE. A USB receptacle
// serves a data link and a console alike, so its interface cannot say which,
// and the port's `role: console` is what the library states for a console.
// An end whose `role` (or whose seated part's `role`) is `console` is a
// console end whatever its connector, so an RJ45 console is one too. Else the
// interface, the port's media or the seated plug's media is read: a stacking
// interface is a stack end, one of the four USB keys a USB end, and the
// StackPower and redundant-power interfaces are power. A console port whose
// role the page does not pass reads as its connector does, as it did before.
export function connectorOf({attrs = null, portMedia = '', iface = '', role = ''} = {}) {
  const a = attrs || {};
  if (role === 'console' || a.role === 'console') return {family: 'console', mode: null};
  const kind = String(a['cable-kind'] || '');
  if (kind === 'aoc') return {family: 'aoc', mode: null};
  if (kind || a.face === 'cable') return {family: 'dac', mode: null};
  const mode = /^single/.test(a.mode || '') ? 'single-mode' : /^multi/.test(a.mode || '') ? 'multimode' : null;
  const face = String(a.face || a.connector || '');      // an optic states `face`, a plug `connector`
  if (a.media === 'fiber' || mode || /^(lc|sc|mpo)/.test(face)) return {family: 'fiber', mode};
  if (a.media === 'copper' || face === 'rj45') return {family: 'copper', mode: null};
  // a seated plug, and a port, name the interface they mate by the same key
  const words = attrs ? [a.media, a.connector, a.face].map(String) : [portMedia, iface];
  if (words.some(w => STACK_IFACES.includes(w))) return {family: 'stack', mode: null};
  if (words.some(w => USB_IFACES.includes(w))) return {family: 'usb', mode: null};
  if (attrs) return UNKNOWN;                    // something is seated, and it does not say
  if (/^rj45/.test(portMedia) || iface === 'rj45') return {family: 'copper', mode: null};
  if (/^(lc|sc|mpo)/.test(iface) || portMedia === 'fiber') return {family: 'fiber', mode: null};
  if (POWER_IFACES.includes(iface) || POWER_IFACES.includes(portMedia)) return {family: 'power', mode: null};
  return UNKNOWN;
}

// THE MEDIA A NEW CABLE IS OFFERED, from its two ends: single-mode fibre ->
// os2; multimode -> om4; fibre that states no mode -> os2; copper -> cat6a;
// a DAC or AOC end -> itself; a power end -> power; a ground end -> ground; a
// stack, USB or console end -> itself; nothing known -> '', and the user
// picks. The first end that knows decides, unless it is fibre of no stated
// mode and the other is fibre that states one.
export function proposeMedia(a, b) {
  const known = [a, b].filter(e => e && e.family);
  if (!known.length) return '';
  const pick = known.find(e => e.family === 'fiber' && e.mode && known[0].family === 'fiber') || known[0];
  if (pick.family === 'fiber') return pick.mode === 'multimode' ? 'om4' : 'os2';
  return {copper: 'cat6a', dac: 'dac', aoc: 'aoc', power: 'power', ground: 'ground', stack: 'stack', usb: 'usb', console: 'console'}[pick.family] || '';
}

const NAMED = {fiber: 'fiber', copper: 'copper', dac: 'a DAC', aoc: 'an AOC', power: 'power', ground: 'ground',
               stack: 'stacking', usb: 'USB', console: 'console'};
const ACDC = {ac: 'AC', dc: 'DC'};
// A MISMATCH IS A WARNING, never a refusal: the sentences to show
// beside the media field, or [] when nothing is known to be wrong.
export function mismatch(media, a, b) {
  const out = [];
  const fa = a?.family, fb = b?.family;
  if (fa && fb && fa !== fb) out.push(`The ends differ: A is ${NAMED[fa]}, B is ${NAMED[fb]}.`);
  if (fa === 'fiber' && fb === 'fiber' && a.mode && b.mode && a.mode !== b.mode)
    out.push(`The ends differ: A is ${a.mode}, B is ${b.mode}.`);
  const m = mediaKind(media);
  if (m.family) for (const [k, e] of [['A', a], ['B', b]])
    if (e?.family && e.family !== m.family)
      out.push(`${Object.hasOwn(MEDIA_LABELS, media) ? MEDIA_LABELS[media] : media} does not suit end ${k}, which is ${NAMED[e.family]}.`);
  // POWER ENDS (docs/cable-ends-design.md section 5). Each is said only where
  // both ends state it: an AC end against a DC end, and two ends that face the
  // same way. The two receptacles are never compared as connectors: a cord
  // has a different plug at each end.
  if (fa === 'power' && fb === 'power') {
    if (ACDC[a.mode] && ACDC[b.mode] && a.mode !== b.mode)
      out.push(`The ends differ: A is ${ACDC[a.mode]} power, B is ${ACDC[b.mode]} power.`);
    if (a.role && a.role === b.role)
      out.push(`Both ends are ${a.role}s: a power cable runs from an outlet to an inlet.`);
  }
  // what each end found about its own plug (endPlug below)
  for (const [k, e] of [['A', a], ['B', b]]) if (e?.note) out.push(`End ${k}: ${e.note}.`);
  return out;
}

// ── plugs: derived, never stored ────────────────────────────────────────
// The plug a slot takes, by its interface, when the slot accepts it. A slot
// with no known plug here (an MPO adapter, a cage - which takes an optic or
// a DAC, not a plug) has none: its cable ends at the port's own centre, or
// on the cable point a seated DAC end carries. That is not an error.
const PLUGS = {lc: 'generic/lc-plug@2', 'lc-duplex': 'generic/lc-duplex-plug@2', rj45: 'generic/rj45-plug@1'};
export function plugFor(slot) {
  const p = PLUGS[slot?.interface];
  return p && (slot.accepts || []).includes(p) ? p : null;
}

// ── where a cable can land ──────────────────────────────────────────────
// A CABLE LANDS ON A PART OF CLASS `port`, OR ON A CONNECTOR SLOT THAT TAKES
// A CABLE END (docs/cable-ends-design.md section 2). This is the one place
// that says so; every reader of the kit asks it, and a page asks it too.
//
// A connector slot is an entry of `cages[]` with `kind: connector`: what the
// build publishes for a part that declares an `interface`. It takes a cable
// end when a part it accepts is of class `port`, which is what every cord end
// and lug of the library is and nothing else that seats in a slot is (an
// optic is a `transceiver`, a dust cap a `cap`, a touch guard `mechanical`).
// So a power inlet, an outlet, a DC terminal and a ground stud land by their
// slot, whatever class they are; a pluggable cage, a module bay and a guard
// seat do not. `compByRef` is the catalogue's lookup (`loadSlots` in `catalog.js`).
const compOfRef = (compByRef, ref) => {
  if (typeof compByRef !== 'function' || !ref) return null;
  try { return compByRef(String(ref).split(':')[0]) || null; } catch { return null; }
};
// The cable ends a slot takes: the parts of class `port` in its accept list;
// none for anything but a connector slot. IN A STATED ORDER, since the order
// of an accept list as built is no promise: the lowest current rating first
// (`attrs.rating-a`, a part that states none after those that do), then by
// ref. So a 15 A plug comes before the 20 A plug of the same receptacle.
const plugWord = ref => String(ref).split(':')[0];
const ratingOf = c => (typeof c?.attrs?.['rating-a'] === 'number' ? c.attrs['rating-a'] : Infinity);
export function cableEndsOf(slot, compByRef) {
  if (slot?.kind !== 'connector' || !Array.isArray(slot.accepts)) return [];
  const ends = [...new Set(slot.accepts.map(plugWord))].map(ref => ({ref, comp: compOfRef(compByRef, ref)})).filter(x => x.comp?.class === 'port');
  return ends.sort((a, b) => (ratingOf(a.comp) - ratingOf(b.comp) || 0) || (a.ref < b.ref ? -1 : a.ref > b.ref ? 1 : 0)).map(x => x.ref);
}
export const takesCableEnd = (slot, compByRef) => cableEndsOf(slot, compByRef).length > 0;
// `cls` is the class of the part at the end's path (a drawing's `data-class`,
// a component's `class`); `slot` the slot at that same path, or null.
export const cableLandsOn = ({cls = null, slot = null} = {}, compByRef = null) =>
  cls === 'port' || takesCableEnd(slot, compByRef);

// WHAT THE PART THAT PRESENTS A SLOT IS, from its component (its class and
// attrs; a page that reads a drawing hands in the component its `data-ref`
// names): the family mismatch reads, which way power runs through it, and AC
// or DC where it says. Same shape as connectorOf, with `role`.
//   class `ground`                            ground, no direction
//   states `attrs.outlet`                     power, an outlet
//   states `attrs.input`, or a media ac/dc    power, an inlet, AC or DC as stated
//   class inlet, psu or power otherwise       power, direction not known
//   anything else, or no component            not known
// Nothing known is never a guess: an end the page said nothing about has no
// family, and mismatch says nothing of it.
const acdc = v => (/^ac$/i.test(String(v ?? '')) ? 'ac' : /^dc/i.test(String(v ?? '')) ? 'dc' : null);
const POWER_CLASSES = ['inlet', 'psu', 'power'];
export function receptacleOf(comp) {
  const a = comp?.attrs || {}, cls = comp?.class ?? null;
  if (cls === 'ground') return {family: 'ground', mode: null, role: null};
  const mode = acdc(a.input) || acdc(a.media);
  if (a.outlet) return {family: 'power', mode, role: 'outlet'};
  if (a.input || mode) return {family: 'power', mode, role: 'inlet'};
  if (POWER_CLASSES.includes(cls)) return {family: 'power', mode: null, role: null};
  return {...UNKNOWN, role: null};
}
// The kind a free end is listed under: 'power', 'ground', or 'other' for a
// slot whose part says neither.
export const endKind = info => (info?.family === 'power' || info?.family === 'ground' ? info.family : 'other');
// A SLOT END AS A PERSON READS IT: "C13 outlet", "C20 inlet", "terminal-stud
// ground", "p40 power connector". The interface is the slot's own word, with
// the `iec-` of an IEC 60320 coupler left off.
// THE COUPLER A SLOT IS, by its interface (P-0019): `iec-c13` and
// `eaton-c39` are a C13 and a C39. null for an interface that names none.
export const couplerType = iface => { const m = /(?:^|-)(c\d+)$/i.exec(String(iface ?? '')); return m ? m[1].toUpperCase() : null; };
// WHICH WAY A COUPLER FACES, where nothing else says: IEC 60320 numbers its
// female connectors odd (a C13 or C19 outlet, and the C39 that takes both a
// C14 and a C20) and its male inlets even (a C14, a C20). A stated rule of
// the standard, not a guess; asked only of a part beside the rack, whose
// panel no page reads (ports.js zeroUEnds).
export const couplerRole = iface => { const t = couplerType(iface); return t ? (Number(t.slice(1)) % 2 ? 'outlet' : 'inlet') : null; };
export function connectorName(slot, info) {
  const iface = String(slot?.interface || '');
  const word = couplerType(iface) ?? (/^iec-/.test(iface) ? iface.slice(4).toUpperCase() : iface);
  const what = info?.role || (info?.family === 'ground' ? 'ground' : info?.family === 'power' ? 'power connector' : 'connector');
  return [word, what].filter(Boolean).join(' ');
}

// THE PLUG AT AN END (section 3 of the same note). The plug or lug a cable
// has where it lands on a slot is DERIVED from the slot: the cable ends it
// accepts (cableEndsOf, in its order). One: that one. Several: the one the
// end states (`plug`, a component ref on the end, the only thing about a plug
// a file holds); with none stated the first, and a sentence that says what to
// set. A stated plug the slot does not take is not drawn, and a sentence
// names what the slot takes.
// A CORD SET PAIRS ITS ENDS (P-0019): an IEC 60320 cord is a C13 to a C14,
// or a C19 to a C20. So where a slot takes several plugs and the end states
// none, the one that pairs with the plug at the cord's other end (`far`, a
// ref) is drawn, and nothing needs setting: a C39 outlet on a cord whose
// other end is a C19 takes its C20. A far plug that pairs with none of them,
// or none known, leaves the rule above.
// {plug, choices, note}: `plug` null when the slot takes no cable end.
const plugCoupler = (compByRef, ref) => couplerType(compOfRef(compByRef, ref)?.attrs?.connector);
const pairedWith = (compByRef, choices, far) => {
  const t = far ? plugCoupler(compByRef, plugWord(far)) : null;
  if (!t) return null;
  const n = Number(t.slice(1)), mate = `C${n % 2 ? n + 1 : n - 1}`;
  return choices.find(ref => plugCoupler(compByRef, ref) === mate) ?? null;
};
export function endPlug(slot, compByRef, stated = null, far = null) {
  const choices = cableEndsOf(slot, compByRef);
  if (!choices.length) return {plug: null, choices, note: null};
  const want = typeof stated === 'string' && stated ? plugWord(stated) : null;
  if (want && choices.includes(want)) return {plug: want, choices, note: null};
  const set = `set "plug" on the end to ${choices.join(' or ')}`;
  if (want) return {plug: choices[0], choices, note: `it states the plug ${want}, which ${slot.id} does not take; ${set}`};
  const paired = choices.length > 1 ? pairedWith(compByRef, choices, far) : null;
  if (paired) return {plug: paired, choices, note: null};
  return {plug: choices[0], choices,
          note: choices.length > 1 ? `${slot.id} takes more than one plug and ${choices[0]} is drawn; ${set}` : null};
}

// The seats a cabled end at `path` adds, as {slotId: plugRef}: the port's own
// slot when it takes a plug (an RJ45 jack, a duplex adapter), else the slots
// one step under what is seated in it (an optic's tx and rx bores). `slots`
// is the face's slot list (swap.js faceCages); a slot the user's own `swaps`
// already speak for - or, for an adapter, any of its bores - is left alone.
// AN END THAT LANDS BY ITS SLOT (a power inlet, a ground stud: `landed` is
// {cls, compByRef, plug}, the class of the part at the path, the catalogue's
// lookup and the plug the end states) seats the plug endPlug derives. A port
// of class `port` is read as it always was, whatever its slot accepts.
//
// AN END AT A DC PORT'S PATH (`landed.dc`, the `dc` ports.js gives the end's
// info, with `end: 'port'`) seats the plug each pole derived on its slot (a
// slots port), or the connector's plug on the connector (a points port).
export function plugSeats(path, slots, swaps = {}, landed = null) {
  const own = k => Object.hasOwn(swaps || {}, k);
  const free = s => !own(s.id) && !(s.bores || []).some(b => own(`${s.id}/${b}`));
  const seat = list => Object.fromEntries(list.filter(s => plugFor(s) && free(s)).map(s => [s.id, plugFor(s)]));
  const dc = landed?.dc;
  if (dc?.end === 'port' && dc.path === path) {
    const seats = dc.kind === 'points' ? [[dc.connector, dc.poles[0]?.plug]] : dc.poles.map(q => [q.path, q.plug]);
    return Object.fromEntries(seats.flatMap(([id, plug]) => {
      const s = slots.find(x => x.id === id);
      return s && plug && free(s) ? [[id, plug]] : [];
    }));
  }
  const exact = slots.filter(s => s.id === path);
  if (exact.some(plugFor)) return seat(exact);
  if (landed && landed.cls !== 'port') {
    const s = exact.find(x => takesCableEnd(x, landed.compByRef));
    const plug = s && free(s) ? endPlug(s, landed.compByRef, landed.plug).plug : null;
    return plug ? {[s.id]: plug} : {};
  }
  const under = `${path}-occupant/`;
  return seat(slots.filter(s => s.id.startsWith(under) && !s.id.slice(under.length).includes('/')));
}
// The swaps a face is drawn with: the item's own, over the derived plugs.
export const mergeSeats = (swaps, plugs) => ({...(plugs || {}), ...(swaps || {})});

// ── loose ends ──────────────────────────────────────────────────────────
// The bay a card port's path sits in: 'slot-2/module/p2' -> 'slot-2'.
export function holderPath(path) {
  const i = String(path).lastIndexOf('/module/');
  return i < 0 ? null : path.slice(0, i);
}
// AN ELEMENT ID IS NOT AN ADDRESS. The build joins the steps of an element's
// id with two hyphens (`slot-2--module--p0`, and `bay-1-rear--b01` for a part
// on the back of what bay-1 holds) and a path's with a slash, and no path in
// the library holds two hyphens in a row. A reader that took an element's id
// for its path offered one as an address; it is refused wherever an end is
// set, with the address it most likely stands for.
export const isElementId = path => String(path ?? '').includes('--');
export function addressFor(path) {
  const p = String(path ?? '');
  const back = /^(.+?)-rear--(.+)$/.exec(p);
  return back ? {path: `${back[1]}/module/${back[2].split('--').join('/')}`, view: 'rear'} : {path: p.split('--').join('/')};
}
// A phrase with no period, as every reason here is.
export function elementIdReason(path) {
  const to = addressFor(path);
  return `${path} is an element id of the drawing, not the address of a port; give ${
    to.view ? `{path: "${to.path}", view: "${to.view}"}` : `the path ${to.path}`}`;
}

// WHY AN END DOES NOT LAND, from what its panel has now - or null when it
// lands. `facts` is what cable-plugs.js read off the face, or what ports.js
// seatedPort answered from the catalogue:
//   {item, drawing, port, cage, occupied, holder: {path, part} | null, onView?, part?, side?}
// item: the device is still in the rack; drawing: its panel has one; port: a
// port is drawn at the end's path; cage: that port takes an optic; occupied:
// something is seated in it; holder: the bay above the path and what it holds;
// onView: where no port is at the path on the end's panel, the panel of the
// same device that has it (the back of a part in a bay shows on the other one).
// part: where something is drawn at the path that is neither a port nor a slot
// that takes a cable end (an outlet with no interface, a fixed cord), its name;
// under: where that part is no slot and its own parts are (a DC terminal,
// whose screws take the lugs), the paths of those with no cable, the one to
// take first; empty when every one has a cable;
// side: where the path is a slot on a side, top or bottom view, that view;
// dcGive: where that part's own parts are the poles of DC ports, the paths of
// the ports with no cable, the one to give (empty when every one has a cable);
// dcContact: {part, plug, port}, where the path is a contact of a pluggable
// connector that states a DC port; dcPanel: where the path is a DC port on the
// other panel, that panel.
export function looseReason(end, facts) {
  if (!facts || !facts.item) return 'the device was removed';
  if (isElementId(end.path)) return elementIdReason(end.path);
  if (!facts.drawing) return 'this panel has no drawing';
  if (!facts.port) {
    const h = facts.holder;
    // a DC port (ports.js dcPortsOf): a contact is no end, and a port is on one panel
    if (facts.dcContact) return `${end.path} is a contact of ${facts.dcContact.part}, whose connector takes ${facts.dcContact.plug}; give the path ${facts.dcContact.port}`;
    if (facts.dcPanel) return `${end.path} is on the ${facts.dcPanel} panel; give view "${facts.dcPanel}"`;
    if (facts.side) return `${end.path} is on the ${facts.side} of the device, and a cable end can be given on the front or rear only`;
    if (!h) return facts.part ? `${end.path} is ${facts.part}, which takes no plug or lug the library knows` : `${end.path} is not on this panel`;
    const leaf = end.path.slice(h.path.length + '/module/'.length);
    // a part whose poles are a DC port's: the port is the end to give
    if (h.part && facts.part && !facts.onView && facts.dcGive)
      return facts.dcGive.length
        ? `${h.path} holds ${h.part}, whose ${leaf} takes a cable on the ${facts.dcGive.length > 1 ? 'ports' : 'port'} ${facts.dcGive.join(', ')} and not on itself; give the path ${facts.dcGive[0]}`
        : `${h.path} holds ${h.part}, whose ${leaf} takes a cable on its ports and not on itself, and every port of its ${leaf} has a cable`;
    if (h.part && facts.part && !facts.onView && facts.under && !facts.under.length)
      return `${h.path} holds ${h.part}, whose ${leaf} takes a cable on its screws and not on itself, and every screw of its ${leaf} has a cable`;
    if (h.part && facts.part && !facts.onView && facts.under?.length)
      return `${h.path} holds ${h.part}, whose ${leaf} takes a cable on ${facts.under.map(x => x.slice(x.lastIndexOf('/') + 1)).join(', ')} and not on itself; give the path ${facts.under[0]}`;
    if (h.part && facts.part && !facts.onView) return `${h.path} holds ${h.part}, whose ${leaf} takes no plug or lug the library knows`;
    if (h.part && facts.onView) return `${h.path} holds ${h.part}, whose port ${leaf} is on the ${facts.onView} panel; give view "${facts.onView}"`;
    return h.part ? `${h.path} holds ${h.part}, which has no port ${leaf}` : `${h.path} is empty`;
  }
  if (facts.cage && !facts.occupied) return `${end.path} holds no optic`;
  return null;
}

// ── the list's filter (two axes) ────────────────────────────────────────
// {value -> count} for a cable field, in first-seen order.
export function countsBy(cables, field) {
  const m = new Map();
  for (const c of cables || []) m.set(c[field], (m.get(c[field]) || 0) + 1);
  return m;
}
// `on` is {purpose, media}; null on an axis means it is not narrowing.
export const matches = (cable, on = {}) =>
  (on.purpose == null || cable.purpose === on.purpose) && (on.media == null || cable.media === on.media);

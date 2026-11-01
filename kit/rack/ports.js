// kit/rack/ports.js
// THE PORTS OF WHAT IS SEATED, read without a drawing. A card in a bay has
// ports on its face, and a panel or a cassette has more on its back, which the
// host shows through its rear panel. Whether a cable end names one of them is
// answered here from `<ref>.configs.json` and `components.json` alone (what
// `loadSlots` in `catalog.js` returns), through the item's own swaps, so a page
// needs no lookup in a drawing for it.
//
// THE ADDRESS of a port on a seated part is `<bay>/module/<part>`, on the
// device's own panel that shows it: the bay's panel for the part's face, the
// other panel for its back. So the rear adapter b01 of a panel in bay-1 of an
// enclosure whose bays open to the front is
//   {item, path: 'bay-1/module/b01', view: 'rear'}
// An element id of the drawing (`bay-1-rear--b01`) is not an address
// (cable-rules.js isElementId).

import {slotEnv, resolverFor, holdsAt, partOf, slotTree} from './slots.js';
import {portPathOf, looseReason, isElementId, connectorOf, endKey, takesCableEnd, receptacleOf, endPlug, connectorName,
        couplerType, couplerRole, endKind} from './cable-rules.js';
import {hexColor} from './cable-geometry.js';
import {zeroUById} from './model.js';

const MODULE = '/module/';
const OTHER = {front: 'rear', rear: 'front'};
const faceRef = f => (typeof f === 'string' ? f : f?.ref) || null;
const list = v => (Array.isArray(v) ? v : []);
const loaded = ctx => typeof ctx?.slotsOf === 'function' && typeof ctx?.compByRef === 'function';
const natural = new Intl.Collator('en', {numeric: true});

// A part as it is named in a reason: its model, else its ref's name in capitals.
const modelOf = (comp, ref) => comp?.attrs?.model || String(ref).split('/').pop().split('@')[0].toUpperCase();

// Is `steps` a port of `comp`: a part it composes whose component is of class
// port, and below that only the ports that part composes in turn. THE ANSWER
// IS ONE-SIDED. Yes is certain: the build draws every such part as a port. No
// is not: a skin may draw a port its contract composes no part for (a test
// point on a card's face), and only the drawing knows those.
function portIn(comp, steps, compByRef) {
  let c = comp;
  for (const id of steps) {
    const part = list(c?.parts).find(q => q.id === id);
    c = part ? partOf(compByRef, part.ref) : null;
    if (c?.class !== 'port') return null;
  }
  return steps.length ? c : null;
}

// The part at `steps` under `comp`, whatever its class: every part on the way
// from the seated part down to it, the last one last; null when a step names
// no part. [{comp, ref}].
function chainIn(comp, steps, compByRef) {
  const out = [];
  let c = comp;
  for (const id of steps) {
    const part = list(c?.parts).find(q => q.id === id);
    c = part ? partOf(compByRef, part.ref) : null;
    if (!c) return null;
    out.push({comp: c, ref: part.ref});
  }
  return out.length ? out : null;
}

// IS THE BACK OF A PART IN A BAY OF A MODULE REACHED FROM THE DEVICE'S OTHER
// PANEL: only where every module the part sits in, from the device's bay down,
// is a mechanical carrier (class `mechanical`: a drawer, a tray), which has
// nothing of its own between the part and the back of the device. A card with
// electronics (line card, riser) hides what its own bays hold. `bayId` is the
// device's bay, `carrier` the path of the bay the part sits in. `R` is the
// resolver of the item's seats.
function carriedByMechanical(R, bayId, carrier, compByRef) {
  if (carrier === bayId) return true;
  const via = carrier.slice(bayId.length + MODULE.length).split(MODULE);
  let path = bayId;
  for (const id of via) {
    if (partOf(compByRef, R.refAt(`${path}/module`))?.class !== 'mechanical') return false;
    path = `${path}/module/${id}`;
  }
  return true;
}

// WHAT AN END THAT LANDS BY ITS SLOT IS (cable-rules.js receptacleOf), with
// the plug the slot gives it (endPlug) and its name for a person. `comps` are
// the components that could say what it is, the nearest first: a screw of a
// DC terminal says nothing of itself, and the terminal it is part of does.
function slotInfo(slot, comps, end, compByRef) {
  const said = comps.map(receptacleOf).find(i => i.family) || receptacleOf(null);
  // (`farPlug`: the plug at the cord's other end, which settleEnds hands in)
  const {plug, note} = endPlug(slot, compByRef, end?.plug, end?.farPlug);
  return {...said, plug, ...(note ? {note} : {}), connector: connectorName(slot, said)};
}

// WHAT A CABLE END UNDER A BAY NAMES, in the words looseReason reads, or null
// when the catalogue cannot say: no parts list was loaded, the path is not
// under a bay of this device's configuration, the part seated there is
// unknown, or the part composes no port of that name on either side. The
// drawing decides then.
//   port      a port is at the path on the end's panel
//   onView    the panel the port is on; where `port` is false, the port is on
//             that panel and the end names the other one
//   back      the port is on the back of the part
//   cage, occupied   the port takes an optic; something is seated in it
//   holder    {path, part, ref}: the bay above the path and what it holds;
//             `part` is null for an empty bay
//   info      the port's connector, as cable-rules.js connectorOf reads it
//   slot      the end lands by its slot and not as a part of class port: a
//             power inlet, a DC terminal, a ground stud (cable-rules.js
//             cableLandsOn). `info` then carries `role`, `plug`, `connector`
//             and, where the plug is in question, `note`
//   part      a part is at the path that takes no cable end: its name
//   dc facts  where the path is a DC port, a pole or a contact (dcPortsOf):
//             `info.dc` on a port, pole or connector end; `dcPanel`,
//             `dcContact` and `dcGive` on one that is loose (cable-rules.js
//             looseReason)
// `ctx` is {slotsOf, compByRef}.
//
// A PORT ON A BACK IS THE PART'S, WHETHER OR NOT THE HOST DRAWS IT. Whether a
// bay shows the back of what it holds on the other panel is the device's own
// statement, which configs.json does not publish. An enclosure with a closed
// back has the port all the same, and a cable on it lands; it is only not
// drawn there, and a route to it ends at the device.
//
// A bay that neither the swaps nor the configuration names holds what it ships
// with, when the configuration has the bay (its `only-in`, slots.js slotEnv).
export function seatedPort(item, end, ctx) {
  return withDcInBay(item, end, ctx, seatedBase(item, end, ctx));
}
function seatedBase(item, end, ctx) {
  if (!item || !loaded(ctx)) return null;
  const p = portPathOf(end?.path ?? ''), first = p.indexOf(MODULE), cut = p.lastIndexOf(MODULE);
  if (first < 0 || isElementId(p)) return null;
  const slots = ctx.slotsOf(item.ref);
  if (!slots || slots.error) return null;
  const env = slotEnv(item, slots, ctx.compByRef, ctx.redirects), swaps = item.swaps || {};
  const bay = env.bays.find(b => b.id === p.slice(0, first));
  if (!bay || !OTHER[bay.view]) return null;
  const carrier = p.slice(0, cut), steps = p.slice(cut + MODULE.length).split('/');
  // A BAY LEFT TO ITS DEFAULT IS ANSWERED FOR when the configuration has it. A
  // device may give a bay to some configurations only (a double-width power
  // bay where another has two card slots); configs.json publishes that as the
  // bay's `only-in`, and slotEnv does not list a bay that leaves the item's
  // configuration out, so `bay` above is none and the build draws nothing there.
  const R = resolverFor(env, swaps);
  const ref = R.refAt(`${carrier}/module`);
  const base = {item: true, drawing: true, port: false, cage: false, occupied: false, onView: null, back: false};
  if (!ref) return R.entryAt(carrier) ? {...base, holder: {path: carrier, part: null, ref: null}} : null;
  const comp = partOf(ctx.compByRef, ref);
  if (!comp) return null;
  const holder = {path: carrier, part: modelOf(comp, ref), ref: String(ref).split(':')[0]};
  const view = end.view === 'rear' ? 'rear' : 'front';
  const face = portIn(comp, steps, ctx.compByRef);
  // only what sits in one of the device's own bays shows its back, and a
  // PASSIVE PANEL in a bay of a mechanical carrier (a holder in a drawer's
  // slot): the glass runs through the drawer, so each adapter has an end on
  // the far panel too
  const open = comp.class === 'adapter-panel' && carriedByMechanical(R, bay.id, carrier, ctx.compByRef);
  const rear = carrier === bay.id || open ? partOf(ctx.compByRef, faceRef(comp.faces?.rear)) : null;
  const behind = rear ? portIn(rear, steps, ctx.compByRef) : null;
  const back = !!behind && view === OTHER[bay.view];
  const drawn = back ? behind : face && view === bay.view ? face : null;
  if (!drawn) {
    if (face || behind) return {...base, holder, onView: face ? bay.view : OTHER[bay.view]};
    // NOT A PORT, BUT A PART OF THE FACE: it lands when a connector slot that
    // takes a cable end is at its path, and is named when none is.
    const chain = view === bay.view ? chainIn(comp, steps, ctx.compByRef) : null;
    if (!chain) return null;
    const seat = R.entryAt(p);
    if (!seat || seat.back || !takesCableEnd(seat, ctx.compByRef)) {
      // no slot itself; where its own parts are (the screws of a DC terminal), they are named
      const last = chain.at(-1);
      const under = list(last.comp.parts).map(q => `${p}/${q.id}`).filter(x => takesCableEnd(R.entryAt(x), ctx.compByRef)).sort(natural.compare);
      return {...base, holder, part: modelOf(last.comp, last.ref), ...(under.length ? {under} : {})};
    }
    return {...base, port: true, slot: true, onView: view, holder,
            info: slotInfo(seat, [...chain.map(x => x.comp).reverse(), comp], end, ctx.compByRef)};
  }
  // the slot at the path: the resolver's, which reads a back's slots where no
  // part of the face shares the id; a back that does share one answers itself
  const slot = back && face ? (steps.length === 1 ? list(rear.cages).find(g => g.id === steps[0]) ?? null : null) : R.entryAt(p);
  // THE ROLE A PORT HAS is the one its placement in the module states (the
  // `parts[]` entry of the last step, on the face or on the back it is read
  // from), else the one its own component states: a console port is a console
  // end whatever its connector (cable-rules.js connectorOf)
  const above = steps.length > 1 ? chainIn(back ? rear : comp, steps.slice(0, -1), ctx.compByRef)?.at(-1)?.comp : back ? rear : comp;
  const role = list(above?.parts).find(q => q.id === steps.at(-1))?.attrs?.role || drawn.attrs?.role || '';
  return {...base, port: true, onView: view, back, holder, cage: slot?.kind === 'cage',
          occupied: !!slot && holdsAt(env, swaps, p, {...slot, isCage: true}) != null,
          info: connectorOf({portMedia: drawn.attrs?.media || '', iface: slot?.interface || drawn.attrs?.connector || '', role})};
}

// AN END THE CATALOGUE KNOWS TO BE LOOSE, said when the cable is made and not
// later: a cable end under a bay whose seated part is known and has no port at
// that path on that panel (seatedPort says `port: false` with a part held).
// The sentence is the loose-end finding's own (looseReason), so a dry run, the
// real add and the finding agree. An empty bay, a bay the catalogue cannot
// answer for and an item whose parts lists are not loaded are not refused: the
// end is kept as given and the page's drawing decides. Returns the first
// reason, or null.
//
// A PORT A PASSIVE PANEL DOES NOT COMPOSE (a made-up `p9`, the rear of a panel
// with no rear) is refused too, though seatedPort leaves it to the drawing: a
// panel (class adapter-panel) has no port its contract does not compose, which
// a card may (a test point only its skin draws). The panel may sit in a bay of
// a module in the device's bay (a holder in a drawer's slot).
export function seatedEndReason(rack, ends, ctx) {
  for (const end of ends) {
    const item = (rack.items || []).find(i => i.id === end.item);
    if (!item || isElementId(end.path)) continue;
    const own = seatedPort(item, end, ctx) ?? absentOnPanel(item, end, ctx);
    if (!own) {
      // a DC port named on the other panel, or a contact of a connector that states one, on the device's own panel
      const dcFacts = dcLoose(item, end, ctx), why = dcFacts ? looseReason(end, {item: true, drawing: true, port: false, holder: null, ...dcFacts}) : null;
      if (why) return why;
      continue;
    }
    // (a part at the path that takes no cable is the page's to call loose: a
    // rack file may hold such an end on purpose)
    if (own.port || !own.holder?.part || own.part) continue;
    const reason = looseReason(end, own);
    if (reason) return reason;
  }
  return null;
}
function absentOnPanel(item, end, ctx) {
  if (!loaded(ctx)) return null;
  const p = portPathOf(end?.path ?? ''), first = p.indexOf(MODULE), cut = p.lastIndexOf(MODULE);
  if (first < 0) return null;
  const steps = p.slice(cut + MODULE.length).split('/');
  const slots = ctx.slotsOf(item.ref);
  if (steps.length !== 1 || !slots || slots.error) return null;
  const env = slotEnv(item, slots, ctx.compByRef, ctx.redirects), swaps = item.swaps || {};
  const bay = env.bays.find(b => b.id === p.slice(0, first)), carrier = p.slice(0, cut);
  // (kept as it was: this refuses a made-up port, so it speaks only for a bay that is spoken for; a bay left
  // to its default is the drawing's here, though seatedPort answers for it)
  const named = id => Object.hasOwn(swaps, id) || env.built(id) !== undefined;
  if (!bay || !OTHER[bay.view] || !(named(bay.id) || (carrier !== bay.id && named(carrier)))) return null;
  const R = resolverFor(env, swaps), ref = R.refAt(`${carrier}/module`), comp = partOf(ctx.compByRef, ref);
  if (!comp || comp.class !== 'adapter-panel' || portIdsOf(comp, ctx.compByRef).has(steps[0])
      || !carriedByMechanical(R, bay.id, carrier, ctx.compByRef)) return null;
  return {item: true, drawing: true, port: false, holder: {path: carrier, part: modelOf(comp, ref), ref: String(ref).split(':')[0]}};
}

// THE FAR END OF EVERY ADAPTER OF A PASSIVE PANEL IN A MECHANICAL CARRIER, from
// the catalogue: a panel (class adapter-panel) seated in a bay of a drawer or a
// tray that sits in a bay of the device has its adapters' other ends on the
// panel opposite the bay's. A page that reads a drawing lists the backs of
// what the device's own bays hold, where the host draws them; a holder in a
// drawer is no bay of the device, so no panel draws its back, and this lists
// them. [{path, view, media?}], the path `<bay>/module/<part>` of the part of
// the panel's rear face, in natural order.
export function backEnds(item, ctx) {
  if (!item || !loaded(ctx)) return [];
  const slots = ctx.slotsOf(item.ref);
  if (!slots || slots.error) return [];
  const env = shownEnv(item, slots, ctx.compByRef, ctx.redirects), swaps = item.swaps || {};
  const R = resolverFor(env, swaps), out = [];
  for (const b of slotTree(env, swaps).bays) {
    const comp = b.holds ? partOf(ctx.compByRef, b.holds) : null;
    if (comp?.class !== 'adapter-panel' || !OTHER[b.view] || !b.path.includes(MODULE)
        || !carriedByMechanical(R, b.path.slice(0, b.path.indexOf(MODULE)), b.path, ctx.compByRef)) continue;
    const rear = partOf(ctx.compByRef, faceRef(comp.faces?.rear));
    for (const q of list(rear?.parts))
      if (partOf(ctx.compByRef, q.ref)?.class === 'port')
        out.push({path: `${b.path}/module/${q.id}`, view: OTHER[b.view], media: q.attrs?.media ?? partOf(ctx.compByRef, q.ref)?.attrs?.media ?? null});
  }
  return out.sort((a, b) => natural.compare(a.path, b.path));
}

// ── what a DCIM calls the port ─────────────────────────────────────────────
// THE DCIM PORTS A CABLE END ON A SEATED PART LANDS ON, as the part's module
// type lists them, or null when the catalogue has none for it. A module type
// does not name a fibre port by its part: a duplex adapter `lc01` on a panel's
// face is the front ports `1` and `2`, one per fibre; its back `b01` is the
// rear port `B01-1`, one connector with two positions; a cassette's `mtp` is
// `MTP-1`. Those names are the exporter's own numbering, so the build writes
// them beside the fibre graph (`optical.ports` in components.json, from the
// walk that writes the type file) and nothing here derives one.
//   part      the part's id on the module
//   back      it is on the back of the module
//   sections  [[section, names]]: the type file's list ('front-ports',
//             'rear-ports') and the names in it, in position order, each once
//             and without the {module}/ a type file writes before them. More
//             than one list: the part's positions are split between two kinds
//             of port (a stated trunk position beside a front one).
// Only a port one step under a module (`holder`): the module may sit in a bay
// of another module, a Fibrain panel in the XCU10 drawer, and dcim-rules.js
// names it through each level (#1024).
export function fibrePorts(item, end, ctx) {
  const at = seatedPort(item, end, ctx);
  if (!at?.port || !at.holder?.ref) return null;
  const p = portPathOf(end.path), cut = p.lastIndexOf(MODULE);
  const part = p.slice(cut + MODULE.length);
  if (part.includes('/')) return null;
  const key = `${at.back ? 'rear:' : ''}${part}`;
  const published = partOf(ctx.compByRef, at.holder.ref)?.optical?.ports;
  const lists = published && Object.hasOwn(published, key) ? published[key] : null;
  if (!lists || typeof lists !== 'object') return null;
  const sections = Object.entries(lists)
    .map(([section, names]) => [section, [...new Set(list(names).filter(n => n != null).map(String))]])
    .filter(([, names]) => names.length);
  return sections.length ? {part, back: at.back, sections} : null;
}

// The ids one step under a part that a cable can be on: its cages, the parts
// it composes and its own bays, and the cages and parts of its back.
export function portIdsOf(comp, compByRef) {
  const rear = partOf(compByRef, faceRef(comp?.faces?.rear));
  return new Set([...list(comp?.cages).map(g => g.id), ...list(comp?.parts).map(q => q.id), ...Object.keys(comp?.bays || {}),
                  ...list(rear?.cages).map(g => g.id), ...list(rear?.parts).map(q => q.id)]);
}

// ── the jacket colour an end states (#1028) ─────────────────────────────
// A cable is drawn in the jacket colour of its two seated ends when both
// state one and they agree (cable-geometry.js agreedJacket). This says what
// one end states.
//
// A DEFAULT IS NOT A STATEMENT. Every generic cable end declares the field
// `jacket-color` with a default (`#1c1c1c` on most), which is what its stub is
// drawn in when nobody has said anything. If that counted, every DAC, AOC and
// power cord between two generic ends would turn black. So an end states a
// jacket colour only when something says it of THAT end:
//   1. the rack: `fields` of the item holds `jacket-color` for the part
//      seated in the port (`<port>-occupant`), set by the `field` command or
//      the page's form. A value set to the very colour of the default is
//      stated all the same: somebody chose it.
//   2. else the part: a maker's part that composes a generic end and gives
//      its jacket a colour (`attrs` of the part, or of a part it composes,
//      to any depth; siemon/qsfp28-aoc@1 states its aqua this way).
// The declared default of a field is never read. A value that is no hex
// colour states nothing the kit can draw, and it does not fall through to the
// part's own: the rack said something else of that end.
export const JACKET_FIELD = 'jacket-color';
function partJacket(comp, compByRef, seen = new Set()) {
  if (!comp || seen.has(comp)) return null;
  seen.add(comp);
  if (comp.attrs && Object.hasOwn(comp.attrs, JACKET_FIELD)) return hexColor(comp.attrs[JACKET_FIELD]);
  for (const q of list(comp.parts)) {
    if (q?.attrs && Object.hasOwn(q.attrs, JACKET_FIELD)) return hexColor(q.attrs[JACKET_FIELD]);
    const under = partJacket(partOf(compByRef, q?.ref), compByRef, seen);
    if (under) return under;
  }
  return null;
}
// The jacket colour the part seated at a cable end states, as `#rrggbb`, or
// null: nothing is seated in the port, the catalogue was not loaded or does
// not know the part, or nothing states a colour of it. `ctx` is
// {slotsOf, compByRef}, what `loadSlots` returns. `kept`, a Map, holds what
// each item seats from one end to the next (jacketsFor passes one): a device
// of sixty cabled ports is then read once and not sixty times.
function seatsOf(item, ctx, kept) {
  if (kept?.has(item)) return kept.get(item);
  const slots = ctx.slotsOf(item.ref);
  const seats = !slots || slots.error ? null : resolverFor(slotEnv(item, slots, ctx.compByRef, ctx.redirects), item.swaps || {});
  kept?.set(item, seats);
  return seats;
}
export function seatedJacket(item, end, ctx, kept = null) {
  if (!item || !loaded(ctx)) return null;
  const port = portPathOf(end?.path ?? '');
  if (!port || isElementId(port)) return null;
  const path = `${port}-occupant`;
  const ref = seatsOf(item, ctx, kept)?.refAt(path);
  if (!ref) return null;
  const set = item.fields?.[path];
  if (set && typeof set === 'object' && Object.hasOwn(set, JACKET_FIELD) && set[JACKET_FIELD] != null && set[JACKET_FIELD] !== '')
    return hexColor(set[JACKET_FIELD]);
  return partJacket(partOf(ctx.compByRef, ref), ctx.compByRef);
}
// One end of a rack's cable, with what a page read laid over the catalogue.
// A PAGE SAYS WHAT IT READ by a `jacket` key on that end's entry of its cable
// facts (`ends`, the Map `cableFacts(rack).ends` is: endKey -> {info, reason,
// jacket}): a colour, or null for an end it found bare. Where the key is
// there, it stands, since a page can see a part the rack file does not name
// (a plug it seats for the cable). Where it is not, the catalogue answers
// (seatedJacket). `parts` is {slotsOf, compByRef}.
export function jacketAt(rack, end, {ends = null, parts = null} = {}, kept = null) {
  const got = ends?.get?.(endKey(end));
  if (got && Object.hasOwn(got, 'jacket')) return hexColor(got.jacket);
  return seatedJacket((rack.items || []).find(i => i.id === end?.item) || null, end, parts, kept);
}
// The `jacketOf` reader the plans and the exports take (cable-rules.js
// colorFacts): end -> the jacket colour it states, or null. Made for one
// rack as it is, and made anew for the next: it keeps what each item seats.
export const jacketsFor = (rack, facts = {}) => { const kept = new Map(); return end => jacketAt(rack, end, facts, kept); };

// ── the panels this configuration shows ─────────────────────────────────
// `configs.json` lists the bays and cages of EVERY panel the device has, each
// under the name of its panel, and a device may have more than one panel for
// a face: a 24-port build of a switch shows `front-24` where the 48-port one
// shows `front`. Which one a configuration shows is its own `views`
// (`{front: 'front-24'}`; a face it does not name shows the panel of that
// name). slotEnv keeps every panel's slots, as the readers of a path need
// them. THIS keeps only the slots of the panels the item's configuration
// shows, each with `view` as the face it is on, so that a slot of another
// build of the device is never taken for one of this build.
const SIX = ['front', 'rear', 'left', 'right', 'top', 'bottom'];
export function shownEnv(item, slots, compByRef = null, redirects = null) {
  const env = slotEnv(item, slots, compByRef, redirects);
  const faceOf = new Map(SIX.map(face => [env.cfg?.views?.[face] ?? face, face]));
  const shown = s => (faceOf.has(s.view) ? [{...s, view: faceOf.get(s.view)}] : []);
  return {...env, bays: env.bays.flatMap(shown), cages: env.cages.flatMap(shown)};
}

// ── a slot of the device itself ─────────────────────────────────────────
// AN END ON ONE OF THE DEVICE'S OWN CONNECTOR SLOTS (an outlet of a PDU, a
// chassis inlet, a ground stud): `<ref>.configs.json` lists the slot, its
// view and what it accepts, so whether a cable lands there is answered here.
// It is asked ONLY where a page read the panel and found no port at the path,
// which is what a page that knows class `port` alone says of every such
// slot; an end the page did not read, or read as a port, is left as it was.
// ONLY A SLOT THIS CONFIGURATION BUILDS: a page that knows class `port` alone
// says "no port" both of a slot that is drawn and of a path with nothing
// drawn, so the slot is looked for on the panel the configuration shows for
// that face (shownEnv) and nowhere else. Port 29 of a 48-port panel is not on
// the 24-port build, whatever the device lists.
//
// WHAT A PAGE HANDS IN, `ctx.drawnAt(end)`: the ref of the component drawn at
// the end's path on that panel (the `data-ref` of the element whose
// `data-path` is the path, a `-occupant` left off), or null. configs.json
// does not say what part presents a slot, so only the drawing knows. With it
// an end says what it is (power or ground, outlet or inlet, AC or DC) and an
// outlet that is no slot is named in its reason. WITHOUT IT NOTHING IS
// GUESSED: the end lands all the same, with no family and no direction, and
// an outlet that is no slot reads "is not on this panel" as before.
//   {facts, info}   facts to lay over the page's; info only when it landed
const FACES = ['front', 'rear'];
function drawnComp(end, ctx) {
  if (typeof ctx?.drawnAt !== 'function') return null;
  let ref = null;
  try { ref = ctx.drawnAt(end); } catch { ref = null; }
  const comp = ref ? partOf(ctx.compByRef, String(ref).split(':')[0]) : null;
  return comp ? {comp, ref: String(ref).split(':')[0]} : null;
}
export function ownSlot(item, end, ctx) {
  return withDcOnPanel(item, end, ctx, ownBase(item, end, ctx));
}
function ownBase(item, end, ctx) {
  if (!item || !loaded(ctx)) return null;
  const p = portPathOf(end?.path ?? '');
  if (!p || p.includes(MODULE) || isElementId(p)) return null;
  const slots = ctx.slotsOf(item.ref);
  if (!slots || slots.error) return null;
  const view = end.view === 'rear' ? 'rear' : 'front';
  const takes = shownEnv(item, slots, ctx.compByRef, ctx.redirects).cages.filter(g => g.id === p && takesCableEnd(g, ctx.compByRef));
  const here = takes.find(g => g.view === view);
  const drawn = drawnComp(end, ctx);
  if (here) return {facts: {port: true, slot: true, cage: false, occupied: false, onView: view},
                    info: slotInfo(here, drawn ? [drawn.comp] : [], end, ctx.compByRef)};
  const side = takes.find(g => !FACES.includes(g.view));
  if (side) return {facts: {side: side.view}};
  return drawn && !takes.length ? {facts: {part: modelOf(drawn.comp, drawn.ref)}} : null;
}

// THE PATHS, ON ONE PANEL OF A DEVICE, OF THE SLOTS A CABLE LANDS ON: what a
// page hands zones.js readSvg as `ends`, so that its ports include a power
// inlet, an outlet, a DC terminal's screws and a ground stud. The device's
// own connector slots on that panel, and those of what its bays there hold,
// to any depth of parts (a supply's terminal, and the screws of that
// terminal), each where cable-rules.js takesCableEnd says so. A slot whose
// part is of class `port` is in the list too; readSvg reads that one as the
// port it is.
export function cableEndPaths(item, view, ctx) {
  if (!item || !loaded(ctx)) return [];
  const slots = ctx.slotsOf(item.ref);
  if (!slots || slots.error) return [];
  // the panels this configuration shows, and no other build's (shownEnv)
  const env = shownEnv(item, slots, ctx.compByRef, ctx.redirects), swaps = item.swaps || {};
  const R = resolverFor(env, swaps), out = new Set();
  const take = path => { if (takesCableEnd(R.entryAt(path), ctx.compByRef)) out.add(path); };
  const under = (comp, base, depth) => {
    for (const q of list(comp?.parts)) {
      take(`${base}/${q.id}`);
      if (depth < 4) under(partOf(ctx.compByRef, q.ref), `${base}/${q.id}`, depth + 1);
    }
  };
  for (const g of env.cages) if (g.view === view) take(g.id);
  for (const b of slotTree(env, swaps).bays)
    if (b.view === view && b.holds) under(partOf(ctx.compByRef, b.holds), `${b.path}/module`, 0);
  return [...out];
}

// ── the ends of a part beside the rack (P-0019) ─────────────────────────
// A PART BESIDE THE RACK (a zero-U PDU) is no rack item, and a page reads no
// panel of it for its cable facts. Every end on it is one of its own
// connector slots, which the catalogue lists with where each is on its panel
// (`mate`, the point a plug meets, else `at`: mm from the top left of the
// panel as drawn). So the catalogue answers for it whole: what each slot is,
// its plug, and where it is on the part, `x` across the panel and `y` up from
// the part's bottom. Where no part says what a slot is, the coupler it is
// does (cable-rules.js couplerRole): a C13 is an outlet. In natural order.
//   [{path, view, slot, type, connector, kind, plug, info, x?, y?}]
function zeroUInfo(slot, end, compByRef) {
  const info = slotInfo(slot, [], end, compByRef), role = couplerRole(slot.interface);
  if (info.family || !role) return info;
  const said = {family: 'power', mode: null, role};
  return {...info, ...said, connector: connectorName(slot, said)};
}
export function zeroUEnds(z, ctx, end = null) {
  if (!z || !loaded(ctx)) return [];
  const slots = ctx.slotsOf(z.ref);
  if (!slots || slots.error) return [];
  const h = Number(ctx.chassisOf?.(z.ref)?.h) || null;
  const env = shownEnv(z, slots, ctx.compByRef, ctx.redirects);
  const place = (p, base = [0, 0]) => (p && h && p.every(Number.isFinite) && base.every(Number.isFinite)
    ? {x: base[0] + p[0], y: h - (base[1] + p[1])} : {});
  const own = env.cages
    .filter(g => FACES.includes(g.view) && takesCableEnd(g, ctx.compByRef))
    .map(g => {
      const info = zeroUInfo(g, end?.path === g.id ? end : null, ctx.compByRef);
      const p = Array.isArray(g.mate) ? g.mate : Array.isArray(g.at) ? g.at : null;
      return {path: g.id, view: g.view, slot: g, type: couplerType(g.interface), connector: info.connector, kind: endKind(info),
              plug: info.plug, info, ...place(p)};
    });
  return [...own, ...moduleEnds(z, env, ctx, end, place)]
    .sort((a, b) => natural.compare(a.path, b.path) || natural.compare(a.view, b.view));
}

// THE PORTS OF THE MODULES IN A PART'S BAYS (P-0038): a vertical PDU's network
// card has ports a cable ends on, as a switch's supply has its inlet. Each
// bay of the part holds what the part's swaps put there, else what its
// configuration builds, else what the bay ships with (the way a rack device's
// bay is read, slots.js holdsAt), and each connector slot the held part
// presents that takes a cable end is an end at `<bay>/module/<port>`, on the
// bay's panel. Its place on the part is the bay's `at` plus the slot's `mate`
// in the module's frame (else its `at`); a bay turned in its slot is not
// placed, since its parts are then drawn turned, and the cable ends at the
// part without a point. A port is data unless the slot is a power coupler.
// `media` and `speed` are the placement's on the module (the sensor jack of an
// eNMC is `rj45-telemetry`, not Ethernet).
function moduleEnds(z, env, ctx, end, place) {
  const swaps = z.swaps && typeof z.swaps === 'object' && !Array.isArray(z.swaps) ? z.swaps : {}, out = [];
  for (const bay of env.bays) {
    if (!FACES.includes(bay.view)) continue;
    const ref = holdsAt(env, swaps, bay.id, bay), comp = partOf(ctx.compByRef, ref);
    if (!comp) continue;
    const turned = Number(bay.rotate) % 360 !== 0 && bay.rotate != null;
    for (const g of list(comp.cages)) {
      if (!takesCableEnd(g, ctx.compByRef)) continue;
      const path = `${bay.id}${MODULE}${g.id}`, attrs = list(comp.parts).find(q => q.id === g.id)?.attrs || {};
      let info = zeroUInfo(g, end?.path === path ? end : null, ctx.compByRef);
      const power = info.family === 'power' || info.family === 'ground';
      const connector = couplerType(g.interface) ? info.connector : `${String(g.interface || 'cable').toUpperCase()} port`;
      if (!power) info = {...info, ...connectorOf({portMedia: attrs.media || '', iface: g.interface || '', role: attrs.role || ''}), connector};
      const p = Array.isArray(g.mate) ? g.mate : Array.isArray(g.at) ? g.at : null;
      out.push({path, view: bay.view, slot: g, module: true, type: couplerType(g.interface), connector: info.connector,
                kind: power ? endKind(info) : 'data', plug: info.plug, info,
                ...(attrs.media ? {media: attrs.media} : {}), ...(attrs.speed ? {speed: attrs.speed} : {}),
                ...(turned || !Array.isArray(bay.at) ? {} : place(p, bay.at))});
    }
  }
  return out;
}
// The words for the ends a part beside the rack has, by type: "C13
// outlet-a1, outlet-a3; C39 outlet-a2", for a refusal that offers them.
export function zeroUEndsText(ends) {
  const by = new Map();
  for (const e of ends) { const k = e.type || e.connector || 'other'; by.set(k, [...(by.get(k) || []), e.view === 'rear' ? `${e.path} (rear)` : e.path]); }
  return [...by].map(([k, paths]) => `${k} ${paths.join(', ')}`).join('; ');
}
// One end on a part beside the rack, answered from the catalogue. null when
// the catalogue is not loaded: the end is then not checked, never called
// loose for want of a page that could not read it.
function zeroUEndFacts(z, end, ctx) {
  if (!loaded(ctx)) return null;
  const view = end.view === 'rear' ? 'rear' : 'front', p = portPathOf(end.path);
  const name = z.label || z.id;
  if (isElementId(p)) return {facts: {item: true}, reason: looseReason(end, {item: true})};
  const ends = zeroUEnds(z, ctx, end), here = ends.find(e => e.path === p && e.view === view);
  if (here) return {facts: {item: true, drawing: true, port: true, slot: !here.module, cage: false, occupied: false, onView: view, holder: null},
                    info: here.info, reason: null};
  const other = ends.find(e => e.path === p);
  const facts = {item: true, drawing: true, port: false, holder: null, ...(other ? {onView: other.view} : {})};
  return {facts, reason: other ? `${p} is on the ${other.view} panel of ${name}; give view "${other.view}"`
    : ends.length ? `${name} has no ${p}; it has ${zeroUEndsText(ends)}` : `${name} has nothing a cable can end on`};
}

// ── what the page read, with what the catalogue knows laid over it ──────
// One end: `got` is the page's {facts, info, reason} for it, or nothing. An
// element id is never an address, whatever a drawing matched it to. Where the
// catalogue answers (seatedPort), its answer stands, unless the page found the
// panel has no drawing at all; where it cannot, the page's does.
export function settleEnd(rack, end, got, ctx) {
  const item = (rack.items || []).find(i => i.id === end.item) || null;
  if (!item) {
    // a part beside the rack: the catalogue answers, over a page that found no item of that id
    const z = zeroUById(rack, end.item);
    return (z && zeroUEndFacts(z, end, ctx)) || (z ? null : got ?? null);
  }
  if (isElementId(end.path)) return {...got, reason: looseReason(end, {item: true})};
  const own = seatedPort(item, end, ctx);
  if (!own && got?.facts?.drawing === true && got.facts.port === false && !got.facts.holder) {
    // the device's own slot, where the page found no port (ownSlot)
    const mine = ownSlot(item, end, ctx);
    if (!mine) return got;
    const facts = {...got.facts, ...mine.facts};
    return {...got, facts, ...(mine.info ? {info: mine.info.family || !got.info?.family ? mine.info : {...got.info, plug: mine.info.plug, ...(mine.info.note ? {note: mine.info.note} : {})}} : {}),
            reason: looseReason(end, facts)};
  }
  if (!own || got?.facts?.drawing === false) return got ?? null;
  const {info, ...facts} = own;
  // the screws to name for an end on a terminal: those no other cable is on
  if (facts.under) facts.under = facts.under.filter(x => !(rack.cables || []).some(c => [c.a, c.b].some(e =>
    e.item === end.item && e.view === end.view && portPathOf(e.path) === x)));
  // the same for the DC ports to give: those no cable is on, at the port or at any pole
  if (facts.dcGive) {
    const read = dcReader(rack, ctx), ports = dcPortsOf(item, ctx);
    const used = new Set((rack.cables || []).flatMap(c => [c.a, c.b]).map(e => read(e)?.key).filter(Boolean));
    facts.dcGive = facts.dcGive.filter(x => !used.has(`${item.id}|${ports.find(q => q.path === x)?.view}|${x}`));
  }
  // an end that lands by its slot is what its part says it is; a port, what the page read of it
  return {...got, facts: {...got?.facts, ...facts}, info: facts.slot ? info : got?.info?.family ? got.info : info ?? got?.info, reason: looseReason(end, facts)};
}
// The page's `cableFacts(rack).ends` settled: every cabled end of the rack,
// and `extra` ends (the two of a cable still being made), as cableFacts takes
// them. Map(endKey -> {facts?, info?, reason}); an end neither the page nor
// the catalogue answered for stays out of it, which reads as not checked.
export function settleEnds(rack, ends, ctx, extra = []) {
  const page = new Map(ends || []), out = new Map(page);
  for (const end of [...(rack.cables || []).flatMap(c => [c.a, c.b]), ...extra]) {
    const k = endKey(end), got = settleEnd(rack, end, out.get(k), ctx);
    // (an end on a part beside the rack that the catalogue cannot answer is
    // not checked: what a page said of it, which found no item, is dropped)
    if (got) out.set(k, got); else out.delete(k);
  }
  // A SLOT THAT TAKES SEVERAL PLUGS, at an end that states none, takes the
  // one that pairs with the plug at the cord's other end (cable-rules.js
  // endPlug): settled again with that plug known.
  for (const c of rack.cables || []) for (const [s, o] of [['a', 'b'], ['b', 'a']]) {
    const k = endKey(c[s]), mine = out.get(k), far = out.get(endKey(c[o]))?.info?.plug;
    if (!mine?.info?.note || c[s].plug || !far) continue;
    const again = settleEnd(rack, {...c[s], farPlug: far}, page.get(k), ctx);
    if (again?.info?.plug && !again.info.note) out.set(k, again);
  }
  return out;
}

// ── DC ports (docs/dc-power-design.md sections 5.2 and 5.4) ─────────────
// A DC PORT IS THE END A FEED LANDS ON, and its poles are taken together. The
// build publishes the ports a part states as `dc-ports`: on the component in
// the part's own frame (`input`, a pole's slot its id inside the part), and per
// configuration with the drawing's paths for what the configuration places.
// dcPortsOf reads them for one rack item:
//   a part placed on the device   the configuration's entries (the placement's
//                                 `dc` override is applied there), those whose
//                                 path is not under a bay
//   a part in a bay, at any depth the seat resolver reads (swaps over the
//                                 configuration over the bay's default): the
//                                 seated component's entries, joined under
//                                 `<bay>/module`. The configuration's own
//                                 entry for a bay is not read, since the item's
//                                 swaps may seat another part there
// A PORT IS ADDRESSED `<part path>/<port id>`, and a pole by its slot's path.
//   kind      'slots' when every pole's slot is a connector slot (a screw, a
//             stud, a stud pair), 'points' when none is and the part itself is
//             the connector slot the contacts belong to (the P40). Neither: the
//             port is left out, as lint refuses it. Nothing is inferred.
//   view      the panel of its poles' slots (slots), or of its connector
//             slot (points); a part in a bay is on the bay's panel unless the
//             slot is on the part's back. Poles on two panels, or a panel the
//             catalogue does not say: null, and the port is neither offered nor landed
//   lands     every pole's slot (slots), or the connector (points), takes a
//             cable end (takesCableEnd)
//   connector the connector slot's path for a points port, else null
//   poles     [{role, path, 'stand-in'?}], in the order the cable lists its conductors
// [] without the catalogue. Cached per item, which the kit never mutates.
const joinPath = (base, tail) => (base && tail ? `${base}/${tail}` : base || tail);
const copy = v => (v == null ? v : structuredClone(v));
const dcCache = new WeakMap();
const dcSeats = new WeakMap();   // port -> {slots: [slot at each pole], connector}
export function dcPortsOf(item, ctx) {
  if (!item || typeof item !== 'object' || !loaded(ctx)) return [];
  const slots = ctx.slotsOf(item.ref);
  if (!slots || slots.error) return [];
  const seen = dcCache.get(item);
  if (seen && seen.slots === slots && seen.compByRef === ctx.compByRef && seen.redirects === (ctx.redirects ?? null)) return seen.ports;
  const ports = readDcPorts(item, slots, ctx);
  dcCache.set(item, {slots, compByRef: ctx.compByRef, redirects: ctx.redirects ?? null, ports});
  return ports;
}
function readDcPorts(item, slots, ctx) {
  const env = shownEnv(item, slots, ctx.compByRef, ctx.redirects), swaps = item.swaps || {};
  const raw = list(env.cfg?.['dc-ports']).filter(q => typeof q?.path === 'string' && !q.path.includes(MODULE));
  for (const b of slotTree(env, swaps).bays) {
    const comp = b.holds ? partOf(ctx.compByRef, b.holds) : null;
    const base = `${b.path}/module`, ref = b.holds ? String(b.holds).split(':')[0] : null;
    for (const q of list(comp?.['dc-ports']))
      raw.push({...q, ref, path: joinPath(base, q.path ?? q.id), poles: list(q.poles).map(o => ({...o, slot: joinPath(base, o.slot)}))});
  }
  const R = resolverFor(env, swaps);
  return raw.flatMap(q => dcPort(q, R, env, ctx) ?? []).sort((a, b) => natural.compare(a.path, b.path));
}
function dcPort(q, R, env, ctx) {
  const id = String(q.id ?? ''), poles = list(q.poles);
  if (!id || !String(q.path).endsWith(`/${id}`) || !poles.length || !poles.every(o => o && typeof o.slot === 'string' && o.slot)) return null;
  const part = q.path.slice(0, -(id.length + 1));
  const entries = poles.map(o => R.entryAt(o.slot));
  const isSlot = e => e?.kind === 'connector';
  let kind = null, connector = null;
  if (entries.every(isSlot)) kind = 'slots';
  else if (!entries.some(isSlot) && isSlot(R.entryAt(part))) { kind = 'points'; connector = R.entryAt(part); }
  if (!kind) return null;
  const lands = kind === 'slots' ? entries.every(e => takesCableEnd(e, ctx.compByRef)) : takesCableEnd(connector, ctx.compByRef);
  // the panel: a slot of the device says its own; one on a part in a bay is on the bay's, or the other on the part's back
  const bay = env.bays.find(b => part.startsWith(`${b.id}/`));
  const viewOf = e => { const v = e.view ?? (bay ? (e.back ? OTHER[bay.view] : bay.view) : null); return FACES.includes(v) ? v : null; };
  const views = new Set((kind === 'slots' ? entries : [connector]).map(viewOf));
  const port = {id, path: q.path, part, ref: q.ref ?? null, direction: q.direction, voltage: copy(q.voltage ?? null), 'rating-a': q['rating-a'] ?? null,
                awg: copy(q.awg ?? null), side: q.side ?? null, kind, view: views.size === 1 ? [...views][0] : null, lands, connector: connector ? part : null,
                poles: poles.map(o => ({role: o.role, path: o.slot, ...(o['stand-in'] ? {'stand-in': copy(o['stand-in'])} : {})}))};
  dcSeats.set(port, {slots: kind === 'slots' ? entries : [], connector});
  return port;
}

// WHAT AN END'S PATH NAMES among an item's DC ports: {port, end: 'port'},
// {port, end: 'pole', pole} (a slots port's pole slot, `pole` its index),
// {port, end: 'connector'} (a points port's connector slot, when it is the
// only port on it: where several are, the end is a plain slot) or
// {port, end: 'contact'} (a points port's contact, which is no end). null where
// the path is none of these. THE PANEL IS NOT ASKED HERE.
export function dcEndOf(item, path, ctx) {
  const ports = dcPortsOf(item, ctx);
  if (!ports.length) return null;
  const port = ports.find(q => q.path === path);
  if (port) return {port, end: 'port'};
  for (const q of ports) {
    const i = q.kind === 'slots' ? q.poles.findIndex(x => x.path === path) : -1;
    if (i >= 0) return {port: q, end: 'pole', pole: i};
  }
  const here = ports.filter(q => q.connector === path);
  if (here.length === 1) return {port: here[0], end: 'connector'};
  if (here.length > 1) return null;
  const contact = ports.find(q => q.kind === 'points' && q.poles.some(x => x.path === path));
  return contact ? {port: contact, end: 'contact'} : null;
}

// How a pole is named for a person: "BATT pole", else "pole terminal-48v".
const roleWord = r => (r === 'unstated' ? '?' : String(r).toUpperCase());
const poleName = (port, i) => (port.poles[i].role !== 'unstated' ? `${roleWord(port.poles[i].role)} pole` : `pole ${port.poles[i].path.split('/').pop()}`);
// A PORT FOR A PERSON, after docs/dc-power-design.md section 8: "input, RTN /
// BATT, -48 V, 18 A, side A", each part only where the catalogue states it.
const dcName = port => [port.id, port.poles.map(q => roleWord(q.role)).join(' / '), port.voltage?.nominal != null ? `${port.voltage.nominal} V` : null,
  port['rating-a'] != null ? `${port['rating-a']} A` : null, port.side ? `side ${String(port.side).toUpperCase()}` : null].filter(Boolean).join(', ');
// The plug each pole takes: its own slot's (endPlug), or the connector's for every contact. A plug the end
// states is read for each pole (`only`: just that one, for a pole end).
function polePlugs(port, ctx, stated, only = null) {
  const seat = dcSeats.get(port);
  return port.poles.map((_, i) => endPlug(port.kind === 'slots' ? seat.slots[i] : seat.connector, ctx.compByRef, only === null || only === i ? stated : null));
}
const figuresOf = port => ({direction: port.direction, voltage: copy(port.voltage), 'rating-a': port['rating-a'], awg: copy(port.awg), side: port.side});
// The `dc` an end carries (see the README): the port's facts, the end it is and its poles with the plug each takes.
function dcOf(port, end, pole, ctx, stated) {
  const plugs = polePlugs(port, ctx, stated, end === 'pole' ? pole : null);
  const dc = {path: port.path, end, ...(end === 'pole' ? {pole, role: port.poles[pole].role} : {}), kind: port.kind, connector: port.connector,
              ...figuresOf(port),
              poles: port.poles.map((q, i) => ({role: q.role, path: q.path, plug: plugs[i].plug, ...(q['stand-in'] ? {'stand-in': copy(q['stand-in'])} : {})}))};
  return {dc, plugs};
}
// An end at a DC port's path: a power end, an inlet for an input and an outlet for an output.
function portInfo(port, ctx, stated) {
  const {dc, plugs} = dcOf(port, 'port', null, ctx, stated);
  const notes = [...new Set(plugs.flatMap(x => x.note ?? []))];
  return {family: 'power', mode: 'dc', role: port.direction === 'output' ? 'outlet' : 'inlet',
          plug: plugs.every(x => x.plug === plugs[0].plug) ? plugs[0].plug : null, connector: dcName(port), ...(notes.length ? {note: notes.join('; ')} : {}), dc};
}
// A port, or one of its poles, as the entry freePorts and slotEnds list:
// {path, view, kind, connector, plug, dc}. A pole's `dc` names its port.
export function dcEntryOf(port, ctx, pole = null) {
  const plugs = polePlugs(port, ctx, null);
  const figures = {...figuresOf(port), poles: port.poles.map((q, i) => ({role: q.role, path: q.path, plug: plugs[i].plug}))};
  if (pole === null) return {path: port.path, view: port.view, kind: 'power', connector: dcName(port),
                             plug: plugs.every(x => x.plug === plugs[0].plug) ? plugs[0].plug : null, dc: figures};
  return {path: port.poles[pole].path, view: port.view, kind: 'power', connector: `${port.id} ${poleName(port, pole)}`, plug: plugs[pole].plug,
          dc: {...figures, pole: {port: port.path, role: port.poles[pole].role}}};
}
// The DC ports whose paths a free-port list shows instead of the slots under them: a slots port's pole slots
// and the connector slot of a points port.
export function dcCovered(item, ctx) {
  return new Set(dcPortsOf(item, ctx).filter(q => q.lands && q.view).flatMap(q => (q.kind === 'slots' ? q.poles.map(x => x.path) : [q.connector])));
}

// ONE CABLE PER PORT, ACROSS A PORT AND ITS POLES (cable-rules.js portFree): the
// reader of a rack, end -> {key, pole, name} for an end that is a DC port, a
// pole or a connector with one port on it, on the panel the port is on; null
// for any other end (a contact is none). `key` names the port, `pole` the
// conductor (null: the whole port), `name` the pole for a person. null where
// the catalogue is not loaded.
export function dcReader(rack, ctx) {
  if (!loaded(ctx)) return null;
  return end => {
    const item = (rack.items || []).find(i => i.id === end?.item);
    const hit = item ? dcEndOf(item, portPathOf(end.path ?? ''), ctx) : null;
    const view = end?.view === 'rear' ? 'rear' : 'front';
    if (!hit || hit.end === 'contact' || !hit.port.lands || hit.port.view !== view) return null;
    return {key: `${item.id}|${view}|${hit.port.path}`, pole: hit.end === 'pole' ? hit.pole : null, name: hit.end === 'pole' ? poleName(hit.port, hit.pole) : null};
  };
}

// WHAT IS LOOSE ABOUT AN END AT A DC PORT, in looseReason's facts, or null: a
// contact of a connector that takes a plug, and a port named on the panel it is not on.
function dcLoose(item, end, ctx) {
  const hit = dcEndOf(item, portPathOf(end?.path ?? ''), ctx);
  if (!hit || !hit.port.lands) return null;
  const view = end.view === 'rear' ? 'rear' : 'front';
  if (hit.end === 'contact')
    return {dcContact: {part: hit.port.part, plug: endPlug(dcSeats.get(hit.port).connector, ctx.compByRef).plug, port: hit.port.path}};
  return hit.end === 'port' && hit.port.view && hit.port.view !== view ? {dcPanel: hit.port.view} : null;
}

// THE LANDING OF A DC END ON A PART IN A BAY, over what seatedBase answered (own):
//   a port path lands when its panel is the port's; named on the other panel it is loose
//   a pole slot and a lone connector slot land as they did (own), and gain `dc`
//   a contact is loose
//   the path of a part whose poles are a DC port's: the ports to give (dcGive)
// An answer that already lands is never changed, and a path no DC port names is own.
function withDcInBay(item, end, ctx, own) {
  if (!item || !loaded(ctx)) return own;
  const p = portPathOf(end?.path ?? '');
  if (!p.includes(MODULE) || isElementId(p)) return own;
  const ports = dcPortsOf(item, ctx);
  if (!ports.length) return own;
  const hit = dcEndOf(item, p, ctx), view = end.view === 'rear' ? 'rear' : 'front';
  if (!hit) {
    if (!own || own.port || !own.part || own.onView) return own;
    const give = ports.filter(q => q.lands && q.view && q.poles.some(x => x.path.startsWith(`${p}/`))).map(q => q.path);
    return give.length ? {...own, dcGive: give} : own;
  }
  const {port} = hit;
  if (hit.end === 'pole' || hit.end === 'connector')
    return own?.port && own.slot ? {...own, info: {...own.info, dc: dcOf(port, hit.end, hit.pole, ctx, end.plug).dc}} : own;
  if (own?.port || !port.lands) return own;
  const comp = partOf(ctx.compByRef, port.ref);
  const holder = {path: port.part.slice(0, -'/module'.length), part: modelOf(comp, port.ref), ref: port.ref};
  const base = {item: true, drawing: true, port: false, cage: false, occupied: false, onView: null, back: false, holder};
  if (hit.end === 'contact') return {...base, ...dcLoose(item, end, ctx)};
  if (!port.view) return own;
  if (port.view !== view) return {...base, dcPanel: port.view};
  return {...base, port: true, slot: true, onView: view, info: portInfo(port, ctx, end.plug)};
}
// The same for a part placed on the device (ownBase answers `own`: a slot of the device).
function withDcOnPanel(item, end, ctx, own) {
  if (!item || !loaded(ctx)) return own;
  const p = portPathOf(end?.path ?? '');
  if (!p || p.includes(MODULE) || isElementId(p)) return own;
  const hit = dcEndOf(item, p, ctx), view = end.view === 'rear' ? 'rear' : 'front';
  if (!hit) return own;
  const {port} = hit;
  if (hit.end === 'pole' || hit.end === 'connector')
    return own?.facts?.port && own.info ? {...own, info: {...own.info, dc: dcOf(port, hit.end, hit.pole, ctx, end.plug).dc}} : own;
  if (own?.facts?.port || !port.lands) return own;
  if (hit.end === 'contact') return {facts: dcLoose(item, end, ctx)};
  if (!port.view) return own;
  if (port.view !== view) return {facts: {dcPanel: port.view}};
  return {facts: {port: true, slot: true, cage: false, occupied: false, onView: view}, info: portInfo(port, ctx, end.plug)};
}

// WHERE A DEVICE MAY GO. Pure: the rack, the candidate, and a
// chassisOf(ref) -> {ru, h, d} that the page backs with rack.json, as the kit loads it.
// Every refusal is a sentence, because the catalogue shows it beside the device
// it grays out - "no" without a reason is a puzzle.
//
// Depth along the rack: a front-face device runs [0, d] back from the front
// rail; a rear-face one runs [railDepth - d, railDepth] forward from the rear
// rail. On four posts the two share a U when those do not overlap, which is
// dFront + dRear <= railDepth. Two-post rails are one plane that every body
// passes through, so there a U is never shared.

import {RU, OPENING, SIDES as RAILS} from './rails.js';
import {uLabel, uText, isPosition, zeroUOf, zeroUBottom, zeroUBottomMm, zeroUOffset, SIDES, holderOf, holdersOf, railWidth, RAIL_WIDTH_IN, firstU, rollOf} from './model.js';

// ── HEIGHTS, SPANS AND BOXES (docs/rack-file-v4-design.md section 2.4) ─────
// PUBLIC: unitsOf, spanOf, itemBox, spanText (kit/README.md). The other names
// exported between here and isRackFace are for the kit's own files.
// These own the answers, and no other file under kit/rack/ computes them: how
// many units a device is, which half units an item fills, and where its body
// is in millimetres. A position is a whole unit or a half (`ru` in steps of
// 0.5, counted bottom-up from 1), so a span is HALF-OPEN: a 1.5U item at U1
// fills [1, 2.5), and a 1U item at U2 meets it.

// The height of a device in units: its stated `ru` rounded up to the next
// half, never less than 0.5; 1 for a device that states none.
export function unitsOf(chassis) {
  const r = chassis?.ru == null ? NaN : Number(chassis.ru);
  return Number.isFinite(r) ? Math.max(0.5, Math.ceil(r * 2 - 1e-9) / 2) : 1;
}
// ROLLED A QUARTER TURN (`roll: 90` or `270`, section 6) an item stands on its
// side: its width is up the rack and its height across the opening.
export const isQuarter = item => rollOf(item) === 90 || rollOf(item) === 270;
// The height of an ITEM in units, as mounted: its device's, or, rolled a
// quarter turn, its width over one unit, rounded up to a whole unit.
export function itemUnits(item, chassisOf) {
  const c = chassisOf(item.ref);
  return isQuarter(item) && Number(c?.w) > 0 ? Math.max(1, Math.ceil(Number(c.w) / RU - 1e-9)) : unitsOf(c);
}
// [lo, hi): the units an item fills, from its bottom up to, not including, hi.
export const spanOf = (item, chassisOf) => [item.ru, item.ru + itemUnits(item, chassisOf)];
// Two spans meet when each starts below the end of the other.
export const spansMeet = (a, b) => a[0] < b[1] && b[0] < a[1];
// THE BODY AS MOUNTED, in mm above the bottom of the rails: {y0, y1, h, lo,
// hi}. `lo` and `hi` are the edges of its span; `h` is the height the
// catalogue gives the body, or the span where it gives none. A body that is
// not as tall as its span is CENTRED in it, always, and one that is taller
// overhangs both edges equally: the holes of a unit are symmetric about its
// middle, and so is the ear that bolts to them.
// Rolled 180 degrees it is the same box. Rolled a quarter turn its height and
// width swap: `h` is the width of the device, and the box also gives `w`, the
// height of the device, which then lies across the opening.
export function itemBox(rack, item, chassisOf) {
  const c = chassisOf(item.ref), q = isQuarter(item);
  const [a, b] = spanOf(item, chassisOf);
  const lo = (a - 1) * RU, hi = (b - 1) * RU;
  const tall = Number(q ? c?.w : c?.h);
  const h = tall > 0 ? tall : hi - lo;
  const y0 = lo + (hi - lo - h) / 2;
  return {y0, y1: y0 + h, h, lo, hi, ...(q ? {w: Number(c?.h) > 0 ? Number(c.h) : RU} : {})};
}
// THE LINE AN ITEM IS CENTRED ON ACROSS THE RACK, in mm from the centre line
// of the rack, right as seen from the front: 0 for anything across the
// opening, and the hole line of its rail for a narrow part on one rail.
export function centreX(item, chassisOf) {
  const rail = railOf(item, chassisOf);
  if (!rail) return 0;
  return ((rail === 'left') === (item.face !== 'rear') ? RAILS[0] : RAILS[1]).hole;
}
// A POINT OF AN UPRIGHT ITEM, TURNED BY ITS ROLL. `p` is a point in the rack
// ({x, y}: mm right of the centre line as seen from the front, and mm above
// the bottom of the rails) where it would be were the item mounted upright;
// the answer is where it is as mounted. The turn is about the centre of the
// box, clockwise as the item is seen in the elevation of the face it is on,
// which from the front of the rack is anticlockwise for an item on the rear.
// An item with no roll is answered with the very point it was given.
export function rollPoint(rack, item, p, chassisOf) {
  const roll = rollOf(item);
  if (!roll) return p;
  const cx = centreX(item, chassisOf);
  const box = itemBox(rack, item, chassisOf);
  const up = itemBox(rack, {...item, roll: undefined}, chassisOf);
  const dx = p.x - cx, dy = p.y - (up.y0 + up.y1) / 2, cy = (box.y0 + box.y1) / 2;
  if (roll === 180) return {...p, x: cx - dx, y: cy - dy};
  const cw = (roll === 90) === (item.face !== 'rear');   // clockwise as the front of the rack sees it
  return {...p, x: cx + (cw ? dy : -dy), y: cy + (cw ? -dx : dx)};
}
// A POINT OF A FACE AS DRAWN, IN THE RACK: `x` mm from the left edge of the
// drawing and `y` mm down from its top, on the item's own `view` (its front
// panel when none is given), through `face`, `turned` and `roll`, on the box
// itemBox gives. A panel that looks out of the back of the rack is mirrored,
// since the rack is measured as its front sees it.
export function facePoint(rack, item, {x, y, view = 'front'}, chassisOf) {
  const c = chassisOf(item.ref) || {};
  const w = Number(c.w) || 0;
  const up = itemBox(rack, {...item, roll: undefined}, chassisOf);
  const other = item.face === 'rear' ? 'front' : 'rear';
  const pane = (view === 'rear') === !!item.turned ? item.face : other;
  const cx = centreX(item, chassisOf);
  return rollPoint(rack, item, {x: cx + (pane === 'rear' ? w / 2 - x : x - w / 2), y: up.y1 - y}, chassisOf);
}
// WHERE A ROUTE MEETS AN ITEM when nothing finer is known (a guide, or a port
// the drawing gives no height for): the middle of its bottom unit for an item
// of one unit or more, the middle of its body for one under a unit.
export function anchorY(rack, item, chassisOf) {
  if (itemUnits(item, chassisOf) >= 1) return laneY(item.ru);
  const box = itemBox(rack, item, chassisOf);
  return (box.y0 + box.y1) / 2;
}
// The middle of the unit that starts at `ru`: a lane waypoint, which is always
// on a whole unit, and the bottom unit of an item.
export function laneY(ru) { return (ru - 0.5) * RU; }
// THE NEIGHBOURS A ROUTE LOOKS TO FOR A MANAGER: the devices of a unit or less
// just above an item and just below it, on any face, above first and nearest
// first, and a manager of any height (one that lists guides). A caller filters
// them by face and by what they carry.
// - Above an item of a unit or more: one that starts on its top edge. Above an
//   item under a unit: one that starts anywhere from its top edge to the next
//   whole unit, so a half-unit panel in the lower half of a unit still finds
//   the 1U device over that unit, as it did when it counted as a unit itself.
// - Below: one whose top edge is the bottom of the item; and one in the whole
//   unit under the unit the bottom of the item is in, when the item starts on
//   a whole unit or is under a unit itself.
export function neighbours(rack, item, chassisOf) {
  const [lo, hi] = spanOf(item, chassisOf), small = hi - lo < 1;
  // a device taller than a unit is a neighbour when it is itself a manager
  // (it lists guides, #1027): a 2U manager over a switch is one a route uses
  const near = rack.items.filter(o => o.id !== item.id
    && (itemUnits(o, chassisOf) <= 1 || Object.keys(chassisOf(o.ref)?.guides || {}).length > 0));
  const above = near.filter(o => (small ? o.ru >= hi && o.ru <= Math.ceil(hi) : o.ru === hi)).sort((p, q) => p.ru - q.ru);
  const under = Math.floor(lo) - 1;
  const below = near.filter(o => spanOf(o, chassisOf)[1] === lo
    || ((small || Number.isInteger(lo)) && Math.floor(o.ru) === under)).sort((p, q) => q.ru - p.ru);
  return [...above, ...below];
}
// THE UNITS FROM `ru` UP, IN WORDS. Whole units on a whole unit read as they
// always did: "U13", "U13-U14". Anything that starts or ends on a half names
// the half, lower and upper as the item hangs whichever way the frame counts:
// "the lower half of U7", "U13 to the lower half of U14". No two placements
// read the same.
export function unitsText(frame, ru, units) {
  const top = ru + units, U = n => uLabel(frame, n);
  if (Number.isInteger(ru) && Number.isInteger(top)) {
    const [a, b] = [U(ru), U(top - 1)].sort((x, y) => x - y);
    return a === b ? `U${a}` : `U${a}-U${b}`;
  }
  if (units === 0.5) return `the ${Number.isInteger(ru) ? 'lower' : 'upper'} half of U${U(Math.floor(ru))}`;
  // its two ends, the lower-numbered first, as a whole span reads
  const ends = [Number.isInteger(ru) ? [U(ru), `U${U(ru)}`] : [U(Math.floor(ru)), `the upper half of U${U(Math.floor(ru))}`],
                Number.isInteger(top) ? [U(top - 1), `U${U(top - 1)}`] : [U(Math.floor(top)), `the lower half of U${U(Math.floor(top))}`]]
    .sort((x, y) => x[0] - y[0]);
  return `${ends[0][1]} to ${ends[1][1]}`;
}
// The span of an item, in those words.
export const spanText = (frame, item, chassisOf) => unitsText(frame, item.ru, itemUnits(item, chassisOf));

export const REACH_MM = 50;   // within this of the far rail, a device's far panel is visible there

// A RACK-FACE PART: bolted to the rail face at a U, projecting
// outward - forward of the front rails, or behind the rear ones. It takes no
// U, so rack devices never collide with it, except a device deep enough to
// come out through the far rail into a manager there.
export const isRackFace = c => c?.mount === 'rack-face';

// A NARROW RACK-FACE PART (#926): narrower than the 450 mm clear opening of a
// 19-inch rack, such as a finger bracket. Placed with `side` it claims its
// units on that face and that rail only, so one can stand on each rail at the
// same U; any other rack-face part, and a narrow one with no side, claims both.
export const NARROW_MM = 450;
export const isNarrow = c => isRackFace(c) && Number(c?.w) > 0 && Number(c.w) < NARROW_MM;
// The rail an item is on: its `side` when its part is narrow, else null (both).
export const railOf = (item, chassisOf) => (SIDES.includes(item?.side) && isNarrow(chassisOf(item.ref)) ? item.side : null);

// A ZERO-U PART (#926) stands beside the rack at an attachment point and takes
// no rack unit (model.js zeroUOf). The mounts that are zero-U parts, in one
// place: a later mount (an in-cabinet channel) joins the list.
export const ZERO_U_MOUNTS = ['rack-side'];
export const isZeroUPart = c => ZERO_U_MOUNTS.includes(c?.mount);
// How many U it runs beside: its stated `ru`, not its drawn height (the 45U
// FS ducts are drawn 2108 mm, cover included, beside 2000 mm of rail). A part
// that states none, or 0, is measured by its height.
export const zeroUUnits = c => (Number(c?.ru) >= 1 ? Math.round(c.ru)
  : Math.max(1, Math.ceil(Number(c?.h) / RU - 1e-6) || 1));
export const zeroUSpan = (z, chassisOf) => {
  const lo = zeroUBottom(z);
  return [lo, lo + zeroUUnits(chassisOf(z.ref)) - 1];
};
// THE UNITS ITS MILLIMETRES TOUCH, for the lane a cable runs down: a part at a
// whole unit runs lo..lo+u-1 as zeroUSpan says, one hung between units also
// touches the unit it overlaps. A label says zeroUSpan, the nearest unit.
export const zeroUTouched = (z, chassisOf) => {
  const [from, to] = zeroUExtent(z, chassisOf);
  return [Math.floor(from / RU + 1e-6) + 1, Math.max(1, Math.ceil(to / RU - 1e-6))];
};
const uSpanText = (frame, lo, hi) => {
  const [a, b] = [uLabel(frame, lo), uLabel(frame, hi)].sort((x, y) => x - y);
  return a === b ? `U${a}` : `U${a}-U${b}`;
};
export const zeroUSpanText = (frame, z, chassisOf) => uSpanText(frame, ...zeroUSpan(z, chassisOf));
const no = reason => ({ok: false, reason});
// A stored unit as a refusal names it: counted from the bottom, from the
// number the frame gives its first unit (`startU`), so U1 of before is U1.
const named = (f, ru) => firstU(f) - 1 + ru;
const nameOf = (c, ref) => c?.model ?? ref;
// A part too tall for the rack from its bottom unit.
const tooTall = (f, u, lo) =>
  no(`${u}U tall; ${f.heightRU - lo + 1}U from U${uLabel(f, lo)} to the top of this ${f.heightRU}U rack.`);
const below = f => no(`Below U${firstU(f)}.`);
// AN ITEM IS BOLTED OVER A DEVICE (`on`) OR HELD BY ONE (`heldBy`), NOT BOTH
// (docs/rack-products-design.md section 7.2): refused until one is removed.
export const bothText = item => `${item.id} is on ${item.on} and held by ${holderOf(item)}: a part is bolted over a device or held by one, not both, so remove one.`;
const isBoth = item => item.on != null && holderOf(item) != null;

// NOT RACK-MOUNT. The catalogue states `mount` only when it is not "rack".
export const isRackMount = chassis => !chassis?.mount || chassis.mount === 'rack';
// The depth between the rails a body must exceed to come out of the far one:
// two-post rails are one plane, so any body does.
const between = f => (f.kind === 'two-post' ? 0 : f.railDepth);

// ── SETBACK (docs/rack-products-design.md section 8) ───────────────────────
// How far a faceplate stands behind the plane of its rail, in mm into the rack
// from the face it is on; negative is proud. Found in this order: the item's
// own `setback`; the device's default ear position in the catalogue
// (`ears.default`: `-at`, or 0 when it is named `flush` and states no `at`);
// the frame's `setback`; 0, flush. A part on the rail face or beside the rack
// has none: it bolts to the rail, and is not between them.
const finite = v => typeof v === 'number' && Number.isFinite(v);
export function setbackOf(rack, item, chassisOf) {
  const c = chassisOf(item.ref);
  if (isRackFace(c) || isZeroUPart(c)) return 0;
  if (finite(item.setback)) return item.setback;
  const ear = c?.ears?.default;
  if (ear && finite(ear.at)) return -ear.at;
  if (ear?.name === 'flush') return 0;
  return finite(rack.frame?.setback) ? rack.frame.setback : 0;
}
// How far the body reaches into the rack from the plane of its rail: its
// setback and its depth.
export const reachOf = (rack, item, chassisOf) => setbackOf(rack, item, chassisOf) + (chassisOf(item.ref)?.d ?? 0);
const deep = (c, s) => `${mm(c.d)} mm deep${s ? `, set ${s > 0 ? 'back' : 'forward'} ${mm(Math.abs(s))} mm` : ''}`;

// ── HELD ITEMS (docs/rack-file-v4-design.md section 7.1) ───────────────────
// An item with `heldBy` is on a shelf, a drawer or a rail of another item. The
// catalogue describes no host yet, so one that is not itself a rack device is
// kept in step with its host, claims no unit, and is not checked; a rack
// device standing on a shelf is fitted as any rack device is.
export const isHeld = (item, chassisOf) => holderOf(item) != null && !isRackMount(chassisOf(item.ref));
export const heldBy = (rack, hostId, chassisOf) => rack.items.filter(i => holderOf(i) === hostId && isHeld(i, chassisOf));
export const uncheckedText = (item, host, chassisOf) =>
  `${item.id} is held by ${host.id}, and ${nameOf(chassisOf(host.ref), host.ref)} states no rail to hold a device, so it is not checked.`;
export const unheldText = item => `${item.id} is held by ${holderOf(item)}, which is not in this rack: place it again, or free it.`;

// WHAT A PAGE SAYS OF A RACK IT HAS OPENED (section 7): the keys this kit
// keeps and does not yet act on, one sentence each.
export function frameNotices(rack, chassisOf) {
  const out = [], f = rack.frame;
  if (railWidth(f) !== RAIL_WIDTH_IN)
    out.push(`This rack states ${railWidth(f)} in rails; it is drawn and fitted as ${RAIL_WIDTH_IN} in.`);
  for (const z of zeroUOf(rack))
    if (typeof z.channel === 'string' && z.channel)
      out.push(`${z.label || z.ref} names the channel ${z.channel}, which is not known for this frame, so it stands at ${z.at}.`);
  for (const it of rack.items)
    if (isQuarter(it) && chassisOf(it.ref))
      out.push(`${it.label} is rolled a quarter turn: it is fitted by its rolled box and drawn turned in the elevation; its 3D solid and its cables are an outline, since how it mounts that way is not described yet.`);
  for (const it of rack.items) {
    const id = holderOf(it);
    if (id == null) continue;
    if (isBoth(it)) { out.push(bothText(it)); continue; }
    const host = rack.items.find(o => o.id === id);
    if (!host) out.push(unheldText(it));
    else if (isHeld(it, chassisOf)) out.push(uncheckedText(it, host, chassisOf));
  }
  return out;
}

// Every unit the part spans is judged, on its face and, for a narrow part on
// one rail, on that rail only (#926). A `side` on a part that is not narrow is
// no rail (railOf): it is judged across both, as it is drawn.
function fitsRackFace(rack, cand, c, chassisOf, {ignoreId = null} = {}) {
  const f = rack.frame, rd = between(f);
  const side = railOf(cand, () => c);
  const u = itemUnits(cand, () => c), lo = cand.ru, hi = cand.ru + u;
  if (cand.ru < 1) return below(f);
  // it bolts to the rail face across its width, or on one rail: a quarter
  // turn would stand it across the holes it bolts to
  if (isQuarter(cand)) return no(`${nameOf(c, cand.ref)} bolts to the rail face, so it cannot be rolled a quarter turn.`);
  // its own position is a whole unit: it bolts over a unit of holes
  if (!Number.isInteger(cand.ru))
    return no(`${nameOf(c, cand.ref)} bolts to the rail face at a whole unit, and ${uText(f, cand.ru, u)} is a half unit.`);
  if (cand.ru > f.heightRU) return {ok: false, reason: `U${named(f, cand.ru)} is past the top of this ${f.heightRU}U rack.`};
  if (hi > f.heightRU + 1) return tooTall(f, u, lo);
  if (cand.face === 'rear' && rd + c.d > f.usableDepth)
    return {ok: false, reason: `${mm(c.d)} mm out from the rear rail; this rack allows ${mm(f.usableDepth - rd)} mm there.`};
  if (cand.on != null) {
    const host = rack.items.find(i => i.id === cand.on), hc = host && chassisOf(host.ref);
    if (!host || isRackFace(hc)) return {ok: false, reason: 'A cable manager goes on a rack device.'};
    const hu = itemUnits(host, chassisOf);
    if (!(Number.isInteger(cand.unit) && cand.unit >= 1 && cand.unit <= hostUnits(host, chassisOf)))
      return {ok: false, reason: `${host.label} is ${hu}U; there is no unit ${cand.unit} on it.`};
    if (host.face !== cand.face)
      return {ok: false, reason: `${host.label} is on the ${host.face}; a manager on it goes on the ${host.face} too.`};
  }
  for (const o of rack.items) {
    if (o.id === ignoreId || isHeld(o, chassisOf)) continue;
    const oc = chassisOf(o.ref);
    if (!oc || !spansMeet([lo, hi], spanOf(o, chassisOf))) continue;
    if (isRackFace(oc)) {
      const rail = railOf(o, chassisOf);
      if (o.face === cand.face && !(side && rail && rail !== side))
        return {ok: false, reason: `Taken by ${o.label} on the ${o.face}${rail ? `, ${rail} rail` : ''}.`};
      continue;
    }
    if (o.face !== cand.face && reachOf(rack, o, chassisOf) > rd)
      return {ok: false, reason: `${o.label} is ${deep(oc, setbackOf(rack, o, chassisOf))} and reaches past the ${cand.face} rail; ` +
                                 `a ${cand.face} manager here would hit it.`};
  }
  return {ok: true};
}

const mm = x => Math.round(x);
// Closed whole-unit ranges, which the parts beside the rack are still judged by.
const overlaps = (a, b) => a[0] <= b[1] && b[0] <= a[1];

// THE WHOLE UNITS A HOST OFFERS A RACK-FACE PART, counted from the unit its
// bottom is in: 1 to ceil(ru + units) - floor(ru). For a host on a whole unit
// that is its height; one starting on a half reaches into a unit more.
export const hostUnits = (host, chassisOf) => {
  const [lo, hi] = spanOf(host, chassisOf);
  return Math.ceil(hi) - Math.floor(lo);
};
// Which of a host's units a rack-face part at `ru` is over, and back again.
export const unitOn = (host, ru) => ru - Math.floor(host.ru) + 1;
export const hostedRu = (host, unit) => Math.floor(host.ru) + unit - 1;
// How much of the whole unit `ru` an item fills, in units: 0, 0.5 or 1.
export const fillOf = (item, ru, chassisOf) => {
  const [lo, hi] = spanOf(item, chassisOf);
  return Math.max(0, Math.min(hi, ru + 1) - Math.max(lo, ru));
};

// A POSITION THE RAIL HOLES ALLOW (section 2.5). The three holes of a unit do
// not repeat in its two halves, so a device of a whole number of units meets
// no hole when it is shifted by half a unit. One whose height is not a whole
// number may start on a whole unit or on a half.
const halfRefusal = (f, c, ref, ru, units) => (!Number.isInteger(ru) && Number.isInteger(units)
  ? `${nameOf(c, ref)} is ${units}U; its ears meet the rail holes only at a whole unit, and ${uText(f, ru, units)} is a half unit.`
  : null);

export function fits(rack, cand, chassisOf, {ignoreId = null} = {}) {
  const f = rack.frame, c = chassisOf(cand.ref);
  if (!c) return {ok: false, reason: `No size is known for ${cand.ref}.`};
  if (isZeroUPart(c)) return no(`${nameOf(c, cand.ref)} stands beside the rack, not on its rails: place it with zerou.place.`);
  if (!isPosition(cand.ru)) return no('A position is a whole unit or a half unit, counted from 1.');
  if (isBoth(cand)) return no(bothText(cand));
  if (isRackFace(c)) return fitsRackFace(rack, cand, c, chassisOf, {ignoreId});
  // a held item: refused while its host is gone, and not checked on a host
  // the catalogue says nothing of
  if (holderOf(cand) != null) {
    const host = rack.items.find(o => o.id === holderOf(cand));
    if (!host) return no(unheldText(cand));
    if (!isRackMount(c)) return {ok: true, unchecked: uncheckedText(cand, host, chassisOf)};
  }
  const units = itemUnits(cand, () => c), lo = cand.ru, hi = cand.ru + units;
  const s = setbackOf(rack, cand, chassisOf), reach = s + c.d;
  // rolled a quarter turn, its height lies across the opening and has to pass between the rails
  if (isQuarter(cand) && Number(c.h) > OPENING)
    return no(`${nameOf(c, cand.ref)} is ${mm(c.h)} mm high; rolled a quarter turn that is across the opening, which is ${mm(OPENING)} mm.`);
  if (lo < 1) return below(f);
  const half = halfRefusal(f, c, cand.ref, lo, units);
  if (half) return no(half);
  if (hi > f.heightRU + 1)
    return {ok: false, reason: `${units}U needed; ${f.heightRU - lo + 1}U free from U${named(f, lo)} to the top.`};
  if (reach > f.usableDepth) return {ok: false, reason: `${deep(c, s)}; this rack allows ${mm(f.usableDepth)} mm.`};
  for (const o of rack.items) {
    if (o.id === ignoreId || isHeld(o, chassisOf)) continue;
    const oc = chassisOf(o.ref);
    if (!oc || !spansMeet([lo, hi], spanOf(o, chassisOf))) continue;
    if (isRackFace(oc)) {
      if (o.face !== cand.face && reach > between(f))
        return {ok: false, reason: `${deep(c, s)}; it would reach past the ${o.face} rail into ${o.label}.`};
      continue;
    }
    if (o.face === cand.face) return {ok: false, reason: `Taken by ${o.label} on the ${o.face}.`};
    if (f.kind === 'two-post')
      return {ok: false, reason: `Taken by ${o.label}; two-post rails are shared by front and rear.`};
    const other = reachOf(rack, o, chassisOf);
    if (reach + other > f.railDepth)
      return {ok: false, reason: `${deep(c, s)}; ${Math.max(0, mm(f.railDepth - other))} mm free behind ${o.label}.`};
  }
  return {ok: true};
}

// DEPTH ALONE: does the body, with its setback, stay inside the usable depth
// and clear of what is on the other face of the units it fills? What a larger
// setback is checked by, so that it is never refused for a reason that has
// nothing to do with depth (an overlap in height the rack already held).
export function fitsDepth(rack, cand, chassisOf, {ignoreId = null} = {}) {
  const f = rack.frame, c = chassisOf(cand.ref);
  if (!c || isRackFace(c) || isZeroUPart(c) || isHeld(cand, chassisOf)) return {ok: true};
  const s = setbackOf(rack, cand, chassisOf), reach = s + c.d, mine = spanOf(cand, chassisOf);
  if (reach > f.usableDepth) return no(`${deep(c, s)}; this rack allows ${mm(f.usableDepth)} mm.`);
  for (const o of rack.items) {
    if (o.id === ignoreId || o.face === cand.face || isHeld(o, chassisOf)) continue;
    const oc = chassisOf(o.ref);
    if (!oc || !spansMeet(mine, spanOf(o, chassisOf))) continue;
    if (isRackFace(oc)) {
      if (reach > between(f)) return no(`${deep(c, s)}; it would reach past the ${o.face} rail into ${o.label}.`);
      continue;
    }
    const other = reachOf(rack, o, chassisOf);
    if (f.kind !== 'two-post' && reach + other > f.railDepth)
      return no(`${deep(c, s)}; ${Math.max(0, mm(f.railDepth - other))} mm free behind ${o.label}.`);
  }
  return {ok: true};
}

// Does this item show its other panel on the other face's elevation, or only
// a ghost of the space it takes?
export function reaches(item, rack, chassisOf) {
  if (rack.frame.kind === 'two-post') return true;
  return reachOf(rack, item, chassisOf) >= rack.frame.railDepth - REACH_MM;
}

// The depth this item could have where it stands: what the other face leaves
// on the U range it shares, or the rack's usable depth, less its own setback.
export function availableDepth(rack, item, chassisOf) {
  const f = rack.frame;
  const own = setbackOf(rack, item, chassisOf);
  if (f.kind === 'two-post') return f.usableDepth - own;
  const mine = spanOf(item, chassisOf);
  const other = rack.items.filter(o => o.id !== item.id && o.face !== item.face
                                       && !isRackFace(chassisOf(o.ref)) && !isHeld(o, chassisOf)
                                       && spansMeet(mine, spanOf(o, chassisOf)));
  if (!other.length) return f.usableDepth - own;
  return Math.min(f.usableDepth, f.railDepth - Math.max(...other.map(o => reachOf(rack, o, chassisOf)))) - own;
}

// Every item with the U height its chassis entry gives it (unitsOf: in halves,
// and 1 when unknown) - what the elevation, the 3D view and any export all need
// beside the item's own fields, so each draws the same rack.
// heightOf(chassisOf) is that height as a lookup by item: what names a device
// with its U (cable-rules.js endName) asks it.
export const heightOf = chassisOf => item => itemUnits(item, chassisOf);

// WHAT THE FIT OF BEFORE ALLOWED AND THIS ONE DOES NOT (section 8): an item
// whose height is not a whole number of units, with another in the unit its
// top half fills. Both are kept where they are, as fit keeps an item it would
// no longer accept; each pair is a sentence, which the editor gives as a
// finding when a document is loaded (editor.js loadDoc).
export function overlapNotices(rack, chassisOf) {
  const out = [];
  for (const a of rack.items) {
    const ac = chassisOf(a.ref);
    if (!ac || isRackFace(ac) || isHeld(a, chassisOf)) continue;
    const [lo, hi] = spanOf(a, chassisOf);
    if (Number.isInteger(hi)) continue;
    for (const b of rack.items) {
      const bc = chassisOf(b.ref);
      if (b === a || !bc || isRackFace(bc) || isHeld(b, chassisOf) || b.ru !== Math.floor(hi) || b.ru <= lo) continue;
      if (fits({...rack, items: [b]}, a, chassisOf).ok) continue;
      out.push(`${a.label} at ${uText(rack.frame, lo, hi - lo)} is ${hi - lo}U and reaches into U${uLabel(rack.frame, b.ru)}, where ${b.label} is.`);
    }
  }
  return out;
}
// A `side` is kept only where it is a rail (railOf), so a drawing or an export
// that reads it never puts a part across the opening on one rail.
export const itemsWithU = (rack, chassisOf) =>
  rack.items.map(({side, ...i}) => {
    const mount = chassisOf(i.ref)?.mount;      // stated only when it is not a rack's
    const rail = railOf({...i, side}, chassisOf);
    return {...i, u: heightOf(chassisOf)(i), ...(isRackMount({mount}) ? {} : {mount}), ...(rail ? {side: rail} : {})};
  });

export const attachPoints = kind => (kind === 'four-post'
  ? ['left-front', 'right-front', 'left-rear', 'right-rear'] : ['left', 'right']);

// SHRINK THE FRAME: a lower height that leaves devices
// hanging past it is no longer refused - it packs them down instead.
//
// Items whose spans meet (on either face - a front/rear pair sharing a U is
// one cluster) move together, keeping their offsets, faces and turned state.
// Clusters close their gaps by packing upward from U1 in their original
// bottom-to-top order. EACH CLUSTER MOVES BY ONE SHIFT, so every item in it
// keeps its parity: a whole number of units for a cluster that holds any item
// of a whole-unit height or any rack-face part (neither may land on a half),
// and a multiple of 0.5 otherwise. So the cursor is rounded up to the next
// position of the parity such a cluster already has, and the packed rack can
// be taller than its heights added up. WHAT IS DROPPED IS JUDGED BY THE PACKED
// TOP: the survivors are packed, and while the top edge of the last is above
// the new height the lowest cluster is dropped and the rest packed again.
export function shrinkRack(rack, newHeight, chassisOf) {
  const withFrameHeight = items => ({...rack, frame: {...rack.frame, heightRU: newHeight}, items});
  const topOf = item => spanOf(item, chassisOf)[1];
  // a top edge of heightRU + 1 is the top of the rack
  const fitsUnder = top => top <= newHeight + 1;

  // A HELD ITEM WHOSE HOST IS GONE (dropped by this shrink, or not in the
  // rack) is kept, held by nothing, and fit refuses it until it is placed
  // again; one left above the new top is brought down to the top unit, so no
  // item is outside the rack. `orphaned` are those this shrink left so.
  const settleHeld = (list, removedIds, moved) => {
    const ids = new Set(list.map(i => i.id)), orphaned = [];
    const out = list.map(it => {
      if (!isHeld(it, chassisOf) || ids.has(holderOf(it))) return it;
      if (removedIds.has(holderOf(it))) orphaned.push(it);
      if (it.ru <= newHeight) return it;
      moved.push(it.id);
      return {...it, ru: newHeight};
    });
    return {items: out, orphaned};
  };
  if (rack.items.every(i => isHeld(i, chassisOf) || fitsUnder(topOf(i)))) {
    const moved = [], s = settleHeld(rack.items, new Set(), moved);
    return {rack: withFrameHeight(s.items), moved, removed: [], orphaned: s.orphaned};
  }

  // Group items into clusters by meeting spans (union-find), face
  // ignored - that is exactly what keeps a front/rear pair together.
  // A held item that is no rack device is not a cluster of its own: it takes
  // the shift of its host, and stays where it was when its host is dropped or
  // is not in the rack.
  const held = rack.items.filter(i => isHeld(i, chassisOf));
  const items = rack.items.filter(i => !held.includes(i));
  const n = items.length;
  const parent = items.map((_, i) => i);
  const find = x => (parent[x] === x ? x : (parent[x] = find(parent[x])));
  for (let i = 0; i < n; i++)
    for (let j = i + 1; j < n; j++)
      if (spansMeet(spanOf(items[i], chassisOf), spanOf(items[j], chassisOf))) {
        const a = find(i), b = find(j);
        if (a !== b) parent[a] = b;
      }
  const groups = new Map();
  items.forEach((it, i) => {
    const r = find(i);
    if (!groups.has(r)) groups.set(r, []);
    groups.get(r).push(it);
  });
  const wholeOnly = it => isRackFace(chassisOf(it.ref)) || Number.isInteger(itemUnits(it, chassisOf));
  const clusters = [...groups.values()]
    .map(list => {
      const lo = Math.min(...list.map(i => i.ru));
      return {items: list, lo, height: Math.max(...list.map(topOf)) - lo, whole: list.some(wholeOnly)};
    })
    .sort((a, b) => a.lo - b.lo); // original bottom-to-top order

  // A shift per surviving item, not a repacked list: the returned rack keeps
  // rack.items in its ORIGINAL order (only positions change), so nothing
  // downstream that assumes item order is stable sees them shuffled by
  // cluster. `top` is the top edge of the last cluster packed.
  const pack = clusterList => {
    let cursor = 1;
    const shiftById = new Map();
    const moved = [];
    for (const c of clusterList) {
      // a cluster that may move only by whole units starts half a unit up
      // when the cursor is on the other parity
      const lo = c.whole && !Number.isInteger(cursor - c.lo) ? cursor + 0.5 : cursor;
      const shift = lo - c.lo;
      for (const it of c.items) {
        shiftById.set(it.id, shift);
        if (shift !== 0) moved.push(it.id);
      }
      cursor = lo + c.height;
    }
    return {shiftById, moved, top: cursor};
  };

  let survivors = clusters;
  const removed = [];
  let packed = pack(survivors);
  while (survivors.length && !fitsUnder(packed.top)) {
    const [gone, ...rest] = survivors;
    removed.push(...gone.items);
    survivors = rest;
    packed = pack(survivors);
  }
  const {shiftById, moved} = packed;
  const removedIds = new Set(removed.map(i => i.id));
  for (const h of held) {
    const shift = shiftById.get(holderOf(h));
    if (shift) { shiftById.set(h.id, shift); moved.push(h.id); }
  }
  const packedItems = rack.items
    .filter(it => !removedIds.has(it.id))
    .map(it => (shiftById.get(it.id) ? {...it, ru: it.ru + shiftById.get(it.id)} : it));
  const s = settleHeld(packedItems, removedIds, moved);
  return {rack: withFrameHeight(s.items), moved, removed, orphaned: s.orphaned};
}

// ZERO-U (#926): a zero-U part on an attachment point of this frame, its
// bottom level with a U (`ru`) or at the `offsetMm` a file stores, within the
// rack's height by the units it states (zeroUUnits), and never overlapping
// another zero-U part on the same attachment point. Parts on two attachment
// points never meet, whatever their height.
// OVERLAP IS JUDGED IN MILLIMETRES (version 4): from `offsetMm` to `offsetMm`
// plus the stated units times one unit. A part the kit placed at a whole unit
// overlaps exactly as it did when units were compared; a part hung on brackets
// stands where they put it, which is no whole unit, and is judged there. A
// PART DOES NOT OVERLAP THE PARTS THAT HOLD IT (`heldBy`), and one whose
// holder is not in the rack is refused until it is hung again or freed.
const MM_EPS = 1e-6;
export const zeroUExtent = (z, chassisOf) => {
  const lo = zeroUBottomMm(z);
  return [lo, lo + zeroUUnits(chassisOf(z.ref)) * RU];
};
export const notBracket = id => `${id} is not a bracket in this rack.`;
export function fitsZeroU(rack, cand, chassisOf, {ignoreId = null} = {}) {
  const f = rack.frame, c = chassisOf(cand.ref);
  if (!c) return no(`No size is known for ${cand.ref}.`);
  if (!isZeroUPart(c)) return no(`${nameOf(c, cand.ref)} does not stand beside the rack: it goes on the rails.`);
  const points = attachPoints(f.kind);
  if (!points.includes(cand.at)) return no(`${cand.at} is not an attachment point of a ${f.kind} frame: use ${points.join(', ')}.`);
  const u = zeroUUnits(c);
  let off;
  if (cand.ru != null) {
    // placed by its unit: a whole number of units, as the commands write it
    const lo = cand.ru;
    if (!Number.isInteger(lo) || lo < 1) return below(f);
    if (lo > f.heightRU) return no(`U${named(f, lo)} is past the top of this ${f.heightRU}U rack.`);
    if (lo + u - 1 > f.heightRU) return tooTall(f, u, lo);
    off = (lo - 1) * RU;
  } else {
    // where the file has it, in mm
    off = Number(cand.offsetMm) || 0;
    if (off < -MM_EPS) return below(f);
    const lo = Math.floor(off / RU + MM_EPS) + 1;
    if (lo > f.heightRU) return no(`U${named(f, lo)} is past the top of this ${f.heightRU}U rack.`);
    if (off + u * RU > f.heightRU * RU + MM_EPS) return tooTall(f, u, lo);
  }
  const mine = cand.id ?? ignoreId, holders = holdersOf(cand);
  for (const id of holders) if (!zeroUOf(rack).some(o => o.id === id)) return no(notBracket(id));
  for (const o of zeroUOf(rack)) {
    if (o.id === ignoreId || o.at !== cand.at || !isZeroUPart(chassisOf(o.ref))) continue;
    if (holders.includes(o.id) || (mine != null && holdersOf(o).includes(mine))) continue;
    const [lo, hi] = zeroUExtent(o, chassisOf);
    if (off < hi - MM_EPS && lo < off + u * RU - MM_EPS) return no(`Overlaps ${o.label || o.ref} at ${o.at}.`);
  }
  return {ok: true};
}

// THE ZERO-U PARTS AFTER A FRAME CHANGE (#926). A new kind moves each part to
// the attachment point on its own side of the new frame (left-front and
// left-rear to left; left to left-front), a lower height moves a part that now
// runs past the top down until it fits, and a part that still does not fit -
// taller than the rack, or overlapping one kept before it - is removed. Parts
// are judged in the order the rack lists them, each where its `offsetMm` has
// it. Returns the rack with `moved` and `removed`, each a list of entries as
// they were.
export function settleZeroU(rack, chassisOf) {
  const points = attachPoints(rack.frame.kind);
  const placeable = new Set(zeroUOf(rack).filter(z => isZeroUPart(chassisOf(z.ref))));
  const moved = [], removed = [], gone = new Set();
  let kept = {...rack, zeroU: (rack.zeroU || []).filter(z => !placeable.has(z))};
  const out = (rack.zeroU || []).map(z => {
    if (!placeable.has(z)) return z;
    const side = String(z.at).startsWith('right') ? 'right' : 'left';
    const at = points.includes(z.at) ? z.at : points.find(p => p.startsWith(side));
    const u = zeroUUnits(chassisOf(z.ref));
    const was = Number(z.offsetMm) || 0;
    // down to the highest place it fits under the top, and never below the rails
    const top = zeroUOffset(Math.max(1, rack.frame.heightRU - u + 1));
    const off = Math.max(0, Math.min(was, top));
    const next = at === z.at && off === was ? z : {...z, at, offsetMm: off};
    // a part whose holder is gone is kept where it is, as fit will say; it is
    // judged here for room alone
    const here = holdersOf(next).filter(id => zeroUOf(rack).some(o => o.id === id));
    const trial = here.length === holdersOf(next).length ? next : {...next, heldBy: {parts: here}};
    if (!fitsZeroU(kept, {...trial, ru: undefined}, chassisOf, {ignoreId: z.id}).ok) {
      removed.push(z); gone.add(z);
      return z;
    }
    if (next !== z) moved.push(z);
    kept = {...kept, zeroU: [...kept.zeroU, next]};
    return next;
  }).filter(z => !gone.has(z));
  return {rack: moved.length || removed.length ? {...rack, zeroU: out} : rack, moved, removed};
}

// RACK-FACE MANAGERS.
// Pure, like fit.js: the rack, the change, and a chassisOf(ref) lookup. A
// manager is an item; `on` and `unit` say which device it bolts over, and its
// `ru` always says where it is. Everything that moves a manager or its host
// comes through here, so the two can never drift apart.

import {fits, isRackFace, railOf} from './fit.js';
import {detached, uLabel} from './model.js';

const unitsOf = (chassisOf, ref) => Math.max(1, chassisOf(ref)?.ru ?? 1);

// The rack device on `face` whose U span holds `ru` - what a manager placed
// there bolts over - or null. Never another manager.
export function hostAt(rack, face, ru, chassisOf, {ignoreId = null} = {}) {
  return rack.items.find(o => o.id !== ignoreId && o.face === face && !isRackFace(chassisOf(o.ref))
    && ru >= o.ru && ru <= o.ru + unitsOf(chassisOf, o.ref) - 1) ?? null;
}

export const managersOf = (rack, hostId) => rack.items.filter(i => i.on === hostId);

// Where a manager put at (face, ru) goes: onto the device there, or alone. A
// part on one rail (`side`, #926) goes alone, with its side: it is not across
// the device behind it.
export function placement(rack, {face, ru, side, ref}, chassisOf, {ignoreId = null} = {}) {
  if (railOf({ref, side}, chassisOf)) return {face, ru, side};
  const host = hostAt(rack, face, ru, chassisOf, {ignoreId});
  return host ? {face, ru, on: host.id, unit: ru - host.ru + 1} : {face, ru};
}

// THE RACK AS OPENED, MADE CONSISTENT. parseDoc cannot see the
// catalogue, so this is where a host is checked: every repair is a sentence.
export function settleManagers(rack, chassisOf) {
  const notices = [];
  const byId = new Map(rack.items.map(i => [i.id, i]));
  const items = rack.items.map(i => {
    if (!('on' in i)) return i;
    const chassis = chassisOf(i.ref);
    if (!chassis) return i;                  // not in the catalogue (yet): nothing to judge it by
    if (!isRackFace(chassis)) {
      notices.push(`${i.label} is not a cable manager, so it is not on another device.`);
      return detached(i);
    }
    const host = byId.get(i.on);
    if (host && !isRackFace(chassisOf(host.ref)) && host.face !== i.face) {
      notices.push(`${i.label}: ${host.label} is on the ${host.face}, so it stays at U${uLabel(rack.frame, i.ru)} on its own.`);
      return detached(i);
    }
    if (!host || isRackFace(chassisOf(host.ref))) {
      notices.push(`${i.label}: the device it was on is not in this rack, so it stays at U${uLabel(rack.frame, i.ru)} on its own.`);
      return detached(i);
    }
    const unit = Math.min(Math.max(1, i.unit), unitsOf(chassisOf, host.ref));
    const ru = host.ru + unit - 1;
    if (ru === i.ru && unit === i.unit) return i;
    notices.push(`${i.label} was out of step with ${host.label}, so it moved to U${uLabel(rack.frame, ru)} with it.`);
    return {...i, ru, unit};
  });
  return {rack: {...rack, items}, notices};
}

// ONE MOVE (a patch with `ru` and/or `face`), checked whole. A manager is
// re-hosted by where it lands. A rack device takes its managers with it: they
// are all moved first and then each is checked against the rack as it would
// be, so two managers of one host never refuse each other's old place.
export function moveItem(rack, id, patch, chassisOf) {
  const it = rack.items.find(i => i.id === id);
  const next = {...it, ...patch};
  if (isRackFace(chassisOf(it.ref))) {
    const placed = {...detached(next), ...placement(rack, next, chassisOf, {ignoreId: id})};
    const f = fits(rack, placed, chassisOf, {ignoreId: id});
    return f.ok ? {ok: true, rack: {...rack, items: rack.items.map(i => (i.id === id ? placed : i))}} : f;
  }
  const moved = new Map(managersOf(rack, id).map(m => [m.id, {...m, face: next.face, ru: next.ru + m.unit - 1}]));
  const after = {...rack, items: rack.items.map(i => (i.id === id ? next : moved.get(i.id) ?? i))};
  // The host is checked in the rack as it will be, so its own managers are
  // already beside it and not at their old places.
  const f = fits(after, next, chassisOf, {ignoreId: id});
  if (!f.ok) return f;
  for (const m of moved.values()) {
    const g = fits(after, m, chassisOf, {ignoreId: m.id});
    if (!g.ok) return {ok: false, reason: `${m.label} moves with it: ${g.reason}`};
  }
  return {ok: true, rack: after};
}

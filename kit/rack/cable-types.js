// THE CABLE TYPES (cable-types.json, written by cable_types_index.py from
// spec/schemas/cable-types.yaml): each type's media, typical outside diameter
// and minimum bend radius, sourced (#919). A type's id is the Rack Builder's
// cable `media` for the bare types (`om4`, `cat6a`, `dac`), so a rack cable's
// media names its type as it stands.
//
// A radius is `{mm}` or `{xOD}` - a fixed figure or a multiple of the cable's
// outside diameter - and `radiusMm` turns either into millimetres with the
// type's `od_mm`. The installed radius is the one a route or a bundle is
// checked against; the loaded one (while a cable is pulled) is data only.

import {jdist} from '../dist.js';

const urlOf = (dist, path) => (typeof dist === 'function' ? dist(path) : `${String(dist).replace(/\/$/, '')}/${path}`);
const positive = v => typeof v === 'number' && Number.isFinite(v) && v > 0;
// Two decimals: 10 x 3.0 is 30, not 30.000000000000004.
const round2 = v => Math.round(v * 100) / 100;

// Own keys only: a hand-edited media named like something every object has
// (`constructor`, `__proto__`) is no type, not Object's.
export const typeOf = (types, id) =>
  (types && typeof id === 'string' && Object.hasOwn(types, id) ? types[id] : null);

// A type's radius in millimetres: `which` is 'installed' (the default) or
// 'loaded'. Null when the type states no such radius, or states a multiple
// of a diameter it does not give.
export function radiusMm(type, which = 'installed') {
  const r = type?.min_bend_radius?.[which];
  if (!r) return null;
  if (positive(r.mm)) return round2(r.mm);
  if (positive(r.xOD) && positive(type.od_mm)) return round2(r.xOD * type.od_mm);
  return null;
}

// The installed minimum bend radius of the type `id` names, in millimetres,
// or null for a type that is not in the table.
export const installedRadiusMm = (types, id) => radiusMm(typeOf(types, id));

// What a cable's type is: its own `type` when it states one (#897's named
// types), else its `media`.
const typeIdOf = cable => (typeof cable?.type === 'string' && cable.type ? cable.type : cable?.media);

// cable => installed minimum bend radius in mm, or null when the cable has no
// type or its type has no radius: the bundle checks' `ctx.bendOf`.
export const bendLookup = types => cable => installedRadiusMm(types, typeIdOf(cable));

// cable => its type's typical outside diameter in mm, or null.
export const diameterLookup = types => cable => {
  const t = typeOf(types, typeIdOf(cable));
  return positive(t?.od_mm) ? t.od_mm : null;
};

export async function loadCableTypes(dist) {
  const j = await jdist(urlOf(dist, 'cable-types.json'));
  if (j?.format !== 1) throw new Error(`cable-types.json: format ${j?.format}; this kit reads format 1`);
  const types = j.types || {};
  return {types, version: j.version ?? null, sources: j.sources || {},
          typeOf: id => typeOf(types, id), bendOf: bendLookup(types), diameterOf: diameterLookup(types)};
}

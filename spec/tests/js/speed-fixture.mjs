// Generated racks at the scale of a real one, for the speed of the rack kit
// (rack-speed.mjs, speed-bench.mjs, speed-goldens.mjs). Not a test file.
//
// THE RACK is a four-post frame of 45 units with `devices` two-unit switches
// stacked from the top down (thirteen by default, one unit left free under
// the seventh), each with 76 ports in two
// rows of 38 and, with `lacers`, an FHD-CMP5DR lacer hosted on it (on its
// upper unit, or its lower one for every third switch); with `managers`, a
// CMV-SFD45U5W duct stands at each front upright; and `cables` cords join
// free ports of two switches (one in ten, two ports of one switch), their
// media mostly AOC and DAC as a router cluster's are. One cord in twelve has
// a length entered by hand, one in fifteen says where its spare is stored,
// and one in twenty is routed by hand down a gutter. `bundles` groups of
// three or more cords between one pair of switches are bundled, their trunk
// down the left front gutter. Every number comes from `rng(seed)`
// (mulberry32), so a rack is the same on every run and in every tree.
//
// THE CONTEXT is made as a page makes it: `ctxOf(rack)` builds a new one,
// whole and frozen, on every call, so two calls for one rack give two
// contexts that answer alike. `portBoxes: false` leaves out
// `ctx.portBoxesOf`, as a page that reads only the cabled ports does.
//
// `M` is a tree's own model.js and `F` its cable-solids-fixture, so the same
// rack can be built for another revision of the kit (speed-goldens.mjs).

function rng(seed) { let a = seed >>> 0; return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

const RU = 44.45;
const SW = {ru: 2, w: 436, h: 87.7, d: 762, kind: 'switch', model: 'SW2', manufacturer: 'Acme'};
const PORTS = 76, COLS = 38;
// a port's centre: x from the centre line, y down from the top of the face
const portOf = n => ({x: Math.round((-207.2 + 11.2 * Math.floor(n / 2)) * 10) / 10, y: n % 2 ? 58.4 : 44.9});
const MEDIA = ['aoc', 'aoc', 'aoc', 'aoc', 'aoc', 'aoc', 'aoc', 'aoc', 'aoc', 'aoc', 'aoc',
  'dac', 'dac', 'dac', 'cat6', 'cat6', 'om4', 'om4', 'os2', 'cat6a'];

export function speedRack(M, F, {devices = 13, cables = 300, seed = 1, lacers = true, managers = true, bundles = 0, portBoxes = true} = {}) {
  const rnd = rng(seed);
  const pick = a => a[Math.floor(rnd() * a.length)];
  let rack = M.newRack({name: `Speed ${devices}x${cables}`});
  rack = {...rack, frame: {...rack.frame, heightRU: 45, railDepth: 740}};
  const sizes = {sw2: SW, 'fhd-cmp5dr': F.CAT['fhd-cmp5dr'], 'cmv-sfd45u5w': F.CAT['cmv-sfd45u5w']};
  const add = (ref, ru, extra = {}) => { rack = M.withItem(rack, {ref, cfg: 'base', ru, label: ref, ...extra}).rack; return rack.items.at(-1).id; };
  const switches = [], lacerOf = {};
  for (let k = 0; k < devices; k++) {
    const ru = 43 - 2 * k - (k > 6 ? 1 : 0);          // a unit left free under the seventh, for moveDevice
    if (ru < 1) throw new Error(`speedRack: ${devices} switches do not fit 45 units`);
    const id = add('sw2', ru, {label: `SW-${k + 1}`});
    switches.push(id);
    if (lacers) lacerOf[id] = add('fhd-cmp5dr', ru + (k % 3 === 2 ? 0 : 1), {on: id, unit: k % 3 === 2 ? 1 : 2, label: `LACER-${k + 1}`});
  }
  if (managers) rack = {...rack, zeroU: [
    {id: 'z1', ref: 'cmv-sfd45u5w', cfg: 'base', label: 'VCM-L', at: 'left-front', offsetMm: 0},
    {id: 'z2', ref: 'cmv-sfd45u5w', cfg: 'base', label: 'VCM-R', at: 'right-front', offsetMm: 0}]};
  const free = Object.fromEntries(switches.map(id => [id, Array.from({length: PORTS}, (_, n) => n)]));
  const take = id => { const l = free[id]; return l.length ? l.splice(Math.floor(rnd() * l.length), 1)[0] : null; };
  const end = (item, n) => ({item, path: `port-${n}`, view: 'front'});
  const list = [];
  const ruOf = id => rack.items.find(i => i.id === id).ru;
  for (let i = 0; list.length < cables && i < cables * 4; i++) {
    const a = pick(switches), b = rnd() < 0.1 ? a : pick(switches.filter(s => s !== a));
    if (free[a].length < 2 || free[b].length < 2) continue;
    const pa = take(a), pb = take(b), n = list.length + 1;
    const c = {id: `c${n}`, a: end(a, pa), b: end(b, pb), media: pick(MEDIA), purpose: 'fabric', label: '', route: []};
    if (n % 12 === 5) c.length = {value: pick([2, 3, 5]), unit: 'm', source: 'entered'};
    if (n % 15 === 7 && lacerOf[a]) c.slack = [{item: lacerOf[a], via: 'tray', form: 'coil'}];
    if (n % 15 === 11) c.slack = [{end: 'a', value: 0.2, unit: 'm'}];
    if (n % 20 === 13 && a !== b) {
      const lane = pick(['left-front', 'right-front']);
      c.route = [{lane, ru: ruOf(a)}, {lane, ru: ruOf(b)}];
      c.routeEdited = true;
    }
    list.push(c);
  }
  rack = {...rack, cables: list};
  if (bundles > 0) {
    const pairs = new Map();
    for (const c of list) {
      if (c.a.item === c.b.item || c.routeEdited) continue;
      const key = [c.a.item, c.b.item].sort().join('|');
      (pairs.get(key) || pairs.set(key, []).get(key)).push(c);
    }
    const groups = [...pairs.values()].filter(g => g.length >= 3).slice(0, bundles);
    rack = {...rack, bundles: groups.map((g, k) => {
      const us = [ruOf(g[0].a.item), ruOf(g[0].b.item)].sort((p, q) => p - q);
      return {id: `b${k + 1}`, number: k + 1, label: '', members: g.map(c => ({cable: c.id})),
        route: [{lane: 'left-front', ru: us[0]}, {lane: 'left-front', ru: us[1]}]};
    })};
  }
  const chassisOf = ref => (Object.hasOwn(sizes, ref) ? sizes[ref] : null);
  // The context for a rack, as a page builds it: new on every call.
  const ctxOf = r => {
    const items = new Map(r.items.map(i => [i.id, i]));
    const numOf = e => { const m = /^port-(\d+)$/.exec(String(e?.path)); return m && Number(m[1]) < PORTS ? Number(m[1]) : null; };
    const yOf = (it, y) => (it.ru + 1) * RU - (0.6 + y);
    const byId = new Map((r.cables || []).map(c => [c.id, c]));
    return Object.freeze({
      chassisOf,
      guidesOf: id => (items.get(id)?.ref === 'fhd-cmp5dr' ? F.RINGS : []),
      portX: e => { const n = numOf(e); return n != null && items.get(e.item)?.ref === 'sw2' ? portOf(n).x : null; },
      portY: e => { const n = numOf(e), it = items.get(e.item); return n != null && it?.ref === 'sw2' ? yOf(it, portOf(n).y) : null; },
      ...(portBoxes ? {portBoxesOf: id => { const it = items.get(id);
        return it?.ref === 'sw2' ? Array.from({length: PORTS}, (_, n) => ({path: `port-${n}`, view: 'front', x: portOf(n).x, y: yOf(it, portOf(n).y), w: 9.6, h: 8.6})) : []; }} : {}),
      // a DAC's or an AOC's head stands 65 mm out of its cage, as a page reads it off the seated part
      plugReachOf: (e, c) => (['dac', 'aoc'].includes((c ?? byId.get(e?.cable))?.media) ? 65 : null),
      zeroUAperture: z => (z?.ref === 'cmv-sfd45u5w' ? {w: 93, h: 165} : null),
    });
  };
  return {rack, ctxOf, chassisOf, switches, lacerOf, COLS};
}

// ONE EDIT, as a page's commands make it: a new rack that shares every cable
// and item it did not touch.
// - `moveCable`: cable `id` repointed at its end b to a free port of the
//   same switch;
// - `moveDevice`: switch `id` (and its lacer) one unit down, where that is free.
export function moveCable(rack, id) {
  const c = rack.cables.find(x => x.id === id);
  const used = new Set(rack.cables.flatMap(x => [x.a, x.b]).filter(e => e.item === c.b.item).map(e => e.path));
  const n = Array.from({length: PORTS}, (_, k) => `port-${k}`).find(p => !used.has(p));
  return {...rack, cables: rack.cables.map(x => (x.id === id ? {...x, b: {...x.b, path: n}} : x))};
}
export function moveDevice(rack, id, by = -1) {
  return {...rack, items: rack.items.map(i => (i.id === id || i.on === id ? {...i, ru: i.ru + by} : i))};
}

// SPANS PAST A TRAY'S EDGE, hung (resting.js hang): from over the middle of
// the floor of the lacer's tray on the reference rack of #949 (cable-solids-fixture)
// out past its front edge, its two ends and a corner, 30, 120 and 400 mm
// beyond, from 4, 20 and 60 mm above the floor, the 120 mm ones 15 mm
// downhill: 45 spans, each [its points to a millionth of a millimetre, what
// it lands on]. `F`, `S` and `Rest` are a tree's cable-solids-fixture,
// solids.js and resting.js.
export function edgeSpans(F, S, Rest) {
  const rack = {...F.ownerRack(), cables: F.OWNER_CABLES}, ctx = F.ctxOf();
  const surfaces = Rest.surfacesOf(rack, ctx), trays = S.traysOf(rack, ctx);
  const floor = trays[0].floors.reduce((m, f) => ((f.x1 - f.x0) * (f.z1 - f.z0) > (m.x1 - m.x0) * (m.z1 - m.z0) ? f : m));
  const top = trays[0].top, cx = (floor.x0 + floor.x1) / 2, cz = (floor.z0 + floor.z1) / 2;
  const spans = [];
  for (const up of [4, 20, 60])
    for (const [dx, dz] of [[0, 1], [1, 0], [-1, 0], [1, 1], [0.3, 1]])
      for (const reach of [30, 120, 400]) {
        const p = {x: cx, y: top + up, z: cz};
        const edge = dz ? floor.z1 - cz : (dx > 0 ? floor.x1 - cx : cx - floor.x0);
        spans.push([p, {x: cx + dx * (edge + reach), y: top + up + (reach === 120 ? -15 : 0), z: cz + dz * (edge + reach)}]);
      }
  const r6 = v => Math.round(v * 1e6) / 1e6;
  return spans.map(([p, q]) => {
    const h = Rest.hang(p, q, {r: 1.5, drape: 1, bend: 25, surfaces});
    return [h.points.map(pt => [r6(pt.x), r6(pt.y), r6(pt.z)]), h.lands.map(g => g.via ?? g.part)];
  });
}

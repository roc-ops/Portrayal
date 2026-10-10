// Generated racks for the bend-room figures of docs/cable-lay-design.md
// section 3.4 (#973), so that they can be counted again. Not a test file:
// rack-bend-room.mjs imports `sampleRack`, and run on its own it prints the
// figures for this tree, and beside another tree of the kit when one is given:
//
//   node spec/tests/js/bend-room-sample.mjs [--base <dir>] [--racks 60]
//
// `<dir>` is a copy of another revision that holds its `kit/rack` and its
// `spec/tests/js` fixtures, for example
//   git archive <rev> kit/rack spec/tests/js | tar -x -C <dir>
// The other tree's paths are counted with THIS tree's cornersOf, since a
// revision before #973 has neither `share: 'need'` nor cornersOf in
// route-path.js; that is how the `before` rows of section 3.4 were measured,
// the owner's rack included (the first lines printed with --base).
//
// THE SAMPLE is one sample, of one generator: rack `seed` (1 to 60 by
// default) is a four-post frame, or a two-post one where the seed divides by
// three, filled from U2 up with six to eleven blocks, each a switch (twelve
// ports), a switch under a panel that hosts an FHD-CMP5DR lacer, a panel
// with its lacer, or a gap of one to three units; where the seed is one more
// than a multiple of four, a zero-U PDU stands at an upright, 200, 400, 610,
// 900 or 1700 mm tall and 0, 5, 12 or 20 units up from the bottom, by turns
// (so that some end below the devices, and a span can pass over one's top);
// and 20 to 49
// cables join ports of two different devices, their media drawn from om4
// (three in eight), os2, cat6, cat6a, dac and aoc. Every number comes from
// `rng(seed)` below (mulberry32), so the racks are the same on every run. The
// parts are those of cable-solids-fixture.mjs.
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';

function rng(seed) { let a = seed >>> 0; return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

// Rack `seed`, built with a tree's own model.js (M) and cable-solids-fixture
// (F): {rack, ctx}.
export function sampleRack(M, F, seed) {
  const rnd = rng(seed);
  const pick = a => a[Math.floor(rnd() * a.length)];
  const kind = seed % 3 === 0 ? 'two-post' : 'four-post';
  let rack = M.newRack();
  rack = {...rack, frame: {...rack.frame, kind, ...(kind === 'four-post' ? {railDepth: 740} : {})}};
  const guides = {}, ports = {}, units = [];
  let ru = 2;
  const add = (ref, u, extra = {}) => { const res = M.withItem(rack, {ref, cfg: 'base', ru: u, label: ref, ...extra}); rack = res.rack; return rack.items.at(-1).id; };
  const row = (first, step, name) => Object.fromEntries(Array.from({length: 12}, (_, i) => [`${name}${i}`, Math.round((first + i * step + rnd() * 6) * 10) / 10]));
  const blocks = 6 + Math.floor(rnd() * 6);
  for (let b = 0; b < blocks && ru < 38; b++) {
    const t = rnd();
    if (t < 0.45) {
      const id = add('sw', ru); units.push({id, kind: 'sw'});
      ports[id] = row(-200, 36, 'p');
      if (rnd() < 0.5) {
        ru += 1;
        const pid = add('panel', ru, {label: 'mgr-host'}), lid = add('fhd-cmp5dr', ru, {on: pid, unit: 1, label: 'lacer'});
        guides[lid] = F.RINGS;
        ports[pid] = row(-190, 34, 'b'); units.push({id: pid, kind: 'panel'});
      }
      ru += 1 + (rnd() < 0.3 ? 1 : 0);
    } else if (t < 0.8) {
      const pid = add('panel', ru), lid = add('fhd-cmp5dr', ru, {on: pid, unit: 1, label: 'lacer'});
      guides[lid] = F.RINGS;
      ports[pid] = row(-190, 34, 'b'); units.push({id: pid, kind: 'panel'});
      ru += 1 + (rnd() < 0.3 ? 1 : 0);
    } else { ru += 1 + Math.floor(rnd() * 3); }
  }
  // the PDU's height and how far up it stands go by the seed, not by `rnd`,
  // so the rest of each rack is as it was before they varied
  const turn = (seed - 1) / 4, pduH = [200, 400, 610, 900, 1700][turn % 5];
  const pduUp = pduH === 1700 ? 0 : [0, 5, 12, 20][Math.floor(turn / 5) % 4] * 44.45;
  if (seed % 4 === 1) rack = {...rack, zeroU: [{id: 'z1', ref: 'pdu', cfg: 'base', at: kind === 'two-post' ? 'left' : pick(['left-front', 'right-front', 'left-rear']), offsetMm: pduUp}]};
  const media = ['om4', 'om4', 'om4', 'os2', 'cat6', 'cat6a', 'dac', 'aoc'];
  const cables = [];
  const n = 20 + Math.floor(rnd() * 30);
  for (let i = 0; i < n && units.length > 1; i++) {
    const a = pick(units), b = pick(units);
    if (b === a) continue;
    cables.push(F.cable(`c${i + 1}`, F.end(a.id, pick(Object.keys(ports[a.id]))), F.end(b.id, pick(Object.keys(ports[b.id]))), pick(media)));
  }
  rack = {...rack, cables};
  const pdu = {...F.chassisOf('pdu'), h: pduH};
  const ctx = {chassisOf: ref => (ref === 'pdu' ? pdu : F.chassisOf(ref)), guidesOf: id => guides[id] ?? [], portX: e => ports[e.item]?.[e.path] ?? null};
  return {rack, ctx};
}

// How many points of a path, every half millimetre along it, stand in the
// space a zero-U part's outward face looks into (docs/cable-lay-design.md
// section 1.3, rule 4): in front of the face, within the part's width and
// height grown by the cable's radius. `solids` is solidsOf(rack, ctx).
export function inFrontOfZeroU(points, solids, r) {
  let n = 0;
  const parts = solids.filter(x => x.zeroU === true);
  for (let k = 1; parts.length && k < points.length; k++) {
    const u = points[k - 1], v = points[k], m = Math.max(1, Math.ceil(Math.hypot(v.x - u.x, v.y - u.y, v.z - u.z) / 0.5));
    for (let j = 0; j <= m; j++) {
      const q = {x: u.x + (v.x - u.x) * j / m, y: u.y + (v.y - u.y) * j / m, z: u.z + (v.z - u.z) * j / m};
      if (parts.some(({box: b, away}) => (away === -1 ? q.z < b.z0 - 1e-9 : q.z > b.z1 + 1e-9)
        && q.x > b.x0 - r && q.x < b.x1 + r && q.y > b.y0 - r && q.y < b.y1 + r)) n++;
    }
  }
  return n;
}

// A cable written the other way round, on the route it resolves to: [as
// written, reversed].
export function bothWays(R, rack, cable, ctx) {
  const route = R.resolveRoute(rack, cable, ctx).waypoints;
  return [{...cable, route, routeEdited: true}, {...cable, a: cable.b, b: cable.a, route: [...route].reverse(), routeEdited: true}];
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) {
  const arg = name => { const i = process.argv.indexOf(name); return i > 0 ? process.argv[i + 1] : null; };
  const here = resolve(new URL('../../..', import.meta.url).pathname), baseDir = arg('--base') && resolve(arg('--base'));
  const racks = Number(arg('--racks') ?? 60);
  const load = async root => ({
    R: await import(pathToFileURL(`${root}/kit/rack/route.js`)), M: await import(pathToFileURL(`${root}/kit/rack/model.js`)),
    Rest: await import(pathToFileURL(`${root}/kit/rack/resting.js`)), S: await import(pathToFileURL(`${root}/kit/rack/solids.js`)),
    F: await import(pathToFileURL(`${root}/spec/tests/js/cable-solids-fixture.mjs`)),
    O: await import(pathToFileURL(`${root}/spec/tests/js/route-direct-fixture.mjs`))});
  const {cornersOf} = await import('../../../kit/rack/route-path.js');
  const This = await load(here), Base = baseDir ? await load(baseDir) : null;
  const shortOf = (pts, need, share) => cornersOf(pts, {share}).filter(c => c.room_mm < need - 1e-9);
  const causeOf = at => (at === 'rest' ? 'rest' : at === 'detour' ? 'detour' : ['approach', 'entry', 'exit', 'face'].includes(at) ? 'approach' : at === 'lead' ? 'lead' : 'plug or other');
  const fam = c => (['om4', 'os2'].includes(c.media) ? 'fibre' : c.media);

  // the owner's rack, by cause, each way of sharing a leg
  for (const [name, K] of [['this tree', This], ...(Base ? [['base', Base]] : [])]) {
    const r = K.O.rack(), ctx = K.O.ctxOf(r);
    for (const share of ['half', 'need']) {
      const by = {};
      let n = 0;
      for (const c of r.cables) { const p = K.R.routePath(r, c, ctx).points; for (const x of shortOf(p, 25, share)) { n++; by[causeOf(p[x.k].at)] = (by[causeOf(p[x.k].at)] ?? 0) + 1; } }
      console.log(`owner's rack, ${name}, by ${share}: ${n} short`, JSON.stringify(by));
    }
    console.log(`  lengths mm: ${r.cables.map(c => { const l = K.R.routedLength(r, c, ctx); return `${c.id} ${(l.measured * 1000).toFixed(1)}/${l.value}`; }).join(' ')}`);
  }

  // the generated racks
  const tot = {cables: 0, crossings: 0, half: 0, need: 0, withBend: 0, front: 0, frontCables: 0}, baseTot = {crossings: 0, half: 0, need: 0, front: 0, frontCables: 0};
  const perFam = {}, deltas = [];
  let up = 0, down = 0, shorter = 0, reversed = 0, reversedShort = 0, reversedBase = 0, tested = 0;
  for (let seed = 1; seed <= racks; seed++) {
    const t = sampleRack(This.M, This.F, seed), b = Base && sampleRack(Base.M, Base.F, seed);
    t.rack.cables.forEach((c, i) => {
      const p = This.R.routePath(t.rack, c, t.ctx);
      if (!p) return;
      const need = This.Rest.bendOf(c, t.ctx);
      tot.cables++; tot.crossings += p.crossings.length;
      const radius = This.R.DIAMETERS[c.media] / 2, ahead = inFrontOfZeroU(p.points, This.S.solidsOf(t.rack, t.ctx), radius);
      tot.front += ahead; if (ahead) tot.frontCables++;
      tot.half += shortOf(p.points, need, 'half').length; tot.need += shortOf(p.points, need, 'need').length;
      (perFam[fam(c)] ||= [0, 0])[0]++;
      if (p.bends.length) { tot.withBend++; perFam[fam(c)][1]++; }
      // from the other end
      const [fwd, back] = bothWays(This.R, t.rack, c, t.ctx), pf = This.R.routePath(t.rack, fwd, t.ctx), pb = This.R.routePath(t.rack, back, t.ctx);
      tested++;
      if (Math.abs(This.R.pathLength(pf).measured - This.R.pathLength(pb).measured) > 1e-6) reversed++;
      if (pf.bends.length !== pb.bends.length) reversedShort++;
      if (b) {
        const cb = b.rack.cables[i], q = Base.R.routePath(b.rack, cb, b.ctx);
        baseTot.crossings += q.crossings.length;
        const was = inFrontOfZeroU(q.points, Base.S.solidsOf(b.rack, b.ctx), radius);
        baseTot.front += was; if (was) baseTot.frontCables++;
        baseTot.half += shortOf(q.points, need, 'half').length; baseTot.need += shortOf(q.points, need, 'need').length;
        const la = Base.R.pathLength(q), lb = This.R.pathLength(p), d = (lb.measured - la.measured) * 1000;
        deltas.push(d); if (d < -0.05) shorter++;
        if (lb.value > la.value) up++; else if (lb.value < la.value) down++;
        const [bf, bb] = bothWays(Base.R, b.rack, cb, b.ctx);
        if (Math.abs(Base.R.routedLength(b.rack, bf, b.ctx).measured - Base.R.routedLength(b.rack, bb, b.ctx).measured) > 1e-6) reversedBase++;
      }
    });
  }
  console.log(`${racks} generated racks, ${tot.cables} cables`);
  console.log(`  corners short of the cable's radius: ${tot.need} by need, ${tot.half} by halves${Base ? ` (base: ${baseTot.need} by need, ${baseTot.half} by halves)` : ''}`);
  console.log(`  cables with a bend finding: ${tot.withBend}; by family [cables, with one]: ${JSON.stringify(perFam)}`);
  console.log(`  legs through a body: ${tot.crossings}${Base ? ` (base: ${baseTot.crossings})` : ''}`);
  console.log(`  points in front of a zero-U part's outward face, every 0.5 mm: ${tot.front} on ${tot.frontCables} cables${Base ? ` (base: ${baseTot.front} on ${baseTot.frontCables})` : ''}`);
  console.log(`  written the other way round, of ${tested}: ${reversed} measure differently${Base ? ` (base: ${reversedBase})` : ''}, ${reversedShort} report a different number of bends`);
  if (Base) {
    deltas.sort((x, y) => x - y);
    console.log(`  length against the base, mm: ${deltas[0].toFixed(1)} to ${deltas.at(-1).toFixed(1)}, median ${deltas[Math.floor(deltas.length / 2)].toFixed(1)}; ${shorter} shorter; stock sizes ${up} up, ${down} down`);
  }
}

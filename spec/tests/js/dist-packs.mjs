// dist.js `fetchDist` and `packedDist` under node, over the packs
// spec/tools/dev/dist_packs.py wrote from a small built dist (process.argv[2],
// process.argv[3]). fetch is stood in for by the file system, and each scenario
// can make a path fail, answer late or answer with a status.
//
// Prints one JSON line, one key per behaviour; test_dist_packs.py asserts them.
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

const [DIST, PACKS] = process.argv.slice(2);
const BASE = 'https://page.test/dist/';
globalThis.location = { href: 'https://page.test/', search: '' };

const log = [];                 // every request, as fetch was called
const faults = new Map();       // path -> list of 'net' | status | {gate, status?}, used in turn
const override = new Map();     // path -> body served instead of the file
globalThis.fetch = async (url, init) => {
  log.push({ url: String(url), init });
  const path = String(url).startsWith(BASE) ? String(url).slice(BASE.length) : null;
  const f = faults.get(path)?.shift();
  if (f === 'net') throw new TypeError('network down');
  if (typeof f === 'number') return new Response('error', { status: f });
  if (f?.gate) { await f.gate; if (f.status) return new Response('error', { status: f.status }); }
  if (path === null) return new Response('not found', { status: 404 });
  if (override.has(path)) return new Response(override.get(path));
  const file = path.startsWith('packs/') ? join(PACKS, path.slice('packs/'.length)) : join(DIST, path);
  return existsSync(file) ? new Response(readFileSync(file)) : new Response('not found', { status: 404 });
};

const D = await import('../../../kit/dist.js');
const R = await import('../../../kit/relief.js');
const { fetchDist, packedDist, flatDist, jdist, clearDistCache } = D;

const paths = () => log.map(l => l.url.slice(BASE.length));
const tick = () => new Promise(r => setTimeout(r, 15));
const gate = () => { let release; const p = new Promise(r => { release = r; }); return { gate: p, release }; };
const reset = () => { clearDistCache(); R.clearSvgCache(); faults.clear(); override.clear(); log.length = 0; };
const fresh = async () => { reset(); const at = await packedDist(BASE); log.length = 0; return at; };
const read = p => readFileSync(join(DIST, p));
const isSvg = async r => r.ok && (await r.text()).startsWith('<svg');

const devices = JSON.parse(read('devices.json')).devices.map(d => d.name);
const facesOf = name => [...new Set(JSON.parse(read(`${name}.configs.json`)).configs.flatMap(c => Object.values(c.files)))];
const skins = readdirSync(join(DIST, 'components')).filter(f => f.endsWith('.svg')).sort();
const CFG = 'acme-two.configs.json';
const out = {};

// every face and skin through a packed dist is the file flatDist reads
{
  const at = await fresh();
  const flat = flatDist(BASE);
  const eq = { devices: 0, faces: 0, skins: 0, hits: 0, mismatches: [] };
  const check = async path => {
    const want = read(path);
    const a = await fetchDist(at(path)), b = await fetchDist(flat(path));
    const got = Buffer.from(await a.text()), plain = Buffer.from(await b.text());
    if (a.ok && b.ok && got.equals(want) && plain.equals(want)) eq.hits++; else eq.mismatches.push(path);
  };
  for (const d of devices) {
    eq.devices++;
    await jdist(at(`${d}.configs.json`));
    for (const f of facesOf(d)) { eq.faces++; await check(f); }
  }
  for (const s of skins) { eq.skins++; await check(`components/${s}`); }
  out.equal = eq;
}

// where each kind of path is
{
  const at = await fresh();
  out.urls = {
    configs: at(CFG), source: at('acme-two.source.json'), devices: at('devices.json'),
    rack: at('racks/acme--frame.rack.json'), face: at('acme-two.wide.front.svg'),
    skins: Object.fromEntries(skins.map(s => [s, at(`components/${s}`)])),
    inherited: at('components/constructor--x--v1--default.svg'),
  };
}

// a plain URL is fetch, arguments and all
{
  reset();
  await fetchDist(`${BASE}acme-one.configs.json`, { method: 'HEAD' });
  const first = log[0];
  log.length = 0;
  await fetchDist('https://page.test/x.json#frag');
  out.plain = { url: first.url, method: first.init.method, hashOnly: log[0].url };
}

// routing, with configs.json loaded
{
  const at = await fresh();
  await jdist(at(CFG));
  log.length = 0;
  const ask = async path => { log.length = 0; const r = await fetchDist(at(path)); return [paths(), r]; };
  const [other, a] = await ask('acme-two.wide.front.svg');
  const [dflt, b] = await ask('acme-two.front.svg');
  const [shared, c] = await ask('acme-two.rear.svg');
  out.loaded = { other, default: dflt, shared, texts: [await isSvg(a), await isSvg(b), await isSvg(c)] };
}

// routing, with configs.json still on its way
{
  const at = await fresh();
  const g = gate();
  faults.set(CFG, [g]);
  const cp = jdist(at(CFG));
  const fp = fetchDist(at('acme-two.wide.front.svg'));
  await tick();
  const beforeRelease = paths();
  g.release();
  const r = await fp;
  await cp;
  out.pending = { beforeRelease, afterRelease: paths(), hit: await isSvg(r) };
}

// routing, with configs.json failed
{
  let at = await fresh();
  faults.set(CFG, [404]);
  await jdist(at(CFG)).catch(() => {});
  log.length = 0;
  const a = await fetchDist(at('acme-two.wide.front.svg'));
  const other = paths();
  at = await fresh();
  faults.set(CFG, [404]);
  await jdist(at(CFG)).catch(() => {});
  log.length = 0;
  const b = await fetchDist(at('acme-two.front.svg'));
  const dflt = paths();
  at = await fresh();
  const g = gate();
  faults.set(CFG, [{ gate: g.gate, status: 500 }]);
  const cp = jdist(at(CFG)).catch(() => {});
  const fp = fetchDist(at('acme-two.wide.front.svg'));
  await tick();
  g.release();
  const c = await fp;
  await cp;
  out.failed = { other, otherHit: await isSvg(a), default: dflt, defaultHit: await isSvg(b),
                 pendingThenFailed: paths(), pendingThenFailedHit: await isSvg(c) };
}

// routing, with a configs.json that names no files
{
  const at = await fresh();
  const bare = n => JSON.stringify({ device: n, default: 'default', configs: [{ name: 'default' }, { name: 'wide' }] });
  override.set(CFG, bare('acme-two'));
  override.set('acme-one.configs.json', bare('acme-one'));
  await jdist(at(CFG));
  await jdist(at('acme-one.configs.json'));
  log.length = 0;
  const a = await fetchDist(at('acme-two.wide.front.svg'));
  const other = paths();
  log.length = 0;
  const b = await fetchDist(at('acme-one.zzz.svg'));
  out.noFiles = { other, otherHit: await isSvg(a), noMore: paths(), noMoreStatus: b.status };
}

// a face no configuration names
{
  const at = await fresh();
  await jdist(at(CFG));
  log.length = 0;
  const a = await fetchDist(at('acme-two.wide.side.svg'));
  const b = await fetchDist(at('acme-two.wide.side.svg'));
  out.unnamed = { requests: paths(), statuses: [a.status, b.status] };
}

// every kind of miss answers a fresh Response
{
  const ms = [];
  let at = await fresh();
  await jdist(at(CFG));
  ms.push(await fetchDist(at('acme-two.wide.side.svg')), await fetchDist(at('acme-two.wide.side.svg')));
  at = await fresh();
  faults.set(CFG, [404]);
  await jdist(at(CFG)).catch(() => {});
  ms.push(await fetchDist(at('acme-two.nothing.svg')));
  const asked = log.length;
  ms.push(await fetchDist(at('acme-two.nothing.svg')));
  const oneRequest = log.length === asked;
  at = await fresh();
  const ghost = `${BASE}packs/devices/acme-ghost.json#acme-ghost.front.svg`;
  ms.push(await fetchDist(ghost), await fetchDist(ghost));
  let readable = true;
  for (const m of ms) { if (m.bodyUsed) readable = false; try { await m.text(); } catch { readable = false; } }
  out.misses = { statuses: ms.map(m => m.status), distinct: new Set(ms).size === ms.length, readable, oneRequest };
}

// a pack that is not there is remembered
{
  const at = await fresh();
  const ghost = f => `${BASE}packs/devices/acme-ghost.json#${f}`;
  const rs = [await fetchDist(ghost('acme-ghost.front.svg')), await fetchDist(ghost('acme-ghost.front.svg')),
              await fetchDist(ghost('acme-ghost.rear.svg'))];
  out.ghost = { statuses: rs.map(r => r.status), requests: paths(), at: typeof at };
}

// a failure is tried again once, and is not remembered
{
  const run = async faultList => {
    const at = await fresh();
    faults.set('packs/devices/acme-one.json', faultList);
    const first = await fetchDist(at('acme-one.front.svg')).then(r => r, () => null);
    const firstRequests = log.length;
    const second = await fetchDist(at('acme-one.front.svg'));
    return { first, firstRequests, second, secondRequests: log.length - firstRequests, at };
  };
  const once = async f => {
    const r = await run(f);
    const at = r.at;
    return { requests: r.firstRequests, hit: await isSvg(r.first), laterRequests: r.secondRequests };
  };
  out.retry = {
    netOnce: await once(['net']),
    fiveOnce: await once([503]),
  };
  const twice = async f => {
    const r = await run(f);
    return { first: r.first ? r.first.status : 'rejected', firstRequests: r.firstRequests,
             second: r.second.status, secondRequests: r.secondRequests };
  };
  out.retry.netTwice = await twice(['net', 'net']);
  out.retry.fiveTwice = await twice([503, 503]);
}

// a hit is a new Response each time, typed by the file name
{
  const at = await fresh();
  const a = await fetchDist(at('acme-one.front.svg')), b = await fetchDist(at('acme-one.front.svg'));
  out.hit = { distinct: a !== b, same: (await a.text()) === (await b.text()), type: a.headers.get('content-type') };
}

// clearDistCache forgets the packs
{
  const at = await fresh();
  const packReqs = () => paths().filter(p => p.startsWith('packs/devices/')).length;
  await fetchDist(at('acme-one.front.svg'));
  const one = packReqs();
  await fetchDist(at('acme-one.rear.svg'));
  const two = packReqs();
  clearDistCache();
  await fetchDist(at('acme-one.front.svg'));
  out.cleared = [one, two, packReqs()];
}

// packedDist is ready when its index has loaded
{
  reset();
  const g = gate();
  faults.set('packs/components/index.json', [g]);
  let done = false;
  const p = packedDist(BASE).then(a => { done = true; return a; });
  await tick();
  const resolvedEarly = done, requested = paths().includes('packs/components/index.json');
  g.release();
  const at = await p;
  reset();
  faults.set('packs/components/index.json', [404]);
  out.ready = { resolvedEarly, resolvedAfter: done, indexRead: requested && typeof at === 'function',
                noIndex: await packedDist(BASE).then(() => 'loaded', e => String(e.message)) };
}

// svgSource: a rejection is dropped, a 404 stays as ''
{
  reset();
  const scope = R.createReliefScope();
  const u = `${BASE}acme-one.front.svg`;
  faults.set('acme-one.front.svg', ['net']);
  const firstRejected = await R.svgSource(u, scope).then(() => false, () => true);
  const second = await R.svgSource(u, scope);
  const requests = log.length;
  log.length = 0;
  const m = `${BASE}nothing.svg`;
  const missing = [await R.svgSource(m, scope), await R.svgSource(m, scope)];
  out.svgSource = { firstRejected, second, requests, missing, missingRequests: log.length };
}

console.log(JSON.stringify(out));

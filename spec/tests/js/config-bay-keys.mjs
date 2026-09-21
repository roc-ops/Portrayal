// Every configuration's bay key, read the way the explorer reads it, names a
// bay in that configuration's drawing and finds the configured occupant there.
//
// The manifest keys a nested bay without the `/module` steps and the drawing
// puts them in, so the kit translates with `configBayPath`. This runs that
// translation against real compiled output rather than against a copy of the
// rule, so a key the renderer ignores and a translation the kit gets wrong fail
// the same way.
//
// usage: node config-bay-keys.mjs <dist dir>
import {readdirSync, readFileSync} from 'node:fs';
import {join} from 'node:path';

const {configBayPath} = await import('../../../kit/swap.js');
const dir = process.argv[2];
const files = readdirSync(dir);
const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

const rows = [];
for (const f of files.filter(f => f.endsWith('.configs.json'))) {
  const name = f.slice(0, -'.configs.json'.length);
  const idx = JSON.parse(readFileSync(join(dir, f), 'utf8'));
  for (const cfg of idx.configs) {
    const faces = files.filter(s => s.startsWith(`${name}.${cfg.name}.`) && s.endsWith('.svg'))
      .map(s => readFileSync(join(dir, s), 'utf8'));
    for (const [key, ref] of Object.entries(cfg.bays || {})) {
      const path = configBayPath(key);
      const bayRe = new RegExp(`<g [^>]*data-path="${esc(path)}"[^>]*data-class="bay"`);
      const modRe = new RegExp(`<g [^>]*data-path="${esc(path)}/module"[^>]*>`);
      const bay = faces.some(t => bayRe.test(t));
      const seated = faces.map(t => modRe.exec(t)?.[0]).filter(Boolean)
        .map(tag => (/data-ref="([^"]*)"/.exec(tag)?.[1] || '').split(':')[0]);
      rows.push({device: name, config: cfg.name, key, path, ref, bay, seated});
    }
  }
}
console.log(JSON.stringify(rows));

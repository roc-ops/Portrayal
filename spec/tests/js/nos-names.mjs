// kit/nosnames.js against the build (#712). Prints one JSON line: every
// listing's expanded names, the edge-case vectors, and the inspector answers,
// for test_nos_names_js.py to compare with dcim_export.listing_names.
import { readFileSync, existsSync } from 'node:fs';
import { listingNames, expandName, nosNameFor } from '../../../kit/nosnames.js';

const vectors = JSON.parse(readFileSync(new URL('./nos-name-vectors.json', import.meta.url)));
const out = {vectors: {}, refused: {}, dist: null, inspector: {}};
for (const [label, rule] of Object.entries(vectors.rules)) {
  try { out.vectors[label] = Object.fromEntries(
          Object.entries(listingNames({interfaces: [rule]})).map(([k, v]) => [k, v.name])); }
  catch (e) { out.vectors[label] = {error: true}; }
}
for (const pat of vectors.refused) {
  try { expandName(pat, 3); out.refused[pat] = false; } catch { out.refused[pat] = true; }
}
const dist = new URL('../../../library/dist/listings.json', import.meta.url);
if (existsSync(dist)) {
  const L = JSON.parse(readFileSync(dist)).listings;
  out.dist = Object.fromEntries(Object.entries(L).map(([k, ls]) =>
    [k, Object.fromEntries(Object.entries(listingNames(ls)).map(([p, v]) => [p, v.name]))]));
  const pick = (k, p) => L[k] ? nosNameFor(L[k], p) : 'absent';
  out.inspector = {
    arcos7: pick('arrcus/as7726-32x', 'port-7'),
    arcosMgmtSfp: pick('arrcus/as7726-32x', 'mgmt-sfp-1'),
    arcosGap: pick('arrcus/s9510-28dc', 'port-0'),
    none: nosNameFor(null, 'port-7'),
  };
}
console.log(JSON.stringify(out));

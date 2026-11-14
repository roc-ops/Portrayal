// The x-sweep of kit/plan.js against the answers the Python version is held to.
//
//   node plan-parity.mjs <kit/plan.js> <sweep-cases.json> <body-cases.json>
//
// Reads both shared files itself, checks every case, and prints
// {checked, names, failures: [...]}. test_plan_js.py asserts the failures are empty and that every
// case of both files was checked, so a case that is skipped is a failure, not a silence.
import * as fs from 'node:fs';
import { pathToFileURL } from 'node:url';

const [, , kit, sweepFile, bodyFile] = process.argv;
const P = await import(pathToFileURL(kit).href);
const sweepCases = JSON.parse(fs.readFileSync(sweepFile, 'utf8')).cases;
const bodyCases = JSON.parse(fs.readFileSync(bodyFile, 'utf8')).cases;

const EPS = 1e-6;
// nested arrays of numbers equal to a millionth of a millimetre
function close(a, b) {
  if (typeof a === 'number' && typeof b === 'number') return Math.abs(a - b) <= EPS;
  if (Array.isArray(a) && Array.isArray(b)) return a.length === b.length && a.every((x, i) => close(x, b[i]));
  if (a && b && typeof a === 'object' && typeof b === 'object') {
    const ka = Object.keys(a).sort(), kb = Object.keys(b).sort();
    return ka.length === kb.length && ka.every((k, i) => k === kb[i] && close(a[k], b[k]));
  }
  return a === b;
}

const tuples = poly => poly.map(p => [p[0], p[1]]);
const rects = (intervals, width) => intervals.map(([a, b]) => [[0, a], [width, a], [width, b], [0, b]]);
const pieceList = pieces => pieces.map(p => P.polygon(p));

const failures = [], names = [];
function check(name, got, want) {
  names.push(name);
  if (!close(got, want)) failures.push({name, got, want});
}

for (const c of sweepCases) {
  switch (c.kind) {
    case 'abscissae':
      check(c.name, P.mergeAbscissae(c.input), c.expected);
      break;
    case 'clip':
      check(c.name, pieceList(P.sweep([[tuples(c.polygon)], rects(c.intervals, c.width)])), c.expected);
      break;
    case 'union':
      check(c.name, P.unionLoops(c.polygons.map(tuples)), c.expected);
      break;
    case 'minus':
      check(c.name, P.loops(P.sweep([[tuples(c.polygon)]], [[tuples(c.take)]])), c.expected);
      break;
    case 'clipped-union':
      check(c.name, P.unionLoops(c.polygons.map(tuples), c.clip), c.expected);
      break;
    case 'snap': {
      const got = P.snapPolygon(tuples(c.polygon), c.targets.x, c.targets.y);
      check(c.name + ' (points)', got.points, c.expected);
      check(c.name + ' (snaps)', got.snaps, c.snaps);
      break;
    }
    case 'rows':
      check(c.name, P.rows(tuples(c.section), c.depth), c.expected);
      break;
    case 'body': {
      const got = P.planBody({width: c.width, depth: c.depth, height: c.height, section: c.section,
                              'plan-outline': c.plan});
      check(c.name + ' (no snaps)', got.snaps, []);
      check(c.name, got.solid.map(s => ({band: s.band, heights: s.heights, pieces: pieceList(s.pieces)})), c.expected);
      break;
    }
    default:
      failures.push({name: c.name, got: `no handler for kind ${c.kind}`, want: null});
  }
}

for (const c of bodyCases) {
  const got = P.planBody(c.chassis);
  check(c.name + ': snaps', got.snaps, c.snaps);
  check(c.name + ': bands', got.bands.map(b => ({heights: b.heights, points: b.points})), c.bands);
  check(c.name + ': rows', got.rows, c.rows);
  check(c.name + ': solid', got.solid.map(s => ({band: s.band, heights: s.heights, pieces: s.pieces,
                                                  loops: P.loops(s.pieces)})), c.solid);
  check(c.name + ': outline', P.unionLoops(got.bands.map(b => b.points)), c.outline);
}

console.log(JSON.stringify({checked: names.length, names, failures}));

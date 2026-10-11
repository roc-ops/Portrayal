// Adjustable positions in the kit, the half that needs no page
// (docs/adjustable-positions-design.md sections 4 to 6): what a typed value is
// worth, the rows of a control, and the move itself, run through kit/fields.js
// on the fake DOM. spec/tests/test_adjustments_js.py reads what this prints and
// holds the accept rule to adjustments.py's on one list of cases.
import { build, install } from './fake-dom.mjs';

install();
globalThis.location = {search: ''};
const F = await import('../../../kit/fields.js');

// the Python test passes {adjustments: {name: decl}, values: [...]} so the two
// sides read one list
const {adjustments: ADJ = {}, values: VALUES = []} = JSON.parse(process.argv[2] || '{}');
const out = {accepts: {}};
for (const [name, decl] of Object.entries(ADJ))
  out.accepts[name] = VALUES.map(v => F.adjustmentAccepts(decl, v, {id: 'panel-setback', on: 'SLIDER'}));

// --- a face, as render.py writes one --------------------------------------------------
const DECL = {axis: 'z', carrier: 'panel', range: [20, 180], default: 60,
              stops: {front: 20, middle: 100, rear: 180}, label: 'Panel setback',
              datum: 'the front face of the panel'};
const face = (at, nodes) => build({t: 'svg', a: {'data-adjustments': JSON.stringify({'panel-setback': {...DECL, at}})}, c: [
  {t: 'rect', a: {id: 'chassis-faceplate', 'data-path': 'chassis', 'data-model': 'SLIDER'}},
  ...nodes]});
const M = (by, a = {}) => ({'data-moves-with': 'panel-setback', 'data-moves-by': by, ...a});
// the plan: decor rects with no transform, and one member drawn with one
const plan = at => face(at, [
  {t: 'g', a: {id: '--decor'}, c: [
    {t: 'rect', a: {id: 'panel', x: '10', y: '138.5', width: '100', height: '1.5', ...M('0 -1 0')}},
    {t: 'rect', a: {id: 'rail', x: '20', y: '140', width: '80', height: '7.5', ...M('0 -1 0')}},
    {t: 'rect', a: {id: 'side-left', x: '0', y: '0', width: '1.5', height: '200'}}]},
  {t: 'g', a: {id: 'tab', transform: 'translate(5,130) rotate(90 1 1)', 'data-path': 'tab', ...M('0 -1 0')}},
]);
// the front: a well, and a rail standing in it with a height and a profile
const front = at => face(at, [
  {t: 'g', a: {id: 'panel', 'data-path': 'panel', 'data-ref': 'fixture/slide-well@1:1.0.0',
               'data-depth': '60', transform: 'translate(10.0,0.0)', ...M('0 0 1')}},
  {t: 'g', a: {id: 'rail', 'data-path': 'rail', 'data-z-lift': '-60', 'data-in': 'panel',
               transform: 'translate(20.0,15.0)', ...M('0 0 1')}, c: [
    {t: 'g', a: {id: 'rail--rail', 'data-z-out': '-52.5'}},
    {t: 'g', a: {id: 'rail--web', 'data-z-profile': '0:-60,10:-52.5', 'data-z-profile-y': '0:-55'}}]},
  {t: 'g', a: {id: 'plain', 'data-path': 'plain', transform: 'translate(1,1)'}},
  {t: 'g', a: {id: 'seen', 'data-projection': '1', 'data-of': 'x/module', ...M('0 0 1')}},
]);
const find = (root, id) => [root, ...root.descendants()].find(n => n.getAttribute('id') === id);
const KEYS = ['transform', 'data-depth', 'data-z-lift', 'data-z-out', 'data-z-profile', 'data-z-profile-y'];
const snap = root => Object.fromEntries([root, ...root.descendants()].filter(n => n.getAttribute('id'))
  .map(n => [n.getAttribute('id'), Object.fromEntries(KEYS.filter(k => n.hasAttribute(k)).map(k => [k, n.getAttribute(k)]))]));
const stashed = root => [root, ...root.descendants()].some(n =>
  n.attributes.some(a => a.name.startsWith('data-portrayal-adjust')));
const set = v => ({panel: {'panel-setback': v}});

// --- the rows of a control ------------------------------------------------------------
const adjs = F.adjustmentsOf(plan(60));
out.of = adjs;
out.ofNone = F.adjustmentsOf(build({t: 'svg', a: {}, c: []}));
out.ofBad = F.adjustmentsOf(build({t: 'svg', a: {'data-adjustments': '{not json'}, c: []}));
out.rows = F.adjustmentRows(adjs, {});
out.rowsSet = F.adjustmentRows(adjs, set('180'));
out.rowsBetween = F.adjustmentRows(adjs, set('120.04'));
out.rowsRefused = F.adjustmentRows(adjs, set('300'));
out.rowsBuiltMoved = F.adjustmentRows(F.adjustmentsOf(plan(20)), {});
// from configs.json: no `at`, and no `id` or `on` inside an entry
out.rowsFromConfigs = F.adjustmentRows({'panel-setback': DECL, 'a-first': {...DECL, range: undefined,
  stops: {far: 100, near: 60}, label: undefined, carrier: 'x'}}, {x: {'a-first': 'far'}});
// the two-argument call: the entry `adjustmentsOf` answers names itself
out.sentenceFromFace = F.adjustmentAccepts(adjs['panel-setback'], '300');
out.sentenceBare = F.adjustmentAccepts(DECL, '300');

// --- the move, in the plane of a face -------------------------------------------------
const steps = {};
const p = plan(60);
steps.built = snap(p);
steps.drew20 = F.paintAdjustments(p, set('20'));
steps.at20 = snap(p);
F.paintAdjustments(p, set('180'));
steps.at180 = snap(p);
F.paintAdjustments(p, set('rear'));            // a stop name is the same position
steps.atRear = snap(p);
F.paintAdjustments(p, set('300'));             // not a position: as built
steps.refused = snap(p);
steps.refusedStash = stashed(p);
F.paintAdjustments(p, set('180'));
F.paintAdjustments(p, {});                     // reset
steps.reset = snap(p);
steps.resetStash = stashed(p);
F.paintAdjustments(p, new Map([['panel', {'panel-setback': '100'}]]));
steps.fromMap = snap(p).panel;
out.plan = steps;

// a face a configuration built moved: the kit moves by (value - at)
const moved = plan(20);
F.paintAdjustments(moved, set('60'));
out.fromBuilt20 = snap(moved).panel;

// --- the move, along the depth of a face ----------------------------------------------
const f = front(60);
const deep = {built: snap(f)};
F.paintAdjustments(f, set('20'));
deep.at20 = snap(f);
F.paintAdjustments(f, set('180'));
deep.at180 = snap(f);
F.paintAdjustments(f, set('60'));              // the default, set: as built
deep.at60 = snap(f);
deep.at60Stash = stashed(f);
F.paintAdjustments(f, set('180'));
F.paintAdjustments(f, {});
deep.reset = snap(f);
deep.resetStash = stashed(f);
out.front = deep;

// a field painted on the carrier does not disturb the move, and unpaint leaves it
const g = front(60);
F.paintAdjustments(g, set('180'));
F.paintFields(find(g, 'panel'), {'panel-setback': '180'});
F.unpaintFields(g);
out.afterUnpaint = {depth: find(g, 'panel').getAttribute('data-depth'),
                    value: find(g, 'panel').getAttribute('data-panel-setback')};

// --- `fields=` there and back ----------------------------------------------------------
const kept = {panel: {'panel-setback': F.adjustmentAccepts(adjs['panel-setback'], 'rear').value}};
out.encoded = F.encodeFields(kept);
out.decoded = F.decodeFields(out.encoded);
out.oneString = [' 271.20 ', '271.2', '271.24'].map(v =>
  F.encodeFields({p: {k: F.adjustmentAccepts({range: [0, 300]}, v).value}}));

console.log(JSON.stringify(out));

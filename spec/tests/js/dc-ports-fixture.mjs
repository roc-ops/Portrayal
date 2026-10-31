// A catalogue that states DC ports: the power-ends fixture with a supply whose
// two screws are the poles of one input port, a panel with two receptacles each
// a points port, a supply whose terminal is the DC port's, a port with
// `unstated` poles and a stand-in, a port whose poles are on two panels, and a
// second supply a swap can seat. The shapes are the build's (docs/format-stability.md,
// "DC ports"): `dc-ports` on a component in its own frame (a pole's `slot` its id
// inside the part), and `configs[].dc-ports` with the drawing's paths.

import {COMPONENTS as BASE, SLOTS as BASE_SLOTS, SIZES as BASE_SIZES, LUG} from './power-ends-fixture.mjs';

const comp = (ref, rest) => { const [ns, tail] = ref.split('/'), [name, major] = tail.split('@'); return {ns, name, major: `v${major}`, parts: [], cages: [], bays: {}, attrs: {}, ...rest}; };
const slot = (id, iface, accepts, rest = {}) => ({id, kind: 'connector', interface: iface, media: null, bores: [], accepts, default: null, ...rest});
const part = (id, ref, rest = {}) => ({id, ref, ...rest});
const port = (id, path, poles, rest = {}) => ({id, path, direction: 'input', voltage: {nominal: -48, range: [-44, -65]}, 'rating-a': 18, awg: [12],
  side: null, poles, ...rest});

export const P40_PLUG = 'acme/p40-plug@1', P40 = 'acme/p40-out@1';
export const PSU_48 = 'acme/psu-48@1', PSU_48B = 'acme/psu-48b@1', PSU_TERM = 'acme/psu-term@1', PSU_Q = 'acme/psu-q@1';
export const FEED = 'acme/dc-feed-block@1', OUTPUT_BLOCK = 'acme/dc-output@1', TWO_HOLE = 'acme/two-hole-lug@1';

const screw = id => part(id, 'common/terminal-screw@1');
const screwSlot = id => slot(id, 'terminal-stud', [LUG]);

export const COMPONENTS = [
  ...BASE,
  comp(TWO_HOLE, {class: 'port', mates: 'terminal-stud', attrs: {connector: 'terminal-stud', media: 'two-hole-lug'}}),
  comp(P40_PLUG, {class: 'port', mates: 'p40', attrs: {connector: 'p40', media: 'p40'}}),
  // the P40 receptacle: a part that is itself the connector slot, with the contacts of the plug as its points
  comp(P40, {class: 'inlet', interface: 'p40', attrs: {outlet: 'p40', model: 'P40 OUT', media: 'dc'}}),
  // a supply: two screws are the poles of one input port
  comp(PSU_48, {class: 'psu', kind: 'module', attrs: {model: 'PSU-48', input: 'dc'}, description: 'Acme PSU-48 - a -48 V supply.',
    parts: [screw('terminal-rtn'), screw('terminal-48v'), part('led', 'common/led-dot@1')], cages: [screwSlot('terminal-rtn'), screwSlot('terminal-48v')],
    'dc-ports': [port('input', 'input', [{role: 'rtn', slot: 'terminal-rtn'}, {role: 'batt', slot: 'terminal-48v'}])]}),
  // the supply a swap seats: one input port too, at another rating and with its poles the other way about
  comp(PSU_48B, {class: 'psu', kind: 'module', attrs: {model: 'PSU-48B', input: 'dc'}, description: 'Acme PSU-48B - another -48 V supply.',
    parts: [screw('post-a'), screw('post-b')], cages: [screwSlot('post-a'), slot('post-b', 'terminal-stud', [TWO_HOLE])],
    'dc-ports': [port('input', 'input', [{role: 'batt', slot: 'post-a'}, {role: 'rtn', slot: 'post-b'}], {'rating-a': 40})]}),
  // a supply whose DC terminal is composed and whose port is over the terminal's screws
  comp(PSU_TERM, {class: 'psu', kind: 'module', attrs: {model: 'PSU-TERM', input: 'dc'}, description: 'Acme PSU-TERM - a supply with a terminal block.',
    parts: [part('terminal', 'common/dc-terminal@1')], cages: [],
    'dc-ports': [port('input', 'input', [{role: 'rtn', slot: 'terminal/lug-1'}, {role: 'batt', slot: 'terminal/lug-2'}])]}),
  // a port whose roles nobody stated, and a stand-in
  comp(PSU_Q, {class: 'psu', kind: 'module', attrs: {model: 'PSU-Q', input: 'dc'}, description: 'Acme PSU-Q - roles not stated.',
    parts: [screw('t1'), screw('t2')], cages: [screwSlot('t1'), screwSlot('t2')],
    'dc-ports': [port('input', 'input', [{role: 'unstated', slot: 't1', 'stand-in': {order: 1}}, {role: 'unstated', slot: 't2', 'stand-in': {order: 2}}], {voltage: null})]}),
  // a placed terminal of two screws, and a placed output block of two screws
  comp(FEED, {class: 'inlet', attrs: {model: 'FEED BLOCK', media: 'dc-terminal'}, parts: [screw('lug-1'), screw('lug-2')], cages: [],
    'dc-ports': [port('input', 'input', [{role: 'rtn', slot: 'lug-1'}, {role: 'batt', slot: 'lug-2'}])]}),
  comp(OUTPUT_BLOCK, {class: 'inlet', attrs: {model: 'OUT BLOCK', media: 'dc-terminal'}, parts: [], cages: [],
    'dc-ports': [port('output', 'output', [{role: 'batt', slot: 'wire-1'}, {role: 'rtn', slot: 'wire-2'}], {direction: 'output', 'rating-a': 30, side: 'a'})]}),
];

// what a device's configuration publishes for a placed part (the placement's override applied) and for a bay's occupant
const cfgPort = (path, ref, rest) => ({...port('input', path, [], rest), ref});
const pole = (role, slot, rest = {}) => ({role, slot, ...rest});

const bay = (id, accepts, def = null) => ({id, group: 'bays', accepts, default: def});
const OUT = (id, side) => ({id: `${id}/output`, path: `${id}/output`, ref: P40, direction: 'output', voltage: {nominal: -48}, 'rating-a': 30, awg: null, side,
  poles: [pole('batt', `${id}/wire-1`), pole('rtn', `${id}/wire-2`)]});
const outputs = [OUT('output-a1', 'a'), OUT('output-b1', 'b')].map(({id: _id, ...p}) => ({id: 'output', ...p}));

export const SLOTS = {
  ...BASE_SLOTS,
  // a switch with DC supplies: psu-0 (PSU-48 by default), psu-1 (left to its default, PSU-TERM), psu-2 (PSU-Q), psu-3 (empty), a carrier
  dc: {default: 'base', 'pdu-class': null,
       bays: {front: [], rear: [bay('psu-0', [PSU_48, PSU_48B], PSU_48), bay('psu-1', [PSU_TERM, PSU_48B], PSU_TERM), bay('psu-2', [PSU_Q], PSU_Q), bay('psu-3', [PSU_48])]},
       cages: {front: [], rear: [slot('ground', 'terminal-stud', [LUG])]},
       configs: [{name: 'base', description: '', airflow: 'front-to-back', bays: {'psu-0': PSU_48, 'psu-2': PSU_Q}, occupants: {},
                  'dc-ports': [
                    {id: 'input', path: 'psu-0/module/input', ref: PSU_48, direction: 'input', voltage: {nominal: -48, range: [-44, -65]}, 'rating-a': 18, awg: [12], side: null,
                     poles: [pole('rtn', 'psu-0/module/terminal-rtn'), pole('batt', 'psu-0/module/terminal-48v')]}]}]},
  // a panel with two P40 receptacles, each a points port; one is side a and one side b by the placement's override
  panel: {default: 'base', 'pdu-class': null, bays: {front: [], rear: []},
          cages: {front: [], rear: [slot('output-a1', 'p40', [P40_PLUG]), slot('output-b1', 'p40', [P40_PLUG]), slot('feed-a/lug-1', 'terminal-stud', [LUG]),
                                    slot('feed-a/lug-2', 'terminal-stud', [LUG])]},
          configs: [{name: 'base', description: '', airflow: 'passive', bays: {}, occupants: {},
                     'dc-ports': [...outputs.map(p => ({...p, ref: OUTPUT_BLOCK})),
                                  {id: 'input', path: 'feed-a/input', ref: FEED, direction: 'input', voltage: {nominal: -48}, 'rating-a': 18, awg: null, side: 'b',
                                   poles: [pole('rtn', 'feed-a/lug-1'), pole('batt', 'feed-a/lug-2')]}]},
                    {name: 'bare', description: '', airflow: 'passive', bays: {}, occupants: {}}]},
  // a port whose poles are on two panels: its first screw is on the front and its second on the rear
  split: {default: 'base', 'pdu-class': null, bays: {front: [], rear: []},
          cages: {front: [slot('half/lug-1', 'terminal-stud', [LUG])], rear: [slot('half/lug-2', 'terminal-stud', [LUG])]},
          configs: [{name: 'base', description: '', airflow: 'passive', bays: {}, occupants: {},
                     'dc-ports': [{id: 'input', path: 'half/input', ref: FEED, direction: 'input', voltage: null, 'rating-a': null, awg: null, side: null,
                                   poles: [pole('rtn', 'half/lug-1'), pole('batt', 'half/lug-2')]}]}]},
  // a card with a bay of its own: a nested supply
  nest: {default: 'base', 'pdu-class': null, bays: {front: [], rear: [bay('carrier', ['acme/carrier@1'], 'acme/carrier@1')]}, cages: {front: [], rear: []},
         configs: [{name: 'base', description: '', airflow: 'passive', bays: {}, occupants: {}}]},
  // a part that states a DC port on a connector two ports share
  twin: {default: 'base', 'pdu-class': null, bays: {front: [], rear: []},
         cages: {front: [], rear: [slot('shared', 'p40', [P40_PLUG])]},
         configs: [{name: 'base', description: '', airflow: 'passive', bays: {}, occupants: {},
                    'dc-ports': [{id: 'a', path: 'shared/a', ref: OUTPUT_BLOCK, direction: 'output', voltage: null, 'rating-a': null, awg: null, side: null, poles: [pole('batt', 'shared/wire-1')]},
                                 {id: 'b', path: 'shared/b', ref: OUTPUT_BLOCK, direction: 'output', voltage: null, 'rating-a': null, awg: null, side: null, poles: [pole('rtn', 'shared/wire-2')]}]}]},
};
// the nested carrier: its bay holds a supply of its own
COMPONENTS.push(comp('acme/carrier@1', {class: 'mechanical', kind: 'module', attrs: {model: 'CARRIER'}, description: 'Acme CARRIER - a tray.',
  bays: {sub: {group: 'bays', accepts: [PSU_48, PSU_48B], default: PSU_48}}}));

export const SIZES = {...BASE_SIZES,
  dc: {ru: 1, w: 438, h: 43.6, d: 400, model: 'DC', manufacturer: 'Acme', kind: 'switch', configs: ['base'], default: 'base'},
  panel: {ru: 1, w: 438, h: 43.6, d: 200, model: 'PANEL', manufacturer: 'Acme', kind: 'panel', configs: ['base', 'bare'], default: 'base'},
  split: {ru: 1, w: 438, h: 43.6, d: 200, model: 'SPLIT', manufacturer: 'Acme', kind: 'panel', configs: ['base'], default: 'base'},
  nest: {ru: 1, w: 438, h: 43.6, d: 200, model: 'NEST', manufacturer: 'Acme', kind: 'switch', configs: ['base'], default: 'base'},
  twin: {ru: 1, w: 438, h: 43.6, d: 200, model: 'TWIN', manufacturer: 'Acme', kind: 'panel', configs: ['base'], default: 'base'}};
// ── for the feed checks (rack-dc-checks.mjs) ─────────────────────────────
// `fuse`: a fuse panel whose outputs are side a (30 A, twice), side b (60 A) and no side (30 A); `load`: a device whose two supplies take -48 V
// (range -40.5 to -57, 12 AWG) at 40 A and at 18 A; `plus`: a +24 V supply with pos and neg poles; `tri`: a supply whose one port has
// three poles; `negpos`: a -48 V supply whose poles are neg and pos, and `bare`: a supply of neg and pos that states no voltage.
// Every supply lists its poles BATT first, as the fuse panel's outputs do.
export const PSU_L40 = 'acme/psu-l40@1', PSU_L18 = 'acme/psu-l18@1', PSU_24 = 'acme/psu-24@1', PSU_TRI = 'acme/psu-tri@1';
export const PSU_NP = 'acme/psu-np@1', PSU_NV = 'acme/psu-nv@1';
const supply = (ref, name, poles, rest) => comp(ref, {class: 'psu', kind: 'module', attrs: {model: name, input: 'dc'}, description: `Acme ${name}.`,
  parts: [...poles.map(([, s]) => screw(s)), part('led', 'common/led-dot@1')], cages: poles.map(([, s]) => screwSlot(s)),
  'dc-ports': [port('input', 'input', poles.map(([role, s]) => ({role, slot: s})), rest)]});
const RANGE = {nominal: -48, range: [-40.5, -57]};
COMPONENTS.push(
  supply(PSU_L40, 'PSU-L40', [['batt', 'terminal-48v'], ['rtn', 'terminal-rtn']], {voltage: RANGE, 'rating-a': 40, awg: [12]}),
  supply(PSU_L18, 'PSU-L18', [['batt', 'terminal-48v'], ['rtn', 'terminal-rtn']], {voltage: RANGE, 'rating-a': 18, awg: [12]}),
  supply(PSU_24, 'PSU-24', [['pos', 'terminal-pos'], ['neg', 'terminal-neg']], {voltage: {nominal: 24, range: [20, 28]}, 'rating-a': 5, awg: [14]}),
  supply(PSU_TRI, 'PSU-TRI', [['batt', 'a'], ['rtn', 'b'], ['gnd', 'c']], {voltage: RANGE, 'rating-a': 18, awg: [12]}),
  supply(PSU_NP, 'PSU-NP', [['neg', 'terminal-neg'], ['pos', 'terminal-pos']], {voltage: {nominal: -48}, 'rating-a': 18, awg: [12]}),
  supply(PSU_NV, 'PSU-NV', [['neg', 'terminal-neg'], ['pos', 'terminal-pos']], {voltage: null, 'rating-a': 18, awg: [12]}));
const OUTR = (id, side, rating) => ({id: 'output', path: `${id}/output`, ref: OUTPUT_BLOCK, direction: 'output', voltage: {nominal: -48}, 'rating-a': rating, awg: null, side,
  poles: [pole('batt', `${id}/wire-1`), pole('rtn', `${id}/wire-2`)]});
const supplied = (...refs) => ({front: [], rear: refs.map((r, i) => bay(`psu-${i}`, [r], r))});
Object.assign(SLOTS, {
  fuse: {default: 'base', 'pdu-class': null, bays: {front: [], rear: []},
         cages: {front: [], rear: ['output-a1', 'output-a2', 'output-b1', 'output-n1'].map(id => slot(id, 'p40', [P40_PLUG]))},
         configs: [{name: 'base', description: '', airflow: 'passive', bays: {}, occupants: {},
                    'dc-ports': [OUTR('output-a1', 'a', 30), OUTR('output-a2', 'a', 30), OUTR('output-b1', 'b', 60), OUTR('output-n1', null, 30)]}]},
  load: {default: 'base', 'pdu-class': null, bays: supplied(PSU_L40, PSU_L18), cages: {front: [], rear: []},
         configs: [{name: 'base', description: '', airflow: 'front-to-back', bays: {}, occupants: {}}]},
  plus: {default: 'base', 'pdu-class': null, bays: supplied(PSU_24, PSU_NP, PSU_NV), cages: {front: [], rear: []},
         configs: [{name: 'base', description: '', airflow: 'front-to-back', bays: {}, occupants: {}}]},
  tri: {default: 'base', 'pdu-class': null, bays: supplied(PSU_TRI), cages: {front: [], rear: []},
        configs: [{name: 'base', description: '', airflow: 'front-to-back', bays: {}, occupants: {}}]},
});
for (const [ref, model] of [['fuse', 'FUSE'], ['load', 'LOAD'], ['plus', 'PLUS'], ['tri', 'TRI']])
  SIZES[ref] = {ru: 1, w: 438, h: 43.6, d: 200, model, manufacturer: 'Acme', kind: ref === 'fuse' ? 'panel' : 'switch', configs: ['base'], default: 'base'};
// `elem`: parts that draw a terminal as an element of their skin and state no DC port: a supply, a line card with an element of the same
// name, and a supply that states a DC port of its own and also lists an element
export const PSU_EL = 'acme/psu-el@1', CARD_EL = 'acme/card-el@1', PSU_ELP = 'acme/psu-elp@1';
COMPONENTS.push(
  comp(PSU_EL, {class: 'psu', kind: 'module', attrs: {model: 'PSU-EL', input: 'dc'}, description: 'Acme PSU-EL - a terminal drawn as art.', elements: ['terminal-48v', 'terminal-rtn']}),
  comp(CARD_EL, {class: 'line-card', kind: 'module', attrs: {model: 'CARD-EL'}, description: 'Acme CARD-EL - a card.', elements: ['terminal-48v']}),
  {...supply(PSU_ELP, 'PSU-ELP', [['batt', 'terminal-48v'], ['rtn', 'terminal-rtn']], {voltage: RANGE, 'rating-a': 18, awg: [12]}), elements: ['led-art']});
SLOTS.elem = {default: 'base', 'pdu-class': null, bays: {front: [], rear: [bay('psu-0', [PSU_EL], PSU_EL), bay('card-0', [CARD_EL], CARD_EL), bay('psu-1', [PSU_ELP], PSU_ELP)]},
              cages: {front: [], rear: []}, configs: [{name: 'base', description: '', airflow: 'front-to-back', bays: {}, occupants: {}}]};
SIZES.elem = {ru: 1, w: 438, h: 43.6, d: 200, model: 'ELEM', manufacturer: 'Acme', kind: 'switch', configs: ['base'], default: 'base'};
// the DC feed types of the cable types table, as the kit reads them (cable-types.json), for the checks that read a type
export const CABLE_TYPES = {
  'dc-feed-2x14awg': {media: 'power', family: 'power', dc: true, conductors: [{role: 'unstated', awg: 14}, {role: 'unstated', awg: 14}], 'ampacity-a': 15, unverified: true},
  'dc-feed-2x12awg': {media: 'power', family: 'power', dc: true, conductors: [{role: 'unstated', awg: 12}, {role: 'unstated', awg: 12}], 'ampacity-a': 20, unverified: true},
  'dc-feed-3x12awg': {media: 'power', family: 'power', dc: true, conductors: [{role: 'unstated', awg: 12}, {role: 'unstated', awg: 12}, {role: 'unstated', awg: 12}], 'ampacity-a': 20},
  'ac-cord': {media: 'power', family: 'power'},
};
const byRef = new Map(COMPONENTS.map(c => [`${c.ns}/${c.name}@${c.major.slice(1)}`, c]));
export const chassisOf = ref => SIZES[ref] || null;
export const compByRef = ref => (ref == null ? null : byRef.get(String(ref).split(':')[0]) ?? null);
export const ctx = {chassisOf, slotsOf: ref => SLOTS[ref] ?? null, compByRef};
export {LUG};

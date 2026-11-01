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
const byRef = new Map(COMPONENTS.map(c => [`${c.ns}/${c.name}@${c.major.slice(1)}`, c]));
export const chassisOf = ref => SIZES[ref] || null;
export const compByRef = ref => (ref == null ? null : byRef.get(String(ref).split(':')[0]) ?? null);
export const ctx = {chassisOf, slotsOf: ref => SLOTS[ref] ?? null, compByRef};
export {LUG};

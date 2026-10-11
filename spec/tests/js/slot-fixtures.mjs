// spec/tests/js/slot-fixtures.mjs
// A small catalogue for the rack tests that need slots: what catalog.js
// loadSlots would return for two devices, and the parts they take. Not a test
// file (the rack wrapper runs rack-*.mjs only).

export const SIZES = {
  leaf: {ru: 1, h: 43.6, d: 400, model: 'Leaf-48', manufacturer: 'Acme', configs: ['base', 'dc'], default: 'base', family: 'Leaf Switch', kind: 'switch'},
  pp: {ru: 1, h: 44, d: 300, model: 'PP-4', manufacturer: 'Acme', configs: ['empty', 'loaded'], default: 'loaded', family: null, kind: 'patch panel',
       guides: {front: ['guide-1']}},
  mgr: {ru: 1, h: 44, d: 110, mount: 'rack-face', model: 'Ring-1', manufacturer: 'Acme', configs: ['base'], default: 'base', family: null,
        kind: 'cable manager', guides: {front: ['guide-1', 'guide-2']}, passes: {front: ['window-1']}},
};
export const chassisOf = ref => (Object.hasOwn(SIZES, ref) ? SIZES[ref] : null);

const SFP = ['acme/sr@1', 'acme/lr@1', 'acme/dac@1'];
const CASSETTES = ['acme/lc6@1', 'acme/mpo2@1', 'acme/blank@1', 'acme/carrier@1'];
export const SLOTS = {
  leaf: {default: 'base',
    bays: {front: [], rear: [{id: 'psu-1', group: 'psus', accepts: ['acme/psu-ac@1', 'acme/psu-dc@1'], default: 'acme/psu-ac@1'}]},
    cages: {front: [{id: 'port-1', group: 'sfp', interface: 'sfp', media: 'sfp', accepts: SFP, default: null},
                    {id: 'port-2', group: 'sfp', interface: 'sfp', media: 'sfp', accepts: SFP, default: null}], rear: []},
    configs: [{name: 'base', description: 'AC power', airflow: 'front-to-back', bays: {}, occupants: {'port-1': 'acme/sr@1'}},
              {name: 'dc', description: 'DC power', airflow: 'front-to-back', bays: {'psu-1': 'acme/psu-dc@1'}, occupants: {}}]},
  pp: {default: 'loaded',
    bays: {front: [{id: 'bay-1', group: 'cassettes', accepts: CASSETTES, default: 'acme/blank@1'},
                   {id: 'bay-2', group: 'cassettes', accepts: CASSETTES, default: 'acme/blank@1'}], rear: []},
    cages: {front: [], rear: []},
    configs: [{name: 'empty', description: 'No cassettes', airflow: 'passive', bays: {}, occupants: {}},
              {name: 'loaded', description: 'One LC cassette', airflow: 'passive', bays: {'bay-1': 'acme/lc6@1'}, occupants: {}}]},
};

const LC = n => ({id: `lc${n}`, interface: 'lc-duplex', media: null, accepts: ['acme/lc-plug@1'], default: null, bores: []});
export const COMPONENTS = {
  'acme/psu-ac@1': {class: 'psu', description: 'AC power supply - 650 W'},
  'acme/psu-dc@1': {class: 'psu', description: 'DC power supply - 650 W'},
  'acme/sr@1': {class: 'transceiver', description: 'SR optic - 850 nm', attrs: {media: 'fiber', mode: 'multimode', face: 'lc-duplex'},
    fields: {'pull-tab': {type: 'choice', options: ['blue', 'black'], default: 'black', label: 'Pull tab'},
             label: {type: 'text', default: '', label: 'Label'}}},
  'acme/lr@1': {class: 'transceiver', description: 'LR optic - 1310 nm', attrs: {media: 'fiber', mode: 'single-mode', face: 'lc-duplex'}},
  'acme/dac@1': {class: 'transceiver', description: 'DAC end', attrs: {'cable-kind': 'dac'}},
  'acme/lc6@1': {class: 'cassette', description: 'LC cassette - six LC duplex', cages: [LC(1), LC(2)],
    parts: [{id: 'lc1', ref: 'acme/lc-adapter@1'}, {id: 'lc2', ref: 'acme/lc-adapter@1'}],
    fields: {'latch-color': {type: 'choice', options: ['blue', 'green', 'beige'], default: 'blue', label: 'Latch colour'}}},
  'acme/mpo2@1': {class: 'cassette', description: 'MPO cassette - two MPO',
    cages: [{id: 'mpo1', interface: 'mpo', media: null, accepts: [], default: null, bores: []}], parts: [{id: 'mpo1', ref: 'acme/mpo-adapter@1'}]},
  'acme/blank@1': {class: 'blank', description: 'Blank plate'},
  'acme/carrier@1': {class: 'module', description: 'Carrier - one sub-bay', bays: {'sub-1': {accepts: ['acme/lc6@1'], default: null}}},
  'acme/lc-plug@1': {class: 'plug', description: 'LC plug'},
};
export const compByRef = ref => {
  const k = ref == null ? null : String(ref).split(':')[0];
  return k && Object.hasOwn(COMPONENTS, k) ? COMPONENTS[k] : null;
};
export const slotsOf = ref => (Object.hasOwn(SLOTS, ref) ? SLOTS[ref] : null);
// What the commands and queries take: chassisOf, and the two lookups loadSlots returns.
export const ctx = {chassisOf, slotsOf, compByRef};

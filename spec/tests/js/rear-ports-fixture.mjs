// A patch enclosure with a panel and a cassette seated, and a switch: the
// catalogue as `loadSlots` hands it to the rack kit (configs.json and
// components.json, cut to what the rules read), and the ports as a page reads
// them off the drawings. The shapes are the library's: an FS FHD-1UFCE with an
// FHD-FAP12LCD panel (its rear adapters b01, b02 on a `faces.rear` component)
// and an FHD cassette (one MTP on its back).

const comp = (ref, rest) => { const [ns, tail] = ref.split('/'), [name, major] = tail.split('@'); return {ns, name, major: `v${major}`, ...rest}; };
const duplex = id => ({id, kind: 'connector', interface: 'lc-duplex', media: null, bores: ['1', '2'],
  accepts: ['common/lc-duplex-dust-cap@2', 'generic/lc-duplex-plug@2'], default: 'common/lc-duplex-dust-cap@2'});
const adapter = id => ({id, ref: 'common/lc-duplex-v-adapter@6'});

export const CARRIER = 'acme/carrier@1';
export const PANEL = 'fs/fhd-fap12lcd-os2@1', PANEL_OM4 = 'fs/fhd-fap12lcd-om4@1', CASSETTE = 'fs/fhd-1mtp6lcd-os2-a@4', BLANK = 'fs/fhd-fapb@1';
export const COMPONENTS = [
  comp('common/lc-duplex-v-adapter@6', {class: 'port', kind: 'component', attrs: {connector: 'lc', media: 'fiber'},
    parts: [{id: '1', ref: 'std/lc-bulkhead-bore@1'}, {id: '2', ref: 'std/lc-bulkhead-bore@1'}], cages: [], bays: {}}),
  comp('std/lc-bulkhead-bore@1', {class: 'port', kind: 'component', attrs: {connector: 'lc', media: 'fiber'}, parts: [], cages: [], bays: {}}),
  comp('common/mpo-flange-adapter@2', {class: 'port', kind: 'component', attrs: {connector: 'mpo', media: 'fiber'}, parts: [], cages: [], bays: {}}),
  comp('common/led-dot@1', {class: 'led', kind: 'component', attrs: {}, parts: [], cages: [], bays: {}}),
  comp(PANEL, {class: 'adapter-panel', kind: 'module', attrs: {media: 'fiber', model: 'FHD-FAP12LCDXSMF'},
    description: 'FS FHD-FAP12LCDXSMF - FHD fiber adapter panel.', faces: {rear: 'fs/fhd-fap12lcd-os2-rear@1'},
    parts: [adapter('lc01'), adapter('lc02')], cages: [duplex('lc01'), duplex('lc02')], bays: {}}),
  comp('fs/fhd-fap12lcd-os2-rear@1', {class: 'adapter-panel', kind: 'component', attrs: {media: 'fiber'},
    parts: [adapter('b01'), adapter('b02')], cages: [duplex('b01'), duplex('b02')], bays: {}}),
  comp(PANEL_OM4, {class: 'adapter-panel', kind: 'module', attrs: {media: 'fiber', model: 'FHD-FAP12LCDX10GMM'},
    description: 'FS FHD-FAP12LCDX10GMM - FHD fiber adapter panel.', faces: {rear: 'fs/fhd-fap12lcd-om4-rear@1'},
    parts: [adapter('lc01'), adapter('lc02')], cages: [duplex('lc01'), duplex('lc02')], bays: {}}),
  comp('fs/fhd-fap12lcd-om4-rear@1', {class: 'adapter-panel', kind: 'component', attrs: {media: 'fiber'},
    parts: [adapter('b01'), adapter('b02')], cages: [duplex('b01'), duplex('b02')], bays: {}}),
  comp(CASSETTE, {class: 'cassette', kind: 'module', attrs: {media: 'fiber', model: 'FHD-1MTP6LCDOS2A'},
    description: 'FS FHD-1MTP6LCDOS2A - MTP-12 to six LC duplex.', faces: {rear: 'fs/fhd-1mtp6lcd-rear@3'},
    parts: [adapter('lc1'), adapter('lc2'), {id: 'led', ref: 'common/led-dot@1'}], cages: [duplex('lc1'), duplex('lc2')], bays: {}}),
  comp('fs/fhd-1mtp6lcd-rear@3', {class: 'cassette', kind: 'component', attrs: {media: 'fiber'},
    parts: [{id: 'mtp', ref: 'common/mpo-flange-adapter@2'}],
    cages: [{id: 'mtp', kind: 'connector', interface: 'mpo', media: null, bores: [], accepts: ['common/mtp-dust-cap@1'], default: 'common/mtp-dust-cap@1'}], bays: {}}),
  // a carrier with a bay of its own, which holds a panel: a part inside a part
  comp(CARRIER, {class: 'carrier', kind: 'module', attrs: {model: 'CARRIER'}, description: 'Carrier.', parts: [], cages: [],
    bays: {'sub-1': {accepts: [PANEL], default: PANEL}}}),
  comp(BLANK, {class: 'blank', kind: 'module', attrs: {model: 'FHD-FAPB'}, description: 'FS FHD-FAPB - blank panel.', parts: [], cages: [], bays: {}}),
  comp('generic/sfp-lc@1', {class: 'transceiver', kind: 'module', attrs: {media: 'fiber', face: 'lc-duplex', mode: 'single-mode'}, parts: [], cages: [], bays: {}}),
];
const ACCEPTS = [PANEL, PANEL_OM4, CASSETTE, BLANK, CARRIER];
const bay = (id, def = null, onlyIn = null) => ({id, group: 'slots', accepts: ACCEPTS, default: def, ...(onlyIn ? {'only-in': onlyIn} : {})});
export const SLOTS = {
  // bay-7 and bay-9 ship a panel and are bays of some configurations only (`only-in`); bay-8 ships one in every
  pp: {default: 'panels', 'pdu-class': null,
       bays: {front: [bay('bay-1'), bay('bay-2'), bay('bay-3'), bay('bay-4'), bay('bay-7', PANEL, ['panels']), bay('bay-8', PANEL), bay('bay-9', PANEL, ['base'])], rear: []},
       cages: {front: [], rear: []},
       configs: [{name: 'panels', description: '', airflow: 'passive', bays: {'bay-1': PANEL, 'bay-2': CASSETTE, 'bay-4': CARRIER}, occupants: {}},
                 {name: 'base', description: '', airflow: 'passive', bays: {}, occupants: {}}]},
  sw: {default: 'base', 'pdu-class': null, bays: {front: [], rear: []},
       cages: {front: [1, 2].map(n => ({id: `port-${n}`, kind: 'cage', group: 'sfp', interface: 'sfp', media: 'sfp', accepts: ['generic/sfp-lc@1'], default: null})), rear: []},
       configs: [{name: 'base', description: '', airflow: 'front-to-back', bays: {}, occupants: {}}]},
};
export const SIZES = {pp: {ru: 1, w: 482.6, h: 44, d: 300, model: 'FHD-1UFCE', manufacturer: 'FS', kind: 'patch panel', configs: ['panels', 'base'], default: 'panels'},
                      sw: {ru: 1, w: 438, h: 43.6, d: 400, model: 'SW', manufacturer: 'Acme', kind: 'switch', configs: ['base'], default: 'base'}};
const byRef = new Map(COMPONENTS.map(c => [`${c.ns}/${c.name}@${c.major.slice(1)}`, c]));
export const chassisOf = ref => SIZES[ref] || null;
export const ctx = {chassisOf, slotsOf: ref => SLOTS[ref] ?? null, compByRef: ref => (ref == null ? null : byRef.get(String(ref).split(':')[0]) ?? null)};

// THE REAR FACE OF THE ENCLOSURE WITH THE PANEL IN BAY-1 AND THE CASSETTE IN
// BAY-2, as the build writes it and swap.js rebuilds it: each back a
// projection in its bay's cutout, `data-of` in place of `data-path`. The tree
// is the fake DOM's (fake-dom.mjs): {t, a, c}.
const g = (a, c = []) => ({t: 'g', a, c});
const rect = (x, y, w, h) => ({t: 'rect', a: {x, y, width: w, height: h}, c: []});
const back = (bayId, x, ports) => g({id: `cutout-back-${bayId}`, 'data-path': `cutout:back-${bayId}`}, [
  g({id: `${bayId}-rear`, 'data-class': 'adapter-panel', 'data-projection': '1', 'data-of': `${bayId}/module`, transform: `translate(${x},4)`},
    ports.map(([id, px, media]) => g({id: `${bayId}-rear--${id}`, 'data-class': 'port', 'data-media': media, 'data-of': `${bayId}/module/${id}`,
      transform: `translate(${px},10)`}, [rect(0, 0, 12, 10),
        g({id: `${bayId}-rear--${id}--1`, 'data-class': 'port', 'data-inner': '1', 'data-of': `${bayId}/module/${id}/1`}, [rect(1, 1, 4, 8)])])))]);
export const REAR_FACE = {t: 'svg', a: {viewBox: '0 0 482.6 44'}, c: [
  g({id: 'chassis', 'data-class': 'chassis'}, [rect(0, 0, 482.6, 44)]),
  back('bay-1', 340, [['b01', 70, 'fiber'], ['b02', 50, 'fiber']]),
  back('bay-2', 230, [['mtp', 40, 'fiber']]),
  g({id: 'ground', 'data-class': 'port', 'data-path': 'ground'}, [rect(10, 30, 6, 6)]),
  g({id: 'label-1', 'data-class': 'port'}, [rect(20, 30, 6, 6)])]};

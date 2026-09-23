// The explorer's fibre rules, run in node: what a path's fibre is, where it
// goes, and how its row reads. The entry is shaped like components.json's.
const {fibreOf, farPath, fibreLabel, connectorLabel, moduleOf} = await import('../../../kit/optical.js');

const rearComp = {parts: [{id: 'mtp1'}, {id: 'mtp2'}]};
const af = {
  parts: [{id: 'lc01'}, {id: 'lc02'}],
  faces: {rear: 'fs/rear@1'},
  optical: {ends: {
    'lc01.1': {to: 'rear:mtp2.2', label: '1'}, 'rear:mtp2.2': {to: 'lc01.1', label: '1'},
    'lc01.2': {to: 'rear:mtp2.1', label: '2'}, 'rear:mtp2.1': {to: 'lc01.2', label: '2'},
    'lc02.1': {to: 'rear:mtp2.4', label: '3'}, 'rear:mtp2.4': {to: 'lc02.1', label: '3'},
  }},
};
const compByRef = r => (r === 'fs/rear@1' ? rearComp : null);

// A splitter: a fan-out `to` (smartoptics/ppm-ocu-50-50's common.1 -> the
// two split legs), not a point-to-point path.
const splitter = {
  parts: [{id: 'common'}, {id: 'split'}],
  optical: {ends: {
    'common.1': {to: ['split.1', 'split.2'], label: '1'},
    'split.1': {to: 'common.1', label: '1'},
    'split.2': {to: 'common.1', label: '1'},
  }},
};

// A splitter's common port with no front label of its own - fibreLabel
// must spell the endpoint, never invent a number (never `0`, never the `n`
// pulled from the endpoint's own suffix).
const splitterNoLabel = {
  parts: [{id: 'common'}, {id: 'split'}],
  optical: {ends: {
    'common.1': {to: ['split.1', 'split.2'], label: null},
    'split.1': {to: 'common.1', label: '1'},
    'split.2': {to: 'common.1', label: '2'},
  }},
};

// A rear connector with one port's label null must not let `Number(null) ===
// 0` slip a phantom "0" into the run.
const gapRear = {
  optical: {ends: {
    'rear:mtp2.1': {to: 'x.1', label: '1'},
    'rear:mtp2.2': {to: 'x.2', label: null},
    'rear:mtp2.3': {to: 'x.3', label: '3'},
  }},
};

console.log(JSON.stringify({
  module: moduleOf('bay-1/module/lc01/1'),
  moduleNested: moduleOf('front-6/module/slot-2/module/lc01/1'),
  moduleNone: moduleOf('chassis'),
  // A part id that itself starts with "module" (e.g. a component literally
  // named `modulex`) must not fool a textual search for the last "/module"
  // into matching partway into it - the module boundary is the segment
  // "module" on its own, not any id that happens to start with those letters.
  moduleIdStartsWithModule: moduleOf('bay-1/module/modulex/1'),
  front: fibreOf('bay-1/module/lc01/1', af, compByRef),
  rear: fibreOf('bay-1/module/mtp2/2', af, compByRef),
  notFibre: fibreOf('bay-1/module/lc01', af, compByRef),
  screw: fibreOf('bay-1/module/mtp2/screw-left', af, compByRef),
  farFront: farPath('bay-1/module', af, 'lc01.1'),
  farRear: farPath('bay-1/module', af, 'rear:mtp2.2'),
  farUnknown: farPath('bay-1/module', af, 'lc09.1'),
  labelFront: fibreLabel(af, 'lc01.1'),
  labelRear: fibreLabel(af, 'rear:mtp2.2'),
  connRear: connectorLabel(af, 'mtp2', 'rear'),
  connFront: connectorLabel(af, 'lc01', 'front'),
  connNone: connectorLabel(af, 'mtp1', 'rear'),
  farSplit: farPath('bay-1/module', splitter, 'common.1'),
  labelSplit: fibreLabel(splitter, 'common.1'),
  labelSplitNoLabel: fibreLabel(splitterNoLabel, 'common.1'),
  connGap: connectorLabel(gapRear, 'mtp2', 'rear'),
}));

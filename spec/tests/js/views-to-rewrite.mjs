// `viewsToRewrite` is the guard `applyBayOverrides` (viewer3d.js) runs before
// fetching and rewriting a face: which views does an override map touch at
// all. It used to be inline and bay-only, so a cage-only override named no
// bay in any view and every view was skipped - the swap applied in 2D
// (shell.js) and the 3D scene, built from fetched face text and not that DOM,
// kept the old occupant. See swap.js for the full account and why the
// function lives there rather than in viewer3d.js (which imports `three`,
// unresolvable under plain node).
const m = await import('../../../kit/swap.js');

const devIndex = {
  bays: {
    'front-0': [{id: 'slot-1'}, {id: 'slot-2'}],
    'front-1': [{id: 'slot-3'}],
  },
  cages: {
    'front-0': [{id: 'port-4'}, {id: 'port-5'}],
    'rear-0': [{id: 'port-9'}],
  },
};

const out = {};

// a cage-only override names that cage's view, and only that view - the case
// that never worked before this function existed
out.cageOnly = m.viewsToRewrite(devIndex, {'port-9': 'generic/qsfp-lc@1'}).sort();

// a bay-only override behaves exactly as before
out.bayOnly = m.viewsToRewrite(devIndex, {'slot-3': 'some/card@1'}).sort();

// a device with no bays at all but with cages is not skipped outright - the
// old guard bailed on `!devIndex?.bays` before this decision ran
const noBaysDevice = {cages: {'front-0': [{id: 'port-4'}]}};
out.noBaysDevice = m.viewsToRewrite(noBaysDevice, {'port-4': 'generic/sfp-lc@1'}).sort();

// a nested (`/module/`) override still rewrites every view WITH BAYS - not a
// view that only has cages, because a nested bay is only ever found by
// walking a device bay's own drawing (nestedBays in swap.js)
out.nested = m.viewsToRewrite(devIndex, {'slot-1/module/ppm-1': 'generic/ppm@1'}).sort();

// an override naming nothing this device has touches no view
out.miss = m.viewsToRewrite(devIndex, {'nope': 'x'});

// an empty override map touches no view, and does not throw on a bare devIndex
out.empty = m.viewsToRewrite(devIndex, {});
out.emptyDevIndex = m.viewsToRewrite({}, {});
out.undefinedDevIndex = m.viewsToRewrite(undefined, {'slot-1': 'x'});

console.log(JSON.stringify(out));

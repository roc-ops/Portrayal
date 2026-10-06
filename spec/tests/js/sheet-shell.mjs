// A sheet body (spec/tests/test_sheet_shell_js.py): viewer3d asks relief.js
// whether a chassis is sheet metal, and draws its faces from both sides when
// it is. An index written before the key existed has no `shell`, and one from
// a newer build may carry a value this kit does not know - both are a box.
globalThis.location = { search: '' };
globalThis.fetch = async () => ({ ok: true, text: async () => '<svg/>' });
globalThis.CSS = {escape: s => s};
const m = await import('../../../kit/relief.js');
console.log(JSON.stringify({
  sheet: m.sheetShell({shell: 'sheet', thickness: 1.5}),
  noThickness: m.sheetShell({shell: 'sheet'}),
  box: m.sheetShell({mount: 'rack'}),
  unknown: m.sheetShell({shell: 'lattice', thickness: 2}),
  missing: m.sheetShell(undefined),
  // a well in a sheet body: the tray floor, and nothing round it
  sheetWell: m.cavityShell({d: 42, sheet: true}, 44),
  sheetWellDeep: m.cavityShell({d: 60, sheet: true}, 44),
  boxWell: m.cavityShell({d: 42}, 44),
  // a handle standing in a well starts at the well's floor
  standsOnFloor: m.standsFrom({lift: -42}),
  standsOnFace: m.standsFrom({}),
  // a face the device does not draw
  missingFaceBox: m.missingFaceFill(false),
  missingFaceSheet: m.missingFaceFill(true),
}));

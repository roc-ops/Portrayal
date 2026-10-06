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
}));

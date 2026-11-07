// What the 3D scene hides when a part is pulled on one view (#1002), on the
// shape of fs/dinrail2u: the `left` and `right` views each place `screw-upper`
// and `screw-lower`, and each side bracket is `under` both. The scene takes a
// pull as paths and, beside them, the view of each; a part pulled on `right`
// is gone from the right face - its texture and its relief - and stays on the
// left. A pull that names no view is every face's, as it was.
//
// relief.js is the module the viewer hides with (applyPulled over a face's
// text, hidePulled over its meshes). The viewer itself needs WebGL, so what is
// left to a browser is that viewer3d.js hands these the view it is given.
globalThis.location = {search: ''};
globalThis.fetch = async () => ({ok: true, text: async () => '<svg/>'});

import {Node, install} from './fake-dom.mjs';
install();
const m = await import('../../../kit/relief.js');

const part = (id, extra = {}) => new Node({'data-path': id, ...extra});
// a face as the build draws it: the bracket and its two screws, plus a projection
// of a module seated on the other face
const face = (bracket) => new Node({}, [
  part(bracket, {'data-under': 'screw-upper screw-lower'}),
  part('screw-upper', {'data-behaviour': 'mounts'}),
  part('screw-lower', {'data-behaviour': 'mounts'}),
  new Node({'data-projection': '1', 'data-of': 'bay-1/module'}),
]);
const hiddenIn = root => root.querySelectorAll('[data-portrayal-pulled]')
  .map(n => n.getAttribute('data-path') ?? n.getAttribute('data-of')).sort();

// a mesh as the scene holds it: a path, a visible flag, and what hangs under it
const mesh = path => ({userData: {portrayalPath: path}, visible: true, children: []});
const faceGroup = (view, paths) => ({userData: {portrayalView: view}, visible: true,
                                     children: paths.map(mesh)});
const scene = () => ({userData: {}, visible: true, children: [
  faceGroup('left', ['side-left', 'screw-upper', 'screw-lower']),
  faceGroup('right', ['side-right', 'screw-upper', 'screw-lower'])]});
const seen = (root, view) => root.children.find(g => g.userData.portrayalView === view)
  .children.map(c => `${c.userData.portrayalPath}:${c.visible ? 'shown' : 'hidden'}`);

const out = {};
const sc = m.createReliefScope();
const L = face('side-left'), R = face('side-right');

// the covers of the right bracket, named for the right view
m.setPulled(['screw-upper', 'screw-lower'], sc, ['right', 'right']);
m.applyPulled(L, sc, 'left');
m.applyPulled(R, sc, 'right');
out.texturesLeft = hiddenIn(L);
out.texturesRight = hiddenIn(R);
const s1 = scene();
m.hidePulled(s1, sc);
out.meshesLeft = seen(s1, 'left');
out.meshesRight = seen(s1, 'right');
out.pulledAnywhere = [...m.pulledPaths(sc)].sort();
out.pulledOnRight = [...m.pulledOn('right', sc)].sort();
out.pulledOnLeft = [...m.pulledOn('left', sc)];

// one view for every path
m.setPulled(['screw-upper'], sc, 'left');
out.oneViewForAll = [m.isPulledOn('screw-upper', 'left', sc), m.isPulledOn('screw-upper', 'right', sc)];

// a pull that names no view is every face's: the call a host made before views
m.setPulled(['screw-upper', 'screw-lower'], sc);
const L2 = face('side-left'), R2 = face('side-right');
m.applyPulled(L2, sc, 'left');
m.applyPulled(R2, sc, 'right');
out.noViewLeft = hiddenIn(L2);
out.noViewRight = hiddenIn(R2);
const s2 = scene();
m.hidePulled(s2, sc);
out.noViewMeshes = [seen(s2, 'left'), seen(s2, 'right')];

// a view a face of the text is not told: only what was pulled on every face is hidden
const L3 = face('side-left');
m.setPulled(['screw-upper'], sc, ['right']);
m.applyPulled(L3, sc);
out.textWithoutAView = hiddenIn(L3);

// the projection of a seated part goes with it, whichever face it was pulled on
m.setPulled(['bay-1/module'], sc, ['front']);
const R4 = face('side-right');
m.applyPulled(R4, sc, 'right');
out.projectionFollows = hiddenIn(R4);

// putting it back
m.setPulled([], sc);
const R5 = face('side-right');
m.applyPulled(R5, sc, 'right');
out.putBack = hiddenIn(R5);
const s3 = scene();
m.hidePulled(s3, sc);
out.meshesBack = [seen(s3, 'left'), seen(s3, 'right')].flat().every(x => x.endsWith('shown'));

console.log(JSON.stringify(out));

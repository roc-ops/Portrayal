// A module's plane on a flipped face (the underside, flipLX / flipLY): the plane is
// cut from the face canvas, which that face has mirrored, so a facet's footprint
// replayed on the cut must be mirrored within the cut's own rect. The numbers are
// the card of the browser fixture: a card 25 x 100 mm at (37.5, 20) on a 100 x 140
// face, a facet 25 x 30 mm at (37.5, 60) on it, drawn at 4 px/mm.
globalThis.location = { search: '' };
globalThis.fetch = async () => ({ ok: true, text: async () => '<svg/>' });
globalThis.CSS = {escape: s => s};
const m = await import('../../../kit/relief.js');
const r3 = v => Math.round(v * 1000) / 1000;
const out = {};

const pf = {x: 37.5, y: 20, w: 25, h: 100};
const facet = {kind: 'rect', x: 37.5, y: 60, w: 25, h: 30, facet: 'card--housing'};
const shape = {kind: 'shape', svg: '<svg/>', x: 37.5, y: 20, w: 25, h: 100};
const rect = p => ({x: r3(p.x), y: r3(p.y), w: r3(p.w), h: r3(p.h)});

out.flatFace = rect(m.cropPunch(facet, pf, false, false));
out.flatFacePx = m.punchRectPx(m.cropPunch(facet, pf, false, false), pf.x, pf.y, 4);
out.flippedBoth = rect(m.cropPunch(facet, pf, true, true));
out.flippedBothPx = m.punchRectPx(m.cropPunch(facet, pf, true, true), pf.x, pf.y, 4);
out.flippedX = rect(m.cropPunch(facet, pf, true, false));
out.flippedY = rect(m.cropPunch(facet, pf, false, true));
// a facet that does not span the card's width: card-local x 2.5 to 12.5 mirrors to 12.5 to 22.5
out.narrow = rect(m.cropPunch({...facet, x: 40, w: 10}, pf, true, false));
out.keepsFacet = m.cropPunch(facet, pf, true, true).facet;
out.theInputIsKept = [facet.x, facet.y, facet.w, facet.h];
// a punch of any other kind is the face's hole as drawn: not touched
out.shapeSame = m.cropPunch(shape, pf, true, true) === shape;
// a flat face gives back the very punch
out.flatSame = m.cropPunch(facet, pf, false, false) === facet;
console.log(JSON.stringify(out));

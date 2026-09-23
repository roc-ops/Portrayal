// Seating an occupant into a bay, in ONE place.
//
// Two callers need the identical surgery and they were never going to stay in
// step by accident:
//
//   shell.js   does it to the LIVE 2D DOM when the inspector's occupant select
//              changes, so the drawing on screen shows the swap;
//   viewer3d.js does it to the FETCHED FACE TEXT before relief is extracted from
//              it, because the 3D scene is built entirely out of that text and a
//              swap changes no file on disk.
//
// Before this module the second caller did not exist at all: the swap feature and
// the 3D view had never been connected, so every runtime swap was invisible in 3D
// on every device in both directions - swapping a card IN showed nothing and
// swapping one OUT still showed the configured occupant. It was found with an XFP
// card because that card has obvious ports; a cover-for-cover swap looks identical
// and nobody would have noticed.
//
// The obvious fix was to copy `rename` and `bayTransform` into viewer3d. That is
// the two-generators problem - two copies of a rule, each right on the day it was
// written, drifting silently afterwards - and this repository has already paid for
// it once in the state CSS. One home, two callers.
export const NS = 'http://www.w3.org/2000/svg';

// Place an occupant the way its bay holds it, matching render.py exactly.
// A rotated bay is not a translate: render.py rotates the component about its
// OWN centre and then translates so the rotated bounding box lands on the bay's
// `at`. The C40G is the case that exposes this - its slots are horizontal, so
// every card sits at rotate: 90, and a swap that only translated re-rendered the
// card upright inside a horizontal slot.
export function bayTransform(bay, c) {
  // THE SAME COMPOSITION render.py USES, and it must stay the same one:
  //
  //     translate(bay centre) rotate(deg) translate(-w/2, -h/2)
  //
  // Read left to right it states the intent: go to where the card belongs, turn
  // it, and put its middle there. Nothing is scaled - this is a rotation and two
  // translations, and the drawing stays at true millimetre scale throughout.
  //
  // The previous version translated to a PRE-COMPENSATED origin and rotated
  // about the component's own centre. That is algebraically the same thing, and
  // it is where the bug lived: it makes the caller solve backwards for an origin
  // that lands the ROTATED box correctly, and this file solved it from the
  // COMPONENT's size while render.py solved it from the BAY's. Those agree
  // exactly when the occupant matches its slot and diverge by half the mismatch
  // when it does not - so an A9K-RSP880-LT-SE swapped into an ASR 9006 landed
  // 16.4 mm from where the build puts it, and hung out through the side of the
  // chassis. There is no origin to solve for now.
  const sz = c?.insert || c?.size;
  if (!sz || !bay.size) return `translate(${bay.at[0]},${bay.at[1]})`;
  const cx = bay.at[0] + bay.size.w / 2;
  const cy = bay.at[1] + bay.size.h / 2;
  const deg = bay.rotate || 0;
  return `translate(${cx},${cy})${deg ? ` rotate(${deg})` : ''}`
       + ` translate(${-sz.w / 2},${-sz.h / 2})`;
}

// Re-address a component's own namespace into the bay's, matching render.py:
//   id="bdm--plate"        -> id="front-0--module--plate"
//   data-path="bdm/status" -> data-path="front-0/module/status"
// The component's own root id/path is the wrapper's already, so it is dropped
// rather than renamed - two nodes claiming one path is the bug this fixes.
// AN ID BASE AND A PATH BASE ARE TWO ARGUMENTS, not one used twice. render.py
// joins an id with `--` and a path with `/`, so the same bay is the element
// `slot-1--module--ppm-2` at the path `slot-1/module/ppm-2`. On a bay of the
// DEVICE those are both `slot-1` and one parameter served both by luck; a bay
// nested inside a seated module is the case where they differ, and rewriting the
// paths with the id base put every descendant of a swapped module at a path
// nothing could address. `pathBase` defaults to `idBase`, so a device bay - and
// the existing caller in the tests - reads exactly as before.
//
// `segment` IS THE WORD THE BUILD INSERTS, and an occupant has none. A module in
// a bay lives one namespace level down - `front-0--module--plate` - because the
// bay is an opening that holds something. An optic seated through `occupants:`
// is a TOP-LEVEL placement of its own, `port-4-occupant`, and render.py names
// its children `port-4-occupant--tx` / `port-4-occupant/tx` with nothing in
// between. `''` means exactly that; the default keeps every bay caller
// byte-identical.
export function rename(wrap, name, idBase, pathBase = idBase, segment = 'module') {
  const idHead = segment ? `${idBase}--${segment}` : idBase;
  const pathHead = segment ? `${pathBase}/${segment}` : pathBase;
  const renamed = new Map();
  for (const el of wrap.querySelectorAll('[id],[data-path]')) {
    const id = el.getAttribute('id');
    if (id === name) el.removeAttribute('id');
    else if (id && id.startsWith(name + '--')) {
      const to = `${idHead}--${id.slice(name.length + 2)}`;
      renamed.set(id, to);
      el.setAttribute('id', to);
    }
    const dp = el.getAttribute('data-path');
    if (dp === name) el.setAttribute('data-path', pathHead);
    else if (dp && dp.startsWith(name + '/'))
      el.setAttribute('data-path', `${pathHead}/${dp.slice(name.length + 1)}`);
    // A `data-for` IS A PATH TOO, and names a slot in the same namespace. A
    // compiled cassette face seats its shipped caps as the build seats any
    // default, `data-for="fhd-2mtp12-lc-os2-a/lc01"` - its own namespace,
    // exactly as its data-paths are - and render.py, drawing the cassette in
    // a bay, writes `bay-2/module/lc01`. Left alone, a module swapped in by
    // the explorer held caps that named no slot of the device: the swap that
    // looked for the occupant of `bay-2/module/lc01` found none, and seated a
    // plug on top of the cap (B3 Task 10a). Each token is re-keyed as a
    // data-path is; a cross-view token (`/rear/psu-0`) and one naming
    // something outside this component are left as they are.
    rekeyFor(el, name, pathHead);
  }
  // RENAMING A DEFINITION IS HALF THE JOB. A skin that clips, masks or fills by
  // reference carries `clip-path="url(#drive-carrier-25--w0)"` beside the
  // `<clipPath id="drive-carrier-25--w0">` it names. Moving the definition into
  // the bay's namespace and leaving the reference behind leaves it dangling -
  // and SVG does not fail a dangling clip-path, it draws the element UNCLIPPED.
  // So a swapped drive carrier rendered its honeycomb across the whole card
  // instead of through the three windows, and nothing anywhere said why.
  //
  // render.py has always done this - it collects the renames, then makes a
  // second pass rewriting every `url(#...)` it can see. This is that pass. 47
  // of the library's component skins carry such a reference.
  if (!renamed.size) return;
  for (const el of wrap.querySelectorAll('*')) {
    for (const {name: attr, value} of [...el.attributes]) {
      if (!value.includes('url(#')) continue;
      el.setAttribute(attr, value.replace(
        /url\(#([^)]*)\)/g, (m, id) => `url(#${renamed.get(id) || id})`));
    }
  }
}

// A `data-for` IS A PATH, re-keyed as a data-path is: each token that is
// `name` or under it moves under `pathHead`; a cross-view token and one
// naming something outside the component stay. ONE RULE for the two places a
// compiled skin is re-addressed into a device - a module seated in a bay
// (rename) and a module's back drawn in a rear hole (applyRearOverrides).
function rekeyFor(el, name, pathHead) {
  const df = el.getAttribute('data-for');
  if (!df) return;
  const to = df.split(/\s+/).map(t => t === name ? pathHead
    : t.startsWith(name + '/') ? `${pathHead}/${t.slice(name.length + 1)}` : t).join(' ');
  if (to !== df) el.setAttribute('data-for', to);
}

// The <g> that represents `ref` seated in `bay`, built from the component's
// compiled standalone skin. `ownerDoc` is whichever document will hold it - the
// live page for shell.js, a parsed face for viewer3d.js.
// `idBase` IS NOT `bayId`, AND ON A NESTED BAY THEY DIVERGE. A path uses `/` and
// a compiled id uses `--`, so the bay at path `slot-1/module/ppm-2` is the
// element `slot-1--module--ppm-2`. On a bay of the DEVICE the two happen to be
// the same string - `slot-1` - which is why one argument served both until a
// nested bay could be swapped at all: the removal below looked for an id built
// out of the path, found nothing, and the seat appended a SECOND occupant beside
// the first. The bay then held two modules and the drawing showed the old one.
// Callers pass the id off the bay element itself; it defaults to `bayId` so a
// device bay reads exactly as before.
export function seatModule(ownerDoc, bayId, bay, ref, comp, skinText, idBase = bayId) {
  const doc = new DOMParser().parseFromString(skinText, 'image/svg+xml');
  const wrap = ownerDoc.createElementNS(NS, 'g');
  wrap.setAttribute('id', `${idBase}--module`);
  wrap.setAttribute('data-path', `${bayId}/module`);
  wrap.setAttribute('data-ref', ref);
  wrap.setAttribute('transform', bayTransform(bay, comp));

  // A standalone component skin is addressed in its OWN namespace: the file
  // carries `<g id="bdm" data-path="bdm">` plus siblings `bdm--screw-t` and so
  // on. render.py rewrites all of that into the bay's namespace when it builds a
  // device - `front-0--module`, `front-0/module/status` - and dropping the file's
  // nodes in verbatim skipped that step, so a swapped bay published a second root
  // called `bdm` into a drawing that already had one at `front-0/module`.
  const root = doc.getElementById(comp.name);
  if (root) for (const a of [...root.attributes])
    if (a.name.startsWith('data-') && a.name !== 'data-path' && !wrap.hasAttribute(a.name))
      wrap.setAttribute(a.name, a.value);
  for (const n of [...doc.documentElement.childNodes])
    (n === root ? [...n.childNodes] : [n]).forEach(k => wrap.appendChild(ownerDoc.importNode(k, true)));
  rename(wrap, comp.name, idBase, bayId);
  return wrap;
}

// what a projection does not carry: relief, refs, behaviour, connection points
const projectionDrops = n => n.startsWith('data-z-') || n.startsWith('data-cp')
  || ['data-depth', 'data-body-depth', 'data-ref', 'data-behaviour',
      'data-vent', 'data-groove'].includes(n);

// A GROUP MADE A PROJECTION, as render.py makes one: `data-path` becomes
// `data-of` (the path is already the part's own), and everything
// projectionDrops names goes, on the group and on every descendant. What the
// kit seats on a back (B3 Task 10b) is built exactly as a seat on a card is
// (seatOccupant: the same transform, ids, paths and lift) and then made this.
function asProjection(wrap) {
  for (const el of [wrap, ...wrap.querySelectorAll('*')]) {
    const dp = el.getAttribute('data-path');
    if (dp != null) {
      el.removeAttribute('data-path');
      el.setAttribute('data-of', dp);
    }
    for (const a of [...el.attributes])
      if (projectionDrops(a.name)) el.removeAttribute(a.name);
  }
  return wrap;
}

// WHOSE BACK A REAR PROJECTION IS. The projection strips `data-ref`, so
// render.py writes the seated module's ref beside `data-of` as `data-of-ref`
// (`fs/fhd-2mtp12-lc-os2-a@3:3.1.0`), and applyRearOverrides writes it on a
// back it rebuilds. The slots on a back are its `faces.rear` component's.
const OF_REF = 'data-of-ref';
const faceRef = f => (typeof f === 'string' ? f : f?.ref) || null;
function backProjection(rootEl, modulePath) {
  return rootEl.querySelector(`[data-projection][data-of="${CSS.escape(modulePath)}"][${OF_REF}]`);
}

// A BAY SEEN FROM BEHIND. render.py draws a seated module's back (`faces.rear`)
// inside the rear-panel hole its bay names, as a projection, and deepens the
// hole to the back of that module. A swap changes the front bay only - there is
// no bay on the rear face for applyOverrides to find - so without this the rear
// kept showing the module the BUILD seated: a 24-fibre cassette swapped in still
// showed a 1-12 MTP from behind.
//
// The hole carries what a swap needs (`data-rear-of`, `data-rear-at`); the new
// module's rear face comes from its components.json entry. Built the way
// render.py builds a projection: `data-of` in place of `data-path`, and nothing
// the kit would extract as relief. In 3D the back is the module body's own.
export async function applyRearOverrides(rootEl, overrides, loadSkin, compByRef) {
  let applied = 0;
  const NSX = 'http://www.w3.org/2000/svg';
  for (const hole of rootEl.querySelectorAll('[data-rear-of]')) {
    const bayId = hole.getAttribute('data-rear-of');
    if (!Object.prototype.hasOwnProperty.call(overrides, bayId)) continue;
    const ref = overrides[bayId];
    const comp = ref ? compByRef(ref) : null;
    const rearRef = comp?.faces?.rear || null;
    const loaded = rearRef ? await loadSkin(rearRef) : null;
    for (const old of hole.querySelectorAll(':scope > [data-projection]')) old.remove();
    applied++;
    if (!loaded) continue;            // emptied, or a module with no back to show
    const doc = new DOMParser().parseFromString(loaded.text, 'image/svg+xml');
    const [x, y] = hole.getAttribute('data-rear-at').split(',').map(Number);
    const wrap = rootEl.ownerDocument.createElementNS(NSX, 'g');
    wrap.setAttribute('id', `${bayId}-rear`);
    wrap.setAttribute('transform', `translate(${x},${y})`);
    const name = loaded.comp.name;
    const root = doc.getElementById(name);
    // THE ROOT'S OWN ATTRIBUTES COME ALONG, as render.py's projection keeps
    // instance_group's: `data-class` and `data-media` are what the tree rows
    // a part by, and without them a swapped cassette's back read as its skin's
    // <title> while the built one beside it read "module - fibre".
    for (const a of (root ? [...root.attributes] : []))
      if (!['id', 'transform', 'data-path'].includes(a.name) && !projectionDrops(a.name))
        wrap.setAttribute(a.name, a.value);
    wrap.setAttribute('data-projection', '1');
    wrap.setAttribute('data-of', `${bayId}/module`);
    wrap.setAttribute(OF_REF, comp.version ? `${ref}:${comp.version}` : ref);
    for (const n of [...doc.documentElement.childNodes])
      (n === root ? [...n.childNodes] : [n])
        .forEach(k => wrap.appendChild(rootEl.ownerDocument.importNode(k, true)));
    for (const el of wrap.querySelectorAll('*')) {
      const id = el.getAttribute('id');
      if (id && id.startsWith(name + '--')) el.setAttribute('id', `${bayId}-rear--${id.slice(name.length + 2)}`);
      const dp = el.getAttribute('data-path');
      if (dp != null) {
        el.setAttribute('data-of', `${bayId}/module` + (dp.startsWith(name + '/') ? dp.slice(name.length) : ''));
        el.removeAttribute('data-path');
      }
      // WHAT A SHIPPED CAP IS FOR, in the device's namespace: the back's
      // drawing seats its flange adapters' default caps `data-for` its own
      // paths (`fhd-2mtp12-lc-rear/mtp1`), and the build, drawing the same
      // back in the bay, writes `bay-1/module/mtp1` - rename's rule
      rekeyFor(el, name, `${bayId}/module`);
      for (const a of [...el.attributes])
        if (projectionDrops(a.name)) el.removeAttribute(a.name);
    }
    hole.appendChild(wrap);
    // AND WHAT THE MAP SEATS ON THIS BACK (B3 Task 10b). A fresh back holds
    // what it ships - the caps came with the drawing - and the keys the map
    // names under this bay (`bay-1/module/mtp1`) are seated into it now,
    // since the back they were seated on before is the one just replaced.
    const under = Object.keys(overrides).filter(k => underCarrier(k, bayId));
    if (under.length) {
      const slots = backSlotsOf(wrap, compByRef).filter(e => under.includes(e.id));
      applied += (await applyOccupantOverrides(rootEl, slots, overrides, loadSkin)).applied;
    }
  }
  return applied;
}

// SEATING AN OPTIC IN A CAGE is the other half of this module, and it is NOT
// seatModule with a different argument.
//
// PLACED BY MATE POINTS, NOT BY A BAY BOX. A bay is an opening with a size, and
// bayTransform centres the card in it. A cage has no box to centre anything in:
// the bay transform is the wrong tool for a part that is larger than its opening
// on purpose - a QSFP is 52 mm deep behind an 18 mm aperture, and its drawn face
// is not the cage's. What the build does instead (manifest.py `seat_point`,
// render.py `seat_at`) is land the optic's own `mate` connection point on the cage's,
// turned with the cage: the published cage carries its `mate` already in the
// device frame with the host's rotation applied, and `occupantAt` solves for the
// `at` that puts the optic's `mate` there while it is drawn at that same turn.
// That one formula is repeated from the build, and its parity is proved against
// a real build (spec/tests/test_cage_seat_js.py), not against itself.
//
// A SIBLING, NOT A CHILD. The build draws an occupant as a top-level placement
// beside its host, carrying `data-for="<cage>"` - that is the shape every
// consumer already reads. relief.js's `cablePoints` walks `data-for` to group a
// plug and the boot on it into one connector, and its lift is summed up the
// ANCESTOR chain; nested inside the cage, the optic would inherit the cage's
// lift twice and stop being the thing `data-for` names. So a swap removes the
// `data-for` occupant wherever it is and inserts the new one next to its host.
// A CAGE ON A CARD is the one exception, and it is the build's too (#484): the
// optic is a child of the CARD's group - still a sibling of its cage, never
// inside it - so it takes the card's translate and turn (nestedCages).
function turn([x, y], rotate) {
  const deg = (((+rotate || 0) % 360) + 360) % 360;
  const exact = {0: [1, 0], 90: [0, 1], 180: [-1, 0], 270: [0, -1]};
  const [c, s] = exact[deg] || [Math.cos(deg * Math.PI / 180), Math.sin(deg * Math.PI / 180)];
  return [x * c - y * s, x * s + y * c];
}

// render.py's `seat_at`, for a published cage and a components.json entry.
export function occupantAt(cage, comp) {
  const cx = comp.size.w / 2, cy = comp.size.h / 2;
  const [dx, dy] = turn([comp.mate[0] - cx, comp.mate[1] - cy], cage.rotate);
  const r4 = v => Math.round(v * 1e4) / 1e4;
  return [r4(cage.mate[0] - cx - dx), r4(cage.mate[1] - cy - dy)];
}

// The same shape as render.py's placement transform: the occupant turns about
// its OWN centre, with its host's rotate.
export function occupantTransform(cage, comp) {
  const [x, y] = occupantAt(cage, comp);
  return `translate(${x},${y})`
       + (cage.rotate ? ` rotate(${cage.rotate} ${comp.size.w / 2} ${comp.size.h / 2})` : '');
}

// A LIFTED SLOT IS SEATED, AS THE BUILD SEATS IT (B3 Task 9). For a slot whose
// aperture stands off the face by L, the build does two things to what it
// seats: `data-z-lift` on the occupant group, AND every descendant's
// `data-z-out` moved by render.py's `_inset_feature(feat, back=-L,
// group_lift=L)` - because `out` is absolute and `lift` is summed. The kit
// refused every such slot until it did both; seatOccupant now does
// (liftOccupant, insetFeature below), held to real builds by
// spec/tests/test_lifted_seat_js.py. The library's shipped dust caps made the
// refusal untenable: every one sits in a bore 3.175 or 1.2 proud.
//
// TWO CAGES ARE STILL REFUSED, because the build does something to the optic
// the kit does not, and no cage in the library exists to hold an
// implementation to.
//   mirror        render.py RAISES for an occupant in a mirrored host (the
//                 optic's handedness would be wrong), so the kit must not
//                 quietly seat an un-mirrored one there;
//   group-states  the build's `apply_states` rewrites the lamps inside a
//                 seated optic from its host group's `states`; the kit does
//                 not, so a kit-seated optic would carry none of them.
// Both are published on the cage entry (render.py `cage_entries`), 0 of each
// today. A refusal names its reason so the caller can say why.
export function refusalReason(cage) {
  if (!cage) return null;
  if (cage.mirror) return 'mirror';
  if (cage['group-states']) return 'group-states';
  return null;
}

// render.py's `_inset_feature`, PORTED, not re-derived: a relief feature on an
// instance mounted `back` mm behind the face, of which `groupLift` is already
// carried by a group's `data-z-lift`. `out` is absolute and moves by `back`;
// `lift` moves by `back + groupLift`; `cyl`/`bar`/`uhandle` are lengths whose
// base is `lift`, so their top moves and they are re-measured from the new
// base. A feature left wholly behind the face is dropped (null). Numbers in,
// numbers out; rounded to 4 places as the build rounds (occupantAt's r4).
export function insetFeature(feat, back, groupLift = 0) {
  if (!back && !groupLift) return feat;
  const r4 = v => Math.round(v * 1e4) / 1e4;
  const f = {...feat};
  const lb = back + groupLift;
  let top = null;
  for (const k of ['cyl', 'bar', 'uhandle'])
    if (f[k] != null) top = (f.lift || 0) + f[k];
  if (f.out != null) {
    f.out = r4(f.out - back);
    if (f.out <= 0) return null;
  }
  if (f.lift != null) {
    f.lift = r4(Math.max(0, f.lift - lb));
    if (!f.lift) delete f.lift;
  }
  if (top != null) {
    top -= lb;
    if (top <= 0) return null;
    for (const k of ['cyl', 'bar', 'uhandle'])
      if (f[k] != null) f[k] = r4(top - (f.lift || 0));
  }
  return f;
}

// HOW THE BUILD SPELLS A NUMBER, two ways. A figure `_inset_feature` rewrote
// is written `str(float)`: shortest round-trip, and `44.0`, never `44`. The
// occupant group's own `data-z-lift` is written `f"{lift:g}"`: six
// significant figures, no trailing zeros.
const pyFloat = v => (Number.isInteger(v) ? v.toFixed(1) : String(v));
export function pyG(v) {
  const n = Number(Number(v).toPrecision(6));
  if (!n) return '0';
  const e = Math.floor(Math.log10(Math.abs(n)));
  if (e >= -4 && e < 6) return String(n);
  const [mant, exp] = n.toExponential().split('e');
  return `${mant}e${exp[0] === '-' ? '-' : '+'}${exp.replace(/^[+-]/, '').padStart(2, '0')}`;
}

// The `_inset_feature` keys a relief feature carries, and every attribute the
// build writes from a feature - all absent when the feature is dropped.
const INSET_KEYS = ['out', 'lift', 'cyl', 'bar', 'uhandle'];
const FEATURE_ATTRS = ['top', 'sink', 'out', 'dome', 'vent', 'cyl', 'lift', 'bar', 'uhandle',
                       'dia', 'profile', 'profile-y', 'color', 'hole-color', 'shape', 'knurl',
                       'thread'].map(k => `data-z-${k}`).concat(['data-depth', 'data-wall']);

// EVERY FEATURE BELOW A SEATED OCCUPANT, MOVED AS THE BUILD MOVES IT. The skin
// the kit copies is the component's STANDALONE drawing, built at back 0; the
// build draws the same component seated with back -L and group lift L
// (`_seat_nested_occupants`: z_inset - lift, z_group_lift + lift; a device
// seat: -seat_lift, seat_lift), so every feature of it goes through
// `_inset_feature(feat, -L, L)`. `L` is the EFFECTIVE lift - the slot's own
// plus every ancestor's (`seat-depth`) - because `out` is measured from the
// panel, not from the card.
//
// AN INSTANCE GROUP IS NOT A FEATURE. An element with `data-ref` - a part the
// occupant composes, or an occupant seated inside it (a plug's boot) - carries
// the `data-z-lift` its composition wrote, which the build never passes
// through `_inset_feature`; its features, below it, are moved like any other.
function liftOccupant(wrap, L) {
  if (!L) return;
  for (const el of wrap.querySelectorAll('*')) {
    if (el.getAttribute('data-ref') != null) continue;
    const feat = {};
    for (const k of INSET_KEYS) {
      const v = el.getAttribute(`data-z-${k}`);
      if (v != null) feat[k] = +v;
    }
    if (!Object.keys(feat).length) continue;
    const moved = insetFeature(feat, -L, L);
    if (!moved) {
      for (const a of FEATURE_ATTRS) el.removeAttribute(a);
      continue;
    }
    for (const k of INSET_KEYS) {
      if (moved[k] == null) el.removeAttribute(`data-z-${k}`);
      else el.setAttribute(`data-z-${k}`, pyFloat(moved[k]));
    }
  }
}

// EVERY ATTRIBUTE THE OCCUPANT <g> CARRIES except its transform, as a plain
// {name: value} map so it can be checked without a DOM. Three sources, in the
// order the build layers them:
//   the skin root's data-*        - what the optic says about itself (copied as
//                                   seatModule copies them: data-path excluded);
//   cage['occupant-attrs']        - render.py's `group_side_attrs` for the host,
//                                   published per cage: a `media: qsfp-dd` group
//                                   over the contract's `media: fiber`;
//   identity                      - id, data-path, data-ref, data-for;
//   the slot's lift               - `data-z-lift`, omitted at 0.
// Nothing else.
//
// THE GROUP CARRIES ITS OWN LIFT, NOT THE EFFECTIVE ONE. relief.js sums
// `data-z-lift` up the ancestors, so a slot on a card in a raised bay writes
// only what the slot adds - `cage.lift` less nestedCages' `seat-depth`, the
// component's published figure - exactly as render.py writes `f"{lift:g}"`
// from solve_seat. The ancestors' part goes into the shift (liftOccupant). If the build ever writes an attribute none of these can supply,
// the parity test fails rather than this growing a special case.
//
// AN ID AND A PATH ARE TWO ARGUMENTS, as they are for rename: a device-level
// occupant is `port-4-occupant` at both, but one seated on a card is the
// element `front-6--module--xg0-occupant` at the path
// `front-6/module/xg0-occupant` (occupantNames). `occPath` defaults to
// `occId`, so a device cage reads exactly as before.
export function occupantAttrs(cage, ref, comp, skinRootAttrs = {}, occId = occupantNames(cage).id,
                              occPath = cage.moduleId ? occupantNames(cage).path : occId) {
  const out = {};
  for (const [k, v] of Object.entries(skinRootAttrs || {}))
    if (k.startsWith('data-') && k !== 'data-path') out[k] = v;
  Object.assign(out, cage['occupant-attrs'] || {});
  out['id'] = occId;
  out['data-path'] = occPath;
  out['data-ref'] = `${ref}:${comp.version}`;
  out['data-for'] = cage.id;
  const own = (+cage.lift || 0) - (+cage['seat-depth'] || 0);
  if (Math.abs(own) > 1e-9) out['data-z-lift'] = pyG(own);
  return out;
}

// The <g> that represents `ref` seated in `cage`, built from the component's
// compiled standalone skin - the occupant's counterpart of seatModule - with
// every feature moved by the slot's effective lift (liftOccupant).
// Returns null for a refused cage rather than a half-seated optic
// (refusalReason: mirrored, or in a group that carries states).
// `occId` / `occPath` default to occupantNames(cage): the bare
// `<cage>-occupant` for a device cage, the module-qualified pair for a cage
// on a seated card (nestedCages).
export function seatOccupant(ownerDoc, cage, ref, comp, skinText,
                             occId = occupantNames(cage).id,
                             occPath = cage.moduleId ? occupantNames(cage).path : occId) {
  if (refusalReason(cage)) return null;
  const doc = new DOMParser().parseFromString(skinText, 'image/svg+xml');
  const root = doc.getElementById(comp.name);
  const rootAttrs = {};
  if (root) for (const a of [...root.attributes]) rootAttrs[a.name] = a.value;
  const wrap = ownerDoc.createElementNS(NS, 'g');
  for (const [k, v] of Object.entries(occupantAttrs(cage, ref, comp, rootAttrs, occId, occPath)))
    wrap.setAttribute(k, v);
  wrap.setAttribute('transform', occupantTransform(cage, comp));
  for (const n of [...doc.documentElement.childNodes])
    (n === root ? [...n.childNodes] : [n]).forEach(k => wrap.appendChild(ownerDoc.importNode(k, true)));
  rename(wrap, comp.name, occId, occPath, '');
  liftOccupant(wrap, +cage.lift || 0);
  return wrap;
}

// TWO SWAPS IN FLIGHT ON ONE TARGET MUST END AS ONE, AND AS THE LATER ONE.
// Every apply below awaits a skin fetch, and a focused select fires `change`
// on every arrow key, and a view change re-seats every touched key while a
// swap may still be loading - so two applies on one cage or one bay overlap
// whenever the network is slow. Removing before the await let both find the
// old occupant gone and both insert: the face held TWO optics, the select
// showed whichever `seat()` finished last, and that is what 3D and the URL
// were given.
//
// ONE MECHANISM FOR BAYS AND CAGES: a claim per target. `seatClaims()` makes a
// claim book; `claim(key)` takes a new claim on `key`, retiring any older one,
// and returns a predicate that is true while that claim is still the newest.
// Both applies take it as `isCurrent` and consult it AFTER their await, right
// before the surgery: a stale claim touches nothing. So the later REQUEST
// wins, whichever fetch resolves first. The caller keeps the same predicate
// and checks it again before writing its own state, so the drawing and the
// state are decided by the same claim. A caller with no concurrency of its
// own (viewer3d.js applies one map to a freshly parsed face) passes nothing.
//
// A CARRIER'S CLAIMS GO WITH IT. `claim.retireUnder(carrier)` retires every
// claim keyed under a bay (underCarrier, the rule pruneCarrier drops state
// by): an optic swap on a card still loading when the card is replaced or
// emptied would otherwise pass its checks after the await, append its optic
// to the card that left, and write its ref into the state under the NEW card
// - 2D empty, state and 3D holding it. The caller retires them where it
// prunes.
export function seatClaims() {
  const newest = new Map();
  const claim = key => {
    const mine = (newest.get(key) || 0) + 1;
    newest.set(key, mine);
    return () => newest.get(key) === mine;
  };
  claim.retireUnder = carrier => {
    for (const [k, n] of newest) if (underCarrier(k, carrier)) newest.set(k, n + 1);
  };
  return claim;
}

// Apply an occupant override map - cage id -> ref, or -> null/'' for an emptied
// cage - to one compiled face. `cages` is the published `cages[view]` list,
// and may carry cages on seated cards too (nestedCages: keyed by the drawing's
// path, `front-6/module/xg0`, and seated INSIDE the card's group), and
// `loadSkin(ref)` returns {comp, text} or null (it may return a promise).
//
// The OWN-KEY rule is applyOverrides': `{port-4: null}` means the optic was
// pulled and must remove the built one, where an absent key means nobody
// touched that cage.
//
// WHAT IS REMOVED is the cage's occupant (occupantsOf): the element that is
// `data-for` the cage and either `data-behaviour="occupies"` or a part the
// cage accepts - the build's occupant or a previous swap's, a plug included
// (a plug carries no behaviour; see isOccupantOf). An LED and a port's
// silkscreen label are `data-for` the port too, and matching on `data-for`
// alone would take the lamp out with the optic.
//
// LOADED FIRST, REMOVED AFTER: there is no await between taking the old optic
// out and putting the new one in, so even two unclaimed calls cannot stack
// (see seatClaims for which of them wins).
//
// ASYNC: it RESOLVES TO `{applied, refused, failed}` - await it and read the
// result. `applied` is how many cages the map changed (the count
// applyOverrides returns). `refused` is the ids of cages the map asked to fill
// that the kit will not (see refusalReason); a refused cage is left EMPTY -
// its old occupant removed, nothing seated - so the drawing never shows an
// optic the 3D would place wrong. `failed` is the ids whose skin did not load
// (a fetch that failed, a ref the index does not know): nothing is removed,
// so the cage KEEPS what it held, and the caller learns the swap did not
// happen rather than finding an empty cage its state calls seated. A stale
// claim is none of the three - it is simply not this call's to make. swap.js
// has no console calls; reporting is the caller's job, as with
// applyAllOverrides' `dropped`. Emptying a refused cage (null) is not refused.
export async function applyOccupantOverrides(rootEl, cages, overrides, loadSkin,
                                             isCurrent = () => true) {
  let applied = 0;
  const refused = [], failed = [];
  for (const cage of cages) {
    if (!Object.prototype.hasOwnProperty.call(overrides, cage.id)) continue;
    const host = slotElement(rootEl, cage);
    if (!host) continue;
    // A CAGE ON A CARD SEATS INSIDE THE CARD. Its module group is re-found
    // by path HERE, not taken from the entry, and must still hold the card
    // the entry was read from: a bay swap between nestedCages and this call
    // replaces that group, and a cage of the card that left is no cage.
    const card = cage.moduleId ? cardOf(rootEl, cage) : null;
    if (cage.moduleId && !card) continue;
    const ref = overrides[cage.id];
    const refuse = !!ref && !!refusalReason(cage);
    const loaded = ref && !refuse ? await loadSkin(ref) : null;
    if (!isCurrent(cage.id)) continue;        // a newer swap owns this cage
    if (ref && !refuse && !loaded) { failed.push(cage.id); continue; }
    for (const old of occupantsOf(rootEl, cage)) old.remove();
    applied++;
    if (refuse) { refused.push(cage.id); continue; }
    if (!ref) continue;                       // deliberately empty
    const occ = seatOccupant(rootEl.ownerDocument, cage, ref, loaded.comp, loaded.text);
    // ON A BACK (B3 Task 10b) the seat is the same one, made a projection as
    // render.py makes what it seats there: `data-of` for `data-path`, and no
    // relief, ref, behaviour or connection point
    if (cage.projection) asProjection(occ);
    // a device cage's optic is its host's next sibling; a card cage's is the
    // LAST CHILD of the card's group, where render.py appends it (after the
    // card's own parts), so it takes the card's translate and turn
    if (card) card.appendChild(occ);
    else host.after(occ);
  }
  return {applied, refused, failed};
}

// WHAT A SLOT HOLDS, KNOWN BY WHAT NAMES IT AND WHAT IT IS - not by how it
// moves. An occupant is the element `data-for` the slot that is either
// `data-behaviour="occupies"` (an optic, a dust cap) OR a part the slot
// accepts (its `data-ref`, less the version, is in the slot's `accepts`).
//
// THE SECOND HALF IS THE PLUGS (B3 Task 10a). generic/lc-plug@2,
// lc-duplex-plug@2, sc-plug@1, mpo12-plug@1 and mpo24-plug@1 are `class:
// port` and carry NO behaviour, deliberately: test_behaviour.py holds every
// `port` to none ("a port that gains a behaviour would be given a 3D body and
// an eject control"), and each plug's `provenance.behaviour` records the
// ruling and names a class of its own for a plug body as the durable fix,
// out of scope. So a plug the kit or the build seated was never taken out:
// the removal looked for `occupies`, found nothing, and the next swap
// stacked a cap on the plug. Giving the plugs the behaviour would reopen
// that ruling and hand every plug a 3D eject control (10c's FRU keying);
// the kit reading the slot's own accept list changes nothing it draws.
//
// `data-for` ALONE IS NOT ENOUGH, as it never was: a port's LED and its
// silkscreen are `data-for` the port too, and no slot accepts an LED. A slot
// known only by id (`{id}`, no accepts) falls back to `occupies` alone - what
// the kit read before.
export function isOccupantOf(el, slot) {
  if (!el || !slot || typeof el.getAttribute !== 'function') return false;
  if (el.getAttribute('data-for') !== slot.id) return false;
  if (el.getAttribute('data-behaviour') === 'occupies') return true;
  const ref = (el.getAttribute('data-ref') || '').split(':')[0];
  if (!ref) return isProjectedOccupant(el, slot);
  return !!ref && (slot.accepts || []).includes(ref);
}

// AN OCCUPANT ON A BACK (B3 Task 10b) carries neither of those: a projection
// strips `data-ref` and `data-behaviour` (projectionDrops), from the build's
// seat and the kit's alike. What is left is its name - render.py seats an
// occupant at `<slot>-occupant`, the path a projection keeps as `data-of` -
// and that is what an LED or a label `data-for` the same slot never has.
// (A configuration may name an occupant `{ref, id}` instead; no library
// configuration keys a back that way, and one that did would not be found.)
function isProjectedOccupant(el, slot) {
  return el.getAttribute('data-path') == null
    && el.getAttribute('data-of') === `${slot.id}-occupant`;
}
export function occupantsOf(rootEl, slot) {
  if (!rootEl || !slot) return [];
  return [...rootEl.querySelectorAll(`[data-for="${CSS.escape(slot.id)}"]`)]
    .filter(el => isOccupantOf(el, slot));
}

// WHAT A CAGE HOLDS ON THIS FACE, as a ref without its version - what a
// caller records when a swap `failed` and the cage kept its old optic, so its
// state says what the drawing shows. null for an empty cage. `cage` is the
// slot entry (so a plug is found - isOccupantOf) or, as before, its id.
export function occupantRef(rootEl, cage) {
  const slot = typeof cage === 'string' ? {id: cage} : cage;
  const ref = occupantsOf(rootEl, slot)[0]?.getAttribute('data-ref') || '';
  return ref ? ref.split(':')[0] : null;
}

// The path of a bay's opening in a compiled drawing. render.py gives the bay rect
// `data-path="<bayId>"` and seats the occupant inside it, which is what makes one
// selector work on the live DOM and on a fetched face alike.
function bayGroup(rootEl, bayId) {
  return rootEl.querySelector(`[data-path="${CSS.escape(bayId)}"]`);
}

// WHICH NESTED BAYS EXIST DEPENDS ON WHAT IS SEATED, so they cannot be in the
// device manifest and never could be: a `dcp-2` has two traffic slots, and
// whether it also has two PPM bays depends on whether the thing in slot 1 is an
// A22 or a DCP-404. They are read off the DRAWING instead, which is the only
// place that knows.
//
// The carrier is the path up to the last `/module` - `slot-1/module/ppm-1` is a
// bay in whatever is seated in `slot-1` - and its `data-ref` names the component
// whose `bays` components.json now publishes.
//
// RESOLVED ON DEMAND, NOT MERGED INTO THE DEVICE'S OWN LIST. `meta.bays` means
// "the bays this device declares" and the status line counts it; a nested bay is
// a property of the current population, not of the device, and folding the two
// together would make that count answer a different question depending on what
// happened to be seated.
export function nestedBays(rootEl, compByRef) {
  const out = [];
  for (const el of rootEl.querySelectorAll('[data-class="bay"]')) {
    const path = el.getAttribute('data-path') || '';
    const cut = path.lastIndexOf('/module/');
    if (cut < 0) continue;                    // a bay on the device itself
    const carrier = bayGroup(rootEl, path.slice(0, cut + '/module'.length));
    const ref = (carrier?.getAttribute('data-ref') || '').split(':')[0];
    const bay = ref ? compByRef(ref)?.bays?.[path.slice(cut + '/module/'.length)] : null;
    if (bay) out.push({...bay, id: path});
  }
  return out;
}

// EVERY SLOT ON THE FACE, read off the drawing (B3 Task 10a; #484 began it
// with the cages on seated cards). Which slots exist on a modular chassis is
// a property of what its bays hold, so they are in no device manifest: every
// `[data-ref]` group is looked up in the index, and each of its component's
// own `cages` (components.json, in the COMPONENT's frame, cages and
// connector slots alike - `kind`) becomes an entry keyed by the drawing's
// path. The carrier is any instance, at any depth:
//   a card in a bay           `front-6/module` -> `front-6/module/xg0`;
//   a cassette in a bay       `bay-1/module`   -> `bay-1/module/lc1`;
//   an adapter composed in it `bay-1/module/lc1` -> `bay-1/module/lc1/tx`;
//   an adapter on the device  `xc01`           -> `xc01/tx`;
//   a module's back           `bay-1/module`   -> `bay-1/module/mtp1`, drawn as
//                             a projection on the rear face (backSlotsOf).
//
// NOTHING INSIDE AN OCCUPANT (P3). An element that names its host with
// `data-for`, or is inside one that does, is skipped (insideOccupant): a
// duplex plug composes two simplex plugs, each with a boot slot, and those
// are the plug's business, not the face's.
//
// A SLOT ON A SLOT IS ONE OF ITS BORES, OR IT IS NOT A SLOT. A cage wrapper
// publishes the aperture it composes as its own cage (component_cages keeps
// P2 to connector slots), and its host - the card, or the device - already
// publishes that same aperture looked through the wrapper, at the wrapper's
// path. So a slot whose carrier is itself a slot (`deviceCages`, or another
// entry here) is kept only when the carrier names it in its `bores` - the
// duplex adapter's two, which L111 makes the other level of one opening.
// Across the built library (2026-09-23) that rule drops the 112 wrapper
// apertures (`port-1/aperture`, `front-6/module/xg0/cage`) and keeps every
// card cage nestedCages ever found; without `deviceCages` a device-level
// wrapper's aperture cannot be told apart and is kept.
//
// THE CAGE IS NOT MOVED INTO THE DEVICE FRAME. The occupant is seated inside
// the carrier's group (applyOccupantOverrides), which already carries every
// translate and turn above it, so occupantTransform runs on the
// component-frame `mate` and `rotate` unchanged - render.py's
// _seat_nested_occupants does the same with the same seat_point/seat_at.
//
// SEATED ON THE EFFECTIVE FACTS (R4), the carrier's as well as the slot's,
// because the kit copies the occupant's standalone skin:
//   lift    the slot's own (a composed part's lift is in it already), PLUS
//           every `data-z-lift` from the carrier's group up (seatDepth) - the
//           shift liftOccupant applies; the occupant's own `data-z-lift` is
//           the sum less `seat-depth` (occupantAttrs);
//   mirror  the slot's own, or the carrier drawn mirrored: the build refuses
//           both.
// A device placement's author `lift:` writes no `data-z-lift`, so a slot on
// such a carrier would be shifted short; no placement in the library composes
// a slot and carries one (Task 9, concern 4).
//
// Each entry adds, to the component's slot: `id` (the drawing path), `key`
// (slotKey: the configuration's module-less key, P1), `cage` (the
// component-local id), `seat-depth`, `module` (the carrier's group element),
// `modulePath`, `moduleId` (its element id, which names the occupant) and
// `carrier` (the ref without its version, which applyOccupantOverrides
// re-checks).
//
// THE FREE LEVEL ONLY, unless `all`. A duplex adapter's slot and its two
// bores are one opening at two levels (L111): while the adapter's slot holds
// something its bores are not offered, and while a bore holds something the
// adapter's slot is not (freeLevel). What the explorer OFFERS is that;
// what a swap SEATS through is `all`, because an override map that empties
// one level and fills the other is applied in one pass, in any order.
export function nestedSlots(rootEl, compByRef, {deviceCages = [], all = false} = {}) {
  const raw = [];
  for (const mod of rootEl.querySelectorAll('[data-ref]')) {
    const modulePath = mod.getAttribute('data-path');
    if (!modulePath || insideOccupant(mod)) continue;
    const carrier = (mod.getAttribute('data-ref') || '').split(':')[0];
    let comp = null;
    try { comp = carrier ? compByRef(carrier) : null; } catch (e) { comp = null; }
    const cages = comp?.cages;
    if (!Array.isArray(cages) || !cages.length) continue;
    const depth = seatDepth(mod);
    const mirrored = /scale\(\s*-/.test(mod.getAttribute('transform') || '');
    for (const c of cages) {
      const id = `${modulePath}/${c.id}`;
      if (!bayGroup(rootEl, id)) continue;    // a slot the skin never drew
      raw.push({...c, id, key: slotKey(id), cage: c.id, lift: (+c.lift || 0) + depth,
                'seat-depth': depth, mirror: !!c.mirror || mirrored,
                module: mod, modulePath, moduleId: mod.getAttribute('id') || '', carrier});
    }
  }
  for (const back of rootEl.querySelectorAll(`[data-projection][${OF_REF}]`))
    raw.push(...backSlotsOf(back, compByRef));
  const hosts = new Map([...(deviceCages || []), ...raw].map(e => [e.id, e]));
  const out = raw.filter(e => {
    const host = hosts.get(e.modulePath);
    return !host || (host.bores || []).includes(e.cage);
  });
  if (all) return out;
  const hidden = freeLevel(rootEl, [...(deviceCages || []), ...out]);
  return out.filter(e => !hidden.has(e.id));
}

// THE SLOTS ON A MODULE'S BACK (B3 Task 10b), read off the rear projection
// render.py draws in the hole its bay names. A projection strips `data-ref`,
// so the group is known by `data-of-ref` - the seated module - and its slots
// are that module's `faces.rear` component's `cages`, each at the module's
// own path (`bay-1/module/mtp1`, keyed `bay-1/mtp1`) as the build publishes
// them. Only the back's own slots: the build accepts a key on a back only one
// step under a device bay's module (manifest.nested_key_host), and a part of
// a flange adapter is no slot. A front part or bay of the same id wins, as it
// does in the build (key_on_back); spec/tests/test_rear_slots.py holds every
// module to having none.
//
// The entry is a card's, with `projection` set: `module` is the projection
// group the occupant is seated in, `moduleId` its id (`bay-1-rear`, which
// names the occupant `bay-1-rear--mtp1-occupant` as the build does),
// `carrier` the back's component and `moduleRef` the module it is the back
// of, which applyOccupantOverrides re-checks.
function backSlotsOf(back, compByRef) {
  const modulePath = back.getAttribute('data-of');
  const moduleRef = (back.getAttribute(OF_REF) || '').split(':')[0];
  const look = r => { try { return r ? compByRef(r) || null : null; } catch (e) { return null; } };
  const module = look(moduleRef);
  const carrier = faceRef(module?.faces?.rear);
  const cages = look(carrier)?.cages;
  if (!modulePath || !Array.isArray(cages)) return [];
  const drawn = new Set([...back.querySelectorAll('[data-of]')].map(e => e.getAttribute('data-of')));
  const front = new Set((module.parts || []).map(q => q.id).concat(Object.keys(module.bays || {})));
  const depth = seatDepth(back);
  const out = [];
  for (const c of cages) {
    const id = `${modulePath}/${c.id}`;
    if (!drawn.has(id) || front.has(c.id)) continue;
    out.push({...c, id, key: slotKey(id), cage: c.id, lift: (+c.lift || 0) + depth,
              'seat-depth': depth, mirror: !!c.mirror, module: back, modulePath,
              moduleId: back.getAttribute('id') || '', carrier, moduleRef, projection: true});
  }
  return out;
}

// Kept for the callers #484 wrote; every slot is found now, not only a card's.
export const nestedCages = (rootEl, compByRef, opts) => nestedSlots(rootEl, compByRef, opts);

// A CONFIGURATION'S KEY FOR A DRAWING PATH (P1): the path with every
// `module` step dropped - manifest.slot_key_prefix, the build's own reading.
// `bay-1/module/lc1/tx` -> `bay-1/lc1/tx`; `xc01/tx` stays as it is.
export function slotKey(path) {
  return String(path).split('/').filter(s => s !== 'module').join('/');
}

// Inside, or itself, an OCCUPANT (P3): an element that names what it sits
// in with `data-for`. Not a COVER, which names what it lies over the same
// way and is `mounts` or `fills` (liesOver's reading): a card that says what
// it fronts is still a carrier. An LED's `data-for` is caught too, and costs
// nothing - an LED carries no slots.
function insideOccupant(el) {
  for (let n = el; n && typeof n.getAttribute === 'function'; n = n.parentNode)
    if (n.getAttribute('data-for') != null
        && !['mounts', 'fills'].includes(n.getAttribute('data-behaviour'))) return true;
  return false;
}

// THE LEVEL OF A DUPLEX ADAPTER THAT IS NOT FREE, as the ids to hide. For a
// slot with `bores` (published: the ids, under its own key, a connector here
// would fill): while it holds an occupant its bores are hidden; while any
// bore does, it is. Both filled cannot come of anything the explorer offers
// and the build refuses it (L111); the adapter level is shown then, so the
// drawing's contradiction is still reachable to be undone.
export function freeLevel(rootEl, slots) {
  const byId = new Map((slots || []).map(e => [e.id, e]));
  const filled = e => occupantsOf(rootEl, e).length > 0;
  const hide = new Set();
  for (const e of slots || []) {
    const bores = (e.bores || []).map(b => byId.get(`${e.id}/${b}`)).filter(Boolean);
    if (!bores.length) continue;
    if (filled(e)) for (const b of bores) hide.add(b.id);
    else if (bores.some(filled)) hide.add(e.id);
  }
  return hide;
}

// EVERY SLOT OF THE FACE AS IT STANDS: the device's own (`cages[view]`, from
// the index) and those read off the drawing (nestedSlots). What the explorer
// seats through, and what the 3D pass applies an override map to - one list,
// so the two cannot disagree about which slots exist. No face, no nested
// slots. `offered` narrows it to what the inspector may offer: the free
// level of each duplex adapter, device-level adapters included (freeLevel).
export function faceCages(rootEl, deviceCages = [], compByRef, {offered = false} = {}) {
  const device = deviceCages || [];
  if (!rootEl) return [...device];
  const nested = nestedSlots(rootEl, compByRef, {deviceCages: device, all: true});
  const every = [...device, ...nested];
  if (!offered) return every;
  const hidden = freeLevel(rootEl, every);
  return every.filter(e => !hidden.has(e.id));
}

// WHICH SLOT `path` NAMES on this face, or null - the explorer's inspector
// asks it of every selection. From the element at `path` upward, the first
// that is either
//   a slot itself - the slot, or one of its own parts (`port-4/opening`,
//                   the SMM-8x10G's composed `front-2/module/xg0/cage`), or
//   an occupant   - an element `data-for` a slot that isOccupantOf it: a
//                   click on the optic, cap or plug, or on anything inside
//                   it, offers the same select as the slot.
// Only the OFFERED level answers (faceCages' `offered`): a click on a bore
// under a duplex cap walks on up to the adapter, whose slot is the free one.
// `data-for` alone is not enough: a port's LED is `data-for` it too, and must
// stay the LED. Walked by `parentNode` and read by `getAttribute`, so a
// parsed face and the fake DOM the tests use answer as the live page does. A
// card is a `fills` module, not an occupant, so a card's own plate names no
// slot.
export function cageAt(rootEl, path, deviceCages = [], compByRef) {
  if (path == null || !rootEl) return null;
  const cages = faceCages(rootEl, deviceCages, compByRef, {offered: true});
  const byId = id => cages.find(c => c.id === id) || null;
  const own = byId(path);
  if (own) return own;
  // a part of a back is drawn `data-of` its path (B3 Task 10b): on the face
  // that shows the back, a projection is the only place that path is drawn
  const start = bayGroup(rootEl, path) || rootEl.querySelector(`[data-of="${CSS.escape(path)}"]`);
  for (let n = start; n && n !== rootEl && typeof n.getAttribute === 'function';
       n = n.parentNode) {
    const hit = byId(n.getAttribute('data-path') ?? n.getAttribute('data-of'));
    if (hit) return hit;
    const host = byId(n.getAttribute('data-for'));
    if (host && isOccupantOf(n, host)) return host;
  }
  return null;
}

// WHAT THE SELECT OFFERS FOR A SLOT, as {value, label, selected} rows:
// `empty` first, then the slot's `accepts` in its own order, the one it ships
// holding (`default`, P5) marked "(ships with)". A slot that ships nothing -
// a cage, the shuttered adapter - marks none. `current` is the ref it holds
// now, '' or null for empty.
export function slotOptions(slot, current) {
  const cur = current || '';
  return [{value: '', label: '— empty —', selected: cur === ''}]
    .concat((slot?.accepts || []).map(a => ({
      value: a, label: a === slot.default ? `${a} (ships with)` : a, selected: a === cur})));
}

// relief.js's reading of depth: `data-z-lift` summed up the ancestor chain,
// from the card's group to the root.
//
// THE THIRD SPELLING OF ONE WALK, on purpose, and the other two are
// relief.js's `nodeTools(svg).liftOf` (the 3D extractor, on `dataset` and
// `parentElement` of a live SVG) and `resolveCablePoint`'s `ancestors` sum
// (cablePoints, over a plain list). Not shared: liftOf reads `dataset` and
// stops at its own svg, the cable sum takes no DOM at all, and this one must
// walk a parsed face or a fake-dom tree that has only getAttribute and
// parentNode - three callers with three shapes of input, and a helper for a
// four-line loop would be a new module for all of them to import. If the
// rule changes - an ancestor stops counting, `out` starts to - it changes in
// all three.
function seatDepth(el) {
  let total = 0;
  for (let n = el; n && typeof n.getAttribute === 'function'; n = n.parentNode)
    total += +(n.getAttribute('data-z-lift') || 0) || 0;
  return total;
}

// The element a slot is drawn as: its `data-path`, or on a back, the part
// of the projection that is `data-of` it.
function slotElement(rootEl, cage) {
  if (!cage.projection) return bayGroup(rootEl, cage.id);
  const back = backProjection(rootEl, cage.modulePath);
  return back?.querySelector(`[data-of="${CSS.escape(cage.id)}"]`) || null;
}

// The card's group a nested cage sits in, if it is still the card the cage was
// read from; null otherwise. On a back, the projection, if it is still the
// back of the module the slot was read from.
function cardOf(rootEl, cage) {
  if (cage.projection) {
    const back = backProjection(rootEl, cage.modulePath);
    return back && (back.getAttribute(OF_REF) || '').split(':')[0] === cage.moduleRef ? back : null;
  }
  const mod = bayGroup(rootEl, cage.modulePath);
  const ref = (mod?.getAttribute('data-ref') || '').split(':')[0];
  return mod && ref === cage.carrier ? mod : null;
}

// WHAT AN OCCUPANT IS CALLED, as render.py names it. On a device cage the id
// and the path are one string, `port-4-occupant`. On a card the build names it
// inside the card's namespace (instance_group with `<card id>--<cage>-occupant`
// and `<card path>/<cage>-occupant`), so the two diverge:
// `front-6--module--xg0-occupant` at `front-6/module/xg0-occupant`.
export function occupantNames(cage) {
  if (cage?.moduleId)
    return {id: `${cage.moduleId}--${cage.cage}-occupant`, path: `${cage.id}-occupant`};
  return {id: `${cage.id}-occupant`, path: `${cage.id}-occupant`};
}

// A CONFIGURATION'S BAY KEY IS NOT A DRAWING PATH. device.yaml keys a nested
// bay without the `/module` steps - `slot-1/ppm-1`, `riser-1/slot-1` - which is
// what render.py's seating and lint's L8 both read, while the drawing, and so
// every bay id here, puts `module` between the steps: `slot-1/module/ppm-1`.
// Looking a configuration's occupant up by the drawing's id missed every nested
// one, and the picker showed the bay's default over the module actually built
// into the face - the dcp-2 ila-node's PPM-AD1-1510 read as the dummy cover.
export function configBayPath(key) {
  return String(key).split('/').join('/module/');
}

// WHAT A CONFIGURATION SEATS IN EACH BAY, keyed by the DRAWING's path - the ONE
// reading of `configs[].bays`, as builtOccupants is of `configs[].occupants`.
// Every reader goes through it: shell.js's state, the swap test
// (`swapOverrides`) and the reload filter (applySwaps' `built`). A reader that
// took the map raw compared `slot-1/module/ppm-1` with the manifest's
// `slot-1/ppm-1`, found no entry, fell back to the bay's default - and an
// UNTOUCHED dcp-2 ila-node page decided the PPM the build put there was a
// swap, wrote it into `swap=` and sent it to the 3D scene as an override.
export function builtBays(cfg) {
  const bays = cfg?.bays;
  if (!bays || typeof bays !== 'object') return {};
  return Object.fromEntries(Object.entries(bays).map(([k, ref]) => [configBayPath(k), ref]));
}

// Apply a whole override map to one compiled face. `overrides` is bay id -> ref,
// or -> null/'' for an emptied bay; bays it does not mention keep whatever the
// configuration built. `loadSkin(ref)` returns {comp, text} or null.
//
// EMPTYING A BAY IS A REAL OVERRIDE and is why the map's own keys are what is
// walked rather than its truthy values: `{slot-0: null}` means the user took the
// card out, which must remove the configured occupant, where an ABSENT key means
// they never touched that bay. Reading it the other way makes an emptied bay
// silently re-fill itself, which is the failure in the other direction and would
// look exactly like the bug this module exists to fix.
//
// `isCurrent(bayId)` is a claim from seatClaims, consulted after the await
// and before any surgery - the one mechanism a cage swap uses too. A bay
// whose claim went stale while its skin loaded is left to the newer swap:
// taking its module out here and seating the stale card after the newer one
// had seated would leave the bay holding two.
export async function applyOverrides(rootEl, bays, overrides, loadSkin, isCurrent = () => true) {
  let applied = 0;
  for (const bay of bays) {
    if (!Object.prototype.hasOwnProperty.call(overrides, bay.id)) continue;
    const g = bayGroup(rootEl, bay.id);
    if (!g) continue;
    const idBase = g.getAttribute('id') || bay.id;
    const ref = overrides[bay.id];
    // LOADED FIRST, REMOVED AFTER, as applyOccupantOverrides does: no await
    // between the removal and the insert. An unknown ref still leaves the bay
    // open, as it always has.
    const loaded = ref ? await loadSkin(ref) : null;
    if (!isCurrent(bay.id)) continue;         // a newer swap owns this bay
    g.querySelector(`[id="${CSS.escape(idBase)}--module"]`)?.remove();
    applied++;
    if (!ref) continue;                       // deliberately empty
    if (!loaded) continue;                    // unknown ref: leave the bay open
    g.appendChild(seatModule(rootEl.ownerDocument, bay.id, bay, ref,
                             loaded.comp, loaded.text, idBase));
  }
  return applied;
}

// EVERY LEVEL, BY FOLLOWING THE FRONTIER. A device's own bays are known before
// anything is applied; nested ones are not, because which nested bays exist -
// and where they are - is a property of the carrier CURRENTLY seated. So the
// only way to apply an override map to a face is to seat what you know, look
// again, and repeat while looking still finds something new.
//
// It ran ONCE and buried every nested swap in 3D; then TWICE, which covered the
// two levels the library actually has. Two is not the number - it is the depth
// of today's deepest carrier. The moment a component that declares bays appears
// in another's `accepts` list, a third level exists and the pass that stops at
// two skips it silently: the 2D drawing swaps, the scene built from this text
// does not, and nothing reports anything. That is the same 2D/3D divergence
// twice already fixed one level at a time, and this is the shape that stops
// fixing it one level at a time.
//
// Returns `{applied, dropped}`: how many bays were seated, and the ids of any
// the override map named that the walk never reached. `dropped` is non-empty
// only when `maxDepth` cut the walk short.
//
// `seen` is what makes the walk terminate on its own: a bay is applied at its
// OWN level and never revisited, so each pass retires at least one level and the
// loop ends when a pass finds nothing left rather than when a counter runs out.
// (It used to say "at the level it first appears at", which was the bug the
// levelling below fixes - a bay can appear in a frontier several levels before
// it is its turn.) `maxDepth` is the belt - render.py bounds its own recursion
// at MAX_BAY_DEPTH = 3 for the same reason - so a drawing with a cycle in it
// cannot spin here.
export async function applyAllOverrides(rootEl, deviceBays, overrides, loadSkin,
                                        compByRef, maxDepth = 4) {
  let n = await applyOverrides(rootEl, deviceBays, overrides, loadSkin);
  const seen = new Set(deviceBays.map(b => b.id));
  // ONLY THE BOUNDED EXIT CAN DROP ANYTHING, and saying so is cheaper than
  // proving it again below. Leaving the loop because the frontier came back
  // empty IS the proof that nothing is left; re-deriving it afterwards walks
  // every bay in the drawing a second time to be told what the loop just
  // established. `applyBayOverrides` runs per view per config, so that is one
  // wasted walk per face on the path that always succeeds.
  let truncated = true;
  for (let depth = 0; depth < maxDepth; depth++) {
    const found = nestedBays(rootEl, compByRef).filter(b => !seen.has(b.id));
    // ONE LEVEL PER PASS, and this is not an optimisation. A COMPILED FACE
    // ALREADY CARRIES ITS NESTING - render.py seats every configured `default:`
    // at build time, and the dist holds 248 level-2 bay groups across 52 files
    // before any override is applied - so `nestedBays` does not hand back one
    // level at a time. It walks `[data-class="bay"]` and level-limits nothing,
    // which means a single frontier can hold a carrier AND something seated
    // inside it.
    // Applied together, the deeper one's `at`/`rotate` were read off the carrier
    // the shallower one is about to replace, and `seen` then guarantees they are
    // never re-derived: the occupant lands where the OLD carrier's bay was.
    // So a bay with an ancestor in the same frontier waits for the next pass,
    // by which time the carrier above it has settled and it resolves against
    // what is actually seated. The `+ '/'` is load-bearing - without it
    // `slot-1/module/ppm-10` reads as a descendant of `slot-1/module/ppm-1`.
    const frontier = found.filter(
      b => !found.some(o => o !== b && b.id.startsWith(o.id + '/')));
    if (!frontier.length) { truncated = false; break; }
    for (const b of frontier) seen.add(b.id);
    n += await applyOverrides(rootEl, frontier, overrides, loadSkin);
  }
  // WHAT WAS LOST, IF ANYTHING - because the two ways out of that loop mean
  // opposite things and used to be indistinguishable. Running out of frontier is
  // completion; running out of `maxDepth` is truncation, and an override the
  // caller asked for was never applied. 2D would show the swap and 3D would not,
  // which is the divergence this whole family of fixes has been about, and it
  // would have gone unreported.
  //
  // NAMED BY THE MAP, not merely unreached. The walk continues while a frontier
  // holds anything NEW, so `depth === maxDepth && frontier.length` is true of a
  // deep drawing nobody swapped anything in - it would announce that overrides
  // were dropped when none were. What was actually lost is the bays still
  // unprocessed THAT THE OVERRIDE MAP NAMES.
  //
  // Reported rather than logged. swap.js has no console calls and runs in two
  // places - the live page and a headless parse of a fetched face - so it says
  // what happened and lets the caller decide how to say it. viewer3d has the
  // `[portrayal] …` voice for that.
  //
  // IT NAMES WHAT IS VISIBLE, WHICH IS NOT NECESSARILY ALL THAT WAS LOST. A bay
  // that would only have appeared once a deeper carrier was seated cannot be in
  // the document to be counted, so a truncated walk can hide further work behind
  // the work it already skipped. `dropped` is therefore a floor: non-empty means
  // something was definitely lost, empty means nothing visible was.
  const dropped = truncated
    ? nestedBays(rootEl, compByRef)
        .filter(b => !seen.has(b.id)
                     && Object.prototype.hasOwnProperty.call(overrides, b.id))
        .map(b => b.id)
    : [];
  return {applied: n, dropped};
}

// WHICH VIEWS OF A CONFIG AN OVERRIDE MAP TOUCHES - the guard that used to
// live inline in viewer3d.js's `applyBayOverrides`, and was bay-only: it read
// `devIndex.bays` alone, so a cage-only override named no bay in any view,
// every view was skipped, and the swap never reached the fetched face text the
// 3D scene is built from - the same 2D/3D divergence this file's header
// describes for a bay swap, now for a cage.
//
// It lives HERE rather than in viewer3d.js because viewer3d.js imports
// `three`, which a plain node process cannot resolve (no import map support,
// no `three` devDependency) - so a pure decision viewer3d.js needs cannot be
// unit-tested from inside it without a browser. swap.js is already the seating
// home for both a bay swap and a cage swap, so it is the home for the question
// "which views did either kind touch" too.
//
// `devIndex` is the loaded `<device>.configs.json`; `devIndex.bays` and
// `devIndex.cages` are each keyed by view. A view is rewritten when:
//   - one of ITS BAYS is named in `overrides` - the original rule, untouched;
//   - one of ITS CAGES is named in `overrides` - the case this function adds;
//   - a key names a slot ON one of its cages - a bore of a duplex adapter
//     placed on the device, `xc01/tx` (B3): no `/module/` in it, and no cage
//     of that id, so it named no view and 3D never saw the swap;
//   - `overrides` names a nested (`/module/`) path AND the view has bays at
//     all. A nested path is never a device bay id (nestedBays only ever
//     produces one by walking what a device bay's OWN drawing seated - see
//     nestedBays above), so it is found only by walking from a bay, and a
//     view with no bays has nothing to walk, cages included.
//
// The view set is read off BOTH `devIndex.bays` and `devIndex.cages`, not
// gated on `devIndex.bays` existing at all - a device that declares cages and
// no bays anywhere (an optics-only faceplate) used to be skipped outright by
// the old `!devIndex?.bays` guard before this function's decision was ever
// consulted.
export function viewsToRewrite(devIndex, overrides) {
  const keys = Object.keys(overrides || {});
  if (!keys.length) return [];
  const nestedOverride = keys.some(k => k.includes('/module/'));
  const byBays = devIndex?.bays || {};
  const byCages = devIndex?.cages || {};
  const views = new Set([...Object.keys(byBays), ...Object.keys(byCages)]);
  const out = [];
  for (const view of views) {
    const bays = byBays[view] || [];
    const cages = byCages[view] || [];
    if (nestedOverride && bays.length) { out.push(view); continue; }
    if (bays.some(b => Object.prototype.hasOwnProperty.call(overrides, b.id))
        || cages.some(c => Object.prototype.hasOwnProperty.call(overrides, c.id)
                           || keys.some(k => k.startsWith(c.id + '/'))))
      out.push(view);
  }
  return out;
}

// ONE FACE, EVERY OVERRIDE: what viewer3d.js does to each fetched face text
// before the scene is cut from it, here so node can run it (viewer3d imports
// `three`). Bays first, every level (applyAllOverrides), and THEN the cages -
// the device's and those on the cards now seated (faceCages), read off the
// face after the bays settled, so a cage on a card this same map seats is the
// new card's and not the one that left. Handed only the device's cages, the
// pass seated no optic on any card: 2D showed the choice and 3D did not.
// Resolves to applyAllOverrides' `{applied, dropped}` plus
// applyOccupantOverrides' `refused` / `failed` (applied summed), and the
// `cages` it applied to, so a caller can say why one was refused.
export async function applyFaceOverrides(rootEl, {bays = [], cages = []}, overrides,
                                         loadSkin, compByRef) {
  const {applied, dropped} = await applyAllOverrides(rootEl, bays, overrides, loadSkin, compByRef);
  const all = faceCages(rootEl, cages, compByRef);
  const occ = await applyOccupantOverrides(rootEl, all, overrides, loadSkin);
  return {applied: applied + occ.applied, dropped, refused: occ.refused, failed: occ.failed,
          cages: all};
}

// A FACE THAT IS NOT ON SCREEN, GIVEN THE SWAPS. The explorer's merged tree
// (3D) lists every face, and all but the mounted one are parsed straight from
// the build, which knows only the configuration. The mounted face is seated
// by the shell's `reseat()`; these were not, so the tree listed a bay the
// reader had filled as "open" on every face but the one the 2D view last
// showed. This is the whole pass one detached face needs, applied as the 3D
// scene applies it: `applyFaceOverrides` for its bays and cages, then
// `applyRearOverrides` for the rear holes that show a swapped front bay's
// back - a face may hold those and no bay at all. Resolves to the face pass's
// result with `rear`, the holes re-seated, and `applied` counting both.
export async function seatFace(rootEl, {bays = [], cages = []}, overrides, loadSkin, compByRef) {
  const face = await applyFaceOverrides(rootEl, {bays, cages}, overrides, loadSkin, compByRef);
  const rear = await applyRearOverrides(rootEl, overrides, loadSkin, compByRef);
  return {...face, applied: face.applied + rear, rear};
}

// THE FACES HELD BUT NOT MOUNTED, KEPT SEATED - the shell's bookkeeping for
// them, here so node can run it. `seat(face, view, map, loadSkin)` is the
// per-face pass (the shell's is `seatFace`).
//
// ONE QUEUE, IN ORDER. `load` and `swap` are jobs on one chain, so a swap
// made while faces are loading is seated into them once they are held, and
// two swaps of one key reach every face in the order they were made. A job
// that fails does not stop the ones behind it.
//
// EACH FACE REMEMBERS WHAT IT WAS SEATED WITH, and a later job skips an entry
// the face already holds: faces loaded with the state's whole delta, then
// handed the swap that was queued while they loaded, would take every module
// out and seat it again - refetching its skin and dropping whatever the
// reader had pulled inside it. A face the queue never seated (the one that
// was mounted, now held) has no record and takes every entry.
//
// `live()` is the caller saying the faces it meant are still the held ones -
// the same device and configuration as when the job was ASKED for, not when
// it ran - and it is read again after every await. Both jobs resolve to what
// they changed (faces stored, entries applied), so a caller can skip a
// redraw that would show nothing new.
//
// A job's skins are loaded once: every face that holds a swapped module asks
// for the same skin, and a module shown front and back asks twice per face.
export function faceQueue({seat, loadSkin}) {
  let work = Promise.resolve();
  const run = job => {
    const r = work.then(job);
    work = r.catch(() => {});
    return r;
  };
  const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  const holds = new WeakMap();
  // A CARRIER RE-SEATED FORGETS WHAT WAS UNDER IT: the module that left
  // took its slots' occupants with it, so a face that held a plug in
  // `bay-1/module/lc01` does not hold one in the cassette that replaced it,
  // and the same swap asked again must be seated (pruneCarrier's rule).
  const note = (face, map) => {
    const h = holds.get(face) || {};
    for (const k of Object.keys(map))
      for (const held of Object.keys(h))
        if (underCarrier(held, k) && !own(map, held)) delete h[held];
    for (const [k, v] of Object.entries(map)) h[k] = v ?? null;
    holds.set(face, h);
  };
  const todo = (face, map) => {
    const h = holds.get(face);
    return Object.fromEntries(Object.entries(map)
      .filter(([k, v]) => !(h && own(h, k) && h[k] === (v ?? null))));
  };
  const skins = () => {
    const memo = new Map();
    return ref => {
      if (!memo.has(ref)) memo.set(ref, Promise.resolve(loadSkin(ref)));
      return memo.get(ref);
    };
  };
  return {
    // fetch every view not yet held, in parallel, and seat each with the
    // delta as it stands once its text has arrived
    load(views, {has, fetch, delta, store, live}) {
      return run(async () => {
        const skin = skins();
        const stored = await Promise.all(views.map(async view => {
          if (!live() || has(view)) return 0;
          const face = await fetch(view);
          if (!face || !live()) return 0;
          const map = delta();
          await seat(face, view, map, skin);
          if (!live() || !store(view, face)) return 0;
          note(face, map);
          return 1;
        }));
        return stored.reduce((a, b) => a + b, 0);
      });
    },
    // one swap into every held face that does not already hold it
    swap(map, {held, live}) {
      return run(async () => {
        const skin = skins();
        let applied = 0;
        for (const [view, face] of held()) {
          if (!live()) break;
          const entries = todo(face, map);
          if (!Object.keys(entries).length) continue;
          applied += (await seat(face, view, entries, skin))?.applied || 0;
          if (!live()) break;
          note(face, entries);
        }
        return applied;
      });
    },
  };
}

// THE SWAP STATE AS A URL PARAMETER, so a swap survives a reload. A runtime
// swap changes no file on disk - it lives in the explorer's memory - and a
// page that forgets it on reload shows the reader the build again with nothing
// to say that their choice was dropped.
//
//   swap=<key>~<ref>,<key>~<ref>,<key>~
//
// `~` separates key from ref, `,` separates entries, and an EMPTY ref is an
// emptied bay or cage - the own-key rule applyOverrides states: `slot-0~` is
// "the card was taken out", which is not the same as `slot-0` never appearing.
// Bay ids, nested bay paths (`slot-1/module/ppm-2`) and cage ids are all
// data-paths in one namespace, so one map carries all three.
//
// Each key and ref is encodeURIComponent-ed, and `~` is escaped as well:
// encodeURIComponent leaves `~` alone (it is unreserved), and a key that
// contained one would otherwise split in the wrong place. The result is made
// only of unreserved characters, `%XX`, `,` and `~`, so it can sit in a query
// string as it is - the caller must not run it through URLSearchParams, which
// would decode it once on the way back and turn an escaped `,` into a real one.
//
// Keys are sorted by the rule index.html's `swapKey` uses (code-unit order),
// so the same state always writes the same URL.
const enc = s => encodeURIComponent(s).replace(/~/g, '%7E');

export function encodeSwaps(map) {
  if (!map || typeof map !== 'object') return '';
  return Object.keys(map).sort((a, b) => a < b ? -1 : a > b ? 1 : 0)
    .map(k => `${enc(k)}~${map[k] ? enc(String(map[k])) : ''}`).join(',');
}

// NEVER THROWS, and one bad entry does not take the rest with it: a `swap=`
// value is typed, pasted and truncated by people, and the worst it may do is
// be ignored. Unknown shapes - no `~`, two of them, an empty key, a malformed
// escape, a non-string - are dropped entry by entry. `__proto__` is dropped
// too, because assigning it to a plain object sets the prototype instead of a
// key.
export function decodeSwaps(s) {
  const out = {};
  if (typeof s !== 'string' || !s) return out;
  for (const part of s.split(',')) {
    const i = part.indexOf('~');
    if (i <= 0 || part.indexOf('~', i + 1) >= 0) continue;
    let k, v;
    try {
      k = decodeURIComponent(part.slice(0, i));
      v = decodeURIComponent(part.slice(i + 1));
    } catch (e) { continue; }
    if (!k || k === '__proto__') continue;
    out[k] = v || null;
  }
  return out;
}

// ONE QUERY PARAMETER, UNDECODED. The counterpart of the warning above: the
// swap string carries its own escaping, so it is read raw.
export function rawParam(search, name) {
  for (const part of String(search || '').replace(/^\?/, '').split('&')) {
    const i = part.indexOf('=');
    if ((i < 0 ? part : part.slice(0, i)) === name) return i < 0 ? '' : part.slice(i + 1);
  }
  return null;
}

// A QUERY STRING WITH SOME PARAMETERS SET, every other one kept as it was
// written. `vals` maps a name to a RAW value (already encoded), or to
// null/'' to remove it. Other parameters - `tex`, which relief.js reads off
// the same location - survive untouched and in their own order.
export function searchWith(search, vals) {
  const kept = String(search || '').replace(/^\?/, '').split('&')
    .filter(p => p && !Object.prototype.hasOwnProperty.call(vals, p.split('=')[0]));
  const set = Object.entries(vals).filter(([, v]) => v != null && v !== '')
    .map(([k, v]) => `${k}=${v}`);
  const all = [...set, ...kept];
  return all.length ? `?${all.join('&')}` : '';
}

// WHICH ENTRIES OF A RELOADED SWAP MAP ARE REAL - the gate between a `swap=`
// somebody wrote (or edited, or pasted from another device) and the state the
// explorer keeps. Whatever passes is written back into the URL AND sent to the
// 3D scene, and applyOverrides above does not check accepts: an entry the 2D
// face would refuse, taken in anyway, is seated in 3D and not in 2D, and it
// lives in the URL for good. So an entry is taken ONLY when it names a bay or
// cage that exists AND its ref is one that bay or cage accepts; an empty ref
// is always allowed for one that exists. Everything else is `ignored`.
//
// A NESTED BAY EXISTS BY VIRTUE OF WHAT ITS CARRIER HOLDS, so it is resolved
// the way nestedBays resolves one off a drawing - the carrier's component and
// its published `bays` - but from the STATE rather than the DOM, because the
// carrier may be on a face that is not on screen. And it is resolved LEVEL BY
// LEVEL, shallowest first - the frontier rule applyAllOverrides follows -
// because what the carrier holds is this same map's decision when the map
// names the carrier: `slot-1~a22,slot-1/module/ppm-1~x` is only valid once
// `slot-1~a22` has been. A carrier entry that is itself refused leaves the
// built carrier in charge.
//
//   bays, cages   the device's own, every view (flattened)
//   built(path)   what the configuration puts at `path`: a ref, null for
//                 built empty, or UNDEFINED for "no answer" - then the resolved
//                 bay's own `default` is what the build seated there. Undefined
//                 and null are different on purpose: an emptied bay is not one
//                 that falls back to its default.
//   compByRef     ref -> components.json entry (may throw on a malformed ref)
//
// A CAGE ON A SEATED CARD (#484) is resolved by the same walk, because it
// exists for the same reason a nested bay does: `front-6/module/xg0` is a cage
// only while what `front-6` holds - this map's decision, else the build's -
// is a component whose own `cages` (components.json) name `xg0`. It is looked
// for after the card's bays, and it is a leaf: nothing is nested under an
// optic, so a key below a cage names nothing.
//
// Returns `{accepted, ignored, cages}`: `cages` is the accepted keys that are
// cages, device or card, so the caller files each where it belongs - a card
// cage's key looks like a nested bay's, and only this walk knows which it is.
export function acceptSwaps(map, {bays = [], cages = [], built = () => null,
                                  builtOcc = () => undefined, compByRef,
                                  placementRef = () => null}) {
  const accepted = {}, ignored = [], cageKeys = [];
  const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  // what a bay holds given what is decided so far: this map's answer, else
  // the build's (`built`), else - undefined, "no answer" - its own default
  const R = slotResolver({bays, cages, compByRef, placementRef,
    bayRef: (path, bay) => {
      if (own(accepted, path)) return accepted[path];
      const was = built(path);
      return was !== undefined ? was : bay.default ?? null;
    }});
  const depth = k => k.split('/module/').length;
  const keys = Object.keys(map && typeof map === 'object' ? map : {})
    .sort((a, b) => depth(a) - depth(b) || (a < b ? -1 : 1));
  const isCage = new Set();
  for (const key of keys) {
    const ref = map[key] || null;
    const target = R.entryAt(key);
    if (!target || (ref && !(target.accepts || []).includes(ref))) { ignored.push(key); continue; }
    accepted[key] = ref;
    if (target.isCage) isCage.add(key);
  }
  // THE EXCLUSION (L111), on the state this map leaves: a fill on one level
  // of a duplex adapter is not taken while the other level holds something -
  // this map's answer, else the configuration's (`builtOcc`), else what the
  // slot ships (`default`), or a fresh seat's when this map re-seated the
  // carrier. Judged against the map as accepted, before any is dropped, so
  // two fills that collide are both refused rather than the first winning.
  const reseated = id => Object.keys(accepted).some(k => !isCage.has(k) && underCarrier(id, k));
  const holds = id => {
    if (own(accepted, id)) return accepted[id];
    const was = reseated(id) ? undefined : builtOcc(id);
    return was !== undefined ? was : R.entryAt(id)?.default ?? null;
  };
  const clash = [];
  for (const key of Object.keys(accepted)) {
    if (!accepted[key] || !isCage.has(key)) continue;
    const e = R.entryAt(key);
    const cut = key.lastIndexOf('/');
    const up = cut > 0 ? R.entryAt(key.slice(0, cut)) : null;
    const bore = !!up?.isCage && (up.bores || []).includes(key.slice(cut + 1));
    if ((e.bores || []).some(b => holds(`${key}/${b}`)) || (bore && holds(key.slice(0, cut))))
      clash.push(key);
  }
  for (const key of clash) { delete accepted[key]; isCage.delete(key); ignored.push(key); }
  return {accepted, ignored, cages: keys.filter(k => isCage.has(k))};
}

// WHAT IS AT A PATH, WITHOUT A DRAWING - the one reading of "which bay or
// slot does this key name" for everything that has no face to look at: the
// reload's gate (acceptSwaps), the delta (swapOverrides), a configuration's
// keys (builtOccupants) and a fresh seat's defaults (pruneCarrier's
// caller). nestedSlots is the same answer read off a drawing, and the two are
// held to each other on real faces (test_nested_slots_js.py).
//
//   bays, cages     the device's own, every view, flattened
//   bayRef(p, bay)  the ref the bay at `p` holds, as the caller decides it
//   compByRef       ref -> components.json entry (may throw)
//   placementRef(p) the ref of the DEVICE placement at `p` - the one fact no
//                   index publishes (configs.json's cages carry no ref), so a
//                   caller reads it off a face; null when it cannot
//
// `entryAt(path)` walks it the way the drawing nests: a device bay or slot;
// a nested bay (`<carrier>/module/<id>` in the carrier's `bays`); a slot on
// whatever instance the parent path names - the module in a bay, a part a
// component composes (components.json `parts`), a device placement. The
// slot-on-a-slot rule is nestedSlots': only a bore of it. Slots come back
// `isCage` with their `key`; bays as they are. `refAt(path)` is the
// component drawn at a path: a bay's module, a part, a placement.
export function slotResolver({bays = [], cages = [], bayRef = (p, b) => b.default ?? null,
                              compByRef, placementRef = () => null}) {
  const comp = ref => {
    if (!ref || !compByRef) return null;
    try { return compByRef(String(ref).split(':')[0]) || null; } catch (e) { return null; }
  };
  const place = p => { try { return placementRef ? placementRef(p) || null : null; } catch (e) { return null; } };
  function refAt(path) {
    if (path.endsWith('/module')) {
      const bayPath = path.slice(0, -'/module'.length);
      const bay = entryAt(bayPath);
      return bay && !bay.isCage ? bayRef(bayPath, bay) || null : null;
    }
    const cut = path.lastIndexOf('/');
    if (cut < 0) return place(path);
    const name = path.slice(cut + 1);
    return (comp(refAt(path.slice(0, cut)))?.parts || []).find(q => q.id === name)?.ref || null;
  }
  function entryAt(path) {
    if (!path || typeof path !== 'string') return null;
    const bay = bays.find(b => b.id === path);
    if (bay) return bay;
    const cage = cages.find(c => c.id === path);
    if (cage) return {...cage, key: slotKey(path), isCage: true};
    const cut = path.lastIndexOf('/');
    if (cut <= 0) return null;
    const parent = path.slice(0, cut), name = path.slice(cut + 1);
    if (name === 'module') return null;
    const c = comp(refAt(parent));
    if (!c) return null;
    const b = parent.endsWith('/module') ? c.bays?.[name] : null;
    if (b) return {...b, id: path};
    const slot = (Array.isArray(c.cages) ? c.cages : []).find(g => g.id === name);
    if (!slot) return backEntry(path, parent, name, c);
    const host = parent.endsWith('/module') ? null : entryAt(parent);
    if (host?.isCage && !(host.bores || []).includes(name)) return null;
    return {...slot, id: path, key: slotKey(path), isCage: true};
  }
  // A SLOT ON A MODULE'S BACK (B3 Task 10b): one step under the module in a
  // DEVICE bay, a slot of the module's `faces.rear` component that no front
  // part or bay of the module shares an id with - manifest.nested_key_host's
  // reading. The build also asks that the bay shows its back somewhere
  // (`rear:`), which configs.json does not publish; every bay in the library
  // that takes a module with a back does (test_nested_slots_js.py pins it).
  function backEntry(path, parent, name, c) {
    if (!parent.endsWith('/module') || !bays.some(b => `${b.id}/module` === parent)) return null;
    if ((c.parts || []).some(q => q.id === name) || c.bays?.[name]) return null;
    const slot = (comp(faceRef(c.faces?.rear))?.cages || []).find(g => g.id === name);
    return slot ? {...slot, id: path, key: slotKey(path), isCage: true, back: true} : null;
  }
  return {entryAt, refAt};
}

// WHAT A CONFIGURATION SEATS IN EACH CAGE, as {cage id: ref | null} - the ONE
// reading of `configs[].occupants` everything in the kit uses (shell.js's
// state and inspector, index.html's "is this a swap" test). The schema lets a
// value be a ref string OR a mapping `{ref, id, attrs, skin}`
// (spec/schemas/device.schema.json, render.py's expansion reads both), and it
// lets a key name an OCCUPANT rather than a cage - the chained form,
// `{port-4: plug, port-4-occupant: boot}`, seats a boot on the plug. Reading
// the map raw handed the inspector an object to compare with its option
// strings (a seated optic shown as "empty", and swapping back to it a
// permanent "swap"), and handed the swap test a boot on a key that is no
// cage - so an UNTOUCHED page wrote `swap=port-4-occupant~...` on load and
// warned about it on every reload.
//
// So: a value is reduced to its ref, and a key is kept only when it is a cage
// of this device (`cages`, every view, flattened) and not an occupant another
// entry seats (its `id`, or the build's default `<host>-occupant`). A chained
// tier is the build's business; the kit swaps cages.
//
// A KEY ON A SEATED CARD (#484) is the manifest's module-less path,
// `front-6/xg0`, and is returned at the DRAWING's, `front-6/module/xg0` -
// configBayPath, the translation builtBays makes for a nested bay key - so the
// state, the swap test and the 3D map all meet the path nestedCages reads off
// the face. Read raw it matched no cage, the state held nothing for a cage the
// build had filled, and the inspector showed that optic as empty (#440's
// lesson, one level down). It is not checked against `cages`, which are the
// device's own: the build refuses a nested key that names no host
// (render.py's _seat_nested_occupants), so a shipped configuration's nested
// keys are real. Its chained tiers are dropped by the same rule, inside the
// card's namespace - `front-6/xg0-occupant`, or `front-6/<id>`.
//
// A SLOT AT ANY DEPTH (B3, P1) is keyed the same way, part ids after the
// bays - `bay-1/lc1/tx` - and the drawing puts `module` only after a BAY:
// `bay-1/module/lc1/tx`, not configBayPath's `bay-1/module/lc1/module/tx`.
// Which steps are bays is the configuration's population's answer, so with
// `ctx` ({bays: the device's own, flattened; compByRef}) each key is walked
// through slotResolver, the bays at what this configuration seats in them.
// Without it a nested key is read by configBayPath, as it always was - right
// for the one level #484 keyed.
export function builtOccupants(cfg, cages, ctx = null) {
  const occ = cfg?.occupants;
  const out = {};
  if (!occ || typeof occ !== 'object') return out;
  const toPath = ctx ? keyPath(cfg, cages, ctx) : configBayPath;
  const cageIds = new Set((cages || []).map(c => c.id));
  const refOf = v => typeof v === 'string' ? v : (v && typeof v === 'object' ? v.ref : null);
  const occIds = new Set(Object.entries(occ).map(([k, v]) => {
    const cut = k.lastIndexOf('/');
    const local = (v && typeof v === 'object' && v.id) || `${k.slice(cut + 1)}-occupant`;
    return cut < 0 ? local : `${k.slice(0, cut)}/${local}`;
  }));
  for (const [k, v] of Object.entries(occ)) {
    const nested = k.includes('/');
    if (!(nested || cageIds.has(k)) || occIds.has(k)) continue;
    out[nested ? toPath(k) : k] = refOf(v) || null;
  }
  return out;
}

// A configuration's module-less key at the drawing's path: `module` after
// each step that is a bay, found by slotResolver with the bays at what `cfg`
// seats in them (builtBays, else each bay's default).
function keyPath(cfg, cages, {bays = [], compByRef, placementRef} = {}) {
  const cb = builtBays(cfg);
  const R = slotResolver({bays, cages, compByRef, placementRef,
    bayRef: (p, bay) => Object.prototype.hasOwnProperty.call(cb, p) ? cb[p] : bay.default ?? null});
  return key => {
    const segs = String(key).split('/');
    let path = segs[0];
    for (const seg of segs.slice(1)) {
      const at = R.entryAt(path);
      path = `${path}${at && !at.isCage ? '/module' : ''}/${seg}`;   // a bay holds a module
    }
    return path;
  };
}

// WHICH ENTRIES OF THE EXPLORER'S STATE ARE SWAPS - what differs from what the
// build seated. That map is what goes into `swap=` and to the 3D scene, so an
// entry here that the user never made is a URL written on an untouched page.
//   cfg            the configuration (`configs[]` entry) on screen
//   bays, cages    the device's own, every view, flattened
//   cfgBays        bay id / nested path -> ref|null, the state's
//   cfgOccupants   cage id -> ref|null, the state's (builtOccupants-shaped)
// A bay's built answer is the configuration's `bays` entry (read through
// builtBays, so a nested key meets the drawing's path) when it has one,
// else the bay's own `default`; a cage's is builtOccupants' - a cage the
// configuration does not name is built empty.
//
// A CAGE ON A CARD THE STATE HAS SWAPPED was never populated by the build: the
// card in that bay is a fresh seat of its component, whose cages hold nothing.
// So its built answer is empty, whatever the configuration put in the old
// card's cage of the same id - read the other way, the configured optic chosen
// on the new card was "no swap", 3D was handed the card alone and showed the
// cage empty. The bays are therefore decided first, and a cage key under a bay
// that differs is measured against nothing.
//
// A NESTED BAY FOLLOWS THE SAME RULE. Under a carrier the state has swapped,
// the bay's built answer is what a fresh seat of the NEW carrier holds there -
// its component's `default` - never the configuration's entry for the old
// carrier's bay of the same id: read that way, choosing the module the build
// had put there was "no swap", `swap=` recorded only the carrier and 3D showed
// the new carrier's default. On the build's own carrier a bay the
// configuration does not name is built at its component's default too. Both
// need `compByRef` (the component index); without it a nested bay's default
// reads as empty, which still gets the swapped-carrier case right for any
// module that is chosen.
//
// Bays are decided SHALLOWEST FIRST, whatever order the state map holds them
// in, so a carrier is in `out` before anything under it asks.
//
// A SLOT THAT SHIPS SOMETHING (B3, P5) is built holding its `default` when
// the configuration does not key it, and a fresh seat of its carrier holds
// that default too. So an occupant key's built answer is the configuration's
// entry (on the build's own carrier), else the slot's `default` - read by
// slotResolver with the bays at what the STATE seats, so a slot on a swapped
// cassette is measured against that cassette's cap. Emptying a shipped cap
// is then a swap (`lc1~`) and putting it back is none. `placementRef` is
// slotResolver's: a slot on a device placement (`xc01/tx`) needs the
// placement's ref to find what it ships.
export function swapOverrides({cfg, bays = [], cages = [], cfgBays = {}, cfgOccupants = {},
                              compByRef = null, placementRef = () => null}) {
  const own = (o, k) => Object.prototype.hasOwnProperty.call(o || {}, k);
  const cageIds = new Set(cages.map(c => c.id));
  const occ = builtOccupants(cfg, cages, compByRef ? {bays, compByRef, placementRef} : null);
  const cb = builtBays(cfg);
  const R = slotResolver({bays, cages, compByRef, placementRef,
    bayRef: (p, bay) => own(cfgBays, p) ? cfgBays[p] : own(cb, p) ? cb[p] : bay.default ?? null});
  const out = {};
  const swappedAbove = id => Object.keys(out).some(k => id.startsWith(k + '/module/'));
  const defaultIn = (carrierRef, id) => nestedDefault(compByRef, carrierRef, id);
  const shipped = id => R.entryAt(id)?.default ?? null;
  const builtOcc = id => (!swappedAbove(id) && own(occ, id)) ? occ[id] ?? null : shipped(id);
  const built = id => {
    if (cageIds.has(id) || own(occ, id)) return builtOcc(id);
    const carrier = carrierOf(id);
    if (carrier != null && swappedAbove(id))
      return defaultIn(own(cfgBays, carrier) ? cfgBays[carrier] : built(carrier), id);
    if (own(cb, id)) return cb[id] || null;
    if (carrier != null) return defaultIn(built(carrier), id);
    return bays.find(b => b.id === id)?.default || null;
  };
  const depth = id => id.split('/module/').length;
  const bayEntries = Object.entries(cfgBays || {}).sort(([a], [b]) => depth(a) - depth(b));
  for (const [id, ref] of bayEntries)
    if ((ref || null) !== built(id)) out[id] = ref || null;
  // an occupant key is measured as a slot, whatever its path looks like - a
  // card's cage and a nested bay share a shape, and the state knows which
  for (const [id, ref] of Object.entries(cfgOccupants || {}))
    if ((ref || null) !== builtOcc(id)) out[id] = ref || null;
  return out;
}

// The bay path a nested key sits in - `slot-1` for `slot-1/module/ppm-1` - or
// null for a device's own bay.
function carrierOf(id) {
  const cut = String(id).lastIndexOf('/module/');
  return cut < 0 ? null : String(id).slice(0, cut);
}

// The bay at `id` in a fresh seat of `carrierRef`: the component's own
// declaration (components.json `bays`), or null when there is no index, no
// such component (compByRef throws on a ref that is not ns/name@major) or no
// such bay.
function nestedBay(compByRef, carrierRef, id) {
  if (!compByRef || !carrierRef) return null;
  let comp = null;
  try { comp = compByRef(carrierRef); } catch (e) { comp = null; }
  return comp?.bays?.[String(id).slice(carrierOf(id).length + '/module/'.length)] || null;
}
const nestedDefault = (compByRef, carrierRef, id) =>
  nestedBay(compByRef, carrierRef, id)?.default || null;

// WHAT A FRESH SEAT OF `ref` IN `carrier` HOLDS IN THE CONFIGURATION'S NESTED
// BAYS under it - `pruneCarrier`'s `freshBays` when the ref going back in is
// the build's own. Keyed by the drawing's path (builtBays), each at the
// component's default, level by level: a bay two deep is read off whatever
// the fresh seat holds in the bay above it, and is left out when that holds
// nothing or has no such bay. Only the configuration's keys: a bay it does
// not name was built at its default already, so a fresh seat changes nothing.
export function freshBaysUnder(cfg, carrier, ref, compByRef) {
  const refAt = path => path === carrier ? ref
    : nestedDefault(compByRef, refAt(carrierOf(path)), path);
  const out = {};
  for (const k of Object.keys(builtBays(cfg)).filter(k => underCarrier(k, carrier))) {
    const bay = nestedBay(compByRef, refAt(carrierOf(k)), k);
    if (bay) out[k] = bay.default || null;
  }
  return out;
}

// AN OPTIC CANNOT OUTLIVE THE CARD IT SAT IN (#484 R5). Replacing or emptying
// what the bay `carrier` holds drops every entry keyed under it -
// `front-6/module/...`, card cages and nested bays alike - from the explorer's
// state slice: `cfgBays`, `cfgOccupants`, `touched`, and the `refused` /
// `failed` notes. Everything else reads that state (swapOverrides for `swap=`
// and the 3D override map, the inspector's select), so this is the one place
// the drop happens. The carrier's own key is the caller's to write.
//
// `builtUnder` is for the one case a drop is not enough: the card put back is
// the BUILD's own card. It is a fresh seat of the component, so it holds none
// of the optics the configuration put in it - but with the carrier back to
// its built ref no swap names the card, and 3D, handed nothing, would show the
// build's optics. So each entry of `builtUnder` (builtOccupants' reading of
// this configuration) under `carrier` that is not empty is recorded as
// emptied, which is what the face shows. The caller passes it only then.
// `freshBays` is the same case for the configuration's NESTED BAYS under the
// carrier (freshBaysUnder): a fresh seat holds each at its component's
// default, not at the module the build put there, so each is recorded at
// that default - or 3D, handed nothing, would keep the build's module while
// 2D shows the default.
//
// PURE: returns a new slice; the one it is handed is not changed.
// Is `key` under the bay `carrier` - `front-6/module/...` - the one reading
// pruneCarrier and seatClaims' retireUnder share.
export function underCarrier(key, carrier) {
  return String(key).startsWith(`${carrier}/module/`);
}

//
// `fresh(k)` is what a fresh seat holds at the slot `k` - its shipped
// `default` (B3, P5), which the caller reads (slotResolver). A slot the
// configuration keyed is recorded at that whenever the two differ: a plug the
// configuration seated where the cassette ships a cap is the cap again, and a
// cap it emptied is back. The default, `() => null`, is #484's rule - a card's
// cage ships nothing, so every non-empty entry is recorded emptied.
export function pruneCarrier(slice, carrier, builtUnder = {}, freshBays = {}, fresh = () => null) {
  const under = k => underCarrier(k, carrier);
  const keep = o => Object.fromEntries(Object.entries(o || {}).filter(([k]) => !under(k)));
  const out = {cfgBays: keep(slice?.cfgBays), cfgOccupants: keep(slice?.cfgOccupants),
               touched: new Set([...(slice?.touched || [])].filter(k => !under(k))),
               refused: keep(slice?.refused), failed: keep(slice?.failed)};
  for (const [k, ref] of Object.entries(builtUnder || {})) {
    if (!under(k)) continue;
    const now = fresh(k) ?? null;
    if ((ref || null) !== now) { out.cfgOccupants[k] = now; out.touched.add(k); }
  }
  for (const [k, ref] of Object.entries(freshBays || {}))
    if (under(k)) { out.cfgBays[k] = ref || null; out.touched.add(k); }
  return out;
}

// DOES `el` LIE OVER THE PART AT `path`? - the cover half of shell.js's
// `over()`, which decides what `reveal()` takes off when a part is selected.
// A cover declares what it hides with `data-for`: the bezel names its drives,
// the C40G's filter cover names all four PSU bays. But `data-for` is also how
// a SEATED OPTIC names its cage, and the two are opposite relations. An
// occupant sits IN what it is for; a cover sits OVER it. `mounts` and `fills`
// are the behaviours of a part that goes on or in front of an opening - the
// same reading the tree's pull control gives them - and `occupies` is the
// behaviour of what the opening holds. Read as a cover, the optic was pulled
// every time its port was selected, and a cage swap ends by selecting the port:
// the optic just chosen vanished and the "removed" chip counted it.
export function liesOver(el, path) {
  if (!el || !path) return false;
  const behaviour = el.getAttribute('data-behaviour');
  if (!behaviour || behaviour === 'occupies') return false;
  const cp = el.getAttribute('data-path');
  return !!cp && cp !== path
    && (el.getAttribute('data-for') || '').split(/\s+/).includes(path);
}

// WHAT A FACE LISTS, AND WHAT A CLICK ON IT NAMES. The tree is built from the
// drawing: every `data-path` is a row. A projection (render.py's `plan:` and
// `rear:`, applyRearOverrides above) carries `data-of` in its place, naming
// the seated part's path, so a part seen from two faces is still one part.
// That is right for the part itself, which the face holding it lists. It is
// wrong for what only the projection draws: a cassette's back is its MTP
// bulkheads, `bay-1/module/mtp1`, and no face draws those with a data-path -
// so they were on no row anywhere, and a click on one selected the rear cutout
// it is seen through. So a face lists every projected path it does not also
// draw as a part, and a click names the nearest part OR projected part.
export function faceEntries(root) {
  const drawn = new Set([...root.querySelectorAll('[data-path]')]
    .map(e => e.getAttribute('data-path')));
  const out = [];
  for (const e of root.querySelectorAll('[data-path],[data-of]')) {
    const dp = e.getAttribute('data-path');
    if (dp != null) out.push({path: dp, el: e});
    else if (!drawn.has(e.getAttribute('data-of')))
      out.push({path: e.getAttribute('data-of'), el: e, projected: true});
  }
  return out;
}
export function ownerPath(el) {
  for (let n = el; n && typeof n.getAttribute === 'function'; n = n.parentNode) {
    const p = n.getAttribute('data-path') ?? n.getAttribute('data-of');
    if (p != null) return p;
  }
  return null;
}

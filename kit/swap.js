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

// SEATING AN OPTIC IN A CAGE is the other half of this module, and it is NOT
// seatModule with a different argument.
//
// PLACED BY MATE POINTS, NOT BY A BAY BOX. A bay is an opening with a size, and
// bayTransform centres the card in it. A cage has no box to centre anything in:
// the bay transform is the wrong tool for a part that is larger than its opening
// on purpose - a QSFP is 52 mm deep behind an 18 mm aperture, and its drawn face
// is not the cage's. What the build does instead (render.py `seat_point` /
// `seat_at`) is land the optic's own `mate` connection point on the cage's,
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

// A LIFTED CAGE IS REFUSED, NOT HALF-SEATED. For a cage whose aperture stands
// off the face by L, the build does two things to the optic it seats: it writes
// `data-z-lift=L` on the occupant group, AND it rewrites every child's
// `data-z-out` to `out + L` (render.py's `_inset_feature`, called with
// z_inset=-L) - because `out` is absolute and `lift` is summed. Copying the
// first without the second puts every `out` face of the optic L mm short in 3D.
// Nothing in the library has a lifted cage today (every published cage has
// lift 0), so a shift formula here would be arithmetic copied from the build
// with no real build to hold it to. Until one exists, the kit does not seat an
// optic into a lifted cage at all, and says so.
//
// TWO MORE CAGES ARE REFUSED ON THE SAME PRECEDENT, and for the same reason:
// the build does something to the optic the kit does not, and no cage in the
// library exists to hold an implementation to.
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
  if (+cage.lift) return 'lift';
  if (cage.mirror) return 'mirror';
  if (cage['group-states']) return 'group-states';
  return null;
}

// EVERY ATTRIBUTE THE OCCUPANT <g> CARRIES except its transform, as a plain
// {name: value} map so it can be checked without a DOM. Three sources, in the
// order the build layers them:
//   the skin root's data-*        - what the optic says about itself (copied as
//                                   seatModule copies them: data-path excluded);
//   cage['occupant-attrs']        - render.py's `group_side_attrs` for the host,
//                                   published per cage: a `media: qsfp-dd` group
//                                   over the contract's `media: fiber`;
//   identity                      - id, data-path, data-ref, data-for.
// No data-z-lift: a lifted cage never gets this far (see refusalReason).
// Nothing else. If the build ever writes an attribute none of these can supply,
// the parity test fails rather than this growing a special case.
export function occupantAttrs(cage, ref, comp, skinRootAttrs = {}, occId = `${cage.id}-occupant`) {
  const out = {};
  for (const [k, v] of Object.entries(skinRootAttrs || {}))
    if (k.startsWith('data-') && k !== 'data-path') out[k] = v;
  Object.assign(out, cage['occupant-attrs'] || {});
  out['id'] = occId;
  out['data-path'] = occId;
  out['data-ref'] = `${ref}:${comp.version}`;
  out['data-for'] = cage.id;
  return out;
}

// The <g> that represents `ref` seated in `cage`, built from the component's
// compiled standalone skin - the occupant's counterpart of seatModule.
// Returns null for a refused cage rather than a half-seated optic
// (refusalReason: lifted, mirrored, or in a group that carries states).
export function seatOccupant(ownerDoc, cage, ref, comp, skinText, occId = `${cage.id}-occupant`) {
  if (refusalReason(cage)) return null;
  const doc = new DOMParser().parseFromString(skinText, 'image/svg+xml');
  const root = doc.getElementById(comp.name);
  const rootAttrs = {};
  if (root) for (const a of [...root.attributes]) rootAttrs[a.name] = a.value;
  const wrap = ownerDoc.createElementNS(NS, 'g');
  for (const [k, v] of Object.entries(occupantAttrs(cage, ref, comp, rootAttrs, occId)))
    wrap.setAttribute(k, v);
  wrap.setAttribute('transform', occupantTransform(cage, comp));
  for (const n of [...doc.documentElement.childNodes])
    (n === root ? [...n.childNodes] : [n]).forEach(k => wrap.appendChild(ownerDoc.importNode(k, true)));
  rename(wrap, comp.name, occId, occId, '');
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
export function seatClaims() {
  const newest = new Map();
  return key => {
    const mine = (newest.get(key) || 0) + 1;
    newest.set(key, mine);
    return () => newest.get(key) === mine;
  };
}

// Apply an occupant override map - cage id -> ref, or -> null/'' for an emptied
// cage - to one compiled face. `cages` is the published `cages[view]` list and
// `loadSkin(ref)` returns {comp, text} or null (it may return a promise).
//
// The OWN-KEY rule is applyOverrides': `{port-4: null}` means the optic was
// pulled and must remove the built one, where an absent key means nobody
// touched that cage.
//
// WHAT IS REMOVED is the element that is `data-for` the cage AND
// `data-behaviour="occupies"` - the build's occupant or a previous swap's. An
// LED and a port's silkscreen label are `data-for` the port too, and matching
// on `data-for` alone would take the lamp out with the optic.
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
    const host = bayGroup(rootEl, cage.id);
    if (!host) continue;
    const ref = overrides[cage.id];
    const refuse = !!ref && !!refusalReason(cage);
    const loaded = ref && !refuse ? await loadSkin(ref) : null;
    if (!isCurrent(cage.id)) continue;        // a newer swap owns this cage
    if (ref && !refuse && !loaded) { failed.push(cage.id); continue; }
    const sel = `[data-for="${CSS.escape(cage.id)}"][data-behaviour="occupies"]`;
    for (const old of [...rootEl.querySelectorAll(sel)]) old.remove();
    applied++;
    if (refuse) { refused.push(cage.id); continue; }
    if (!ref) continue;                       // deliberately empty
    host.after(seatOccupant(rootEl.ownerDocument, cage, ref, loaded.comp, loaded.text));
  }
  return {applied, refused, failed};
}

// WHAT A CAGE HOLDS ON THIS FACE, as a ref without its version - what a
// caller records when a swap `failed` and the cage kept its old optic, so its
// state says what the drawing shows. null for an empty cage.
export function occupantRef(rootEl, cageId) {
  const el = rootEl.querySelector(
    `[data-for="${CSS.escape(cageId)}"][data-behaviour="occupies"]`);
  const ref = el?.getAttribute('data-ref') || '';
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
        || cages.some(c => Object.prototype.hasOwnProperty.call(overrides, c.id)))
      out.push(view);
  }
  return out;
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
export function acceptSwaps(map, {bays = [], cages = [], built = () => null, compByRef}) {
  const accepted = {}, ignored = [];
  const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  const comp = ref => { try { return ref ? compByRef(String(ref).split(':')[0]) : null; } catch (e) { return null; } };
  const memo = new Map();
  // the bay at `path` given what is decided so far, or null
  function bayAt(path) {
    if (memo.has(path)) return memo.get(path);
    let bay = bays.find(b => b.id === path) || null;
    const cut = path.lastIndexOf('/module/');
    if (!bay && cut > 0) {
      const carrier = path.slice(0, cut);
      const name = path.slice(cut + '/module/'.length);
      const holder = bayAt(carrier);
      if (holder && name) {
        const was = built(carrier);
        const ref = own(accepted, carrier) ? accepted[carrier]
                  : was !== undefined ? was
                  : holder.default ?? null;
        const b = comp(ref)?.bays?.[name];
        if (b) bay = {...b, id: path};
      }
    }
    memo.set(path, bay);
    return bay;
  }
  const depth = k => k.split('/module/').length;
  const keys = Object.keys(map && typeof map === 'object' ? map : {})
    .sort((a, b) => depth(a) - depth(b) || (a < b ? -1 : 1));
  for (const key of keys) {
    const ref = map[key] || null;
    const target = cages.find(c => c.id === key) || bayAt(key);
    if (!target || (ref && !(target.accepts || []).includes(ref))) { ignored.push(key); continue; }
    accepted[key] = ref;
    // a decided carrier changes what is nested under it: forget what was
    // resolved beneath it before this decision
    for (const k of [...memo.keys()]) if (k.startsWith(key + '/')) memo.delete(k);
  }
  return {accepted, ignored};
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
export function builtOccupants(cfg, cages) {
  const occ = cfg?.occupants;
  const out = {};
  if (!occ || typeof occ !== 'object') return out;
  const cageIds = new Set((cages || []).map(c => c.id));
  const refOf = v => typeof v === 'string' ? v : (v && typeof v === 'object' ? v.ref : null);
  const occIds = new Set(Object.entries(occ).map(
    ([k, v]) => (v && typeof v === 'object' && v.id) || `${k}-occupant`));
  for (const [k, v] of Object.entries(occ)) {
    if (!cageIds.has(k) || occIds.has(k)) continue;
    out[k] = refOf(v) || null;
  }
  return out;
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
export function swapOverrides({cfg, bays = [], cages = [], cfgBays = {}, cfgOccupants = {}}) {
  const own = (o, k) => Object.prototype.hasOwnProperty.call(o || {}, k);
  const cageIds = new Set(cages.map(c => c.id));
  const occ = builtOccupants(cfg, cages);
  const cb = builtBays(cfg);
  const built = id => {
    if (cageIds.has(id)) return occ[id] ?? null;
    if (own(cb, id)) return cb[id] || null;
    return bays.find(b => b.id === id)?.default || null;
  };
  const out = {};
  for (const map of [cfgBays, cfgOccupants])
    for (const [id, ref] of Object.entries(map || {}))
      if ((ref || null) !== built(id)) out[id] = ref || null;
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

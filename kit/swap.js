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
export function rename(wrap, name, idBase, pathBase = idBase) {
  const renamed = new Map();
  for (const el of wrap.querySelectorAll('[id],[data-path]')) {
    const id = el.getAttribute('id');
    if (id === name) el.removeAttribute('id');
    else if (id && id.startsWith(name + '--')) {
      const to = `${idBase}--module--${id.slice(name.length + 2)}`;
      renamed.set(id, to);
      el.setAttribute('id', to);
    }
    const dp = el.getAttribute('data-path');
    if (dp === name) el.setAttribute('data-path', `${pathBase}/module`);
    else if (dp && dp.startsWith(name + '/'))
      el.setAttribute('data-path', `${pathBase}/module/${dp.slice(name.length + 1)}`);
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
export async function applyOverrides(rootEl, bays, overrides, loadSkin) {
  let applied = 0;
  for (const bay of bays) {
    if (!Object.prototype.hasOwnProperty.call(overrides, bay.id)) continue;
    const g = bayGroup(rootEl, bay.id);
    if (!g) continue;
    const idBase = g.getAttribute('id') || bay.id;
    g.querySelector(`[id="${CSS.escape(idBase)}--module"]`)?.remove();
    applied++;
    const ref = overrides[bay.id];
    if (!ref) continue;                       // deliberately empty
    const loaded = await loadSkin(ref);
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

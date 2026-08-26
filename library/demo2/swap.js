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
export function rename(wrap, name, bayId) {
  for (const el of wrap.querySelectorAll('[id],[data-path]')) {
    const id = el.getAttribute('id');
    if (id === name) el.removeAttribute('id');
    else if (id && id.startsWith(name + '--'))
      el.setAttribute('id', `${bayId}--module--${id.slice(name.length + 2)}`);
    const dp = el.getAttribute('data-path');
    if (dp === name) el.setAttribute('data-path', `${bayId}/module`);
    else if (dp && dp.startsWith(name + '/'))
      el.setAttribute('data-path', `${bayId}/module/${dp.slice(name.length + 1)}`);
  }
}

// The <g> that represents `ref` seated in `bay`, built from the component's
// compiled standalone skin. `ownerDoc` is whichever document will hold it - the
// live page for shell.js, a parsed face for viewer3d.js.
export function seatModule(ownerDoc, bayId, bay, ref, comp, skinText) {
  const doc = new DOMParser().parseFromString(skinText, 'image/svg+xml');
  const wrap = ownerDoc.createElementNS(NS, 'g');
  wrap.setAttribute('id', `${bayId}--module`);
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
  rename(wrap, comp.name, bayId);
  return wrap;
}

// The path of a bay's opening in a compiled drawing. render.py gives the bay rect
// `data-path="<bayId>"` and seats the occupant inside it, which is what makes one
// selector work on the live DOM and on a fetched face alike.
function bayGroup(rootEl, bayId) {
  return rootEl.querySelector(`[data-path="${CSS.escape(bayId)}"]`);
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
    g.querySelector(`[id="${CSS.escape(bay.id)}--module"]`)?.remove();
    applied++;
    const ref = overrides[bay.id];
    if (!ref) continue;                       // deliberately empty
    const loaded = await loadSkin(ref);
    if (!loaded) continue;                    // unknown ref: leave the bay open
    g.appendChild(seatModule(rootEl.ownerDocument, bay.id, bay, ref,
                             loaded.comp, loaded.text));
  }
  return applied;
}

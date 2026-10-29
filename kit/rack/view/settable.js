// WHAT A RACK ENTRY IS SET TO AND WHAT ITS DISPLAYS SHOW, as the page draws it
// (kit 0.45.0 settable lamps and digits, 0.47.0 displays). An item and a part
// beside the rack carry `states` (a lamp, a digit, an outlet, a breaker) and
// `displays` (text, digits or an image); the file keeps what it was given, and
// the kit says which of it the device can take (statesFor, displaysFor). This
// is the one place the page turns an entry into what a drawing is handed, for
// 2D (paintFace) and 3D (the same maps, set on the entry's own relief scope:
// rack3d.js), so the two cannot drift. No fetch of its own: the bytes of a
// library picture come from the caller.

import {zeroUOf} from '../model.js';
import {configFacts} from '../catalog.js';
import {statesFor} from '../states.js';
import {displaysFor} from '../displays.js';
import {loadDisplayImages, paintDisplays} from '../../displays.js';
import {boundLamps, expandStates} from '../../states.js';

const plain = v => !!v && typeof v === 'object' && !Array.isArray(v);
const some = v => plain(v) && Object.keys(v).length > 0;

// True when any entry of the rack says what a lamp is or what a display shows:
// the rack with none is drawn as it always was, and reads no parts list for it.
export const paints = rack => [...(rack.items || []), ...zeroUOf(rack)].some(e => some(e.states) || some(e.displays));

// {id: {states: {path: state}, displays: {path: content}}} for every entry that
// has something the device can take. `ctx` is the kit's per-call context (the
// parts lists: slotsOf, compByRef); `bytesOf(path)` answers a library picture's
// bytes. An entry whose parts list is not loaded paints nothing, as the kit's
// own functions say.
export async function paintMaps(rack, ctx, bytesOf) {
  const out = new Map();
  for (const entry of [...(rack.items || []), ...zeroUOf(rack)]) {
    if (!some(entry.states) && !some(entry.displays)) continue;
    const slots = typeof ctx?.slotsOf === 'function' ? ctx.slotsOf(entry.ref) : null;
    const facts = slots && !slots.error ? configFacts(slots, entry.cfg) : null;
    const states = facts && some(entry.states) ? statesFor(entry, facts) : {};
    const shown = some(entry.displays) ? displaysFor(entry, ctx) : {};
    const {displays} = await loadDisplayImages(shown, bytesOf);
    if (some(states) || some(displays)) out.set(entry.id, {states, displays});
  }
  return out;
}

// Paint one entry's maps into a drawing's group (2D). The state classes are the
// ones the drawing's own stylesheet has a rule for (`state-<name>`); a lamp
// bound to an outlet with `for:` takes its outlet's state (states.js
// expandStates, the rule 3D's relief applies too). A path the drawing does not
// have is skipped: the kit's notices say so.
export function paintFace(root, paint) {
  if (!root || !paint) return root;
  if (some(paint.states)) {
    const named = Object.fromEntries(Object.entries(paint.states).map(([p, s]) => [p, `state-${s}`]));
    const cssEscape = root.ownerDocument.defaultView.CSS.escape;
    for (const [path, cls] of Object.entries(expandStates(named, boundLamps(root)))) {
      for (const el of root.querySelectorAll(`[data-path="${cssEscape(path)}"]`)) {
        for (const c of [...el.classList]) if (c.startsWith('state-')) el.classList.remove(c);
        el.classList.add(cls);
      }
    }
  }
  if (some(paint.displays)) paintDisplays(root, paint.displays);
  return root;
}

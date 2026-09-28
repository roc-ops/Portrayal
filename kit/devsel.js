// One device picker, used in two places: the tab shell's nav and the shell's own
// header when a page is opened on its own.
//
// The rule the demo now follows is that the outer shell owns *which device* and
// a tab owns *how you are looking at it* - config, view, 2D/3D, colour. Before
// this there were two device menus kept in step by postMessage, which is two
// sources of truth for one piece of state; the sync existed only to hide that.
// So the picker is a component, and the page that owns the state mounts it.
//
//   const pick = createDevicePicker({mount: el, devices: DEVICES, value: name,
//                                    listings: LISTINGS,       // optional
//                                    onchange: (name, {listing}) => ...});
//   pick.value = 'as7946-30xb';        // set without firing onchange
//   pick.listing                        // 'arrcus/as7726-32x', or null
//
// Two stages: vendor, then device. Vendor first because it is the one axis
// everybody knows before they start - you come looking for "the Edgecore box",
// not for "the aggregation router". The device list is grouped by the vendor's
// own portfolio words.

// `<optgroup>` cannot nest, and building a custom listbox to get a third level
// would cost the keyboard and screen-reader behaviour a native select has for
// free. So two levels of the taxonomy are composed into the group label and the
// third goes in the option text:
//
//   Service Provider · Aggregation Router
//       AGR400 — AS7946-30XB
//
// A device with no `portfolio:` block sorts under its manufacturer alone, as a
// bare option above the groups. Most of the library is in that state and will
// be for a while; the taxonomy is harvested as devices are touched, not
// backfilled as a migration.
const groupLabel = p => [p?.line, p?.family].filter(Boolean).join(' · ');
export const deviceLabel = d =>
  d._label ? d._label
  : d.portfolio?.series ? `${d.portfolio.series} — ${d.model}` : d.model;

// A NOS VENDOR SELLS SOMEBODY ELSE'S METAL. `listings.json` (#674) says Arrcus
// lists the AS7726-32X and IP Infusion the S9510-28DC, and a buyer of either
// looks for it under the vendor they bought it from - so each listing is an
// entry of its own, under its own manufacturer and filed by its own portfolio
// words, which need not be the ODM's. It draws nothing: `name` is the
// hardware's, so choosing it loads the hardware's drawing, and `_listing` is
// what remembers which vendor's entry was chosen.
//
// Every entry carries a `_key` - the value its <option> holds. A device's key
// is its bare name, as before; a listing's is its `<ns>/<id>`, which no device
// name can collide with because names carry no slash.
export function pickerEntries(devices, listings = {}) {
  const byHw = new Map(devices.map(d => [`${d.ns}/${d.name}`, d]));
  const out = devices.map(d => ({...d, _key: d.name, _listing: null}));
  for (const [key, ls] of Object.entries(listings || {})) {
    const hw = byHw.get(ls.hardware);
    if (!hw) continue;                       // a listing of a box this build lacks
    const own = ls.model && ls.model !== hw.model ? ls.model : null;
    const names = (ls.aliases || []).map(a => a?.name).filter(Boolean);
    out.push({
      ...hw, _key: key, _listing: key,
      manufacturer: ls.manufacturer || ls.ns || key.split('/')[0],
      model: own || hw.model,
      portfolio: ls.portfolio || {},
      _label: `${own ? `${own} — ` : ''}${hw.manufacturer} ${hw.model}`,
      search: [hw.search, hw.manufacturer, hw.model, ls.ns, ls.nos, ls.model, ...names,
               ...Object.values(ls.portfolio || {})].filter(Boolean).join(' '),
    });
  }
  return out;
}

// Everything a person might type. Past about fifty devices a three-deep grouped
// select is worse than a flat one - more depth to navigate, no less to read - so
// the filter is not a refinement of the grouping, it is the other way in, and it
// has to be built at the same time or it never gets built.
//
// The names alone are not enough, and the failures were measured: "400g",
// "qumran" and "roadm" all found nothing while a device with 400G ports, four
// with a Qumran ASIC and two ROADM line units sat in the list. `description`
// finds them, but it indexes prose - what a query finds then depends on how
// somebody worded a summary. `search` is the durable answer: a blob the build
// flattens from the device's own data, including GROUP attrs, which is where the
// answer usually lives. The AGR400 says 400G in exactly one place,
// `groups.qsfpdd-400g.attrs.speed`; its device attrs say "2.4 Tb/s" and never
// mention it.
//
// Both stay in the list. `description` still carries words no structured field
// has, `attrs` is read if a device entry ever carries one directly, and a build
// that predates `search` degrades to what it used to do rather than to nothing.
const haystack = d => [d.manufacturer, d.model, d.name, d.description,
                       d.portfolio?.series, d.portfolio?.family, d.portfolio?.line,
                       d.search, d.attrs && Object.values(d.attrs).join(' ')]
  .filter(Boolean).join(' ').toLowerCase();

const cmp = (a, b) => a.localeCompare(b, undefined, {numeric: true});

const CSS = `
  .devpick { display:flex; gap:0.55rem; align-items:center; flex-wrap:wrap; }
  .devpick label { display:flex; gap:0.3rem; align-items:center;
                   font-size:0.75rem; color:var(--dim, #8d939a); }
  .devpick select, .devpick input {
      background:var(--field, #1c1f23); color:var(--ink, #d7dbdf); border:1px solid var(--field-line, #33373c); border-radius:6px;
      padding:0.22rem 0.35rem; font-size:0.85rem; font-family:inherit; max-width:18rem; }
  .devpick input { width:7.5rem; }
  .devpick input::placeholder { color:var(--hint, #6b7178); }
  .devpick input:focus { outline:none; border-color:var(--accent, #4c9aff); }
  .devpick .none { color:var(--warn, #f59e0b); font-size:0.72rem; }
`;

let cssDone = false;

export function createDevicePicker({mount, devices, value, onchange, listings, listing}) {
  if (!cssDone) {
    document.head.appendChild(Object.assign(document.createElement('style'),
                                            {textContent: CSS}));
    cssDone = true;
  }

  const all = pickerEntries(devices, listings).sort((a, b) => cmp(a.manufacturer, b.manufacturer)
                                       || cmp(groupLabel(a.portfolio), groupLabel(b.portfolio))
                                       || cmp(deviceLabel(a), deviceLabel(b)));
  for (const d of all) d._hay = haystack(d);

  const root = document.createElement('span');
  root.className = 'devpick';
  root.innerHTML =
    `<label>filter <input type="search" spellcheck="false"
        placeholder="AGR, 400G, ROADM…"
        title="Matches manufacturer, model, series, family and description. Enter picks the first match."></label>`
  + `<label>vendor <select class="ven"></select></label>`
  + `<label>device <select class="dev"></select></label>`;
  const q = root.querySelector('input');
  const ven = root.querySelector('.ven');
  const dev = root.querySelector('.dev');
  mount.appendChild(root);

  // `current` is an entry KEY: a device name, or a listing's `<ns>/<id>`.
  const byKey = k => all.find(d => d._key === k);
  let current = (listing && byKey(listing)?.name === (value || byKey(listing)?.name)
                 ? listing : null) || value || all[0]?._key;
  // The chosen vendor is state in its own right, not a projection of the chosen
  // device: someone who picks "Smartoptics" wants to see the Smartoptics list
  // before committing to one of them, and recomputing it from the device would
  // snap the menu back under them.
  let vendor = byKey(current)?.manufacturer;

  const matches = () => {
    const toks = q.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    if (!toks.length) return all;
    return all.filter(d => toks.every(t => d._hay.includes(t)));
  };

  function paint() {
    const hits = matches();
    const hit = new Set(hits);
    const cur = byKey(current);
    // The selected device stays reachable whatever the filter says, because a
    // menu that disagrees with the drawing on screen is worse than one extra
    // row - but it is labelled as the selection rather than left looking like a
    // match, or "no device matched" reads as "one device matched".
    const kept = cur && !hit.has(cur);
    const vendors = [...new Set(hits.map(d => d.manufacturer)
                                    .concat(cur ? [cur.manufacturer] : []))].sort(cmp);
    // Filtering to one vendor and leaving the menu on another is the whole
    // interaction failing silently: the device list goes empty and nothing says
    // why. The chosen vendor survives only while it still has matches.
    const live = new Set(hits.map(d => d.manufacturer));
    if (!vendors.includes(vendor) || (live.size && !live.has(vendor)))
      vendor = live.has(cur?.manufacturer) ? cur.manufacturer
             : [...live].sort(cmp)[0] || cur?.manufacturer || vendors[0] || '';

    ven.innerHTML = vendors.map(v =>
      `<option value="${v.replace(/"/g, '&quot;')}">${v}</option>`).join('');
    ven.value = vendor;

    const list = all.filter(d => d.manufacturer === vendor && hit.has(d));
    const groups = new Map();
    for (const d of list) {
      const g = groupLabel(d.portfolio);
      if (!groups.has(g)) groups.set(g, []);
      groups.get(g).push(d);
    }
    const opt = d =>
      `<option value="${d._key}">${deviceLabel(d).replace(/</g, '&lt;')}</option>`;
    // ungrouped first, so the groups read as a block rather than being split by
    // whichever devices happen to have no portfolio words yet
    let html = (groups.get('') || []).map(opt).join('');
    for (const g of [...groups.keys()].filter(Boolean).sort(cmp))
      html += `<optgroup label="${g.replace(/"/g, '&quot;')}">`
            + groups.get(g).map(opt).join('') + `</optgroup>`;
    if (kept && cur.manufacturer === vendor)
      html = `<optgroup label="current selection">${opt(cur)}</optgroup>` + html;
    // Typing can move the vendor menu off the device that is actually on the
    // stage. Nothing is loaded until the user asks for it, so the menu says so
    // rather than naming a device it has not opened.
    const away = cur && cur.manufacturer !== vendor;
    if (away) html = `<option value="">${list.length} match${list.length === 1 ? '' : 'es'}`
                   + ` \u2014 pick one</option>` + html;
    dev.innerHTML = html;
    dev.value = away ? ''
              : ([...list, ...(kept ? [cur] : [])].some(d => d._key === current)
                 ? current : (list[0]?._key || ''));
    dev.disabled = !list.length && !kept;

    root.querySelector('.none')?.remove();
    if (!hits.length) root.insertAdjacentHTML('beforeend',
      `<span class="none">no device matches \u201c${q.value.replace(/</g, '&lt;')}\u201d</span>`);
  }

  const pick = key => {
    if (!key || key === current) return;
    current = key;
    const e = byKey(key);
    vendor = e?.manufacturer || vendor;
    paint();
    // THE DEVICE NAME FIRST, as before, so a caller written for devices alone
    // keeps working; which vendor's entry it was comes second. Choosing another
    // vendor's entry for the box already on the stage is still a change - the
    // caller may name its ports differently - so it is reported too.
    if (e) onchange?.(e.name, {listing: e._listing});
  };

  q.oninput = paint;
  // Enter takes the first match without reaching for the device menu, which is
  // what the filter is for once the library is large.
  q.onkeydown = e => {
    if (e.key !== 'Enter') return;
    e.preventDefault();
    const first = matches().filter(d => d.manufacturer === vendor)[0] || matches()[0];
    if (first) pick(first._key);
  };
  // Asking for a vendor by hand is a request to look at that vendor, so it lands
  // on its first device rather than leaving the two selects describing different
  // boxes. Typing does not: the filter narrows what is on offer, and nothing is
  // opened until you choose it.
  const firstIn = v => matches().find(d => d.manufacturer === v);
  ven.onchange = () => {
    vendor = ven.value;
    const first = firstIn(vendor);
    paint();
    if (first) pick(first._key);
  };
  dev.onchange = () => pick(dev.value);

  paint();

  return {
    el: root,
    // THE DEVICE NAME, whichever entry is chosen - what a caller loads.
    get value() { return byKey(current)?.name ?? current; },
    set value(name) {
      // Setting the device a listing entry already shows keeps that entry: the
      // stage reloading the same box must not throw the reader back under its
      // ODM. A listing key may be set directly too.
      if (!name || !byKey(name)) return;
      if (byKey(current)?.name === name && byKey(current)?._listing && !name.includes('/')) return;
      current = name;
      vendor = byKey(name).manufacturer;
      paint();
    },
    // THE LISTING KEY when a NOS vendor's entry is chosen, else null.
    get listing() { return byKey(current)?._listing ?? null; },
    focusFilter: () => q.focus(),
  };
}

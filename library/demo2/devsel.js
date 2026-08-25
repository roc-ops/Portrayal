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
//                                    onchange: name => ...});
//   pick.value = 'as7946-30xb';        // set without firing onchange
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
  d.portfolio?.series ? `${d.portfolio.series} — ${d.model}` : d.model;

// Everything a person might type. Past about fifty devices a three-deep grouped
// select is worse than a flat one - more depth to navigate, no less to read - so
// the filter is not a refinement of the grouping, it is the other way in, and it
// has to be built at the same time or it never gets built.
const haystack = d => [d.manufacturer, d.model, d.name, d.portfolio?.series,
                       d.portfolio?.family, d.portfolio?.line]
  .filter(Boolean).join(' ').toLowerCase();

const cmp = (a, b) => a.localeCompare(b, undefined, {numeric: true});

const CSS = `
  .devpick { display:flex; gap:0.55rem; align-items:center; flex-wrap:wrap; }
  .devpick label { display:flex; gap:0.3rem; align-items:center;
                   font-size:0.75rem; color:#8d939a; }
  .devpick select, .devpick input {
      background:#1c1f23; color:#d7dbdf; border:1px solid #33373c; border-radius:6px;
      padding:0.22rem 0.35rem; font-size:0.85rem; font-family:inherit; max-width:18rem; }
  .devpick input { width:7.5rem; }
  .devpick input::placeholder { color:#6b7178; }
  .devpick input:focus { outline:none; border-color:#4c9aff; }
  .devpick .none { color:#f59e0b; font-size:0.72rem; }
`;

let cssDone = false;

export function createDevicePicker({mount, devices, value, onchange}) {
  if (!cssDone) {
    document.head.appendChild(Object.assign(document.createElement('style'),
                                            {textContent: CSS}));
    cssDone = true;
  }

  const all = [...devices].sort((a, b) => cmp(a.manufacturer, b.manufacturer)
                                       || cmp(groupLabel(a.portfolio), groupLabel(b.portfolio))
                                       || cmp(deviceLabel(a), deviceLabel(b)));
  for (const d of all) d._hay = haystack(d);

  const root = document.createElement('span');
  root.className = 'devpick';
  root.innerHTML =
    `<label>filter <input type="search" spellcheck="false"
        placeholder="AGR, 400G…"
        title="Matches manufacturer, model, series and family. Enter picks the first match."></label>`
  + `<label>vendor <select class="ven"></select></label>`
  + `<label>device <select class="dev"></select></label>`;
  const q = root.querySelector('input');
  const ven = root.querySelector('.ven');
  const dev = root.querySelector('.dev');
  mount.appendChild(root);

  let current = value || all[0]?.name;
  const byName = n => all.find(d => d.name === n);
  // The chosen vendor is state in its own right, not a projection of the chosen
  // device: someone who picks "Smartoptics" wants to see the Smartoptics list
  // before committing to one of them, and recomputing it from the device would
  // snap the menu back under them.
  let vendor = byName(current)?.manufacturer;

  const matches = () => {
    const toks = q.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    if (!toks.length) return all;
    return all.filter(d => toks.every(t => d._hay.includes(t)));
  };

  function paint() {
    const hits = matches();
    const cur = byName(current);
    // The selected device always stays reachable: a filter that hides what you
    // are looking at, and so silently disagrees with the drawing on screen, is
    // worse than one that shows a row it did not match.
    const vendors = [...new Set(hits.map(d => d.manufacturer)
                                    .concat(cur ? [cur.manufacturer] : []))].sort(cmp);
    if (!vendors.includes(vendor))
      vendor = vendors.includes(cur?.manufacturer) ? cur.manufacturer : vendors[0] || '';

    ven.innerHTML = vendors.map(v =>
      `<option value="${v.replace(/"/g, '&quot;')}">${v}</option>`).join('');
    ven.value = vendor;

    const hit = new Set(hits);
    const list = all.filter(d => d.manufacturer === vendor && (hit.has(d) || d === cur));

    const groups = new Map();
    for (const d of list) {
      const g = groupLabel(d.portfolio);
      if (!groups.has(g)) groups.set(g, []);
      groups.get(g).push(d);
    }
    const opt = d =>
      `<option value="${d.name}">${deviceLabel(d).replace(/</g, '&lt;')}</option>`;
    // ungrouped first, so the groups read as a block rather than being split by
    // whichever devices happen to have no portfolio words yet
    let html = (groups.get('') || []).map(opt).join('');
    for (const g of [...groups.keys()].filter(Boolean).sort(cmp))
      html += `<optgroup label="${g.replace(/"/g, '&quot;')}">`
            + groups.get(g).map(opt).join('') + `</optgroup>`;
    dev.innerHTML = html;
    dev.value = list.some(d => d.name === current) ? current : (list[0]?.name || '');
    dev.disabled = !list.length;

    root.querySelector('.none')?.remove();
    if (!hits.length) root.insertAdjacentHTML('beforeend',
      `<span class="none">no device matches \u201c${q.value.replace(/</g, '&lt;')}\u201d</span>`);
  }

  const pick = name => {
    if (!name || name === current) return;
    current = name;
    vendor = byName(name)?.manufacturer || vendor;
    paint();
    onchange?.(name);
  };

  q.oninput = paint;
  // Enter takes the first match without reaching for the device menu, which is
  // what the filter is for once the library is large.
  q.onkeydown = e => {
    if (e.key !== 'Enter') return;
    e.preventDefault();
    const first = matches().filter(d => d.manufacturer === vendor)[0] || matches()[0];
    if (first) pick(first.name);
  };
  // Changing vendor lands on that vendor's first device rather than leaving the
  // two selects describing different boxes.
  ven.onchange = () => { vendor = ven.value; paint(); pick(dev.value); };
  dev.onchange = () => pick(dev.value);

  paint();

  return {
    el: root,
    get value() { return current; },
    set value(name) {
      if (!name || !byName(name)) return;
      current = name;
      vendor = byName(name).manufacturer;
      paint();
    },
    focusFilter: () => q.focus(),
  };
}

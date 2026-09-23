// WHERE A FIBRE GOES, for the explorer. A fibre endpoint `X.n` is drawn at
// path `X/n` (L112), a rear endpoint `rear:X.n` at `X/n` on the rear face.
// The graph and the vendor's front numbers come from components.json
// (`optical.ends`, written by components_index.py from optical_ports), so
// nothing here numbers a fibre - it only reads.
//
// A FAN-OUT `to` IS AN ARRAY, not a string: a splitter's common end (e.g.
// smartoptics/ppm-ocu-50-50's common.1) reaches several branches at once, so
// `farPath` returns an array of paths for it and `fibreLabel` spells each
// branch, joined with ", ". A branch's own `to` is still a single string
// pointing back at the one common end.

export function moduleOf(path) {
  if (!path) return null;
  // Greedy and segment-anchored: backtracks from the end of the string to
  // the LAST "/module" that is a whole path segment (followed by "/" or the
  // end), so a part id that itself starts with "module" (`modulex`) cannot
  // be mistaken for the segment "module" partway through a lastIndexOf scan.
  return path.match(/^(.*\/module)(?=\/|$)/)?.[1] ?? null;
}

const ids = c => new Set((c?.parts || []).map(p => String(p.id)));

export function fibreOf(path, entry, compByRef) {
  const module = moduleOf(path);
  if (!module || !entry) return null;
  const rest = path.slice(module.length + 1).split('/');
  if (rest.length !== 2 || !/^\d+$/.test(rest[1])) return null;
  const [part, n] = rest;
  const rear = entry.faces?.rear ? compByRef(entry.faces.rear) : null;
  // Front and rear ids never collide (L112), so a part missing from the
  // front but present on the rear is unambiguously a rear endpoint.
  const face = !ids(entry).has(part) && ids(rear).has(part) ? 'rear:' : '';
  const endpoint = `${face}${part}.${n}`;
  return entry.optical?.ends?.[endpoint] ? {module, endpoint} : null;
}

function pathOf(module, endpoint) {
  const [, part, n] = endpoint.match(/^(?:[a-z]+:)?(.+)\.(\d+)$/) || [];
  return part ? `${module}/${part}/${n}` : null;
}

export function farPath(module, entry, endpoint) {
  const to = entry?.optical?.ends?.[endpoint]?.to;
  if (!to) return null;
  return Array.isArray(to) ? to.map(t => pathOf(module, t)) : pathOf(module, to);
}

const spell = ep => ep.replace(/^rear:/, 'rear ').replace(/\.(\d+)$/, ' · $1');

export function fibreLabel(entry, endpoint) {
  const end = entry?.optical?.ends?.[endpoint];
  if (!end) return null;
  if (endpoint.startsWith('rear:')) {
    const n = endpoint.match(/\.(\d+)$/)[1];
    return end.label ? `${n} → front ${end.label}` : null;
  }
  const to = Array.isArray(end.to) ? end.to.map(spell).join(', ') : spell(end.to);
  // A front end with no label (a splitter's common port can legitimately
  // have none) never invents a number - it spells the endpoint itself.
  return `${end.label ?? spell(endpoint)} → ${to}`;
}

export function connectorLabel(entry, part, face) {
  if (face !== 'rear') return null;
  const nums = Object.entries(entry?.optical?.ends || {})
    .filter(([ep]) => ep.startsWith(`rear:${part}.`))
    .map(([, e]) => e.label)
    .filter(label => label != null)
    .map(Number).filter(Number.isFinite).sort((a, b) => a - b);
  if (!nums.length) return null;
  const run = nums.every((v, i) => v === nums[0] + i);
  return run ? `front ${nums[0]}-${nums[nums.length - 1]}` : `front ${nums.join(', ')}`;
}

// What a NOS calls each port, read from a listing (#712).
//
// A listing (listings.json, #674) states its NOS's port names as rules:
//
//   {physical: 'port-{n}', name: 'Ethernet{4*n-4}', range: '1-32',
//    breakout: {modes: [4x25g, 4x10g], child-name: 'Ethernet{4*n-4}_{i}'}}
//
// THE SAME GRAMMAR AS THE EXPORTER, OR TWO ANSWERS TO ONE QUESTION. The DCIM
// export expands these rules in Python (`dcim_export.listing_names`), and a
// port the inspector calls one thing while the NetBox document calls it
// another is the drift #63 was filed about. So this is a port of that
// function, not a reading of the same data: `{n}` runs over `range`, a name's
// braces take arithmetic over n with Python's semantics - `/` truncates, `//`
// floors, `%` takes the divisor's sign - `{i}` (a breakout child's index) is
// left standing, and a later rule for the same port wins. test_nos_names_js.py
// runs every listing in the build through both and compares them.
//
// Parsed, never eval'd: a name pattern is data out of a file, and only numbers,
// `n`, parentheses and + - * / // % are allowed. Anything else throws, as the
// Python refuses it.

function evalIndex(expr, n) {
  const toks = expr.match(/\/\/|\d+(?:\.\d+)?|[n+\-*/%()]|\S/g) || [];
  let k = 0;
  const peek = () => toks[k];
  const take = t => { if (toks[k] !== t) throw new Error(`name pattern {${expr}}: expected ${t}`); k++; };
  const atom = () => {
    const t = toks[k++];
    if (t === 'n') return n;
    if (t === '(') { const v = sum(); take(')'); return v; }
    if (/^\d/.test(t ?? '')) return Number(t);
    throw new Error(`name pattern {${expr}}: only arithmetic over n is allowed`);
  };
  const unary = () => {
    if (peek() === '-') { k++; return -unary(); }
    if (peek() === '+') { k++; return +unary(); }
    return atom();
  };
  const product = () => {
    let v = unary();
    for (;;) {
      const op = peek();
      if (op !== '*' && op !== '/' && op !== '//' && op !== '%') return v;
      k++;
      const r = unary();
      if ((op === '/' || op === '//' || op === '%') && r === 0)
        throw new Error(`name pattern {${expr}}: division by zero`);
      v = op === '*' ? v * r
        : op === '/' ? v / r
        : op === '//' ? Math.floor(v / r)
        : ((v % r) + r) % r;                  // Python's %: the divisor's sign
    }
  };
  const sum = () => {
    let v = product();
    while (peek() === '+' || peek() === '-') { const op = toks[k++]; const r = product(); v = op === '+' ? v + r : v - r; }
    return v;
  };
  const v = sum();
  if (k !== toks.length) throw new Error(`name pattern {${expr}}: only arithmetic over n is allowed`);
  return Math.trunc(v);                       // Python's int(): toward zero
}

// Fill every `{...}` in a pattern for port n; `{i}` stays for the reader.
export function expandName(pattern, n) {
  return String(pattern).replace(/\{([^{}]*)\}/g,
    (whole, inner) => inner.trim() === 'i' ? whole : String(evalIndex(inner, n)));
}

// physical id -> {name, breakout}, as `dcim_export.listing_names` returns it.
export function listingNames(listing) {
  const out = {};
  for (const rule of listing?.interfaces || []) {
    const {physical, name} = rule;
    if (String(physical).includes('{n}')) {
      if (!rule.range) throw new Error(`listing interface ${physical} has {n} and no range`);
      const [lo, hi] = String(rule.range).split('-', 2).map(Number);
      for (let n = lo; n <= hi; n++)
        out[physical.replaceAll('{n}', String(n))] = {name: expandName(name, n), breakout: rule.breakout || null, n};
    } else {
      out[physical] = {name, breakout: rule.breakout || null, n: null};
    }
  }
  return out;
}

// The breakout a port allows, as a line of prose - `dcim_export.breakout_note`
// without the length cut, which is the DCIM description's limit and not ours.
export function breakoutNote(breakout, n) {
  if (!breakout) return '';
  const modes = (breakout.modes || []).join(', ');
  const parts = [modes ? `Breakout: ${modes}` : 'Breakout capable'];
  if (breakout['child-name'] && n != null) parts.push(`children ${expandName(breakout['child-name'], n)}`);
  return parts.join('; ');
}

// What the inspector says about one port of the device on the stage, or null
// when no listing is chosen. A port the listing does not name gets no guess:
// where the listing records WHY (a `*-names` gap - `arcos-port-names`,
// `dnos-management-names`), that is what is said.
export function nosNameFor(listing, path) {
  if (!listing) return null;
  const vendor = listing.manufacturer || listing.ns || 'NOS';
  const hit = listingNames(listing)[path];
  if (hit) return {vendor, name: hit.name, note: breakoutNote(hit.breakout, hit.n)};
  const gap = (listing.gaps || []).find(g => /-names$/.test(g.what || ''));
  return {vendor, name: null, gap: gap?.what || null};
}

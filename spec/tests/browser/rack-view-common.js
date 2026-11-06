// What the golden recorder and rack-view-2d.html share, so that a golden and
// its comparison cannot disagree on format (docs/rack-views-design.md §6):
// the one serialiser (attributes sorted, numbers rounded to six decimals) and
// the two fixtures as documents.

const round = s => s.replace(/-?\d+\.\d+(?:e[-+]?\d+)?/gi, n => String(Number(Number(n).toFixed(6)) + 0));
const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

export function serialise(node) {
  if (node.nodeType === 3) return esc(round(node.nodeValue));
  if (node.nodeType !== 1) return '';
  const attrs = [...node.attributes].sort((a, b) => (a.name < b.name ? -1 : a.name > b.name ? 1 : 0))
    .map(a => ` ${a.name}="${esc(round(a.value)).replace(/"/g, '&quot;')}"`).join('');
  const kids = [...node.childNodes].map(serialise).join('');
  return `<${node.nodeName}${attrs}>${kids}</${node.nodeName}>`;
}

const json = async url => {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  return r.json();
};

/** {acceptance, 'cable-lay'}: each fixture as parseDoc reads it. `fixtures` is
 *  the URL of spec/tests/fixtures/. The cable-lay file is one bare rack, so it
 *  is wrapped in a document as a rack file holds it. */
export async function loadFixtures(fixtures, parseDoc) {
  const lay = await json(`${fixtures}cable-lay/cable-lay-rack.json`);
  delete lay._source; delete lay._note;
  return {
    acceptance: parseDoc(await json(`${fixtures}racks/acceptance.rack.json`)),
    'cable-lay': parseDoc({format: 'portrayal-rack', version: 4, id: 'd', racks: [lay]}),
  };
}

/** A golden's text without its `# ` header lines. */
export const goldenBody = text => text.split('\n').filter(l => !l.startsWith('# ')).join('\n').trim();

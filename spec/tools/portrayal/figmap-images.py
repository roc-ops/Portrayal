"""Map "Figure N" captions to the docling-extracted PNGs, for any converted doc.

The extraction writes one fig-NNNN.png per `<!-- image -->` marker, in document
order, so the Nth marker is fig-(N-1).png. What it does NOT write is which
FIGURE each one is - the caption sits in the prose, usually before the marker
and sometimes after it, and some markers are icons with no caption at all.

Without this map every reference to "ISM figure 8" means opening the PDF again,
which is the thing the fact sheet exists to stop.

    figmap.py <converted-dir> [out.json]
"""
import json
import pathlib
import re
import sys

CAP = re.compile(r'^(?:#+\s*)?Figure\s+(\d+)\.\s*(.*)$')


def build(conv):
    """Pair images with captions GREEDILY AND IN ORDER, not by proximity.

    Neither simple rule works on these documents, and each fails differently:

      "the caption precedes its image"  - true for most, but "Inside the system"
      puts the caption two lines AFTER, so those come out attached to whatever
      figure was pending from pages earlier.

      "take the nearest caption"        - true for those, and WRONG for the PSU
      pair: figure 11's caption is followed by its callout list and a whole
      table before its image appears, by which point figure 12's caption is two
      lines away and steals it. Checked against the pictures: fig-0018 is the AC
      supply (figure 11) and fig-0019 the DC one (figure 12), so nearest-wins
      shifts that whole section by one.

    What holds is ORDER. Captions and images both run down the page, so the nth
    unclaimed caption takes the nth image, and a caption is only a candidate
    while it has no image yet. Uncaptioned icons fall out because every caption
    within reach is already spoken for.
    """
    lines = pathlib.Path(conv, 'doc.md').read_text().splitlines()
    caps, imgs = [], []
    for i, l in enumerate(lines):
        m = CAP.match(l.strip())
        if m:
            caps.append({'n': int(m.group(1)), 'text': m.group(2).strip(),
                         'line': i, 'img': None})
        if l.strip() == '<!-- image -->':
            imgs.append({'idx': len(imgs), 'line': i, 'cap': None})
    BEFORE, AFTER = 40, 8          # how far a caption may sit from its image
    for e in imgs:
        best = None
        for c in caps:
            if c['img'] is not None:
                continue
            d = e['line'] - c['line']
            if not -AFTER <= d <= BEFORE:
                continue
            # A PRECEDING CAPTION WINS OVER A NEARER FOLLOWING ONE. Figure 11's
            # caption is separated from its image by a callout list and a whole
            # table, which puts figure 12's caption two lines away on the other
            # side - and nearest-wins then shifts the AC supply, the DC supply
            # and the drive indicators each one place along. Ranking "before"
            # ahead of "after" fixes those without disturbing the sections where
            # the caption genuinely follows, because there the preceding caption
            # is already claimed.
            rank = (0 if d >= 0 else 1, abs(d))
            if best is None or rank < best[0]:
                best = (rank, c)
        if best:
            best[1]['img'] = e['idx']
            e['cap'] = (best[1]['n'], best[1]['text'], best[1]['line'])
    byfig = {}
    for e in imgs:
        if e['cap'] and e['cap'][0] not in byfig:
            byfig[e['cap'][0]] = (e['idx'], e['cap'][1], e['line'])
    return imgs, byfig


if __name__ == '__main__':
    conv = sys.argv[1]
    imgs, byfig = build(conv)
    print(f'{len(imgs)} images, {len(byfig)} figures identified')
    for n in sorted(byfig):
        idx, cap, ln = byfig[n]
        print(f'  Figure {n:>3}: fig-{idx:04d}.png  line {ln:>5}  {cap[:66]}')
    if len(sys.argv) > 2:
        pathlib.Path(sys.argv[2]).write_text(json.dumps(
            {str(k): {'file': f'fig-{v[0]:04d}.png', 'caption': v[1],
                      'line': v[2]} for k, v in sorted(byfig.items())}, indent=1))

"""A part that spans between two side brackets meets both of them (#971).

The FS DINRAIL2U and DINRAIL4U drew their rail panel at the rail's 400 mm, the
figure the datasheet dimensions, while the brackets stand 421.2 and 419.7 apart:
a gap of about 10 mm each side in 2D and in 3D, the shelf three loose pieces.
The panel is screwed to the brackets through their slots; it meets them.

The rule is stated on what the build writes, for every device, not on two names:
in any compiled view with exactly two upright `side-bracket` strips, every
top-level `bracket` placement standing between them (the elements file) and every
`rail-panel` decor (the compiled source) runs from the one strip's inner face to
the other's. At the default position, which is the only one the format draws
until #950 lets the panel move; a moved panel keeps its width, so the rule holds
there too.
"""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"
TOL = 0.05


@pytest.fixture(scope="module")
def built():
    if not (DIST / "devices.json").exists():
        pytest.skip("library/dist not built")
    return DIST


def _strips(decor):
    """The two upright side-bracket strips of a view, as (inner-left, inner-right)."""
    ups = sorted((d for d in decor if d.get("kind") == "side-bracket" and d["size"][0] < d["size"][1]),
                 key=lambda d: d["at"][0])
    if len(ups) != 2:
        return None
    return ups[0]["at"][0] + ups[0]["size"][0], ups[1]["at"][0]


def _spans(built):
    """Every spanning part found: (where, x0, x1, inner-left, inner-right)."""
    out = []
    for src in sorted(built.glob("*.source.json")):
        dev = src.name[: -len(".source.json")]
        data = json.loads(src.read_text())
        for view, v in (data.get("views") or {}).items():
            decor = ((v or {}).get("panel") or {}).get("decor") or []
            st = _strips(decor)
            if not st:
                continue
            for d in decor:
                if d.get("kind") == "rail-panel" and d["size"][0] > d["size"][1]:
                    out.append((f"{dev} {view} decor {d['id']}", d["at"][0], d["at"][0] + d["size"][0], *st))
            el = built / f"{dev}.{view}.elements.json"
            if not el.exists():
                continue
            for e in json.loads(el.read_text())["elements"]:
                b = e["box"]
                if e.get("parent") is None and e.get("class") == "bracket" and st[0] - 15 <= b["x"] \
                        and b["x"] + b["w"] <= st[1] + 15:
                    out.append((f"{dev} {view} placement {e['id']}", b["x"], b["x"] + b["w"], *st))
    return out


def test_a_part_between_two_side_brackets_meets_both(built):
    spans = _spans(built)
    devs = {s[0].split()[0] for s in spans}
    # the DIN shelves: the front placement, the rear panel and the two plan edges each
    assert {"dinrail2u", "dinrail4u"} <= devs, f"the sweep found nothing to measure: {sorted(devs)}"
    assert len(spans) >= 8, spans
    bad = [f"{w}: runs {x0:.2f}..{x1:.2f}, the brackets' inner faces are {l:.2f} and {r:.2f}"
           for w, x0, x1, l, r in spans if abs(x0 - l) > TOL or abs(x1 - r) > TOL]
    assert not bad, "\n".join(bad)

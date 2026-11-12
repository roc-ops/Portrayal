"""The Fibrain HD LC holders and the 1U frame, two things drawn once and read twice.

  * A SLEEVE HAS ONE AXIS. An adapter's two ferrules lie on one line, and the front
    face and the rear face of a six-way LC holder draw the same sleeve, so the line
    stands the same distance from the holder's top on both. The rear turns each
    adapter half a turn about its centre, which takes the ferrules from 6.10 to 3.20
    from the top of the 9.30 body: the rear's `at` is where that is put right.
  * THE BOTTOM VIEW DRAWS THE BAR THE TOP VIEW DRAWS. The frame's rear cable bar is
    the part the top view places; the bottom view draws the same strips, upright and
    tie slots, the other way across because the underside is seen from below.
"""
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
FIB = LIB / "components" / "fibrain"

# the six-way LC holders: one row of adapters, so the rear's two faces can share a row
SIX_WAY_LC = ("xmi1021ca", "xmi1021da", "xmi1021ga", "xmi1021ha", "xmi1031ga")

BAR_W = 435.0


def _yaml(path):
    return yaml.safe_load(path.read_text())


def _component(ref):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    return _yaml(LIB / "components" / ns / name / f"v{major}" / "contract.yaml")


def _latest(name):
    majors = sorted(int(p.name[1:]) for p in (FIB / name).iterdir() if re.fullmatch(r"v\d+", p.name))
    return _component(f"fibrain/{name}@{majors[-1]}")


def _axis(part, adapter):
    """Mm from the holder top to the ferrule line of a placed adapter, worked from the
    adapter's own mate point: its y in the 9.30 body, or 9.30 less that when turned."""
    mate_y = adapter["connection-points"]["mate"]["at"][1]
    turned = (part.get("rotate") or 0) % 360 == 180
    return part["at"][1] + (adapter["size"]["h"] - mate_y if turned else mate_y)


def test_a_six_way_rear_shares_the_axis_of_its_front():
    adapter = _component("fibrain/lc-duplex-adapter@1")
    for name in SIX_WAY_LC:
        front = _latest(name)
        rear = _component(front["faces"]["rear"]["ref"])
        rear_parts = {p["id"]: p for p in rear["parts"]}
        assert len(rear_parts) == 6, name
        for part in front["parts"]:
            if not part["ref"].startswith("fibrain/lc-duplex-adapter@"):
                continue
            behind = rear_parts["b" + part["id"][2:]]
            assert abs(_axis(part, adapter) - _axis(behind, adapter)) < 1e-6, (name, part["id"])
            # the body stays on the 21 high face
            assert 0 <= behind["at"][1] and behind["at"][1] + adapter["size"]["h"] <= rear["size"]["h"], (name, part["id"])


def _skin_elements():
    svg = (FIB / "xpu-cable-bar" / "v1" / "skins" / "default.svg").read_text()
    slots = {}
    for pid in ("upper", "lower"):
        d = re.search(rf'<path id="{pid}"[^>]* d="([^"]+)"', svg).group(1)
        slots[pid] = [tuple(map(float, m)) for m in re.findall(r"M ([\d.]+) ([\d.]+) h ([\d.]+) v ([\d.]+) h -[\d.]+ Z", d)]
    upright = tuple(float(v) for v in re.search(
        r'<rect id="upright" x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"', svg).groups())
    return slots, upright


def _frame():
    return _yaml(LIB / "devices" / "fibrain" / "xpu" / "device.yaml")


def test_the_bottom_view_draws_the_cable_bar_the_top_view_places():
    frame = _frame()
    placed = next(p for p in frame["views"]["top"]["components"]["placements"] if p["ref"].startswith("fibrain/xpu-cable-bar@"))
    x0 = placed["at"][0]
    decor = frame["views"]["bottom"]["panel"]["decor"]
    bar = [d for d in decor if d.get("kind") in ("cable-bar", "cable-bar-slot")]
    # no plain rectangle for the whole bar any more
    assert not [d for d in bar if d["size"] == [435, 29]], "the bar is one plain rectangle"

    slots, upright = _skin_elements()
    want = sorted((round(x0 + BAR_W - x - w, 2), y, w, h) for strip in slots.values() for x, y, w, h in strip)
    drawn = sorted((round(d["at"][0], 2), d["at"][1], d["size"][0], d["size"][1]) for d in bar if d["kind"] == "cable-bar-slot")
    assert len(drawn) == 48
    assert drawn == want

    # the two strips and the upright, mirrored across the width
    strips = {d["id"]: d for d in bar if d["kind"] == "cable-bar" and d["size"][0] == 435}
    assert sorted(d["at"][1] for d in strips.values()) == [0, 14.5]
    assert all(d["at"][0] == x0 and d["size"][1] == 14.5 for d in strips.values())
    ux, uy, uw, uh = upright
    line = next(d for d in bar if d["kind"] == "cable-bar" and d["size"][0] != 435)
    assert (round(line["at"][0], 2), line["at"][1], line["size"]) == (round(x0 + BAR_W - ux - uw, 2), uy, [uw, uh])


def test_every_bottom_slot_is_inside_its_strip():
    decor = _frame()["views"]["bottom"]["panel"]["decor"]
    strips = [d for d in decor if d.get("kind") == "cable-bar" and d["size"][0] == 435]
    slots = [d for d in decor if d.get("kind") == "cable-bar-slot"]
    assert len(strips) == 2 and slots, "the bottom view draws no strips and slots"
    for slot in slots:
        x, y = slot["at"]
        w, h = slot["size"]
        assert any(s["at"][0] <= x and x + w <= s["at"][0] + 435 and s["at"][1] <= y and y + h <= s["at"][1] + 14.5
                   for s in strips), slot["id"]
